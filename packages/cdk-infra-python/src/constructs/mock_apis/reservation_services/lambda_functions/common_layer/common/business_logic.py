import re
import uuid
from datetime import datetime
from typing import Any


def generate_confirmation_number(hotel_id: int) -> str:
    """
    Generate a unique confirmation number for a reservation.
    Format: [hotel_id]CU[6-digit number]

    Args:
        hotel_id: The ID of the hotel

    Returns:
        A unique confirmation number
    """
    random_number = str(uuid.uuid4().int % 1000000).zfill(6)  # Get exactly 6 digits
    return f"{hotel_id}CU{random_number}"


def generate_cancellation_number(hotel_id: int) -> str:
    """
    Generate a unique cancellation number for a cancelled reservation.
    Format: [hotel_id]X[6-digit number]

    Args:
        hotel_id: The ID of the hotel

    Returns:
        A unique cancellation number
    """
    random_number = str(uuid.uuid4().int % 1000000).zfill(6)  # Get exactly 6 digits
    return f"{hotel_id}X{random_number}"


def validate_booking_model(booking_data: dict[str, Any]) -> dict[str, str]:
    """
    Validate a booking model against schema requirements.

    Args:
        booking_data: The booking data to validate

    Returns:
        Dictionary of validation errors, empty if valid
    """
    errors = {}

    # Check required fields
    required_fields = ["BookingInfo", "Hotel", "RoomStay", "Guests", "status"]
    for field in required_fields:
        if field not in booking_data:
            errors[field] = f"Missing required field: {field}"

    # Continue validation even if top-level fields are missing
    # Validate status enum if it exists
    if "status" in booking_data:
        valid_statuses = [
            "Booked",
            "Cancelled",
            "Confirmed",
            "Ignored",
            "OnHold",
            "PendingModify",
            "PaymentPending",
            "Requested",
            "Released",
            "Stored",
            "Waitlisted",
        ]

        if booking_data["status"] not in valid_statuses:
            errors["status"] = f"Invalid status: {booking_data['status']}. Must be one of: {', '.join(valid_statuses)}"

    # Validate BookingInfo if it exists
    if "BookingInfo" in booking_data:
        booking_info = booking_data["BookingInfo"]
        if not isinstance(booking_info, dict):
            errors["BookingInfo"] = "BookingInfo must be an object"
        else:
            if "BookedBy" not in booking_info:
                errors["BookingInfo.BookedBy"] = "BookedBy is required in BookingInfo"
            if "BookingDate" not in booking_info:
                errors["BookingInfo.BookingDate"] = "BookingDate is required in BookingInfo"

    # Validate Hotel if it exists
    if "Hotel" in booking_data:
        hotel = booking_data["Hotel"]
        if not isinstance(hotel, dict):
            errors["Hotel"] = "Hotel must be an object"
        else:
            if "Id" not in hotel:
                errors["Hotel.Id"] = "Hotel.Id is required"

    # Validate RoomStay if it exists
    if "RoomStay" in booking_data:
        room_stay = booking_data["RoomStay"]
        if not isinstance(room_stay, dict):
            errors["RoomStay"] = "RoomStay must be an object"
        else:
            room_stay_required = ["CheckInDate", "CheckOutDate", "GuestCount", "NumRooms", "Products"]
            for field in room_stay_required:
                if field not in room_stay:
                    errors[f"RoomStay.{field}"] = f"Missing required field in RoomStay: {field}"

    # Validate Guests if it exists
    if "Guests" in booking_data:
        guests = booking_data["Guests"]
        if not isinstance(guests, list) or len(guests) == 0:
            errors["Guests"] = "Guests must be a non-empty array"
        else:
            for i, guest in enumerate(guests):
                if not isinstance(guest, dict):
                    errors[f"Guests[{i}]"] = "Each guest must be an object"
                elif "PersonName" not in guest:
                    errors[f"Guests[{i}].PersonName"] = "PersonName is required for each guest"

    return errors


def validate_update_booking_model(update_data: dict[str, Any]) -> dict[str, str]:
    """
    Validate an update booking model against schema requirements.

    Args:
        update_data: The update booking data to validate

    Returns:
        Dictionary of validation errors, empty if valid
    """
    errors = {}

    # Check required fields
    if "Reservations" not in update_data:
        errors["Reservations"] = "Missing required field: Reservations"
    else:
        # Continue with validation if the required field exists
        reservations = update_data["Reservations"]
        if not isinstance(reservations, list) or len(reservations) == 0:
            errors["Reservations"] = "Reservations must be a non-empty array"
        else:
            # Validate each reservation in the array
            for i, reservation in enumerate(reservations):
                # Check for confirmation number
                if "CrsConfirmationNumber" not in reservation:
                    errors[f"Reservations[{i}].CrsConfirmationNumber"] = (
                        "CrsConfirmationNumber is required for each reservation"
                    )

                # Additional validations could be added here as needed

    return errors


def validate_cancel_model(cancel_data: dict[str, Any]) -> dict[str, str]:
    """
    Validate a cancel model against schema requirements.

    Args:
        cancel_data: The cancel data to validate

    Returns:
        Dictionary of validation errors, empty if valid
    """
    errors = {}

    # Check required fields
    required_fields = ["Hotel", "CrsConfirmationNumber"]
    for field in required_fields:
        if field not in cancel_data:
            errors[field] = f"Missing required field: {field}"

    # Continue validation even if top-level fields are missing
    # Validate Hotel if it exists
    if "Hotel" in cancel_data:
        hotel = cancel_data["Hotel"]
        if not isinstance(hotel, dict):
            errors["Hotel"] = "Hotel must be an object"
        elif "Id" not in hotel:
            errors["Hotel.Id"] = "Hotel.Id is required"

    # Validate CrsConfirmationNumber format if it exists
    if "CrsConfirmationNumber" in cancel_data:
        confirmation_number = cancel_data["CrsConfirmationNumber"]
        if not re.match(r"^\d+CU\d+$", confirmation_number):
            errors["CrsConfirmationNumber"] = (
                "Invalid confirmation number format. Expected format: [hotel_id]CU[digits]"
            )

    return errors


def can_cancel_reservation(reservation: dict[str, Any]) -> bool:
    """
    Check if a reservation can be cancelled based on business rules.

    Args:
        reservation: The reservation to check

    Returns:
        True if the reservation can be cancelled, False otherwise
    """
    # Check status is Confirmed
    if reservation["status"] != "Confirmed":
        return False

    # In a real system, there would be additional business rules here,
    # such as checking cancellation policies, package policies, etc.
    # For this example, we'll just check that the status is Confirmed.

    return True


def create_reservation_from_booking(booking_model: dict[str, Any]) -> dict[str, Any]:
    """
    Create a reservation from a booking model.

    Args:
        booking_model: The booking model to convert

    Returns:
        A new reservation
    """
    # Generate a confirmation number if not provided
    if "CrsConfirmationNumber" not in booking_model or not booking_model["CrsConfirmationNumber"]:
        booking_model["CrsConfirmationNumber"] = generate_confirmation_number(booking_model["Hotel"]["Id"])

    # Add timestamps
    now = datetime.utcnow().isoformat()
    booking_model["CreateDateTime"] = now
    booking_model["UpdateDateTime"] = now

    # In a real system, you might do more here, like calculate prices,
    # check availability, etc.

    return booking_model


def parse_date_range(date_range_str: str | None) -> tuple | None:
    """
    Parse a date range string in format 'YYYY-MM-DD;YYYY-MM-DD' or 'YYYY-MM-DD,YYYY-MM-DD'.

    Args:
        date_range_str: The date range string to parse

    Returns:
        Tuple of (start_date, end_date) or None
    """
    if not date_range_str:
        return None

    if date_range_str.lower() in ["none", "past", "future"]:
        return date_range_str.lower()

    # Try to split by comma first, then by semicolon
    if "," in date_range_str:
        try:
            start_date, end_date = date_range_str.split(",", 1)
            return (start_date.strip(), end_date.strip())
        except ValueError:
            pass

    # Try semicolon as fallback
    if ";" in date_range_str:
        try:
            start_date, end_date = date_range_str.split(";", 1)
            return (start_date.strip(), end_date.strip())
        except ValueError:
            pass

    return None


def handle_api_gateway_date_range(query_params: dict[str, Any], param_name: str) -> tuple | None:
    """
    Handle date range parameters from API Gateway, working around its semicolon parsing behavior.

    When a semicolon is used in a query parameter (e.g., arrival=2025-02-14;2025-03-30),
    API Gateway may split it into multiple parameters:
    - arrival=2025-02-14
    - 2025-03-30=

    This function detects and handles this case.

    Args:
        query_params: Dictionary of query parameters
        param_name: Name of the parameter that contains a date range

    Returns:
        Tuple of (start_date, end_date) or None
    """
    # First try the normal case
    if param_name in query_params:
        value = query_params.get(param_name)
        if value and ("," in value or ";" in value):
            return parse_date_range(value)

    # If that doesn't work, look for a split parameter
    date_keys = []
    for key in query_params:
        # Look for keys that appear to be dates themselves (like "2025-03-30")
        if key != param_name and key.startswith("20") and len(key) == 10 and key.count("-") == 2:
            date_keys.append(key)

    # If we have the main parameter and exactly one date key,
    # treat them as the start and end dates of a range
    if param_name in query_params and len(date_keys) == 1:
        start_date = query_params.get(param_name)
        end_date = date_keys[0]  # The key itself is the end date

        # Validate they both look like dates
        if start_date and start_date.startswith("20") and len(start_date) == 10 and start_date.count("-") == 2:
            return (start_date, end_date)

    return None
