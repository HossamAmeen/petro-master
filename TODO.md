# TODO

Running list of things to implement. Newest ideas at the bottom, finished items checked off.

- [ ] **Send forgot password**
  - Endpoint already exists: `POST /api/v1/auth/password-reset-request/` → `PasswordResetRequestAPIView` in [apps/auth/v1/views.py](apps/auth/v1/views.py).
  - It takes `email` only and sends the reset link with `send_mail` + `reset_password_email_template.html`.
  - Most users log in by phone and get a generated `{phone}@petro.com` email, so the email never reaches them → make it send by phone too (SMS via `apps/shared/send_sms.py`) or accept an `identifier` like the login endpoints.
  - Token lives on the user: `create_password_reset_token()` / `is_valid_password_reset_token()` in [apps/users/models.py](apps/users/models.py) (24h expiry).
  - Tests: [apps/auth/tests/test_password_reset_request.py](apps/auth/tests/test_password_reset_request.py).

- [ ] **Use Celery to send notifications and background tasks**
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
