import json
from datetime import datetime


def validate_credit_card_number(card_number: str) -> bool:
    """
    Validate credit card number using Luhn algorithm.
    """
    # Remove spaces and non-digits
    card_number = "".join(filter(str.isdigit, card_number))

    # Check length (13-19 digits for most cards)
    if len(card_number) < 13 or len(card_number) > 19:
        return False

    # Luhn algorithm
    def luhn_check(card_num):
        def digits_of(n):
            return [int(d) for d in str(n)]

        digits = digits_of(card_num)
        odd_digits = digits[-1::-2]
        even_digits = digits[-2::-2]
        checksum = sum(odd_digits)
        for d in even_digits:
            checksum += sum(digits_of(d * 2))
        return checksum % 10 == 0

    return luhn_check(card_number)


def validate_expiration_date(month: str, year: str) -> dict:
    """
    Validate credit card expiration date.
    """
    try:
        month_int = int(month)
        year_int = int(year)

        # Validate month range
        if month_int < 1 or month_int > 12:
            return {"valid": False, "error": "Month must be between 01 and 12"}

        # Validate year (current year or future)
        current_year = datetime.now().year
        if year_int < current_year:
            return {"valid": False, "error": "Expiration year cannot be in the past"}

        # Check if card is expired (same year, past month)
        if year_int == current_year:
            current_month = datetime.now().month
            if month_int < current_month:
                return {"valid": False, "error": "Card is expired"}

        return {"valid": True, "error": None}

    except ValueError:
        return {"valid": False, "error": "Invalid month or year format"}


def capture_payment_details(
    card_number: str | None = None,
    expiration_month: str | None = None,
    expiration_year: str | None = None,
    cvv: str | None = None,
    cardholder_name: str | None = None,
) -> dict:
    """
    Capture and validate credit card payment information.
    """
    print("Capturing payment details")

    try:
        # Collect provided fields
        provided_fields = {}
        validation_errors = []

        # Validate card number
        if card_number is not None:
            card_number_clean = "".join(filter(str.isdigit, card_number))
            if len(card_number_clean) == 0:
                validation_errors.append("Card number is required")
            elif not validate_credit_card_number(card_number_clean):
                validation_errors.append("Invalid credit card number")
            else:
                provided_fields["card_number"] = card_number_clean

        # Validate expiration date
        if expiration_month is not None or expiration_year is not None:
            if expiration_month is None or expiration_year is None:
                validation_errors.append("Both expiration month and year are required")
            else:
                exp_validation = validate_expiration_date(expiration_month, expiration_year)
                if not exp_validation["valid"]:
                    validation_errors.append(exp_validation["error"])
                else:
                    provided_fields["expiration_month"] = expiration_month.zfill(2)
                    provided_fields["expiration_year"] = expiration_year

        # Validate CVV
        if cvv is not None:
            cvv_clean = "".join(filter(str.isdigit, cvv))
            if len(cvv_clean) < 3 or len(cvv_clean) > 4:
                validation_errors.append("CVV must be 3 or 4 digits")
            else:
                provided_fields["cvv"] = cvv_clean

        # Validate cardholder name
        if cardholder_name is not None:
            name_clean = cardholder_name.strip()
            if len(name_clean) == 0:
                validation_errors.append("Cardholder name is required")
            elif len(name_clean) < 2:
                validation_errors.append("Cardholder name is too short")
            elif len(name_clean) > 50:
                validation_errors.append("Cardholder name is too long")
            else:
                provided_fields["cardholder_name"] = name_clean

        # Determine completion status
        required_fields = ["card_number", "expiration_month", "expiration_year", "cvv", "cardholder_name"]
        missing_fields = [field for field in required_fields if field not in provided_fields]
        is_complete = len(missing_fields) == 0

        # Prepare result
        result = {
            "success": len(validation_errors) == 0,
            "validation_errors": validation_errors,
            "provided_fields": provided_fields,
            "missing_fields": missing_fields,
            "is_complete": is_complete,
            "requires_additional_info": len(missing_fields) > 0,
        }

        # Add user-friendly messages
        if len(validation_errors) > 0:
            result["message"] = f"Payment validation failed: {'; '.join(validation_errors)}"
        elif not is_complete:
            missing_list = ", ".join([field.replace("_", " ").title() for field in missing_fields])
            result["message"] = f"Please provide the following payment details: {missing_list}"
        else:
            result["message"] = "Payment details captured and validated successfully"

        return result

    except Exception as e:
        print(f"Error capturing payment details: {str(e)}")
        return {
            "success": False,
            "validation_errors": [f"Failed to process payment details: {str(e)}"],
            "provided_fields": {},
            "missing_fields": required_fields,
            "is_complete": False,
            "message": "An error occurred while processing your payment information",
        }


def lambda_handler(event, context):  # noqa: ARG001
    """
    Lambda handler for payment validation API.
    """
    try:
        # Parse request body
        if event.get("body"):
            try:
                body = json.loads(event["body"])
            except json.JSONDecodeError:
                return {
                    "statusCode": 400,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps(
                        {
                            "success": False,
                            "validation_errors": ["Invalid JSON in request body"],
                            "provided_fields": {},
                            "missing_fields": [
                                "card_number",
                                "expiration_month",
                                "expiration_year",
                                "cvv",
                                "cardholder_name",
                            ],
                            "is_complete": False,
                            "message": "Invalid JSON in request body",
                        }
                    ),
                }
        else:
            body = {}

        # Extract payment details from body
        card_number = body.get("card_number")
        expiration_month = body.get("expiration_month")
        expiration_year = body.get("expiration_year")
        cvv = body.get("cvv")
        cardholder_name = body.get("cardholder_name")

        # Call payment validation function
        result = capture_payment_details(
            card_number=card_number,
            expiration_month=expiration_month,
            expiration_year=expiration_year,
            cvv=cvv,
            cardholder_name=cardholder_name,
        )

        # Return 200 for both success and validation errors (business logic errors)
        # Only return 4xx/5xx for actual HTTP/system errors
        return {"statusCode": 200, "headers": {"Content-Type": "application/json"}, "body": json.dumps(result)}

    except Exception as e:
        print(f"Lambda handler error: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {
                    "success": False,
                    "validation_errors": [f"Internal server error: {str(e)}"],
                    "provided_fields": {},
                    "missing_fields": ["card_number", "expiration_month", "expiration_year", "cvv", "cardholder_name"],
                    "is_complete": False,
                    "message": "An error occurred while processing your payment information",
                }
            ),
        }
