import json
import random
from datetime import datetime


# Room types with detailed information
ROOM_TYPES = [
    {
        "RoomCode": "A1K",
        "RoomName": "Standard King",
        "BaseRate": 250.00,
        "BedType": "One king bed",
        "SquareFeet": 350,
        "MaxOccupancy": 2,
        "View": "City view",
        "Amenities": "Free WiFi, coffee maker, 42-inch flat-screen TV, air conditioning, work desk, luxury bathroom amenities, daily housekeeping",
        "Description": "Comfortable king room perfect for business or leisure travel with essential amenities and city views.",
    },
    {
        "RoomCode": "A2Q",
        "RoomName": "Standard Double Queen",
        "BaseRate": 275.00,
        "BedType": "Two queen beds",
        "SquareFeet": 400,
        "MaxOccupancy": 4,
        "View": "City view",
        "Amenities": "Free WiFi, coffee maker, 42-inch flat-screen TV, air conditioning, spacious work area, luxury bathroom amenities, daily housekeeping",
        "Description": "Spacious room with two queen beds, ideal for families or groups traveling together.",
    },
    {
        "RoomCode": "B1K",
        "RoomName": "Club Level King",
        "BaseRate": 350.00,
        "BedType": "One king bed",
        "SquareFeet": 450,
        "MaxOccupancy": 2,
        "View": "Premium city view",
        "Amenities": "Club lounge access, complimentary continental breakfast, evening cocktails and hors d'oeuvres, free WiFi, coffee maker, 49-inch flat-screen TV, air conditioning, executive work desk, luxury bathroom amenities, turndown service",
        "Description": "Elevated experience with club lounge privileges, premium amenities, and exclusive services for discerning travelers.",
    },
    {
        "RoomCode": "B1S",
        "RoomName": "Deluxe Suite",
        "BaseRate": 450.00,
        "BedType": "One king bed + sofa bed",
        "SquareFeet": 650,
        "MaxOccupancy": 4,
        "View": "Premium city view",
        "Amenities": "Separate living area, dining table, kitchenette with mini-fridge, free WiFi, coffee maker, 55-inch flat-screen TV, air conditioning, executive work area, luxury bathroom with soaking tub, daily housekeeping, turndown service",
        "Description": "Spacious suite with separate living area, perfect for extended stays or entertaining, featuring premium amenities and extra space.",
    },
    {
        "RoomCode": "D1P",
        "RoomName": "Presidential Suite",
        "BaseRate": 950.00,
        "BedType": "One king bed + separate bedroom options",
        "SquareFeet": 1200,
        "MaxOccupancy": 6,
        "View": "Panoramic city view",
        "Amenities": "Multiple bedrooms, grand living area, formal dining room, full kitchen, private balcony, butler service, club lounge access, complimentary breakfast and cocktails, free WiFi, multiple flat-screen TVs, air conditioning, executive office space, marble bathroom with jacuzzi, 24-hour room service, concierge service",
        "Description": "Luxurious presidential suite offering the ultimate in space, service, and amenities with panoramic views and personalized butler service.",
    },
]


def check_room_availability(
    hotel_id: str, check_in_date: str, check_out_date: str, room_type: str | None = None
) -> dict:
    """
    Check room availability using seed data room types.
    """
    print(f"Checking room availability for hotel {hotel_id} from {check_in_date} to {check_out_date}")

    try:
        # Calculate number of nights
        check_in = datetime.strptime(check_in_date, "%Y-%m-%d")
        check_out = datetime.strptime(check_out_date, "%Y-%m-%d")
        num_nights = (check_out - check_in).days

        if num_nights <= 0:
            return {"error": "Check-out date must be after check-in date", "available_rooms": []}

        # Filter room types if specific type requested
        room_candidates = ROOM_TYPES.copy()
        if room_type:
            room_candidates = [
                r
                for r in room_candidates
                if room_type.lower() in r["RoomName"].lower() or room_type.upper() == r["RoomCode"]
            ]

        # Mock availability with dynamic pricing
        available_rooms = []
        for room in room_candidates:
            # Simulate availability (80% base chance, less for suites)
            availability_chance = 0.8 if "Suite" not in room["RoomName"] else 0.6

            if random.random() < availability_chance:
                # Dynamic pricing factors
                weekend_multiplier = 1.2 if check_in.weekday() >= 4 else 1.0
                seasonal_multiplier = 1.15 if check_in.month in [6, 7, 8] else 1.0
                demand_multiplier = 1.0 + (random.random() * 0.2)

                # Calculate final price
                price_per_night = round(
                    room["BaseRate"] * weekend_multiplier * seasonal_multiplier * demand_multiplier, 2
                )

                available_rooms.append(
                    {
                        "room_code": room["RoomCode"],
                        "room_name": room["RoomName"],
                        "base_rate": room["BaseRate"],
                        "price_per_night": price_per_night,
                        "price_per_night_usd": f"${price_per_night:.2f} USD",
                        "total_price": round(price_per_night * num_nights, 2),
                        "total_price_usd": f"${round(price_per_night * num_nights, 2):.2f} USD",
                        "available_count": random.randint(1, 5),
                        "bed_type": room["BedType"],
                        "square_feet": room["SquareFeet"],
                        "max_occupancy": room["MaxOccupancy"],
                        "view": room["View"],
                        "amenities": room["Amenities"],
                        "description": room["Description"],
                        "pricing_factors": {
                            "weekend_adjustment": weekend_multiplier > 1.0,
                            "seasonal_adjustment": seasonal_multiplier > 1.0,
                            "demand_level": "high" if demand_multiplier > 1.15 else "normal",
                        },
                    }
                )

        return {
            "hotel_id": hotel_id,
            "check_in_date": check_in_date,
            "check_out_date": check_out_date,
            "num_nights": num_nights,
            "available_rooms": available_rooms,
            "total_available": len(available_rooms),
            "message": f"Found {len(available_rooms)} room types available"
            if available_rooms
            else "No rooms available for these dates",
        }

    except ValueError as e:
        return {"error": f"Invalid date format: {str(e)}", "available_rooms": []}
    except Exception as e:
        return {"error": f"Failed to check availability: {str(e)}", "available_rooms": []}


def lambda_handler(event, context):  # noqa: ARG001
    """
    Lambda handler for room availability API.
    """
    try:
        # Extract query parameters
        query_params = event.get("queryStringParameters") or {}

        hotel_id = query_params.get("hotel_id")
        check_in_date = query_params.get("check_in_date")
        check_out_date = query_params.get("check_out_date")
        room_type = query_params.get("room_type")

        # Validate required parameters
        if not hotel_id:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "hotel_id parameter is required", "available_rooms": []}),
            }

        if not check_in_date:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "check_in_date parameter is required", "available_rooms": []}),
            }

        if not check_out_date:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "check_out_date parameter is required", "available_rooms": []}),
            }

        # Call availability check function
        result = check_room_availability(hotel_id, check_in_date, check_out_date, room_type)

        # Return appropriate status code
        status_code = 400 if "error" in result else 200

        return {"statusCode": status_code, "headers": {"Content-Type": "application/json"}, "body": json.dumps(result)}

    except Exception as e:
        print(f"Lambda handler error: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": f"Internal server error: {str(e)}", "available_rooms": []}),
        }
