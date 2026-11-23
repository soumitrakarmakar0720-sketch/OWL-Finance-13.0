# OWL FINANCE 6.2.1 — Loan management corrections

- Foreclosure settlement now accepts `active` and legacy `demo_active` loan statuses.
- Verified foreclosure settlements transition loans to `foreclosed`, which is listed under the Foreclosed category instead of Active.
- Active and settled loans display a Manage explanation instead of an unexplained Deletion locked label.
- Cancel/archive remains restricted to loans without installment, payment, disbursement, or foreclosure records. No financial history is erased.
- Duplicate cancel form on loan detail removed.

## Deploy
Push these files to GitHub, then redeploy on Render. Back up the Neon database before deployment. Existing loans are not automatically altered. For an existing approved foreclosure, use the admin loan detail page to record a **verified** settlement only after receipt of the exact required funds. Do not manually change database status to pretend a payment occurred.
