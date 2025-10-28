# Bruno API Testing Setup

This directory contains Bruno API tests for the sample mock APIs.

## Quick Start

### 1. Deploy the APIs

```bash
# From the monorepo root
pnpm cdk deploy AgentCoreTechSummitMockApis
```

### 2. Set AWS Credentials for Authentication

The APIs require AWS SigV4 authentication. Set up credentials in your terminal session:

```bash
# Navigate to Bruno tests directory
cd packages/cdk-infra-python/tests/bruno/

# Source the helper script to export AWS credentials to environment variables
source ./set-aws-creds.sh
```

**Important:** The credentials are only available in the terminal session where you run this script. You must run Bruno tests from the same terminal.

### 3. Update Environment Files

After deployment, update the environment files with your actual API URLs and keys:

#### Property Resolution API

Edit `booking_mock_apis/environments/PropertyResolution.bru`:

```
vars {
  apiUrl: https://YOUR_PROPERTY_API_ID.execute-api.YOUR_REGION.amazonaws.com/dev/api/v1
  apiKey: YOUR_PROPERTY_RESOLUTION_API_KEY
  testId: {{$timestamp}}
  awsRegion: YOUR_REGION
  awsAccessKeyId: {{process.env.AWS_ACCESS_KEY_ID}}
  awsSecretAccessKey: {{process.env.AWS_SECRET_ACCESS_KEY}}
  awsSessionToken: {{process.env.AWS_SESSION_TOKEN}}
}
```

#### Reservation Services API

Edit `booking_mock_apis/environments/Reservations.bru`:

```
vars {
  apiUrl: https://YOUR_RESERVATIONS_API_ID.execute-api.YOUR_REGION.amazonaws.com/v1/
  awsRegion: YOUR_REGION
  awsAccessKeyId: {{process.env.AWS_ACCESS_KEY_ID}}
  awsSecretAccessKey: {{process.env.AWS_SECRET_ACCESS_KEY}}
  awsSessionToken: {{process.env.AWS_SESSION_TOKEN}}
  # ... rest of the variables stay the same
}
```

#### Toxicity Detection API

Edit `booking_mock_apis/environments/ToxicityDetection.bru`:

```
vars {
  BASE_URL: https://YOUR_TOXICITY_API_ID.execute-api.YOUR_REGION.amazonaws.com/v1/
  API_KEY: YOUR_TOXICITY_DETECTION_API_KEY
  awsRegion: YOUR_REGION
  awsAccessKeyId: {{process.env.AWS_ACCESS_KEY_ID}}
  awsSecretAccessKey: {{process.env.AWS_SECRET_ACCESS_KEY}}
  awsSessionToken: {{process.env.AWS_SESSION_TOKEN}}
}
```

### 4. Run Tests

From the monorepo root:

```bash
# Run all API tests
pnpm test:apis:all

# Run individual API tests
pnpm test:apis:property-resolution
pnpm test:apis:reservations
pnpm test:apis:toxicity
```

## Authentication Requirements

The APIs are protected by AWS resource policies and require:

- **AWS SigV4 signing** (handled automatically by Bruno with credentials)
- **API keys** (configured in environment files)

### Troubleshooting Authentication

If you get 403 Forbidden errors:

1. **Verify AWS credentials**:

   ```bash
   aws sts get-caller-identity
   ```

2. **Check environment variables are set**:

   ```bash
   echo $AWS_ACCESS_KEY_ID
   echo $AWS_SECRET_ACCESS_KEY
   ```

3. **For SSO users, refresh token**:
   ```bash
   aws sso login --profile your-profile
   ```

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
