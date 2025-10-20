"""
Amazon Comprehend client wrapper for toxicity and sentiment detection.
"""

import asyncio
import boto3
import os
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache


# Get the AWS region from environment or default to us-west-2
AWS_REGION = os.environ.get("COMPREHEND_REGION", "us-west-2")


@lru_cache(maxsize=1)
def get_comprehend_client():
    """
    Get a cached Amazon Comprehend client.
    Using LRU cache to maintain connection pooling.
    """
    return boto3.client("comprehend", region_name=AWS_REGION)


def detect_toxic_content(text: str) -> dict[str, float]:
    """
    Detect toxic content in the provided text using Amazon Comprehend.

    Args:
        text: The text to analyze

    Returns:
        Dictionary with toxicity labels and scores

    Raises:
        Exception: If the Comprehend API call fails
    """
    client = get_comprehend_client()

    try:
        # Call Amazon Comprehend to detect toxic content
        response = client.detect_toxic_content(TextSegments=[{"Text": text}], LanguageCode="en")

        # Extract the first (and only) result
        if response["ResultList"]:
            result = response["ResultList"][0]

            # Convert labels list to dictionary
            labels_dict = {}
            for label in result.get("Labels", []):
                labels_dict[label["Name"]] = label["Score"]

            # Add the overall toxicity score
            labels_dict["TOXICITY"] = result.get("Toxicity", 0.0)

            return labels_dict
        else:
            # Return zeros if no results
            return {
                "TOXICITY": 0.0,
                "PROFANITY": 0.0,
                "HATE_SPEECH": 0.0,
                "INSULT": 0.0,
                "GRAPHIC": 0.0,
                "HARASSMENT_OR_ABUSE": 0.0,
                "SEXUAL": 0.0,
                "VIOLENCE_OR_THREAT": 0.0,
            }

    except Exception as e:
        print(f"Error calling Comprehend detect_toxic_content: {str(e)}")
        raise


def detect_sentiment(text: str) -> dict[str, float]:
    """
    Detect sentiment in the provided text using Amazon Comprehend.

    Args:
        text: The text to analyze

    Returns:
        Dictionary with sentiment scores

    Raises:
        Exception: If the Comprehend API call fails
    """
    client = get_comprehend_client()

    try:
        # Call Amazon Comprehend to detect sentiment
        response = client.detect_sentiment(Text=text, LanguageCode="en")

        # Extract sentiment scores
        sentiment_scores = response.get("SentimentScore", {})

        return {
            "POSITIVE": sentiment_scores.get("Positive", 0.0),
            "NEGATIVE": sentiment_scores.get("Negative", 0.0),
            "NEUTRAL": sentiment_scores.get("Neutral", 0.0),
            "MIXED": sentiment_scores.get("Mixed", 0.0),
        }

    except Exception as e:
        print(f"Error calling Comprehend detect_sentiment: {str(e)}")
        raise


def detect_toxicity_and_sentiment_parallel(text: str) -> tuple[dict[str, float], dict[str, float]]:
    """
    Detect both toxicity and sentiment in parallel using asyncio.

    Args:
        text: The text to analyze

    Returns:
        Tuple of (toxicity_results, sentiment_results)

    Raises:
        Exception: If either Comprehend API call fails
    """

    async def _detect_parallel():
        loop = asyncio.get_event_loop()

        # Use ThreadPoolExecutor to make synchronous boto3 calls async
        with ThreadPoolExecutor(max_workers=2) as executor:
            # Submit both tasks
            toxicity_task = loop.run_in_executor(executor, detect_toxic_content, text)
            sentiment_task = loop.run_in_executor(executor, detect_sentiment, text)

            # Wait for both to complete
            toxicity_result, sentiment_result = await asyncio.gather(toxicity_task, sentiment_task)

            return toxicity_result, sentiment_result

    # Run the async function
    return asyncio.run(_detect_parallel())
