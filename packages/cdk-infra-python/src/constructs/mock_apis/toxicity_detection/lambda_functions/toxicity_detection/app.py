"""
Main Lambda handler for the Toxicity Detection Service.
"""

import json
import traceback
from common.comprehend_client import detect_toxicity_and_sentiment_parallel
from common.label_mapper import map_comprehend_to_response
from common.response_utils import build_error_response, build_toxicity_response, validate_request
from common.text_preprocessor import preprocess_text_for_toxicity
from typing import Any


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:  # noqa: ARG001
    """
    Handler for POST /toxicity-detection endpoint.

    Analyzes text content for toxicity using Amazon Comprehend and returns
    toxicity scores for different categories.

    Args:
        event: API Gateway event
        context: Lambda context

    Returns:
        API Gateway response with toxicity scores
    """
    try:
        print(f"Received event: {json.dumps(event)}")

        # Validate request
        validation_error = validate_request(event)
        if validation_error:
            return validation_error

        # Parse request body
        request_body = json.loads(event["body"]) if isinstance(event["body"], str) else event["body"]

        # Extract text
        original_text = request_body.get("text", "").strip()
        region_name = request_body.get("region_name", "NA")

        print(f"Processing text for region: {region_name}, original text length: {len(original_text)}")
        print(f"Original text: '{original_text}'")

        # Preprocess text to filter whitelisted words before toxicity analysis
        processed_text = preprocess_text_for_toxicity(original_text)

        print(f"Processed text: '{processed_text}' (length: {len(processed_text)})")

        # Log filtering results if any changes were made
        if original_text != processed_text:
            print("WHITELIST FILTERING APPLIED:")
            print(f"  BEFORE: '{original_text}'")
            print(f"  AFTER:  '{processed_text}'")
        else:
            print("No whitelist filtering applied - text unchanged")

        # Call Amazon Comprehend to detect both toxicity and sentiment in parallel
        comprehend_labels, sentiment_scores = detect_toxicity_and_sentiment_parallel(processed_text)

        print(f"Comprehend labels: {comprehend_labels}")
        print(f"Sentiment scores: {sentiment_scores}")

        # Map Comprehend labels to our response format
        response_scores = map_comprehend_to_response(comprehend_labels, sentiment_scores)

        print(f"Mapped response scores: {response_scores}")

        # Return successful response
        return build_toxicity_response(response_scores)

    except Exception as e:
        print(f"Error processing request: {str(e)}")
        print(traceback.format_exc())
        return build_error_response(500, "Internal Server Error", {"error": str(e)})
