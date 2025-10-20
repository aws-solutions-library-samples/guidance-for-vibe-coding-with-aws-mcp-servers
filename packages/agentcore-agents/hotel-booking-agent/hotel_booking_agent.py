import boto3
import json
import logging
import traceback
import uuid
from bedrock_agentcore import BedrockAgentCoreApp

# Import AWS configuration utilities
from common.aws_config import AWSConfig
from common.cognito_token_manager import CognitoTokenManager
from common.prompts import get_hotel_booking_system_prompt
from datetime import datetime
from mcp.client.streamable_http import streamablehttp_client
from memory.short_term_memory import ShortTermMemoryHooks, create_hotel_booking_short_term_memory
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from strands import Agent
from strands.models import BedrockModel
from strands.tools.mcp.mcp_client import MCPClient


# Configure default logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_logger():
    """Get the logger instance"""
    return logger


# Log that the main agent is initialized
logger.info("Hotel booking agent initialized")

# Initialize AWS configuration with the logger
aws_config = AWSConfig(logger)
AWS_REGION = aws_config.get_region()

# Configure boto3 clients
bedrock_client = boto3.client("bedrock-runtime")

app = BedrockAgentCoreApp()
app = Starlette(app)
app = BedrockAgentCoreApp(CORSMiddleware(app=app, allow_origins=["*"], allow_headers=["*"], allow_methods=["*"]))

# Initialize memory at load time
short_term_memory_id = None
short_term_memory_client = None


def initialize_memory():
    """Initialize both long-term and short-term memory resources at module load time"""
    global short_term_memory_id, short_term_memory_client
    try:
        if AWS_REGION:
            # Initialize short-term memory
            short_term_memory_id, short_term_memory_client = create_hotel_booking_short_term_memory(logger, AWS_REGION)
            logger.info(f"✅ Short-term memory initialized at load time: {short_term_memory_id}")
        else:
            logger.warn("⚠️ No AWS region available at load time, will initialize on first invocation")
    except Exception as e:
        logger.warn(f"⚠️ Failed to initialize memory at load time: {e}")
        # Memory will be created on first invocation if this fails


# Initialize memory when module loads
initialize_memory()


@app.entrypoint
async def agent_invocation(payload, context):  # noqa: ARG001
    logger.info(f"Received payload: {payload}")

    """Handler for agent invocation"""
    prompt = payload.get(
        "prompt", "No prompt found in input, please guide customer to create a json payload with prompt key"
    )

    # Extract customer ID from payload or generate one
    customer_id = payload.get("customer_id", f"customer_{uuid.uuid4().hex[:8]}")
    session_id = payload.get("session_id", f"booking_{datetime.now().strftime('%Y%m%d%H%M%S')}")

    try:
        # Get tool name from SSM to construct proper parameter paths
        ssm_client = boto3.client("ssm", region_name=AWS_REGION)
        tool_name_response = ssm_client.get_parameter(Name="/hotel_booking_mcp/runtime/agent_name")
        tool_name = tool_name_response["Parameter"]["Value"]
        logger.info(f"Retrieved tool name: {tool_name}")

        agent_arn_response = ssm_client.get_parameter(Name=f"/{tool_name}/runtime/agent_arn")
        agent_arn = agent_arn_response["Parameter"]["Value"]
        logger.info(f"Retrieved Agent ARN: {agent_arn}")

        # Initialize token manager and get fresh bearer token
        token_manager = CognitoTokenManager(secret_name=f"{tool_name}/cognito/credentials")
        bearer_token = token_manager.get_fresh_token()
        logger.info("✓ Retrieved bearer token from Secrets Manager")

        # Use global memory or create if not available
        global short_term_memory_id, short_term_memory_client
        if not short_term_memory_id or not short_term_memory_client:
            logger.info("Short-term memory not initialized at load time, creating now...")
            short_term_memory_id, short_term_memory_client = create_hotel_booking_short_term_memory(logger, AWS_REGION)

        logger.info(f"Using short-term memory: {short_term_memory_id}")

    except Exception as e:
        logger.error(f"Error retrieving credentials or setting up memory: {e}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": f"Setup error: {e}"}),
        }

    encoded_arn = agent_arn.replace(":", "%3A").replace("/", "%2F")
    mcp_url = (
        f"https://bedrock-agentcore.{AWS_REGION}.amazonaws.com/runtimes/{encoded_arn}/invocations?qualifier=DEFAULT"
    )

    logger.info(f"MCP URL: {mcp_url}")

    headers = {"authorization": f"Bearer {bearer_token}", "Content-Type": "application/json"}

    bedrock_model = BedrockModel(model_id="us.anthropic.claude-sonnet-4-20250514-v1:0", client=bedrock_client)

    mcp_client = MCPClient(lambda: streamablehttp_client(mcp_url, headers=headers))

    with mcp_client:
        try:
            logger.info("Successfully connected to MCP server")

            # Get the tools from the MCP client
            logger.info("Listing available tools from MCP server...")
            tools = mcp_client.list_tools_sync()
            logger.info(f"Found {len(tools)} tools")

            # Create tool descriptions for the system prompt
            toolsDesciptions = []
            for tool in tools:
                # Convert display properties to string to avoid type issues
                display_props = tool.get_display_properties()
                if isinstance(display_props, dict):
                    display_props = json.dumps(display_props)
                toolsDesciptions.append(f"{tool.tool_name}: {display_props}")
                logger.info(f"Tool: {tool.tool_name}: {display_props}")

            # Enhanced system prompt with comprehensive booking capabilities and memory awareness
            system_prompt = get_hotel_booking_system_prompt(toolsDesciptions)

            logger.info(f"System Prompt: {system_prompt}")

            # Create memory hooks for and short-term memory
            short_term_hooks = ShortTermMemoryHooks(
                memory_client=short_term_memory_client,
                memory_id=short_term_memory_id,
                actor_id=customer_id,
                session_id=session_id,
                logger=logger,
                conversation_turns=20,  # Load last 20 conversation turns
            )

            # Create an agent with both memory hooks, system prompt and tools
            agent = Agent(
                model=bedrock_model,
                system_prompt=system_prompt,
                tools=tools,
                hooks=[short_term_hooks],  # Both memory types
            )
            logger.info("Agent created successfully with long-term and short-term memory capabilities")

            # Invoke the agent with the prompt
            result = agent(prompt)
            logger.info(f"Agent response: {result}")

            final_response = {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(
                    {
                        "status": "COMPLETED",
                        "message": result.message,
                        "customer_id": customer_id,
                        "session_id": session_id,
                    }
                ),
            }
            return final_response

        except Exception as e:
            logger.error(f"Error in MCP tool connection: {e}")
            logger.error(traceback.format_exc())
            response = {
                "statusCode": 500,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": f"Error in MCP tool connection: {e}"}),
            }
            return response


if __name__ == "__main__":
    app.run()
