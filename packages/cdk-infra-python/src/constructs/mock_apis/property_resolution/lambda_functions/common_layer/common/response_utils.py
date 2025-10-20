import json
from datetime import datetime
from typing import Any


def build_response(status_code: int, body: Any) -> dict[str, Any]:
    """
    Build a standardized API Gateway response.

    Args:
        status_code: HTTP status code
        body: Response body object that will be JSON serialized

    Returns:
        API Gateway response dictionary
    """
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key",
            "Access-Control-Allow-Methods": "OPTIONS,POST,GET",
        },
        "body": json.dumps(body),
    }


def build_error_response(
    status_code: int,
    error_code: str,  # noqa: ARG001
    error_message: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build a standardized error response.

    Args:
        status_code: HTTP status code
        error_code: Error code string
        error_message: Human readable error message
        details: Optional dictionary with additional error details

    Returns:
        API Gateway response dictionary
    """
    error_body = {"statusCode": status_code, "message": error_message}

    if details:
        error_body["details"] = details

    return build_response(status_code, error_body)


def build_property_results_response(properties: list[dict[str, Any]], status_code: int = 200) -> dict[str, Any]:
    """
    Build a standardized response for property resolution results.

    Args:
        properties: List of property dictionaries with rank
        status_code: HTTP status code (default 200)

    Returns:
        API Gateway response dictionary with result array
    """
    # Sort properties by rank if provided
    sorted_properties = sorted(properties, key=lambda p: p.get("rank", 999))

    response_body = {"statusCode": status_code, "result": sorted_properties}

    return build_response(status_code, response_body)


def build_no_results_response() -> dict[str, Any]:
    """
    Build a standardized response for when no properties match the query.

    Returns:
        API Gateway response dictionary
    """
    return build_error_response(
        status_code=404,
        error_code="NoMatchingProperties",
        error_message="No properties found matching the query",
        details={"timestamp": datetime.utcnow().isoformat()},
    )


def validate_request(event: dict[str, Any]) -> dict[str, Any] | None:
    """
    Validate the request and return an error response if invalid.

    Args:
        event: API Gateway event

    Returns:
        Error response if invalid, None if valid
    """
    # Check if body exists
    if not event.get("body"):
        return build_error_response(400, "InvalidRequest", "Request body is required")

    # Parse body as JSON
    try:
        request_body = json.loads(event["body"]) if isinstance(event["body"], str) else event["body"]
    except json.JSONDecodeError:
        return build_error_response(400, "InvalidJSON", "Request body is not valid JSON")

    # Check for unique_client_id
    if not request_body.get("unique_client_id"):
        return build_error_response(400, "InvalidRequest", "unique_client_id is required")

    # Check for valid client ID
    valid_client_ids = ["AWS_PACE_Agent", "CXOne"]
    if request_body.get("unique_client_id") not in valid_client_ids:
        return build_error_response(
            400, "InvalidClientId", f"unique_client_id must be one of: {', '.join(valid_client_ids)}"
        )

    # Check for input and query
    if not request_body.get("input") or not request_body.get("input", {}).get("query"):
        return build_error_response(400, "InvalidRequest", "input.query is required")

    # If all validations pass, return None to indicate no errors
    return None
