import boto3
import os
from datetime import datetime
from decimal import Decimal
from typing import Any


class DynamoDBClient:
    """
    Client for interacting with DynamoDB tables for the reservation service.
    """

    def __init__(self):
        self.dynamodb = boto3.resource("dynamodb")
        self.hotels_table = self.dynamodb.Table(os.environ.get("HOTELS_TABLE_NAME", "Hotels"))
        self.room_types_table = self.dynamodb.Table(os.environ.get("ROOM_TYPES_TABLE_NAME", "RoomTypes"))
        self.reservations_table = self.dynamodb.Table(os.environ.get("RESERVATIONS_TABLE_NAME", "Reservations"))

    # Hotel operations
    def get_hotel(self, hotel_id: int) -> dict[str, Any] | None:
        """Get a hotel by its ID."""
        response = self.hotels_table.get_item(Key={"Id": hotel_id})
        return response.get("Item")

    def get_hotel_by_code(self, code: str) -> dict[str, Any] | None:
        """Get a hotel by its code using the GSI."""
        response = self.hotels_table.query(
            IndexName="CodeIndex", KeyConditionExpression="Code = :code", ExpressionAttributeValues={":code": code}
        )
        items = response.get("Items", [])
        return items[0] if items else None

    def list_hotels(self) -> list[dict[str, Any]]:
        """List all hotels."""
        response = self.hotels_table.scan()
        return response.get("Items", [])

    # Room type operations
    def get_room_type(self, room_code: str) -> dict[str, Any] | None:
        """Get a room type by its code."""
        response = self.room_types_table.get_item(Key={"RoomCode": room_code})
        return response.get("Item")

    def list_room_types(self) -> list[dict[str, Any]]:
        """List all room types."""
        response = self.room_types_table.scan()
        return response.get("Items", [])

    # Reservation operations
    def get_reservation(self, confirmation_number: str) -> dict[str, Any] | None:
        """Get a reservation by its confirmation number."""
        response = self.reservations_table.get_item(Key={"CrsConfirmationNumber": confirmation_number})
        return response.get("Item")

    def create_reservation(self, reservation: dict[str, Any]) -> dict[str, Any]:
        """Create a new reservation."""
        # Add timestamps if not present
        now = datetime.utcnow().isoformat()
        if "CreateDateTime" not in reservation:
            reservation["CreateDateTime"] = now
        if "UpdateDateTime" not in reservation:
            reservation["UpdateDateTime"] = now

        # Add flattened attributes for GSI compatibility
        reservation = self.add_flattened_attributes(reservation)

        # Convert floats to Decimals for DynamoDB compatibility
        reservation = self.convert_floats_to_decimals(reservation)

        self.reservations_table.put_item(Item=reservation)
        return reservation

    def update_reservation(self, reservation: dict[str, Any]) -> dict[str, Any]:
        """Update an existing reservation."""
        # Update timestamp
        reservation["UpdateDateTime"] = datetime.utcnow().isoformat()

        # Update flattened attributes for GSI compatibility
        reservation = self.add_flattened_attributes(reservation)

        # Convert floats to Decimals for DynamoDB compatibility
        reservation = self.convert_floats_to_decimals(reservation)

        self.reservations_table.put_item(Item=reservation)
        return reservation

    def add_flattened_attributes(self, reservation: dict[str, Any]) -> dict[str, Any]:
        """
        Add flattened attributes to reservation item for GSI compatibility.
        DynamoDB GSIs with keys like "Hotel.Id" expect a top-level attribute with that exact name,
        not the nested attribute Hotel.Id.

        Args:
            reservation: Reservation data

        Returns:
            Reservation with flattened attributes added
        """
        # Add flattened Hotel.Id for the HotelId-status-index
        if "Hotel" in reservation and "Id" in reservation["Hotel"]:
            reservation["Hotel.Id"] = reservation["Hotel"]["Id"]

        # Add flattened RoomStay.CheckInDate for the status-CheckInDate-index
        if "RoomStay" in reservation and "CheckInDate" in reservation["RoomStay"]:
            reservation["RoomStay.CheckInDate"] = reservation["RoomStay"]["CheckInDate"]

        return reservation

    def query_reservations(
        self,
        status_filter: list[str] | None = None,
        hotel_id: int | None = None,
        arrival_date_range: tuple[str, str] | None = None,
        departure_date_range: tuple[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Query reservations with various filters.

        Args:
            status_filter: List of reservation statuses to filter by
            hotel_id: Filter by hotel ID
            arrival_date_range: Tuple of (start_date, end_date) for arrival
            departure_date_range: Tuple of (start_date, end_date) for departure

        Returns:
            List of matching reservations
        """
        # Start with base query
        if hotel_id is not None and status_filter:
            # Use GSI-1 for queries by hotel and status
            # Query once for each status and combine results
            items = []
            for status in status_filter:
                response = self.reservations_table.query(
                    IndexName="HotelId-status-index",
                    KeyConditionExpression="#hotelId = :hotel_id AND #statusAttr = :status",
                    ExpressionAttributeNames={"#hotelId": "Hotel.Id", "#statusAttr": "status"},
                    ExpressionAttributeValues={":hotel_id": hotel_id, ":status": status},
                )
                items.extend(response.get("Items", []))

        elif status_filter:
            # Use GSI-2 for queries by status
            # Query once for each status and combine results (DynamoDB can only query with equality on partition key)
            items = []
            for status in status_filter:
                response = self.reservations_table.query(
                    IndexName="status-CheckInDate-index",
                    KeyConditionExpression="#statusAttr = :status",
                    ExpressionAttributeNames={"#statusAttr": "status"},
                    ExpressionAttributeValues={":status": status},
                )
                items.extend(response.get("Items", []))

        else:
            # No filters, scan the table
            response = self.reservations_table.scan()
            items = response.get("Items", [])

        # Apply date filters if needed
        if arrival_date_range:
            start_date_str, end_date_str = arrival_date_range
            items = [
                item
                for item in items
                if self._is_date_in_range(item.get("RoomStay", {}).get("CheckInDate", ""), start_date_str, end_date_str)
            ]

        if departure_date_range:
            start_date_str, end_date_str = departure_date_range
            items = [
                item
                for item in items
                if self._is_date_in_range(
                    item.get("RoomStay", {}).get("CheckOutDate", ""), start_date_str, end_date_str
                )
            ]

        return items

    def sanitize_response(self, item):
        """
        Remove internal attributes (those with dots in the name) from response items.
        Also recursively processes nested dictionaries and lists.

        Args:
            item: The item to sanitize

        Returns:
            Sanitized item without internal attributes
        """
        if isinstance(item, dict):
            return {k: self.sanitize_response(v) for k, v in item.items() if "." not in k}
        elif isinstance(item, list):
            return [self.sanitize_response(i) for i in list(item)]
        else:
            return item

    def _is_date_in_range(self, date_str: str, start_date_str: str, end_date_str: str) -> bool:
        """
        Check if a date string is within a given range.
        Handles both ISO date strings with and without time components.

        Args:
            date_str: The date string to check
            start_date_str: The start date string of the range
            end_date_str: The end date string of the range

        Returns:
            True if the date is within the range, False otherwise
        """
        if not date_str:
            print("DEBUG: Empty date string encountered")
            return False

        try:
            # Extract just the date portion (YYYY-MM-DD) for consistent comparison
            if "T" in date_str:
                item_date_str = date_str.split("T")[0]
            else:
                item_date_str = date_str

            # For start/end dates, make sure we just have the date portion
            start_date_clean = start_date_str.split("T")[0] if "T" in start_date_str else start_date_str
            end_date_clean = end_date_str.split("T")[0] if "T" in end_date_str else end_date_str

            # Parse to datetime objects for comparison
            from datetime import datetime

            item_date = datetime.fromisoformat(item_date_str)
            start_date = datetime.fromisoformat(start_date_clean)
            end_date = datetime.fromisoformat(end_date_clean)

            print(f"DEBUG: Comparing dates - Item: {item_date}, Range: {start_date} to {end_date}")

            # Compare just the dates without time components
            result = start_date <= item_date <= end_date
            print(f"DEBUG: Result of comparison: {result}")
            return result

        except Exception as e:
            print(f"DEBUG: Error in date comparison: {str(e)}")
            # If there's an error, be conservative and exclude the item
            return False

    # Removing the old _parse_iso_date method as it's no longer needed

    def delete_reservation(self, confirmation_number: str) -> bool:
        """Delete a reservation by confirmation number (for testing)."""
        response = self.reservations_table.delete_item(
            Key={"CrsConfirmationNumber": confirmation_number}, ReturnValues="ALL_OLD"
        )
        return "Attributes" in response

    def convert_floats_to_decimals(self, obj):
        """
        Recursively converts all float values in a dictionary or list to Decimal.

        Args:
            obj: The object to convert (dict, list, or primitive type)

        Returns:
            The object with all floats converted to Decimal
        """
        if isinstance(obj, dict):
            return {k: self.convert_floats_to_decimals(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self.convert_floats_to_decimals(i) for i in obj]
        elif isinstance(obj, float):
            return Decimal(str(obj))
        else:
            return obj
