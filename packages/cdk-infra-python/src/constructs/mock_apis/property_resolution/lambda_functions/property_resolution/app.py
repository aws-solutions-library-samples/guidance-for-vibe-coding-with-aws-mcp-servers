import json
import traceback
from common.dynamo_client import DynamoDBClient
from common.fuzzy_match import get_ranked_properties
from common.hotel_manager import HotelManager
from common.response_utils import (
    build_error_response,
    build_no_results_response,
    build_property_results_response,
    validate_request,
)
from typing import Any


# Initialize clients
dynamo_client = DynamoDBClient()
hotel_manager = HotelManager()


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:  # noqa: ARG001
    """
    Handler for POST /property-resolution endpoint.

    Takes a natural language query and returns a ranked list of matching hotel properties.
    Uses the shared Hotels table from Reservation Services.

    Args:
        event: API Gateway event
        context: Lambda context

    Returns:
        API Gateway response with ranked property results
    """
    try:
        print(f"Received event: {json.dumps(event)}")

        # Validate API key if required - case insensitive check
        headers = event.get("headers", {}) or {}  # Handle None headers
        headers_lower = {k.lower(): v for k, v in headers.items()}
        if not headers_lower.get("x-api-key"):
            return build_error_response(401, "Unauthorized", "API key is required")

        # Validate request
        validation_error = validate_request(event)
        if validation_error:
            return validation_error

        # Parse request body
        request_body = json.loads(event["body"]) if isinstance(event["body"], str) else event["body"]

        # Extract query
        query = request_body.get("input", {}).get("query", "")

        # Get session context (optional)
        request_body.get("session_context", {})

        print(f"Processing query: {query}")

        # Get hotels from DynamoDB and convert to properties format
        all_properties = dynamo_client.get_all_properties()

        if not all_properties:
            print("No hotels found in database, will rely on Amazon Location Service")

        # Process properties with fuzzy matching (will use Amazon Location Service if needed)
        ranked_properties = get_ranked_properties(query, all_properties)

        if not ranked_properties:
            print("No hotels matched the query")
            return build_no_results_response()

        # Print matching results for debugging
        print(f"Found {len(ranked_properties)} matching hotels")

        # Sanitize properties to handle Decimal serialization and limit to top 5
        sanitized_properties = []
        for property_data in ranked_properties[:5]:  # Limit to top 5
            sanitized_property = dynamo_client.sanitize_response(property_data)
            sanitized_properties.append(sanitized_property)

        print(f"Returning top {len(sanitized_properties)} sanitized properties")

        # Return property results
        return build_property_results_response(sanitized_properties)

    except Exception as e:
        print(f"Error processing request: {str(e)}")
        print(traceback.format_exc())
        return build_error_response(500, "InternalServerError", str(e))
