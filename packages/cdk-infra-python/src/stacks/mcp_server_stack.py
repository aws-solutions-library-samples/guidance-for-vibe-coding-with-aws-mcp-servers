"""
Hotel Booking MCP Server Stack

This stack deploys the Hotel Booking MCP Server using Amazon Bedrock AgentCore.
"""

from aws_cdk import (
    CfnOutput,
    CustomResource,
    Duration,
    RemovalPolicy,
    Stack,
    aws_bedrock_agentcore_alpha as agentcore,
    aws_cognito as cognito,
    aws_ecr_assets as ecr_assets,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_logs as logs,
    aws_ssm as ssm,
    custom_resources as cr,
)
from cdk_nag import NagSuppressions
from constructs import Construct
from pathlib import Path


class HotelBookingMCPStack(Stack):
    """
    CDK Stack for Hotel Booking MCP Server using AgentCore Runtime

    This stack creates and deploys the MCP server directly using CDK constructs,
    eliminating the need for manual deployment scripts.
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Get context values
        agentcore_context = self.node.try_get_context("mcp-agentcore") or {}
        cognito_config = self.node.try_get_context("cognito") or {}

        self.tool_name = agentcore_context.get("tool-name", "hotel_booking_mcp")
        test_username = cognito_config.get("testUsername", "testuser")
        test_password = cognito_config.get("testPassword", "MyPassword123!")

        # Create IAM role for AgentCore
        self.agentcore_role = self._create_agentcore_role()

        # Create CloudWatch log group
        self.log_group = self._create_log_group()

        # Create Cognito User Pool for authentication
        self.user_pool, self.user_pool_client, self.test_user = self._create_cognito_user_pool(
            test_username, test_password
        )

        # Create custom resource to update Secrets Manager
        self._create_secret_update_resource(test_username, test_password)

        # Create AgentCore Runtime
        self.runtime = self._create_agentcore_runtime()

        # Create SSM parameters
        self._create_ssm_parameters()

        # Apply CDK Nag suppressions
        self._apply_cdk_nag_suppressions()

        # Create outputs
        self._create_outputs()

    def _create_agentcore_role(self) -> iam.Role:
        """Create IAM role for AgentCore execution"""
        role = iam.Role(
            self,
            "AgentCoreRole",
            role_name=f"{self.region}-agentcore-{self.tool_name}-role",
            assumed_by=iam.ServicePrincipal("bedrock-agentcore.amazonaws.com"),
        )

        self.agentcore_policy = iam.Policy(
            self,
            "AgentCorePolicy",
            policy_name="AgentCorePolicy",
            statements=[
                iam.PolicyStatement(
                    sid="BedrockPermissions",
                    actions=["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
                    resources=["arn:aws:bedrock:*::foundation-model/*", "arn:aws:bedrock:*:*:inference-profile/*"],
                ),
                iam.PolicyStatement(
                    sid="MarketplaceModelAccess",
                    actions=["aws-marketplace:Subscribe", "aws-marketplace:ViewSubscriptions"],
                    resources=["*"],
                ),
                iam.PolicyStatement(
                    sid="ECRImageAccess",
                    actions=["ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer", "ecr:GetAuthorizationToken"],
                    resources=["*"],
                ),
                iam.PolicyStatement(
                    actions=["logs:DescribeLogStreams", "logs:CreateLogGroup"],
                    resources=[
                        f"arn:aws:logs:{self.region}:{self.account}:log-group:/aws/bedrock-agentcore/runtimes/*"
                    ],
                ),
                iam.PolicyStatement(
                    actions=["logs:CreateLogStream", "logs:PutLogEvents"],
                    resources=[
                        f"arn:aws:logs:{self.region}:{self.account}:log-group:/aws/bedrock-agentcore/runtimes/*:log-stream:*"
                    ],
                ),
                iam.PolicyStatement(
                    sid="XRayTracingPermissions",
                    actions=[
                        "xray:PutTraceSegments",
                        "xray:PutTelemetryRecords",
                        "xray:GetSamplingRules",
                        "xray:GetSamplingTargets",
                    ],
                    resources=["*"],
                ),
                iam.PolicyStatement(
                    actions=["cloudwatch:PutMetricData"],
                    resources=["*"],
                    conditions={"StringEquals": {"cloudwatch:namespace": "bedrock-agentcore"}},
                ),
                iam.PolicyStatement(
                    sid="GetAgentAccessToken",
                    actions=[
                        "bedrock-agentcore:GetWorkloadAccessToken",
                        "bedrock-agentcore:GetWorkloadAccessTokenForJWT",
                        "bedrock-agentcore:GetWorkloadAccessTokenForUserId",
                    ],
                    resources=[
                        f"arn:aws:bedrock-agentcore:{self.region}:{self.account}:workload-identity-directory/default*",
                        f"arn:aws:bedrock-agentcore:{self.region}:{self.account}:workload-identity-directory/default/workload-identity/{self.tool_name}-*",
                    ],
                ),
                iam.PolicyStatement(
                    sid="ParameterStoreReadOnly",
                    actions=[
                        "ssm:GetParameter",
                        "ssm:GetParameters",
                        "ssm:GetParametersByPath",
                        "ssm:DescribeParameters",
                    ],
                    resources=["*"],
                ),
                iam.PolicyStatement(
                    sid="SecretsManagerReadOnly",
                    actions=["secretsmanager:GetSecretValue", "secretsmanager:DescribeSecret"],
                    resources=["*"],
                ),
                iam.PolicyStatement(
                    sid="ApiGatewayReadOnly",
                    actions=["apigateway:GET"],
                    resources=[f"arn:aws:apigateway:{self.region}::/apikeys/*"],
                ),
            ],
        )

        role.attach_inline_policy(self.agentcore_policy)
        return role

    def _create_log_group(self) -> logs.LogGroup:
        """Create CloudWatch log group for AgentCore"""
        return logs.LogGroup(
            self,
            "AgentCoreLogGroup",
            log_group_name=f"/aws/bedrock-agentcore/runtimes/{self.tool_name}",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY,
        )

    def _create_cognito_user_pool(
        self, username: str, password: str
    ) -> tuple[cognito.UserPool, cognito.UserPoolClient, cognito.CfnUserPoolUser]:
        """Create Cognito User Pool for authentication"""
        user_pool = cognito.UserPool(
            self,
            "AgentCoreUserPool",
            user_pool_name=f"{self.tool_name}.Pool",
            password_policy=cognito.PasswordPolicy(min_length=8),
            removal_policy=RemovalPolicy.DESTROY,
        )

        user_pool_client = user_pool.add_client(
            "AgentCoreClient", auth_flows=cognito.AuthFlow(user_password=True), generate_secret=False
        )

        # Create test user
        test_user = cognito.CfnUserPoolUser(
            self,
            "TestUser",
            user_pool_id=user_pool.user_pool_id,
            username=username,
            user_attributes=[{"name": "email", "value": "test@example.com"}],
        )

        return user_pool, user_pool_client, test_user

    def _create_secret_update_resource(self, username: str, password: str) -> None:
        """Create custom resource to update Secrets Manager with Cognito credentials"""
        # IAM role for Lambda function
        update_secret_role = iam.Role(
            self,
            "UpdateSecretRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ],
            inline_policies={
                "SecretsAndCognitoAccess": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=[
                                "secretsmanager:UpdateSecret",
                                "secretsmanager:CreateSecret",
                                "secretsmanager:DescribeSecret",
                            ],
                            resources=[
                                f"arn:aws:secretsmanager:{self.region}:{self.account}:secret:{self.tool_name}/cognito/credentials-*"
                            ],
                        ),
                        iam.PolicyStatement(
                            actions=["cognito-idp:AdminSetUserPassword"], resources=[self.user_pool.user_pool_arn]
                        ),
                    ]
                )
            },
        )

        # Lambda function for custom resource
        update_secret_function = lambda_.Function(
            self,
            "UpdateSecretFunction",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="index.handler",
            code=lambda_.Code.from_inline("""
import boto3
import json

cognito = boto3.client('cognito-idp')
secrets = boto3.client('secretsmanager')

def handler(event, context):
    if event['RequestType'] in ['Create', 'Update']:
        user_pool_id = event['ResourceProperties']['UserPoolId']
        username = event['ResourceProperties']['Username']
        password = event['ResourceProperties']['Password']
        client_id = event['ResourceProperties']['ClientId']
        discovery_url = event['ResourceProperties']['DiscoveryUrl']
        secret_name = event['ResourceProperties']['SecretName']

        # Set password
        cognito.admin_set_user_password(
            UserPoolId=user_pool_id,
            Username=username,
            Password=password,
            Permanent=True
        )

        # Update secret
        secret_value = {
            'user_pool_id': user_pool_id,
            'client_id': client_id,
            'username': username,
            'password': password,
            'discovery_url': discovery_url
        }

        try:
            secrets.update_secret(
                SecretId=secret_name,
                SecretString=json.dumps(secret_value)
            )
        except secrets.exceptions.ResourceNotFoundException:
            secrets.create_secret(
                Name=secret_name,
                SecretString=json.dumps(secret_value),
                Description=f'Cognito credentials for {secret_name.split("/")[0]}'
            )

        return {'PhysicalResourceId': f'{user_pool_id}-secret'}

    return {'PhysicalResourceId': event.get('PhysicalResourceId', 'default')}
"""),
            role=update_secret_role,
            timeout=Duration.minutes(2),
        )

        # Custom resource provider
        update_secret_provider = cr.Provider(self, "UpdateSecretProvider", on_event_handler=update_secret_function)

        # Custom resource
        update_secret_resource = CustomResource(
            self,
            "UpdateSecretResource",
            service_token=update_secret_provider.service_token,
            properties={
                "UserPoolId": self.user_pool.user_pool_id,
                "Username": username,
                "Password": password,
                "ClientId": self.user_pool_client.user_pool_client_id,
                "DiscoveryUrl": f"https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool.user_pool_id}/.well-known/openid-configuration",
                "SecretName": f"{self.tool_name}/cognito/credentials",
            },
        )

        # Add dependencies
        update_secret_resource.node.add_dependency(self.test_user)
        update_secret_resource.node.add_dependency(self.user_pool_client)

        # Store references for suppressions
        self.update_secret_role = update_secret_role
        self.update_secret_function = update_secret_function
        self.update_secret_provider = update_secret_provider

    def _create_agentcore_runtime(self) -> agentcore.Runtime:
        """Create AgentCore Runtime from local asset"""
        # Get path to MCP server directory
        mcp_server_path = Path(__file__).parent.parent.parent.parent / "agentcore-mcp-servers" / "hotel-booking"

        agent_runtime_artifact = agentcore.AgentRuntimeArtifact.from_asset(
            str(mcp_server_path), platform=ecr_assets.Platform.LINUX_ARM64
        )

        # Create runtime
        runtime = agentcore.Runtime(
            self,
            "HotelBookingMCPRuntime",
            runtime_name=self.tool_name,
            agent_runtime_artifact=agent_runtime_artifact,
            execution_role=self.agentcore_role,
            protocol_configuration=agentcore.ProtocolType.MCP,
            authorizer_configuration=agentcore.RuntimeAuthorizerConfiguration.using_jwt(
                f"https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool.user_pool_id}/.well-known/openid-configuration",
                [self.user_pool_client.user_pool_client_id],
            ),
            environment_variables={"AWS_REGION": self.region, "AWS_DEFAULT_REGION": self.region},
        )

        # Ensure IAM policy is attached before runtime is created
        runtime.node.add_dependency(self.agentcore_policy)

        return runtime

    def _create_ssm_parameters(self) -> None:
        """Create SSM parameters for configuration"""
        ssm.StringParameter(
            self,
            "ToolNameParameter",
            parameter_name=f"/{self.tool_name}/runtime/agent_name",
            string_value=self.tool_name,
        )

        ssm.StringParameter(
            self,
            "AgentRoleNameParameter",
            parameter_name=f"/{self.tool_name}/runtime/agent_role_name",
            string_value=self.agentcore_role.role_name,
        )

        ssm.StringParameter(
            self,
            "UserPoolIdParameter",
            parameter_name=f"/{self.tool_name}/runtime/user_pool_id",
            string_value=self.user_pool.user_pool_id,
        )

        ssm.StringParameter(
            self,
            "ClientIdParameter",
            parameter_name=f"/{self.tool_name}/runtime/client_id",
            string_value=self.user_pool_client.user_pool_client_id,
        )

        ssm.StringParameter(
            self,
            "DiscoveryUrlParameter",
            parameter_name=f"/{self.tool_name}/runtime/discovery_url",
            string_value=f"https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool.user_pool_id}/.well-known/openid-configuration",
        )

        ssm.StringParameter(
            self,
            "AgentArnParameter",
            parameter_name=f"/{self.tool_name}/runtime/agent_arn",
            string_value=self.runtime.agent_runtime_arn,
        )

        ssm.StringParameter(
            self,
            "AgentIdParameter",
            parameter_name=f"/{self.tool_name}/runtime/agent_id",
            string_value=self.runtime.agent_runtime_id,
        )

    def _create_outputs(self) -> None:
        """Create CloudFormation outputs"""
        CfnOutput(
            self,
            "AgentCoreRoleArn",
            value=self.agentcore_role.role_arn,
            description="IAM Role ARN for AgentCore execution",
        )

        CfnOutput(self, "RuntimeArn", value=self.runtime.agent_runtime_arn, description="AgentCore Runtime ARN")

        CfnOutput(self, "RuntimeId", value=self.runtime.agent_runtime_id, description="AgentCore Runtime ID")

        CfnOutput(self, "UserPoolId", value=self.user_pool.user_pool_id, description="Cognito User Pool ID")

        CfnOutput(self, "ClientId", value=self.user_pool_client.user_pool_client_id, description="Cognito Client ID")

        CfnOutput(
            self,
            "DeploymentInstructions",
            value=f"Hotel Booking MCP Server deployed successfully. Runtime: {self.tool_name}",
            description="Deployment complete",
        )

    def _apply_cdk_nag_suppressions(self) -> None:
        """Apply CDK Nag suppressions for security rules"""
        NagSuppressions.add_resource_suppressions(
            self.agentcore_policy,
            [
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "Wildcard permissions required for X-Ray tracing, CloudWatch metrics, Bedrock model access, AWS Marketplace model enablement, and ECR authorization.",
                    "appliesTo": [
                        "Resource::*",
                        "Resource::arn:aws:bedrock:*::foundation-model/*",
                        "Resource::arn:aws:bedrock:*:*:inference-profile/*",
                        "Resource::arn:aws:logs:<AWS::Region>:<AWS::AccountId>:log-group:/aws/bedrock-agentcore/runtimes/*",
                        "Resource::arn:aws:logs:<AWS::Region>:<AWS::AccountId>:log-group:/aws/bedrock-agentcore/runtimes/*:log-stream:*",
                        "Resource::arn:aws:bedrock-agentcore:<AWS::Region>:<AWS::AccountId>:workload-identity-directory/default*",
                        "Resource::arn:aws:bedrock-agentcore:<AWS::Region>:<AWS::AccountId>:workload-identity-directory/default/workload-identity/hotel_booking_mcp-*",
                        "Resource::arn:aws:apigateway:<AWS::Region>::/apikeys/*",
                    ],
                }
            ],
        )

        NagSuppressions.add_resource_suppressions(
            self.user_pool,
            [
                {
                    "id": "AwsSolutions-COG1",
                    "reason": "This is a development/test user pool. Password policy is simplified for workshop purposes.",
                },
                {
                    "id": "AwsSolutions-COG2",
                    "reason": "MFA is not required for development/test environments. Enable for production deployments.",
                },
                {
                    "id": "AwsSolutions-COG3",
                    "reason": "Advanced security mode is not required for development/test environments. Enable for production deployments.",
                },
            ],
        )

        # Suppressions for custom resource components
        NagSuppressions.add_resource_suppressions(
            self.update_secret_role,
            [
                {
                    "id": "AwsSolutions-IAM4",
                    "reason": "Lambda basic execution role is required for CloudWatch Logs access.",
                    "appliesTo": [
                        "Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
                    ],
                },
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "Wildcard required for Secrets Manager secret suffix which is auto-generated by AWS.",
                    "appliesTo": [
                        "Resource::arn:aws:secretsmanager:<AWS::Region>:<AWS::AccountId>:secret:hotel_booking_mcp/cognito/credentials-*"
                    ],
                },
            ],
        )

        NagSuppressions.add_resource_suppressions(
            self.update_secret_function,
            [{"id": "AwsSolutions-L1", "reason": "Python 3.12 is the latest stable runtime for Lambda."}],
        )

        # Suppress for the provider's framework Lambda
        NagSuppressions.add_resource_suppressions_by_path(
            self,
            f"/{self.stack_name}/UpdateSecretProvider/framework-onEvent/ServiceRole",
            [
                {
                    "id": "AwsSolutions-IAM4",
                    "reason": "CDK custom resource provider requires managed policy for Lambda execution.",
                    "appliesTo": [
                        "Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
                    ],
                }
            ],
        )

        NagSuppressions.add_resource_suppressions_by_path(
            self,
            f"/{self.stack_name}/UpdateSecretProvider/framework-onEvent/ServiceRole/DefaultPolicy",
            [
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "CDK custom resource provider requires wildcard permissions to invoke the handler function.",
                    "appliesTo": ["Resource::<UpdateSecretFunction83556651.Arn>:*"],
                }
            ],
        )
