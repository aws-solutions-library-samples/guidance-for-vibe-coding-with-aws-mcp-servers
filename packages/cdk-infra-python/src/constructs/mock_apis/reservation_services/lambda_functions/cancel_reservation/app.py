import json
from common.business_logic import can_cancel_reservation, generate_cancellation_number, validate_cancel_model
from common.dynamo_client import DynamoDBClient
from common.response_utils import build_error_response, build_response
from datetime import datetime


dynamo_client = DynamoDBClient()


def handler(event, context):  # noqa: ARG001
    """
    Handler for POST /reservation/cancel endpoint.

    Cancels a reservation if it meets the eligibility criteria:
    - Reservation status is Confirmed
    - (Other business rules would apply in a real system)

    Request body should contain a CancelModel.

    Returns:
        API Gateway response with cancellation details
    """
    try:
        print(f"Received event: {json.dumps(event)}")

        # Parse request body
        if not event.get("body"):
            return build_error_response(400, "InvalidRequest", "Request body is required")

        try:
            body = json.loads(event["body"]) if isinstance(event["body"], str) else event["body"]
        except json.JSONDecodeError:
            return build_error_response(400, "InvalidJSON", "Request body is not valid JSON")

        # Validate cancel model
        validation_errors = validate_cancel_model(body)
        if validation_errors:
            # Format all validation errors into a meaningful error message
            error_message = "; ".join([f"{key}: {value}" for key, value in validation_errors.items()])
            return build_error_response(400, "ValidationError", error_message)

        # Get the confirmation number and hotel ID
        confirmation_number = body["CrsConfirmationNumber"]
        hotel_id = body["Hotel"]["Id"]

        # Get the existing reservation
        reservation = dynamo_client.get_reservation(confirmation_number)
        if not reservation:
            return build_error_response(
                404, "ReservationNotFound", f"Reservation with confirmation number {confirmation_number} not found"
            )

        # Check if the reservation belongs to the specified hotel
        if reservation["Hotel"]["Id"] != hotel_id:
            return build_error_response(
                400, "HotelMismatch", f"Reservation {confirmation_number} does not belong to hotel {hotel_id}"
            )

        # Check if the reservation is eligible for cancellation
        if not can_cancel_reservation(reservation):
            return build_error_response(
                409,
                "CannotCancel",
                'This reservation cannot be cancelled. Only reservations with status "Confirmed" can be cancelled.',
            )

        # Generate a cancellation number
        cancellation_number = generate_cancellation_number(hotel_id)

        # Update the reservation
        reservation["status"] = "Cancelled"
        reservation["UpdateDateTime"] = datetime.utcnow().isoformat()

        # Add cancellation details
        if "CancellationDetails" in body:
            reservation["CancellationDetails"] = body["CancellationDetails"]

        # Save the cancelled reservation
        dynamo_client.update_reservation(reservation)

        # Format response according to CancelResponseModel
        response_data = {"CrsCancellationNumber": cancellation_number}

        return build_response(200, response_data)

    except Exception as e:
        print(f"Error processing request: {str(e)}")
        import traceback

        print(traceback.format_exc())
        return build_error_response(500, "InternalServerError", str(e))
