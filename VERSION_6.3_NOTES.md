# OWL FINANCE 6.3 — Customer 360 & Operations

- Customer directory opens individual profiles with applications, KYC status, loan terms, repayment and foreclosure history.
- Admin can edit customer name and phone, with audit logging. Financial fields are intentionally changed only through their corresponding verified workflows.
- Admin dashboard groups application requests, KYC pending, review, disbursement pending, active, closed, foreclosed and deleted loans.
- Admin can soft-delete any loan after entering a reason and exact confirmation phrase. This removes it from normal operational lists but **does not erase loan, disbursement, payment, KYC, or audit records**. Admin can restore the loan.
- Banking-inspired visual theme (original UI, not a copy of ICICI assets).
- No new database columns or migrations required.
- IMPORTANT: Do not soft-delete a loan to avoid an outstanding legal repayment obligation; operational deletion is not debt forgiveness. Test with a staging database before production.
