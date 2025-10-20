import boto3
import os
import re
from datetime import datetime
from decimal import Decimal
from thefuzz import fuzz
from typing import Any


def generate_chain_id(chain_name: str) -> int:
    """Generate deterministic chain ID from name using hash."""
    hash_value = hash(chain_name.lower()) % 10000
    return 20000 + hash_value


def generate_brand_id(brand_name: str) -> int:
    """Generate deterministic brand ID from name using hash."""
    hash_value = hash(brand_name.lower()) % 10000
    return 30000 + hash_value


def extract_brand_and_chain(hotel_name: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Extract brand and chain info from hotel name.
    Returns: (chain_dict, brand_dict)
    """
    words = hotel_name.split()

    # Chain is first 2 words (or 1 if only 1 word)
    chain_name = " ".join(words[:2]) if len(words) > 1 else words[0]

    # Brand is first word
    brand_name = words[0]

    # Generate codes (first 4 letters uppercase)
    chain_code = chain_name.replace(" ", "")[:4].upper()
    brand_code = brand_name[:4].upper()

    chain = {"Code": chain_code, "Id": generate_chain_id(chain_name), "Name": chain_name}

    brand = {"Code": brand_code, "Id": generate_brand_id(brand_name), "Name": brand_name}

    return chain, brand


class HotelManager:
    """
    Manager for hotel data operations, integrating Property Resolution Service
    with the Hotels table from Reservation Services.
    """

    def __init__(self):
        self.dynamodb = boto3.resource("dynamodb")
        self.hotels_table = self.dynamodb.Table(os.environ.get("HOTELS_TABLE_NAME", "Hotels"))

    def list_hotels(self) -> list[dict[str, Any]]:
        """List all hotels in the Hotels table."""
        response = self.hotels_table.scan()
        return response.get("Items", [])

    def get_hotel_by_code(self, code: str) -> dict[str, Any] | None:
        """Get a hotel by its code using the GSI."""
        response = self.hotels_table.query(
            IndexName="CodeIndex", KeyConditionExpression="Code = :code", ExpressionAttributeValues={":code": code}
        )
        items = response.get("Items", [])
        return items[0] if items else None

    def generate_hotel_code(self, hotel_name: str, chain_code: str, city: str) -> str:
        """
        Generate a 4-character hotel code (spirit_cd) similar to existing codes.
        Format: [Chain prefix][City prefix]
        """
        # Use first 2 characters from chain code
        prefix = chain_code[:2]

        # Use first 2 characters from city name (up to 2 words)
        city_words = city.split()[:2]
        city_code = "".join([word[0].upper() for word in city_words])

        # If city code is too short, add from hotel name
        if len(city_code) < 2:
            # Extract brand words from hotel name
            brand_words = hotel_name.split()[:2]
            extra_words = [
                word
                for word in hotel_name.split()
                if word.lower() not in ["hotel", "by", "the", "and", "at"] and word not in brand_words
            ]
            extra = "".join([word[0].upper() for word in extra_words])[: 2 - len(city_code)]
            city_code += extra

        # Ensure exactly 2 characters for city code
        city_code = city_code[:2].upper()

        return f"{prefix}{city_code}"

    def generate_hotel_id(self) -> int:
        """
        Generate a unique ID for hotels from Amazon Location Service.
        Uses ID range starting at 50000 to distinguish from seed data.
        """
        # Get all hotels
        hotels = self.list_hotels()

        # Filter for IDs in the external range (50000+)
        external_ids = [hotel["Id"] for hotel in hotels if hotel["Id"] >= 50000]

        # Start with 50000 or increment from the highest existing ID
        next_id = 50000 if not external_ids else max(external_ids) + 1

        return next_id

    def is_duplicate_hotel(self, new_hotel: dict[str, Any]) -> tuple[bool, dict[str, Any] | None]:
        """
        Check if this hotel already exists in the database.
        Uses name similarity and address to detect duplicates.
        """
        # Get all existing hotels
        existing_hotels = self.list_hotels()

        # Extract key details for comparison
        new_name = new_hotel["Name"].lower()
        new_address = new_hotel["Address"].lower()

        for hotel in existing_hotels:
            existing_name = hotel["Name"].lower()
            existing_address = hotel["Address"].lower()

            # Address-based matching (strongest indicator)
            if new_address and existing_address and new_address == existing_address:
                return True, hotel

            # Name similarity in same city
            name_similarity = fuzz.ratio(new_name, existing_name)
            if name_similarity > 85:
                # Check if they're in the same city
                new_city = new_address.split(",")[0].strip() if "," in new_address else ""
                existing_city = existing_address.split(",")[0].strip() if "," in existing_address else ""

                if new_city and existing_city and new_city == existing_city:
                    return True, hotel

        return False, None

    def transform_location_service_hotel(self, hotel_data: dict[str, Any]) -> dict[str, Any]:
        """
        Transform a hotel from Amazon Location Service to Hotels table format.
        """
        hotel_name = hotel_data.get("metadata", {}).get("property_name", "Unknown Hotel")
        address = hotel_data.get("metadata", {}).get("address", {})
        city = address.get("city", "")
        address_line = address.get("address_line_1", "")
        address.get("country", "United States")
        zip_code = address.get("zip_code", "")

        # Extract internal data if available
        internal_data = hotel_data.get("_internal", {})
        coordinates = internal_data.get("coordinates")
        phone = internal_data.get("phone")

        # Format phone number if available
        if phone:
            # Format phone number to standard format if it's not already
            # Remove any non-numeric characters
            phone_digits = re.sub(r"\D", "", phone)
            if len(phone_digits) == 10:
                # Format as (XXX) XXX-XXXX
                phone = f"({phone_digits[:3]}) {phone_digits[3:6]}-{phone_digits[6:]}"
            elif len(phone_digits) == 11 and phone_digits[0] == "1":
                # US number with country code
                phone = f"({phone_digits[1:4]}) {phone_digits[4:7]}-{phone_digits[7:]}"
            else:
                # Keep the original if we can't format it
                pass
        else:
            phone = "(000) 000-0000"  # Default phone if not provided

        # Extract chain and brand dynamically from hotel name
        chain_info, brand_info = extract_brand_and_chain(hotel_name)

        # Generate a unique code for this hotel
        hotel_code = self.generate_hotel_code(hotel_name, chain_info["Code"], city)

        # Check if this code already exists and append number if needed
        existing_codes = {h.get("Code") for h in self.list_hotels()}
        if hotel_code in existing_codes:
            for i in range(2, 10):  # Try suffixes 2-9
                new_code = f"{hotel_code[:3]}{i}"
                if new_code not in existing_codes:
                    hotel_code = new_code
                    break

        # Generate a unique ID in the external range
        hotel_id = self.generate_hotel_id()

        # Format full address
        full_address = f"{address_line}, {city}, {zip_code}" if zip_code else f"{address_line}, {city}"

        # Create hotel record
        hotel_record = {
            "Code": hotel_code,
            "Id": hotel_id,
            "Name": hotel_name,
            "Address": full_address,
            "Phone": phone,
            "Chain": chain_info,
            "Brand": brand_info,
            # Add metadata to track the source
            "ExternalSource": "AmazonLocationService",
            "LastUpdated": datetime.now().isoformat(),
        }

        # Add coordinates if available - convert to Decimal for DynamoDB compatibility
        if coordinates:
            hotel_record["Coordinates"] = {
                "Longitude": Decimal(str(coordinates[0])),
                "Latitude": Decimal(str(coordinates[1])),
            }

        return hotel_record

    def process_and_store_hotel_results(self, location_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Process results from Amazon Location Service and store new hotels.

        Args:
            location_results: List of hotel results from Amazon Location Service

        Returns:
            List of new hotels added to the database
        """
        hotels_to_add = []

        for result in location_results:
            # Transform to Hotels table format
            hotel_record = self.transform_location_service_hotel(result)

            # Check if duplicate
            is_dupe, existing = self.is_duplicate_hotel(hotel_record)

            if not is_dupe:
                try:
                    # Add to DynamoDB
                    self.hotels_table.put_item(Item=hotel_record)
                    hotels_to_add.append(hotel_record)
                    print(f"Added new hotel to database: {hotel_record['Name']}")
                except Exception as e:
                    print(f"Error adding hotel to database: {str(e)}")
            else:
                # print(f"Skipped duplicate hotel: {hotel_record['Name']} (matches {existing['Name']})")
                pass

        return hotels_to_add

    def map_hotel_to_property(self, hotel: dict[str, Any]) -> dict[str, Any]:
        """
        Map a hotel from the Hotels table format to Property Resolution Service format.
        """
        # Extract address components
        address_parts = hotel.get("Address", "").split(",")
        address_line = address_parts[0].strip() if len(address_parts) > 0 else ""
        city = address_parts[1].strip() if len(address_parts) > 1 else ""

        # Extract zip code if present
        zip_code = ""
        if len(address_parts) > 2:
            last_part = address_parts[2].strip()
            zip_match = re.search(r"\d{5}(-\d{4})?", last_part)
            if zip_match:
                zip_code = zip_match.group(0)

        # Create property in PRS format
        property_data = {
            "spirit_cd": hotel.get("Code", ""),
            "hotel_id": hotel.get("Id"),
            "metadata": {
                "property_name": hotel.get("Name", ""),
                "address": {
                    "address_line_1": address_line,
                    "city": city,
                    "country": "United States",  # Default for our mock data
                    "zip_code": zip_code,
                },
            },
        }

        # Add coordinates if available
        if "Coordinates" in hotel:
            property_data["_internal"] = {
                "coordinates": [hotel["Coordinates"]["Longitude"], hotel["Coordinates"]["Latitude"]],
                "city": city,
                "country": "United States",
            }

        return property_data
