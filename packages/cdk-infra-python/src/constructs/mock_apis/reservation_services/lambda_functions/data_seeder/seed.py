import boto3
import json
import logging
import os
from datetime import datetime
from decimal import Decimal
from typing import Any


# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize DynamoDB client
dynamodb = boto3.resource("dynamodb")


def handler(event, context):  # noqa: ARG001
    """
    Lambda handler function for seeding DynamoDB tables with sample data.
    This is triggered by a custom resource in the CDK stack.

    Args:
        event: Custom resource event
        context: Lambda context

    Returns:
        Response for CloudFormation custom resource
    """
    logger.info(f"Received event: {json.dumps(event)}")

    # Get the request type from the CloudFormation event
    request_type = event.get("RequestType")

    # Use the existing PhysicalResourceId if available (Update/Delete), otherwise create a new one (Create)
    physical_resource_id = event.get("PhysicalResourceId", f"seed-data-{datetime.now().strftime('%Y%m%d%H%M%S')}")

    # Get table names from environment variables
    room_types_table_name = os.environ.get("ROOM_TYPES_TABLE_NAME", "RoomTypes")
    reservations_table_name = os.environ.get("RESERVATIONS_TABLE_NAME", "Reservations")

    # Only seed data for Create and Update operations
    if request_type in ["Create", "Update"]:
        try:
            # Get tables
            room_types_table = dynamodb.Table(room_types_table_name)
            reservations_table = dynamodb.Table(reservations_table_name)

            # Load and seed data (hotels now come from Amazon Location Service)
            room_types = load_json_file("data/room_types.json")
            reservations = load_json_file("data/reservations.json")

            # Add flattened attributes for GSIs
            reservations = flatten_attributes_for_gsi(reservations)
            logger.info("Flattened reservation attributes for GSI compatibility")

            seed_table(room_types_table, room_types)
            seed_table(reservations_table, reservations)

            # Success response - IMPORTANT: Use the consistent PhysicalResourceId
            response = {
                "Status": "SUCCESS",
                "Reason": "Seed data loaded successfully",
                "PhysicalResourceId": physical_resource_id,  # Use consistent ID
                "StackId": event.get("StackId"),
                "RequestId": event.get("RequestId"),
                "LogicalResourceId": event.get("LogicalResourceId"),
                "Data": {
                    "RoomTypesTableName": room_types_table_name,
                    "RoomTypesCount": len(room_types),
                    "ReservationsTableName": reservations_table_name,
                    "ReservationsCount": len(reservations),
                    "Timestamp": datetime.now().isoformat(),
                },
            }

            return response
        except Exception as e:
            logger.warning(f"Error seeding tables: {str(e)}")

            # Error response - IMPORTANT: Use the consistent PhysicalResourceId
            response = {
                "Status": "FAILED",
                "Reason": f"Error seeding tables: {str(e)}",
                "PhysicalResourceId": physical_resource_id,  # Use consistent ID
                "StackId": event.get("StackId"),
                "RequestId": event.get("RequestId"),
                "LogicalResourceId": event.get("LogicalResourceId"),
            }

            return response
    elif request_type == "Delete":
        # For Delete operations, just return success without any data operations
        # In a production environment, you might want to clean up resources here
        return {
            "Status": "SUCCESS",
            "Reason": "Delete request acknowledged",
            "PhysicalResourceId": physical_resource_id,  # Use consistent ID
            "StackId": event.get("StackId"),
            "RequestId": event.get("RequestId"),
            "LogicalResourceId": event.get("LogicalResourceId"),
        }
    else:
        # Invalid request type
        return {
            "Status": "FAILED",
            "Reason": f"Invalid request type: {request_type}",
            "PhysicalResourceId": physical_resource_id,  # Use consistent ID
            "StackId": event.get("StackId"),
            "RequestId": event.get("RequestId"),
            "LogicalResourceId": event.get("LogicalResourceId"),
        }


def flatten_attributes_for_gsi(reservations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Add flattened attributes to reservation items for GSI compatibility.
    DynamoDB GSIs with keys like "Hotel.Id" expect a top-level attribute with that exact name,
    not the nested attribute Hotel.Id.

    Args:
        reservations: List of reservation items

    Returns:
        List of reservations with flattened attributes added
    """
    for reservation in reservations:
        # Add flattened Hotel.Id for the HotelId-status-index
        if "Hotel" in reservation and "Id" in reservation["Hotel"]:
            reservation["Hotel.Id"] = reservation["Hotel"]["Id"]

        # Add flattened RoomStay.CheckInDate for the status-CheckInDate-index
        if "RoomStay" in reservation and "CheckInDate" in reservation["RoomStay"]:
            reservation["RoomStay.CheckInDate"] = reservation["RoomStay"]["CheckInDate"]

    return reservations


def convert_floats_to_decimals(obj):
    """
    Recursively converts all float values in a dictionary or list to Decimal.

    Args:
        obj: The object to convert (dict, list, or primitive type)

    Returns:
        The object with all floats converted to Decimal
    """
    if isinstance(obj, dict):
        return {k: convert_floats_to_decimals(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_floats_to_decimals(i) for i in obj]
    elif isinstance(obj, float):
        return Decimal(str(obj))
    else:
        return obj


def load_json_file(file_path: str) -> list[dict[str, Any]]:
    """
    Load JSON data from a file and convert floats to Decimals.

    Args:
        file_path: Path to the JSON file

    Returns:
        List of dictionaries with floats converted to Decimals
    """
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        full_path = os.path.join(current_dir, file_path)

        logger.info(f"Loading data from {full_path}")

        with open(full_path, encoding="utf-8") as file:
            data = json.load(file)

        # Convert floats to Decimals for DynamoDB compatibility
        data = convert_floats_to_decimals(data)

        return data

    except Exception as e:
        logger.warning(f"Error loading JSON file {file_path}: {str(e)}")
        raise


def seed_table(table, items: list[dict[str, Any]]):
    """
    Seed a DynamoDB table with items.

    Args:
        table: DynamoDB table
        items: List of items to put into the table
    """
    try:
        logger.info(f"Seeding table {table.table_name} with {len(items)} items")

        # Use batch_writer for more efficient writes
        with table.batch_writer() as batch:
            for item in items:
                batch.put_item(Item=item)

        logger.info(f"Successfully seeded table {table.table_name}")

    except Exception as e:
        logger.warning(f"Error seeding table {table.table_name}: {str(e)}")
        raise


# If the script is executed directly, run the seed function
if __name__ == "__main__":
    # Mock event for local testing
    mock_event = {
        "RequestType": "Create",
        "StackId": "local-test",
        "RequestId": "local-test",
        "LogicalResourceId": "local-test",
    }

    handler(mock_event, None)
