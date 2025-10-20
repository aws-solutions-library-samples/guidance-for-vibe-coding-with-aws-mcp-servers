import boto3
import json
import os
from .hotel_manager import HotelManager
from decimal import Decimal
from typing import Any


# Initialize hotel manager
hotel_manager = HotelManager()


class DecimalEncoder(json.JSONEncoder):
    """
    JSON encoder that can handle decimal types from DynamoDB.
    """

    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


class DynamoDBClient:
    """
    Client for interacting with DynamoDB tables.
    """

    def __init__(self):
        """
        Initialize DynamoDB client and table name from environment variables.
        """
        self.dynamodb = boto3.resource("dynamodb")

        # Initialize the Hotels table
        self.hotels_table = self.dynamodb.Table(os.environ.get("HOTELS_TABLE_NAME", "Hotels"))

    def get_all_hotels(self) -> list[dict[str, Any]]:
        """
        Get all hotels from the Hotels table.

        Returns:
            List of hotel dictionaries
        """
        response = self.hotels_table.scan()
        hotels = response.get("Items", [])

        # Continue scanning if we have more items (pagination)
        while "LastEvaluatedKey" in response:
            response = self.hotels_table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
            hotels.extend(response.get("Items", []))

        return hotels

    def get_hotel_by_id(self, hotel_id: int) -> dict[str, Any] | None:
        """
        Get a hotel by its ID.

        Args:
            hotel_id: The ID of the hotel

        Returns:
            Hotel dictionary if found, None otherwise
        """
        response = self.hotels_table.get_item(Key={"Id": hotel_id})

        return response.get("Item")

    def get_hotel_by_code(self, code: str) -> dict[str, Any] | None:
        """
        Get a hotel by its code using the GSI.

        Args:
            code: The hotel code (spirit_cd)

        Returns:
            Hotel dictionary if found, None otherwise
        """
        response = self.hotels_table.query(
            IndexName="CodeIndex", KeyConditionExpression="Code = :code", ExpressionAttributeValues={":code": code}
        )

        items = response.get("Items", [])
        return items[0] if items else None

    def get_all_properties(self) -> list[dict[str, Any]]:
        """
        Get all properties by converting Hotels table data to Property format.

        Returns:
            List of properties formatted for the Property Resolution Service
        """
        # Get all hotels from the Hotels table
        hotels = self.get_all_hotels()

        # Convert each hotel to property format
        properties = []
        for hotel in hotels:
            property_data = hotel_manager.map_hotel_to_property(hotel)
            properties.append(property_data)

        return properties

    def get_property_by_id(self, spirit_cd: str) -> dict[str, Any] | None:
        """
        Get a single property by its spirit_cd (mapped from hotel Code).

        Args:
            spirit_cd: The unique identifier for the property

        Returns:
            Property dictionary if found, None otherwise
        """
        # Get the hotel by code and convert to property format
        hotel = self.get_hotel_by_code(spirit_cd)
        if hotel:
            return hotel_manager.map_hotel_to_property(hotel)
        return None

    def update_hotel(self, hotel_data: dict[str, Any]) -> dict[str, Any]:
        """
        Add or update a hotel in the Hotels table.

        Args:
            hotel_data: The hotel data to save

        Returns:
            The saved hotel data
        """
        try:
            # Put the item in the table
            self.hotels_table.put_item(Item=hotel_data)
            return hotel_data
        except Exception as e:
            print(f"Error updating hotel: {str(e)}")
            raise

    def sanitize_response(self, property_data: dict[str, Any]) -> dict[str, Any]:
        """
        Sanitize DynamoDB response by converting decimals to floats and
        removing internal fields.

        Args:
            property_data: Property data from DynamoDB

        Returns:
            Sanitized property data
        """
        # Convert from DynamoDB format to JSON
        json_data = json.loads(json.dumps(property_data, cls=DecimalEncoder))

        # Remove internal fields
        if "_internal" in json_data:
            del json_data["_internal"]

        return json_data
