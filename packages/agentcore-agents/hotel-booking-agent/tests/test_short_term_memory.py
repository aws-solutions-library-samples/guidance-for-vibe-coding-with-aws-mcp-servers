#!/usr/bin/env python3
"""
Test script to demonstrate short-term memory functionality in hotel booking agent
"""

import os

# Add the parent directory to sys.path to find common modules
import sys


parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

import logging  # noqa: E402
from common.aws_config import AWSConfig  # noqa: E402
from memory.short_term_memory import (  # noqa: E402
    ShortTermMemoryHooks,
    create_hotel_booking_short_term_memory,
    format_conversation_history,
    get_conversation_history,
)


# Configure default logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

aws_config = AWSConfig(logger)
AWS_REGION = aws_config.get_region()


def test_short_term_memory_creation():
    """Test creating short-term memory resource"""
    print("🧠 Testing Short-Term Memory Creation")
    print("=" * 50)

    try:
        memory_id, memory_client = create_hotel_booking_short_term_memory(logger=logger, region=AWS_REGION)
        print("✅ Short-term memory created successfully")
        print(f"   Memory ID: {memory_id}")
        print(f"   Memory Client: {type(memory_client).__name__}")

        return memory_id, memory_client

    except Exception as e:
        print(f"❌ Error creating short-term memory: {e}")
        import traceback

        traceback.print_exc()
        return None, None


def test_conversation_storage(memory_client, memory_id):
    """Test storing and retrieving conversation history"""
    print("\n💬 Testing Conversation Storage and Retrieval")
    print("=" * 50)

    actor_id = "customer_003"
    # session_id = f"test_session_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    session_id = "f97b7d28-3a8d-4c07-8680-c8f991488d7a"

    # Sample conversation messages (for reference - not used in current test)
    # conversation_messages = [
    #     ("I'm looking for a luxury hotel in Paris for my anniversary", "USER"),
    #     (
    #         "I'd be happy to help you find the perfect luxury hotel in Paris for your anniversary! Let me search for some romantic options with excellent amenities.",
    #         "ASSISTANT",
    #     ),
    #     ("I prefer hotels with spa services and a budget around $400-600 per night", "USER"),
    #     (
    #         "Perfect! I'll look for luxury hotels in Paris with spa services in your budget range. Let me find some excellent options for your special celebration.",
    #         "ASSISTANT",
    #     ),
    #     ("Do you have any recommendations in the 7th arrondissement?", "USER"),
    #     (
    #         "The 7th arrondissement is a wonderful choice! It's home to the Eiffel Tower and has some beautiful luxury hotels. Let me find spa hotels in that area within your budget.",
    #         "ASSISTANT",
    #     ),
    # ]

    try:
        # Store conversation messages
        # print(f"Storing conversation for actor: {actor_id}, session: {session_id}")

        # for i, (message, role) in enumerate(conversation_messages):
        #     memory_client.create_event(
        #         memory_id=memory_id, actor_id=actor_id, session_id=session_id, messages=[(message, role)]
        #     )
        #     print(f"  ✅ Stored message {i + 1}: {role} - {message[:50]}...")

        print("\n📖 Retrieving conversation history...")

        # Retrieve conversation history
        conversation_turns = get_conversation_history(
            memory_client=memory_client,
            memory_id=memory_id,
            actor_id=actor_id,
            session_id=session_id,
            k=5,  # Get last 3 turns
        )

        if conversation_turns:
            print(f"✅ Retrieved {len(conversation_turns)} conversation turns")
            formatted_history = format_conversation_history(conversation_turns)
            print("\nFormatted conversation history:")
            print("-" * 30)
            print(formatted_history)
        else:
            print("❌ No conversation history retrieved")

        return actor_id, session_id

    except Exception as e:
        print(f"❌ Error testing conversation storage: {e}")
        import traceback

        traceback.print_exc()
        return None, None


def test_memory_hooks_simulation(memory_client, memory_id, actor_id, session_id):
    """Test memory hooks functionality (simulation)"""
    print("\n🔗 Testing Memory Hooks Simulation")
    print("=" * 50)

    try:
        # Create memory hooks instance
        _hooks = ShortTermMemoryHooks(
            memory_client=memory_client,
            memory_id=memory_id,
            actor_id=actor_id,
            session_id=session_id,
            logger=logger,
            conversation_turns=10,
        )

        print("✅ Memory hooks created successfully")
        print(f"   Actor ID: {actor_id}")
        print(f"   Session ID: {session_id}")
        print("   Conversation turns to load: 3")

        # Simulate what would happen when agent initializes
        print("\n🚀 Simulating agent initialization...")

        # Get conversation history (simulating what the hook would do)
        recent_turns = memory_client.get_last_k_turns(
            memory_id=memory_id, actor_id=actor_id, session_id=session_id, k=10
        )

        if recent_turns:
            print(f"✅ Retrieved {len(recent_turns)} conversation turns")
            formatted_history = format_conversation_history(recent_turns)
            print("\nFormatted conversation history:")
            print("-" * 30)
            print(formatted_history)
        else:
            print("❌ No recent turns found")

    except Exception as e:
        print(f"❌ Error testing memory hooks: {e}")
        import traceback

        traceback.print_exc()


def test_conversation_continuity():
    """Test conversation continuity across sessions"""
    print("\n🔄 Testing Conversation Continuity")
    print("=" * 50)

    print("This test simulates how the hotel booking agent would:")
    print("1. Store conversation history as messages are exchanged")
    print("2. Load recent conversation when a new session starts")
    print("3. Provide context continuity for personalized responses")
    print()
    print("Key benefits:")
    print("✅ Customers don't need to repeat their preferences")
    print("✅ Agent remembers previous booking discussions")
    print("✅ Seamless conversation flow across interactions")
    print("✅ Personalized recommendations based on history")


def main():
    """Main test function"""
    print("🧪 Hotel Booking Agent Short-Term Memory Tests")
    print("=" * 60)
    # print(f"AWS Region: {AWS_REGION}")
    print()

    # Test 1: Create short-term memory
    memory_id, memory_client = test_short_term_memory_creation()
    if not memory_id or not memory_client:
        print("❌ Cannot continue tests without memory")
        return 1

    # Test 2: Store and retrieve conversation
    # actor_id, session_id = test_conversation_storage(memory_client, memory_id)

    session_id = "8b81d737-91a2-4b80-998d-52e1cc76e381"
    actor_id = "customer_004"
    if not actor_id or not session_id:
        print("❌ Cannot continue tests without conversation data")
        return 1

    # Test 3: Test memory hooks simulation
    test_memory_hooks_simulation(memory_client, memory_id, actor_id, session_id)

    # Test 4: Explain conversation continuity
    # test_conversation_continuity()

    print("\n" + "=" * 60)
    print("🎉 All short-term memory tests completed!")
    print()
    print("Next steps:")
    print("1. Deploy the updated hotel booking agent")
    print("2. Test with real conversations")
    print("3. Verify conversation continuity works in production")

    return 0


if __name__ == "__main__":
    exit(main())
