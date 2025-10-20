"""
Label mapper for converting Amazon Comprehend toxicity and sentiment labels to the required response format.
"""


def map_comprehend_to_response(
    comprehend_labels: dict[str, float], sentiment_scores: dict[str, float]
) -> dict[str, float]:
    """
    Map Amazon Comprehend toxicity and sentiment labels to the required response format.

    Toxicity mapping strategy:
    - toxic: Overall TOXICITY score from Comprehend
    - severe_toxic: Combination of HATE_SPEECH and GRAPHIC scores
    - obscene: Combination of PROFANITY and SEXUAL scores
    - threat: VIOLENCE_OR_THREAT score
    - insult: INSULT score
    - identity_hate: HATE_SPEECH score

    Sentiment mapping strategy:
    - negative_sentiment_score: NEGATIVE score from sentiment analysis

    Args:
        comprehend_labels: Dictionary of toxicity labels from Amazon Comprehend
        sentiment_scores: Dictionary of sentiment scores from Amazon Comprehend

    Returns:
        Dictionary with mapped toxicity and sentiment scores
    """
    # Get toxicity scores with defaults of 0.0
    toxicity = comprehend_labels.get("TOXICITY", 0.0)
    hate_speech = comprehend_labels.get("HATE_SPEECH", 0.0)
    graphic = comprehend_labels.get("GRAPHIC", 0.0)
    profanity = comprehend_labels.get("PROFANITY", 0.0)
    sexual = comprehend_labels.get("SEXUAL", 0.0)
    violence_threat = comprehend_labels.get("VIOLENCE_OR_THREAT", 0.0)
    insult = comprehend_labels.get("INSULT", 0.0)

    # Get sentiment scores with defaults of 0.0
    negative_sentiment = sentiment_scores.get("NEGATIVE", 0.0)

    # Map to required format
    return {
        "toxic": toxicity,
        "severe_toxic": max(hate_speech, graphic),  # Use max of hate speech and graphic
        "obscene": max(profanity, sexual),  # Use max of profanity and sexual
        "threat": violence_threat,
        "insult": insult,
        "identity_hate": hate_speech,
        "negative_sentiment_score": negative_sentiment,
    }
