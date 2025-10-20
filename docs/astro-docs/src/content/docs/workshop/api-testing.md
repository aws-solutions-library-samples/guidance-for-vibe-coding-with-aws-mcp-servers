---
title: API Testing Guide
description: Learn about the mock APIs using interactive test files and Bruno CLI
---

This guide helps you understand and test the three mock APIs that support your AgentCore hotel booking agent. Use the provided Bruno test files to explore API functionality and understand how the agent interacts with these services.

## Overview of Mock APIs

Your AgentCore hotel booking agent integrates with three mock APIs:

<CardGrid>
<Card title="🏨 Property Resolution API" icon="external">

**Purpose**: Natural language hotel search and discovery

**Key Features**:

- Converts queries like "luxury hotels near the beach" into ranked results
- Integrates with Amazon Location Service for dynamic discovery
- Returns structured hotel data for the agent to process

</Card>
<Card title="🏢 Reservation Services API" icon="puzzle">

**Purpose**: Complete booking lifecycle management

**Key Features**:

- Create, modify, and cancel hotel reservations
- Manage guest information and payment processing
- Check room availability and pricing

</Card>
<Card title="🛡️ Toxicity Detection API" icon="shield">

**Purpose**: Content moderation and safety analysis

**Key Features**:

- Analyze user messages for harmful content
- Multi-category detection (threats, insults, hate speech)
- Automated escalation triggers

</Card>
</CardGrid>

## Testing with Bruno CLI

The workshop includes pre-configured Bruno test files that let you interact with the APIs directly.

### Setup Bruno Testing

<Steps>

1. **Navigate to Test Directory**

   ```bash
   cd packages/cdk-infra-python/tests/bruno/booking_mock_apis
   ```

2. **Update Environment Variables**

   After deploying your AgentCore system, update the Bruno environment with your API URLs and keys:

   ```bash
   # Get your API URLs from CloudFormation outputs
   aws cloudformation describe-stacks \
     --stack-name AgentCoreTechSummitMockApis \
     --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
     --output table
   ```

3. **Run All Tests**

   ```bash
   bru run --env local
   ```

4. **Run Specific API Tests**

   ```bash
   # Test only Property Resolution API
   bru run --env local --folder "Property Resolution"

   # Test only Reservation Services API
   bru run --env local --folder "Reservation Services"

   # Test only Toxicity Detection API
   bru run --env local --folder "Toxicity Detection"
   ```

</Steps>

## Understanding API Interactions

### Property Resolution API Testing

**Sample Request**: Search for hotels in San Francisco

```json
{
  "unique_client_id": "workshop_participant",
  "anon_guest_id": "guest-12345",
  "input": {
    "query": "luxury hotels in San Francisco with ocean views"
  },
  "session_context": {
    "session_id": "session-abc123",
    "local_ts": "2024-01-15T10:30:00Z",
    "country_name": "United States",
    "city_name": "San Francisco"
  }
}
```

**What to Observe**:

- How natural language queries are processed
- The ranking system for hotel results
- Integration with Amazon Location Service

### Reservation Services API Testing

**Sample Operations**:

- Query existing reservations
- Create new bookings
- Check room availability
- Validate payment information

**What to Observe**:

- Complete booking workflow from search to confirmation
- Guest information management
- Payment processing and validation

### Toxicity Detection API Testing

**Sample Request**: Analyze user message content

```json
{
  "text": "I'm really frustrated with this booking process!",
  "region_name": "NA"
}
```

**What to Observe**:

- Content analysis across multiple categories
- Scoring system for different types of harmful content
- Escalation triggers and thresholds

## Integration with AgentCore Agent

### How the Agent Uses These APIs

1. **User Request Processing**

   - Agent receives natural language input from user
   - Determines which APIs are needed to fulfill the request
   - Uses MCP server to coordinate API calls

2. **API Orchestration**

   - **Property Resolution**: For hotel search and discovery
   - **Reservation Services**: For booking operations
   - **Toxicity Detection**: For content safety analysis

3. **Response Synthesis**
   - Agent combines results from multiple APIs
   - Provides intelligent, contextual responses to users
   - Handles errors and edge cases gracefully

### Testing Agent Integration

After understanding the individual APIs, you can test how your AgentCore agent orchestrates them:

```bash
# Test the complete agent workflow
# (Instructions for agent testing will be provided during deployment)
```

## Phase 2 Activity: API Discovery

During **Phase 2: Discovery & Analysis**, use these Bruno tests to:

1. **Explore API Functionality**

   - Run the test suites to understand what each API does
   - Examine request/response formats
   - Identify integration patterns

2. **Analyze Business Logic**

   - Understand hotel search ranking algorithms
   - Explore booking workflow and validation rules
   - Review content moderation policies

3. **Discover Enhancement Opportunities**
   - Identify areas for improvement or new features
   - Consider how the agent could better utilize these APIs
   - Plan enhancements for Phase 3 implementation

<Aside type="tip">
**Pro Tip**: Use the Bruno test results to inform your Phase 3 enhancement choices. Understanding how the APIs currently work will help you identify meaningful improvements to implement.
</Aside>

## Troubleshooting API Tests

### Common Issues

**Authentication Errors**

- Verify API keys are correctly configured in Bruno environment
- Check that CloudFormation stack deployment completed successfully

**Connection Timeouts**

- Ensure your AWS credentials are valid and not expired
- Verify the API Gateway endpoints are accessible

**Test Failures**

- Check that sample data was properly seeded during deployment
- Verify the API responses match expected formats

### Getting Help

If you encounter issues with API testing:

1. Check the CloudFormation stack status and outputs
2. Verify your AWS credentials and permissions
3. Ask trainers for assistance during the workshop
4. Review the API documentation in the trainer materials

---

**Next**: Use your API testing insights to inform your choices during [Workshop Phases](/workshop/phases/) and [Tasks & Activities](/workshop/tasks/).
