#!/bin/bash

# Generic AgentCore Destroy Script
# Usage: ./destroy.sh <agent_file_path> <agent_name>
# Example: ./destroy.sh src/agentcore/hotel-booking-agent/hotel_booking_agent.py hotel_booking_agent
# Example: ./destroy.sh src/agentcore/mcp-server/hotel-booking/hotel_booking_mcp.py hotel_booking_mcp

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
    echo "Usage: $0 <agent_file_path> <agent_name>"
    echo ""
    echo "Parameters:"
    echo "  agent_file_path : Path to the agent Python entrypoint file (e.g., path/to/agent.py)"
    echo "  agent_name      : Name of the agent (e.g., hotel_booking_agent, hotel_booking_mcp)"
    echo ""
    echo "Examples:"
    echo "  $0 src/agentcore/hotel-booking-agent/hotel_booking_agent.py hotel_booking_agent"
    echo "  $0 src/agentcore/mcp-server/hotel-booking/hotel_booking_mcp.py hotel_booking_mcp"
    echo "  $0 /path/to/my/custom/agent.py my_custom_agent"
    echo ""
    echo "Note:"
    echo "  - The agent_file_path is used for context and to determine working directory"
    echo "  - Cleanup is primarily based on the agent_name and SSM parameters"
}

# Check parameters
if [ $# -lt 2 ]; then
    print_error "Insufficient parameters provided"
    show_usage
    exit 1
fi

AGENT_FILE_PATH="$1"
AGENT_NAME="$2"

# Convert relative path to absolute path for consistency
if [[ "$AGENT_FILE_PATH" != /* ]]; then
    AGENT_FILE_PATH="$(pwd)/$AGENT_FILE_PATH"
fi

# Extract directory from the agent file path
WORK_DIR="$(dirname "$AGENT_FILE_PATH")"

print_info "🗑️  Starting cleanup process for agent: $AGENT_NAME"
print_info "Agent file path: $AGENT_FILE_PATH"
print_info "Working directory: $WORK_DIR"

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

# Check for agent name in SSM Parameter Store first, fallback to derived value
AGENT_NAME_FROM_SSM=$(aws ssm get-parameter --name "/$AGENT_NAME/runtime/agent_name" --query "Parameter.Value" --output text 2>/dev/null || echo "")

if [ -n "$AGENT_NAME_FROM_SSM" ] && [ "$AGENT_NAME_FROM_SSM" != "None" ]; then
    print_info "Found agent name in SSM Parameter Store: $AGENT_NAME_FROM_SSM"
    AGENT_NAME="$AGENT_NAME_FROM_SSM"
else
    print_info "Agent name not found in SSM Parameter Store, using derived value: $AGENT_NAME"
fi

# Change to working directory if it exists
if [ -d "$WORK_DIR" ]; then
    cd "$WORK_DIR"
    print_info "Changed to agent directory: $WORK_DIR"
else
    print_warning "Agent directory not found: $WORK_DIR"
    print_info "Continuing with cleanup using SSM parameters..."
fi

# Delete .bedrock_agentcore.yaml file if it exists
if [ -f ".bedrock_agentcore.yaml" ]; then
    rm -f ".bedrock_agentcore.yaml"
    print_status ".bedrock_agentcore.yaml deleted"
fi

# Function to get parameter from SSM
get_parameter() {
    local param_name="$1"
    local param_value
    
    param_value=$(aws ssm get-parameter --name "$param_name" --query "Parameter.Value" --output text 2>/dev/null || echo "")
    
    if [ -z "$param_value" ] || [ "$param_value" == "None" ]; then
        print_warning "Parameter $param_name not found or empty"
        return 1
    fi
    
    echo "$param_value"
}

# Function to check if parameter exists
parameter_exists() {
    local param_name="$1"
    aws ssm get-parameter --name "$param_name" >/dev/null 2>&1
}

print_info "📋 Retrieving configuration from Parameter Store..."

# Retrieve all the information from the parameter store
AGENT_ID=""
ECR_REPO_NAME=""
AGENT_ROLE_NAME=""
USER_POOL_ID=""

if parameter_exists "/$AGENT_NAME/runtime/agent_id"; then
    AGENT_ID=$(get_parameter "/$AGENT_NAME/runtime/agent_id")
    if [ $? -eq 0 ]; then
        print_info "Retrieved Agent ID: $AGENT_ID"
    fi
fi

if parameter_exists "/$AGENT_NAME/runtime/user_pool_id"; then
    USER_POOL_ID=$(get_parameter "/$AGENT_NAME/runtime/user_pool_id")
    if [ $? -eq 0 ]; then
        print_info "User Pool ID: $USER_POOL_ID"
    fi
fi

if parameter_exists "/$AGENT_NAME/runtime/ecr_repo_name"; then
    ECR_REPO_NAME=$(get_parameter "/$AGENT_NAME/runtime/ecr_repo_name")
    if [ $? -eq 0 ]; then
        print_info "ECR Repo Name: $ECR_REPO_NAME"
    fi
fi

if parameter_exists "/$AGENT_NAME/runtime/agent_role_name"; then
    AGENT_ROLE_NAME=$(get_parameter "/$AGENT_NAME/runtime/agent_role_name")
    if [ $? -eq 0 ]; then
        print_info "Agent Role Name: $AGENT_ROLE_NAME"
    fi
fi

# Track cleanup success
CLEANUP_ERRORS=0

# Delete AgentCore Runtime
if [ -n "$AGENT_ID" ]; then
    print_info "🤖 Deleting AgentCore Runtime..."
    if aws bedrock-agentcore-control delete-agent-runtime --agent-runtime-id "$AGENT_ID" --region "$REGION" 2>/dev/null; then
        print_status "AgentCore Runtime deletion initiated"
        
        # Wait for deletion to complete
        print_info "Waiting for AgentCore Runtime deletion to complete..."
        DELETION_COMPLETE=false
        WAIT_COUNT=0
        MAX_WAIT=30  # Maximum wait time in iterations (5 minutes)
        
        while [ "$DELETION_COMPLETE" = false ] && [ $WAIT_COUNT -lt $MAX_WAIT ]; do
            sleep 10
            WAIT_COUNT=$((WAIT_COUNT + 1))
            
            # Check if agent still exists
            if ! aws bedrock-agentcore-control get-agent-runtime --agent-runtime-id "$AGENT_ID" --region "$REGION" >/dev/null 2>&1; then
                DELETION_COMPLETE=true
                print_status "AgentCore Runtime deletion completed"
            else
                print_info "Still waiting for deletion... ($WAIT_COUNT/$MAX_WAIT)"
            fi
        done
        
        if [ "$DELETION_COMPLETE" = false ]; then
            print_warning "AgentCore Runtime deletion is taking longer than expected"
            print_info "You may need to check the AWS console for completion status"
        fi
    else
        print_warning "Failed to delete AgentCore Runtime (may not exist or already deleted)"
        CLEANUP_ERRORS=$((CLEANUP_ERRORS + 1))
    fi
else
    print_warning "Agent ID not found, skipping AgentCore Runtime deletion"
fi

# Delete ECR repository images
if [ -n "$ECR_REPO_NAME" ]; then
    print_info "📦 Deleting ECR repository images..."
    
    # First, try to delete all images in the repository
    print_info "Removing all images from ECR repository..."
    if aws ecr describe-repositories --repository-names "$ECR_REPO_NAME" --region "$REGION" >/dev/null 2>&1; then
        # Get all image IDs and delete them
        IMAGE_IDS=$(aws ecr list-images --repository-name "$ECR_REPO_NAME" --region "$REGION" --query 'imageIds[*]' --output json 2>/dev/null)
        if [ "$IMAGE_IDS" != "[]" ] && [ -n "$IMAGE_IDS" ]; then
            echo "$IMAGE_IDS" | aws ecr batch-delete-image --repository-name "$ECR_REPO_NAME" --region "$REGION" --image-ids file:///dev/stdin >/dev/null 2>&1
            print_status "ECR images deleted"
        else
            print_info "No images found in ECR repository"
        fi
    else
        print_info "ECR repository not found (may already be deleted)"
    fi
else
    print_warning "ECR repository name not found, skipping ECR deletion"
fi

# Delete Cognito User Pool
if [ -n "$USER_POOL_ID" ]; then
    print_info "👤 Deleting Cognito User Pool..."
    
    # Check if user pool exists
    if aws cognito-idp describe-user-pool --user-pool-id "$USER_POOL_ID" --region "$REGION" >/dev/null 2>&1; then
        if aws cognito-idp delete-user-pool --user-pool-id "$USER_POOL_ID" --region "$REGION" 2>/dev/null; then
            print_status "Cognito User Pool deleted"
        else
            print_warning "Failed to delete Cognito User Pool"
            CLEANUP_ERRORS=$((CLEANUP_ERRORS + 1))
        fi
    else
        print_warning "Cognito User Pool not found (may already be deleted)"
    fi
else
    print_warning "User Pool ID not found, skipping Cognito deletion"
fi

# Clean up SSM parameters
print_info "🧹 Cleaning up SSM parameters..."
PARAMETERS=(
    "/$AGENT_NAME/runtime/agent_id"
    "/$AGENT_NAME/runtime/agent_arn"    
    "/$AGENT_NAME/runtime/user_pool_id"
    "/$AGENT_NAME/runtime/client_id"
    "/$AGENT_NAME/runtime/discovery_url"    
)

DELETED_PARAMS=0
for PARAM in "${PARAMETERS[@]}"; do
    if parameter_exists "$PARAM"; then
        if aws ssm delete-parameter --name "$PARAM" --region "$REGION" 2>/dev/null; then
            print_status "Deleted parameter: $PARAM"
            DELETED_PARAMS=$((DELETED_PARAMS + 1))
        else
            print_warning "Failed to delete parameter: $PARAM"
            CLEANUP_ERRORS=$((CLEANUP_ERRORS + 1))
        fi
    fi
done

print_info "Deleted $DELETED_PARAMS SSM parameters"

# Summary
echo ""
print_info "🏁 Cleanup process completed!"

if [ $CLEANUP_ERRORS -eq 0 ]; then
    print_status "All resources cleaned up successfully!"
else
    print_warning "Cleanup completed with $CLEANUP_ERRORS errors."
    print_info "Some resources may need to be manually cleaned up."
    print_info "Check the output above for details."
fi

echo ""
print_info "📋 Cleanup Summary:"
print_info "   Agent File Path: $AGENT_FILE_PATH"
print_info "   Agent Name: $AGENT_NAME"
print_info "   - AgentCore Runtime: $([ -n "$AGENT_ID" ] && echo "Processed" || echo "Skipped")"
print_info "   - ECR Repository: $([ -n "$ECR_REPO_NAME" ] && echo "Processed" || echo "Skipped")"
print_info "   - Cognito User Pool: $([ -n "$USER_POOL_ID" ] && echo "Processed" || echo "Skipped")"
print_info "   - Secrets Manager: Processed"
print_info "   - SSM Parameters: $DELETED_PARAMS deleted"
echo ""

if [ $CLEANUP_ERRORS -gt 0 ]; then
    print_info "💡 Note: Some errors are expected if resources were already deleted"
    print_info "or if this is a partial cleanup. Review the output above."
    exit 1
else
    print_status "🎉 All done! Your AgentCore deployment has been cleaned up."
    exit 0
fi