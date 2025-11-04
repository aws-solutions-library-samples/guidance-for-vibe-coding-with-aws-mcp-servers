#!/bin/bash

# Script to set AWS credentials for Bruno testing
# This script exports AWS credentials as environment variables that Bruno can use for SigV4 signing

echo "==================================================================="
echo "AWS Credential Helper for Bruno Testing"
echo "==================================================================="

# Check if credentials are already in environment (Workshop Studio case)
if [ -n "$AWS_ACCESS_KEY_ID" ] && [ -n "$AWS_SECRET_ACCESS_KEY" ]; then
    echo "✓ Using existing AWS credentials from environment"
    echo ""
    echo "You can now run Bruno tests with AWS SigV4 authentication!"
    echo "==================================================================="
    return 0
fi

# Get the AWS profile from environment or use default
PROFILE="${AWS_PROFILE:-default}"
echo "Using AWS Profile: $PROFILE"
echo ""

# Try to get credentials from AWS configuration
AWS_ACCESS_KEY_ID=$(aws configure get aws_access_key_id --profile $PROFILE 2>/dev/null)
AWS_SECRET_ACCESS_KEY=$(aws configure get aws_secret_access_key --profile $PROFILE 2>/dev/null)
AWS_SESSION_TOKEN=$(aws configure get aws_session_token --profile $PROFILE 2>/dev/null)

# Check if we got basic credentials
if [ -z "$AWS_ACCESS_KEY_ID" ] || [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
    echo "Basic credentials not found in profile '$PROFILE'."
    echo "Attempting to get credentials from SSO or temporary credentials..."
    echo ""
    
    # Check if SSO is configured and try to get credentials
    ACCOUNT_ID=$(aws sts get-caller-identity --profile $PROFILE --query 'Account' --output text 2>/dev/null)
    
    if [ $? -eq 0 ]; then
        echo "✓ Successfully authenticated with AWS"
        echo "  Account ID: $ACCOUNT_ID"
        
        # Export credentials using aws configure export-credentials (for SSO/assumed roles)
        echo ""
        echo "Exporting credentials from AWS profile..."
        
        # Export credentials in a format we can parse
        TEMP_CREDS=$(aws configure export-credentials --profile $PROFILE --format env-no-export 2>/dev/null)
        
        if [ $? -eq 0 ]; then
            # Parse the credentials from the output
            eval "$TEMP_CREDS"
            echo "✓ Credentials exported successfully"
        else
            echo "⚠ Failed to export credentials. Trying alternate method..."
            
            # Alternate method: Get credentials via STS assume-role or get-session-token
            CREDS_JSON=$(aws sts get-session-token --profile $PROFILE --output json 2>/dev/null)
            
            if [ $? -eq 0 ]; then
                AWS_ACCESS_KEY_ID=$(echo $CREDS_JSON | jq -r '.Credentials.AccessKeyId')
                AWS_SECRET_ACCESS_KEY=$(echo $CREDS_JSON | jq -r '.Credentials.SecretAccessKey')
                AWS_SESSION_TOKEN=$(echo $CREDS_JSON | jq -r '.Credentials.SessionToken')
                echo "✓ Obtained temporary credentials via STS"
            fi
        fi
    else
        echo "✗ Failed to authenticate with AWS"
        echo ""
        echo "Please ensure you are logged in to AWS:"
        echo "  - For SSO: aws sso login --profile $PROFILE"
        echo "  - For IAM: Check your credentials in ~/.aws/credentials"
        return 1
    fi
fi

# Export the credentials as environment variables
export AWS_ACCESS_KEY_ID
export AWS_SECRET_ACCESS_KEY
export AWS_SESSION_TOKEN

# Verify credentials are set
if [ -n "$AWS_ACCESS_KEY_ID" ] && [ -n "$AWS_SECRET_ACCESS_KEY" ]; then
    echo ""
    echo "==================================================================="
    echo "✓ AWS Credentials Set Successfully!"
    echo "==================================================================="
    echo ""
    echo "Credentials exported for Bruno testing:"
    echo "  AWS_ACCESS_KEY_ID: ${AWS_ACCESS_KEY_ID:0:10}..."
    echo "  AWS_SECRET_ACCESS_KEY: ****"
    if [ -n "$AWS_SESSION_TOKEN" ]; then
        echo "  AWS_SESSION_TOKEN: ${AWS_SESSION_TOKEN:0:20}..."
    fi
    echo ""
    echo "You can now run Bruno tests with AWS SigV4 authentication!"
    echo ""
    echo "To run Bruno tests from this terminal:"
    echo "  1. Open Bruno from this terminal session"
    echo "  2. Or run: bruno run PropertyResolution/"
    echo ""
    echo "Note: These credentials are only available in this terminal session."
    echo "==================================================================="
else
    echo ""
    echo "✗ Failed to set AWS credentials"
    echo ""
    echo "Please check your AWS configuration and try again."
    return 1
fi
