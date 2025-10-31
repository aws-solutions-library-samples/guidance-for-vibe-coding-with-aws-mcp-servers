"""
Mock APIs Stack for AgentCore Vibe Coding Workshop

This stack contains three mock API services:
1. Property Resolution Service - Hotel search and discovery
2. Reservation Services - Booking management with full CRUD operations
3. Toxicity Detection Service - Content moderation and safety analysis

Each service can be enabled/disabled via CDK context parameters:
- deploy_property_resolution: Enable Property Resolution API (default: true)
- deploy_reservation_services: Enable Reservation Services API (default: true)
- deploy_toxicity_detection: Enable Toxicity Detection API (default: true)
- deploy_all_mock_apis: Enable all APIs (default: true)

Example usage:
  cdk deploy --context deploy_all_mock_apis=true
  cdk deploy --context deploy_property_resolution=true --context deploy_reservation_services=false
"""

from ..constructs.mock_apis.property_resolution.construct import PropertyResolutionConstruct
from ..constructs.mock_apis.reservation_services.construct import ReservationServicesConstruct
from ..constructs.mock_apis.toxicity_detection.construct import ToxicityDetectionConstruct
from aws_cdk import CfnOutput, Stack, aws_ssm as ssm
from constructs import Construct


class MockApisStack(Stack):
    """
    CDK Stack containing all three mock API services for the AgentCore Vibe Coding.

    This stack provides modular deployment options allowing trainers to deploy
    all APIs or select specific ones based on workshop requirements.
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Get deployment configuration from CDK context
        deploy_all = self.node.try_get_context("deploy_all_mock_apis")
        if deploy_all is None:
            deploy_all = True  # Default to deploying all APIs

        deploy_property_resolution = self.node.try_get_context("deploy_property_resolution")
        if deploy_property_resolution is None:
            deploy_property_resolution = deploy_all

        deploy_reservation_services = self.node.try_get_context("deploy_reservation_services")
        if deploy_reservation_services is None:
            deploy_reservation_services = deploy_all

        deploy_toxicity_detection = self.node.try_get_context("deploy_toxicity_detection")
        if deploy_toxicity_detection is None:
            deploy_toxicity_detection = deploy_all

        # Initialize constructs based on configuration
        self.reservation_services: ReservationServicesConstruct | None = None
        self.property_resolution: PropertyResolutionConstruct | None = None
        self.toxicity_detection: ToxicityDetectionConstruct | None = None

        # Note: Individual Lambda execution roles are created per construct to avoid circular dependencies

        # Deploy Reservation Services first (creates shared Hotels table)
        if deploy_reservation_services:
            self.reservation_services = ReservationServicesConstruct(
                self,
                "ReservationServices",
                api_name="Reservation Services API",
                api_description="Mock API for hotel reservation management with full CRUD operations",
                stage_name="dev",
            )

            # Output Reservation Services API information
            CfnOutput(
                self,
                "ReservationServicesApiUrl",
                value=self.reservation_services.api_url,
                description="URL of the Reservation Services API",
                export_name=f"{self.stack_name}-ReservationServicesApiUrl",
            )

            CfnOutput(
                self,
                "ReservationServicesApiId",
                value=self.reservation_services.api_id,
                description="API ID of the Reservation Services API",
                export_name=f"{self.stack_name}-ReservationServicesApiId",
            )

            CfnOutput(
                self,
                "ReservationServicesApiKeyId",
                value=self.reservation_services.api_key_id,
                description="API Key ID for Reservation Services API",
                export_name=f"{self.stack_name}-ReservationServicesApiKeyId",
            )

        # Deploy Property Resolution Service (uses shared Hotels table)
        if deploy_property_resolution:
            self.property_resolution = PropertyResolutionConstruct(
                self,
                "PropertyResolution",
                api_name="Property Resolution API",
                api_description="Mock API for hotel search and discovery using natural language queries",
                stage_name="dev",
                # Reference shared Hotels table if Reservation Services is deployed
                shared_hotels_table=self.reservation_services.hotels_table if self.reservation_services else None,
            )

            # Output Property Resolution API information
            CfnOutput(
                self,
                "PropertyResolutionApiUrl",
                value=self.property_resolution.api_url,
                description="URL of the Property Resolution API",
                export_name=f"{self.stack_name}-PropertyResolutionApiUrl",
            )

            CfnOutput(
                self,
                "PropertyResolutionApiId",
                value=self.property_resolution.api_id,
                description="API ID of the Property Resolution API",
                export_name=f"{self.stack_name}-PropertyResolutionApiId",
            )

            CfnOutput(
                self,
                "PropertyResolutionApiKeyId",
                value=self.property_resolution.api_key_id,
                description="API Key ID for the Property Resolution API",
                export_name=f"{self.stack_name}-PropertyResolutionApiKeyId",
            )

        # Deploy Toxicity Detection Service (standalone)
        if deploy_toxicity_detection:
            self.toxicity_detection = ToxicityDetectionConstruct(
                self,
                "ToxicityDetection",
                api_name="Toxicity Detection API",
                api_description="Mock API for content moderation and safety analysis",
                stage_name="dev",
            )

            # Output Toxicity Detection API information
            CfnOutput(
                self,
                "ToxicityDetectionApiUrl",
                value=self.toxicity_detection.api_url,
                description="URL of the Toxicity Detection API",
                export_name=f"{self.stack_name}-ToxicityDetectionApiUrl",
            )

            CfnOutput(
                self,
                "ToxicityDetectionApiId",
                value=self.toxicity_detection.api_id,
                description="API ID for the Toxicity Detection API",
                export_name=f"{self.stack_name}-ToxicityDetectionApiId",
            )

            CfnOutput(
                self,
                "ToxicityDetectionApiKeyId",
                value=self.toxicity_detection.api_key_id,
                description="API Key ID for the Toxicity Detection API",
                export_name=f"{self.stack_name}-ToxicityDetectionApiKeyId",
            )

        # Create SSM parameters for MCP server configuration
        self._create_ssm_parameters()

        # Add CDK Nag suppressions for all Lambda function roles
        self._add_lambda_role_suppressions()

        # Output shared resources information
        if self.reservation_services:
            CfnOutput(
                self,
                "SharedHotelsTableName",
                value=self.reservation_services.hotels_table.table_name,
                description="Name of the shared Hotels DynamoDB table",
                export_name=f"{self.stack_name}-SharedHotelsTableName",
            )

        # Output deployment summary
        deployed_apis = []
        if deploy_property_resolution:
            deployed_apis.append("Property Resolution")
        if deploy_reservation_services:
            deployed_apis.append("Reservation Services")
        if deploy_toxicity_detection:
            deployed_apis.append("Toxicity Detection")

        CfnOutput(
            self,
            "DeployedApis",
            value=", ".join(deployed_apis) if deployed_apis else "None",
            description="List of deployed mock APIs in this stack",
        )

    def _create_ssm_parameters(self) -> None:
        """Create SSM parameters for MCP server API configuration."""

        if self.property_resolution:
            ssm.StringParameter(
                self,
                "PropertyResolutionApiUrlParam",
                parameter_name="/hotel_booking_mcp/property_resolution/api_url",
                string_value=self.property_resolution.api_url,
                description="Property Resolution API URL for MCP server",
            )

            # Store the API key ID for now - we'll need to retrieve the actual value separately
            ssm.StringParameter(
                self,
                "PropertyResolutionApiKeyParam",
                parameter_name="/hotel_booking_mcp/property_resolution/api_key",
                string_value=self.property_resolution.api_key_id,
                description="Property Resolution API Key ID for MCP server (needs to be resolved to actual key)",
            )

        if self.reservation_services:
            ssm.StringParameter(
                self,
                "ReservationServicesApiUrlParam",
                parameter_name="/hotel_booking_mcp/reservation_services/api_url",
                string_value=self.reservation_services.api_url,
                description="Reservation Services API URL for MCP server",
            )

            # Store the API key ID for now - we'll need to retrieve the actual value separately
            ssm.StringParameter(
                self,
                "ReservationServicesApiKeyParam",
                parameter_name="/hotel_booking_mcp/reservation_services/api_key",
                string_value=self.reservation_services.api_key_id,
                description="Reservation Services API Key ID for MCP server (needs to be resolved to actual key)",
            )

        if self.toxicity_detection:
            ssm.StringParameter(
                self,
                "ToxicityDetectionApiUrlParam",
                parameter_name="/hotel_booking_mcp/toxicity_detection/api_url",
                string_value=self.toxicity_detection.api_url,
                description="Toxicity Detection API URL for MCP server",
            )

            # Store the API key ID for now - we'll need to retrieve the actual value separately
            ssm.StringParameter(
                self,
                "ToxicityDetectionApiKeyParam",
                parameter_name="/hotel_booking_mcp/toxicity_detection/api_key",
                string_value=self.toxicity_detection.api_key_id,
                description="Toxicity Detection API Key ID for MCP server (needs to be resolved to actual key)",
            )

    def _add_lambda_role_suppressions(self) -> None:
        """Add CDK Nag suppressions for all Lambda function roles and policies."""
        from cdk_nag import NagSuppressions

        # Add stack-level suppressions for all Lambda function roles
        NagSuppressions.add_stack_suppressions(
            self,
            [
                {
                    "id": "AwsSolutions-IAM4",
                    "reason": "Lambda functions require AWSLambdaBasicExecutionRole for CloudWatch Logs access. This is the standard AWS managed policy for Lambda execution.",
                    "appliesTo": [
                        "Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
                    ],
                },
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "Lambda functions require wildcard permissions for DynamoDB table indexes to query Global Secondary Indexes (GSI). This is a standard pattern for DynamoDB GSI access.",
                    "appliesTo": [
                        "Resource::<ReservationServicesHotelsTable49FDA2BD.Arn>/index/*",
                        "Resource::<ReservationServicesReservationsTableAF6E1B6C.Arn>/index/*",
                    ],
                },
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "Lambda functions require invoke permissions with wildcard for custom resource providers and framework functions.",
                    "appliesTo": ["Resource::<ReservationServicesDataSeederFunction78EEA9EB.Arn>:*"],
                },
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "Amazon Location Service requires wildcard permissions for geo-places operations across different place indexes and regions.",
                    "appliesTo": ["Resource::*"],
                },
            ],
        )
