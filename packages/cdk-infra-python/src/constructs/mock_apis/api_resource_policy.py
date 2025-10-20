"""
API Gateway Resource Policy Helper

Provides reusable resource policy configurations for API Gateway REST APIs.
"""


def create_account_restricted_policy(account_id: str) -> dict:
    """
    Create a resource policy that restricts API access to a specific AWS account.

    This policy allows all principals to invoke the API, but only if the request
    originates from the specified AWS account. This prevents cross-account access
    even if API keys are compromised.

    Args:
        account_id: AWS account ID to allow access from

    Returns:
        dict: IAM policy document in JSON format
    """
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": "*",
                "Action": "execute-api:Invoke",
                "Resource": "execute-api:/*",
                "Condition": {"StringEquals": {"aws:SourceAccount": account_id}},
            }
        ],
    }
