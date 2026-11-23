# OWL FINANCE 7.0 Enterprise — deployment and limitations

## Upgrade path
1. Back up the current GitHub project and Neon database (restore point / dump).
2. Upload the entire project contents, including `enterprise.py` and `templates/enterprise/`.
3. Keep existing Render environment variables, especially `DATABASE_URL`, `SECRET_KEY`, `KYC_ENCRYPTION_KEY`, Cashfree credentials, and `CASHFREE_ENV`.
4. Deploy the latest commit. The existing `db.create_all()` will create **new** enterprise tables, without altering the existing tables. For controlled production deployments, apply schema migrations instead of relying on `create_all()`.
5. Open `/admin/enterprise/` as administrator. Create a branch, assign an application, configure staff permissions, record review recommendations, and test reconciliation against non-production transactions.

## New additive database tables
- enterprise_branch
- enterprise_assignment
- enterprise_approval
- enterprise_reconciliation
- enterprise_ticket
- enterprise_staff_permission

## What works
- Admin command center with counts and links
- Branch directory, application assignment to branches/staff
- Multi-stage review recommendations with audit entries
- Granular Enterprise screen permissions for staff
- Payment reconciliation register, with no modification of actual payment statuses
- Overdue installment queue
- Customer support tickets and resolution tracking
- Audit CSV export
- Existing customer dashboard, admin loans, KYC, foreclosure, manual disbursement and Cashfree integration preserved from 6.3.1

## Known boundaries
- Review recommendations do **not** replace final loan approval, disbursement, or KYC verification; those remain in the legacy workflows.
- Branch assignment does not yet restrict the legacy admin/staff dashboards to branch-specific records. This is an operations directory, not full tenant isolation.
- Staff permissions apply to Enterprise routes, not all pre-existing routes. Full organization-wide RBAC is a separate migration.
- Reconciliation does not settle, refund or reverse money. Payment statuses still require Cashfree server-side verification.
- No automatic SMS/WhatsApp notifications, scheduled jobs, credit bureau integrations, bank transfers, or external payout APIs are included.
- This release is source/syntax/template validated, **not** production-certified or end-to-end tested against your Neon database/Cashfree merchant account.
- Do not treat `demo_active` loans as real disbursements without transfer evidence.
- Mobile-number-only loan lookup must not expose real borrower details; protect public repayment lookup before production use.

## Required production testing
Test branch assignments, staff access denial, application approval controls, customer KYC, disbursement evidence, successful and failed Cashfree webhooks, idempotent repayments, reconciliation, overdue classification, deletion/restoration and foreclosure with a staging database before live use.
