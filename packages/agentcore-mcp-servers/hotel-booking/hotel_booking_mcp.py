import logging
from common.hotel_booking_support import HotelBookingService
from mcp.server.fastmcp import FastMCP
from typing import Any


# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize FastMCP server
mcp = FastMCP(host="0.0.0.0", stateless_http=True)

# Lazy initialization of hotel booking service
hotel_service = None


def _get_service():
    """Get the hotel service instance, initializing it if needed."""
    global hotel_service
    if hotel_service is None:
        try:
            logger.info("🔄 Initializing hotel booking service...")
            hotel_service = HotelBookingService()
            logger.info("✅ Hotel booking service initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize hotel booking service: {e}")
            return {"status": "error", "message": f"Hotel booking service initialization failed: {str(e)}"}
    return hotel_service


@mcp.tool()
def search_properties(
    location: str, check_in_date: str, check_out_date: str, guests: int = 2, min_rating: float = 0.0
) -> dict[str, Any]:
    """
    Search for available properties based on location, dates, and preferences.

    Args:
        location: City or location to search for properties
        check_in_date: Check-in date in YYYY-MM-DD format
        check_out_date: Check-out date in YYYY-MM-DD format
        guests: Number of guests (default: 2)
        min_rating: Minimum property rating (default: 0.0)

    Returns:
        Dictionary containing matching properties with availability and pricing
    """
    service = _get_service()
    if isinstance(service, dict):
        return service
    return service.search_properties(location, check_in_date, check_out_date, guests, min_rating)


@mcp.tool()
def create_reservation(
    hotel_id: str,
    check_in_date: str,
    check_out_date: str,
    guest_name: str,
    guest_email: str,
    room_type: str | None = None,
    guests: int = 2,
    special_requests: str = "",
) -> dict[str, Any]:
    """
    Create a new hotel reservation.

    Args:
        hotel_id: Unique identifier for the hotel
        check_in_date: Check-in date in YYYY-MM-DD format
        check_out_date: Check-out date in YYYY-MM-DD format
        guest_name: Name of the primary guest
        guest_email: Email address of the primary guest
        room_type: Type of room to book (optional)
        guests: Number of guests (default: 2)
        special_requests: Any special requests or notes

    Returns:
        Dictionary containing reservation confirmation details
    """
    service = _get_service()
    if isinstance(service, dict):
        return service
    return service.create_reservation(
        hotel_id,
        room_type or "Standard",
        check_in_date,
        check_out_date,
        guest_name,
        guest_email,
        guests,
        special_requests,
    )


@mcp.tool()
def get_booking_details(booking_id: str) -> dict[str, Any]:
    """
    Retrieve details for a specific booking.

    Args:
        booking_id: Unique booking identifier

    Returns:
        Dictionary containing booking details
    """
    service = _get_service()
    if isinstance(service, dict):
        return service
    return service.get_booking_details(booking_id)


@mcp.tool()
def cancel_booking(booking_id: str, reason: str = "") -> dict[str, Any]:
    """
    Cancel an existing booking.

    Args:
        booking_id: Unique booking identifier
        reason: Optional reason for cancellation

    Returns:
        Dictionary containing cancellation confirmation
    """
    service = _get_service()
    if isinstance(service, dict):
        return service
    return service.cancel_booking(booking_id, reason)


@mcp.tool()
def get_booking_history(guest_email: str) -> dict[str, Any]:
    """
    Get booking history for a guest by email address.

    Args:
        guest_email: Email address of the guest

    Returns:
        Dictionary containing list of bookings for the guest
    """
    service = _get_service()
    if isinstance(service, dict):
        return service
    return service.get_booking_history(guest_email)


@mcp.tool()
def check_room_availability(
    hotel_id: str, check_in_date: str, check_out_date: str, room_type: str | None = None
) -> dict[str, Any]:
    """
    Check room availability for specific dates at a hotel.

    Args:
        hotel_id: Unique identifier for the hotel
        check_in_date: Check-in date in YYYY-MM-DD format
        check_out_date: Check-out date in YYYY-MM-DD format
        room_type: Optional specific room type to check

    Returns:
        Dictionary containing availability information
    """
    service = _get_service()
    if isinstance(service, dict):
        return service
    return service.check_room_availability(hotel_id, check_in_date, check_out_date, room_type)


@mcp.tool()
def validate_payment_details(payment_info: dict[str, Any]) -> dict[str, Any]:
    """
    Validate payment details for booking.

    Args:
        payment_info: Dictionary containing payment information (card number, expiry, etc.)

    Returns:
        Dictionary containing validation results
    """
    service = _get_service()
    if isinstance(service, dict):
        return service
    return service.validate_payment_details(payment_info)


@mcp.tool()
def modify_reservation(
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
    Modify an existing hotel reservation.

    Args:
        booking_id: Booking confirmation number
        check_in_date: New check-in date in YYYY-MM-DD format (optional)
        check_out_date: New check-out date in YYYY-MM-DD format (optional)
        room_type: New room type (optional)
        guests: New number of guests (optional)
        special_requests: New special requests or notes (optional)
        guest_name: New guest name (optional)
        guest_email: New guest email (optional)

    Returns:
        Dictionary containing modification confirmation details
    """
    service = _get_service()
    if isinstance(service, dict):
        return service
    return service.modify_reservation(
        booking_id, check_in_date, check_out_date, room_type, guests, special_requests, guest_name, guest_email
    )


# if __name__ == "__main__":
mcp.run(transport="streamable-http")
