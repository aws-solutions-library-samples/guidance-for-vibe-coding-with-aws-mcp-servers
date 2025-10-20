#!/bin/bash

# Vite Dev Server Security Group Updater
# Opens port 5173 for the participant's IP address and CloudFront access
# For AWS-furnished VSCode environments only

set -euo pipefail

# Configuration
VITE_PORT=5173
PARTICIPANT_IP="${1:-}"
INSTANCE_NAME="CodeServer"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Simple logging function
log_msg() {
    local level=$1
    local msg=$2
    case $level in
        "ERROR")
            echo -e "${RED}[ERROR]${NC} ${msg}" >&2
            ;;
        "SUCCESS")
            echo -e "${GREEN}[SUCCESS]${NC} ${msg}"
            ;;
        "INFO")
            echo -e "${BLUE}[INFO]${NC} ${msg}"
            ;;
        "WARN")
            echo -e "${YELLOW}[WARN]${NC} ${msg}"
            ;;
    esac
}

# Show usage
if [[ $# -eq 0 ]] || [[ "$1" == "--help" ]] || [[ "$1" == "-h" ]]; then
    echo "Usage: $0 <your-public-ip-address>"
    echo "Example: $0 76.88.122.94"
    echo ""
    echo "This script opens port 5173 for Vite dev server access."
    echo "It adds TWO security group rules:"
    echo "  1. Port 5173 from YOUR IP (for direct browser access)"
    echo "  2. Port range 80-5173 from CloudFront (for proxied access)"
    echo ""
    echo "To find your public IP, visit: https://ifconfig.me"
    echo ""
    echo "Note: This script is only needed when using an AWS-furnished VSCode environment."
    echo "      If you're using your own local machine, you don't need this script."
    exit 0
fi

# Validate IP format
if [[ ! $PARTICIPANT_IP =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
    log_msg "ERROR" "Invalid IP format: $PARTICIPANT_IP"
    exit 1
fi

log_msg "INFO" "Starting Vite dev server security group update for IP: $PARTICIPANT_IP"

# Check prerequisites
if ! command -v aws &> /dev/null; then
    log_msg "ERROR" "AWS CLI not found"
    exit 1
fi

# Get instance details using AWS CLI (metadata endpoint doesn't work in this environment)
log_msg "INFO" "Detecting instance information..."
INSTANCE_INFO=$(aws ec2 describe-instances --region us-west-2 \
  --filters "Name=tag:Name,Values=$INSTANCE_NAME" "Name=instance-state-name,Values=running" \
  --query 'Reservations[0].Instances[0].[InstanceId,PublicIpAddress,SecurityGroups[0].GroupId,Placement.AvailabilityZone]' \
  --output text 2>/dev/null)

if [[ -z "$INSTANCE_INFO" ]]; then
    log_msg "ERROR" "Failed to find running instance with name: $INSTANCE_NAME"
    exit 1
fi

# Parse the instance information
INSTANCE_ID=$(echo "$INSTANCE_INFO" | awk '{print $1}')
EC2_PUBLIC_IP=$(echo "$INSTANCE_INFO" | awk '{print $2}')
SG_ID=$(echo "$INSTANCE_INFO" | awk '{print $3}')
AZ=$(echo "$INSTANCE_INFO" | awk '{print $4}')
REGION=$(echo "$AZ" | sed 's/[a-z]$//')

log_msg "SUCCESS" "Instance ID: $INSTANCE_ID"
log_msg "SUCCESS" "Region: $REGION"
log_msg "SUCCESS" "Security Group: $SG_ID"
log_msg "SUCCESS" "EC2 Public IP: $EC2_PUBLIC_IP"

# Get CloudFront prefix list ID for the region
case "$REGION" in
    us-west-2) CF_PREFIX_LIST="pl-82a045eb" ;;
    us-east-1) CF_PREFIX_LIST="pl-3b927c52" ;;
    us-east-2) CF_PREFIX_LIST="pl-b6a144df" ;;
    us-west-1) CF_PREFIX_LIST="pl-4ea04527" ;;
    eu-west-1) CF_PREFIX_LIST="pl-4fa04526" ;;
    eu-west-2) CF_PREFIX_LIST="pl-93a247fa" ;;
    eu-central-1) CF_PREFIX_LIST="pl-a3a144ca" ;;
    ap-southeast-1) CF_PREFIX_LIST="pl-31a34658" ;;
    ap-southeast-2) CF_PREFIX_LIST="pl-b8a742d1" ;;
    ap-northeast-1) CF_PREFIX_LIST="pl-58a04531" ;;
    *)
        log_msg "WARN" "CloudFront prefix list not configured for region $REGION"
        CF_PREFIX_LIST=""
        ;;
esac

# Get existing port 5173 rules
log_msg "INFO" "Checking for existing port $VITE_PORT rules..."
EXISTING_RULES=$(aws ec2 describe-security-groups --region "$REGION" --group-ids "$SG_ID" --query "SecurityGroups[0].IpPermissions[?FromPort==\`$VITE_PORT\` && ToPort==\`$VITE_PORT\`].IpRanges[].CidrIp" --output text 2>/dev/null | tr '\t' '\n' | grep -v '^$' || true)

# Remove existing port 5173 rules if any
if [[ -n "$EXISTING_RULES" ]]; then
    log_msg "INFO" "Removing existing port $VITE_PORT rules..."
    while IFS= read -r cidr; do
        if [[ -n "$cidr" ]]; then
            echo "  Removing: $cidr"
            aws ec2 revoke-security-group-ingress --region "$REGION" --group-id "$SG_ID" --protocol tcp --port "$VITE_PORT" --cidr "$cidr" >/dev/null 2>&1 || true
        fi
    done <<< "$EXISTING_RULES"
fi

# Add Rule 1: Direct access for participant's IP
log_msg "INFO" "Adding port $VITE_PORT access for $PARTICIPANT_IP/32..."
if aws ec2 authorize-security-group-ingress \
    --region "$REGION" \
    --group-id "$SG_ID" \
    --protocol tcp \
    --port "$VITE_PORT" \
    --cidr "$PARTICIPANT_IP/32" >/dev/null 2>&1; then
    log_msg "SUCCESS" "Port $VITE_PORT access granted for $PARTICIPANT_IP/32"
else
    log_msg "ERROR" "Failed to add port $VITE_PORT access for $PARTICIPANT_IP/32"
    exit 1
fi

# Add Rule 2: CloudFront access for port range 80-5173
# If security group is at limit, we need to replace the existing port 80 rule
if [[ -n "$CF_PREFIX_LIST" ]]; then
    log_msg "INFO" "Adding CloudFront access for port range 80-$VITE_PORT..."
    set +e  # Temporarily disable exit on error
    RULE2_OUTPUT=$(aws ec2 authorize-security-group-ingress \
        --region "$REGION" \
        --group-id "$SG_ID" \
        --ip-permissions "[{\"IpProtocol\":\"tcp\",\"FromPort\":80,\"ToPort\":$VITE_PORT,\"PrefixListIds\":[{\"PrefixListId\":\"$CF_PREFIX_LIST\"}]}]" 2>&1)
    RULE2_EXIT=$?
    set -e  # Re-enable exit on error
    
    if [[ $RULE2_EXIT -eq 0 ]]; then
        log_msg "SUCCESS" "CloudFront access granted for port range 80-$VITE_PORT"
    elif echo "$RULE2_OUTPUT" | grep -q "InvalidPermission.Duplicate"; then
        log_msg "SUCCESS" "CloudFront port range rule already exists (no action needed)"
    elif echo "$RULE2_OUTPUT" | grep -q "RulesPerSecurityGroupLimitExceeded"; then
        log_msg "WARN" "Security group at rule limit. Replacing port 80 rule with port range 80-$VITE_PORT..."
        # Remove existing port 80 CloudFront rule
        aws ec2 revoke-security-group-ingress \
            --region "$REGION" \
            --group-id "$SG_ID" \
            --ip-permissions "[{\"IpProtocol\":\"tcp\",\"FromPort\":80,\"ToPort\":80,\"PrefixListIds\":[{\"PrefixListId\":\"$CF_PREFIX_LIST\"}]}]" >/dev/null 2>&1 || true
        # Add port range 80-5173 CloudFront rule
        if aws ec2 authorize-security-group-ingress \
            --region "$REGION" \
            --group-id "$SG_ID" \
            --ip-permissions "[{\"IpProtocol\":\"tcp\",\"FromPort\":80,\"ToPort\":$VITE_PORT,\"PrefixListIds\":[{\"PrefixListId\":\"$CF_PREFIX_LIST\"}]}]" >/dev/null 2>&1; then
            log_msg "SUCCESS" "Replaced port 80 rule with port range 80-$VITE_PORT"
        else
            log_msg "ERROR" "Failed to replace CloudFront rule"
        fi
    else
        log_msg "WARN" "CloudFront port range rule not added."
        echo "  Error: $RULE2_OUTPUT"
    fi
fi

echo ""
log_msg "SUCCESS" "Script completed successfully!"
echo ""
echo "  Access your Vite dev server at:"
echo "  → http://$EC2_PUBLIC_IP:5173"
echo ""
