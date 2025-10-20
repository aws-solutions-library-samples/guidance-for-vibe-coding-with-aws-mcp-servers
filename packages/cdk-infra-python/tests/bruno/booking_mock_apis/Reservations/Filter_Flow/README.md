# Reservation Filter Tests

This test flow provides comprehensive testing of the GET /reservation filtering capabilities using Bruno API client.

## Test Flow Overview

The flow follows these steps:

1. **Create Test Reservations** (files 01-03):

   - Chicago Regency Hotel (03/15-03/20, Confirmed status)
   - Mountain View Hotel (04/10-04/15, Booked status)
   - Chicago Magnificent Mile Hotel (03/20-03/25, Confirmed status)

2. **Test Basic Retrieval** (file 04):

   - Get all reservations

3. **Test Status Filters** (files 05-06):

   - Filter by single status: "Confirmed"
   - Filter by multiple statuses: "Confirmed,Booked"

4. **Test Date Range Filters** (files 07-08):

   - Filter by arrival date range: 03/10-03/25
   - Filter by departure date range: 03/20-04/01

5. **Test Confirmation Number Filters** (files 09-10):

   - Filter by single confirmation number
   - Filter by multiple confirmation numbers

6. **Test Combined Filters** (file 11):

   - Combined status and arrival date filters

7. **Test Pagination** (file 12):

   - Control result size with pageStart=0, pageSize=2

8. **Cleanup Test Data** (files 13-15):
   - Cancel Chicago Regency reservation
   - Update Mountain View reservation status to Confirmed (prerequisite for cancellation)
   - Cancel Mountain View reservation
   - Cancel Chicago Magnificent Mile reservation

## Running the Tests

To run the entire flow:

```bash
cd packages/cdk-infra-python/tests/bruno/booking_mock_apis
bru run Reservations/Filter_Flow --env Reservations
```

To run specific tests:

```bash
# Run setup (creating test reservations)
bru run Reservations/Filter_Flow/01_Create_Chicago_Reservation.bru Reservations/Filter_Flow/02_Create_MountainView_Reservation.bru Reservations/Filter_Flow/03_Create_ChicagoMagnificent_Reservation.bru --env Reservations

# Run filter tests (after setup)
bru run Reservations/Filter_Flow/05_Filter_By_Status_Confirmed.bru --env Reservations

# Run cleanup (after testing)
bru run Reservations/Filter_Flow/13_Cancel_Chicago_Reservation.bru Reservations/Filter_Flow/13_5_Update_MountainView_Status.bru Reservations/Filter_Flow/14_Cancel_MountainView_Reservation.bru Reservations/Filter_Flow/15_Cancel_ChicagoMagnificent_Reservation.bru --env Reservations
```

## Tests Description

Each test applies specific filters and validates the expected results:

### Status Filters

Tests that reservations can be filtered by their status value, with both single and multiple status filters supported.

### Date Range Filters

Tests that reservations can be filtered by check-in and check-out dates, supporting date range queries.

### Confirmation Number Filters

Tests that specific reservations can be retrieved by their confirmation number(s).

### Combined Filters

Tests that multiple filter parameters can be combined for precise querying.

### Pagination Tests

Ensures that results can be limited and paginated properly.

## Environment Variables

The tests use Bruno environment variables to store and retrieve reservation confirmation numbers. These variables are automatically set during test execution.

- `chicagoConfirmationNumber`: Chicago Regency reservation confirmation
- `mvConfirmationNumber`: Mountain View reservation confirmation
- `chicagoMileConfirmationNumber`: Chicago Magnificent Mile reservation confirmation
