"""
Toxicity Detection Construct

This construct creates the Toxicity Detection Service mock API which provides:
- Content moderation and safety analysis for user interactions
- Multi-category toxicity analysis (threats, insults, hate speech, obscenity)
- Sentiment analysis and negative emotion detection
- Escalation detection for human intervention

The API supports:
- POST /api/v1/toxicity-detection - Analyze text for toxicity
- API key authentication
- Configurable thresholds for different toxicity categories
"""

import os
from ..api_resource_policy import create_account_restricted_policy
from aws_cdk import Duration, RemovalPolicy, Stack, aws_apigateway as apigateway, aws_iam, aws_logs as logs
from aws_cdk.aws_lambda import Runtime
from aws_cdk.aws_lambda_python_alpha import PythonFunction, PythonLayerVersion
from cdk_nag import NagSuppressions
from constructs import Construct


class ToxicityDetectionConstruct(Construct):
    """
    Construct for the Toxicity Detection Service mock API.

    Creates Lambda function and API Gateway for content moderation
    and toxicity analysis functionality.

    This is a standalone service that doesn't require DynamoDB tables.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        api_name: str = "Toxicity Detection API",
        api_description: str = "Mock API for content moderation and safety analysis",
        stage_name: str = "v1",
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create Lambda function
        self._create_lambda_function()

        # Create API Gateway with API key authentication
        self._create_api_gateway(api_name, api_description, stage_name)

    def _create_lambda_function(self) -> None:
        """Create Lambda function for toxicity detection."""

        # Common layer for shared utilities
        self.common_layer = PythonLayerVersion(
            self,
            "CommonLayer",
            entry=os.path.join(os.path.dirname(__file__), "lambda_functions", "common_layer"),
            description="Common utilities for toxicity detection service",
            layer_version_name="toxicity-detection-common",
            compatible_runtimes=[Runtime.PYTHON_3_13],
        )

        # Toxicity detection Lambda function
        self.toxicity_detection_function = PythonFunction(
            self,
            "ToxicityDetectionFunction",
            runtime=Runtime.PYTHON_3_13,
            entry=os.path.join(os.path.dirname(__file__), "lambda_functions", "toxicity_detection"),
            index="app.py",
            handler="handler",
            layers=[self.common_layer],
            timeout=Duration.seconds(30),
            memory_size=256,
            environment={"LOG_LEVEL": "INFO"},
            # log_retention deprecated - using default log group,
        )

        # Grant Comprehend permissions to the Lambda function
        self.toxicity_detection_function.add_to_role_policy(
            statement=aws_iam.PolicyStatement(
                effect=aws_iam.Effect.ALLOW,
                actions=["comprehend:DetectSentiment", "comprehend:DetectToxicContent"],
                resources=["*"],
            )
        )

    def _create_api_gateway(self, api_name: str, api_description: str, stage_name: str) -> None:
        """Create API Gateway for toxicity detection service with API key authentication."""

        # Create CloudWatch Logs log group with retention
        self.access_log_group = logs.LogGroup(
            self,
            "ApiAccessLogs",
            log_group_name=f"/aws/apigateway/{api_name.replace(' ', '-').lower()}",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # Create resource policy to restrict access to this AWS account
        policy_document = aws_iam.PolicyDocument.from_json(create_account_restricted_policy(Stack.of(self).account))

        # Create REST API
        self.api = apigateway.RestApi(
            self,
            "ToxicityDetectionApi",
            rest_api_name=api_name,
            description=api_description,
            policy=policy_document,
            cloud_watch_role=True,
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=apigateway.Cors.ALL_ORIGINS,
                allow_methods=apigateway.Cors.ALL_METHODS,
                allow_headers=["Content-Type", "X-Amz-Date", "Authorization", "X-Api-Key", "X-Amz-Security-Token"],
            ),
            deploy_options=apigateway.StageOptions(
                stage_name=stage_name,
                throttling_rate_limit=100,
                throttling_burst_limit=200,
                tracing_enabled=True,
                metrics_enabled=True,
                access_log_destination=apigateway.LogGroupLogDestination(self.access_log_group),
                access_log_format=apigateway.AccessLogFormat.clf(),
            ),
        )

        # Suppress CloudWatch role managed policy warning
        NagSuppressions.add_resource_suppressions_by_path(
            Stack.of(self),
            f"{self.api.node.path}/CloudWatchRole/Resource",
            [
                {
                    "id": "AwsSolutions-IAM4",
                    "reason": "API Gateway CloudWatch role uses AWS managed policy AmazonAPIGatewayPushToCloudWatchLogs which is the recommended approach for API Gateway logging.",
                    "appliesTo": [
                        "Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AmazonAPIGatewayPushToCloudWatchLogs"
                    ],
                }
            ],
        )

        # Create basic request validator (validates body exists and is valid JSON)
        self.request_validator = apigateway.RequestValidator(
            self,
            "RequestValidator",
            rest_api=self.api,
            request_validator_name=f"{api_name.replace(' ', '-').lower()}-validator",
            validate_request_body=True,
            validate_request_parameters=False,
        )

        # Create minimal model (just ensures valid JSON object)
        self.request_model = apigateway.Model(
            self,
            "RequestModel",
            rest_api=self.api,
            content_type="application/json",
            model_name=f"{api_name.replace(' ', '').replace('-', '')}Request",
            schema=apigateway.JsonSchema(
                schema=apigateway.JsonSchemaVersion.DRAFT4, type=apigateway.JsonSchemaType.OBJECT
            ),
        )

        # Create API key for authentication
        self.api_key = apigateway.ApiKey(
            self,
            "ToxicityDetectionApiKey",
            api_key_name="toxicity-detection-api-key",
            description="API key for Toxicity Detection Service",
        )

        # Create usage plan with throttling and quota limits
        self.usage_plan = apigateway.UsagePlan(
            self,
            "ToxicityDetectionUsagePlan",
            name="toxicity-detection-usage-plan",
            description="Usage plan for Toxicity Detection API with balanced rate limits for workshop",
            throttle=apigateway.ThrottleSettings(rate_limit=150, burst_limit=300),
            quota=apigateway.QuotaSettings(limit=1500, period=apigateway.Period.DAY),
            api_stages=[apigateway.UsagePlanPerApiStage(api=self.api, stage=self.api.deployment_stage)],
        )

        # Associate API key with usage plan
        self.usage_plan.add_api_key(self.api_key)

        # Create API structure: /api/v1/toxicity-detection
        api_resource = self.api.root.add_resource("api")
        v1_resource = api_resource.add_resource("v1")
        toxicity_detection_resource = v1_resource.add_resource("toxicity-detection")

        # POST /api/v1/toxicity-detection - Analyze text for toxicity (requires API key)
        toxicity_detection_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(self.toxicity_detection_function, proxy=True),
            api_key_required=True,
            request_validator=self.request_validator,
            request_models={"application/json": self.request_model},
        )

        # Store API URL and key for outputs
        self.api_url = self.api.url + "api/v1"
        self.api_id = self.api.rest_api_id
        self.api_key_id = self.api_key.key_id

        # CDK Nag suppressions for workshop environment
        NagSuppressions.add_resource_suppressions(
            self.api,
            [
                {
                    "id": "AwsSolutions-APIG4",
                    "reason": "API uses API key authentication which is sufficient for workshop environment. Cognito not required.",
                },
                {
                    "id": "AwsSolutions-COG4",
                    "reason": "Workshop environment uses API key authentication instead of Cognito User Pools by design.",
                },
                {
                    "id": "AwsSolutions-APIG2",
                    "reason": "Request validation is implemented via RequestValidator and Model attached to POST method. CDK Nag has a known bug (issue #1075) where it cannot detect validators attached to methods. Validation works correctly at runtime.",
                },
                {
                    "id": "AwsSolutions-APIG3",
                    "reason": "AWS WAFv2 not required for workshop environment. Mock APIs for learning purposes with controlled access.",
                },
                {
                    "id": "AwsSolutions-APIG6",
                    "reason": "CloudWatch logging disabled to avoid account-level API Gateway CloudWatch Logs role configuration requirement. Workshop environment prioritizes ease of deployment.",
                },
            ],
            apply_to_children=True,
        )
