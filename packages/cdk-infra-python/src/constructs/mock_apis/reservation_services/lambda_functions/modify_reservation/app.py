import json
from common.business_logic import validate_update_booking_model
from common.dynamo_client import DynamoDBClient
from common.response_utils import build_error_response, build_response
from datetime import datetime


dynamo_client = DynamoDBClient()


def handler(event, context):  # noqa: ARG001
    """
    Handler for PATCH /reservation endpoint.

    Enables modification of a previously booked reservation using only the data included in the request message.

    Request body should contain an UpdateBookingModel.

    Returns:
        API Gateway response with updated reservation
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

        # Validate update booking model
        validation_errors = validate_update_booking_model(body)
        if validation_errors:
            # Format all validation errors into a meaningful error message
            error_message = "; ".join([f"{key}: {value}" for key, value in validation_errors.items()])
            return build_error_response(400, "ValidationError", error_message)

        # Process each reservation in the update model
        updated_reservations = []

        for reservation_update in body["Reservations"]:
            # Get the confirmation number
            confirmation_number = reservation_update.get("CrsConfirmationNumber")
            if not confirmation_number:
                return build_error_response(
                    400, "InvalidRequest", "CrsConfirmationNumber is required for each reservation"
                )

            # Get the existing reservation
            existing_reservation = dynamo_client.get_reservation(confirmation_number)
            if not existing_reservation:
                return build_error_response(
                    404, "ReservationNotFound", f"Reservation with confirmation number {confirmation_number} not found"
                )

            # Apply updates
            for key, value in reservation_update.items():
                # Skip the confirmation number since we're not changing it
                if key == "CrsConfirmationNumber":
                    continue

                # Handle nested updates
                if (
                    isinstance(value, dict)
                    and key in existing_reservation
                    and isinstance(existing_reservation[key], dict)
                ):
                    # Update nested dictionary
                    existing_reservation[key].update(value)
                else:
                    # Direct update
                    existing_reservation[key] = value

            # Update the timestamp
            existing_reservation["UpdateDateTime"] = datetime.utcnow().isoformat()

            # Save the updated reservation
            updated_reservation = dynamo_client.update_reservation(existing_reservation)
            updated_reservations.append(updated_reservation)

        # Sanitize the reservations and format response
        sanitized_reservations = [dynamo_client.sanitize_response(res) for res in updated_reservations]

        # Format response according to ReservationsModel
        response_data = {
            "pagination": {"total": len(sanitized_reservations), "start": 0, "size": len(sanitized_reservations)},
            "reservations": sanitized_reservations,
        }

        return build_response(200, response_data)

    except Exception as e:
        print(f"Error processing request: {str(e)}")
        import traceback

        print(traceback.format_exc())
        return build_error_response(500, "InternalServerError", str(e))
