# MCP Server Bruno Tests

This directory contains Bruno test files for testing the deployed MCP server directly through AgentCore endpoints.

## 📁 Directory Structure

```
mcp_server_tests/
├── bruno.json                    # Bruno collection configuration
├── environments/
│   └── MCPServer.bru             # MCP server environment variables
├── Tools/
│   ├── 01_Search_Properties.bru  # Test property search functionality
│   ├── 02_Create_Reservation.bru # Test reservation creation
│   └── 03_Check_Toxicity.bru     # Test toxicity detection (disabled)
└── README.md                     # This file
```

## 🚀 Setup Instructions

### Prerequisites

Before running these tests, you must:

1. **Deploy the MCP server** using the deployment script
2. **Deploy the Mock APIs** (Property Resolution, Reservations, Toxicity Detection)
3. **Have valid AWS credentials** with access to AgentCore and Cognito

⚠️ **Important**: The environment file contains placeholder values that MUST be replaced with actual values from your deployment:

- `mcpServerUrl`: Replace `YOUR_MCP_SERVER_URL` with your AgentCore runtime URL
- `bearerToken`: Replace `YOUR_BEARER_TOKEN` with a valid Cognito token
- Hotel IDs and details: Will be populated dynamically by tests or can be set manually

### 1. Update Environment Variables

After deploying the MCP server, update the values in `environments/MCPServer.bru`:

```bash
# Get the MCP server ARN from Parameter Store
aws ssm get-parameter --name "/hotel_booking_mcp/runtime/agent_arn" --query "Parameter.Value" --output text

# Get a fresh Cognito bearer token
# (Use the cognito_token_manager.py or test_mcp_direct.py to get a token)
```

Update these values in `MCPServer.bru`:

- `mcpServerUrl`: Replace with the correct AgentCore URL using your MCP server ARN
- `bearerToken`: Replace with a valid Cognito bearer token

### 2. URL Format

The MCP server URL should follow this format:

```
https://bedrock-agentcore.{region}.amazonaws.com/runtimes/{encoded_arn}/invocations
```

Where `{encoded_arn}` is your MCP server ARN with URL encoding:

- `:` becomes `%3A`
- `/` becomes `%2F`

Example:

```
Original ARN: arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/hotel_booking_mcp
Encoded ARN:  arn%3Aaws%3Abedrock-agentcore%3Aus-east-1%3A123456789012%3Aruntime%2Fhotel_booking_mcp
Full URL:     https://bedrock-agentcore.us-east-1.amazonaws.com/runtimes/arn%3Aaws%3Abedrock-agentcore%3Aus-east-1%3A123456789012%3Aruntime%2Fhotel_booking_mcp/invocations
```

## 🧪 Running Tests

### Using Bruno CLI

```bash
# Install Bruno CLI if not already installed
npm install -g @usebruno/cli

# Run all tests
bru run packages/cdk-infra-python/tests/bruno/mcp_server_tests --env MCPServer

# Run specific test
bru run packages/cdk-infra-python/tests/bruno/mcp_server_tests/Tools/01_Search_Properties.bru --env MCPServer
```

### Using Bruno GUI

1. Open Bruno application
2. Open the collection: `packages/cdk-infra-python/tests/bruno/mcp_server_tests`
3. Select the `MCPServer` environment
4. Run individual tests or the entire collection

## 📋 Test Descriptions

### 1. Search Properties (`01_Search_Properties.bru`)

- **Purpose**: Tests the `search_properties` MCP tool
- **API Called**: Property Resolution API via MCP server
- **Expected**: Returns hotel search results for San Francisco
- **Validation**: HTTP 200, response contains search data

### 2. Create Reservation (`02_Create_Reservation.bru`)

- **Purpose**: Tests the `create_reservation` MCP tool
- **API Called**: Reservation Services API via MCP server
- **Expected**: Creates a hotel reservation successfully
- **Validation**: HTTP 200, response contains reservation confirmation

### 3. Check Toxicity (`03_Check_Toxicity.bru`)

- **Purpose**: Tests the `check_toxicity` MCP tool
- **API Called**: Toxicity Detection API (currently disabled)
- **Expected**: Returns appropriate message about disabled functionality
- **Validation**: HTTP 200, response handles disabled tool gracefully

## 🔧 Troubleshooting

### Common Issues

1. **401 Unauthorized**

   - Check that `bearerToken` is valid and not expired
   - Regenerate token using `cognito_token_manager.py`

2. **404 Not Found**

   - Verify `mcpServerUrl` is correctly formatted
   - Ensure MCP server is deployed and running
   - Check ARN encoding is correct

3. **500 Internal Server Error**
   - Check MCP server logs in CloudWatch
   - Verify Parameter Store configuration
   - Ensure Mock APIs are deployed and accessible

### Getting Fresh Tokens

Use the existing test script to get a fresh token:

```bash
cd src/agentcore/mcp-server/hotel-booking
python -c "
from cognito_token_manager import CognitoTokenManager
token_manager = CognitoTokenManager(secret_name='hotel_booking_mcp/cognito/credentials')
print('Bearer Token:', token_manager.get_fresh_token())
"
```

## 🔗 Related Files

- **MCP Server Code**: `src/agentcore/mcp-server/hotel-booking/`
- **Direct Test Script**: `src/agentcore/mcp-server/hotel-booking/test_mcp_direct.py`
- **Local Test Script**: `src/agentcore/mcp-server/hotel-booking/test_bruno_local.py`
  - ⚠️ **Setup Required**: Replace placeholder API URLs and keys with your deployed stack outputs
  - Get values from CDK deployment outputs or CloudFormation stack outputs
- **Mock API Tests**: `packages/cdk-infra-python/tests/bruno/booking_mock_apis/`

## 📊 Test Results

After running tests, you should see:

- ✅ All HTTP requests return 200 status
- ✅ Responses contain expected data structures
- ✅ MCP tools are properly invoked through AgentCore
- ✅ Integration with Mock APIs works correctly

## 🎯 Next Steps

1. Deploy the MCP server using the deployment script
2. Update environment variables with actual values
3. Run tests to verify end-to-end functionality
4. Use results to debug any integration issues
