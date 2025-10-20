import json
from aws_cdk import (
    CfnOutput,
    CfnParameter,
    RemovalPolicy,
    Stack,
    aws_cognito as cognito,
    aws_ecr as ecr,
    aws_iam as iam,
    aws_logs as logs,
    aws_ssm as ssm,
    aws_xray as xray,
)
from cdk_nag import NagSuppressions
from constructs import Construct


# from . import add_common_cdk_nag_suppressions


class BookingAgentCoreStack(Stack):
    """
    AWS CDK Stack for Booking AgentCore Infrastructure

    This stack creates the foundational infrastructure components needed for AgentCore deployment.
    The actual AgentCore runtime must still be deployed using the agentcore CLI tool.
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Get context values for defaults
        agentcore_context = self.node.try_get_context("booking-agent-agentcore") or {}

        self.toolname_from_config = agentcore_context.get("tool-name", "hotel_booking_agent")

        # Parameters with context-based defaults
        self.tool_name = CfnParameter(
            self,
            "ToolName",
            type="String",
            description="Tool name for AgentCore deployment",
            default=agentcore_context.get("tool-name", self.toolname_from_config),
        )

        self.xray_indexing_percentage = CfnParameter(
            self,
            "XRayIndexingPercentage",
            type="Number",
            description="Percentage of X-Ray traces to index for Transaction Search (0-100)",
            default=agentcore_context.get("xray-indexing-percentage", 20),
            min_value=0,
            max_value=100,
        )

        # Create IAM role for AgentCore
        self.agentcore_role = self._create_agentcore_role()

        # Create ECR repository
        self.ecr_repository = self._create_ecr_repository()

        # Create CloudWatch log group
        self.log_group = self._create_log_group()

        # Create X-Ray Transaction Search configuration
        self._create_transaction_search_config()

        # Create SSM parameters
        self._create_ssm_parameters()

        # Apply CDK Nag suppressions
        self._apply_cdk_nag_suppressions()

        # Create outputs
        self._create_outputs()

    def _create_cognito_user_pool(self) -> cognito.UserPool:
        """Create Cognito User Pool for authentication"""

        # Create pool name dynamically from tool name
        pool_name = f"{self.tool_name.value_as_string}.Pool"

        return cognito.UserPool(
            self,
            self.tool_name.value_as_string,
            user_pool_name=pool_name,
            password_policy=cognito.PasswordPolicy(
                min_length=8, require_lowercase=True, require_uppercase=True, require_digits=True, require_symbols=False
            ),
            sign_in_aliases=cognito.SignInAliases(username=True, email=False),
            removal_policy=RemovalPolicy.DESTROY,  # For development - change for production
        )

    def _create_agentcore_role(self) -> iam.Role:
        """Create IAM role for AgentCore execution"""

        # Create the role using assumed_by parameter
        # Note: Using simpler approach for compatibility. Additional security conditions
        # (like source account/ARN restrictions) can be added later if required by AgentCore
        role = iam.Role(
            self,
            "AgentCoreRole",
            role_name=f"{self.region}-agentcore-{self.tool_name.value_as_string}-role",
            assumed_by=iam.ServicePrincipal("bedrock-agentcore.amazonaws.com"),
        )

        # Create and attach the policy
        self.agentcore_policy = iam.Policy(
            self,
            "AgentCorePolicy",
            policy_name="AgentCorePolicy",
            statements=[
                # Bedrock permissions
                iam.PolicyStatement(
                    sid="BedrockPermissions",
                    effect=iam.Effect.ALLOW,
                    actions=["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
                    resources=["arn:aws:bedrock:*::foundation-model/*", "arn:aws:bedrock:*:*:inference-profile/*"],
                ),
                # ECR permissions
                iam.PolicyStatement(
                    sid="ECRImageAccess",
                    effect=iam.Effect.ALLOW,
                    actions=["ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer", "ecr:GetAuthorizationToken"],
                    resources=["*"],
                ),
                iam.PolicyStatement(
                    sid="ECRRepositoryAccess",
                    effect=iam.Effect.ALLOW,
                    actions=["ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer"],
                    resources=[f"arn:aws:ecr:{self.region}:{self.account}:repository/*"],
                ),
                # CloudWatch Logs permissions
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=["logs:DescribeLogStreams", "logs:CreateLogGroup"],
                    resources=[
                        f"arn:aws:logs:{self.region}:{self.account}:log-group:/aws/bedrock-agentcore/runtimes/*"
                    ],
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=["logs:DescribeLogGroups"],
                    resources=[f"arn:aws:logs:{self.region}:{self.account}:log-group:*"],
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=["logs:CreateLogStream", "logs:PutLogEvents"],
                    resources=[
                        f"arn:aws:logs:{self.region}:{self.account}:log-group:/aws/bedrock-agentcore/runtimes/*:log-stream:*"
                    ],
                ),
                # X-Ray permissions for tracing and Transaction Search
                iam.PolicyStatement(
                    sid="XRayTracingPermissions",
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "xray:PutTraceSegments",
                        "xray:PutTelemetryRecords",
                        "xray:GetSamplingRules",
                        "xray:GetSamplingTargets",
                        "xray:GetTraceGraph",
                        "xray:GetTraceSummaries",
                        "xray:BatchGetTraces",
                        "xray:GetServiceGraph",
                        "xray:GetTimeSeriesServiceStatistics",
                    ],
                    resources=["*"],
                ),
                # X-Ray Transaction Search specific permissions
                iam.PolicyStatement(
                    sid="XRayTransactionSearchPermissions",
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "xray:GetTransactionSearchConfig",
                        "xray:SearchTransactions",
                        "xray:GetTransactionSearchResults",
                    ],
                    resources=["*"],
                ),
                # CloudWatch metrics permissions
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=["cloudwatch:PutMetricData"],
                    resources=["*"],
                    conditions={"StringEquals": {"cloudwatch:namespace": "bedrock-agentcore"}},
                ),
                # AgentCore workload access token permissions
                iam.PolicyStatement(
                    sid="GetAgentAccessToken",
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "bedrock-agentcore:GetWorkloadAccessToken",
                        "bedrock-agentcore:GetWorkloadAccessTokenForJWT",
                        "bedrock-agentcore:GetWorkloadAccessTokenForUserId",
                    ],
                    resources=[
                        f"arn:aws:bedrock-agentcore:{self.region}:{self.account}:workload-identity-directory/default*",
                        f"arn:aws:bedrock-agentcore:{self.region}:{self.account}:workload-identity-directory/default/workload-identity/{self.tool_name.value_as_string}-*",
                    ],
                ),
                # SSM Parameter Store permissions
                iam.PolicyStatement(
                    sid="ParameterStoreReadOnly",
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "ssm:GetParameter",
                        "ssm:GetParameters",
                        "ssm:GetParametersByPath",
                        "ssm:DescribeParameters",
                        "ssm:List*",
                    ],
                    resources=["*"],
                ),
                # KMS permissions for Parameter Store
                iam.PolicyStatement(
                    sid="KmsDecryptForParameterStore",
                    effect=iam.Effect.ALLOW,
                    actions=["kms:Decrypt"],
                    resources=[f"arn:aws:kms:{self.region}:{self.account}:key/*"],
                    conditions={"StringEquals": {"kms:ViaService": f"ssm.{self.region}.amazonaws.com"}},
                ),
                # Secrets Manager permissions
                iam.PolicyStatement(
                    sid="SecretsManagerReadOnly",
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "secretsmanager:GetSecretValue",
                        "secretsmanager:DescribeSecret",
                        "secretsmanager:ListSecrets",
                    ],
                    resources=["*"],
                ),
                # KMS permissions for Secrets Manager
                iam.PolicyStatement(
                    sid="KmsDecryptForSecretsManager",
                    effect=iam.Effect.ALLOW,
                    actions=["kms:Decrypt"],
                    resources=[f"arn:aws:kms:{self.region}:{self.account}:key/*"],
                    conditions={"StringEquals": {"kms:ViaService": f"secretsmanager.{self.region}.amazonaws.com"}},
                ),
                # CloudWatch Logs Insights and Transaction Search permissions
                iam.PolicyStatement(
                    sid="CloudWatchLogsInsightsAccess",
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "logs:StartQuery",
                        "logs:GetQueryResults",
                        "logs:StopQuery",
                        "logs:FilterLogEvents",
                        "logs:GetLogEvents",
                        "logs:DescribeLogGroups",
                        "logs:DescribeLogStreams",
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents",
                    ],
                    resources=[
                        f"arn:aws:logs:{self.region}:{self.account}:log-group:/aws/bedrock-agentcore/runtimes/*",
                        f"arn:aws:logs:{self.region}:{self.account}:log-group:aws/spans:*",
                        f"arn:aws:logs:{self.region}:{self.account}:log-group:/aws/application-signals/data:*",
                    ],
                ),
                # Additional CloudWatch permissions for observability
                iam.PolicyStatement(
                    sid="CloudWatchObservabilityAccess",
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "logs:DescribeLogGroups",
                        "logs:DescribeLogStreams",
                        "cloudwatch:GetMetricStatistics",
                        "cloudwatch:ListMetrics",
                        "cloudwatch:GetMetricData",
                    ],
                    resources=["*"],
                ),
                # Bedrock AgentCore Memory permissions
                iam.PolicyStatement(
                    sid="BedrockAgentCoreMemoryAccess",
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "bedrock-agentcore:CreateMemory",
                        "bedrock-agentcore:GetMemory",
                        "bedrock-agentcore:UpdateMemory",
                        "bedrock-agentcore:DeleteMemory",
                        "bedrock-agentcore:ListMemories",
                        "bedrock-agentcore:CreateEvent",
                        "bedrock-agentcore:GetEvent",
                        "bedrock-agentcore:ListEvents",
                        "bedrock-agentcore:RetrieveMemoryRecords",
                    ],
                    resources=["*"],
                ),
            ],
        )

        role.attach_inline_policy(self.agentcore_policy)
        return role

    def _create_ecr_repository(self) -> ecr.Repository:
        """Create ECR repository for AgentCore container images"""

        return ecr.Repository(
            self,
            "AgentCoreECRRepository",
            repository_name=f"bedrock-agentcore-{self.tool_name.value_as_string}",
            image_scan_on_push=True,
            lifecycle_rules=[
                ecr.LifecycleRule(description="Keep only the latest 10 images", max_image_count=10, rule_priority=1)
            ],
            removal_policy=RemovalPolicy.DESTROY,  # For development - change for production
        )

    def _create_log_group(self) -> logs.LogGroup:
        """Create CloudWatch log group for AgentCore"""

        return logs.LogGroup(
            self,
            "AgentCoreLogGroup",
            log_group_name=f"/aws/bedrock-agentcore/runtimes/{self.tool_name.value_as_string}",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY,
        )

    def _create_transaction_search_config(self) -> None:
        """
        Create X-Ray Transaction Search configuration for CloudWatch Logs

        This enables X-Ray Transaction Search feature which allows searching and filtering
        traces in CloudWatch. The configuration includes:
        1. CloudWatch Logs Resource Policy to allow X-Ray to write logs
        2. X-Ray Transaction Search Config with indexing percentage

        Based on AWS documentation:
        https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Transaction-Search-Cloudformation.html
        """

        # Create CloudWatch Logs Resource Policy to allow X-Ray to write logs
        # This policy allows X-Ray service to put log events to specific log groups
        # Note: This is an account-level resource shared by all stacks using X-Ray Transaction Search
        logs_resource_policy = logs.CfnResourcePolicy(
            self,
            "TransactionSearchLogsResourcePolicy",
            policy_name="TransactionSearchAccess",
            policy_document=json.dumps(
                {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Sid": "TransactionSearchXRayAccess",
                            "Effect": "Allow",
                            "Principal": {"Service": "xray.amazonaws.com"},
                            "Action": "logs:PutLogEvents",
                            "Resource": [
                                f"arn:aws:logs:{self.region}:{self.account}:log-group:aws/spans:*",
                                f"arn:aws:logs:{self.region}:{self.account}:log-group:/aws/application-signals/data:*",
                            ],
                            "Condition": {
                                "ArnLike": {"aws:SourceArn": f"arn:aws:xray:{self.region}:{self.account}:*"},
                                "StringEquals": {"aws:SourceAccount": self.account},
                            },
                        }
                    ],
                }
            ),
        )

        # Create X-Ray Transaction Search Config
        # IndexingPercentage controls what percentage of spans are indexed for search
        # Configurable via parameter for cost vs observability balance (can be 0-100)
        transaction_search_config = xray.CfnTransactionSearchConfig(
            self, "XRayTransactionSearchConfig", indexing_percentage=self.xray_indexing_percentage.value_as_number
        )

        # Ensure the resource policy is created before the transaction search config
        transaction_search_config.add_dependency(logs_resource_policy)

        # Note: AWS automatically creates the required log groups when X-Ray Transaction Search is enabled:
        # - aws/spans (for X-Ray spans data)
        # - /aws/application-signals/data (for application signals data)
        # We don't need to create these manually as they are AWS-managed resources

    def _create_ssm_parameters(self) -> None:
        """Create SSM parameters for configuration"""

        # Tool Name parameter - store the tool name for deploy.sh to use
        ssm.StringParameter(
            self,
            "ToolNameParameter",
            parameter_name=f"/{self.toolname_from_config}/runtime/agent_name",
            string_value=self.tool_name.value_as_string,
            description="Tool name for AgentCore deployment",
        )

        # Agent Role name parameter
        ssm.StringParameter(
            self,
            "AgentRoleNameParameter",
            parameter_name=f"/{self.toolname_from_config}/runtime/agent_role_name",
            string_value=self.agentcore_role.role_name,
            description="Agent Role name",
        )

        # ECR Repository name parameter
        ssm.StringParameter(
            self,
            "ECRRepoNameParameter",
            parameter_name=f"/{self.toolname_from_config}/runtime/ecr_repo_name",
            string_value=f"{self.account}.dkr.ecr.{self.region}.amazonaws.com/{self.ecr_repository.repository_name}",
            description="ECR Repository name",
        )

        # X-Ray Transaction Search configuration parameter
        ssm.StringParameter(
            self,
            "XRayTransactionSearchParameter",
            parameter_name=f"/{self.toolname_from_config}/observability/xray_transaction_search_enabled",
            string_value="true",
            description="X-Ray Transaction Search enabled status",
        )

        # X-Ray indexing percentage parameter
        ssm.StringParameter(
            self,
            "XRayIndexingPercentageParameter",
            parameter_name=f"/{self.toolname_from_config}/observability/xray_indexing_percentage",
            string_value=str(self.xray_indexing_percentage.value_as_number),
            description="X-Ray Transaction Search indexing percentage",
        )

    def _create_outputs(self) -> None:
        """Create CloudFormation outputs"""

        # ECR Repository output
        CfnOutput(
            self,
            "ECRRepositoryUri",
            value=self.ecr_repository.repository_uri,
            description="ECR Repository URI",
            export_name=f"{self.stack_name}-ECRRepositoryUri",
        )

        # X-Ray Transaction Search outputs
        CfnOutput(
            self,
            "TransactionSearchEnabled",
            value="true",
            description="X-Ray Transaction Search enabled with CloudWatch Logs integration",
        )

        CfnOutput(
            self,
            "TransactionSearchIndexingPercentage",
            value=str(self.xray_indexing_percentage.value_as_number),
            description="Percentage of traces being indexed for Transaction Search",
        )

        CfnOutput(
            self,
            "XRaySpansLogGroupName",
            value="aws/spans",
            description="CloudWatch Log Group for X-Ray spans data (AWS-managed)",
        )

        CfnOutput(
            self,
            "ApplicationSignalsLogGroupName",
            value="/aws/application-signals/data",
            description="CloudWatch Log Group for Application Signals data (AWS-managed)",
        )

        # AgentCore log group output
        CfnOutput(
            self,
            "AgentCoreLogGroupName",
            value=self.log_group.log_group_name,
            description="CloudWatch Log Group for AgentCore runtime logs",
        )

        # IAM Role output
        CfnOutput(
            self,
            "AgentCoreRoleArn",
            value=self.agentcore_role.role_arn,
            description="IAM Role ARN for AgentCore execution",
        )

        # Output deployment instructions
        CfnOutput(
            self,
            "DeploymentInstructions",
            value=f"Infrastructure created. Tool name '{self.tool_name.value_as_string}' stored in SSM. Run './src/agentcore/deploy.sh src/agentcore/hotel-booking-agent/hotel_booking_agent.py hotel_booking_agent' to complete AgentCore deployment.",
            description="Next steps for AgentCore deployment",
        )

    # ========================================================================
    # CDK NAG SUPPRESSIONS SECTION
    # ========================================================================

    def _apply_cdk_nag_suppressions(self) -> None:
        """
        Apply comprehensive CDK Nag suppressions for the booking agent stack.

        This method applies suppressions for security rules that are either:
        1. Not applicable to this specific use case
        2. Acceptable for development/test environments
        3. Require specific business justification
        """

        # IAM Role suppressions
        NagSuppressions.add_resource_suppressions(
            self.agentcore_role,
            [
                {
                    "id": "AwsSolutions-IAM4",
                    "reason": "AgentCore service requires broad permissions for Bedrock, X-Ray, CloudWatch, and other AWS services. The permissions are scoped to necessary actions and resources where possible. This is the standard pattern for AgentCore execution roles.",
                },
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "Wildcard permissions are required for: 1) X-Ray tracing across all resources, 2) CloudWatch metrics publishing, 3) Bedrock model access across regions, 4) ECR authorization tokens. These are standard patterns for observability and AI services that cannot be further restricted.",
                },
            ],
        )

        # IAM Policy suppressions
        NagSuppressions.add_resource_suppressions(
            self.agentcore_policy,
            [
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "Policy contains necessary wildcard permissions for X-Ray tracing, CloudWatch metrics, and Bedrock model access. These services require broad permissions by design and cannot be further restricted while maintaining functionality.",
                }
            ],
        )

        # ECR Repository suppressions
        NagSuppressions.add_resource_suppressions(
            self.ecr_repository,
            [
                {
                    "id": "AwsSolutions-ECR2",
                    "reason": "ECR repository uses default encryption which is sufficient for AgentCore container images. Customer-managed KMS keys are not required for this use case as the images contain application code, not sensitive data.",
                }
            ],
        )

    def _apply_iam_policy_suppressions(self, resource) -> None:
        """
        Apply CDK Nag suppressions for Secrets Manager resources.

        This method contains suppressions for Secrets Manager best practices
        that may not be applicable for development/test environments.

        Args:
            resource: The Secrets Manager resource (secret or custom resource) to apply suppressions to
        """
        # Note: For custom resources managing secrets, the SMG4 rule may not apply
        # but we include the suppression for completeness
        try:
            NagSuppressions.add_resource_suppressions(
                resource,
                [
                    {
                        "id": "AwsSolutions-SMG4",
                        "reason": "This is a development/test secret for Cognito credentials managed via custom resource. Automatic rotation is not required for this use case as credentials are managed through CDK parameters and can be updated via stack updates. For production deployments, consider implementing automatic rotation.",
                    }
                ],
            )
        except Exception:
            # Custom resources may not support all suppression types
            pass
