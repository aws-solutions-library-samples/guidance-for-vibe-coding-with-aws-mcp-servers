"""
AWS configuration utilities for hotel booking agent.

This module provides centralized AWS configuration management to avoid
duplicate boto3 session creation and region detection.
"""

import logging
import os
from boto3.session import Session


logger = logging.getLogger(__name__)


class AWSConfig:
    """
    Simple AWS configuration manager that uses a shared logger instance.
    """

    def __init__(self, logger=None):
        """
        Initialize AWS configuration with optional logger.

        Args:
            logger: Logger instance to use for logging.
        """
        self.logger = logger
        self._region = None
        self._session = None
        self._account_id = None

    def get_region(self) -> str:
        """Get AWS region from environment or session."""
        if self._region:
            return self._region

        # Try environment variable first
        region = os.environ.get("AWS_DEFAULT_REGION")

        if not region:
            # Fall back to boto3 session
            try:
                session = self.get_session()
                region = session.region_name
            except Exception as e:
                self.logger.warning(f"Failed to get region from boto3 session: {e}", "ERROR")

        if not region:
            raise ValueError("Unable to determine AWS region from environment or session")

        self._region = region
        self.logger.info(f"AWS region: {region}")
        return region

    def get_session(self) -> Session:
        """Get or create a boto3 session."""
        if not self._session:
            self._session = Session()
        return self._session

    def get_account_id(self) -> str | None:
        """Get the AWS account ID."""
        if self._account_id:
            return self._account_id

        try:
            session = self.get_session()
            region = self.get_region()
            sts_client = session.client("sts", region_name=region)
            identity = sts_client.get_caller_identity()
            self._account_id = identity.get("Account")
            self.logger.info(f"AWS account ID: {self._account_id}")
            return self._account_id
        except Exception as e:
            self.logger.warning(f"Failed to get AWS account ID: {e}", "ERROR")
            return None
