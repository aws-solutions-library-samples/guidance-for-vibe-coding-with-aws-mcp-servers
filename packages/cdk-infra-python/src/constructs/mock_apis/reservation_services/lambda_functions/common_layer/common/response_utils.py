import json
from datetime import datetime
from decimal import Decimal
from typing import Any


def build_response(status_code: int, body: Any, headers: dict[str, str] | None = None) -> dict[str, Any]:
    """
    Build a standardized API Gateway response.

    Args:
        status_code: HTTP status code
        body: Response body (will be converted to JSON)
        headers: Optional headers to include in the response

    Returns:
        API Gateway compatible response dictionary
    """
    standard_headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",  # For CORS
        "Access-Control-Allow-Headers": "Content-Type,Authorization",
        "Access-Control-Allow-Methods": "GET,POST,PATCH,DELETE,OPTIONS",
    }

    # Merge standard headers with custom headers if provided
    if headers:
        standard_headers.update(headers)

    return {"statusCode": status_code, "headers": standard_headers, "body": json.dumps(body, default=json_serializer)}


def build_error_response(status_code: int, error_code: str, error_message: str) -> dict[str, Any]:
    """
    Build a standardized error response.

    Args:
        status_code: HTTP status code
        error_code: Application-specific error code
        error_message: Human-readable error message

    Returns:
        API Gateway compatible error response
    """
    error_body = {"errorCode": error_code, "errorMessage": error_message, "timeStamp": datetime.utcnow().isoformat()}

    return build_response(status_code, error_body)


def build_success_response(body: Any = None) -> dict[str, Any]:
    """
    Build a standardized success response.

    Args:
        body: Optional response body

    Returns:
        API Gateway compatible success response
    """
    success_body = {"success": True, "timeStamp": datetime.utcnow().isoformat()}

    # Include additional data if provided
    if body is not None:
        if isinstance(body, dict):
            success_body.update(body)
        else:
            success_body["data"] = body

    return build_response(200, success_body)


def json_serializer(obj):
    """
    Custom JSON serializer for objects not serializable by default json code.

    Args:
        obj: Object to serialize

    Returns:
        Serialized object
    """
    if isinstance(obj, datetime):
        return obj.isoformat()

    if isinstance(obj, Decimal):
        # Convert Decimal to float for JSON serialization
        return float(obj)

    # Add more custom serialization as needed

    # Default: raise TypeError
    raise TypeError(f"Type {type(obj)} not serializable")
