# Stations App (`apps/stations`)

This application is responsible for managing everything related to stations (gas stations, service centers) within the system, tracking their branches, services offered, workers, and operations (refueling, wash, etc.) conducted on cars.

## Models

### Core Models
- **`Station`**: Represents the main entity of a gas/service station. It has a balance, name, location (lat/lang/district).
- **`StationBranch`**: Represents individual branches of a `Station`. It holds specific location data, balance, and various fees (e.g., `fees`, `other_service_fees`, `cash_request_fees`).
- **`Service`**: A lookup table for services provided (e.g., Petrol, Diesel, Wash, Other). Tracks unit type (litre, unit) and cost.
- **`StationService`** & **`StationBranchService`**: Join tables linking services to the main station and individual branches respectively.

## Roles & Access Control

Users interact with the station app under different roles defined in the `User` model:
- **`StationOwner`**: Has full oversight over all branches belonging to their `Station`. Operations filters are scoped to `station_branch__station_id`.
- **`StationBranchManager`**: Has oversight only for the branches they manage.
- **`StationWorker`**: The employee on the ground. Has access only to operations they perform at their specific branch.

## Views & APIs

### `station_views.py`
- **`StationViewSet`**: Provides CRUD endpoints for `Station`. Includes counts for branches, services, managers, and workers. Accessible mostly via dashboard permissions.
- **`StationHomeAPIView`**: Provides a dashboard summary tailored to the user's role. Returns balance, managers count, workers count, and recent `CarOperation`s.
- **`StationOperationsAPIView`**: Lists `CarOperation` history filtered by the user's role and search parameters. Returns balances separated by petrol/diesel and other services.
- **`StationReportsAPIView`**: Generates reports for services used, total balance, and cash requests within a given date/time range.

### `car_operations_views.py`
- **`StationGasOperationAPIView`**: 
  - Handles updating a gas/fuel `CarOperation` (PATCH).
  - Validates `car_meter` is strictly greater than the car's `last_meter`.
  - Calculates allowed fuel limit based on car's remaining `balance` and `company_liter_cost`.
  - Upon completion, deducts the operation's total cost from the `car.balance` and `station_branch.balance`.
  - Generates notifications (including oil change reminders) and `KhaznaTransaction`s (both station and company).
- **`StationOtherOperationAPIView`**:
  - Handles non-fuel operations (e.g., Wash).
  - Checks if the car has enough balance to cover the `company_cost`.
  - Generates respective station/company `KhaznaTransaction`s and notifications.
  
## Key Business Logic Points
- **Profit Calculation**: The company charges more per liter/service based on `branch.fees`. `profits = company_cost - station_cost`.
- **Atomic Transactions**: Operations that adjust balances (`PATCH` on `StationGasOperationAPIView` and `StationOtherOperationAPIView`) use `@atomic` to ensure data integrity during partial updates.
- **Meter Validation**: Required for vehicles with `is_with_odometer` set to True. The new odometer reading cannot be less than the old reading.
