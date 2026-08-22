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
