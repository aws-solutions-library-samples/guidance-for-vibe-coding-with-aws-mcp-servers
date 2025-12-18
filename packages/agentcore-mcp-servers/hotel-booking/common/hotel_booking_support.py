"""
Hotel Booking Support Module

This module contains all the business logic and API integration
for the hotel booking MCP server. It integrates with real AWS APIs
for property resolution, reservation services, and toxicity detection.
"""

import boto3
import json
import logging
import requests
from .config import config
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from datetime import datetime
from typing import Any


# Configure logging
logger = logging.getLogger(__name__)


class APIError(Exception):
    """Custom exception for API-related errors."""

    pass


class HotelBookingService:
    """Service class for hotel booking operations with real API integration."""

    def __init__(self):
        """Initialize the service with API configurations."""
        self.property_config = config.get_property_resolution_config()
        self.reservation_config = config.get_reservation_services_config()
        # Toxicity detection temporarily disabled
        # self.toxicity_config = config.get_toxicity_detection_config()

        # Initialize AWS session and credentials for SigV4 signing
        try:
            self.session = boto3.Session()
            self.credentials = self.session.get_credentials()
            self.region = self.session.region_name or config.aws_region
            logger.info(f"Initialized AWS session with region: {self.region}")
        except Exception as e:
            logger.warning(f"Could not initialize AWS session: {e}. Will fall back to API key only.")
            self.session = None
            self.credentials = None
            self.region = config.aws_region

    def _make_api_request(
        self, method: str, url: str, headers: dict, data: dict | None = None, timeout: int = 30
    ) -> dict:
        """
        Make an API request with AWS SigV4 signing and error handling.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Full URL for the request
            headers: Request headers
            data: Request payload (for POST requests)
            timeout: Request timeout in seconds

        Returns:
            Response data as dictionary

        Raises:
            APIError: If the request fails
        """
        try:
            logger.info(f"Making {method} request to {url}")

            # Prepare the request body
            body = None
            if data:
                body = json.dumps(data)
                headers["Content-Type"] = "application/json"

            # If we have AWS credentials, sign the request with SigV4
            if self.credentials:
                try:
                    logger.info(f"Attempting SigV4 signing with credentials for region: {self.region}")

                    # Create AWS request for signing
                    aws_request = AWSRequest(method=method.upper(), url=url, data=body, headers=headers)

                    # Sign with SigV4 using the IAM role credentials
                    SigV4Auth(self.credentials, "execute-api", self.region).add_auth(aws_request)

                    # Use the signed headers
                    signed_headers = dict(aws_request.headers)
                    logger.info("✅ Request signed with AWS SigV4")

                    # Log if Authorization header was added (without showing value)
                    if "Authorization" in signed_headers:
                        logger.info("Authorization header present")
                except Exception as e:
                    logger.warning(f"Failed to sign request with SigV4: {e}. Using API key only.")
                    logger.exception("SigV4 signing error details:")
                    signed_headers = headers
            else:
                # No AWS credentials, use headers as-is (API key only)
                logger.warning("No AWS credentials available, using API key only")
                signed_headers = headers

            # Make the actual HTTP request
            if method.upper() == "GET":
                response = requests.get(url, headers=signed_headers, timeout=timeout)
            elif method.upper() == "POST":
                response = requests.post(url, headers=signed_headers, data=body, timeout=timeout)
            elif method.upper() == "PATCH":
                response = requests.patch(url, headers=signed_headers, data=body, timeout=timeout)
            else:
                raise APIError(f"Unsupported HTTP method: {method}")

            # Log response status
            logger.info(f"API response status: {response.status_code}")

            # Check for HTTP errors
            if response.status_code >= 400:
                error_msg = f"API request failed with status {response.status_code}"
                try:
                    error_detail = response.json()
                    error_msg += f": {error_detail}"
                except Exception:
                    error_msg += f": {response.text}"
                raise APIError(error_msg)

            # Parse JSON response
            return response.json()

        except requests.exceptions.Timeout as e:
            raise APIError(f"API request timed out after {timeout} seconds") from e
        except requests.exceptions.ConnectionError as e:
            raise APIError("Failed to connect to API endpoint") from e
        except requests.exceptions.RequestException as e:
            raise APIError(f"API request failed: {str(e)}") from e
        except Exception as e:
            raise APIError(f"Unexpected error during API request: {str(e)}") from e

    def search_properties(
        self, location: str, check_in_date: str, check_out_date: str, guests: int = 2, min_rating: float = 0.0
    ) -> dict[str, Any]:
        """
        Search for available properties using Property Resolution API.

        Args:
            location: Location to search for properties
            check_in_date: Check-in date (YYYY-MM-DD)
            check_out_date: Check-out date (YYYY-MM-DD)
            guests: Number of guests
            min_rating: Minimum property rating

        Returns:
            Dictionary with search results
        """
        try:
            # Prepare search request using actual Property Resolution API format
            search_url = f"{self.property_config['base_url']}/property-resolution"
            search_data = {
                "unique_client_id": "AWS_PACE_Agent",
                "anon_guest_id": "guest_12345",
                "input": {"query": f"{location} check-in {check_in_date} check-out {check_out_date} guests {guests}"},
                "session_context": {
                    "session_id": f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "local_ts": datetime.now().isoformat() + "Z",
                    "country_name": "United States",
                    "region_name": "California",
                    "city_name": location,
                    "user_agent": "Hotel Booking MCP Server",
                },
            }

            # Make API request
            response = self._make_api_request(
                method="POST", url=search_url, headers=self.property_config["headers"], data=search_data
            )

            # Process response - use correct field name from actual API
            properties = response.get("result", [])

            # Calculate nights for pricing
            check_in = datetime.strptime(check_in_date, "%Y-%m-%d")
            check_out = datetime.strptime(check_out_date, "%Y-%m-%d")
            nights = (check_out - check_in).days

            # Transform properties to expected format and add calculated pricing
            hotels = []
            for prop in properties:
                hotel = {
                    "hotel_id": prop.get("hotel_id"),
                    "spirit_cd": prop.get("spirit_cd"),
                    "rank": prop.get("rank"),
                    "metadata": prop.get("metadata", {}),
                    "nights": nights,
                    # Add basic room type info (can be enhanced later)
                    "room_types": {
                        "standard": {
                            "price": 350.0,  # Default price
                            "total_price": 350.0 * nights,
                            "price_per_night": 350.0,
                        }
                    },
                }
                hotels.append(hotel)

            return {
                "status": "success",
                "search_criteria": {
                    "location": location,
                    "check_in": check_in_date,
                    "check_out": check_out_date,
                    "guests": guests,
                    "min_rating": min_rating,
                },
                "hotels_found": len(hotels),
                "hotels": hotels,
            }

        except APIError as e:
            logger.error(f"Property Resolution API error: {str(e)}")
            return {"status": "error", "message": f"Hotel search failed: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error in hotel search: {str(e)}")
            return {"status": "error", "message": f"Hotel search failed: {str(e)}"}

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
        """
        Create a new hotel reservation using Reservation Services API.

        Args:
            hotel_id: Hotel identifier
            room_type: Type of room to book
            check_in_date: Check-in date (YYYY-MM-DD)
            check_out_date: Check-out date (YYYY-MM-DD)
            guest_name: Guest name
            guest_email: Guest email
            guests: Number of guests
            special_requests: Special requests or notes

        Returns:
            Dictionary with reservation confirmation
        """
        try:
            # Prepare booking request using actual Reservation Services API format
            booking_url = f"{self.reservation_config['base_url']}/reservation"

            # Split guest name into first and last name
            name_parts = guest_name.split(" ", 1)
            given_name = name_parts[0] if name_parts else guest_name
            surname = name_parts[1] if len(name_parts) > 1 else ""

            # Convert hotel_id to integer for Mock API compatibility
            try:
                hotel_id_int = int(hotel_id)
            except ValueError:
                return {
                    "status": "error",
                    "message": f"Invalid hotel_id '{hotel_id}'. Must be numeric (e.g., 10001, 10004).",
                }

            booking_data = {
                "BookingInfo": {"BookedBy": guest_name, "BookingDate": datetime.now().strftime("%Y-%m-%d")},
                "Hotel": {"Id": hotel_id_int, "Code": f"H{hotel_id_int}", "Name": f"Hotel {hotel_id_int}"},
                "RoomStay": {
                    "CheckInDate": check_in_date,
                    "CheckOutDate": check_out_date,
                    "GuestCount": [{"NumGuests": guests}],
                    "NumRooms": 1,
                    "Products": [
                        {"Product": {"RoomCode": room_type, "RoomName": room_type}, "Price": {"Amount": 350.0}}
                    ],
                },
                "Guests": [
                    {
                        "PersonName": {"GivenName": given_name, "Surname": surname},
                        "EmailAddress": [{"Type": "Primary", "Value": guest_email}],
                        "ContactNumbers": [{"Number": "5551234567"}],
                    }
                ],
                "status": "Confirmed",
                "Currency": {"Code": "USD", "Name": "US Dollars", "Symbol": "$"},
                "RoomPrices": {
                    "TotalPrice": {
                        "Price": {
                            "CurrencyCode": "USD",
                            "TotalAmount": 1750.0,
                            "TotalAmountIncludingTaxesFees": 1942.50,
                        }
                    }
                },
            }

            if special_requests:
                booking_data["SpecialRequests"] = special_requests

            # Make API request
            response = self._make_api_request(
                method="POST", url=booking_url, headers=self.reservation_config["headers"], data=booking_data
            )

            booking = response.get("reservation", response)

            return {"status": "success", "message": "Booking created successfully", "booking": booking}

        except APIError as e:
            logger.error(f"Reservation Services API error: {str(e)}")
            return {"status": "error", "message": f"Failed to create booking: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error creating booking: {str(e)}")
            return {"status": "error", "message": f"Failed to create booking: {str(e)}"}

    def get_booking_details(self, booking_id: str) -> dict[str, Any]:
        """
        Retrieve details for a specific booking using Reservation Services API.

        Args:
            booking_id: Booking identifier

        Returns:
            Dictionary with booking details
        """
        try:
            # Extract hotel ID from booking ID format: {hotelId}CU{digits}
            # Example: "10004CU156038" -> hotel_id = "10004"
            if "CU" not in booking_id:
                return {
                    "status": "error",
                    "message": f"Invalid booking ID format '{booking_id}'. Expected format: {{hotelId}}CU{{digits}} (e.g., 10004CU156038)",
                }

            hotel_id = booking_id.split("CU")[0]
            if not hotel_id.isdigit():
                return {
                    "status": "error",
                    "message": f"Invalid hotel ID in booking ID '{booking_id}'. Hotel ID must be numeric.",
                }

            booking_url = f"{self.reservation_config['base_url']}/reservation/hotel/{hotel_id}/{booking_id}"

            response = self._make_api_request(method="GET", url=booking_url, headers=self.reservation_config["headers"])

            booking = response.get("reservation", response)

            if not booking:
                return {"status": "error", "message": f"Booking with ID {booking_id} not found"}

            return {"status": "success", "booking": booking}

        except APIError as e:
            logger.error(f"Reservation Services API error: {str(e)}")
            return {"status": "error", "message": f"Failed to get booking details: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error getting booking details: {str(e)}")
            return {"status": "error", "message": f"Failed to get booking details: {str(e)}"}

    def cancel_booking(self, booking_id: str, reason: str = "") -> dict[str, Any]:
        """
        Cancel an existing booking using Reservation Services API.

        Args:
            booking_id: Booking identifier
            reason: Cancellation reason

        Returns:
            Dictionary with cancellation confirmation
        """
        try:
            # Extract hotel ID from booking ID format: {hotelId}CU{digits}
            # Example: "10004CU156038" -> hotel_id = 10004
            if "CU" not in booking_id:
                return {
                    "status": "error",
                    "message": f"Invalid booking ID format '{booking_id}'. Expected format: {{hotelId}}CU{{digits}} (e.g., 10004CU156038)",
                }

            hotel_id_str = booking_id.split("CU")[0]
            if not hotel_id_str.isdigit():
                return {
                    "status": "error",
                    "message": f"Invalid hotel ID in booking ID '{booking_id}'. Hotel ID must be numeric.",
                }

            hotel_id = int(hotel_id_str)

            # Use the correct Mock API endpoint: /reservation/cancel
            cancel_url = f"{self.reservation_config['base_url']}/reservation/cancel"
            cancel_data = {
                "Hotel": {"Id": hotel_id},  # Use extracted hotel ID
                "CrsConfirmationNumber": booking_id,
                "CancellationDetails": {"Comment": reason},
            }

            response = self._make_api_request(
                method="POST", url=cancel_url, headers=self.reservation_config["headers"], data=cancel_data
            )

            return {
                "status": "success",
                "message": "Booking cancelled successfully",
                "booking_id": booking_id,
                "cancellation": response,
            }

        except APIError as e:
            logger.error(f"Reservation Services API error: {str(e)}")
            return {"status": "error", "message": f"Failed to cancel booking: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error cancelling booking: {str(e)}")
            return {"status": "error", "message": f"Failed to cancel booking: {str(e)}"}

    def get_booking_history(self, guest_email: str) -> dict[str, Any]:
        """
        Get booking history for a guest using Reservation Services API.

        Args:
            guest_email: Guest email address

        Returns:
            Dictionary with booking history
        """
        try:
            # Get booking history from Reservation Services API using actual endpoint
            history_url = f"{self.reservation_config['base_url']}/reservation"
            params = {"pageSize": "0"}  # Get all reservations

            # Add query parameters to URL
            history_url += "?" + "&".join([f"{k}={v}" for k, v in params.items()])

            response = self._make_api_request(method="GET", url=history_url, headers=self.reservation_config["headers"])

            # Filter bookings by guest email
            all_bookings = response.get("reservations", [])
            bookings = []
            for booking in all_bookings:
                # Check if any guest has the matching email
                guests = booking.get("Guests", [])
                for guest in guests:
                    email_addresses = guest.get("EmailAddress", [])
                    for email in email_addresses:
                        if email.get("Value") == guest_email:
                            bookings.append(booking)
                            break

            return {
                "status": "success",
                "guest_email": guest_email,
                "total_bookings": len(bookings),
                "bookings": bookings,
            }

        except APIError as e:
            logger.error(f"Reservation Services API error: {str(e)}")
            return {"status": "error", "message": f"Failed to get booking history: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error getting booking history: {str(e)}")
            return {"status": "error", "message": f"Failed to get booking history: {str(e)}"}

    def check_room_availability(
        self, hotel_id: str, check_in_date: str, check_out_date: str, room_type: str | None = None
    ) -> dict[str, Any]:
        """
        Check room availability using Reservation Services API.

        Args:
            hotel_id: Hotel identifier
            check_in_date: Check-in date (YYYY-MM-DD)
            check_out_date: Check-out date (YYYY-MM-DD)
            room_type: Specific room type to check (optional)

        Returns:
            Dictionary with availability information
        """
        try:
            # Use the correct Mock API endpoint: GET /reservation/availability with query parameters
            availability_url = f"{self.reservation_config['base_url']}/reservation/availability"

            # Build query parameters
            params = {"hotel_id": hotel_id, "check_in_date": check_in_date, "check_out_date": check_out_date}

            if room_type:
                params["room_type"] = room_type

            # Add query parameters to URL
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            availability_url += f"?{query_string}"

            response = self._make_api_request(
                method="GET", url=availability_url, headers=self.reservation_config["headers"]
            )

            # Calculate nights
            check_in = datetime.strptime(check_in_date, "%Y-%m-%d")
            check_out = datetime.strptime(check_out_date, "%Y-%m-%d")
            nights = (check_out - check_in).days

            return {
                "status": "success",
                "hotel_id": hotel_id,
                "check_in_date": check_in_date,
                "check_out_date": check_out_date,
                "nights": nights,
                "availability": response,
            }

        except APIError as e:
            logger.error(f"Reservation Services API error: {str(e)}")
            return {"status": "error", "message": f"Failed to check availability: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error checking availability: {str(e)}")
            return {"status": "error", "message": f"Failed to check availability: {str(e)}"}

    def validate_payment_details(self, payment_info: dict[str, Any]) -> dict[str, Any]:
        """
        Validate payment details using Reservation Services API.

        Args:
            payment_info: Payment information dictionary

        Returns:
            Dictionary with validation results
        """
        try:
            # Use the correct Mock API endpoint: /reservation/payment/validate
            validation_url = f"{self.reservation_config['base_url']}/reservation/payment/validate"

            response = self._make_api_request(
                method="POST", url=validation_url, headers=self.reservation_config["headers"], data=payment_info
            )

            return {
                "status": "success",
                "valid": response.get("success", False),
                "message": response.get("message", "Payment validation completed"),
                "details": response,
            }

        except APIError as e:
            logger.error(f"Payment validation API error: {str(e)}")
            return {"status": "error", "message": f"Payment validation failed: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error validating payment: {str(e)}")
            return {"status": "error", "message": f"Payment validation failed: {str(e)}"}

    def modify_reservation(
        self,
        booking_id: str,
        check_in_date: str | None = None,
        check_out_date: str | None = None,
        room_type: str | None = None,
        guests: int | None = None,
        special_requests: str | None = None,
        guest_name: str | None = None,
        guest_email: str | None = None,
    ) -> dict[str, Any]:
        """
        Modify an existing hotel reservation using Reservation Services API.

        Args:
            booking_id: Booking confirmation number
            check_in_date: New check-in date (YYYY-MM-DD) (optional)
            check_out_date: New check-out date (YYYY-MM-DD) (optional)
            room_type: New room type (optional)
            guests: New number of guests (optional)
            special_requests: New special requests (optional)
            guest_name: New guest name (optional)
            guest_email: New guest email (optional)

        Returns:
            Dictionary with modification confirmation
        """
        try:
            # Prepare modification request using actual Reservation Services API format
            modify_url = f"{self.reservation_config['base_url']}/reservation"

            # Build update data - only include fields that are being changed
            update_data = {"Reservations": [{"CrsConfirmationNumber": booking_id}]}

            reservation = update_data["Reservations"][0]

            # Add fields that are being modified
            if check_in_date or check_out_date or room_type or guests:
                reservation["RoomStay"] = {}

                if check_in_date:
                    reservation["RoomStay"]["CheckInDate"] = check_in_date
                if check_out_date:
                    reservation["RoomStay"]["CheckOutDate"] = check_out_date
                if guests:
                    reservation["RoomStay"]["GuestCount"] = [{"NumGuests": guests}]
                if room_type:
                    reservation["RoomStay"]["Products"] = [{"Product": {"RoomCode": room_type, "RoomName": room_type}}]

            if guest_name or guest_email or special_requests:
                reservation["Guests"] = [{}]
                guest = reservation["Guests"][0]

                if guest_name:
                    # Split guest name into first and last name
                    name_parts = guest_name.split(" ", 1)
                    given_name = name_parts[0] if name_parts else guest_name
                    surname = name_parts[1] if len(name_parts) > 1 else ""

                    guest["PersonName"] = {"GivenName": given_name, "Surname": surname}

                if guest_email:
                    guest["EmailAddress"] = [{"Type": "Primary", "Value": guest_email}]

                if special_requests:
                    guest["Comments"] = special_requests

            # Make API request
            response = self._make_api_request(
                method="PATCH", url=modify_url, headers=self.reservation_config["headers"], data=update_data
            )

            reservation_data = response.get("reservations", [{}])[0] if response.get("reservations") else response

            return {
                "status": "success",
                "message": "Reservation modified successfully",
                "booking_id": booking_id,
                "reservation": reservation_data,
            }

        except APIError as e:
            logger.error(f"Reservation Services API error: {str(e)}")
            return {"status": "error", "message": f"Failed to modify reservation: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error modifying reservation: {str(e)}")
            return {"status": "error", "message": f"Failed to modify reservation: {str(e)}"}
