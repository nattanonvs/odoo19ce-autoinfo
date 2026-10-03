# Odoo 19 CE Enterprise Blueprint

Date: 2026-10-04
Status: Draft for user review
Scope: Enterprise-wide greenfield rebuild using Odoo 15 CE as a study/reference system

## 1. Purpose

This blueprint defines how the company should design and build a new Odoo 19 Community Edition platform without carrying forward the technical debt and structural weaknesses of the current Odoo 15 CE implementation.

The new platform is not a version-to-version migration project. It is an enterprise redesign and engineering governance program with these goals:

- Make future upgrades easier.
- Make maintenance easier.
- Use clear, standard, readable engineering practices.
- Avoid direct modifications to Odoo core.
- Enforce modular design so addons can be installed or removed safely.
- Use OCA-first principles wherever possible.
- Allow business flow redesign where legacy behavior conflicts with the target principles.
- Improve the owner's ability to analyze, monitor, and steer the business using system data.

## 2. Strategic Position

The Odoo 15 CE system is a reference system, not a technical template.

The current system should be used to study:

- Actual business flows
- Exceptions and edge cases
- Custom domains and custom models
- Reports used by managers and owners
- User roles and approval paths
- Data quality and master data structure
- Pain points, workarounds, and technical debt

The Odoo 19 CE system should be designed from the target operating model, not by copying the current implementation.

## 3. Design Principles

The new platform must follow these non-negotiable principles:

1. Upgradeability first
2. Maintainability first
3. Readable and standard engineering practices
4. No direct core modifications
5. Modular install/uninstall safety
6. OCA-first adoption and OCA-style discipline
7. Business redesign allowed when legacy behavior conflicts with better practice
8. Controlled human-governed AI-assisted delivery
9. Owner-focused reporting and decision support

## 4. Target Architecture

The platform should be designed as a greenfield enterprise platform with six layers:

### 4.1 Odoo Core CE Layer

- Standard Odoo 19 CE only
- No direct changes to Odoo source files
- No core patching as a normal delivery method

### 4.2 OCA Foundation Layer

- OCA modules adopted before considering custom build
- OCA repository and addon conventions used as baseline engineering discipline
- OCA quality expectations used as a reference for module boundaries, testing, and packaging

### 4.3 Company Extension Layer

- Company-specific addons only for genuine business gaps
- One addon per bounded responsibility where possible
- No mega-module covering multiple unrelated domains

### 4.4 Integration Layer

- External APIs
- Imports/exports
- Connectors
- Messaging and document exchanges
- Integration jobs separated from domain logic when possible

### 4.5 Analytics and Decision Layer

- KPI models
- Management reporting
- Alerts and signals
- Analytical datasets and dashboards for owner and leadership use

### 4.6 Delivery and Governance Layer

- Repositories
- CI/CD
- Tests
- Reviews
- Release governance
- Documentation
- Rollback and cutover control

## 5. OCA-First Policy

Every requirement must pass this decision order:

1. Standard Odoo
2. OCA
3. Approved third-party module
4. Custom build

If a requirement does not use OCA when OCA exists, the reason must be recorded in writing.

If a third-party module is selected, it must be reviewed for:

- License
- Maintainability
- Community activity
- Upgrade support
- Code quality
- Operational risk

## 6. Module Policy

Every custom module must follow these rules:

- Clear purpose
- Clear dependency declaration
- No hidden coupling
- No reliance on side effects in unrelated modules
- Safe installation on a clean environment
- Controlled upgrade path
- Safe uninstall expectation
- Documentation and test ownership

Each module should include, at minimum:

- Manifest
- Security rules
- Views
- Data files
- Tests
- Migration notes
- Ownership and purpose description

## 7. Core Protection Rule

The project must not modify Odoo core directly.

Allowed extension mechanisms:

- Inheritance and extension through custom addons
- Standard hooks and extension points
- Controlled overrides with clear contract

Disallowed as normal practice:

- Direct file edits inside `odoo/`
- Direct edits in standard addons
- Untracked source hacks
- Emergency shortcuts that break future upgrades

If exceptional patching is ever required, it must be:

- Explicitly approved
- Documented with justification
- Tracked with removal plan
- Treated as temporary technical debt

## 8. Delivery Model

The delivery model is human-governed and AI-accelerated.

### 8.1 Roles

#### Business Owners and Sponsors

- Define business objectives
- Define investment intent
- Approve major decisions
- Approve redesigned flows that impact staff behavior

#### Domain Key Users

- Explain actual business processes
- Validate exceptions
- Review future-state flow
- Participate in UAT and training review

#### Human Technical Supervisors

- Review architecture and code
- Approve risky operations
- Control production access
- Validate security, quality, and release readiness

#### TRAE AI Agents

- Analyze current system
- Produce maps, specs, plans, code, tests, and documentation
- Accelerate delivery under review gates

### 8.2 Rules of Engagement

- AI may not bypass review gates.
- Important decisions must be backed by evidence.
- Production changes require explicit approval and rollback readiness.
- No domain should start building before blueprint and domain spec approval.
- No critical deployment should happen without human review.

## 9. Access and Readiness Requirements

To let the new-system team work effectively, the company must provide:

### 9.1 System Access

- Odoo 15 CE admin access
- Developer mode and technical access
- Full menu visibility across all relevant companies and domains

### 9.2 Server and Environment Access

- Read-only production access where appropriate
- Shell access to staging or clone environment
- Odoo configuration visibility
- Addon path visibility
- Service and deployment configuration visibility

### 9.3 Database Access

- Full database dump
- Sanitized copy for analysis and development
- Access to inspect schema, record counts, and data quality issues

### 9.4 Source Code Access

- All custom addons
- Related repositories
- Deployment scripts
- Configuration files

### 9.5 Integration Access

- Integration inventory
- API documents
- Test credentials where applicable
- Mail, documents, payment, and automation settings

## 10. Legacy Screening Rules

Nothing in Odoo 15 CE should be migrated automatically.

Every feature, screen, report, field, document, and process should be classified as:

- Keep
- Refactor
- Replace
- Retire

Every legacy item must be reviewed against these questions:

- Does it still solve a real business problem?
- Is it only compensating for limitations in the old system?
- Is there a standard or OCA solution that is better?
- Does it help operational work, owner decision-making, or both?
- Is it worth its long-term maintenance cost?

Legacy workarounds should be treated as redesign signals, not features to preserve.

## 11. Owner-Value Design Rule

Every domain in the new platform must answer:

- What does the owner need to see?
- What should leadership be able to measure?
- What signals or warnings should the system generate?
- Which trends, ratios, or variances matter?
- Which decisions become faster or better because of the system?

The new platform is not complete unless it improves decision quality, not just daily operations.

## 12. Workstreams

The program should be split into the following workstreams:

1. Discovery and legacy intelligence
2. Enterprise blueprint and governance
3. Data and reporting strategy
4. Foundation platform
5. Domain redesign
6. Build and verification
7. Training and change adoption
8. Parallel run and cutover

## 13. Sequencing

Recommended sequence:

### Phase A: Discovery

- Custom map
- Process map
- Report map
- Data map
- Integration map

### Phase B: Blueprint

- Architecture
- Engineering standards
- Governance model
- OCA/custom policy

### Phase C: Foundation

- Odoo 19 CE baseline
- Repository structure
- Environments
- CI/CD
- Testing harness

### Phase D: Domain Design

- Future-state domain specs
- Role and approval model
- Reporting and KPI requirements

### Phase E: Incremental Build

- Module-by-module implementation
- Review and verification
- Reconciliation against current business reality

### Phase F: Adoption Preparation

- Training package
- Manuals
- Sandbox exercises
- Change communication

### Phase G: Parallel Run and Cutover

- Validation against current system
- Reconciliation of critical outputs
- Phased cutover
- Hypercare and support

## 14. Recommended Domain Waves

Because the scope is enterprise-wide, delivery should still be phased.

### Wave 0

- Foundation platform
- Governance
- KPI and reporting baseline

### Wave 1

- Contacts
- Sales
- Purchase
- Inventory
- Accounting

### Wave 2

- Advance
- Cheque
- Money In Analysis

### Wave 3

- Sales Services
- Claims
- Warranty
- Service Card flows
- Product Return

### Wave 4

- Stock Requests
- Transportation
- Logistics extensions

### Wave 5

- Employees
- Attendances
- Time Off
- Other operational enablement domains

## 15. Engineering Standards

### 15.1 Coding Standards

- Readable Python and Odoo conventions
- Clear naming
- Small and focused methods
- Explicit business intent in function boundaries
- Comments explaining why, not repeating what

### 15.2 Security Standards

- Explicit access rights and record rules
- Minimize `sudo()`
- Traceable approval and financial actions
- Review of all privileged operations

### 15.3 Data Model Standards

- Add fields only with business justification
- Avoid speculative fields
- Plan schema evolution from day one
- Define migration strategy for every material schema change

### 15.4 Workflow Standards

- Explicit state transitions
- Testable approval logic
- Avoid hiding critical business logic in fragile automation
- Cron jobs and automations must be documented and controlled

### 15.5 Testing Standards

Every important module should include:

- Install tests
- Upgrade tests
- Key business flow tests
- Security tests
- Regression tests for critical domains

### 15.6 Documentation Standards

Each module and each domain should have:

- Purpose
- Scope
- Dependencies
- Roles
- Process summary
- Technical notes
- Known limitations

## 16. Parallel Run Strategy

The Odoo 19 CE system should run in parallel with Odoo 15 CE before cutover.

Parallel run must validate:

- Business flows
- Key numbers and reconciliations
- User roles and approvals
- KPI and management reporting outputs

The objective is not only to prove the new system works, but to prove it is more suitable and more reliable.

## 17. Definition of Success

The program is successful only when all of the following are true:

### Technical Success

- No direct core modifications
- Modular custom design
- Safe install, upgrade, and removal behavior
- Maintainable, readable engineering baseline

### Operational Success

- Enterprise-wide flows work in the new system
- Workarounds are reduced
- Controls are clearer and stronger than before

### Data Success

- Master data is governed and reliable
- Critical reports reconcile appropriately
- KPI and decision support outputs are available and trusted

### Governance Success

- Owners and reviewers are defined
- Decisions are traceable
- Handover is possible without depending on one individual

### Investment Success

- The owner receives better information for control, planning, and growth decisions
- The company gains a more sustainable operating platform, not only a newer version

## 18. Non-Negotiables

- No direct edits to Odoo core
- No copying legacy behavior without screening
- No custom build before standard/OCA review
- No fragile module dependencies
- No uncontrolled AI-driven production change
- No cutover without documentation, training, reconciliation, and rollback readiness
- No success claim based only on visual similarity to the legacy system

## 19. Kill Criteria

The program must stop and re-evaluate if any of the following happen:

- Building starts before blueprint approval
- Core is modified for convenience
- Domain specs remain unclear while implementation proceeds
- No business owner can make decisions for a domain
- Reporting requirements remain undefined while data structures are locked in
- Migration readiness is weak but cutover pressure increases
- Training and documentation are treated as optional or postponed to the end

## 20. Deliverables

The blueprint should eventually produce:

- Enterprise blueprint
- Domain specs
- Engineering standards
- Governance model
- Access and readiness checklist
- Custom map and legacy intelligence pack
- Reporting and KPI strategy
- Training and adoption strategy
- Roadmap and phase gates

## 21. Immediate Next Steps

The next planning layer after this blueprint should be:

1. Break the program into domain-level specs
2. Build the discovery pack from Odoo 15 CE
3. Define foundation engineering standards in executable form
4. Create the implementation roadmap and review gates

The first practical execution target should be a master implementation plan derived from this blueprint, followed by workstream plans and domain-specific specs.
