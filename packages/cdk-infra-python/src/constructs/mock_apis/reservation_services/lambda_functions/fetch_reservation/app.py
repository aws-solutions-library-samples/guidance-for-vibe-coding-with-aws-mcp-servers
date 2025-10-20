import json
from common.dynamo_client import DynamoDBClient
from common.response_utils import build_error_response, build_response


dynamo_client = DynamoDBClient()


def handler(event, context):  # noqa: ARG001
    """
    Handler for GET /reservation/hotel/{hotelId}/{id} endpoint.

    Retrieves a single reservation by hotel ID and reservation ID (confirmation number).

    Path parameters:
    - hotelId: The ID of the hotel
    - id: The reservation ID or confirmation number

    Returns:
        API Gateway response with the reservation details
    """
    try:
        print(f"Received event: {json.dumps(event)}")

        # Extract path parameters
        path_parameters = event.get("pathParameters", {})
        if not path_parameters:
            return build_error_response(400, "MissingPathParameters", "Path parameters are required")

        hotel_id_str = path_parameters.get("hotelId")
        reservation_id = path_parameters.get("id")

        if not hotel_id_str:
            return build_error_response(400, "MissingHotelId", "Hotel ID is required")

        if not reservation_id:
            return build_error_response(400, "MissingReservationId", "Reservation ID is required")

        # Convert hotel_id to integer
        try:
            hotel_id = int(hotel_id_str)
        except ValueError:
            return build_error_response(400, "InvalidHotelId", "Hotel ID must be a number")

        # Try to find the reservation by confirmation number
        reservation = dynamo_client.get_reservation(reservation_id)

        # If not found by confirmation number, we could try other lookups here
        # For example, itinerary number, guest reference number, etc.
        # This would depend on having appropriate indexes in DynamoDB

        if not reservation:
            return build_error_response(404, "ReservationNotFound", f"Reservation with ID {reservation_id} not found")

        # Check if the reservation belongs to the specified hotel
        if reservation["Hotel"]["Id"] != hotel_id:
            return build_error_response(
                404, "ReservationNotFound", f"Reservation {reservation_id} not found for hotel {hotel_id}"
            )

        # Return the sanitized reservation
        sanitized_reservation = dynamo_client.sanitize_response(reservation)
        return build_response(200, sanitized_reservation)

    except Exception as e:
        print(f"Error processing request: {str(e)}")
        import traceback

        print(traceback.format_exc())
        return build_error_response(500, "InternalServerError", str(e))
