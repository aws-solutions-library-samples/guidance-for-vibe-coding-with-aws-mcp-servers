"""
Memory hooks for hotel booking agent with long-term memory capabilities.

This module provides the HotelBookingMemoryHooks class that automatically manages
customer context storage and retrieval using Amazon Bedrock AgentCore Memory.
"""

import logging
import os
from bedrock_agentcore.memory import MemoryClient
from bedrock_agentcore.memory.constants import StrategyType
from strands.hooks import AfterInvocationEvent, HookProvider, HookRegistry, MessageAddedEvent


logger = logging.getLogger(__name__)
# Get AWS region from environment
AWS_REGION = os.environ.get("AWS_DEFAULT_REGION")

# Memory configuration
MEMORY_NAME = "HotelBookingMemory"
MEMORY_EXPIRY_DAYS = 90


def get_namespaces(mem_client: MemoryClient, memory_id: str) -> dict:
    """Get namespace mapping for memory strategies."""
    strategies = mem_client.get_memory_strategies(memory_id)
    return {i["type"]: i["namespaces"][0] for i in strategies}


class HotelBookingMemoryHooks(HookProvider):
    """Memory hooks for hotel booking agent"""

    def __init__(self, memory_id: str, client: MemoryClient, actor_id: str, session_id: str, logger):
        """
        Initialize memory hooks for hotel booking agent.

        Args:
            memory_id: The ID of the memory resource
            client: The MemoryClient instance
            actor_id: The customer/actor ID
            session_id: The current session ID
            logger: Logger instance to use
        """
        self.memory_id = memory_id
        self.client = client
        self.actor_id = actor_id
        self.session_id = session_id
        self.logger = logger
        self.namespaces = get_namespaces(self.client, self.memory_id)

    def retrieve_customer_context(self, event: MessageAddedEvent):
        """
        Retrieve customer context before processing booking query.

        This hook automatically injects relevant customer context from previous
        interactions into the current query to provide personalized responses.
        """
        messages = event.agent.messages
        if messages[-1]["role"] == "user" and "toolResult" not in messages[-1]["content"][0]:
            user_query = messages[-1]["content"][0]["text"]

            try:
                # Retrieve customer context from all namespaces
                all_context = []

                for context_type, namespace in self.namespaces.items():
                    memories = self.client.retrieve_memories(
                        memory_id=self.memory_id,
                        namespace=namespace.format(actorId=self.actor_id),
                        query=user_query,
                        top_k=3,
                    )

                    for memory in memories:
                        if isinstance(memory, dict):
                            content = memory.get("content", {})
                            if isinstance(content, dict):
                                text = content.get("text", "").strip()
                                if text:
                                    all_context.append(f"[{context_type.upper()}] {text}")

                # Inject customer context into the query
                if all_context:
                    context_text = "\n".join(all_context)
                    original_text = messages[-1]["content"][0]["text"]
                    messages[-1]["content"][0]["text"] = f"Customer Context:\n{context_text}\n\n{original_text}"
                    self.logger.info(f"Retrieved {len(all_context)} customer context items")

            except Exception as e:
                self.logger.warn(f"Failed to retrieve customer context: {e}", "error")

    def save_booking_interaction(self, event: AfterInvocationEvent):
        """
        Save booking interaction after agent response.

        This hook automatically stores customer interactions in memory for
        future reference and personalization.
        """
        try:
            messages = event.agent.messages
            if len(messages) >= 2 and messages[-1]["role"] == "assistant":
                # Get last customer query and agent response
                customer_query = None
                agent_response = None

                for msg in reversed(messages):
                    if msg["role"] == "assistant" and not agent_response:
                        agent_response = msg["content"][0]["text"]
                    elif msg["role"] == "user" and not customer_query and "toolResult" not in msg["content"][0]:
                        customer_query = msg["content"][0]["text"]
                        break

                if customer_query and agent_response:
                    # Save the booking interaction
                    self.client.create_event(
                        memory_id=self.memory_id,
                        actor_id=self.actor_id,
                        session_id=self.session_id,
                        messages=[(customer_query, "USER"), (agent_response, "ASSISTANT")],
                    )
                    self.logger.info("Saved booking interaction to memory")

        except Exception as e:
            self.logger.warn(f"Failed to save booking interaction: {e}", "error")

    def register_hooks(self, registry: HookRegistry) -> None:
        """
        Register hotel booking memory hooks.

        This method registers the memory hooks with the agent's hook registry
        to enable automatic memory management.
        """
        registry.add_callback(MessageAddedEvent, self.retrieve_customer_context)
        registry.add_callback(AfterInvocationEvent, self.save_booking_interaction)
        self.logger.info("Hotel booking memory hooks registered")


def find_existing_memory(logger, client: MemoryClient, memory_name: str) -> str:
    """
    Find existing memory by name.

    Args:
        client: MemoryClient instance
        memory_name: Name of the memory to find

    Returns:
        Memory ID if found

    Raises:
        Exception: If memory not found
    """
    try:
        memories = client.list_memories()
        logger.info(f"Searching through {len(memories)} existing memories for '{memory_name}'")

        for memory in memories:
            logger.info(f"Memory found: ID={memory.get('id')}, Name={memory.get('name')}")

            # Check by exact name match first
            if memory.get("name") == memory_name:
                return memory["id"]

            # Fallback: check if ID contains the memory name (case insensitive)
            memory_id = memory.get("id", "")
            if memory_name.lower() in memory_id.lower():
                return memory_id

        raise Exception(f"No memory found with name '{memory_name}'")

    except Exception as e:
        logger.warn(f"Error finding existing memory: {e}", "error")
        raise


def create_or_get_memory(logger, region: str = None) -> tuple[str, MemoryClient]:
    """
    Create or get existing memory resource for hotel booking.

    Args:
        region: AWS region name (optional, uses global AWS_REGION if not provided)

    Returns:
        Tuple of (memory_id, memory_client)

    Raises:
        Exception: If memory creation or retrieval fails
    """
    if not region:
        region = AWS_REGION

    if not region:
        raise ValueError("AWS region is required for memory creation")

    print(f"Using AWS region: {region}")

    client = MemoryClient(region_name=region)

    # Define memory strategies for hotel booking
    strategies = [
        {
            StrategyType.USER_PREFERENCE.value: {
                "name": "CustomerPreferences",
                "description": "Captures customer preferences for hotels, rooms, and travel",
                "namespaces": ["booking/customer/{actorId}/preferences"],
            }
        },
        {
            StrategyType.SEMANTIC.value: {
                "name": "BookingSemantic",
                "description": "Stores facts from booking conversations and history",
                "namespaces": ["booking/customer/{actorId}/semantic"],
            }
        },
    ]

    memory_id = None

    # If memory already exists, find and return it
    try:
        memory_id = find_existing_memory(logger, client, MEMORY_NAME)
        logger.info(f"✅ Found existing memory: {memory_id}")
        return memory_id, client
    except Exception as find_error:
        logger.warn(f"❌ Error finding existing memory: {find_error}")

    try:
        if not memory_id:
            memory = client.create_memory_and_wait(
                name=MEMORY_NAME,
                strategies=strategies,
                description="Memory for hotel booking agent",
                event_expiry_days=MEMORY_EXPIRY_DAYS,
            )
            memory_id = memory["id"]
            logger.info(f"✅ Created memory: {memory_id}")
            return memory_id, client
    except Exception as e:
        logger.warn(f"❌ ERROR: {e}", "error")
        raise
