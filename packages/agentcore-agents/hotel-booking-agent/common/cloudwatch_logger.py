import boto3
import time
import uuid
from datetime import datetime


class CloudWatchLogger:
    """
    A CloudWatch logging utility that creates log groups and streams automatically
    and gracefully handles permission issues by falling back to console logging.
    """

    def __init__(self, log_group_name: str, log_stream_name: str | None = None):
        """
        Initialize CloudWatch logger.

        Args:
            log_group_name: Name of the CloudWatch log group
            log_stream_name: Optional name for the log stream. If not provided,
                           generates a unique name with timestamp and UUID
        """
        self.logs_client = boto3.client("logs")
        self.log_group_name = log_group_name
        self.log_stream_name = (
            log_stream_name
            or f"hotel-booking-agent-{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}-{str(uuid.uuid4())[:8]}"
        )
        self.sequence_token = None
        self.cloudwatch_enabled = False
        self._setup_log_stream()

    def _setup_log_stream(self):
        """Create log group and log stream if they don't exist, with graceful permission handling"""
        try:
            # First, try to check if log group exists (this requires fewer permissions)
            log_group_exists = self._check_log_group_exists()

            if not log_group_exists:
                # Try to create log group if it doesn't exist
                try:
                    self.logs_client.create_log_group(logGroupName=self.log_group_name)
                    print(f"Created log group: {self.log_group_name}")
                except self.logs_client.exceptions.ResourceAlreadyExistsException:
                    print(f"Log group already exists: {self.log_group_name}")
                except Exception as e:
                    if "AccessDenied" in str(e) or "not authorized" in str(e):
                        print(f"No permission to create log group. Falling back to console logging. Error: {e}")
                        self.cloudwatch_enabled = False
                        return
                    else:
                        print(f"Error creating log group: {e}")
                        self.cloudwatch_enabled = False
                        return

            # Check if log stream already exists before creating
            existing_stream = self._check_log_stream_exists()
            if existing_stream:
                print(f"Using existing log stream: {self.log_stream_name}")
                self.sequence_token = existing_stream.get("uploadSequenceToken")
                return

            # Try to create log stream
            try:
                self.logs_client.create_log_stream(logGroupName=self.log_group_name, logStreamName=self.log_stream_name)
                print(f"Created log stream: {self.log_stream_name}")
            except self.logs_client.exceptions.ResourceAlreadyExistsException:
                print(f"Log stream already exists: {self.log_stream_name}")
                # Get the sequence token for existing stream
                self._get_sequence_token()
            except Exception as e:
                if "AccessDenied" in str(e) or "not authorized" in str(e):
                    print(f"No permission to create log stream. Falling back to console logging. Error: {e}")
                    self.cloudwatch_enabled = False
                    return
                else:
                    print(f"Error creating log stream: {e}")
                    self.cloudwatch_enabled = False
                    return

        except Exception as e:
            print(f"Error setting up CloudWatch logging: {e}")
            self.cloudwatch_enabled = False

    def _check_log_group_exists(self):
        """Check if log group exists without creating it"""
        try:
            response = self.logs_client.describe_log_groups(logGroupNamePrefix=self.log_group_name, limit=1)
            return any(lg["logGroupName"] == self.log_group_name for lg in response.get("logGroups", []))
        except Exception as e:
            print(f"Error checking log group existence: {e}")
            return False

    def _check_log_stream_exists(self):
        """Check if log stream exists and return its details"""
        try:
            response = self.logs_client.describe_log_streams(
                logGroupName=self.log_group_name, logStreamNamePrefix=self.log_stream_name, limit=1
            )
            for stream in response.get("logStreams", []):
                if stream["logStreamName"] == self.log_stream_name:
                    return stream
            return None
        except Exception as e:
            print(f"Error checking log stream existence: {e}")
            return None

    def _get_sequence_token(self):
        """Get the sequence token for the log stream"""
        try:
            response = self.logs_client.describe_log_streams(
                logGroupName=self.log_group_name, logStreamNamePrefix=self.log_stream_name
            )
            if response["logStreams"]:
                self.sequence_token = response["logStreams"][0].get("uploadSequenceToken")
        except Exception as e:
            print(f"Error getting sequence token: {e}")
            self.cloudwatch_enabled = False

    def log(self, message: str, level: str = "INFO"):
        """
        Send log message to CloudWatch or fallback to console.

        Args:
            message: The log message to send
            level: Log level (INFO, ERROR, WARN, DEBUG)
        """
        # If CloudWatch is disabled, use console logging
        if not self.cloudwatch_enabled:
            print(f"[{level}] {message}")
            return

        try:
            timestamp = int(time.time() * 1000)
            log_event = {"timestamp": timestamp, "message": f"[{level}] {message}"}

            put_log_events_kwargs = {
                "logGroupName": self.log_group_name,
                "logStreamName": self.log_stream_name,
                "logEvents": [log_event],
            }

            if self.sequence_token:
                put_log_events_kwargs["sequenceToken"] = self.sequence_token

            response = self.logs_client.put_log_events(**put_log_events_kwargs)
            self.sequence_token = response.get("nextSequenceToken")

        except Exception as e:
            print(f"Error sending log to CloudWatch: {e}")
            # Disable CloudWatch logging for future calls and fallback to console
            self.cloudwatch_enabled = False
            print(f"[{level}] {message}")

    def is_enabled(self):
        """Check if CloudWatch logging is enabled"""
        return self.cloudwatch_enabled

    def get_log_stream_info(self):
        """Get information about the current log stream"""
        return {
            "log_group_name": self.log_group_name,
            "log_stream_name": self.log_stream_name,
            "cloudwatch_enabled": self.cloudwatch_enabled,
        }
