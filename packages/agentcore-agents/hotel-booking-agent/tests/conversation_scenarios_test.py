#!/usr/bin/env python3
"""
Conversation Scenarios Test for Hotel Booking Agent

This script runs predefined conversation scenarios to test various
hotel booking agent capabilities including memory and context handling.
"""

import boto3
import json
import os
import requests
import sys
import time
import uuid
from boto3.session import Session


# Add parent directory to path to import from common and memory modules
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from common.cognito_token_manager import CognitoTokenManager  # noqa: E402


class ConversationScenarioTester:
    def __init__(self):
        self.session = Session()
        self.region = self.session.region_name
        self._setup_connection()

    def _setup_connection(self):
        """Setup connection to AgentCore service"""
        try:
            ssm_client = boto3.client("ssm", region_name=self.region)
            agent_arn_response = ssm_client.get_parameter(Name="/hotel_booking_agent/runtime/agent_arn")
            self.agent_arn = agent_arn_response["Parameter"]["Value"]

            encoded_arn = self.agent_arn.replace(":", "%3A").replace("/", "%2F")
            self.url = f"https://bedrock-agentcore.{self.region}.amazonaws.com/runtimes/{encoded_arn}/invocations"

            token_manager = CognitoTokenManager(secret_name="hotel_booking_agent/cognito/credentials")
            self.bearer_token = token_manager.get_fresh_token()

            self.headers = {"authorization": f"Bearer {self.bearer_token}", "Content-Type": "application/json"}

            self.url = "http://0.0.0.0:8080/invocations"
            self.headers = {"Content-Type": "application/json"}

            print(f"✅ Connected to AgentCore in region: {self.region}")

        except Exception as e:
            print(f"❌ Connection setup failed: {e}")
            sys.exit(1)

    def send_message(self, prompt, conversation_id, chat_history):
        """Send message and return response"""
        try:
            payload = json.dumps(
                {
                    "prompt": prompt,
                    "conversation_id": conversation_id,
                    "chat_history": json.dumps(chat_history) if chat_history else "",
                }
            )

            response = requests.post(self.url, headers=self.headers, data=payload)

            if response.status_code == 200:
                response_data = response.json()

                # Parse nested response structure
                if "body" in response_data:
                    body_data = json.loads(response_data["body"])
                    if "message" in body_data and "content" in body_data["message"]:
                        content = body_data["message"]["content"]
                        if isinstance(content, list) and len(content) > 0:
                            return content[0].get("text", "No text content")
                    return body_data.get("message", "No message in body")

                return response_data.get("response", "No response field")
            else:
                return f"Error {response.status_code}: {response.text}"

        except Exception as e:
            return f"Request failed: {e}"

    def run_scenario(self, scenario_name, messages, delay=2):
        """Run a conversation scenario"""
        print(f"\n{'=' * 60}")
        print(f"🎭 SCENARIO: {scenario_name}")
        print(f"{'=' * 60}")

        conversation_id = str(uuid.uuid4())
        chat_history = []

        for i, message in enumerate(messages, 1):
            print(f"\n{i}. 👤 User: {message}")
            print("   🤖 Agent: ", end="", flush=True)

            response = self.send_message(message, conversation_id, chat_history)
            print(response)

            # Update history
            chat_history.append({"user": message, "agent": response})

            # Delay between messages
            if i < len(messages):
                time.sleep(delay)

        print(f"\n✅ Scenario '{scenario_name}' completed")
        return chat_history


def main():
    tester = ConversationScenarioTester()

    # Scenario 1: Basic Hotel Search and Booking
    scenario1_messages = [
        "Hi! I'm planning a trip to New York City.",
        "I need a hotel for 2 guests from August 15th to August 18th, 2025.",
        "What hotels do you have available for those dates?",
        "Tell me more about the Grand Plaza Hotel.",
        "I'd like to book a deluxe room at the Grand Plaza Hotel.",
        "What's my confirmation number?",
    ]

    # Scenario 2: Memory and Context Testing
    scenario2_messages = [
        "Hello, I'm John Smith and I'm looking for hotels in Miami.",
        "I prefer oceanview rooms and I'm traveling with my family.",
        "Show me available hotels for July 20-25, 2025.",
        "I like the Ocean View Resort. What amenities does it have?",
        "Book an oceanview room for me.",
        "Can you remind me what preferences I mentioned earlier?",
    ]

    # Scenario 3: Error Handling and Clarification
    scenario3_messages = [
        "I want to book a hotel.",
        "Somewhere nice.",
        "For next month.",
        "Actually, I meant Denver, Colorado for 3 nights starting July 10th, 2025.",
        "Show me the Mountain Lodge details.",
        "Book a standard room for 2 guests.",
    ]

    # Scenario 4: Booking Management
    scenario4_messages = [
        "I have a booking confirmation BK20250808160000. Can you find it?",
        "I need to modify my check-out date to one day later.",
        "What's the new total cost?",
        "Actually, I need to cancel this booking.",
        "What's your cancellation policy?",
    ]

    # Run all scenarios
    scenarios = [
        ("Basic Hotel Search and Booking", scenario1_messages),
        ("Memory and Context Testing", scenario2_messages),
        ("Error Handling and Clarification", scenario3_messages),
        ("Booking Management", scenario4_messages),
    ]

    print("🚀 Starting Hotel Booking Agent Conversation Tests")
    print(f"⏰ Test started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    for scenario_name, messages in scenarios:
        try:
            tester.run_scenario(scenario_name, messages)
        except Exception as e:
            print(f"❌ Scenario '{scenario_name}' failed: {e}")

        # Pause between scenarios
        print("\n" + "-" * 40)
        time.sleep(3)

    print(f"\n🏁 All scenarios completed at: {time.strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
