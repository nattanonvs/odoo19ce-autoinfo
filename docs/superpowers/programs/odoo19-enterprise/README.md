# Odoo 19 CE Enterprise Program Workspace

This directory contains the executable planning workspace for the company-wide Odoo 19 CE rebuild program.

## Purpose

- Keep all program-level artifacts in one place
- Separate blueprint/governance from domain implementation
- Track discovery, standards, backlog, and review gates

## Subdirectories

- `discovery/` - evidence from Odoo 15 CE
- `foundation/` - engineering and platform rules
- `governance/` - gates, decision records, operating model
- `backlog/` - wave sequencing and domain spec index

## Working Rules

1. No domain build starts without an approved domain spec.
2. Standard Odoo and OCA options are evaluated before custom build.
3. No direct Odoo core modifications are allowed.
4. Every artifact in this workspace must be reviewable and versioned.

## Execution Order

1. Complete discovery pack with evidence from Odoo 15 CE
2. Confirm engineering and governance rules
3. Approve domain wave sequencing
4. Write child specs per wave
5. Generate implementation plans per child spec
