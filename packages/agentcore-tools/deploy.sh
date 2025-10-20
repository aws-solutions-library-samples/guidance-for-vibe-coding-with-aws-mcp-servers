#!/bin/bash

# Generic AgentCore Deployment Script
# Usage: ./deploy.sh <agent_file_path> <agent_name> [protocol]
# Example: ./deploy.sh src/agentcore/hotel-booking-agent/hotel_booking_agent.py hotel_booking_agent
# Example: ./deploy.sh src/agentcore/mcp-server/hotel-booking/hotel_booking_mcp.py hotel_booking_mcp MCP

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}❌${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 <agent_file_path> <agent_name> [protocol]"
    echo ""
    echo "Parameters:"
    echo "  agent_file_path : Path to the agent Python entrypoint file (e.g., path/to/agent.py)"
    echo "  agent_name      : Name of the agent (e.g., hotel_booking_agent, hotel_booking_mcp)"
    echo "  protocol        : Protocol type (optional, auto-detected based on path/name)"
    echo ""
    echo "Examples:"
    echo "  $0 src/agentcore/hotel-booking-agent/hotel_booking_agent.py hotel_booking_agent"
    echo "  $0 src/agentcore/mcp-server/hotel-booking/hotel_booking_mcp.py hotel_booking_mcp MCP"
    echo "  $0 /path/to/my/custom/agent.py my_custom_agent"
    echo ""
    echo "Requirements:"
    echo "  - The agent_file_path must be a valid Python file"
    echo "  - The directory containing the agent file must have requirements.txt"
}

# Check parameters
if [ $# -lt 2 ]; then
    print_error "Insufficient parameters provided"
    show_usage
    exit 1
fi

AGENT_FILE_PATH="$1"
AGENT_NAME="$2"
PROTOCOL="${3:-agent}"

# Convert relative path to absolute path for consistency
if [[ "$AGENT_FILE_PATH" != /* ]]; then
    AGENT_FILE_PATH="$(pwd)/$AGENT_FILE_PATH"
fi

# Extract directory and filename from the agent file path
WORK_DIR="$(dirname "$AGENT_FILE_PATH")"
ENTRYPOINT_FILE="$(basename "$AGENT_FILE_PATH")"

# Validate that the file exists and is a Python file
if [ ! -f "$AGENT_FILE_PATH" ]; then
    print_error "Agent file not found: $AGENT_FILE_PATH"
    exit 1
fi

if [[ "$ENTRYPOINT_FILE" != *.py ]]; then
    print_error "Agent file must be a Python file (.py): $ENTRYPOINT_FILE"
    exit 1
fi

# Auto-detect protocol based on path if not explicitly provided
if [ $# -eq 2 ]; then
    if [[ "$AGENT_FILE_PATH" == *"mcp-server"* ]] || [[ "$AGENT_NAME" == *"_mcp" ]]; then
        PROTOCOL="MCP"
    else
        PROTOCOL="agent"
    fi
fi

print_info "Starting deployment for agent: $AGENT_NAME"
print_info "Agent file path: $AGENT_FILE_PATH"
print_info "Working directory: $WORK_DIR"
print_info "Entrypoint file: $ENTRYPOINT_FILE"
print_info "Protocol: $PROTOCOL"

# Check if working directory exists
if [ ! -d "$WORK_DIR" ]; then
    print_error "Agent directory not found: $WORK_DIR"
    print_error "Please provide a valid path to the agent Python file"
    exit 1
fi

# Change to working directory
cd "$WORK_DIR"

# Check for required files
print_info "Checking for required files..."

# Check if requirements.txt exists in the working directory
if [ ! -f "$WORK_DIR/requirements.txt" ]; then
    print_error "Required file requirements.txt not found in $WORK_DIR"
    exit 1
fi

print_status "All required files found"
print_info "  - Entrypoint: $AGENT_FILE_PATH"
print_info "  - Requirements: $WORK_DIR/requirements.txt"

# Get AWS region
REGION="$AWS_DEFAULT_REGION"
if [ -z "$REGION" ]; then
    REGION=$(aws configure get region)
fi

if [ -z "$REGION" ]; then
    print_error "AWS region not set. Please set AWS_DEFAULT_REGION or configure AWS CLI"
    exit 1
fi

print_info "Using AWS region: $REGION"

# Check for agent name in SSM Parameter Store first, fallback to provided value
AGENT_NAME_FROM_SSM=$(aws ssm get-parameter --name "/$AGENT_NAME/runtime/agent_name" --query "Parameter.Value" --output text 2>/dev/null || echo "")

if [ -n "$AGENT_NAME_FROM_SSM" ] && [ "$AGENT_NAME_FROM_SSM" != "None" ]; then
    print_info "Found agent name in SSM Parameter Store: $AGENT_NAME_FROM_SSM"
    AGENT_NAME="$AGENT_NAME_FROM_SSM"
else
    print_info "Agent name not found in SSM Parameter Store, using provided value: $AGENT_NAME"
fi

POOL_NAME="$AGENT_NAME.Pool"
AGENTCORE_ROLE_NAME="$REGION-agentcore-$AGENT_NAME-role"

print_info "Using agent name: $AGENT_NAME"
print_info "Pool name: $POOL_NAME"
print_info "Role name: $AGENTCORE_ROLE_NAME"

# Check if role exists
ROLE_EXISTS=$(aws iam get-role --role-name "$AGENTCORE_ROLE_NAME" 2>/dev/null || echo "false")
if [ "$ROLE_EXISTS" == "false" ]; then
    print_error "Role $AGENTCORE_ROLE_NAME does not exist"
    print_error "Please run the CDK stack to create the role before running this deployment script"
    exit 1
fi
print_status "IAM role exists: $AGENTCORE_ROLE_NAME"

# Cognito Setup
print_info "Setting up Amazon Cognito user pool..."

# Check if user pool already exists in parameter store
EXISTING_POOL_ID=$(aws ssm get-parameter --name "/$AGENT_NAME/runtime/user_pool_id" --query "Parameter.Value" --output text 2>/dev/null || echo "")

if [ -n "$EXISTING_POOL_ID" ] && [ "$EXISTING_POOL_ID" != "None" ]; then
    print_info "Found existing user pool in parameter store: $EXISTING_POOL_ID"
    POOL_ID="$EXISTING_POOL_ID"
    
    # Retrieve CLIENT_ID and DISCOVERY_URL from parameter store
    CLIENT_ID=$(aws ssm get-parameter --name "/$AGENT_NAME/runtime/client_id" --query "Parameter.Value" --output text 2>/dev/null || echo "")
    DISCOVERY_URL=$(aws ssm get-parameter --name "/$AGENT_NAME/runtime/discovery_url" --query "Parameter.Value" --output text 2>/dev/null || echo "")
    
    if [ -z "$CLIENT_ID" ] || [ -z "$DISCOVERY_URL" ]; then
        print_warning "Missing CLIENT_ID or DISCOVERY_URL in parameter store, retrieving from Cognito..."
        
        # Get the app client from the existing user pool
        APP_CLIENTS=$(aws cognito-idp list-user-pool-clients --user-pool-id "$POOL_ID" --output json)
        CLIENT_ID=$(echo $APP_CLIENTS | jq -r '.UserPoolClients[0].ClientId')
        DISCOVERY_URL="https://cognito-idp.$REGION.amazonaws.com/$POOL_ID/.well-known/openid-configuration"
        
        # Store CLIENT_ID and DISCOVERY_URL in parameter store
        aws ssm put-parameter \
          --name "/$AGENT_NAME/runtime/client_id" \
          --value "$CLIENT_ID" \
          --type "String" \
          --description "Cognito Client ID" \
          --overwrite
        
        aws ssm put-parameter \
          --name "/$AGENT_NAME/runtime/discovery_url" \
          --value "$DISCOVERY_URL" \
          --type "String" \
          --description "Cognito Discovery URL" \
          --overwrite
    fi
    
    print_status "Using existing user pool:"
    print_info "  Pool ID: $POOL_ID"
    print_info "  Client ID: $CLIENT_ID"
    print_info "  Discovery URL: $DISCOVERY_URL"
    
else
    print_info "Creating new Cognito user pool: $POOL_NAME"

    USER_POOL_RESPONSE=$(aws cognito-idp create-user-pool \
      --pool-name "$POOL_NAME" \
      --policies '{"PasswordPolicy":{"MinimumLength":8}}' \
      --output json)

    POOL_ID=$(echo $USER_POOL_RESPONSE | jq -r '.UserPool.Id')
    print_info "Pool ID: $POOL_ID"

    aws ssm put-parameter \
      --name "/$AGENT_NAME/runtime/user_pool_id" \
      --value "$POOL_ID" \
      --type "String" \
      --description "User Pool Id" \
      --overwrite
    print_status "User Pool ID stored in Parameter Store"

    # Create App Client
    APP_CLIENT_RESPONSE=$(aws cognito-idp create-user-pool-client \
      --user-pool-id "$POOL_ID" \
      --client-name "${POOL_NAME}Client" \
      --no-generate-secret \
      --explicit-auth-flows "ALLOW_USER_PASSWORD_AUTH" "ALLOW_REFRESH_TOKEN_AUTH" \
      --output json)

    CLIENT_ID=$(echo $APP_CLIENT_RESPONSE | jq -r '.UserPoolClient.ClientId')
    print_info "Client ID: $CLIENT_ID"

    # Create User
    aws cognito-idp admin-create-user \
      --user-pool-id "$POOL_ID" \
      --username "testuser" \
      --temporary-password "Temp123!" \
      --message-action SUPPRESS

    # Set Permanent Password
    aws cognito-idp admin-set-user-password \
      --user-pool-id "$POOL_ID" \
      --username "testuser" \
      --password "MyPassword123!" \
      --permanent

    DISCOVERY_URL="https://cognito-idp.$REGION.amazonaws.com/$POOL_ID/.well-known/openid-configuration"
    
    print_info "Discovery URL: $DISCOVERY_URL"
    print_status "New user pool created"
    
    # Store CLIENT_ID and DISCOVERY_URL in parameter store
    aws ssm put-parameter \
      --name "/$AGENT_NAME/runtime/client_id" \
      --value "$CLIENT_ID" \
      --type "String" \
      --description "Cognito Client ID" \
      --overwrite
    
    aws ssm put-parameter \
      --name "/$AGENT_NAME/runtime/discovery_url" \
      --value "$DISCOVERY_URL" \
      --type "String" \
      --description "Cognito Discovery URL" \
      --overwrite
fi

# Authenticate User and get Access Token
AUTH_RESPONSE=$(aws cognito-idp initiate-auth \
  --client-id "$CLIENT_ID" \
  --auth-flow USER_PASSWORD_AUTH \
  --auth-parameters USERNAME=testuser,PASSWORD=MyPassword123! \
  --output json)

BEARER_TOKEN=$(echo $AUTH_RESPONSE | jq -r '.AuthenticationResult.AccessToken')
print_info "Bearer Token obtained"
print_status "Cognito setup completed"

# Store configuration in Secrets Manager
print_info "Storing Cognito values in Secrets Manager..."

# Create JSON for Cognito credentials
cat > cognito_config.json << EOF
{
  "pool_id": "$POOL_ID",
  "client_id": "$CLIENT_ID",
  "bearer_token": "$BEARER_TOKEN",  
  "username": "testuser",
  "password": "MyPassword123!"
}
EOF

# Store Cognito credentials in Secrets Manager
SECRET_EXISTS=$(aws secretsmanager describe-secret --secret-id $AGENT_NAME/cognito/credentials 2>/dev/null || echo "false")
if [ "$SECRET_EXISTS" == "false" ]; then
    aws secretsmanager create-secret \
      --name $AGENT_NAME/cognito/credentials \
      --description "Cognito credentials for $AGENT_NAME" \
      --secret-string file://cognito_config.json
    print_status "Cognito credentials stored in Secrets Manager"
else
    aws secretsmanager update-secret \
      --secret-id $AGENT_NAME/cognito/credentials \
      --secret-string file://cognito_config.json
    print_status "Cognito credentials updated in Secrets Manager"
fi

# IAM Role Setup
print_info "Setting up IAM role for $AGENT_NAME..."

ACCOUNT_ID=$(aws sts get-caller-identity --query "Account" --output text)
ROLE_ARN="arn:aws:iam::$ACCOUNT_ID:role/$AGENTCORE_ROLE_NAME"

aws ssm put-parameter \
  --name "/$AGENT_NAME/runtime/agent_role_name" \
  --value "$AGENTCORE_ROLE_NAME" \
  --type "String" \
  --description "Agent Role name" \
  --overwrite
print_status "Agent Role name stored in Parameter Store"

# Configure AgentCore Runtime
print_info "Configuring AgentCore Runtime..."

# Ensure DISCOVERY_URL is in the correct format
if [[ "$DISCOVERY_URL" == *"{"* ]]; then
    print_warning "DISCOVERY_URL contains JSON content, reconstructing URL..."
    DISCOVERY_URL="https://cognito-idp.$REGION.amazonaws.com/$POOL_ID/.well-known/openid-configuration"
    
    aws ssm put-parameter \
      --name "/$AGENT_NAME/runtime/discovery_url" \
      --value "$DISCOVERY_URL" \
      --type "String" \
      --description "Cognito Discovery URL" \
      --overwrite
fi

# Validate DISCOVERY_URL format
if [[ ! "$DISCOVERY_URL" == *"/.well-known/openid-configuration" ]]; then
    print_error "Invalid DISCOVERY_URL format: $DISCOVERY_URL"
    print_error "Expected format: https://cognito-idp.REGION.amazonaws.com/POOL_ID/.well-known/openid-configuration"
    exit 1
fi

# Create auth config JSON
AUTH_CONFIG_JSON=$(jq -n \
  --arg client_id "$CLIENT_ID" \
  --arg discovery_url "$DISCOVERY_URL" \
  '{
    "customJWTAuthorizer": {
      "allowedClients": [$client_id],
      "discoveryUrl": $discovery_url
    }
  }')

# Validate JSON
echo "$AUTH_CONFIG_JSON" | jq . > /dev/null
if [ $? -ne 0 ]; then
    print_error "Invalid JSON in auth config"
    exit 1
fi

print_info "Auth config JSON created successfully"

# Configure ECR
ECR_REPO="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/bedrock-agentcore-$AGENT_NAME"
ECR_REPO_NAME="bedrock-agentcore-$AGENT_NAME"

aws ssm put-parameter \
  --name "/$AGENT_NAME/runtime/ecr_repo_name" \
  --value "$ECR_REPO_NAME" \
  --type "String" \
  --description "ECR Repo Name" \
  --overwrite
print_status "ECR Repo Name stored in Parameter Store"

# Configure AgentCore
print_info "Configuring AgentCore with protocol: $PROTOCOL"

if [ "$PROTOCOL" == "MCP" ]; then
    uvx --from bedrock-agentcore-starter-toolkit agentcore configure \
      --entrypoint "$ENTRYPOINT_FILE" \
      --name "$AGENT_NAME" \
      --execution-role "$ROLE_ARN" \
      --ecr "$ECR_REPO" \
      --requirements-file requirements.txt \
      --authorizer-config "$AUTH_CONFIG_JSON" \
      --request-header-allowlist "Authorization" \
      --disable-memory \
      --protocol "MCP"
else
    uvx --from bedrock-agentcore-starter-toolkit agentcore configure \
      --entrypoint "$ENTRYPOINT_FILE" \
      --name "$AGENT_NAME" \
      --execution-role "$ROLE_ARN" \
      --ecr "$ECR_REPO" \
      --requirements-file requirements.txt \
      --request-header-allowlist "Authorization" \
      --disable-memory \
      --authorizer-config "$AUTH_CONFIG_JSON"
fi

print_status "Configuration completed"

# Launch AgentCore Runtime
print_info "Launching AgentCore Runtime..."
print_warning "This may take several minutes..."

LAUNCH_RESULT=$(uvx --from bedrock-agentcore-starter-toolkit agentcore launch -auc)

# Extract agent ARN and ID from launch result
AGENT_ARN=$(echo "$LAUNCH_RESULT" | grep -o "arn:aws:bedrock-agentcore:[^[:space:]]*" | head -1)
AGENT_ID=$(echo "$AGENT_ARN" | awk -F'/' '{print $NF}')

print_status "Launch completed"
print_info "Agent ARN: $AGENT_ARN"
print_info "Agent ID: $AGENT_ID"

# Check AgentCore Runtime status
print_info "Checking AgentCore Runtime status..."
STATUS_RESPONSE=$(uvx --from bedrock-agentcore-starter-toolkit agentcore status 2>&1)
STATUS_EXIT_CODE=$?

if [ $STATUS_EXIT_CODE -ne 0 ]; then
    print_warning "AgentCore status command failed with exit code: $STATUS_EXIT_CODE"
    print_warning "Response: $STATUS_RESPONSE"
    exit 1
fi

# Extract the status from the response with robust parsing for new format
extract_status() {
    local response="$1"
    local status=""
    
    # Method 1: Check for "Ready - Agent deployed and endpoint available"
    if echo "$response" | grep -q "Ready - Agent deployed and endpoint available"; then
        status="READY"
    fi
    
    # Method 2: Check for "Deploying - Agent created, endpoint starting"
    if [ -z "$status" ] && echo "$response" | grep -q "Deploying - Agent created, endpoint starting"; then
        status="CREATING"
    fi
    
    # Method 3: Check for "Endpoint: DEFAULT (READY)"
    if [ -z "$status" ] && echo "$response" | grep -q "Endpoint:.*READY"; then
        status="READY"
    fi
    
    # Method 4: Legacy STATUS: format (for backward compatibility)
    if [ -z "$status" ]; then
        status=$(echo "$response" | grep "STATUS:" | sed 's/.*STATUS: *\([A-Z_]*\).*/\1/')
    fi
    
    # Method 5: Check for common failure patterns
    if [ -z "$status" ]; then
        if echo "$response" | grep -qi "failed\|error\|not found"; then
            status="CREATE_FAILED"
        elif echo "$response" | grep -qi "creating\|deploying\|updating"; then
            status="CREATING"
        fi
    fi
    
    echo "$status"
}

# Extract Agent ARN from response
extract_agent_arn() {
    local response="$1"
    local arn=""
    
    # Method 1: Extract the ARN lines after "Agent ARN:" and before "Endpoint:"
    local arn_lines=$(echo "$response" | grep -A 3 "Agent ARN:" | grep -v "Agent ARN:" | grep -v "Endpoint:" | tr -d '│ ')
    
    if [ -n "$arn_lines" ]; then
        # Concatenate all ARN parts and remove spaces/newlines
        arn=$(echo "$arn_lines" | tr -d '\n' | sed 's/[[:space:]]*//g')
    fi
    
    # Method 2: Try single line extraction (fallback)
    if [ -z "$arn" ]; then
        arn=$(echo "$response" | grep -o "arn:aws:bedrock-agentcore:[^[:space:]│]*" | head -1)
    fi
    
    # Method 3: Direct sed extraction
    if [ -z "$arn" ]; then
        arn=$(echo "$response" | sed -n '/Agent ARN:/,/Endpoint:/p' | grep "arn:aws:bedrock-agentcore" | tr -d '│ ' | head -1)
    fi
    
    echo "$arn"
}

STATUS=$(extract_status "$STATUS_RESPONSE")
print_info "Initial status: $STATUS"

# Validate status was extracted
if [ -z "$STATUS" ]; then
    print_warning "Could not extract status from response:"
    print_warning "$STATUS_RESPONSE"
    exit 1
fi

# Wait for agent to be ready
END_STATUS=("READY" "CREATE_FAILED" "DELETE_FAILED" "UPDATE_FAILED" "FAILED")
while [[ ! " ${END_STATUS[@]} " =~ " ${STATUS} " ]]; do
    print_info "Status: $STATUS - waiting..."
    sleep 10
    STATUS_RESPONSE=$(uvx --from bedrock-agentcore-starter-toolkit agentcore status 2>&1)
    STATUS_EXIT_CODE=$?
    
    if [ $STATUS_EXIT_CODE -ne 0 ]; then
        print_warning "AgentCore status command failed during polling with exit code: $STATUS_EXIT_CODE"
        print_warning "Response: $STATUS_RESPONSE"
        exit 1
    fi
    
    STATUS=$(extract_status "$STATUS_RESPONSE")
    
    if [ -z "$STATUS" ]; then
        print_warning "Could not extract status during polling from response:"
        print_warning "$STATUS_RESPONSE"
        exit 1
    fi
done

if [ "$STATUS" == "READY" ]; then
    print_status "AgentCore Runtime is READY!"
else
    print_warning "AgentCore Runtime status: $STATUS"
fi

# Extract final Agent ARN from status response
print_info "Extracting Agent ARN from status response..."

# Debug: Show relevant lines from response
print_info "Debug: ARN-related lines from response:"
echo "$STATUS_RESPONSE" | grep -A 5 -B 2 "Agent ARN\|arn:aws:bedrock-agentcore" | head -10

print_info "Debug: Calling extract_agent_arn function..."
AGENT_ARN=$(extract_agent_arn "$STATUS_RESPONSE")
print_info "Debug: Function returned ARN: '$AGENT_ARN'"
print_info "Debug: ARN length: ${#AGENT_ARN}"

# Validate ARN extraction
if [ -n "$AGENT_ARN" ] && [[ "$AGENT_ARN" == arn:aws:bedrock-agentcore:* ]]; then
    # Extract Agent ID from ARN
    AGENT_ID=$(echo "$AGENT_ARN" | awk -F'/' '{print $NF}')
    print_info "✅ Successfully extracted Agent ARN: $AGENT_ARN"
    print_info "✅ Successfully extracted Agent ID: $AGENT_ID"
    
    # Validate Agent ID is not empty
    if [ -z "$AGENT_ID" ] || [ "$AGENT_ID" = "$AGENT_ARN" ]; then
        print_warning "Agent ID extraction failed - ARN may not contain '/' separator"
        print_warning "ARN: '$AGENT_ARN'"
        # Try alternative extraction
        AGENT_ID=$(echo "$AGENT_ARN" | sed 's/.*runtime\///')
        print_info "Alternative Agent ID extraction: '$AGENT_ID'"
    fi
else
    print_warning "❌ Could not extract valid Agent ARN from response"
    print_warning "Extracted ARN: '$AGENT_ARN'"
    print_warning "ARN length: ${#AGENT_ARN}"
    print_warning "Full response:"
    print_warning "$STATUS_RESPONSE"
    
    # Try manual extraction as last resort
    print_info "Attempting manual ARN extraction..."
    MANUAL_ARN=$(echo "$STATUS_RESPONSE" | grep -o "arn:aws:bedrock-agentcore[^│]*" | head -1 | tr -d '│ ')
    print_info "Manual extraction result: '$MANUAL_ARN'"
    
    if [ -n "$MANUAL_ARN" ]; then
        AGENT_ARN="$MANUAL_ARN"
        AGENT_ID=$(echo "$AGENT_ARN" | awk -F'/' '{print $NF}')
        print_info "✅ Manual extraction successful!"
        print_info "Agent ARN: $AGENT_ARN"
        print_info "Agent ID: $AGENT_ID"
    else
        exit 1
    fi
fi

print_info "Final Agent ID: $AGENT_ID"
print_info "Final Agent ARN: $AGENT_ARN"

# Store parameters in SSM Parameter Store
aws ssm put-parameter \
  --name "/$AGENT_NAME/runtime/agent_arn" \
  --value "$AGENT_ARN" \
  --type "String" \
  --description "Agent ARN for $AGENT_NAME" \
  --overwrite
print_status "Agent ARN stored in Parameter Store"

aws ssm put-parameter \
  --name "/$AGENT_NAME/runtime/agent_id" \
  --value "$AGENT_ID" \
  --type "String" \
  --description "Agent Id" \
  --overwrite
print_status "Agent ID stored in Parameter Store"

# Clean up temporary files
rm -f auth_config.json cognito_config.json

print_status "Deployment completed successfully!"
print_info ""
print_info "🎉 Deployment Summary:"
print_info "   Agent File Path: $AGENT_FILE_PATH"
print_info "   Agent Name: $AGENT_NAME"
print_info "   Protocol: $PROTOCOL"
print_info "   Status: $STATUS"
print_info "   Agent ID: $AGENT_ID"
print_info "   Agent ARN: $AGENT_ARN"
print_info ""