---
title: Testing Guide
description: Comprehensive guide for testing the mock APIs during the AgentCore Vibe Coding workshop.
---

This guide provides detailed instructions for testing and validating the mock APIs functionality during the workshop.

## Testing Overview

The mock APIs include comprehensive test suites using Bruno API client, which provides:

- **Pre-configured test collections** for all three APIs
- **Environment-based configuration** for different deployment stages
- **Automated test execution** for validation
- **Response validation** and assertion testing

## Bruno API Client Setup

### Installation

```bash
# Install Bruno CLI globally
npm install -g @usebruno/cli

# Verify installation
bru --version
```

### Test Structure

The test files are organized as follows:

```
packages/cdk-infra-python/tests/bruno/booking_mock_apis/
├── environments/
│   └── local.bru                    # Environment configuration
├── Property Resolution/
│   ├── Property Search.bru          # Basic property search test
│   └── Property Search Advanced.bru # Advanced search scenarios
├── Reservation Services/
│   ├── Get Reservations.bru         # Query reservations
│   ├── Create Reservation.bru       # Create new reservation
│   ├── Modify Reservation.bru       # Update reservation
│   ├── Cancel Reservation.bru       # Cancel reservation
│   └── Fetch Reservation.bru        # Get specific reservation
├── Toxicity Detection/
│   ├── Basic Toxicity Check.bru     # Basic toxicity analysis
│   └── Advanced Toxicity.bru        # Multi-category analysis
└── bruno.json                       # Collection configuration
```

## Environment Configuration

### Update API URLs

After deploying the mock APIs, update the Bruno environment with your API URLs:

```bash
# Navigate to the test directory
cd packages/cdk-infra-python/tests/bruno/booking_mock_apis

# Edit the environment file
nano environments/local.bru
```

Update the environment file with your deployed API URLs and keys:

```javascript
vars {
  property_resolution_url: https://your-property-api-id.execute-api.region.amazonaws.com/v1
  reservations_url: https://your-reservations-api-id.execute-api.region.amazonaws.com/v1
  toxicity_detection_url: https://your-toxicity-api-id.execute-api.region.amazonaws.com/v1
  property_api_key: your-actual-property-api-key
  toxicity_api_key: your-actual-toxicity-api-key
}
```

### Get API URLs and Keys from Stack Outputs

```bash
# Get all stack outputs
aws cloudformation describe-stacks \
  --stack-name VibeCodingWorkshopMockApis \
  --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
  --output table

# Get API key values (after getting key IDs from outputs above)
PROPERTY_KEY_ID="your-property-key-id-from-outputs"
TOXICITY_KEY_ID="your-toxicity-key-id-from-outputs"

aws apigateway get-api-key --api-key $PROPERTY_KEY_ID --include-value --query 'value' --output text
aws apigateway get-api-key --api-key $TOXICITY_KEY_ID --include-value --query 'value' --output text
  --output table
```

## Running Tests

### Run All Tests

```bash
# Navigate to test directory
cd packages/cdk-infra-python/tests/bruno/booking_mock_apis

# Run all tests
bru run --env local
```

### Run Specific API Tests

```bash
# Test only Property Resolution
bru run --env local --folder "Property Resolution"

# Test only Reservation Services
bru run --env local --folder "Reservation Services"

# Test only Toxicity Detection
bru run --env local --folder "Toxicity Detection"
```

### Run Individual Tests

```bash
# Run a specific test file
bru run --env local "Property Resolution/Property Search.bru"
```

## Test Scenarios

### Property Resolution Service Tests

#### Basic Property Search

**Test**: `Property Resolution/Property Search.bru`

**Purpose**: Validates basic property search functionality

**Request**:

```json
{
  "unique_client_id": "AWS_PACE_Agent",
  "anon_guest_id": "test-guest-123",
  "input": {
    "query": "hotels in San Francisco"
  },
  "session_context": {
    "session_id": "test-session-123",
    "local_ts": "2024-01-15T10:30:00Z",
    "country_name": "United States",
    "city_name": "San Francisco"
  }
}
```

**Expected Response**:

- Status Code: 200
- Response contains ranked hotel results
- Each result has required fields: `spirit_cd`, `hotel_id`, `metadata`, `rank`

#### Advanced Property Search

**Test**: `Property Resolution/Property Search Advanced.bru`

**Purpose**: Tests complex queries and edge cases

**Scenarios**:

- Misspelled city names
- Vague location queries
- Specific amenity requests
- Date-based searches

### Reservation Services Tests

#### Query Reservations

**Test**: `Reservation Services/Get Reservations.bru`

**Purpose**: Validates reservation querying with filters

**Query Parameters**:

- `status`: Filter by reservation status
- `arrival`: Date range for arrival dates
- `pageStart`: Pagination offset
- `pageSize`: Number of results per page

**Expected Response**:

- Status Code: 200
- Paginated reservation results
- Proper filtering applied

#### Create Reservation

**Test**: `Reservation Services/Create Reservation.bru`

**Purpose**: Tests new reservation creation

**Request Body**:

```json
{
  "Hotel": {
    "Id": 10001,
    "Name": "Sample Hotel",
    "Code": "SMPL"
  },
  "Guest": {
    "FirstName": "John",
    "LastName": "Doe",
    "Email": "john.doe@example.com"
  },
  "RoomStay": {
    "CheckInDate": "2024-02-15",
    "CheckOutDate": "2024-02-18",
    "NumberOfNights": 3
  }
}
```

**Expected Response**:

- Status Code: 201
- Created reservation with confirmation number
- All input data preserved in response

#### Modify Reservation

**Test**: `Reservation Services/Modify Reservation.bru`

**Purpose**: Tests reservation updates

**Expected Response**:

- Status Code: 200
- Updated reservation data
- Modification timestamp

#### Cancel Reservation

**Test**: `Reservation Services/Cancel Reservation.bru`

**Purpose**: Tests reservation cancellation

**Expected Response**:

- Status Code: 200
- Cancellation confirmation
- Refund/fee information

#### Fetch Specific Reservation

**Test**: `Reservation Services/Fetch Reservation.bru`

**Purpose**: Tests retrieval of specific reservation by ID

**Expected Response**:

- Status Code: 200
- Complete reservation details
- Matches requested reservation ID

### Toxicity Detection Service Tests

#### Basic Toxicity Check

**Test**: `Toxicity Detection/Basic Toxicity Check.bru`

**Purpose**: Validates basic toxicity analysis

**Request**:

```json
{
  "text": "I'm really frustrated with this booking process!",
  "region_name": "NA"
}
```

**Expected Response**:

- Status Code: 200
- Toxicity scores for all categories
- Scores between 0.0 and 1.0

#### Advanced Toxicity Analysis

**Test**: `Toxicity Detection/Advanced Toxicity.bru`

**Purpose**: Tests various content types and edge cases

**Test Cases**:

- Clean text (low toxicity scores)
- Mildly negative text (moderate scores)
- Profanity (high obscenity scores)
- Threats (high threat scores)
- Empty text (error handling)

## Manual Testing

### Using curl Commands

For manual testing without Bruno:

#### Property Resolution

```bash
curl -X POST "https://your-api-url/api/v1/property-resolution" \
  -H "Content-Type: application/json" \
  -H "X-Api-Key: workshop-api-key" \
  -d '{
    "unique_client_id": "test",
    "anon_guest_id": "test-guest",
    "input": {
      "query": "luxury hotels in San Francisco"
    },
    "session_context": {
      "session_id": "test-session",
      "local_ts": "2024-01-15T10:30:00Z",
      "country_name": "United States",
      "city_name": "San Francisco"
    }
  }'
```

#### Reservation Services - Query

```bash
curl -X GET "https://your-api-url/api/v1/reservation?status=Confirmed&pageSize=10"
```

#### Toxicity Detection

```bash
curl -X POST "https://your-api-url/api/v1/toxicity-detection" \
  -H "Content-Type: application/json" \
  -H "X-Api-Key: workshop-api-key" \
  -d '{
    "text": "This is a test message for toxicity analysis",
    "region_name": "NA"
  }'
```

### Using Postman

Import the OpenAPI specifications for Postman testing:

1. **Import Specs**:

   - `packages/cdk-infra-python/specs/property-resolution-service.yaml`
   - `packages/cdk-infra-python/specs/reservations_services_10_35_minimal_openapi_3_0.yaml`
   - `packages/cdk-infra-python/specs/toxicity-detection-service.yaml`

2. **Configure Environment**:

   - Set base URLs from stack outputs
   - Configure API keys and OAuth tokens

3. **Run Collections**:
   - Execute pre-configured request collections
   - Validate responses against expected schemas

## Performance Testing

### Load Testing with Artillery

For workshop load testing:

```bash
# Install Artillery
npm install -g artillery

# Create load test configuration
cat > load-test.yml << EOF
config:
  target: 'https://your-api-url'
  phases:
    - duration: 60
      arrivalRate: 10
  defaults:
    headers:
      X-Api-Key: 'workshop-api-key'
      Content-Type: 'application/json'

scenarios:
  - name: "Property Search Load Test"
    requests:
      - post:
          url: "/api/v1/property-resolution"
          json:
            unique_client_id: "load-test"
            anon_guest_id: "guest-{{ \$randomNumber() }}"
            input:
              query: "hotels in {{ \$randomString() }}"
EOF

# Run load test
artillery run load-test.yml
```

### Monitoring During Tests

Monitor API performance during testing:

```bash
# Watch CloudWatch metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApiGateway \
  --metric-name Count \
  --dimensions Name=ApiName,Value=PropertyResolutionApi \
  --start-time 2024-01-15T10:00:00Z \
  --end-time 2024-01-15T11:00:00Z \
  --period 300 \
  --statistics Sum

# Monitor Lambda metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=VibeCodingWorkshopMockApis-PropertyResolution-PropertyResolutionFunction \
  --start-time 2024-01-15T10:00:00Z \
  --end-time 2024-01-15T11:00:00Z \
  --period 300 \
  --statistics Average,Maximum
```

## Troubleshooting Tests

### Common Test Failures

#### 1. Authentication Errors

**Error**: `401 Unauthorized`

**Solutions**:

- Verify API keys are correctly configured for Property Resolution and Toxicity Detection
- Ensure API key values are retrieved from AWS API Gateway (not placeholder values)
- Note: Reservation Services requires no authentication

#### 2. Network Timeouts

**Error**: `Request timeout`

**Solutions**:

- Check API Gateway endpoints are accessible
- Verify Lambda functions aren't cold starting excessively
- Increase timeout values in Bruno configuration

#### 3. Data Validation Errors

**Error**: `400 Bad Request` with validation messages

**Solutions**:

- Check request body format matches API specification
- Verify required fields are included
- Validate date formats and data types

#### 4. Rate Limiting

**Error**: `429 Too Many Requests`

**Solutions**:

- Reduce test execution frequency
- Check API Gateway throttling settings
- Implement retry logic with backoff

### Debug Mode

Run tests with verbose output for debugging:

```bash
# Run with debug information
bru run --env local --verbose

# Run single test with full output
bru run --env local --verbose "Property Resolution/Property Search.bru"
```

### Log Analysis

Check Lambda logs for detailed error information:

```bash
# View recent logs for Property Resolution
aws logs tail /aws/lambda/VibeCodingWorkshopMockApis-PropertyResolution-PropertyResolutionFunction \
  --follow --format short

# Search for errors in logs
aws logs filter-log-events \
  --log-group-name /aws/lambda/VibeCodingWorkshopMockApis-PropertyResolution-PropertyResolutionFunction \
  --filter-pattern "ERROR"
```

## Test Automation

### CI/CD Integration

For automated testing in CI/CD pipelines:

```bash
# Create test script
cat > test-apis.sh << EOF
#!/bin/bash
set -e

echo "Running API tests..."
cd packages/cdk-infra-python/tests/bruno/booking_mock_apis

# Run tests and capture results
bru run --env local --output results.json

# Check if tests passed
if [ $? -eq 0 ]; then
  echo "All tests passed!"
  exit 0
else
  echo "Tests failed!"
  exit 1
fi
EOF

chmod +x test-apis.sh
```

### Scheduled Testing

Set up scheduled testing with cron:

```bash
# Add to crontab for hourly testing
0 * * * * /path/to/test-apis.sh >> /var/log/api-tests.log 2>&1
```

---

**Next**: Return to [APIs Overview](/apis/overview) for additional information about the mock APIs.
