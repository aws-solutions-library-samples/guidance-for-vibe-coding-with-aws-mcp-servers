import json
from common.business_logic import handle_api_gateway_date_range
from common.dynamo_client import DynamoDBClient
from common.response_utils import build_error_response, build_response


dynamo_client = DynamoDBClient()


def handler(event, context):  # noqa: ARG001
    """
    Handler for GET /reservation endpoint.

    Query parameters:
    - status: Array of reservation statuses to filter by
    - crsConfirmationNumber: Array of confirmation numbers to match
    - arrival: Range of arrival dates (format: 'YYYY-MM-DD;YYYY-MM-DD')
    - departure: Range of departure dates (format: 'YYYY-MM-DD;YYYY-MM-DD')
    - pageStart: Starting record for pagination
    - pageSize: Number of records per page

    Returns:
        API Gateway response with matching reservations
    """
    try:
        print(f"Received event: {json.dumps(event)}")
        query_params = event.get("queryStringParameters", {}) or {}

        # Parse query parameters
        status_filter = query_params.get("status", "").split(",") if query_params.get("status") else None
        confirmation_numbers = (
            query_params.get("crsConfirmationNumber", "").split(",")
            if query_params.get("crsConfirmationNumber")
            else None
        )

        # Use the special handling for API Gateway's date range parameters
        arrival_date_range = handle_api_gateway_date_range(query_params, "arrival")
        departure_date_range = handle_api_gateway_date_range(query_params, "departure")

        print(f"DEBUG: Arrival date range parsed as {arrival_date_range}")
        print(f"DEBUG: Departure date range parsed as {departure_date_range}")

        # Parse pagination parameters
        try:
            page_start = int(query_params.get("pageStart", "0"))
            page_size = int(query_params.get("pageSize", "10"))

            # Validate pagination parameters
            if page_start < 0:
                return build_error_response(400, "InvalidParameter", "pageStart must be non-negative")

            if page_size < 0:
                return build_error_response(400, "InvalidParameter", "pageSize must be non-negative")

        except ValueError:
            return build_error_response(400, "InvalidParameter", "pageStart and pageSize must be integers")

        # Handle case when confirmation numbers are provided
        if (
            confirmation_numbers and confirmation_numbers[0]
        ):  # Check if there's at least one non-empty confirmation number
            reservations = []
            for number in confirmation_numbers:
                if not number.strip():  # Skip empty strings
                    continue
                reservation = dynamo_client.get_reservation(number.strip())
                if reservation:
                    reservations.append(reservation)
        else:
            # Query based on other filters
            hotel_id = None  # Could be expanded to extract from path or query params if needed

            reservations = dynamo_client.query_reservations(
                status_filter=status_filter,
                hotel_id=hotel_id,
                arrival_date_range=arrival_date_range,
                departure_date_range=departure_date_range,
            )

        # Apply pagination
        total_count = len(reservations)

        # Handle case when page_size is 0 (return all)
        if page_size == 0:
            paginated_reservations = reservations
            actual_page_size = total_count
        else:
            paginated_reservations = reservations[page_start : page_start + page_size]
            actual_page_size = len(paginated_reservations)

        # Sanitize response to remove internal attributes
        sanitized_reservations = [dynamo_client.sanitize_response(item) for item in paginated_reservations]

        # Format response according to ReservationsModel
        response_data = {
            "pagination": {"total": total_count, "start": page_start, "size": actual_page_size},
            "reservations": sanitized_reservations,
        }

        return build_response(200, response_data)

    except Exception as e:
        print(f"Error processing request: {str(e)}")
        import traceback

        print(traceback.format_exc())
        return build_error_response(500, "InternalServerError", str(e))
