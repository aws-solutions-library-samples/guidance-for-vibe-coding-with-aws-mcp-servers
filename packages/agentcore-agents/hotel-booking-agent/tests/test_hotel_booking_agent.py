import boto3
import json
import os
import requests
import sys
from boto3.session import Session


# Add parent directory to path to import from common and memory modules
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from common.cognito_token_manager import CognitoTokenManager  # noqa: E402


boto_session = Session()
region = boto_session.region_name

print(f"Using AWS region: {region}")

agentcore_client = boto3.client("bedrock-agentcore", region_name=region)

try:
    ssm_client = boto3.client("ssm", region_name=region)
    agent_arn_response = ssm_client.get_parameter(Name="/hotel_booking_agent/runtime/agent_arn")
    agent_arn = agent_arn_response["Parameter"]["Value"]
    print(f"Retrieved Agent ARN: {agent_arn}")

except Exception as e:
    print(f"Error retrieving credentials: {e}")
    sys.exit(1)

if not agent_arn:
    print("Error: AGENT_ARN not retrieved properly")
    sys.exit(1)

encoded_arn = agent_arn.replace(":", "%3A").replace("/", "%2F")
url = f"https://bedrock-agentcore.{region}.amazonaws.com/runtimes/{encoded_arn}/invocations"
print(f"Using URL: {url}")
# Initialize token manager and get fresh bearer token
token_manager = CognitoTokenManager(secret_name="hotel_booking_agent/cognito/credentials")
bearer_token = token_manager.get_fresh_token()
print("✓ Retrieved bearer token refreshed.")

endpoint_name = "DEFAULT"
headers = {
    "authorization": f"Bearer {bearer_token}",
    # "X-Amzn-Trace-Id": "your-trace-id",
    "Content-Type": "application/json",
    # "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id": "testsession123"
}

# url="http://0.0.0.0:8080/invocations"
# headers = {"Content-Type": "application/json"}

prompt = "How many hotels available on 15th Aug 2025?"
payload = json.dumps({"prompt": prompt, "conversation_id": "2dd227fa-81a9-44af-aa13-8bdb04c057ca", "chat_history": ""})

invoke_response = requests.post(url, headers=headers, data=payload)

# Print response in a safe manner
print(f"Status Code: {invoke_response.status_code}")
print(f"Response Headers: {dict(invoke_response.headers)}")

# Handle response based on status code
if invoke_response.status_code == 200:
    response_data = invoke_response.json()
    print("Response JSON:")
    print(json.dumps(response_data, indent=2))
elif invoke_response.status_code >= 400:
    print(f"Error Response ({invoke_response.status_code}):")
    error_data = invoke_response.json()
    print(json.dumps(error_data, indent=2))

else:
    print(f"Unexpected status code: {invoke_response.status_code}")
    print("Response text:")
    print(invoke_response.text[:500])
