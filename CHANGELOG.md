# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- Added OCA dependency repositories for the Wave 1 Sales baseline and formalized them as Git submodules for reproducible setup.
- Extended `od19_sales_oca_bridge_workflow` to support the required-now OCA baseline for blanket orders, sale revisions, and exception-driven controls.
- Added `docs/superpowers/programs/odoo19-enterprise/sales/oca-installation-recommendations.md` to map OCA sales modules into `Wave 1`, `Wave 2`, `Wave 3`, and `Deferred / Not now`.

### Changed
- Aligned Sales OCA baseline references across fit-gap, addon boundaries, baseline design, and the Wave 1 implementation plan.
- Updated the Wave 1 Sales Contract Core design to include explicit OCA installation guidance by wave.

### Fixed
- Tightened the OCA bridge baseline after review follow-ups so the required-now stack matches the approved baseline more closely.
- Cleaned up OCA bridge form semantics and related bridge tests to reduce UI ambiguity in the sales workflow.

### Documentation
- Added a documented shortlist for immediate OCA installation: `base_user_role`, `sale_blanket_order`, `base_revision`, `sale_order_revision`, `sale_delivery_state`, `base_exception`, and `sale_exception`.
- Documented the next recommended candidates for later waves: `sale_order_line_price_source`, `sale_invoice_to_partner`, `sale_invoice_blocking`, `sale_order_type`, `sale_invoice_frequency`, `sale_substate`, and `sale_cancel_reason`.
- Kept `sale_tier_validation` and `sale_invoice_plan` in deferred status pending clearer 19.0 baseline confirmation.
