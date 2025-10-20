import json
from common.business_logic import create_reservation_from_booking, validate_booking_model
from common.dynamo_client import DynamoDBClient
from common.response_utils import build_error_response, build_response


dynamo_client = DynamoDBClient()


def handler(event, context):  # noqa: ARG001
    """
    Handler for POST /reservation endpoint.

    Creates a new reservation with a reservation status of Booked, Waitlisted, OnHold, or Confirmed.

    Request body should contain a BookingModel.

    Returns:
        API Gateway response with created reservation
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

        # Validate booking model
        validation_errors = validate_booking_model(body)
        if validation_errors:
            # Format all validation errors into a meaningful error message
            error_message = "; ".join([f"{key}: {value}" for key, value in validation_errors.items()])
            return build_error_response(400, "ValidationError", error_message)

        # Validate status enum
        valid_statuses = ["Booked", "Waitlisted", "OnHold", "Confirmed"]
        if body["status"] not in valid_statuses:
            return build_error_response(
                400, "InvalidStatus", f"Status for new reservations must be one of: {', '.join(valid_statuses)}"
            )

        try:
            # Convert booking model to reservation
            reservation = create_reservation_from_booking(body)

            # Save to DynamoDB
            saved_reservation = dynamo_client.create_reservation(reservation)

            # Sanitize and format response according to ReservationsModel
            sanitized_reservation = dynamo_client.sanitize_response(saved_reservation)
            response_data = {"pagination": {"total": 1, "start": 0, "size": 1}, "reservations": [sanitized_reservation]}

            return build_response(200, response_data)

        except Exception as e:
            print(f"Error creating reservation: {str(e)}")
            import traceback

            print(traceback.format_exc())
            return build_error_response(500, "ReservationCreationError", str(e))

    except Exception as e:
        print(f"Error processing request: {str(e)}")
        import traceback

        print(traceback.format_exc())
        return build_error_response(500, "InternalServerError", str(e))
