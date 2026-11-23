# OWL FINANCE 7.0.1 — Branch-first staff workflow

1. Log in as admin and create a branch at `/admin/enterprise/branches`.
2. Add staff at `/admin/staff`, selecting an active branch. Staff creation is blocked when there are no active branches.
3. Change existing staff memberships at `/admin/enterprise/staff`. Reassignment is blocked while the staff member owns applications from another branch.
4. Application assignments at `/admin/enterprise/assignments` now reject staff from a different branch.

Database: a new additive `enterprise_staff_branch` table is created by the existing `db.create_all()` startup flow. Existing staff remain unassigned until an administrator assigns them. Back up Neon before deploying.

Important: this release enforces branch membership during staff creation and application assignment. It does not yet enforce branch-based access across every legacy admin route.
