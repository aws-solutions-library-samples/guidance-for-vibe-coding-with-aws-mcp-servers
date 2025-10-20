"""
Short-term memory implementation for hotel booking agent.

This module provides conversation history continuity using Amazon Bedrock AgentCore Memory
short-term memory capabilities. It stores raw conversation turns that can be retrieved
with get_last_k_turns for seamless conversation continuation.
"""

import logging
import os
from bedrock_agentcore.memory import MemoryClient
from botocore.exceptions import ClientError
from strands.hooks import AgentInitializedEvent, HookProvider, HookRegistry, MessageAddedEvent
from typing import Any


logger = logging.getLogger(__name__)

# Get AWS region from environment
AWS_REGION = os.environ.get("AWS_DEFAULT_REGION")

# Short-term memory configuration
SHORT_TERM_MEMORY_NAME = "HotelBookingShortTermMemory"
SHORT_TERM_MEMORY_EXPIRY_DAYS = 7  # Short retention for conversation history
DEFAULT_CONVERSATION_TURNS = 10  # Number of recent turns to load


class ShortTermMemoryHooks(HookProvider):
    """
    Short-term memory hooks for hotel booking agent.

    Provides conversation history continuity by:
    1. Loading recent conversation turns when agent initializes
    2. Storing new messages as they are added
    """

    def __init__(
        self,
        memory_client: MemoryClient,
        memory_id: str,
        actor_id: str,
        session_id: str,
        logger,
        conversation_turns: int = DEFAULT_CONVERSATION_TURNS,
    ):
        """
        Initialize short-term memory hooks.

        Args:
            memory_client: MemoryClient instance
            memory_id: ID of the memory resource
            actor_id: Unique identifier for the customer/user
            session_id: Unique identifier for the current session
            logger: Logger instance to use
            conversation_turns: Number of recent conversation turns to load (default: 5)
        """
        self.memory_client = memory_client
        self.memory_id = memory_id
        self.actor_id = actor_id
        self.session_id = session_id
        self.conversation_turns = conversation_turns
        self.logger = logger

    def on_agent_initialized(self, event: AgentInitializedEvent):
        """
        Load recent conversation history when agent starts.

        This hook automatically loads the last K conversation turns from memory
        and adds them to the agent's system prompt for context continuity.
        """
        try:
            self.logger.info(f"Loading last {self.conversation_turns} conversation turns for session {self.session_id}")

            # Load recent conversation turns from memory
            recent_turns = self.memory_client.get_last_k_turns(
                memory_id=self.memory_id, actor_id=self.actor_id, session_id=self.session_id, k=self.conversation_turns
            )

            if recent_turns:
                context_messages = []
                for turn in recent_turns:
                    for message in turn:
                        role = message["role"]
                        content = message["content"]["text"]
                        context_messages.append(f"{role}: {content}")

                context = "\n".join(context_messages)
                self.logger.info(f"Context from memory: {context}")

                # Add context to agent's system prompt
                event.agent.system_prompt += f"\n\nRecent conversation history:\n{context}\n\nContinue the conversation naturally based on this context."
                self.logger.info(f"Added context to system prompt: {event.agent.system_prompt}")

                self.logger.info(
                    f"✅ Loaded {len(recent_turns)} conversation turns with {len(context_messages)} messages"
                )
            else:
                self.logger.info("No conversation messages found in recent turns")

        except Exception as e:
            self.logger.warn(f"❌ Error loading conversation history: {e}", "error")
            # Don't fail the agent initialization if memory loading fails

    def on_message_added(self, event: MessageAddedEvent):
        """
        Store new messages in short-term memory.

        This hook automatically saves each new message to memory for future retrieval.
        """
        try:
            messages = event.agent.messages
            if not messages:
                return

            last_message = messages[-1]
            role = last_message.get("role", "unknown")
            content = last_message.get("content", "")

            # Extract text content if it's in a structured format
            if isinstance(content, list) and len(content) > 0:
                if isinstance(content[0], dict) and "text" in content[0]:
                    content_text = content[0]["text"]
                else:
                    content_text = str(content[0])
            elif isinstance(content, dict) and "text" in content:
                content_text = content["text"]
            else:
                content_text = str(content)

            # messages_to_be_stored = [(str(messages[-1].get("content", "")), messages[-1]["role"])]
            # Store the message in memory
            self.memory_client.create_event(
                memory_id=self.memory_id,
                actor_id=self.actor_id,
                session_id=self.session_id,
                messages=[(content_text, role.upper())],
                # messages=messages_to_be_stored
            )

            self.logger.info(f"✅ Stored {role} message {content_text} in short-term memory")

        except Exception as e:
            self.logger.warn(f"❌ Error storing message in memory: {e}", "error")
            # Don't fail the conversation if memory storage fails

    def register_hooks(self, registry: HookRegistry) -> None:
        """
        Register short-term memory hooks with the agent.

        Args:
            registry: HookRegistry to register callbacks with
        """
        registry.add_callback(AgentInitializedEvent, self.on_agent_initialized)
        registry.add_callback(MessageAddedEvent, self.on_message_added)
        self.logger.info("✅ Short-term memory hooks registered")


def create_short_term_memory(
    logger, region: str = None, memory_name: str = None, expiry_days: int = None
) -> tuple[str, MemoryClient]:
    """
    Create or get existing short-term memory resource for hotel booking agent.

    Args:
        region: AWS region (optional, uses global AWS_REGION if not provided)
        memory_name: Name for the memory resource (optional, uses default)
        expiry_days: Days before memories expire (optional, uses default)

    Returns:
        Tuple of (memory_id, memory_client)

    Raises:
        Exception: If memory creation or retrieval fails
    """
    if not region:
        region = AWS_REGION

    if not region:
        raise ValueError("AWS region is required for memory creation")

    if not memory_name:
        memory_name = SHORT_TERM_MEMORY_NAME

    if not expiry_days:
        expiry_days = SHORT_TERM_MEMORY_EXPIRY_DAYS

    client = MemoryClient(region_name=region)

    try:
        # First try to find existing memory
        memories = client.list_memories()
        logger.info(f"Searching through {len(memories)} existing memories for '{memory_name}'")

        memory_id = None
        for memory in memories:
            if memory.get("name") == memory_name:
                memory_id = memory["id"]
                break
            # Fallback: check if ID contains the memory name
            elif memory_name.lower() in memory.get("id", "").lower():
                memory_id = memory["id"]
                break

        if memory_id:
            logger.info(f"✅ Found existing short-term memory: {memory_id}")
            return memory_id, client

        # If not found, create new memory
        logger.info(f"Creating new short-term memory: {memory_name}")
        memory = client.create_memory_and_wait(
            name=memory_name,
            strategies=[],  # No strategies for short-term memory - stores raw events only
            description="Short-term memory for hotel booking agent conversation history",
            event_expiry_days=expiry_days,
        )
        memory_id = memory["id"]
        logger.info(f"✅ Created short-term memory: {memory_id}")
        return memory_id, client

    except ClientError as e:
        logger.warn(f"❌ Error accessing memory service: {e}", "error")
        raise
    except Exception as e:
        logger.warn(f"❌ Unexpected error: {e}", "error")
        raise


def get_conversation_history(
    logger, memory_client: MemoryClient, memory_id: str, actor_id: str, session_id: str, k: int = 5
) -> str:
    """
    Retrieve recent conversation history from short-term memory.

    Args:
        memory_client: MemoryClient instance
        memory_id: ID of the memory resource
        actor_id: Unique identifier for the customer/user
        session_id: Unique identifier for the session
        k: Number of recent conversation turns to retrieve

    Returns:
        List of conversation turns, each containing messages
    """
    try:
        recent_turns = memory_client.get_last_k_turns(
            memory_id=memory_id, actor_id=actor_id, session_id=session_id, k=k
        )

        logger.info(f"Retrieved {len(recent_turns)} conversation turns from memory")

        conversation_history = format_conversation_history(recent_turns)
        return conversation_history

    except Exception as e:
        logger.warn(f"❌ Error retrieving conversation history: {e}", "error")
        return []


def format_conversation_history(conversation_turns: list[dict[str, Any]]) -> str:
    """
    Format conversation history for display or logging.

    Args:
        conversation_turns: List of conversation turns from memory

    Returns:
        Formatted conversation history as string
    """
    if not conversation_turns:
        return "No conversation history available."

    formatted_messages = []
    for _turn_idx, turn in enumerate(conversation_turns, start=1):
        for message in turn:
            role = message["role"]
            content = message["content"]["text"]
            # Truncate long messages for display
            display_content = content
            formatted_messages.append(f"  {role}: {display_content}")
        formatted_messages.append("")  # Empty line between turns

    return "\\n".join(formatted_messages)


# Convenience function for hotel booking agent
def create_hotel_booking_short_term_memory(logger, region: str = None) -> tuple[str, MemoryClient]:
    """Create short-term memory specifically for hotel booking agent"""
    return create_short_term_memory(logger, region=region, memory_name="HotelBookingShortTermMemory", expiry_days=7)
