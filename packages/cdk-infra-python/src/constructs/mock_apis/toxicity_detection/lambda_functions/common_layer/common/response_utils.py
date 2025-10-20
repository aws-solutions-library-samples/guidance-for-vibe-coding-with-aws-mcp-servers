"""
Response utilities for the Toxicity Detection Service.
"""

import json
from typing import Any


def build_response(status_code: int, body: dict[str, Any]) -> dict[str, Any]:
    """
    Build a standard API Gateway response.

    Args:
        status_code: HTTP status code
        body: Response body dictionary

    Returns:
        API Gateway response dictionary
    """
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,X-Api-Key",
            "Access-Control-Allow-Methods": "OPTIONS,POST",
        },
        "body": json.dumps(body),
    }


def build_error_response(status_code: int, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Build an error response.

    Args:
        status_code: HTTP status code
        message: Error message
        details: Optional additional error details

    Returns:
        API Gateway error response
    """
    error_body = {"statusCode": status_code, "message": message}

    if details:
        error_body["details"] = details

    return build_response(status_code, error_body)


def build_toxicity_response(toxicity_scores: dict[str, float]) -> dict[str, Any]:
    """
    Build a successful toxicity detection response.

    Args:
        toxicity_scores: Dictionary with toxicity scores

    Returns:
        API Gateway response with toxicity scores
    """
    return build_response(200, toxicity_scores)


def validate_request(event: dict[str, Any]) -> dict[str, Any] | None:
    """
    Validate the incoming request.

    Args:
        event: API Gateway event

    Returns:
        Error response if validation fails, None otherwise
    """
    # Check for API key
    headers = event.get("headers", {}) or {}
    headers_lower = {k.lower(): v for k, v in headers.items()}
    if not headers_lower.get("x-api-key"):
        return build_error_response(401, "Unauthorized", {"error": "API key is required"})

    # Check for body
    if not event.get("body"):
        return build_error_response(400, "Bad Request", {"error": "Request body is required"})

    # Parse and validate body
    try:
        body = json.loads(event["body"]) if isinstance(event["body"], str) else event["body"]
    except json.JSONDecodeError:
        return build_error_response(400, "Bad Request", {"error": "Invalid JSON in request body"})

    # Check for required 'text' field
    if "text" not in body:
        return build_error_response(400, "Bad Request", {"error": 'Field "text" is required'})

    # Validate text is a string and not empty
    if not isinstance(body["text"], str) or not body["text"].strip():
        return build_error_response(400, "Bad Request", {"error": 'Field "text" must be a non-empty string'})

    # Check text length (max 1KB)
    if len(body["text"].encode("utf-8")) > 1024:
        return build_error_response(400, "Bad Request", {"error": "Text exceeds maximum length of 1024 bytes"})

    # Validate region_name if provided
    if "region_name" in body:
        if body["region_name"] != "NA":
            return build_error_response(
                422, "Unprocessable Entity", {"error": 'Only region "NA" is currently supported'}
            )

    return None
