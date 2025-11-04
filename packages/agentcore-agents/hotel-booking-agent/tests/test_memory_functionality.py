#!/usr/bin/env python3
"""
Test script to demonstrate hotel booking agent memory functionality
"""

import json
import os
import sys


# Add parent directory to path to import from common and memory modules
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from bedrock_agentcore.memory import MemoryClient  # noqa: E402
from common.aws_config import AWS_REGION  # noqa: E402
from memory.memory_hooks import MEMORY_NAME  # noqa: E402


def test_memory_setup():
    """Test memory setup and seeding with sample data"""

    # Configuration
    REGION = AWS_REGION  # Use detected region or fallback
    CUSTOMER_ID = "customer_test_001"

    print("🧠 Testing Hotel Booking Agent Memory Setup")
    print("=" * 50)

    try:
        # Initialize Memory Client
        client = MemoryClient(region_name=REGION)

        # Find existing memory
        memories = client.list_memories()
        memory_id = next((m["id"] for m in memories if m["id"].startswith(MEMORY_NAME)), None)

        if not memory_id:
            print("❌ Memory not found. Please run the agent first to create memory.")
            return

        print(f"✅ Found memory: {memory_id}")

        # Seed with sample customer interactions
        sample_interactions = [
            ("I'm looking for a luxury hotel in Paris for my honeymoon next month.", "USER"),
            (
                "Congratulations on your upcoming honeymoon! I'd be happy to help you find the perfect luxury hotel in Paris. Let me search for some romantic options with excellent amenities.",
                "ASSISTANT",
            ),
            (
                "I prefer hotels with spa services and prefer rooms with city views. Budget is around $500-800 per night.",
                "USER",
            ),
            (
                "Perfect! I'll focus on luxury hotels with spa services and city view rooms in your budget range. Let me find some excellent options for you.",
                "ASSISTANT",
            ),
            ("I also have a preference for boutique hotels over large chains.", "USER"),
            (
                "Noted! Boutique hotels often provide more personalized service and unique character, which is perfect for a honeymoon. I'll prioritize boutique luxury properties.",
                "ASSISTANT",
            ),
        ]

        # Save sample interactions
        client.create_event(
            memory_id=memory_id, actor_id=CUSTOMER_ID, session_id="sample_session_001", messages=sample_interactions
        )
        print("✅ Seeded sample customer interactions")

        # Test memory retrieval
        print("\n📚 Testing Memory Retrieval:")
        print("-" * 30)

        # Get memory strategies
        strategies = client.get_memory_strategies(memory_id)
        namespaces = {i["type"]: i["namespaces"][0] for i in strategies}

        for context_type, namespace_template in namespaces.items():
            namespace = namespace_template.replace("{actorId}", CUSTOMER_ID)

            memories = client.retrieve_memories(
                memory_id=memory_id, namespace=namespace, query="hotel preferences and requirements", top_k=3
            )

            print(f"\n{context_type.upper()} ({len(memories)} items):")
            for i, memory in enumerate(memories, 1):
                if isinstance(memory, dict):
                    content = memory.get("content", {})
                    if isinstance(content, dict):
                        text = content.get("text", "")[:100] + "..."
                        print(f"  {i}. {text}")

        print("\n" + "=" * 50)
        print("✅ Memory functionality test completed!")
        print(f"Customer ID for testing: {CUSTOMER_ID}")
        print("You can now test the agent with this customer ID to see memory in action.")

    except Exception as e:
        print(f"❌ Error testing memory: {e}")
        import traceback

        traceback.print_exc()


def test_agent_payload():
    """Generate sample payloads for testing the agent"""

    print("\n🧪 Sample Test Payloads:")
    print("=" * 30)

    payloads = [
        {
            "prompt": "I'm looking for hotels in Paris again. Do you remember my preferences?",
            "customer_id": "customer_test_001",
        },
        {
            "prompt": "Can you recommend some boutique hotels in Rome with spa services?",
            "customer_id": "customer_test_001",
        },
        {
            "prompt": "I need a hotel in Tokyo for business travel. Something different from my usual preferences.",
            "customer_id": "customer_test_001",
        },
    ]

    for i, payload in enumerate(payloads, 1):
        print(f"\nTest Payload {i}:")
        print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    test_memory_setup()
    test_agent_payload()
