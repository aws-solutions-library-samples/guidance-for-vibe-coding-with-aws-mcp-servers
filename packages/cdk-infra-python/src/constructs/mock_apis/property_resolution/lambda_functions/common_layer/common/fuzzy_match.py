import copy
import re
from .hotel_manager import HotelManager
from thefuzz import fuzz
from typing import Any


# Initialize the hotel manager
hotel_manager = HotelManager()


def preprocess_text(text: str) -> str:
    """
    Preprocess text for fuzzy matching by standardizing format.

    Args:
        text: Input text string

    Returns:
        Preprocessed text string
    """
    if not text:
        return ""

    # Convert to lowercase
    text = text.lower()

    # Remove punctuation except spaces
    text = re.sub(r"[^\w\s]", "", text)

    # Normalize whitespace
    text = " ".join(text.split())

    return text


def enhance_brand_recognition(query: str) -> str:
    """
    Enhance brand recognition by normalizing common hotel brand terms.
    Extracts brand terms from loaded hotel data to remain generic.

    Args:
        query: Original query string

    Returns:
        Query with normalized brand terms
    """
    processed_query = preprocess_text(query)

    # Extract unique brand terms from hotel data
    brand_terms = set()
    hotels = hotel_manager.list_hotels()
    for hotel in hotels:
        name = hotel.get("Name", "")
        # Extract first 1-2 words from hotel names as potential brand terms
        words = name.split()[:2]
        for word in words:
            word_clean = preprocess_text(word)
            if len(word_clean) > 2:  # Only consider words longer than 2 chars
                brand_terms.add(word_clean)

    # Apply fuzzy matching to correct misspellings in query
    query_tokens = processed_query.split()
    corrected_tokens = []

    for token in query_tokens:
        best_match = token
        best_score = 0

        # Find best matching brand term
        for brand in brand_terms:
            score = fuzz.ratio(token, brand)
            if score > best_score and score >= 85:  # High threshold for brand correction
                best_score = score
                best_match = brand

        corrected_tokens.append(best_match)

    return " ".join(corrected_tokens)


def extract_locations(query: str) -> list[str]:
    """
    Extract potential location names from query.

    Args:
        query: Input query string

    Returns:
        List of potential location terms
    """
    # Split query into tokens
    tokens = preprocess_text(query).split()

    # Build hotel terms dynamically from loaded hotel data
    hotel_terms = {"hotel", "place", "rooms"}  # Generic terms
    hotels = hotel_manager.list_hotels()
    for hotel in hotels:
        name = hotel.get("Name", "")
        # Extract first 1-2 words as brand terms
        words = name.split()[:2]
        for word in words:
            word_clean = preprocess_text(word)
            if len(word_clean) > 2:
                hotel_terms.add(word_clean)

    # Potential locations are tokens that aren't hotel terms
    potential_locations = [token for token in tokens if token.lower() not in hotel_terms]

    # Join adjacent tokens that aren't hotel terms to form location phrases
    location_phrases = []
    current_phrase = []

    for token in tokens:
        if token.lower() not in hotel_terms:
            current_phrase.append(token)
        else:
            if current_phrase:
                location_phrases.append(" ".join(current_phrase))
                current_phrase = []

    if current_phrase:
        location_phrases.append(" ".join(current_phrase))

    return potential_locations + location_phrases


def fuzzy_match_property_name(query: str, property_name: str) -> tuple[int, str]:
    """
    Perform fuzzy matching between query and property name.

    Args:
        query: Input query string
        property_name: Property name to match against

    Returns:
        Tuple of (match score, match type)
    """
    processed_query = enhance_brand_recognition(query)
    processed_name = preprocess_text(property_name)

    # Different matching strategies
    ratio_score = fuzz.ratio(processed_query, processed_name)
    partial_ratio = fuzz.partial_ratio(processed_query, processed_name)
    token_sort_ratio = fuzz.token_sort_ratio(processed_query, processed_name)
    token_set_ratio = fuzz.token_set_ratio(processed_query, processed_name)

    # Weighted average of different scores
    # Token set ratio works well for cases where word order doesn't matter
    # Partial ratio helps when the query is a subset of the property name
    weighted_score = ratio_score * 0.1 + partial_ratio * 0.3 + token_sort_ratio * 0.2 + token_set_ratio * 0.4

    # Determine match type for debugging
    match_type = "exact" if ratio_score > 90 else "partial" if weighted_score > 70 else "fuzzy"

    return int(weighted_score), match_type


def fuzzy_match_location(query_location: str, property_locations: list[str]) -> tuple[int, str]:
    """
    Match potentially misspelled location against property address components.

    Args:
        query_location: Location term from query
        property_locations: List of property address components

    Returns:
        Tuple of (match score, best matching location)
    """
    query_location = preprocess_text(query_location)
    best_score = 0
    best_match = ""

    for location in property_locations:
        location = preprocess_text(location)
        if not location:
            continue

        # Apply fuzzy matching techniques
        token_set_score = fuzz.token_set_ratio(query_location, location)
        partial_score = fuzz.partial_ratio(query_location, location)

        # Weighted score favoring token_set_ratio for location matching
        weighted_score = (token_set_score * 0.7) + (partial_score * 0.3)

        if weighted_score > best_score:
            best_score = weighted_score
            best_match = location

    return int(best_score), best_match


def match_property_with_query(query: str, property: dict[str, Any]) -> dict[str, Any]:
    """
    Match a property with a query using fuzzy matching.

    Args:
        query: Input query string
        property: Property dictionary

    Returns:
        Dictionary with property and match details
    """
    # Match property name
    property_name = property.get("metadata", {}).get("property_name", "")
    name_score, name_match_type = fuzzy_match_property_name(query, property_name)

    # Extract location information from property
    address = property.get("metadata", {}).get("address", {})
    property_locations = [
        address.get("city", ""),
        address.get("country", ""),
        f"{address.get('city', '')} {address.get('country', '')}",
        address.get("zip_code", ""),
    ]

    # Extract potential location terms from query
    location_terms = extract_locations(query)

    # Calculate best location match
    best_location_score = 0
    best_location_match = ""

    for term in location_terms:
        location_score, location_match = fuzzy_match_location(term, property_locations)
        if location_score > best_location_score:
            best_location_score = location_score
            best_location_match = location_match

    # Calculate combined score
    # Determine query focus: if multiple location terms, weight location higher
    location_terms_count = len(location_terms)
    location_weight = min(0.6, 0.2 + location_terms_count * 0.1)
    name_weight = 1.0 - location_weight

    # For external properties, boost the location score if they were found via location search
    # Updated to access 'source' field from _internal instead of metadata
    if (
        property.get("_internal", {}).get("is_external", False)
        and property.get("_internal", {}).get("source") == "amazon_location_service"
    ):
        best_location_score = max(best_location_score, 95)  # Boost location score

    combined_score = (name_score * name_weight) + (best_location_score * location_weight)

    return {
        "property": property,
        "name_score": name_score,
        "location_score": best_location_score,
        "combined_score": combined_score,
        "matched_location": best_location_match,
        "match_type": name_match_type,
    }


def get_ranked_properties(query: str, properties: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Get properties ranked by relevance to the query.

    Args:
        query: Input query string
        properties: List of properties to match

    Returns:
        List of properties with rank assigned based on match score
    """
    # Import here to avoid circular import issues
    try:
        from common.location_service import merge_properties, search_location_text, search_nearby_hotels

        location_service_available = True
    except ImportError:
        print("Location service module not available, falling back to local matching only")
        location_service_available = False

    # Match each property with the query
    matches = []
    for property in properties:
        match_result = match_property_with_query(query, property)
        matches.append(match_result)

    # Try location service integration if available
    external_properties = []
    if location_service_available:
        # Extract location terms from query
        location_terms = extract_locations(query)

        # If we identified a potential location with sufficient length, try the Location Service
        valid_location_terms = [term for term in location_terms if len(term) >= 3]
        if valid_location_terms:
            try:
                # Sort by length (descending) to prioritize longer location phrases
                # This ensures "san francisco" is used instead of just "san"
                valid_location_terms = sorted(valid_location_terms, key=len, reverse=True)

                # Use the longest extracted location term
                location_term = valid_location_terms[0]
                print(f"Trying Amazon Location Service with term: {location_term}")

                # Get coordinates for this location
                coordinates = search_location_text(location_term)

                # If we got coordinates, find nearby hotels
                if coordinates:
                    external_properties = search_nearby_hotels(coordinates)

                    # Merge with seed properties to avoid duplicates
                    # Always prioritizing our seed data over external properties
                    merged_properties = merge_properties(properties, external_properties)

                    # Start with a fresh list of matches
                    matches = []

                    # Process these merged properties with our matching algorithm
                    for property in merged_properties:
                        match_result = match_property_with_query(query, property)
                        matches.append(match_result)
            except Exception as e:
                print(f"Error using Amazon Location Service: {str(e)}")
                # Continue with just our properties

    # Sort by combined score
    matches.sort(key=lambda x: x["combined_score"], reverse=True)

    # Identify if there's a dominant location in the top results
    # This helps filter out irrelevant locations when a clear location is specified
    location_candidates = {}

    # Look at top 3 results to determine dominant location
    for match in matches[:3]:
        if match["location_score"] >= 70:  # High confidence location match
            location = match["matched_location"]
            if location:
                location_candidates[location] = location_candidates.get(location, 0) + 1

    # Apply location filtering if there's a clear dominant location
    filtered_matches = matches
    if location_candidates:
        # Find most common high-scoring location
        dominant_location = max(location_candidates.items(), key=lambda x: x[1])[0]

        # If we have a clear dominant location, filter matches
        if dominant_location:
            print(f"Dominant location detected: {dominant_location}")
            filtered_matches = [
                match
                for match in matches
                if (match["matched_location"].lower() == dominant_location.lower() and match["location_score"] >= 50)
                or (match["location_score"] >= 90)  # Keep extremely high location matches regardless
                or match["property"]
                .get("_internal", {})
                .get("is_external", False)  # Keep external properties from Amazon Location Service
            ]

            # Ensure we have at least some results
            if not filtered_matches and matches:
                print("Location filtering too strict, falling back to original results")
                filtered_matches = matches

    # Create result list with ranks - clean up schema
    result = []
    for i, match in enumerate(filtered_matches):
        # Only include properties with a combined score above 30
        if match["combined_score"] > 30:
            property_copy = copy.deepcopy(match["property"])

            # Clean up schema by removing internal fields
            if "_internal" in property_copy:
                del property_copy["_internal"]

            # Add rank based on position in sorted results
            property_copy["rank"] = i + 1
            result.append(property_copy)

    return result
