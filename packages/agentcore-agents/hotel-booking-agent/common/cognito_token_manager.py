"""
Cognito Token Manager for refreshing bearer tokens using Cognito credentials.
"""

import boto3
import json
import logging
from botocore.exceptions import ClientError


logger = logging.getLogger(__name__)


class CognitoTokenManager:
    """Manages Cognito authentication tokens for AgentCore communication."""

    def __init__(self, secret_name: str = "hotel_booking_agent/cognito/credentials"):
        """
        Initialize the token manager.

        Args:
            secret_name: AWS Secrets Manager secret name containing Cognito credentials
        """
        self.secret_name = secret_name
        self.secrets_client = boto3.client("secretsmanager")
        self._cached_credentials = None

    def _get_cognito_credentials(self) -> dict[str, str]:
        """
        Retrieve Cognito credentials from AWS Secrets Manager.

        Returns:
            Dictionary containing pool_id, client_id, discovery_url, etc.
        """
        try:
            if self._cached_credentials is None:
                logger.info(f"Retrieving Cognito credentials from secret: {self.secret_name}")

                secret_value = self.secrets_client.get_secret_value(SecretId=self.secret_name)
                self._cached_credentials = json.loads(secret_value["SecretString"])

                logger.info("Successfully retrieved Cognito credentials")

            return self._cached_credentials

        except ClientError as e:
            logger.error(f"Failed to retrieve Cognito credentials: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Cognito credentials JSON: {e}")
            raise

    def refresh_bearer_token(self) -> str:
        """
        Refresh the bearer token using Cognito authentication.
        Retrieves username and password from Secrets Manager.

        Returns:
            Fresh bearer token string

        Raises:
            Exception: If token refresh fails
        """
        try:
            credentials = self._get_cognito_credentials()
            client_id = credentials["client_id"]

            # Get username and password from the credentials stored in Secrets Manager
            username = credentials.get("username", "")
            password = credentials.get("password", "")

            logger.info(f"Refreshing bearer token for user: {username}")

            # Initialize Cognito Identity Provider client
            cognito_client = boto3.client("cognito-idp")

            # Authenticate user and get fresh access token
            auth_response = cognito_client.initiate_auth(
                ClientId=client_id,
                AuthFlow="USER_PASSWORD_AUTH",
                AuthParameters={"USERNAME": username, "PASSWORD": password},
            )

            # Extract the access token
            bearer_token = auth_response["AuthenticationResult"]["AccessToken"]

            logger.info("Successfully refreshed bearer token")
            return bearer_token

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))

            logger.error(f"Cognito authentication failed - {error_code}: {error_message}")

            if error_code == "NotAuthorizedException":
                raise Exception("Authentication failed: Invalid username or password") from e
            elif error_code == "UserNotFoundException":
                raise Exception("User not found in Cognito user pool") from e
            elif error_code == "TooManyRequestsException":
                raise Exception("Too many authentication requests. Please try again later.") from e
            else:
                raise Exception(f"Cognito authentication error: {error_message}") from e

        except Exception as e:
            logger.error(f"Unexpected error during token refresh: {e}")
            raise Exception(f"Token refresh failed: {str(e)}") from e

    def get_fresh_token(self) -> str:
        """
        Get a fresh bearer token, refreshing if necessary.
        Retrieves username and password from Secrets Manager.

        Returns:
            Fresh bearer token string
        """
        return self.refresh_bearer_token()

    def get_cognito_info(self) -> dict[str, str]:
        """
        Get Cognito configuration information.

        Returns:
            Dictionary with pool_id, client_id, discovery_url
        """
        credentials = self._get_cognito_credentials()
        return {
            "pool_id": credentials.get("pool_id"),
            "client_id": credentials.get("client_id"),
            "discovery_url": credentials.get("discovery_url"),
        }
