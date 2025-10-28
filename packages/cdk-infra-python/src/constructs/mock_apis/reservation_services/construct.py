"""
Reservation Services Construct

This construct creates the Reservation Services mock API which provides:
- Full CRUD operations for hotel reservations
- Guest information management
- Shared Hotels DynamoDB table used by other services
- Room types and reservation data management

The API supports:
- GET /api/v1/reservation - Query reservations by status, date ranges, hotel
- POST /api/v1/reservation - Create new reservations with guest and payment info
- PATCH /api/v1/reservation - Update existing reservations
- POST /api/v1/reservation/cancel - Cancel reservations with policies
- GET /api/v1/reservation/hotel/{hotelId}/{id} - Get specific reservation
- OAuth2 authentication
"""

import os
from ..api_resource_policy import create_account_restricted_policy
from aws_cdk import (
    CustomResource,
    Duration,
    RemovalPolicy,
    Stack,
    aws_apigateway as apigateway,
    aws_dynamodb as dynamodb,
    aws_iam,
    aws_logs as logs,
    custom_resources as cr,
)
from aws_cdk.aws_lambda import Runtime
from aws_cdk.aws_lambda_python_alpha import PythonFunction, PythonLayerVersion
from cdk_nag import NagSuppressions
from constructs import Construct


class ReservationServicesConstruct(Construct):
    """
    Construct for the Reservation Services mock API.

    Creates DynamoDB tables, 5 separate Lambda functions (one per API operation),
    and API Gateway for complete reservation management functionality.

    This matches the original TypeScript CDK architecture exactly.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        api_name: str = "Reservation Services API",
        api_description: str = "Mock API for hotel reservation management",
        stage_name: str = "v1",
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create DynamoDB tables
        self._create_tables()

        # Create Lambda functions (5 separate functions)
        self._create_lambda_functions()

        # Create API Gateway with proper routing
        self._create_api_gateway(api_name, api_description, stage_name)

        # Seed tables with initial data
        self._create_data_seeder()

    def _create_tables(self) -> None:
        """Create DynamoDB tables for reservation services."""

        # Hotels table (shared with other services)
        self.hotels_table = dynamodb.Table(
            self,
            "HotelsTable",
            table_name="Hotels",
            partition_key=dynamodb.Attribute(name="Id", type=dynamodb.AttributeType.NUMBER),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            point_in_time_recovery_specification=dynamodb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled=False
            ),  # Disabled for workshop/dev environment
        )

        # Add GSI for looking up hotels by code
        self.hotels_table.add_global_secondary_index(
            index_name="CodeIndex",
            partition_key=dynamodb.Attribute(name="Code", type=dynamodb.AttributeType.STRING),
            projection_type=dynamodb.ProjectionType.ALL,
        )

        # Room Types table
        self.room_types_table = dynamodb.Table(
            self,
            "RoomTypesTable",
            table_name="RoomTypes",
            partition_key=dynamodb.Attribute(name="RoomCode", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            point_in_time_recovery_specification=dynamodb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled=False
            ),
        )

        # Reservations table
        self.reservations_table = dynamodb.Table(
            self,
            "ReservationsTable",
            table_name="Reservations",
            partition_key=dynamodb.Attribute(name="CrsConfirmationNumber", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            point_in_time_recovery_specification=dynamodb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled=False
            ),
        )

        # Add GSI for querying by hotel and status
        self.reservations_table.add_global_secondary_index(
            index_name="HotelId-status-index",
            partition_key=dynamodb.Attribute(name="Hotel.Id", type=dynamodb.AttributeType.NUMBER),
            sort_key=dynamodb.Attribute(name="status", type=dynamodb.AttributeType.STRING),
            projection_type=dynamodb.ProjectionType.ALL,
        )

        # Add GSI for querying by status and check-in date
        self.reservations_table.add_global_secondary_index(
            index_name="status-CheckInDate-index",
            partition_key=dynamodb.Attribute(name="status", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="RoomStay.CheckInDate", type=dynamodb.AttributeType.STRING),
            projection_type=dynamodb.ProjectionType.ALL,
        )

        # Suppress DDB3 warnings for workshop environment - PITR disabled intentionally for cost/simplicity
        for table in [self.hotels_table, self.room_types_table, self.reservations_table]:
            NagSuppressions.add_resource_suppressions(
                table,
                [
                    {
                        "id": "AwsSolutions-DDB3",
                        "reason": "Point-in-time Recovery disabled intentionally for workshop environment to reduce costs and complexity. Mock data can be easily regenerated.",
                    }
                ],
            )

    def _create_lambda_functions(self) -> None:
        """Create 5 separate Lambda functions for reservation services."""

        # Common layer for shared utilities
        self.common_layer = PythonLayerVersion(
            self,
            "CommonLayer",
            entry=os.path.join(os.path.dirname(__file__), "lambda_functions", "common_layer"),
            description="Common utilities for reservation services",
            layer_version_name="reservation-services-common",
            compatible_runtimes=[Runtime.PYTHON_3_13],
        )

        # Environment variables for all Lambda functions
        environment_vars = {
            "HOTELS_TABLE_NAME": self.hotels_table.table_name,
            "ROOM_TYPES_TABLE_NAME": self.room_types_table.table_name,
            "RESERVATIONS_TABLE_NAME": self.reservations_table.table_name,
            "LOG_LEVEL": "INFO",
        }

        # 1. GET /reservation - Query reservations
        self.get_reservations_function = PythonFunction(
            self,
            "GetReservationsFunction",
            runtime=Runtime.PYTHON_3_13,
            entry=os.path.join(os.path.dirname(__file__), "lambda_functions", "get_reservations"),
            index="app.py",
            handler="handler",
            layers=[self.common_layer],
            timeout=Duration.seconds(30),
            memory_size=256,
            environment=environment_vars,
            # log_retention deprecated - using default log group,
        )

        # 2. POST /reservation - Create reservation
        self.create_reservation_function = PythonFunction(
            self,
            "CreateReservationFunction",
            runtime=Runtime.PYTHON_3_13,
            entry=os.path.join(os.path.dirname(__file__), "lambda_functions", "create_reservation"),
            index="app.py",
            handler="handler",
            layers=[self.common_layer],
            timeout=Duration.seconds(30),
            memory_size=256,
            environment=environment_vars,
            # log_retention deprecated - using default log group,
        )

        # 3. PATCH /reservation - Modify reservation
        self.modify_reservation_function = PythonFunction(
            self,
            "ModifyReservationFunction",
            runtime=Runtime.PYTHON_3_13,
            entry=os.path.join(os.path.dirname(__file__), "lambda_functions", "modify_reservation"),
            index="app.py",
            handler="handler",
            layers=[self.common_layer],
            timeout=Duration.seconds(30),
            memory_size=256,
            environment=environment_vars,
            # log_retention deprecated - using default log group,
        )

        # 4. POST /reservation/cancel - Cancel reservation
        self.cancel_reservation_function = PythonFunction(
            self,
            "CancelReservationFunction",
            runtime=Runtime.PYTHON_3_13,
            entry=os.path.join(os.path.dirname(__file__), "lambda_functions", "cancel_reservation"),
            index="app.py",
            handler="handler",
            layers=[self.common_layer],
            timeout=Duration.seconds(30),
            memory_size=256,
            environment=environment_vars,
            # log_retention deprecated - using default log group,
        )

        # 5. GET /reservation/hotel/{hotelId}/{id} - Fetch specific reservation
        self.fetch_reservation_function = PythonFunction(
            self,
            "FetchReservationFunction",
            runtime=Runtime.PYTHON_3_13,
            entry=os.path.join(os.path.dirname(__file__), "lambda_functions", "fetch_reservation"),
            index="app.py",
            handler="handler",
            layers=[self.common_layer],
            timeout=Duration.seconds(30),
            memory_size=256,
            environment=environment_vars,
            # log_retention deprecated - using default log group,
        )

        # 6. GET /reservation/availability - Check room availability
        self.check_room_availability_function = PythonFunction(
            self,
            "CheckRoomAvailabilityFunction",
            runtime=Runtime.PYTHON_3_13,
            entry=os.path.join(os.path.dirname(__file__), "lambda_functions", "check_room_availability"),
            index="lambda_function.py",
            handler="lambda_handler",
            layers=[self.common_layer],
            timeout=Duration.seconds(30),
            memory_size=256,
            environment=environment_vars,
            # log_retention deprecated - using default log group,
        )

        # 7. POST /reservation/payment/validate - Validate payment details
        self.validate_payment_function = PythonFunction(
            self,
            "ValidatePaymentFunction",
            runtime=Runtime.PYTHON_3_13,
            entry=os.path.join(os.path.dirname(__file__), "lambda_functions", "validate_payment"),
            index="lambda_function.py",
            handler="lambda_handler",
            layers=[self.common_layer],
            timeout=Duration.seconds(30),
            memory_size=256,
            environment=environment_vars,
            # log_retention deprecated - using default log group,
        )

        # Grant appropriate DynamoDB permissions to each function
        self._grant_table_permissions()

    def _grant_table_permissions(self) -> None:
        """Grant appropriate DynamoDB permissions to each Lambda function."""

        # All functions need read access to hotels and room types
        functions = [
            self.get_reservations_function,
            self.create_reservation_function,
            self.modify_reservation_function,
            self.cancel_reservation_function,
            self.fetch_reservation_function,
            self.check_room_availability_function,
            self.validate_payment_function,
        ]

        for func in functions:
            self.hotels_table.grant_read_data(func)
            self.room_types_table.grant_read_data(func)

        # Reservations table permissions based on function needs
        self.reservations_table.grant_read_data(self.get_reservations_function)
        self.reservations_table.grant_read_data(self.fetch_reservation_function)
        self.reservations_table.grant_read_write_data(self.create_reservation_function)
        self.reservations_table.grant_read_write_data(self.modify_reservation_function)
        self.reservations_table.grant_read_write_data(self.cancel_reservation_function)
        # Note: check_room_availability_function and validate_payment_function don't need reservations table access

    def _create_api_gateway(self, api_name: str, api_description: str, stage_name: str) -> None:
        """Create API Gateway with access logging enabled."""

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
            "ReservationServicesApi",
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
            "ReservationServicesApiKey",
            api_key_name="reservation-services-api-key",
            description="API key for Reservation Services",
        )

        # Create usage plan with throttling and quota limits
        self.usage_plan = apigateway.UsagePlan(
            self,
            "ReservationServicesUsagePlan",
            name="reservation-services-usage-plan",
            description="Usage plan for Reservation Services API with balanced rate limits for workshop",
            throttle=apigateway.ThrottleSettings(rate_limit=150, burst_limit=300),
            quota=apigateway.QuotaSettings(limit=1500, period=apigateway.Period.DAY),
            api_stages=[apigateway.UsagePlanPerApiStage(api=self.api, stage=self.api.deployment_stage)],
        )

        # Associate API key with usage plan
        self.usage_plan.add_api_key(self.api_key)

        # Create API structure: /api/v1/reservation
        api_resource = self.api.root.add_resource("api")
        v1_resource = api_resource.add_resource("v1")
        reservation_resource = v1_resource.add_resource("reservation")

        # GET /api/v1/reservation - Query reservations
        reservation_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(self.get_reservations_function, proxy=True),
            api_key_required=True,
            authorization_type=apigateway.AuthorizationType.IAM,
        )

        # POST /api/v1/reservation - Create reservation
        reservation_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(self.create_reservation_function, proxy=True),
            api_key_required=True,
            authorization_type=apigateway.AuthorizationType.IAM,
            request_validator=self.request_validator,
            request_models={"application/json": self.request_model},
        )

        # PATCH /api/v1/reservation - Modify reservation
        reservation_resource.add_method(
            "PATCH",
            apigateway.LambdaIntegration(self.modify_reservation_function, proxy=True),
            api_key_required=True,
            authorization_type=apigateway.AuthorizationType.IAM,
            request_validator=self.request_validator,
            request_models={"application/json": self.request_model},
        )

        # POST /api/v1/reservation/cancel - Cancel reservation
        cancel_resource = reservation_resource.add_resource("cancel")
        cancel_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(self.cancel_reservation_function, proxy=True),
            api_key_required=True,
            authorization_type=apigateway.AuthorizationType.IAM,
            request_validator=self.request_validator,
            request_models={"application/json": self.request_model},
        )

        # GET /api/v1/reservation/hotel/{hotelId}/{id} - Get specific reservation
        hotel_resource = reservation_resource.add_resource("hotel")
        hotel_id_resource = hotel_resource.add_resource("{hotelId}")
        reservation_id_resource = hotel_id_resource.add_resource("{id}")
        reservation_id_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(self.fetch_reservation_function, proxy=True),
            api_key_required=True,
            authorization_type=apigateway.AuthorizationType.IAM,
        )

        # GET /api/v1/reservation/availability - Check room availability
        availability_resource = reservation_resource.add_resource("availability")
        availability_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(self.check_room_availability_function, proxy=True),
            api_key_required=True,
            authorization_type=apigateway.AuthorizationType.IAM,
        )

        # POST /api/v1/reservation/payment/validate - Validate payment details
        payment_resource = reservation_resource.add_resource("payment")
        validate_resource = payment_resource.add_resource("validate")
        validate_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(self.validate_payment_function, proxy=True),
            api_key_required=True,
            authorization_type=apigateway.AuthorizationType.IAM,
            request_validator=self.request_validator,
            request_models={"application/json": self.request_model},
        )

        # Store API URL and key for outputs
        self.api_url = self.api.url + "api/v1"
        self.api_id = self.api.rest_api_id
        self.api_key_id = self.api_key.key_id

    def _create_data_seeder(self) -> None:
        """Create Lambda function and custom resource to seed DynamoDB tables with initial data."""

        # Data seeder Lambda function
        self.seeder_function = PythonFunction(
            self,
            "DataSeederFunction",
            runtime=Runtime.PYTHON_3_13,
            entry=os.path.join(os.path.dirname(__file__), "lambda_functions", "data_seeder"),
            index="seed.py",
            handler="handler",
            timeout=Duration.minutes(5),
            memory_size=512,
            environment={
                "HOTELS_TABLE_NAME": self.hotels_table.table_name,
                "ROOM_TYPES_TABLE_NAME": self.room_types_table.table_name,
                "RESERVATIONS_TABLE_NAME": self.reservations_table.table_name,
            },
            # log_retention deprecated - using default log group,
        )

        # Grant permissions to seed all tables
        self.hotels_table.grant_write_data(self.seeder_function)
        self.room_types_table.grant_write_data(self.seeder_function)
        self.reservations_table.grant_write_data(self.seeder_function)

        # Suppress API authorization violations - intentional for workshop learning objectives
        NagSuppressions.add_resource_suppressions(
            self.api,
            [
                {
                    "id": "AwsSolutions-APIG4",
                    "reason": "Reservations API intentionally has no authentication as part of workshop learning objectives. Participants will implement API key authentication during the workshop.",
                },
                {
                    "id": "AwsSolutions-COG4",
                    "reason": "Workshop environment does not use Cognito User Pools by design. Participants will implement API key authentication instead.",
                },
                {
                    "id": "AwsSolutions-APIG2",
                    "reason": "Request validation is implemented via RequestValidator and Model attached to POST/PATCH methods. CDK Nag has a known bug (issue #1075) where it cannot detect validators attached to methods. Validation works correctly at runtime.",
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

        # Create custom resource provider
        seeder_provider = cr.Provider(
            self,
            "DataSeederProvider",
            on_event_handler=self.seeder_function,
            # log_retention deprecated - using default log group
        )

        # Create custom resource to trigger seeding
        CustomResource(
            self,
            "DataSeederResource",
            service_token=seeder_provider.service_token,
            properties={
                "Timestamp": "2025-01-01T00:00:00Z"  # Forces update on stack changes
            },
        )
