# Petro Master Backend Guide

## Formatting

- Run `make format` on your changes and make sure `make check` passes (activate the venv first: `source venv/bin/activate && make check`). black and isort are configured in `pyproject.toml`, flake8 in `.flake8`.

## Testing

- Use `pytest` with `pytest-django`; run the suite with `venv/bin/python -m pytest` (or `make test`).
- Coverage: `make coverage` runs the whole suite with `pytest-cov`, prints a term-missing summary, writes `htmlcov/`, and fails under 80% (currently ~83%). Config (measured packages, omits, exclude lines) is in `pyproject.toml` under `[tool.coverage.*]`; `pytest-cov` is pinned in `requirements/dev.txt`.
- Keep shared API clients, JWT-claim helpers, and cross-domain fixtures in the root `conftest.py`.
- Keep domain-specific fixtures in that app's test `conftest.py`.
- Reuse factories from `apps/companies/factories.py`; add a factory before repeating model setup in tests.
- API tests must cover successful requests and relevant authentication, authorization, validation, and ownership boundaries.
- Wrap tests in a `Test*` class per module. Keep `pytestmark`, URL helpers, and non-test helpers at module level. Method names end in `_success` or `_fail`.
- Keep code shared by the tests in a class in a setup method on that class, not repeated in every test. Use an autouse fixture named `setup` when it needs fixtures or the database (`setup_method` cannot request fixtures); use plain `setup_method` only for fixture-free setup. Put only what most tests in the class need in it, never assert in it, and leave anything one or two tests need in those tests.
- Exercise application code against the test database. Mock only network-bound third-party adapters, such as Firebase Cloud Messaging and email/SMS providers.
- Car API tests live in `apps/companies/tests/api/v1/car/`, with one module per CRUD action plus custom-action modules (`test_update_balance.py`, `test_verify_driver.py`). Wrap tests in a `Test*` class; method names end in `_success` or `_fail`.
- Reuse `car_factory`, `car_code_factory`, `car_payload_factory`, `company_car`, and `car_operation_factory` from `apps/companies/tests/conftest.py` instead of creating car graphs inside tests.
- `VerifyDriverView` tests authenticate as a station worker via `auth_client(..., station_id=...)`. Cover petrol and non-petrol quotes, code/company/driver ownership, in-progress operations, allowed fuel days, balance, and daily petrol/diesel fueling limits.
- Driver API tests live in `apps/companies/tests/api/v1/driver/`, with one module per CRUD action. Wrap tests in a `Test*` class; method names end in `_success` or `_fail`.
- Reuse `driver_factory`, `driver_payload_factory`, and `company_driver` from `apps/companies/tests/conftest.py` instead of creating driver graphs inside tests.
- Company API tests live in `apps/companies/tests/api/v1/company/`, with one module per CRUD action. Wrap tests in a `Test*` class; method names end in `_success` or `_fail`.
- Reuse `company_factory`, `company_payload_factory`, `company`, and `other_company` from `apps/companies/tests/conftest.py` instead of creating company graphs inside tests.
- `CompanyViewSet` is authenticated but not role-scoped: any logged-in user can list, retrieve, create, update, or delete companies. Cover annotated branch/car/driver/manager counts, district/city filters, name/phone search, `no_paginate`, ignored writable-balance, and PROTECT deletes when branches or owners exist.
- Company home tests live in `apps/companies/tests/api/v1/company/test_home.py`. Reuse `car_factory`, `driver_factory`, `car_operation_factory`, `cash_request_factory`, and `company_transaction_factory`. Cover owner vs branch-manager scoping, empty companies, missing `company_id`, fuel-type and license-expiration counts, in-progress cash-request totals, and the latest-three operations/transactions windows.
- Company cash-request API tests live in `apps/companies/tests/api/v1/cash_request/`, with one module per CRUD action. Wrap tests in a `Test*` class; method names end in `_success` or `_fail`.
- Reuse `cash_request_factory`, `cash_request_payload_factory`, `driver_factory`, and `company_driver` from `apps/companies/tests/conftest.py`. SMS is autouse-mocked in that package; do not hit the SMS provider.
- `CompanyCashRequestViewSet` GET is authenticated; POST/DELETE allow company and dashboard roles; PATCH is station-worker-only. Owner queryset is company-scoped; branch managers see the whole company but may mutate only requests they created; station owners/branch managers see station-linked requests; workers list their own approved rows unless `driver_code` is sent (then in-progress). Assert full list/retrieve payloads, create/approve/cancel money side effects, OTP, notifications, and khazna transactions.
- Car-operation API tests live in `apps/companies/tests/api/v1/car_operation/`, with one module per CRUD action plus `test_export.py`. Wrap tests in a `Test*` class; method names end in `_success` or `_fail`.
- Reuse `car_operation_factory`, `car_operation_payload_factory`, `car_factory`, `driver_factory`, `company_car`, and `company_driver` from `apps/companies/tests/conftest.py`.
- `CarOperationViewSet` list/retrieve allow company, dashboard, and station roles; create is dashboard-only; PATCH allows company, dashboard, and station; export/download-excel are company-owner/branch-manager only. Deletion is always rejected. Owner/manager querysets are petrol/diesel only and company/managed-branch scoped. Assert full list/retrieve payloads (company list omits `profits`), create/complete money side effects, and Excel export/download.
- Company branch API tests live in `apps/companies/tests/api/v1/company_branch/`, with one module per CRUD action plus `test_assign_managers.py` and `test_update_balance.py`. Wrap tests in a `Test*` class; method names end in `_success` or `_fail`.
- Reuse `company_branch_factory`, `company_branch_payload_factory`, `branch_manager_user_factory`, `company_branch`, `second_company_branch`, and `other_company_branch` from `apps/companies/tests/conftest.py` instead of creating branch graphs inside tests.
- `CompanyBranchViewSet` list allows company and dashboard roles; create is dashboard-only; `assign-managers` and `update-balance` are company-owner-only. Retrieve/update/delete are authenticated and queryset-scoped for owners (their company) and branch managers (assigned branches only). Cover city/company filters, `no_paginate`, annotated counts, manager replacement, and company↔branch balance transfers.
- Station API tests live in `apps/stations/tests/api/v1/` (`station`, `station_branch`, `service`, `home`, `operations`, `reports`, `gas_operation`, `other_operation`). Wrap tests in a `Test*` class; method names end in `_success` or `_fail`.
- Reuse `station`, `branch`, `station_owner`, `branch_manager`, `station_worker`, `service`, `other_service`, `gas_operation`, `other_operation`, and factories from `apps/stations/tests/conftest.py`. Image helpers and cost/notification asserts live in `apps/stations/tests/helpers.py`.
- Gas PATCH is authenticated (not worker-scoped): `start_time`, then `car_meter`+`motor_image`, then `amount`+`fuel_image` within 60s. Assert car and station-branch balance deductions, khazna rows, oil-change GENERAL recipients, and MONEY recipients (station owners + actor; car-branch company managers + actor). Other-op PATCH is the assigned worker only; company MONEY goes to every `CompanyUser` for that company plus the worker.
- Also cover empty/invalid payloads, meter-vs-amount precedence, the 60s window, zero fees, exact oil-change km, diesel vs wash/other types, exact car-balance completion, dashboard/station role retrieve-update, branch city/landing-page filters, operations petrol/diesel totals, and reports `date_to` / time windows.

## API conventions

- Tests target the versioned `/api/v1/` endpoints and use DRF's `APIClient`.
- Set `company_id` or `station_id` JWT claims through the shared `auth_client` fixture for scoped endpoints. `auth_client(user, ...)` returns a fresh authenticated client per call; `api_client` is always the unauthenticated one, so a class can build `self.client` in `setup` and still assert 401s with `api_client`.
- Shared test helpers: `set_balance` in `apps/companies/tests/helpers.py`, car URL builders in `apps/companies/tests/api/v1/car/helpers.py`, and station helpers (`worker_client`, `gas_url`, `other_url`, `fund_balance_source`, cost helpers) in `apps/stations/tests/helpers.py`. Import them instead of redefining them per module.
- Auth API tests live in `apps/auth/tests/`, with one module per endpoint (`test_company_login.py`, `test_station_login.py`, `test_dashboard_login.py`, `test_profile.py`, `test_password_reset_request.py`, `test_password_reset_confirm.py`, `test_token_refresh.py`) plus `test_utils.py` for SendGrid. Wrap tests in a `Test*` class; method names end in `_success` or `_fail`.
- Reuse `company_owner`, `company_branch_manager`, `station_owner`, `branch_manager`, `station_worker`, and dashboard user fixtures. Hash passwords with `set_login_password` before login assertions — most user fixtures store a raw password string.
- Company login is owner/branch-manager only and embeds `company_id` plus all company branch IDs. Station login is owner/manager/worker and embeds `station_id` (workers via `worker.station_branch.station_id`). Dashboard login is admin/finance/customer_support only. Wrong-role, inactive, and unknown-identifier attempts return 401 `invalid_credentials`.
- Profile GET adds role-specific `balance` (company total, managed-branch sum, station total, or 0 for workers) and `available_balance=0`. `phone_number` and `role` are read-only. Mock only SendGrid in `test_utils.py`; password-reset email uses the locmem backend and `django.core.mail.outbox`.
- Users API tests live in `apps/users/tests/api/v1/`, with one package per ViewSet (`user`, `company_owner`, `company_branch_manager`, `station_owner`, `station_branch_manager`, `worker`, `supervisor`, `firebase_token`). Wrap tests in a `Test*` class; method names end in `_success` or `_fail`.
- Reuse `admin_user`, `finance_user`, `customer_support_user`, `company_owner`, `company_branch_manager`, `station_owner`, `branch_manager`, `station_worker`, `supervisor`, and `agent` from `apps/users/test/conftest.py` plus company/station fixtures. Extra owners/stations/payload factories live in `apps/users/tests/conftest.py`.
- `UserViewSet` and `SupervisorViewSet` are admin-only. `CompanyOwnerViewSet` is dashboard-only. Company branch managers allow company + dashboard (owners are company-scoped). Station owner/manager/worker endpoints allow station + dashboard. Firebase tokens are authenticated; queryset is the current user only. Cover unauthenticated 401, wrong-role 403, queryset scoping, search/filters, password hashing, default `{phone}@petro.com` email, and branch-assignment side effects.
- Notifications API tests live in `apps/notifications/tests/` (`test_list.py`, `test_update.py`, `test_signals.py`, `test_fcm_manager.py`). The list is authenticated and current-user scoped. Dashboard roles get a real `unread_count`; company/station roles always receive `unread_count=0`. PATCH may only change `is_read`. FCM is autouse-mocked in root `conftest.py`; assert the mock from notification `post_save`. Test `FCMManager.send_fcm_message` against the original function captured in `apps/notifications/tests/conftest.py`.
- Geo API tests live in `apps/geo/tests/` (`test_cities.py`, `test_districts.py`). Cities and districts are unauthenticated GET-only (`http_method_names=["get"]`). Cover public list/retrieve, `country`/`city` filters, name search, `no_paginate`, newest-first ordering, nested district→city payload, and POST/PATCH/DELETE 405. There is no Country endpoint.

### Feature tests (end-to-end business scenarios)

- Feature tests live in the root `tests/features/` package, one module per business scenario (`test_fueling.py`, `test_cash_request.py`, `test_company_onboarding.py`, `test_station_onboarding.py`, `test_company_money.py`, `test_station_money.py`, `test_other_services.py`, `test_dashboard_operations.py`, `test_reports.py`, `test_account_lifecycle.py`, `test_notifications.py`, `test_tenant_isolation.py`, `test_public_pages.py`, `test_ai_operations.py`). They differ from the per-app API tests: each runs a whole workflow across several `/api/v1/` endpoints in order and asserts the end state (balances, statuses, khazna rows, notifications).
- They carry the `feature` marker (registered in `pytest.ini`): `pytestmark = [pytest.mark.django_db, pytest.mark.feature]`. Run them alone with `venv/bin/python -m pytest -m feature`.
- Log in through the real login endpoints so the JWT claims come from the real flow. Use `sign_in(kind, user)` / `login(kind, user)` / `login_client(kind, token)` from `tests/features/helpers.py` (kind is `"company"`, `"station"`, or `"dashboard"`); it hashes the fixture's raw password first. Do not build clients with `auth_client` here.
- Create through the API whatever the scenario itself creates; use factories only for the starting point (geo data, services, the users/companies the scenario doesn't create). Shared multi-request steps (`fuel`, `start_fueling`, `complete_other_service`, balance/branch URL builders, `fresh_balance`) live in `tests/features/helpers.py`.
- `tests/features/conftest.py` mocks SMS, points `MEDIA_ROOT` at a temp dir, and adds `fees` (standard company/station fee percentages), `fuelable_car` (petrol car allowed every day), and `local_cache` (locmem cache + DB sessions, for admin-client and throttle tests). Add a new scenario as a new `test_*.py` module there.
- When a flow hits a known bug, assert the current behaviour with a short "Open issue"/"Known bug" note and `pytest.raises` where it 500s (e.g. the approve-PATCH `KeyError` on khazna transactions); do not route around it. `_success`/`_fail` name the happy vs failure branches as elsewhere.
- Each feature test body follows the **Given-When-Then** template with `# Given` / `# When` / `# Then` comment markers (a step with several requests may repeat When/Then). The shared Given usually lives in the class's `setup` fixture, so a test's `# Given` marks only its extra arrangement and may be omitted when there is none.
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
- **Test classes**: Put tests in a `Test*` class per module. Keep `pytestmark` and helpers at module level. Method names end in `_success` or `_fail`.
- **Setup method**: Hold the code a class's tests share in a setup method on the class rather than repeating it per test. Use an autouse fixture named `setup` when it needs fixtures or the database — `setup_method` cannot request fixtures — and reserve plain `setup_method` for fixture-free setup (constants, payload templates). pytest builds a fresh instance per test, so `self` attributes never leak between tests.

```python
class TestCarUpdateBalance:
    @pytest.fixture(autouse=True)
    def setup(self, auth_client, company_owner, company, company_car):
        self.company = company
        self.car = company_car
        self.client = auth_client(company_owner, company_id=company.id)
        self.url = update_balance_url(company_car.id)

    def test_add_balance_success(self):
        set_balance(self.company, "100.00")

        response = self.client.post(
            self.url, {"amount": "40.00", "type": "add"}, format="json"
        )

        assert response.status_code == status.HTTP_200_OK
```

  Keep in setup only what most tests in the class need, never assert in it, and let each test still read as Arrange–Act–Assert.
- **Comprehensive Coverage**: Tests must cover all logical edge cases. Do not just test validation errors; ensure you test the full "happy path" (successful creation, balance deductions, profits). Test different permission layers for user roles (Owner vs Manager vs Worker).
- **Avoid Repetition**: Utilize `@pytest.mark.parametrize` where applicable to test multiple roles or conditions within the same test method.
- **Fixture Reusability**: Do not duplicate data creation in test methods. Create and utilize standard fixtures in `conftest.py` that fully model business requirements (e.g. `company`, `car`, `car_operation`).

## Entity availability

`Company`, `CompanyBranch`, `Station`, and `StationBranch` each have an `is_available` boolean that defaults to `True`. Use this field to mark an entity unavailable without deleting it.

The stations list API returns available stations by default. Supplying the `is_available` query parameter explicitly overrides that default, including `is_available=false` for unavailable stations.

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

## Accounting App Overview

The `accounting` app (`apps/accounting`) tracks khazna (cash-box) transactions for companies and stations.

### Models (`apps/accounting/models.py`)
- **`KhaznaTransaction`**: Concrete base model (multi-table inheritance). `is_incoming=True` **decreases** the linked balance; `False` increases it (`update_company_balance`/`update_station_balance`).
- **`CompanyKhaznaTransaction`**: Adds `company` (required FK) and `company_branch` (nullable FK) plus `for_what`.
- **`StationKhaznaTransaction`**: Adds `station` (required FK) and `station_branch` (nullable FK).

### Views (`apps/accounting/api/v1/views.py`)
- **`KhaznaTransactionViewSet`**: `IsAuthenticated` only, full CRUD, no `InjectUserMixin` — clients must supply `created_by` themselves. `get_queryset` only special-cases `CompanyOwner`/`CompanyBranchManager` by filtering `.filter(company=...)`, but the base model has no `company` field, so those two roles get an unhandled `FieldError` (500), not a scoped list. Every other authenticated role (dashboard, station roles) gets the fully unscoped queryset.
- **`CompanyKhaznaTransactionViewSet`**: `EitherPermission([CompanyPermission, DashboardPermission])` for every action (create/update/destroy included — no per-action override). Owners are scoped to their company; branch managers to `company_branch__managers__user_id` (their specific branch only). `CreateCompanyKhaznaTransactionSerializer` redeclares `company_branch` as `required=True`, so branch-less company-level charges cannot be created through the API. On `status=APPROVED`, it deducts/credits the branch (or company, if no branch) balance and notifies branch managers (or company owners).
- **`StationKhaznaTransactionViewSet`**: `EitherPermission([StationPermission, DashboardPermission])`. Station owners scoped to their station; **station branch managers are scoped to the whole station** (`station__branches__managers__user`), not just their managed branch — unlike the company side; workers are scoped to `created_by=self.request.user`.
- **Known bug (both `Update*Serializer`s)**: `validate()` does `attrs["company_branch"]` / `attrs["station_branch"]` with direct indexing, not `.get()`. Since that field is not required on partial update, a typical approve/decline PATCH like `{"status": "approved"}` that omits the branch raises an unhandled `KeyError` (500) instead of a clean validation error.
- Deleting a transaction never reverses the balance change it caused — mutation only happens in `create`/`partial_update`.

### Testing (`apps/accounting/tests/`)
- Tests live in `apps/accounting/tests/api/v1/`, one package per viewset (`khazna_transaction`, `company_transaction`, `station_transaction`), each with `helpers.py` plus `test_list.py` / `test_retrieve.py` / `test_create.py` / `test_update.py` / `test_destroy.py`. Wrap tests in a `Test*` class; method names end in `_success` or `_fail`.
- `apps/accounting/tests/conftest.py` adds `khazna_transaction_factory` and `station_transaction_factory` (no model factory existed for the station side); reuse `company_transaction_factory` from `apps/companies/tests/conftest.py`.
- The known `KeyError`/`FieldError` bugs above are asserted with `pytest.raises`, per the "assert actual behavior" standard — do not silently "fix" the test by avoiding the buggy payload shape.

## Auth App Overview

The `auth` app (`apps/auth`) issues JWT sessions for company, station, and dashboard users and handles profile + password-reset flows.

### Views (`apps/auth/v1/views.py`)
- **`CompanyLoginAPIView`**: Unauthenticated. Accepts email or phone `identifier`. Allows `company_owner` and `company_branch_manager` only. Tokens carry `company_id`; the body also returns `user` and all company `branches`.
- **`StationLoginAPIView`**: Unauthenticated. Allows station owner, branch manager, and worker. Tokens carry `station_id` from `stationowner.station` or `worker.station_branch.station_id`.
- **`DashboardLoginAPIView`**: Unauthenticated. Allows `DASHBOARD_ROLES` (admin, finance, customer_support). Tokens do not embed company/station claims.
- **`CustomTokenRefreshView`**: Copies `company_id` / `station_id` from the refresh token onto the new access token. Company/station roles without those claims are rejected.
- **`ProfileAPIView`**: Authenticated retrieve/update of the current user. Password is write-only; phone and role are read-only. `to_representation` adds role-specific `balance` and `available_balance`.
- **`PasswordResetRequestAPIView`** / **`PasswordResetConfirmAPIView`**: Unauthenticated. Request emails a 24-hour token via Django `send_mail`. Confirm GET renders HTML; POST sets the password and clears the token.

### Testing
- Auth API tests live in `apps/auth/tests/` with one module per endpoint. Reuse shared user/company/station fixtures and `apps/auth/tests/helpers.py` (`set_login_password`, URL reverses, JWT helpers).
- Cover successful logins by email and phone, JWT claims, wrong-role/inactive/unknown credentials, profile balances per role, reset email/outbox, expired tokens, and refresh-token claim copying. Mock SendGrid only.

## Notifications App Overview

The `notifications` app (`apps/notifications`) stores in-app notifications and fans them out over FCM.

- **`NotificationViewSet`**: Authenticated list + PATCH. Queryset is `user=request.user`. Search `title`/`description`; filter `is_read` and `type` (iexact). List adds `unread_count` for dashboard roles only (always `0` for company/station). PATCH serializer accepts `is_read` only. No retrieve/create/delete.
- Creating a `Notification` fires `post_save` → `FCMManager.send_fcm_message` with that user's Firebase tokens. Updates do not resend. `user=None` raises on send because the signal dereferences `instance.user.firebase_tokens`.
- Tests live in `apps/notifications/tests/`. Mock FCM at `FCMManager.send_fcm_message`; unit-test the real sender via `ORIGINAL_SEND_FCM`.

## Geo App Overview

The `geo` app (`apps/geo`) is the country → city → district catalog.

- **`CityViewSet`** / **`DistrictViewSet`**: Unauthenticated GET-only. Filter cities by `country`, districts by `city`; search by `name`; order by `-id`. District list/retrieve nest the full city (`id`, `name`, `country` PK). There is no Country API.
- Tests live in `apps/geo/tests/`. Reuse root `geo_data` plus `other_country` / `other_city` / `other_district` from that package's conftest.

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

### Testing (`apps/stations/tests/`)
- Tests live in `apps/stations/tests/api/v1/` with one package per area: `station`, `station_branch`, `service`, `home`, `operations`, `reports`, `gas_operation`, `other_operation`. Wrap tests in a `Test*` class; method names end in `_success` or `_fail`.
- Reuse `station`, `branch`, `station_owner`, `branch_manager`, `station_worker`, `service`, `other_service`, `gas_operation`, `other_operation`, plus factories in `apps/stations/tests/conftest.py` (`station_factory`, `station_branch_factory`, `station_branch_service_factory`).
- Shared helpers (`gas_url`, `image_file`, `gas_costs`, `notification_user_ids`) live in `apps/stations/tests/helpers.py`. Multipart image uploads are required for meter/amount/other-op patches.
- `StationGasOperationAPIView` PATCH is authenticated only (not worker-scoped). Completing `amount` requires `start_time` within 60 seconds, `fuel_image`, and amount ≤ min(tank/permitted, floor(car.balance / company_liter_cost)). It deducts `company_cost` from `car.balance` and `station_cost` from `station_branch.balance` (station/company entity balances are unchanged).
- Gas MONEY notifications: all `StationOwner` rows for the JWT `station_id` plus the acting user; company MONEY goes to managers of that car's company branch plus the acting user (not the company owner). Oil-change GENERAL goes to company owners and that branch's managers.
- `StationOtherOperationAPIView` is worker-scoped and requires `service__isnull=True`. Completing deducts `company_cost` from the car only (station branch balance is not changed). Station MONEY: all station owners plus the worker. Company MONEY: all `CompanyUser` rows for the company plus the worker.
- `StationViewSet` list/create are dashboard-only; retrieve/PATCH allow dashboard or station roles. `StationBranchViewSet` list is public; `update-balance` is station-owner-only. `StationHomeAPIView` / `StationReportsAPIView` require station roles; operations list is authenticated and role-scoped.
- Model smoke tests remain in `apps/stations/tests/test_models.py`.
