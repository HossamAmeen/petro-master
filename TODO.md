# TODO

Running list of things to implement. Newest ideas at the bottom, finished items checked off.

- [ ] **Send forgot password**
  - Endpoint already exists: `POST /api/v1/auth/password-reset-request/` → `PasswordResetRequestAPIView` in [apps/auth/v1/views.py](apps/auth/v1/views.py).
  - It takes `email` only and sends the reset link with `send_mail` + `reset_password_email_template.html`.
  - Most users log in by phone and get a generated `{phone}@petro.com` email, so the email never reaches them → make it send by phone too (SMS via `apps/shared/send_sms.py`) or accept an `identifier` like the login endpoints.
  - Token lives on the user: `create_password_reset_token()` / `is_valid_password_reset_token()` in [apps/users/models.py](apps/users/models.py) (24h expiry).
  - Tests: [apps/auth/tests/test_password_reset_request.py](apps/auth/tests/test_password_reset_request.py).

- [X] **Use Celery to send notifications and background tasks**
  - Celery is already wired up: [config/celery.py](config/celery.py), `CELERY_*` settings in [config/settings.py](config/settings.py#L330) (Redis broker), `celery==5.5.3` in [requirements/base.txt](requirements/base.txt).
  - Nothing uses it yet — every send is inline and blocks the request.
  - Move these off the request path into tasks: FCM push in [apps/notifications/fcm_manager.py](apps/notifications/fcm_manager.py) (fired from [apps/notifications/signals.py](apps/notifications/signals.py)), SMS in [apps/shared/send_sms.py](apps/shared/send_sms.py), password-reset email in [apps/auth/v1/views.py](apps/auth/v1/views.py), and the senders in [apps/companies/signals.py](apps/companies/signals.py) / [apps/companies/helper.py](apps/companies/helper.py).
  - Add retries for the network-bound ones, and a worker to the deploy setup.
  - Tests mock FCM/SMS already — keep that working (`CELERY_TASK_ALWAYS_EAGER` in test settings).

- [x] **Add format/lint commands to the Makefile and align the tool configs**
  - Add targets to [Makefile](Makefile): `format` (black + isort), `lint` (flake8), and a `check` that runs all three in `--check`/`--diff` mode for CI. Remember to add them to `.PHONY`.
  - Tools are already installed in [requirements/dev.txt](requirements/dev.txt): `black==24.1.1`, `isort==6.0.0`, `flake8==7.1.2`, `pre-commit==4.2.0`.
  - Make the configs agree — they currently drift:
    - black has **no config at all** (no `pyproject.toml`), so it runs on defaults (line length 88).
    - [.flake8](.flake8) sets `max-line-length = 88`, ignores `E203, E266, E501, W503`, excludes `venv, */migrations/*, settings.py`.
    - [.isort.cfg](.isort.cfg) uses `profile = black`, skips `venv, migrations`.
    - Pick one source of truth (a `pyproject.toml` with `[tool.black]` + `[tool.isort]`) and use the same line length and the same exclude list (venv, migrations, settings.py) everywhere.
  - [.pre-commit-config.yaml](.pre-commit-config.yaml) pins older versions than dev.txt (isort 5.13.2 vs 6.0.0, flake8 6.0.0 vs 7.1.2) and has an empty `rev: ''` on the remove-print-statements hook — bump them to match so pre-commit and `make format` produce identical output.
  - Then run the formatters across the whole repo once and commit the reformat on its own, so it doesn't get mixed into feature diffs.

- [ ] **Customer support role: view only (no create / update / delete)**
  - The role already exists (`User.UserRoles.CustomerSupport` in [apps/users/models.py](apps/users/models.py)) and is in `DASHBOARD_ROLES` in [apps/shared/constants.py](apps/shared/constants.py), so today it passes `DashboardPermission` and can **write** everywhere an admin can.
  - Rules for the whole task:
    - Block writes with a permission class, not by overriding `create` / `update` / `destroy` in the views. Only override a view method if the permission approach really doesn't work for that endpoint.
    - Small cleanups in the transaction and car-operation viewsets are fine while touching them (e.g. merging the repeated `get_permissions` branches), but keep them small.
  - **Phase 1 — model, viewset, admin**
    - Add a `CustomerSupport` model as a **proxy** of `User` (`class Meta: proxy = True`). No extra fields and no new table, unlike `Supervisor` / `Agent` which use multi-table inheritance.
    - Give it a manager / `get_queryset` filtered on `role=CustomerSupport`, and set the role in `save()` the same way `Worker` / `Supervisor` do.
    - Add a viewset + serializer under [apps/users/v1/](apps/users/v1/) (admin-only via `AdminPermission`, same as `UserViewSet`) and register it in [apps/users/v1/urls.py](apps/users/v1/urls.py).
    - Register it in [apps/users/admin.py](apps/users/admin.py).
    - Tests: CRUD by admin, and no other role can create customer-support users.
  - **Phase 2 — view only on `CarOperationViewSet`**
    - [apps/companies/api/v1/views/car_operation_views.py](apps/companies/api/v1/views/car_operation_views.py): `list` / `retrieve` stay open to customer support; `create` / `partial_update` (which use `DashboardPermission`) must reject it.
    - Proposed solution: add a reusable permission in [apps/shared/permissions.py](apps/shared/permissions.py) (e.g. `CustomerSupportReadOnlyPermission`) that allows customer support only on `SAFE_METHODS`. Use it in `get_permissions` next to the existing classes. Once it works here, reuse it for the other `DashboardPermission` viewsets (company, station, users, station branches).
    - Tests: customer support gets 200 on list/retrieve and 403 on create/patch; admin and finance behave as before.
  - **Phase 3 — view only on transaction viewsets (company, station)**
    - [apps/accounting/api/v1/views.py](apps/accounting/api/v1/views.py): `CompanyKhaznaTransactionViewSet` and `StationKhaznaTransactionViewSet`. Apply the same permission from phase 2.
    - Also check `KhaznaTransactionViewSet`: it only has `IsAuthenticated`, so any role (customer support included) can write there right now.
    - Tests: same matrix as phase 2 for both company and station transactions.

- [x] **Feature tests: every business scenario end to end**
  - Done: `tests/features/` (14 modules, 125 tests, `-m feature`). See the "Feature tests" section in [AGENTS.md](AGENTS.md).
  - Do it on a new branch cut from `staging` (e.g. `git checkout -b add/feature-tests`), not on `staging` directly.
  - Gap: every current test covers one endpoint and builds its starting state with factories. Nothing checks that the endpoints work together, e.g. that money loaded by the dashboard actually reaches a car and gets spent at a station. A feature test runs one whole scenario through the real `/api/v1/` endpoints in order and checks the end state (balances, statuses, khazna rows, notifications).
  - Where and how:
    - New root package `tests/features/` (with `__init__.py`), one module per scenario below (`test_fueling.py`, `test_cash_request.py`, …). The root [conftest.py](conftest.py) already loads the users/companies/stations fixtures.
    - Register a `feature` marker in [pytest.ini](pytest.ini) (it runs `--strict-markers`) and use `pytestmark = [pytest.mark.django_db, pytest.mark.feature]`, so `pytest -m feature` runs them alone.
    - Log in through the real login endpoints and use the returned tokens instead of `auth_client`, so the JWT claims come from the real flow too. Reuse `set_login_password` / `login_payload` from [apps/auth/tests/helpers.py](apps/auth/tests/helpers.py).
    - Create through the API whatever the scenario itself creates. Use factories only for the starting point (geo data, services, users/companies the scenario doesn't create).
    - Follow the testing rules in [AGENTS.md](AGENTS.md) (`Test*` class, `setup` fixture, `reverse()`, `_success` / `_fail`). Mock only FCM, SMS, SendGrid and OpenAI.
    - When a flow hits a known bug (e.g. the approve-PATCH `KeyError` on khazna transactions), assert the current behaviour and leave a note. Don't route around it.
  - Scenarios (each module: happy path first, then its failure branches):
    1. **Company onboarding**: dashboard admin logs in → creates company → company owner (`users/company-owners/`) → company branch (dashboard-only) → owner logs in (token has `company_id` + branches) → creates a branch manager and `assign-managers` → manager logs in and sees only their branch. Fail: owner creating a branch (403), manager reading another branch.
    2. **Station onboarding**: admin creates station → station owner → station branch → `assign-services` / `add-service` → worker + branch manager → worker logs in (token has `station_id`). Fail: non-dashboard user creating a station or branch.
    3. **Company money chain**: dashboard creates an approved company khazna transaction (the API requires a branch, and `is_incoming=false` is what adds money) → branch balance up → owner moves branch → company (`branches/{id}/update-balance`, `subtract`) and company → another branch (`add`) → owner tops up a car from the company, manager from the branch (`cars/{id}/update-balance`), then pulls it back. Assert every balance, the internal khazna rows and the MONEY notifications. Fail: not enough balance at each level, topping up a car whose `balance_source` is branch/company, topping up a car locked mid-operation.
    4. **Station money**: dashboard creates an approved station khazna transaction → owner moves station ↔ branch (`stations/branches/{id}/update-balance`). Fail: not enough balance, non-owner 403.
    5. **Fueling (petrol / diesel)**, the core flow: worker calls `verify-driver/…/petrol/` → PENDING op, car locked → gas PATCH `start_time` → `car_meter` + `motor_image` → `amount` + `fuel_image` within 60s → COMPLETED. Assert `company_cost` taken from the balance holder, `station_cost` from the station branch, profits, both khazna rows, notifications, car unlocked, `last_meter` updated. Parametrize over `balance_source` = car / branch / company. Then the company sees the op in `car-operations/` and `home/`, and the station in `operations/`, `home/` and `reports/`.
       - Fail: verify while another op is open, car not allowed today, company inactive, driver from another company, not enough balance, daily fueling limit (complete one, verify again), amount over the available liters, past the 60s window, meter lower than `last_meter`, cancel (DELETE) unlocks the car so a new verify works.
       - Also: a meter past `next_oil_change_km` sends the GENERAL oil-change notification.
    6. **Other services (wash / other)**: verify with a non-petrol type → other-operation PATCH with the cost → holder charged cost + branch `other_service_fees`, station transaction, notifications, car unlocked. Fail: a different worker completing it, not enough balance, cancel.
    7. **Cash request**: owner (and separately a branch manager) creates a request for a driver → company / branch charged amount + `cash_request_fees`, OTP sent (SMS mocked) → worker finds it by `driver_code` → approves with the OTP → station branch charged, company + station khazna rows, notifications → the worker's list shows it approved. Alternative path: cancel while in progress → REJECTED and refunded. Fail: second request for the same driver, wrong OTP, cancel after approval, manager changing a request someone else created.
    8. **Dashboard-side operations**: dashboard creates a car operation (`car-operations/`, dashboard-only) and completes it by PATCH. Admin clones an operation from the Django admin (`…/clone/`, [apps/companies/operation_clone.py](apps/companies/operation_clone.py)). The money side effects must match a station-made operation.
    9. **Reports and exports**: after several completed operations over two days and two branches, check company `home/`, `car-operations/export/` → `download-excel/`, and station `reports/` with `date_from` / `date_to`. The totals must add up to what the operations charged.
    10. **Account lifecycle**: login → token refresh keeps `company_id` / `station_id` → profile update → password reset request (locmem outbox) → confirm → the new password logs in and the old one fails. Inactive and wrong-role logins get 401.
    11. **Notifications**: user registers a firebase token (`users/firebase-tokens/`) → a money action from scenario 3 or 5 → FCM mock called with that token → list shows it unread → PATCH `is_read`.
    12. **Tenant isolation**: two companies and two stations fully set up. Every company and station role in A gets 404/403 on B's cars, drivers, operations, cash requests and transactions. Write down what's still open (e.g. gas PATCH only needs authentication).
    13. **Public / landing page**: no auth. Geo cities/districts, station branches list (available ones only by default), sliders, `configrations`, `contact-us` (throttled). The `configrations` app has no tests at all today.
    14. **AI operation check**: completed operation → `manage.py process_ai_operations` with the OpenAI client and `requests.get` mocked → one `AIApiResponse` per operation, max 100 per branch.
  - Celery: once the `use-celery` branch is merged, keep `CELERY_TASK_ALWAYS_EAGER` on in [config/settings_test.py](config/settings_test.py) so notification / SMS tasks still run inside the test.
  - Done when: `venv/bin/python -m pytest -m feature` passes, the full suite still passes, `make check` is clean, and AGENTS.md says where feature tests live and how to add one.
