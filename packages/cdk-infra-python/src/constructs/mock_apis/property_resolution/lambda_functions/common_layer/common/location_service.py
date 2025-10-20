import boto3
import re
import traceback
from .hotel_manager import HotelManager, extract_brand_and_chain
from typing import Any


# Initialize the hotel manager
hotel_manager = HotelManager()


def search_location_text(location: str) -> dict[str, float] | None:
    """
    Use Amazon Location Service Places V2 to search for a location and return its coordinates.

    Args:
        location: Location string to search for

    Returns:
        Dictionary containing longitude and latitude or None if not found
    """
    try:
        # Initialize the Amazon Location Service Places V2 client (uses IAM role)
        location_client = boto3.client("geo-places")

        print(f"Searching Amazon Location Service for: {location}")

        # Define a default bias position (approximate center of US)
        # This helps when searching for locations without specifying a region
        default_bias_position = [-98.5795, 39.8283]  # [longitude, latitude]

        # Call the SearchText API with required BiasPosition parameter
        response = location_client.search_text(
            QueryText=location,  # Changed from Text to QueryText
            BiasPosition=default_bias_position,  # Add this required parameter
            MaxResults=1,
            IntendedUse="SingleUse",
        )

        # Extract coordinates from the response with updated structure
        result_items = response.get("ResultItems", [])  # Changed from Results to ResultItems
        if result_items:
            position = result_items[0].get("Position")  # Direct access to Position field
            if position and len(position) == 2:
                # print(f"Found coordinates: {position}")
                return {"longitude": position[0], "latitude": position[1]}

        # print(f"No coordinates found for location: {location}")
        return None

    except Exception as e:
        print(f"Error searching location text: {str(e)}")
        print(traceback.format_exc())
        return None


def search_nearby_hotels(coordinates: dict[str, float]) -> list[dict[str, Any]]:
    """
    Search for hotels near the given coordinates using Amazon Location Service Places V2.

    Args:
        coordinates: Dictionary containing longitude and latitude

    Returns:
        List of property dictionaries formatted for the API response
    """
    try:
        # Initialize the Amazon Location Service Places V2 client (uses IAM role)
        location_client = boto3.client("geo-places")

        # Call the SearchNearby API with correct parameter structure
        response = location_client.search_nearby(
            QueryPosition=[coordinates["longitude"], coordinates["latitude"]],  # Required parameter
            MaxResults=20,  # Increased since we're not filtering by brand
            Filter={
                "IncludeCategories": ["hotel"],  # Only search for hotels
                "IncludeCountries": ["US"],  # Limit search to US only
                # OPTION 2: Uncomment below to filter by specific hotel chains
                # This approach filters for major hotel brands if you want to limit results
                # "IncludeBusinessChains": [
                #     # Hyatt
                #     "Hyatt", "Hyatt_Regency", "Grand_Hyatt", "HYATT_house",
                #     "Hyatt_Place", "HYATT_CENTRIC",
                #
                #     # Marriott International
                #     "Marriott", "JW_Marriott", "The_Ritz-Carlton", "W_Hotels",
                #     "Sheraton", "Westin", "Renaissance", "Courtyard", "Residence_Inn",
                #     "Fairfield_Inn", "SpringHill_Suites", "TownePlace_Suites",
                #     "AC_Hotels", "Aloft", "Element", "Four_Points", "Le_Meridien",
                #
                #     # Hilton Worldwide
                #     "Hilton", "Conrad", "Waldorf_Astoria", "DoubleTree",
                #     "Embassy_Suites", "Hampton_Inn", "Hilton_Garden_Inn",
                #     "Homewood_Suites", "Home2_Suites", "Tru", "Canopy",
                #
                #     # IHG (InterContinental Hotels Group)
                #     "InterContinental", "Crowne_Plaza", "Holiday_Inn",
                #     "Holiday_Inn_Express", "Staybridge_Suites", "Candlewood_Suites",
                #     "EVEN_Hotels", "Kimpton", "Hotel_Indigo",
                #
                #     # Choice Hotels
                #     "Comfort_Inn", "Comfort_Suites", "Quality_Inn", "Sleep_Inn",
                #     "Clarion", "Cambria_Hotels", "MainStay_Suites",
                #
                #     # Wyndham Hotels
                #     "Wyndham", "Ramada", "Days_Inn", "Super_8", "Howard_Johnson",
                #     "Travelodge", "Baymont", "La_Quinta", "Wingate",
                #
                #     # Best Western
                #     "Best_Western", "Best_Western_Plus", "Best_Western_Premier",
                #
                #     # Other Major Brands
                #     "Omni_Hotels", "Four_Seasons", "Mandarin_Oriental"
                # ],
            },
            AdditionalFeatures=["Contact"],  # Include Contact Information in response
            IntendedUse="SingleUse",
        )

        # Process the results with updated structure
        results = process_location_results(response.get("ResultItems", []))  # Changed from Results to ResultItems
        print(f"Found {len(results)} hotels from Amazon Location Service")
        return results

    except Exception as e:
        print(f"Error searching nearby hotels: {str(e)}")
        print(traceback.format_exc())
        return []


def process_location_results(result_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Convert Amazon Location Service Places V2 results to our property format.
    Also stores new hotels in the Hotels table.

    Args:
        result_items: List of result items from Amazon Location Service Places V2

    Returns:
        List of property dictionaries formatted for the API response
    """
    # print(f"ResultItems from search_nearby response: \n {result_items}")
    properties = []

    for i, item in enumerate(result_items):
        # Extract data from the updated response structure
        title = item.get("Title", "Unknown Hotel")
        address = item.get("Address", {})
        position = item.get("Position", [])

        # Extract phone number from Contacts if available
        phone = None
        contacts = item.get("Contacts", {})
        phones = contacts.get("Phones", [])
        if phones and len(phones) > 0:
            phone = phones[0].get("Value", "")

        # Format the address for our API - structure is different in Places V2
        formatted_address = {
            "address_line_1": f"{address.get('AddressNumber', '')} {address.get('Street', '')}".strip(),
            "city": address.get("Locality", ""),
            "country": address.get("Country", {}).get("Name", ""),
            "zip_code": address.get("PostalCode", ""),
        }

        # Create property dictionary in our format (strictly following schema)
        # We'll assign real spirit_cd later from the hotel record
        property_data = {
            "spirit_cd": f"TEMP_{i}",  # Temporary ID, will be replaced
            "metadata": {"property_name": title, "address": formatted_address},
            # Temporarily store additional data that will be used for ranking
            # but stripped before returning to client
            "_internal": {
                "is_external": True,
                "source": "amazon_location_service",
                "coordinates": position if position and len(position) == 2 else None,
                "city": formatted_address["city"],
                "country": formatted_address["country"],
                "phone": phone,  # Store phone number if available
            },
        }

        properties.append(property_data)

    # Process and store hotels in the Hotels table
    # This will also add proper hotel codes (spirit_cd)
    try:
        # Store results in the Hotels table and get the stored hotels back
        stored_hotels = hotel_manager.process_and_store_hotel_results(properties)

        # Now update the spirit_cd in our properties with real hotel codes from the database
        for i, prop in enumerate(properties):
            hotel_name = prop.get("metadata", {}).get("property_name", "")
            address = prop.get("metadata", {}).get("address", {})

            # Find the matching stored hotel by name and address
            matching_hotel = None
            for hotel in stored_hotels:
                if hotel.get("Name", "").lower() == hotel_name.lower() and any(
                    addr_part in hotel.get("Address", "").lower()
                    for addr_part in address.get("address_line_1", "").lower().split()
                ):
                    matching_hotel = hotel
                    break

            if matching_hotel:
                # Use the actual Code from the stored hotel
                prop["spirit_cd"] = matching_hotel.get("Code", f"TEMP_{i}")
                prop["hotel_id"] = matching_hotel.get("Id")
            else:
                # Fallback: generate a code if we can't find a match
                # print(f"Warning: Could not find stored hotel for {hotel_name}")
                chain_info, _ = extract_brand_and_chain(hotel_name)
                chain_code = chain_info["Code"]
                prop["spirit_cd"] = hotel_manager.generate_hotel_code(hotel_name, chain_code, address.get("city", ""))
    except Exception as e:
        print(f"Error processing hotels for Hotels table: {str(e)}")

    return properties


def merge_properties(
    seed_properties: list[dict[str, Any]], external_properties: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """
    Merge seed properties with external properties, avoiding duplicates using smart matching.

    Args:
        seed_properties: List of properties from our seed data
        external_properties: List of properties from Amazon Location Service

    Returns:
        Merged list of properties with duplicates removed
    """
    from thefuzz import fuzz

    merged = []

    # Add all seed properties first
    merged.extend(seed_properties)

    # Track seen properties with detailed info for better matching
    seen_properties = []
    for p in seed_properties:
        seen_properties.append(
            {
                "name": p.get("metadata", {}).get("property_name", "").lower(),
                "address": p.get("metadata", {}).get("address", {}).get("address_line_1", "").lower(),
                "city": p.get("metadata", {}).get("address", {}).get("city", "").lower(),
                "zip": p.get("metadata", {}).get("address", {}).get("zip_code", "").lower(),
            }
        )

    # Only add external properties that don't match existing ones
    for ext_prop in external_properties:
        ext_name = ext_prop.get("metadata", {}).get("property_name", "").lower()
        ext_addr = ext_prop.get("metadata", {}).get("address", {}).get("address_line_1", "").lower()
        ext_city = ext_prop.get("metadata", {}).get("address", {}).get("city", "").lower()
        ext_zip = ext_prop.get("metadata", {}).get("address", {}).get("zip_code", "").lower()

        # Normalize names (remove hyphens, etc.)
        normalized_ext_name = re.sub(r"[^\w\s]", "", ext_name)

        is_duplicate = False
        for seen in seen_properties:
            normalized_seen_name = re.sub(r"[^\w\s]", "", seen["name"])

            # Check for address match (strongest indicator)
            if ext_addr and seen["address"] and ext_addr == seen["address"] and ext_city == seen["city"]:
                # print(f"Duplicate found by address match: {ext_name} == {seen['name']}")
                # print(f"  Address: {ext_addr} in {ext_city}")
                is_duplicate = True
                break

            # Check for name similarity + city match
            name_similarity = fuzz.ratio(normalized_ext_name, normalized_seen_name)
            if name_similarity > 85 and ext_city == seen["city"]:
                # print(f"Duplicate found by name similarity ({name_similarity}%): {ext_name} ~= {seen['name']}")
                # print(f"  City: {ext_city}")
                is_duplicate = True
                break

            # Check for zip match + similar name
            if ext_zip and seen["zip"] and ext_zip == seen["zip"] and name_similarity > 70:
                # print(f"Duplicate found by ZIP + name similarity ({name_similarity}%): {ext_name} ~= {seen['name']}")
                # print(f"  ZIP: {ext_zip}")
                is_duplicate = True
                break

        if not is_duplicate:
            merged.append(ext_prop)

    return merged
