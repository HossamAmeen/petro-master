# Petro Master Backend Guide

## Testing

- Use `pytest` with `pytest-django`; run the suite with `venv/bin/python -m pytest`.
- Keep shared API clients, JWT-claim helpers, and cross-domain fixtures in the root `conftest.py`.
- Keep domain-specific fixtures in that app's test `conftest.py`.
- Reuse factories from `apps/companies/factories.py`; add a factory before repeating model setup in tests.
- API tests must cover successful requests and relevant authentication, authorization, validation, and ownership boundaries.
- Exercise application code against the test database. Mock only network-bound third-party adapters, such as Firebase Cloud Messaging and email/SMS providers.
- Car API tests live in `apps/companies/tests/api/v1/car/`, with one module per CRUD action plus custom-action modules (`test_update_balance.py`, `test_verify_driver.py`). Test function names end in `_success` or `_fail`.
- Reuse `car_factory`, `car_code_factory`, `car_payload_factory`, `company_car`, and `car_operation_factory` from `apps/companies/tests/conftest.py` instead of creating car graphs inside tests.
- `VerifyDriverView` tests authenticate as a station worker via `auth_client(..., station_id=...)`. Cover petrol and non-petrol quotes, code/company/driver ownership, in-progress operations, allowed fuel days, balance, and daily petrol/diesel fueling limits.
- Driver API tests live in `apps/companies/tests/api/v1/driver/`, with one module per CRUD action. Test function names end in `_success` or `_fail`.
- Reuse `driver_factory`, `driver_payload_factory`, and `company_driver` from `apps/companies/tests/conftest.py` instead of creating driver graphs inside tests.

## API conventions

- Tests target the versioned `/api/v1/` endpoints and use DRF's `APIClient`.
- Set `company_id` or `station_id` JWT claims through the shared `auth_client` fixture for scoped endpoints.
# AGENTS.md

Living guide for coding agents working on Petro Master backend.

## Product docs

Read `business-analysis.txt` and `documentation.txt` before planning changes when those files exist. Do not violate documented rules, flows, or assumptions unless the task explicitly asks for a change.

## Admin: parent → branch dependent dropdowns

Jazzmin list filters live in the search form. Selecting a filter does **not** reload the page; options become GET params only after Search.

`CompanyKhaznaTransactionAdmin` and `StationKhaznaTransactionAdmin` both use the same pattern:

- Branch list filter options load via AJAX when the parent (company/station) is selected. Do not require Search or a page refresh just to show options.
- The add/change form keeps the branch field empty until a parent is selected, then loads that parent’s branches.
- Approved/declined transactions are view-only (`has_change_permission` is False). Django then excludes every field from the ModelForm, so form `__init__` must not assume `company_branch` / `station_branch` exist.
- Branch fields are optional (`required=False`, model `null=True, blank=True`). Saving without a branch applies the transaction to the company/station.
- Endpoints:
  - `admin:accounting_companykhaznatransaction_branches_by_company`
  - `admin:accounting_stationkhaznatransaction_branches_by_station`
- Script is inlined from `apps/accounting/templates/admin/accounting/includes/dependent_branch.html` so it does not depend on collectstatic.
- Filter template: `apps/accounting/templates/admin/accounting/dependent_branch_filter.html`.

Do not populate a branch dropdown with every branch in the system. Always scope by the selected company or station.

## Testing Standards (Pytest)

When writing tests (especially using Pytest) for this project, you **must** adhere to the following senior backend standards:
- **URL Resolution**: Always use `django.urls.reverse` (e.g. `reverse("station-home")`) for endpoints. Never hardcode API URL strings.
- **Comprehensive Coverage**: Tests must cover all logical edge cases. Do not just test validation errors; ensure you test the full "happy path" (successful creation, balance deductions, profits). Test different permission layers for user roles (Owner vs Manager vs Worker).
- **Avoid Repetition**: Utilize `@pytest.mark.parametrize` where applicable to test multiple roles or conditions within the same test function.
- **Fixture Reusability**: Do not duplicate data creation in test functions. Create and utilize standard fixtures in `conftest.py` that fully model business requirements (e.g. `company`, `car`, `car_operation`).

## Companies App Overview

The `companies` app (`apps/companies`) manages company accounts, branches, cars, drivers, and their related operations and cash requests.

### Models (`apps/companies/models/`)
- **`Company`** (`company_models.py`): Represents a corporate client. Tracks balance, contact info, and status.
- **`CompanyBranch`** (`company_models.py`): A branch of a company. Tracks its own balance, managers, and various fees (service, cash request).
- **`Car`** (`company_models.py`): A vehicle belonging to a branch. Tracks fuel type, plate, tank capacity, balances, and operational limits.
- **`CarCode`** (`company_models.py`): QR code generation logic and unique identifier for a `Car`.
- **`Driver`** (`company_models.py`): A driver assigned to a branch, with license tracking.
- **`CarOperation`** (`operation_model.py`): Records a service or fueling event for a `Car`. Tracks cost, company/station deductions, profits, and images.
- **`CompanyCashRequest`** (`company_cash_models.py`): A request by a company driver for cash at a station. Includes OTP generation for verification.
- **`AIApiResponse`** (`ai_api_response_model.py`): Logs AI model processing results associated with a `CarOperation` (e.g., number extraction, match score).

### Views (`apps/companies/api/v1/views/`)
- **`CompanyViewSet`** (`company_views.py`): Standard CRUD for companies, including annotated counts (branches, cars, drivers, managers).
- **`CompanyBranchViewSet`** (`company_views.py`): Manages branches with endpoints for assigning managers (`/assign-managers`) and updating branch balances via internal transfers between branch and parent company (`/update-balance`).
- **`CompanyHomeView`** (`company_views.py`): Aggregates dashboard metrics for a company owner or branch manager, returning total cars, balances across entities, recent operations, and transactions.
- **`CarOperationViewSet`** (`car_operation_views.py`): Manages car service/fueling records. Includes custom `export` and `download-excel` actions to generate and retrieve Excel reports of operations asynchronously. Deletion of operations is explicitly disabled.
- **`CarViewSet` & `VerifyDriverView`** (`car_views.py`): 
  - **`CarViewSet`**: Manages car records. Features a custom `update-balance` action for transferring funds between a branch/company and a car, which also generates internal transactions and notifications. Prevents deleting cars with a positive balance. Car clients do not submit `created_by` or `updated_by`; `InjectUserMixin` owns these read-only audit fields.
  - **`VerifyDriverView`**: Station-facing endpoint that verifies a driver and car code before a service begins. It checks balances and daily fueling limits, calculates available liters, creates a `PENDING` `CarOperation`, and locks the car from receiving balance updates (`is_blocked_balance_update = True`).
- **`CompanyCashRequestViewSet`** (`company_cash_request_views.py`): Manages driver cash requests at stations. Role-based scoping applies (Company vs Station users).
  - **`create`**: Initiates a request, proactively deducting the total cost (amount + company fees) from the company/branch balance and notifying owners.
  - **`partial_update`**: Used by Station Workers to approve an in-progress request (validating via OTP). Finalizes the workflow, deducts station costs (amount + station fees) from the station branch balance, logs transactions for both the company and the station, and sends out notifications.
  - **`destroy`**: Cancels a pending request, changes its status to `REJECTED`, and refunds the deducted balance back to the company or branch.

## Stations App Overview

The `stations` app (`apps/stations`) manages gas station networks, their physical branches, available services, and financial operations initiated by workers.

### Models (`apps/stations/models/`)
- **`Service`** (`service_models.py`): Represents a service (petrol, diesel, wash, other) offered across the system, including cost and unit data.
- **`Station`** (`stations_models.py`): A high-level entity representing a gas station network. Holds an overall balance.
- **`StationBranch`** (`stations_models.py`): A physical branch of a station. Maintains its own balance and tracks specific fee percentages (e.g. `cash_request_fees`).
- **`StationService` & `StationBranchService`** (`stations_models.py`): Mapping models to assign global services to specific stations and branches.

### Views (`apps/stations/api/v1/views/`)
- **`StationViewSet`** (`station_views.py`): Standard CRUD for Stations, including aggregated metrics (branch counts, combined balances).
- **`StationHomeAPIView`** (`station_views.py`): Returns dashboard metrics for owners/managers, summarizing balances (base vs distributed), worker counts, and recent operations.
- **`StationOperationsAPIView` & `StationReportsAPIView`** (`station_views.py`): Provides scoped lists of operations and advanced reporting (e.g., aggregated balances by service type, date/time filtering) based on user role.
- **`StationBranchViewSet`** (`station_branch_views.py`): Manages branches with custom actions to assign managers (`/assign-managers`), assign services (`/assign-services`, `/add-service`), and perform internal balance transfers between a Station and a Branch (`/update-balance`).
- **`StationGasOperationAPIView` & `StationOtherOperationAPIView`** (`car_operations_views.py`): Core endpoints used by Station Workers to process and finalize operations.
  - **`StationGasOperationAPIView`**: Handles fuel operations. Validates amounts against car limits, calculates company vs station costs, deducts from car balances, records internal transactions, and triggers system notifications.
  - **`StationOtherOperationAPIView`**: Similar flow but tailored for non-fuel services (like washing), utilizing branch-specific `other_service_fees`.
