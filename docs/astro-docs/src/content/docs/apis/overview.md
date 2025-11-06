---
title: Mock APIs Overview
description: Comprehensive guide to the three mock API services that support the AgentCore Vibe Coding workshop.
---

This guide covers the three mock API services that provide backend functionality for the workshop. These services simulate real hotel industry APIs and provide realistic data for training purposes.

## Overview

The workshop includes three CDK-deployed mock services:

| Service                  | Purpose                    | Key Features                               |
| ------------------------ | -------------------------- | ------------------------------------------ |
| **Property Resolution**  | Hotel search and discovery | Natural language queries, ranked results   |
| **Reservation Services** | Booking management         | Full CRUD operations, guest management     |
| **Toxicity Detection**   | Content moderation         | Multi-category analysis, sentiment scoring |

## 🏨 Property Resolution Service

**Purpose**: Converts natural language queries into ranked hotel property results

### Key Features

#### Natural Language Processing

- **Input**: Conversational queries like "luxury hotels near the beach"
- **Processing**: Handles misspellings and grammatical errors
- **Output**: Structured, ranked property results

#### Comprehensive Property Data

- **Hotel Metadata**: Name, address, unique identifiers
- **Location Information**: City, country, postal codes
- **Ranking System**: Relevance-based result ordering
- **Multi-Brand Discovery**: Searches across all major hotel brands (Marriott, Hilton, Hyatt, IHG, etc.)

#### Amazon Location Service Integration

- **Dynamic Discovery**: Uses Amazon Location Service to find hotels beyond seeded data
- **Real-Time Results**: Discovers and stores new properties automatically
- **Broad Coverage**: Searches all hotel brands, not limited to specific chains

### API Endpoint

```http
POST /api/v1/property-resolution
Content-Type: application/json
X-Api-Key: {your-api-key}
```

### Request Format

```json
{
  "unique_client_id": "AWS_PACE_Agent",
  "anon_guest_id": "guest-12345",
  "input": {
    "query": "luxury hotels in San Francisco with ocean views"
  },
  "session_context": {
    "session_id": "session-abc123",
    "local_ts": "2024-01-15T10:30:00Z",
    "country_name": "United States",
    "city_name": "New York"
  }
}
```

### Response Format

```json
{
  "statusCode": 200,
  "result": [
    {
      "spirit_cd": "HCSF",
      "hotel_id": 10001,
      "metadata": {
        "property_name": "Luxury Hotel San Francisco",
        "address": {
          "address_line_1": "555 North Point St",
          "city": "San Francisco",
          "zip_code": "94133",
          "country": "United States"
        }
      },
      "rank": 1
    }
  ]
}
```

## 🏢 Reservation Services

**Purpose**: Complete reservation lifecycle management with full CRUD operations

### Key Features

#### Reservation Management

- **Create**: New bookings with guest and payment info
- **Retrieve**: Query reservations by multiple criteria
- **Update**: Modify existing reservations
- **Cancel**: Process cancellations with policies
- **Room Availability**: Check available rooms and pricing for specific dates
- **Payment Validation**: Validate credit card information before booking

#### Guest Information Handling

- **Personal Details**: Names, contact information, preferences
- **Payment Processing**: Multiple payment methods and split payments
- **Special Requests**: Comments and accommodation needs

#### Flexible Querying

- **Status Filtering**: Booked, Confirmed, Cancelled, etc.
- **Date Ranges**: Arrival/departure date searches
- **Pagination**: Large result set handling

### API Endpoints

#### Query Reservations

```http
GET /api/v1/reservation?status=Confirmed&arrival=2024-01-15;2024-01-20
Authorization: Bearer {oauth-token}
```

#### Create Reservation

```http
POST /api/v1/reservation
Authorization: Bearer {oauth-token}
Content-Type: application/json
```

#### Modify Reservation

```http
PATCH /api/v1/reservation
Authorization: Bearer {oauth-token}
Content-Type: application/json
```

#### Cancel Reservation

```http
POST /api/v1/reservation/cancel
Authorization: Bearer {oauth-token}
Content-Type: application/json
```

#### Get Specific Reservation

```http
GET /api/v1/reservation/hotel/{hotelId}/{id}
```

#### Check Room Availability

```http
GET /api/v1/reservation/availability?hotel_id=HCSF&check_in_date=2024-03-15&check_out_date=2024-03-17
```

#### Validate Payment Details

```http
POST /api/v1/reservation/payment/validate
Content-Type: application/json
```

## 🛡️ Toxicity Detection Service

**Purpose**: Content moderation and safety analysis for user interactions

### Key Features

#### Multi-Category Analysis

- **Overall Toxicity**: General harmful content detection
- **Specific Categories**: Threats, insults, hate speech, obscenity
- **Sentiment Analysis**: Negative emotion detection
- **Escalation Detection**: Identifies when human intervention needed

#### Configurable Thresholds

- **Toxicity Levels**: Adjustable sensitivity settings
- **Category-Specific**: Different thresholds per category
- **Action Triggers**: Automated escalation or filtering

### API Endpoint

```http
POST /api/v1/toxicity-detection
Content-Type: application/json
X-Api-Key: {your-api-key}
```

### Request Format

```json
{
  "text": "I'm really frustrated with this booking process!",
  "region_name": "NA"
}
```

### Response Format

```json
{
  "toxic": 0.15,
  "severe_toxic": 0.02,
  "obscene": 0.01,
  "threat": 0.0,
  "insult": 0.08,
  "identity_hate": 0.0,
  "negative_sentiment_score": 0.75
}
```

## 🧪 Testing the APIs

### Using pnpm Scripts

The workshop includes pre-configured test scripts for all APIs:

```bash
# Test all APIs
pnpm test:apis:all

# Test individual APIs
pnpm test:apis:property-resolution
pnpm test:apis:reservations
pnpm test:apis:toxicity
```

### Quick API Testing

Test the APIs directly with curl using your API keys:

```bash
# Test Property Resolution (requires API key)
curl -X POST "https://your-property-api-url/api/v1/property-resolution" \
  -H "Content-Type: application/json" \
  -H "X-Api-Key: $PROPERTY_API_KEY" \
  -d '{"input": {"query": "hotels in San Francisco"}}'

# Test Toxicity Detection (requires API key)
curl -X POST "https://your-toxicity-api-url/api/v1/toxicity-detection" \
  -H "Content-Type: application/json" \
  -H "X-Api-Key: $TOXICITY_API_KEY" \
  -d '{"text": "This is a test message"}'

# Test Reservation Services (no authentication required)
curl -X GET "https://your-reservations-api-url/api/v1/reservation"
```

## 📊 Monitoring and Troubleshooting

### CloudWatch Logs

All Lambda functions log to CloudWatch with 1-week retention:

- `/aws/lambda/VibeCodingWorkshopMockApis-ReservationServices-*`
- `/aws/lambda/VibeCodingWorkshopMockApis-PropertyResolution-*`
- `/aws/lambda/VibeCodingWorkshopMockApis-ToxicityDetection-*`

### Common Issues

1. **API Key Authentication Failures**

   - Verify API key is included in `X-Api-Key` header
   - Check API key format and validity

2. **OAuth2 Token Issues (Reservations API)**

   - Ensure Bearer token is properly formatted
   - Verify token hasn't expired

3. **DynamoDB Throttling**

   - APIs use on-demand billing mode
   - Should handle normal workshop loads automatically

4. **Lambda Timeouts**
   - Functions have 30-second timeout
   - Check CloudWatch logs for performance issues

---

For more detailed testing procedures, see the [API Testing Guide](/apis/testing/).
