# Bruno API Testing Setup

This directory contains Bruno API tests for the AgentCore Tech Summit mock APIs.

## Quick Start

### 1. Deploy the APIs

```bash
# From the monorepo root
pnpm cdk deploy AgentCoreTechSummitMockApis
```

### 2. Update Environment Files

After deployment, update the environment files with your actual API URLs and keys:

#### Reservation Services API

Edit `booking_mock_apis/environments/Reservations.bru`:

```
vars {
  apiUrl: https://YOUR-ACTUAL-API-ID.execute-api.YOUR-REGION.amazonaws.com/v1/
  # ... rest of the variables stay the same
}
```

#### Property Resolution API

Edit `booking_mock_apis/environments/PropertyResolution.bru`:

```
vars {
  apiUrl: https://YOUR-ACTUAL-API-ID.execute-api.YOUR-REGION.amazonaws.com/v1/
  apiKey: YOUR-ACTUAL-API-KEY
  testId: {{$timestamp}}
}
```

#### Toxicity Detection API

Edit `booking_mock_apis/environments/ToxicityDetection.bru`:

```
vars {
  BASE_URL: https://YOUR-ACTUAL-API-ID.execute-api.YOUR-REGION.amazonaws.com/v1/
  API_KEY: YOUR-ACTUAL-API-KEY
}
```

### 3. Run Tests

From the monorepo root:

```bash
# Run all API tests
pnpm test:apis:all

# Run individual API tests
pnpm test:apis:property-resolution
pnpm test:apis:reservations
pnpm test:apis:toxicity
```

## Getting API URLs and Keys from Stack Outputs

After deploying, get your API URLs and keys:

```bash
aws cloudformation describe-stacks \
  --stack-name AgentCoreTechSummitMockApis \
  --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
  --output table
```

Look for these outputs:

- `ReservationServicesApiUrl` → Use for Reservations.bru
- `PropertyResolutionApiUrl` → Use for PropertyResolution.bru
- `PropertyResolutionApiKeyId` → API Key ID for Property Resolution API
- `ToxicityDetectionApiUrl` → Use for ToxicityDetection.bru
- `ToxicityDetectionApiKeyId` → API Key ID for Toxicity Detection API

### Getting API Key Values

To get the actual API key values (not just the IDs), use:

```bash
# Property Resolution API Key
aws apigateway get-api-key --api-key <PropertyResolutionApiKeyId> --include-value --query 'value' --output text

# Toxicity Detection API Key
aws apigateway get-api-key --api-key <ToxicityDetectionApiKeyId> --include-value --query 'value' --output text
```

## Test Structure

### Property Resolution Tests

- **Basic_Flow**: Standard property search functionality
- **Error_Flow**: Error handling and validation
- **Location_Flow**: Location-based search scenarios

### Reservation Services Tests

- **SF_Flow**: San Francisco hotel reservation workflow
- **NY_Flow**: New York hotel reservation workflow
- **Filter_Flow**: Reservation filtering and querying
- **Error_Flow**: Error handling scenarios

### Toxicity Detection Tests

- **Basic_Flow**: Standard toxicity detection
- **Edge_Cases**: Edge cases and boundary conditions
- **Error_Flow**: Error handling and validation

## Troubleshooting

### Common Issues

1. **Connection Errors**

   - Verify API URLs are correct in environment files
   - Ensure APIs are deployed and accessible

2. **Authentication Errors**

   - Check API keys are correctly configured
   - Verify OAuth tokens for Reservation Services

3. **Test Failures**
   - Check CloudWatch logs for Lambda function errors
   - Verify DynamoDB tables have sample data

### Manual Testing

You can also run Bruno tests manually:

```bash
# Navigate to test directory
cd packages/cdk-infra-python/tests/bruno/booking_mock_apis

# Run specific test
bru run PropertyResolution/Basic_Flow --env PropertyResolution

# Run with custom delay
bru run Reservations/SF_Flow --env Reservations --delay 500
```

## Environment Variables Reference

### Reservations.bru (Reservations API)

- `apiUrl`: Base URL for Reservation Services API
- `testId`: Timestamp for unique test data
- Hotel and guest data for test scenarios

### PropertyResolution.bru

- `apiUrl`: Base URL for Property Resolution API
- `apiKey`: API key for authentication
- `testId`: Timestamp for unique test data

### ToxicityDetection.bru

- `BASE_URL`: Base URL for Toxicity Detection API
- `API_KEY`: API key for authentication
