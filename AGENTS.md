# AGENTS.md

Living guide for coding agents working on Petro Master backend.

## Product docs

Read `business-analysis.txt` and `documentation.txt` before planning changes when those files exist. Do not violate documented rules, flows, or assumptions unless the task explicitly asks for a change.

## Admin: company → company_branch dependent dropdowns

`CompanyKhaznaTransactionAdmin` uses Jazzmin search filters (not Django’s default sidebar links).

- Jazzmin list filters live in the search form. Selecting a filter does **not** reload the page; options only become GET params after the user clicks Search.
- `CompanyBranchByCompanyListFilter` must not require Search or a page refresh just to show branch options. Selecting **company** loads branches via AJAX into the **company_branch** filter.
- The add/change form keeps `company_branch` empty until a company is known. Selecting **company** loads that company’s branches via the same endpoint.
- Endpoint: `admin:accounting_companykhaznatransaction_branches_by_company` (`branches-by-company/?company=<id>`).
- JS: `apps/accounting/static/accounting/js/filter_company_branch.js`.
- Filter template: `apps/accounting/templates/admin/accounting/company_branch_filter.html`.

Do not populate `company_branch` with every branch in the system. Always scope by the selected company.
