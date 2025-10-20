#!/usr/bin/env python3

import aws_cdk as cdk
from cdk_nag import AwsSolutionsChecks
from src.stacks.booking_agent_stack import BookingAgentCoreStack
from src.stacks.mcp_server_stack import MCPAgentCoreStack
from src.stacks.mock_apis_stack import MockApisStack


app = cdk.App()

# Mock APIs stack
MockApisStack(
    app,
    "AgentCoreTechSummitMockApis",
    description="Mock APIs for AgentCore Tech Summit 2025 workshop - Property Resolution, Reservation Services, and Toxicity Detection",
)

# Hotel Booking Agent stack (must be deployed first)
booking_agent_stack = BookingAgentCoreStack(
    app, "AgentCoreTechSummitBookingAgent", description="Hotel Booking Agent for AgentCore Tech Summit 2025 workshop"
)

# MCP Server stack (depends on booking agent stack)
mcp_server_stack = MCPAgentCoreStack(
    app, "AgentCoreTechSummitMcpServer", description="MCP Server for AgentCore Tech Summit 2025 workshop"
)

# Set up dependency: MCP server stack depends on booking agent stack
mcp_server_stack.add_dependency(booking_agent_stack)

# Add CDK Nag checks for security and best practices
cdk.Aspects.of(app).add(AwsSolutionsChecks(verbose=True))

app.synth()
