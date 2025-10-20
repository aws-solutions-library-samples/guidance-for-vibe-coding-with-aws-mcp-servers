#!/usr/bin/env python3
"""
Interactive Chat Test for Hotel Booking Agent

This script provides a back-and-forth conversation interface to test
the hotel booking agent's chatbot functionality with memory persistence.
"""

import boto3
import json
import os
import requests
import sys
import uuid
from boto3.session import Session


# Add parent directory to path to import from common and memory modules
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from common.cognito_token_manager import CognitoTokenManager  # noqa: E402


class HotelBookingChatTester:
    def __init__(self):
        self.session = Session()
        self.region = self.session.region_name
        self.conversation_id = str(uuid.uuid4())
        self.customer_id = str(uuid.uuid4())
        self.chat_history = []  # Initialize chat history

        print(f"🌍 Using AWS region: {self.region}")
        print(f"💬 Conversation ID: {self.conversation_id}")
        print(f"💬 Customer ID: {self.customer_id}")

        # Initialize connection
        self._setup_connection()

    def _setup_connection(self):
        """Setup connection to AgentCore service"""
        try:
            # Get agent ARN from parameter store
            ssm_client = boto3.client("ssm", region_name=self.region)
            agent_arn_response = ssm_client.get_parameter(Name="/hotel_booking_agent/runtime/agent_arn")
            self.agent_arn = agent_arn_response["Parameter"]["Value"]
            print(f"🤖 Agent ARN: {self.agent_arn}")

            # Setup URL
            encoded_arn = self.agent_arn.replace(":", "%3A").replace("/", "%2F")
            self.url = f"https://bedrock-agentcore.{self.region}.amazonaws.com/runtimes/{encoded_arn}/invocations"

            # Get authentication token
            token_manager = CognitoTokenManager(secret_name="hotel_booking_agent/cognito/credentials")
            self.bearer_token = token_manager.get_fresh_token()
            print("🔐 Authentication token retrieved")

            # Setup headers
            self.headers = {"authorization": f"Bearer {self.bearer_token}", "Content-Type": "application/json"}

            # self.url="http://0.0.0.0:8080/invocations"
            # self.headers = {"Content-Type": "application/json"}

        except Exception as e:
            print(f"❌ Error setting up connection: {e}")
            sys.exit(1)

    def send_message(self, prompt):
        """Send a message to the agent and get response"""
        try:
            # Prepare payload with conversation history
            payload = json.dumps(
                {"prompt": prompt, "session_id": self.conversation_id, "customer_id": self.customer_id}
            )

            print(f"Sending Payload:{payload}")

            # Send request
            response = requests.post(self.url, headers=self.headers, data=payload)

            if response.status_code == 200:
                response_data = response.json()

                # Parse nested response structure
                if "body" in response_data:
                    body_data = json.loads(response_data["body"])
                    if "message" in body_data and "content" in body_data["message"]:
                        content = body_data["message"]["content"]
                        if isinstance(content, list) and len(content) > 0:
                            agent_response = content[0].get("text", "No text content")
                        else:
                            agent_response = "No content available"
                    else:
                        agent_response = body_data.get("message", "No message in body")
                else:
                    agent_response = response_data.get("response", "No response field")

                # Update chat history
                self.chat_history.append({"user": prompt, "agent": agent_response})

                return agent_response
            else:
                error_msg = f"Error {response.status_code}: {response.text}"
                print(f"❌ {error_msg}")
                return None

        except Exception as e:
            print(f"❌ Error sending message: {e}")
            return None

    def start_conversation(self):
        """Start interactive conversation"""
        print("\n" + "=" * 60)
        print("🏨 HOTEL BOOKING AGENT - INTERACTIVE CHAT TEST")
        print("=" * 60)
        print("Type 'quit' to exit, 'history' to see conversation history")
        print("Type 'clear' to start a new conversation")
        print("-" * 60)

        while True:
            try:
                # Get user input
                user_input = input("\n👤 You: ").strip()

                if not user_input:
                    continue

                # Handle special commands
                if user_input.lower() == "quit":
                    print("\n👋 Goodbye! Thanks for testing the hotel booking agent.")
                    break

                elif user_input.lower() == "history":
                    self._show_history()
                    continue

                elif user_input.lower() == "clear":
                    self._clear_conversation()
                    continue

                # Send message to agent
                print("🤖 Agent: ", end="", flush=True)
                response = self.send_message(user_input)

                if response:
                    print(response)
                else:
                    print("Sorry, I couldn't process your request. Please try again.")

            except KeyboardInterrupt:
                print("\n\n👋 Chat interrupted. Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Unexpected error: {e}")

    def _show_history(self):
        """Show conversation history"""
        if not self.chat_history:
            print("📝 No conversation history yet.")
            return

        print(f"\n📝 Conversation History (ID: {self.conversation_id})")
        print("-" * 50)
        for i, turn in enumerate(self.chat_history, 1):
            print(f"{i}. 👤 You: {turn['user']}")
            print(f"   🤖 Agent: {turn['agent']}")
            print()

    def _clear_conversation(self):
        """Clear conversation and start fresh"""
        self.conversation_id = str(uuid.uuid4())
        self.chat_history = []
        print(f"🔄 Started new conversation (ID: {self.conversation_id})")


def run_sample_conversation():
    """Run a sample conversation for testing"""
    tester = HotelBookingChatTester()

    sample_messages = [
        "Hello! I'm looking for a hotel in New York for next month.",
        "I need a room for 2 guests from July 15th to July 18th, 2025.",
        "What hotels do you have available?",
        "Can you tell me more about the Grand Plaza Hotel?",
        "I'd like to book a deluxe room at the Grand Plaza Hotel.",
        "What's my booking confirmation number?",
    ]

    print("\n🧪 Running sample conversation...")
    print("=" * 60)

    for i, message in enumerate(sample_messages, 1):
        print(f"\n{i}. 👤 User: {message}")
        print("🤖 Agent: ", end="", flush=True)

        response = tester.send_message(message)
        if response:
            print(response)
        else:
            print("Error getting response")

        # Small delay for readability
        import time

        time.sleep(1)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--sample":
        run_sample_conversation()
    else:
        tester = HotelBookingChatTester()
        tester.start_conversation()
