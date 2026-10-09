# Odoo 19 CE Enterprise Program Workspace

This directory contains the executable planning workspace for the company-wide Odoo 19 CE rebuild program.

The target source of truth is Odoo 19 CE. Historical file or folder names may still contain older wording where renaming would add churn without improving control.

## Purpose

- Keep all program-level artifacts in one place
- Separate blueprint/governance from domain implementation
- Track discovery, standards, backlog, and review gates

## Subdirectories

- `discovery/` - evidence from Odoo 15 CE
- `foundation/` - engineering and platform rules
- `governance/` - gates, decision records, operating model
- `backlog/` - wave sequencing and domain spec index
- `reporting/` - KPI contracts and dashboard blueprint baseline
- `sales/` - active sales governance and OCA alignment references

## Working Rules

1. No domain build starts without an approved domain spec.
2. Standard Odoo and OCA options are evaluated before custom build.
3. No direct Odoo core modifications are allowed.
4. Every artifact in this workspace must be reviewable and versioned.

## OCA Submodule Setup

This project stores approved OCA dependencies as Git submodules under `third_party/oca/`.
If a machine has cloned the repository but has not initialized submodules yet, Odoo will not be able to find modules such as `sale-workflow`, `sale-blanket`, `server-backend`, `server-tools`, or `server-ux`.

### When this is required

Run submodule initialization before:

- running Odoo with custom addons that depend on OCA modules
- executing tests for `od19_sales_oca_bridge_workflow`
- validating Wave 1 Sales OCA baseline on a new machine or fresh clone

### Quick guide

1. Clone the main repository as usual.
2. From the repository root, run:

```bash
git submodule update --init --recursive
```

3. Verify that submodules are checked out:

```bash
git submodule status
```

4. Then run Odoo or tests normally.

### What the command does

- `init` registers submodules configured in `.gitmodules` for the current clone
- `update` checks out each submodule at the exact commit pinned by the main repository
- `recursive` applies the same process to nested submodules if they exist

### Practical note for this program

For the current Sales wave, this step is mandatory before using or testing:

- `base_user_role`
- `base_revision`
- `sale_order_revision`
- `base_exception`
- `sale_exception`
- `sale_blanket_order`
- `sale_delivery_state`

Reference: `docs/superpowers/programs/odoo19-enterprise/sales/oca-installation-recommendations.md`

## Execution Order

1. Complete discovery pack with evidence from Odoo 15 CE
2. Confirm engineering and governance rules
3. Approve domain wave sequencing
4. Write child specs per wave
5. Generate implementation plans per child spec

## Wave 0 Artifact Pack

- [foundation/repository-and-addon-baseline.md](foundation/repository-and-addon-baseline.md)
- [foundation/environment-and-delivery-baseline.md](foundation/environment-and-delivery-baseline.md)
- [foundation/production-readiness-baseline.md](foundation/production-readiness-baseline.md)
- [reporting/kpi-reporting-baseline.md](reporting/kpi-reporting-baseline.md)
- [reporting/role-based-dashboard-blueprint.md](reporting/role-based-dashboard-blueprint.md)
- [governance/wave-0-readiness-assessment.md](governance/wave-0-readiness-assessment.md)
- [governance/wave-1-handoff-baseline.md](governance/wave-1-handoff-baseline.md)

## Additional Governed Areas

- [backlog/domain-wave-matrix.md](backlog/domain-wave-matrix.md)
- [backlog/domain-spec-index.md](backlog/domain-spec-index.md)
- [sales/addon-boundaries.md](sales/addon-boundaries.md)
- [sales/oca-fit-gap.md](sales/oca-fit-gap.md)
- [sales/oca-installation-recommendations.md](sales/oca-installation-recommendations.md)
