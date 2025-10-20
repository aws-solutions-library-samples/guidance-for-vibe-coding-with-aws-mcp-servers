#!/usr/bin/env python3
"""
Local test script for MCP server functions using Bruno test data.

This script tests the actual MCP server functions from hotel_booking_support.py
using Bruno API configuration instead of Parameter Store.

⚠️ SETUP REQUIRED:
Before running this script, you must:
1. Deploy the AgentCoreTechSummitMockApis CDK stack
2. Get the API URLs from CloudFormation stack outputs
3. Get the API keys from AWS API Gateway console
4. Replace the placeholder values in BrunoConfig.__init__()
"""

import logging
import os
import sys
from typing import Any


# Add parent directory to path to import from common modules
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class BrunoConfig:
    """Configuration class using Bruno test data instead of Parameter Store."""

    def __init__(self):
        """Initialize with Bruno test values."""
        # TODO: Replace with actual API URLs from your deployed stack
        # Get these values from:
        # 1. AWS CloudFormation stack outputs after deployment
        # 2. Bruno API test collection environment variables
        # 3. CDK deployment outputs

        # Bruno PropertyResolution values - REPLACE WITH YOUR DEPLOYED API
        self.property_resolution_api_url = (
            "https://YOUR_PROPERTY_API_ID.execute-api.YOUR_REGION.amazonaws.com/dev/api/v1"
        )
        self.property_resolution_api_key = "YOUR_PROPERTY_RESOLUTION_API_KEY"

        # Bruno Reservations values - REPLACE WITH YOUR DEPLOYED API
        self.reservation_services_api_url = (
            "https://YOUR_RESERVATION_API_ID.execute-api.YOUR_REGION.amazonaws.com/dev/api/v1"
        )
        self.reservation_services_api_key = "no-key-required"

        # Toxicity detection disabled for local testing
        self.toxicity_detection_api_url = None
        self.toxicity_detection_api_key = None
        self.toxicity_detection_enabled = False

        logger.info("✅ Bruno configuration initialized")
        logger.info(f"Property Resolution URL: {self.property_resolution_api_url}")
        logger.info(f"Reservation Services URL: {self.reservation_services_api_url}")

    def get_property_resolution_config(self) -> dict:
        """Get Property Resolution API configuration."""
        return {
            "base_url": self.property_resolution_api_url,
            "api_key": self.property_resolution_api_key,
            "headers": {"Content-Type": "application/json", "X-Api-Key": self.property_resolution_api_key},
        }

    def get_reservation_services_config(self) -> dict:
        """Get Reservation Services API configuration."""
        headers = {"Content-Type": "application/json"}
        if self.reservation_services_api_key != "no-key-required":
            headers["X-Api-Key"] = self.reservation_services_api_key

        return {
            "base_url": self.reservation_services_api_url,
            "api_key": self.reservation_services_api_key,
            "headers": headers,
        }


class BrunoHotelBookingService:
    """Wrapper to test actual MCP server functions with Bruno configuration."""

    def __init__(self):
        """Initialize with Bruno configuration and import MCP server code."""
        # Import the actual MCP server service
        try:
            from common.hotel_booking_support import HotelBookingService

            # Create the actual service instance
            self.actual_service = HotelBookingService()

            # Replace its configuration with Bruno values
            bruno_config = BrunoConfig()
            self.actual_service.property_config = bruno_config.get_property_resolution_config()
            self.actual_service.reservation_config = bruno_config.get_reservation_services_config()

            logger.info("✅ MCP server service initialized with Bruno configuration")

        except ImportError as e:
            logger.error(f"❌ Failed to import MCP server code: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Failed to initialize MCP server service: {e}")
            raise

    def search_properties(
        self, location: str, check_in_date: str, check_out_date: str, guests: int = 2, min_rating: float = 0.0
    ) -> dict[str, Any]:
        """Test the actual MCP server search_properties function."""
        logger.info("🏨 Testing MCP server search_properties function")
        logger.info(f"📍 Location: {location}, Guests: {guests}")
        logger.info(f"📅 Check-in: {check_in_date}, Check-out: {check_out_date}")

        # Call the actual MCP server function
        result = self.actual_service.search_properties(location, check_in_date, check_out_date, guests, min_rating)

        logger.info(f"📊 MCP server function result: {result.get('status')}")
        return result

    def create_reservation(
        self,
        hotel_id: str,
        room_type: str,
        check_in_date: str,
        check_out_date: str,
        guest_name: str,
        guest_email: str,
        guests: int = 2,
        special_requests: str = "",
    ) -> dict[str, Any]:
        """Test the actual MCP server create_reservation function."""
        logger.info("🏨 Testing MCP server create_reservation function")
        logger.info(f"🏨 Hotel ID: {hotel_id}, Room: {room_type}")
        logger.info(f"👤 Guest: {guest_name} ({guest_email})")
        logger.info(f"📅 {check_in_date} to {check_out_date}, {guests} guests")

        # Call the actual MCP server function
        result = self.actual_service.create_reservation(
            hotel_id, room_type, check_in_date, check_out_date, guest_name, guest_email, guests, special_requests
        )

        logger.info(f"📊 MCP server function result: {result.get('status')}")
        return result


def test_property_search():
    """Test property search functionality."""
    print("\n" + "=" * 60)
    print("🏨 TESTING PROPERTY SEARCH")
    print("=" * 60)

    service = BrunoHotelBookingService()

    # Test search
    result = service.search_properties(
        location="Bei San Francisco", check_in_date="2025-06-15", check_out_date="2025-06-20", guests=2
    )

    print("\n📊 RESULT:")
    print(f"Status: {result.get('status')}")
    if result.get("status") == "success":
        print(f"Hotels found: {result.get('hotels_found')}")
        hotels = result.get("hotels", [])
        for i, hotel in enumerate(hotels[:3]):  # Show first 3
            print(f"  {i + 1}. Hotel ID: {hotel.get('hotel_id')}, Rank: {hotel.get('rank')}")
            metadata = hotel.get("metadata", {})
            if metadata:
                print(f"     Name: {metadata.get('property_name', 'N/A')}")
    else:
        print(f"Error: {result.get('message')}")

    return result


def test_reservation_creation():
    """Test reservation creation functionality."""
    print("\n" + "=" * 60)
    print("🏨 TESTING RESERVATION CREATION")
    print("=" * 60)

    service = BrunoHotelBookingService()

    # Test reservation
    result = service.create_reservation(
        hotel_id="10001",
        room_type="B1K",
        check_in_date="2025-06-15",
        check_out_date="2025-06-20",
        guest_name="Test User",
        guest_email="test@example.com",
        guests=2,
    )

    print("\n📊 RESULT:")
    print(f"Status: {result.get('status')}")
    if result.get("status") == "success":
        print(f"Message: {result.get('message')}")
        booking = result.get("booking", {})
        if booking:
            print(f"Booking details available: {len(booking)} fields")
    else:
        print(f"Error: {result.get('message')}")

    return result


def main():
    """Run all tests."""
    print("🚀 Starting Bruno-based local MCP server tests...")

    try:
        # Test 1: Property Search
        search_result = test_property_search()

        # Test 2: Reservation Creation
        reservation_result = test_reservation_creation()

        # Summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"Property Search: {'✅ PASS' if search_result.get('status') == 'success' else '❌ FAIL'}")
        print(f"Reservation Creation: {'✅ PASS' if reservation_result.get('status') == 'success' else '❌ FAIL'}")

        if search_result.get("status") == "success" and reservation_result.get("status") == "success":
            print("\n🎉 All tests passed! MCP server functions work with Bruno API configuration.")
        else:
            print("\n⚠️  Some tests failed. Check the logs above for details.")

    except Exception as e:
        logger.error(f"❌ Test execution failed: {str(e)}")
        print(f"\n❌ Test execution failed: {str(e)}")


if __name__ == "__main__":
    main()
