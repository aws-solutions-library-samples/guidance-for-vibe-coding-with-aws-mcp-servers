#!/usr/bin/env python3

import aws_cdk as cdk
from cdk_nag import AwsSolutionsChecks
from src.stacks.booking_agent_stack import HotelBookingAgentStack
from src.stacks.mcp_server_stack import HotelBookingMCPStack
from src.stacks.mock_apis_stack import MockApisStack


app = cdk.App()

# Mock APIs stack
MockApisStack(
    app,
    "VibeCodingWorkshopMockApis",
    description="Mock APIs for Vibe Coding workshop - Property Resolution, Reservation Services, and Toxicity Detection",
)

# Hotel Booking Agent stack
booking_agent_stack = HotelBookingAgentStack(
    app,
    "VibeCodingWorkshopBookingAgent",
    description="Hotel Booking Agent for AgentCore Vibe Coding workshop (Solution ID: SO9638)",
)

# MCP Server stack
mcp_server_stack = HotelBookingMCPStack(
    app, "VibeCodingWorkshopMcpServer", description="MCP Server for AgentCore Vibe Coding workshop"
)

# Set up dependency: MCP server stack depends on booking agent stack
mcp_server_stack.add_dependency(booking_agent_stack)

# Add CDK Nag checks for security and best practices
cdk.Aspects.of(app).add(AwsSolutionsChecks(verbose=True))

app.synth()
