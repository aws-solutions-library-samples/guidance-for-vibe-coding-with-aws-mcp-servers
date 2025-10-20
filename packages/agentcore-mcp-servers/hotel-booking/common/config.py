"""
Configuration management for Hotel Booking MCP Server.

This module handles loading configuration from AWS Parameter Store only.
No fallback to environment variables or .env files.
"""

import boto3
import logging
import os
from botocore.exceptions import ClientError, NoCredentialsError


# Configure logging
logger = logging.getLogger(__name__)


class Config:
    """Configuration class for Hotel Booking MCP Server using Parameter Store."""

    def __init__(self):
        """Initialize configuration from AWS Parameter Store."""
        # Get AWS region from environment or boto3 session
        self.aws_region = self._get_aws_region()

        # Load configuration from Parameter Store
        self._load_from_parameter_store()

        # Validate required configuration
        self._validate_config()

    def _get_aws_region(self) -> str:
        """Get AWS region from environment or boto3 session."""
        # Try environment variable first
        region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")

        if region:
            return region

        # Try boto3 session
        try:
            session = boto3.Session()
            region = session.region_name
            if region:
                return region
        except Exception:
            pass

        # Default fallback
        return "us-west-2"

    def _load_from_parameter_store(self) -> None:
        """Load configuration from AWS Parameter Store."""
        try:
            ssm = boto3.client("ssm", region_name=self.aws_region)

            # Get all parameters for the MCP server
            response = ssm.get_parameters_by_path(Path="/hotel_booking_mcp/", Recursive=True, WithDecryption=True)

            # Initialize all config values
            self.property_resolution_api_url = None
            self.property_resolution_api_key = None
            self.reservation_services_api_url = None
            self.reservation_services_api_key = None
            # Toxicity detection temporarily disabled
            self.toxicity_detection_api_url = None
            self.toxicity_detection_api_key = None
            self.toxicity_detection_enabled = False

            # Map parameters to config attributes
            for param in response["Parameters"]:
                param_name = param["Name"]  # Full parameter name
                param_value = param["Value"]

                if param_name == "/hotel_booking_mcp/property_resolution/api_url":
                    # Add /api/v1 to URL based on Bruno test requirements
                    if not param_value.endswith("/api/v1"):
                        param_value = param_value.rstrip("/") + "/api/v1"
                    self.property_resolution_api_url = param_value
                elif param_name == "/hotel_booking_mcp/property_resolution/api_key":
                    self.property_resolution_api_key = self._resolve_api_key(param_value)
                elif param_name == "/hotel_booking_mcp/reservation_services/api_url":
                    # Add /api/v1 to URL based on Bruno test requirements
                    if not param_value.endswith("/api/v1"):
                        param_value = param_value.rstrip("/") + "/api/v1"
                    self.reservation_services_api_url = param_value
                elif param_name == "/hotel_booking_mcp/reservation_services/api_key":
                    self.reservation_services_api_key = self._resolve_api_key(param_value)
                # elif param_name == '/hotel_booking_mcp/toxicity_detection/api_url':
                #     self.toxicity_detection_api_url = param_value
                # elif param_name == '/hotel_booking_mcp/toxicity_detection/api_key':
                #     self.toxicity_detection_api_key = self._resolve_api_key(param_value)

            logger.info(
                f"Loaded {len(response['Parameters'])} parameters from Parameter Store in region {self.aws_region}"
            )

        except NoCredentialsError as e:
            raise ValueError("AWS credentials not available. Cannot load configuration from Parameter Store.") from e
        except ClientError as e:
            raise ValueError(f"Failed to load configuration from Parameter Store: {e}") from e
        except Exception as e:
            raise ValueError(f"Unexpected error loading configuration: {e}") from e

    def _resolve_api_key(self, api_key_id: str) -> str:
        """Resolve API key ID to actual API key value."""
        if api_key_id == "no-key-required":
            return api_key_id

        try:
            # Use API Gateway client to get the actual API key value
            apigateway = boto3.client("apigateway", region_name=self.aws_region)
            response = apigateway.get_api_key(apiKey=api_key_id, includeValue=True)
            logger.info(f"Successfully resolved API key ID {api_key_id}")
            return response["value"]
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            if error_code == "AccessDeniedException":
                logger.error(
                    f"Access denied resolving API key ID {api_key_id}. Check MCP server IAM permissions for apigateway:GET"
                )
            else:
                logger.error(f"Failed to resolve API key ID {api_key_id}: {e}")
            # Return the ID as fallback - might work if the API expects the ID
            return api_key_id
        except Exception as e:
            logger.error(f"Unexpected error resolving API key ID {api_key_id}: {e}")
            return api_key_id

    def _validate_config(self) -> None:
        """Validate that all required configuration is present."""
        required_configs = [
            ("property_resolution_api_url", self.property_resolution_api_url),
            ("property_resolution_api_key", self.property_resolution_api_key),
            ("reservation_services_api_url", self.reservation_services_api_url),
            ("reservation_services_api_key", self.reservation_services_api_key),
            # Toxicity detection temporarily disabled
            # ('toxicity_detection_api_url', self.toxicity_detection_api_url),
            # ('toxicity_detection_api_key', self.toxicity_detection_api_key),
        ]

        missing_configs = []
        for config_name, config_value in required_configs:
            if not config_value:
                missing_configs.append(config_name)

        if missing_configs:
            raise ValueError(
                f"Missing required Parameter Store configuration: {', '.join(missing_configs)}. "
                f"Please ensure parameters exist at /hotel_booking_mcp/ path in Parameter Store (region: {self.aws_region})."
            )

    def get_property_resolution_config(self) -> dict:
        """Get Property Resolution API configuration."""
        return {
            "base_url": self.property_resolution_api_url,
            "api_key": self.property_resolution_api_key,
            "headers": {"Content-Type": "application/json", "x-api-key": self.property_resolution_api_key},
        }

    def get_reservation_services_config(self) -> dict:
        """Get Reservation Services API configuration."""
        return {
            "base_url": self.reservation_services_api_url,
            "api_key": self.reservation_services_api_key,
            "headers": {"Content-Type": "application/json", "x-api-key": self.reservation_services_api_key},
        }

    def get_toxicity_detection_config(self) -> dict:
        """Get Toxicity Detection API configuration."""
        return {
            "base_url": self.toxicity_detection_api_url,
            "api_key": self.toxicity_detection_api_key,
            "headers": {"Content-Type": "application/json", "x-api-key": self.toxicity_detection_api_key},
        }

    def is_configured(self) -> bool:
        """Check if all required configuration is present."""
        try:
            self._validate_config()
            return True
        except ValueError:
            return False

    def get_missing_config(self) -> list[str]:
        """Get list of missing configuration items."""
        required_configs = [
            ("property_resolution_api_url", self.property_resolution_api_url),
            ("property_resolution_api_key", self.property_resolution_api_key),
            ("reservation_services_api_url", self.reservation_services_api_url),
            ("reservation_services_api_key", self.reservation_services_api_key),
            # Toxicity detection temporarily disabled
            # ('toxicity_detection_api_url', self.toxicity_detection_api_url),
            # ('toxicity_detection_api_key', self.toxicity_detection_api_key),
        ]

        missing_configs = []
        for config_name, config_value in required_configs:
            if not config_value:
                missing_configs.append(config_name)

        return missing_configs


# Global configuration instance
config = Config()
