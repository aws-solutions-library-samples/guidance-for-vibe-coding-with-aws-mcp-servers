"""
Test suite for Hotel Booking MCP Server.
"""

import boto3
import json
import requests
import sys
from boto3.session import Session
from pathlib import Path


# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "common"))
from cognito_token_manager import CognitoTokenManager


def setup_mcp_connection():
    """Setup MCP server connection details."""
    print("\n🔍 Setting up MCP Server Connection...")

    try:
        boto_session = Session()
        region = boto_session.region_name
        print(f"✅ Using AWS region: {region}")

        # Get agent ARN from Parameter Store
        ssm_client = boto3.client("ssm", region_name=region)
        agent_arn_response = ssm_client.get_parameter(Name="/hotel_booking_mcp/runtime/agent_arn")
        agent_arn = agent_arn_response["Parameter"]["Value"]
        print(f"✅ Retrieved Agent ARN: {agent_arn}")

        # Setup URL
        encoded_arn = agent_arn.replace(":", "%3A").replace("/", "%2F")
        url = f"https://bedrock-agentcore.{region}.amazonaws.com/runtimes/{encoded_arn}/invocations?qualifier=DEFAULT"
        print(f"✅ MCP URL: {url}")

        # Get bearer token
        token_manager = CognitoTokenManager(secret_name="hotel_booking_mcp/cognito/credentials")
        bearer_token = token_manager.get_fresh_token()
        print("✅ Retrieved bearer token")

        # Setup headers
        headers = {
            "authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }

        return url, headers, True

    except Exception as e:
        print(f"❌ MCP connection setup error: {e}")
        return None, None, False


def test_mcp_list_tools(url, headers):
    """Test MCP list_tools functionality."""
    print("\n🔍 Testing MCP List Tools...")

    try:
        mcp_request = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}

        response = requests.post(url, headers=headers, json=mcp_request, timeout=30)

        print(f"Response Status: {response.status_code}")

        if response.status_code == 200:
            response_text = response.text.strip()

            # Extract JSON from SSE format
            if response_text.startswith("event: message\ndata: "):
                json_data = response_text.replace("event: message\ndata: ", "")
            elif "data: " in response_text:
                lines = response_text.split("\n")
                for line in lines:
                    if line.startswith("data: "):
                        json_data = line.replace("data: ", "")
                        break
                else:
                    json_data = response_text
            else:
                json_data = response_text

            response_data = json.loads(json_data)

            if "result" in response_data and "tools" in response_data["result"]:
                tools = response_data["result"]["tools"]
                print(f"✅ Found {len(tools)} tools available")

                expected_tools = [
                    "search_properties",
                    "create_reservation",
                    "get_booking_details",
                    "cancel_booking",
                    "get_booking_history",
                    "check_room_availability",
                    "validate_payment_details",
                    "modify_reservation",
                ]

                available_tool_names = [tool["name"] for tool in tools]
                for expected_tool in expected_tools:
                    if expected_tool in available_tool_names:
                        print(f"✅ Tool available: {expected_tool}")
                    else:
                        print(f"⚠️  Tool missing: {expected_tool}")

                return True, tools
            else:
                print(f"❌ Invalid response format: {response_data}")
                return False, []
        else:
            print(f"❌ HTTP Error {response.status_code}: {response.text}")
            return False, []

    except Exception as e:
        print(f"❌ List tools error: {e}")
        return False, []


def test_mcp_tool_call(url, headers, tool_name, arguments):
    """Test calling a specific MCP tool."""
    try:
        mcp_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }

        response = requests.post(url, headers=headers, json=mcp_request, timeout=30)

        if response.status_code == 200:
            response_text = response.text.strip()

            # Extract JSON from SSE format
            if response_text.startswith("event: message\ndata: "):
                json_data = response_text.replace("event: message\ndata: ", "")
            elif "data: " in response_text:
                lines = response_text.split("\n")
                for line in lines:
                    if line.startswith("data: "):
                        json_data = line.replace("data: ", "")
                        break
                else:
                    json_data = response_text
            else:
                json_data = response_text

            response_data = json.loads(json_data)

            if "result" in response_data:
                result = response_data["result"]
                if "content" in result and result["content"]:
                    content = result["content"][0]
                    if "text" in content:
                        tool_response = json.loads(content["text"])

                        if "status" in tool_response:
                            if tool_response["status"] == "success":
                                print(f"✅ {tool_name}: SUCCESS")
                                return True, tool_response
                            elif tool_response["status"] == "error":
                                print(f"⚠️  {tool_name}: ERROR - {tool_response.get('message', 'Unknown error')}")
                                return True, tool_response
                            else:
                                print(f"❓ {tool_name}: UNEXPECTED STATUS - {tool_response['status']}")
                                return True, tool_response
                        else:
                            print(f"✅ {tool_name}: RESPONSE RECEIVED")
                            return True, tool_response
                    else:
                        print(f"✅ {tool_name}: TOOL EXECUTED")
                        return True, {}
                else:
                    print(f"❌ {tool_name}: NO RESPONSE CONTENT")
                    return False, {}
            else:
                print(f"❌ {tool_name}: Invalid response format")
                return False, {}
        else:
            print(f"❌ {tool_name}: HTTP Error {response.status_code}")
            return False, {}

    except Exception as e:
        print(f"❌ {tool_name}: FAILED - {str(e)}")
        return False, {}


def test_mcp_tools_with_mock_data(url, headers, tools):  # noqa: ARG001
    """Test all MCP tools with mock input data."""
    print("\n🔍 Testing MCP Tools with Mock Data...")

    successful_tests = 0
    failed_tests = 0
    created_booking_id = None

    # Test 1: Search properties
    print("\n🔧 Testing tool: search_properties")
    search_data = {
        "location": "Seattle, WA",
        "check_in_date": "2025-12-01",
        "check_out_date": "2025-12-05",
        "guests": 2,
        "min_rating": 4.0,
    }
    success, response = test_mcp_tool_call(url, headers, "search_properties", search_data)
    if success:
        successful_tests += 1
    else:
        failed_tests += 1

    # Test 2: Create reservation
    print("\n🔧 Testing tool: create_reservation")
    create_data = {
        "hotel_id": "hotel_123",
        "guest_name": "Test User",
        "guest_email": "test@example.com",
        "check_in_date": "2025-12-01",
        "check_out_date": "2025-12-05",
        "room_type": "deluxe",
        "guests": 2,
        "special_requests": "Late check-in",
    }
    success, response = test_mcp_tool_call(url, headers, "create_reservation", create_data)
    if success and response.get("status") == "success":
        created_booking_id = response.get("booking_id")
        print(f"✅ create_reservation: Created booking {created_booking_id}")
        successful_tests += 1
    else:
        failed_tests += 1

    if not created_booking_id:
        print("\n⚠️  Cannot continue tests without booking ID")
        return successful_tests, failed_tests

    # Test 3: Get booking details
    print("\n🔧 Testing tool: get_booking_details")
    success, _ = test_mcp_tool_call(url, headers, "get_booking_details", {"booking_id": created_booking_id})
    if success:
        successful_tests += 1
    else:
        failed_tests += 1

    # Test 4: Check room availability
    print("\n🔧 Testing tool: check_room_availability")
    availability_data = {
        "hotel_id": "hotel_123",
        "check_in_date": "2025-12-10",
        "check_out_date": "2025-12-15",
        "room_type": "deluxe",
    }
    success, _ = test_mcp_tool_call(url, headers, "check_room_availability", availability_data)
    if success:
        successful_tests += 1
    else:
        failed_tests += 1

    # Test 5: Validate payment details
    print("\n🔧 Testing tool: validate_payment_details")
    payment_data = {
        "payment_info": {
            "card_number": "4111111111111111",
            "expiry_date": "12/26",
            "cvv": "123",
            "cardholder_name": "Test User",
        }
    }
    success, _ = test_mcp_tool_call(url, headers, "validate_payment_details", payment_data)
    if success:
        successful_tests += 1
    else:
        failed_tests += 1

    # Test 6: Modify reservation
    print("\n🔧 Testing tool: modify_reservation")
    modify_data = {
        "booking_id": created_booking_id,
        "check_out_date": "2025-12-06",
        "special_requests": "Updated: Late check-in and early breakfast",
    }
    success, _ = test_mcp_tool_call(url, headers, "modify_reservation", modify_data)
    if success:
        successful_tests += 1
    else:
        failed_tests += 1

    # Test 7: Get booking history
    print("\n🔧 Testing tool: get_booking_history")
    success, _ = test_mcp_tool_call(url, headers, "get_booking_history", {"guest_email": "test@example.com"})
    if success:
        successful_tests += 1
    else:
        failed_tests += 1

    # Test 8: Cancel booking
    print("\n🔧 Testing tool: cancel_booking")
    cancel_data = {"booking_id": created_booking_id, "reason": "Test cancellation"}
    success, _ = test_mcp_tool_call(url, headers, "cancel_booking", cancel_data)
    if success:
        successful_tests += 1
    else:
        failed_tests += 1

    print("\n📊 Tool Testing Summary:")
    print(f"✅ Successful: {successful_tests}")
    print(f"❌ Failed: {failed_tests}")
    print(f"📋 Total: {successful_tests + failed_tests}")

    return successful_tests, failed_tests


def run_comprehensive_test():
    """Run the complete test suite."""
    print("🚀 Hotel Booking MCP Server - Comprehensive Test Suite")
    print("=" * 60)

    # Test 1: MCP Connection Setup
    url, headers, connection_success = setup_mcp_connection()
    if not connection_success:
        print("\n❌ MCP connection setup failed. Stopping tests.")
        return False

    # Test 2: MCP List Tools
    tools_success, tools = test_mcp_list_tools(url, headers)
    if not tools_success:
        print("\n❌ MCP list tools failed. Stopping tests.")
        return False

    # Test 3: Tool Testing
    successful_tools, failed_tools = test_mcp_tools_with_mock_data(url, headers, tools)

    # Final Summary
    print("\n" + "=" * 60)
    print("🎉 COMPREHENSIVE TEST RESULTS")
    print("=" * 60)
    print(f"✅ MCP Connection Setup: {'PASS' if connection_success else 'FAIL'}")
    print(f"✅ MCP Tools Available: {len(tools)}/8")
    print(f"✅ Tools Tested Successfully: {successful_tools}")
    print(f"❌ Tools Failed: {failed_tools}")

    overall_success = connection_success and len(tools) >= 8 and failed_tools == 0

    if overall_success:
        print("\n🎉 ALL TESTS PASSED! MCP Server is fully functional.")
    else:
        print("\n⚠️  Some tests failed. Check the details above.")

    return overall_success


def main():
    """Main test runner."""
    try:
        success = run_comprehensive_test()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n💥 Unexpected error during testing: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
