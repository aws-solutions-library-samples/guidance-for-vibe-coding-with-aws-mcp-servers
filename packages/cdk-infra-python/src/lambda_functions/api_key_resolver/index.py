"""
API Key Resolver Lambda Function

This Lambda function is used as a Custom Resource to resolve API Gateway API Key IDs
to their actual values and store them in Parameter Store for MCP server configuration.
"""

import boto3
import json
import logging


logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):  # noqa: ARG001
    """
    Custom Resource handler for API Key resolution.

    This function:
    1. Receives API Key IDs from CDK
    2. Calls API Gateway to get actual API Key values
    3. Stores the actual values in Parameter Store as SecureString
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")

        request_type = event["RequestType"]
        properties = event["ResourceProperties"]

        if request_type == "Delete":
            logger.info("Delete request - no action needed")
            return {"PhysicalResourceId": "api-key-resolver"}

        # Get AWS clients
        apigateway = boto3.client("apigateway")
        ssm = boto3.client("ssm")

        resolved_keys = {}

        # Resolve Property Resolution API Key if provided
        if "PropertyResolutionApiKeyId" in properties:
            api_key_id = properties["PropertyResolutionApiKeyId"]
            logger.info("Resolving Property Resolution API Key")

            try:
                response = apigateway.get_api_key(apiKey=api_key_id, includeValue=True)
                api_key_value = response["value"]

                # Store actual API key value in Parameter Store
                ssm.put_parameter(
                    Name="/hotel_booking_mcp/property_resolution/api_key",
                    Value=api_key_value,
                    Type="SecureString",
                    Overwrite=True,
                    Description="Property Resolution API Key actual value for MCP server",
                )

                resolved_keys["PropertyResolution"] = "SUCCESS"
                logger.info("Successfully resolved Property Resolution API Key")

            except Exception:
                logger.error("Failed to resolve Property Resolution API Key")
                resolved_keys["PropertyResolution"] = "ERROR"

        # Resolve Toxicity Detection API Key if provided
        if "ToxicityDetectionApiKeyId" in properties:
            api_key_id = properties["ToxicityDetectionApiKeyId"]
            logger.info("Resolving Toxicity Detection API Key")

            try:
                response = apigateway.get_api_key(apiKey=api_key_id, includeValue=True)
                api_key_value = response["value"]

                # Store actual API key value in Parameter Store
                ssm.put_parameter(
                    Name="/hotel_booking_mcp/toxicity_detection/api_key",
                    Value=api_key_value,
                    Type="SecureString",
                    Overwrite=True,
                    Description="Toxicity Detection API Key actual value for MCP server",
                )

                resolved_keys["ToxicityDetection"] = "SUCCESS"
                logger.info("Successfully resolved Toxicity Detection API Key")

            except Exception:
                logger.error("Failed to resolve Toxicity Detection API Key")
                resolved_keys["ToxicityDetection"] = "ERROR"

        logger.info("API Key resolution completed")

        return {"PhysicalResourceId": "api-key-resolver", "Data": resolved_keys}

    except Exception as e:
        logger.error(f"Unexpected error in API Key resolver: {e}")
        raise e
