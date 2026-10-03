# Odoo 19 CE Wave 0 Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** เปลี่ยน Wave 0 design spec ให้เป็นชุด artifact ที่ใช้งานจริงได้ใน program workspace พร้อมตัวตรวจสอบความครบถ้วนก่อนเริ่ม Wave 1

**Architecture:** แผนนี้ไม่สร้าง business modules ของ Odoo โดยตรง แต่สร้างฐานเอกสารและกติกาที่โปรแกรมต้องใช้จริง ได้แก่ foundation baselines, production readiness baseline, KPI/reporting baselines, dashboard blueprint, readiness assessment และ handoff package ไป Wave 1 พร้อมผูกทุก artifact เข้ากับ `program-manifest.yaml` เพื่อให้ validator ตรวจได้อัตโนมัติ

**Tech Stack:** Markdown, Python 3, pytest, Git, existing `tools/program_blueprint/check_program_workspace.py`

---

## File Structure

**Create**
- `docs/superpowers/programs/odoo19-enterprise/foundation/repository-and-addon-baseline.md`
- `docs/superpowers/programs/odoo19-enterprise/foundation/environment-and-delivery-baseline.md`
- `docs/superpowers/programs/odoo19-enterprise/foundation/production-readiness-baseline.md`
- `docs/superpowers/programs/odoo19-enterprise/reporting/kpi-reporting-baseline.md`
- `docs/superpowers/programs/odoo19-enterprise/reporting/role-based-dashboard-blueprint.md`
- `docs/superpowers/programs/odoo19-enterprise/governance/wave-0-readiness-assessment.md`
- `docs/superpowers/programs/odoo19-enterprise/governance/wave-1-handoff-baseline.md`

**Modify**
- `docs/superpowers/specs/2026-10-04-odoo19-enterprise-wave-0-foundation-governance-design.md`
- `docs/superpowers/programs/odoo19-enterprise/README.md`
- `docs/superpowers/programs/odoo19-enterprise/backlog/domain-spec-index.md`
- `docs/superpowers/programs/odoo19-enterprise/program-manifest.yaml`
- `tools/program_blueprint/tests/test_check_program_workspace.py`

**Reuse Without Code Changes**
- `tools/program_blueprint/check_program_workspace.py`
- `docs/superpowers/programs/odoo19-enterprise/foundation/engineering-standards.md`
- `docs/superpowers/programs/odoo19-enterprise/governance/review-gates.md`

## Scope Note

Wave 0 spec ครอบคลุมหลายหัวข้อ แต่ในแผนนี้จะทำเป็น `หนึ่งแพ็กเกจ foundation` ที่ส่งมอบได้จริงและตรวจสอบได้จริงก่อน จากนั้นค่อยแตก `Wave 1` เป็น child specs รายโดเมนธุรกิจ เช่น Sales, Purchase, Inventory, Accounting ต่อไป

### Task 1: ผูก Wave 0 เข้ากับ Program Manifest

**Files:**
- Modify: `tools/program_blueprint/tests/test_check_program_workspace.py`
- Modify: `docs/superpowers/programs/odoo19-enterprise/program-manifest.yaml`

- [ ] **Step 1: เขียน failing test เพื่อบังคับให้ manifest รู้จักไฟล์ Wave 0**

เพิ่ม test นี้ต่อท้าย `tools/program_blueprint/tests/test_check_program_workspace.py`

```python
def test_program_manifest_tracks_wave0_foundation_artifacts() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    manifest_path = (
        repo_root
        / "docs/superpowers/programs/odoo19-enterprise/program-manifest.yaml"
    )

    data = load_manifest(manifest_path)

    expected_paths = [
        "docs/superpowers/programs/odoo19-enterprise/foundation/repository-and-addon-baseline.md",
        "docs/superpowers/programs/odoo19-enterprise/foundation/environment-and-delivery-baseline.md",
        "docs/superpowers/programs/odoo19-enterprise/foundation/production-readiness-baseline.md",
        "docs/superpowers/programs/odoo19-enterprise/reporting/kpi-reporting-baseline.md",
        "docs/superpowers/programs/odoo19-enterprise/reporting/role-based-dashboard-blueprint.md",
        "docs/superpowers/programs/odoo19-enterprise/governance/wave-0-readiness-assessment.md",
        "docs/superpowers/programs/odoo19-enterprise/governance/wave-1-handoff-baseline.md",
    ]

    assert all(path in data["required_paths"] for path in expected_paths)
```

- [ ] **Step 2: รัน test เพื่อยืนยันว่าล้มก่อน**

Run:

```bash
python -m pytest tools/program_blueprint/tests/test_check_program_workspace.py::test_program_manifest_tracks_wave0_foundation_artifacts -v
```

Expected:

```text
FAILED tools/program_blueprint/tests/test_check_program_workspace.py::test_program_manifest_tracks_wave0_foundation_artifacts
```

- [ ] **Step 3: เพิ่ม required paths ของ Wave 0 ลงใน manifest**

แก้ `docs/superpowers/programs/odoo19-enterprise/program-manifest.yaml` ให้มีรายการเพิ่มดังนี้:

```yaml
required_paths:
  - docs/superpowers/programs/odoo19-enterprise/README.md
  - docs/superpowers/programs/odoo19-enterprise/discovery/current-state-inventory.md
  - docs/superpowers/programs/odoo19-enterprise/discovery/access-readiness-checklist.md
  - docs/superpowers/programs/odoo19-enterprise/foundation/engineering-standards.md
  - docs/superpowers/programs/odoo19-enterprise/foundation/repository-and-addon-baseline.md
  - docs/superpowers/programs/odoo19-enterprise/foundation/environment-and-delivery-baseline.md
  - docs/superpowers/programs/odoo19-enterprise/foundation/production-readiness-baseline.md
  - docs/superpowers/programs/odoo19-enterprise/governance/review-gates.md
  - docs/superpowers/programs/odoo19-enterprise/governance/wave-0-readiness-assessment.md
  - docs/superpowers/programs/odoo19-enterprise/governance/wave-1-handoff-baseline.md
  - docs/superpowers/programs/odoo19-enterprise/reporting/kpi-reporting-baseline.md
  - docs/superpowers/programs/odoo19-enterprise/reporting/role-based-dashboard-blueprint.md
  - docs/superpowers/programs/odoo19-enterprise/backlog/domain-wave-matrix.md
  - docs/superpowers/programs/odoo19-enterprise/backlog/domain-spec-index.md
```

- [ ] **Step 4: รัน test ซ้ำให้ผ่าน**

Run:

```bash
python -m pytest tools/program_blueprint/tests/test_check_program_workspace.py::test_program_manifest_tracks_wave0_foundation_artifacts -v
```

Expected:

```text
PASSED tools/program_blueprint/tests/test_check_program_workspace.py::test_program_manifest_tracks_wave0_foundation_artifacts
```

- [ ] **Step 5: Commit งานนี้**

```bash
git add tools/program_blueprint/tests/test_check_program_workspace.py docs/superpowers/programs/odoo19-enterprise/program-manifest.yaml
git commit -m "test(program): track Wave 0 foundation artifacts"
```

### Task 2: สร้าง Foundation Baselines

**Files:**
- Create: `docs/superpowers/programs/odoo19-enterprise/foundation/repository-and-addon-baseline.md`
- Create: `docs/superpowers/programs/odoo19-enterprise/foundation/environment-and-delivery-baseline.md`
- Create: `docs/superpowers/programs/odoo19-enterprise/foundation/production-readiness-baseline.md`

- [ ] **Step 1: สร้างเอกสาร repository และ addon baseline**

สร้าง `docs/superpowers/programs/odoo19-enterprise/foundation/repository-and-addon-baseline.md` ด้วยโครงนี้:

```md
# Repository and Addon Baseline

## Purpose
- กำหนดว่าของแต่ละประเภทต้องอยู่ตรงไหน
- กันการปนกันระหว่าง docs, addons, deployment, tests, migrations

## Repository Layout Rules
- `docs/` เก็บ specs, plans, governance, reporting artifacts
- `custom_addons/` เก็บ company-specific addons
- `third_party/oca/` เก็บ OCA addons ที่เลือกใช้
- `deployment/` เก็บ config, compose, service, release notes
- `tests/` หรือ test paths ตาม addon สำหรับ automation

## Addon Boundary Rules
- หนึ่ง addon มีหน้าที่หลักหนึ่งเรื่อง
- dependency ต้องประกาศใน manifest เท่านั้น
- ห้าม hidden coupling
- ต้อง install, upgrade, uninstall ได้

## Naming Rules
- addon ใช้ prefix เดียวกันตาม program
- model, field, security group, data xml id ต้องสื่อความหมายและ trace กลับ spec ได้
```

- [ ] **Step 2: สร้างเอกสาร environment และ delivery baseline**

สร้าง `docs/superpowers/programs/odoo19-enterprise/foundation/environment-and-delivery-baseline.md` ด้วยโครงนี้:

```md
# Environment and Delivery Baseline

## Environment Model
- Local Dev
- Shared Dev / Integration
- Test / QA
- UAT / Training
- Production

## Access Expectations
- ใครเข้าได้
- ใช้ข้อมูลประเภทไหน
- เปลี่ยนแปลงผ่านใคร

## Delivery Baseline
- merge ต้องผ่าน lint/tests/review
- deploy ต้องมี release note และ rollback expectation
- ห้ามใช้ production เป็นที่ทดลอง

## Minimum Quality Gates
- lint
- automated tests
- install/uninstall checks
- security review
- upgrade note
```

- [ ] **Step 3: สร้าง production readiness baseline**

สร้าง `docs/superpowers/programs/odoo19-enterprise/foundation/production-readiness-baseline.md` ด้วยโครงนี้:

```md
# Production Readiness Baseline

## Production Topology Expectations
- app layer
- database layer
- worker/cron layer
- reverse proxy
- file storage and backup scope

## Ownership
- config owner
- deployment owner
- security reviewer
- incident first responder

## Safety Baselines
- secrets must not live in source code
- backups must cover database and filestore
- restore path must be testable
- logging and monitoring must exist before go-live
- rollback path must be defined before release
```

- [ ] **Step 4: รัน validator เพื่อยืนยันว่าตอนนี้ยังขาดไฟล์ Wave 0 ชุดอื่นอยู่**

Run:

```bash
python tools/program_blueprint/check_program_workspace.py
```

Expected:

```text
Missing required program files:
- docs/superpowers/programs/odoo19-enterprise/reporting/kpi-reporting-baseline.md
- docs/superpowers/programs/odoo19-enterprise/reporting/role-based-dashboard-blueprint.md
- docs/superpowers/programs/odoo19-enterprise/governance/wave-0-readiness-assessment.md
- docs/superpowers/programs/odoo19-enterprise/governance/wave-1-handoff-baseline.md
```

- [ ] **Step 5: Commit งานนี้**

```bash
git add docs/superpowers/programs/odoo19-enterprise/foundation/repository-and-addon-baseline.md docs/superpowers/programs/odoo19-enterprise/foundation/environment-and-delivery-baseline.md docs/superpowers/programs/odoo19-enterprise/foundation/production-readiness-baseline.md
git commit -m "docs(program): add Wave 0 foundation baselines"
```

### Task 3: สร้าง Reporting และ Dashboard Baselines

**Files:**
- Create: `docs/superpowers/programs/odoo19-enterprise/reporting/kpi-reporting-baseline.md`
- Create: `docs/superpowers/programs/odoo19-enterprise/reporting/role-based-dashboard-blueprint.md`

- [ ] **Step 1: สร้าง KPI และ reporting baseline**

สร้าง `docs/superpowers/programs/odoo19-enterprise/reporting/kpi-reporting-baseline.md` ด้วยโครงนี้:

```md
# KPI and Reporting Baseline

## Purpose
- กำหนดว่า owner, manager, และ operational lead ควรเห็นข้อมูลอะไร

## KPI Layers
- Owner level
- Management level
- Operational level

## Reporting Contract
- รายงานนี้ตอบคำถามอะไร
- ใครใช้
- ใช้ตัดสินใจอะไร
- มาจากข้อมูลไหน
- อัปเดตถี่แค่ไหน
- drill-down ได้แค่ไหน

## Signal and Alert Model
- health signals
- control alerts
- operational alerts
- severity owner
- expected response
```

- [ ] **Step 2: สร้าง dashboard blueprint ตามบทบาท**

สร้าง `docs/superpowers/programs/odoo19-enterprise/reporting/role-based-dashboard-blueprint.md` ด้วยโครงนี้:

```md
# Role-Based Dashboard Blueprint

## Owner Dashboard
- executive summary
- risk and alert zone
- trend zone
- business unit comparison
- decision support

## Management Dashboard
- performance summary
- pipeline/workload
- exception zone
- SLA/timeliness
- manager action zone

## Operational Lead Dashboard
- today's priority queue
- pending and stuck workflows
- near deadline zone
- execution health
- operational actions
```

- [ ] **Step 3: เติมกติกา dashboard ที่ต้องใช้ร่วมกัน**

เพิ่มส่วนนี้ใน `docs/superpowers/programs/odoo19-enterprise/reporting/role-based-dashboard-blueprint.md`

```md
## Shared Dashboard Rules
- summary first
- alerts second
- trend third
- drill-down after that

## Red / Yellow / Green Logic
- Red = ต้องจัดการทันที
- Yellow = ต้องติดตามใกล้ชิด
- Green = อยู่ในเกณฑ์ยอมรับได้
- Grey = ข้อมูลไม่พร้อมหรือไม่ใช้ในบริบทนี้

## Drill-Down Rules
- owner ลงได้ถึง summary and exception detail
- manager ลงได้ถึง team/domain detail
- operational lead ลงได้ถึง queue และ document level
```

- [ ] **Step 4: รัน validator เพื่อยืนยันว่ายังเหลือเฉพาะเอกสาร governance**

Run:

```bash
python tools/program_blueprint/check_program_workspace.py
```

Expected:

```text
Missing required program files:
- docs/superpowers/programs/odoo19-enterprise/governance/wave-0-readiness-assessment.md
- docs/superpowers/programs/odoo19-enterprise/governance/wave-1-handoff-baseline.md
```

- [ ] **Step 5: Commit งานนี้**

```bash
git add docs/superpowers/programs/odoo19-enterprise/reporting/kpi-reporting-baseline.md docs/superpowers/programs/odoo19-enterprise/reporting/role-based-dashboard-blueprint.md
git commit -m "docs(program): add Wave 0 reporting baselines"
```

### Task 4: สร้าง Readiness Assessment และ Handoff Pack

**Files:**
- Create: `docs/superpowers/programs/odoo19-enterprise/governance/wave-0-readiness-assessment.md`
- Create: `docs/superpowers/programs/odoo19-enterprise/governance/wave-1-handoff-baseline.md`
- Modify: `docs/superpowers/specs/2026-10-04-odoo19-enterprise-wave-0-foundation-governance-design.md`

- [ ] **Step 1: สร้าง readiness assessment**

สร้าง `docs/superpowers/programs/odoo19-enterprise/governance/wave-0-readiness-assessment.md` ด้วยโครงนี้:

```md
# Wave 0 Readiness Assessment

## Readiness Areas
| Area | Status | Owner | Notes |
| --- | --- | --- | --- |
| Governance baseline | Draft | Program delivery lead | Waiting for implementation evidence |
| Technical platform baseline | Draft | Program engineering lead | Waiting for artifact package |
| Production readiness baseline | Draft | Architecture lead | Waiting for review |
| KPI/reporting baseline | Draft | Business sponsor | Waiting for dashboard review |
| Wave 1 handoff | Draft | Program delivery lead | Waiting for handoff package |

## Exit Criteria Checklist
- governance approved
- technical baseline approved
- reporting baseline approved
- handoff package ready
```

- [ ] **Step 2: สร้าง Wave 1 handoff baseline**

สร้าง `docs/superpowers/programs/odoo19-enterprise/governance/wave-1-handoff-baseline.md` ด้วยโครงนี้:

```md
# Wave 1 Handoff Baseline

## What Wave 1 Receives
- approved Wave 0 child spec
- engineering standards
- review gates
- repository and addon baseline
- environment and delivery baseline
- production readiness baseline
- KPI/reporting baseline
- dashboard blueprint

## What Wave 1 Still Must Define
- domain transaction flows
- field-level mapping
- domain-specific security details
- migration details by domain

## Deferred Items
- UI detail
- implementation code
- dashboard build in Odoo
```

- [ ] **Step 3: เปลี่ยนสถานะใน Wave 0 spec ให้สอดคล้องกับการอนุมัติแล้ว**

แก้บรรทัดต้น ๆ ของ `docs/superpowers/specs/2026-10-04-odoo19-enterprise-wave-0-foundation-governance-design.md`

จาก:

```md
สถานะ: รอผู้ใช้ทบทวน
```

เป็น:

```md
สถานะ: อนุมัติแล้ว
```

- [ ] **Step 4: รัน validator ให้ผ่านทั้งแพ็กเกจ**

Run:

```bash
python tools/program_blueprint/check_program_workspace.py
```

Expected:

```text
Program workspace is complete.
```

- [ ] **Step 5: Commit งานนี้**

```bash
git add docs/superpowers/programs/odoo19-enterprise/governance/wave-0-readiness-assessment.md docs/superpowers/programs/odoo19-enterprise/governance/wave-1-handoff-baseline.md docs/superpowers/specs/2026-10-04-odoo19-enterprise-wave-0-foundation-governance-design.md
git commit -m "docs(program): add Wave 0 readiness and handoff"
```

### Task 5: อัปเดต README และดัชนีสเปกโดยไม่ทับของเดิม

**Files:**
- Modify: `docs/superpowers/programs/odoo19-enterprise/README.md`
- Modify: `docs/superpowers/programs/odoo19-enterprise/backlog/domain-spec-index.md`

- [ ] **Step 1: อ่านไฟล์ปัจจุบันก่อนแก้ และรักษาเนื้อหาที่มีอยู่แล้ว**

Run:

```bash
git diff -- docs/superpowers/programs/odoo19-enterprise/README.md docs/superpowers/programs/odoo19-enterprise/backlog/domain-spec-index.md
```

Expected:

```text
Output may be empty or show current local edits; do not delete existing content unless the plan explicitly replaces that section.
```

- [ ] **Step 2: เพิ่มส่วน Wave 0 artifact pack ใน README**

เพิ่มหัวข้อแบบนี้ลงใน `docs/superpowers/programs/odoo19-enterprise/README.md` โดยต่อท้ายหรือแทรกในส่วน artifact overview ที่มีอยู่แล้ว:

```md
## Wave 0 Artifact Pack
- `foundation/repository-and-addon-baseline.md`
- `foundation/environment-and-delivery-baseline.md`
- `foundation/production-readiness-baseline.md`
- `reporting/kpi-reporting-baseline.md`
- `reporting/role-based-dashboard-blueprint.md`
- `governance/wave-0-readiness-assessment.md`
- `governance/wave-1-handoff-baseline.md`
```

- [ ] **Step 3: อัปเดต domain spec index ให้เห็นสถานะ Wave 0 ชัดเจน**

เพิ่มหรือแก้ section ที่เกี่ยวกับ Wave 0 ใน `docs/superpowers/programs/odoo19-enterprise/backlog/domain-spec-index.md` ให้มีรูปแบบชัดเจน เช่น:

```md
## Wave 0
| Item | Status | Primary artifact |
| --- | --- | --- |
| Foundation and governance baseline | Approved | `docs/superpowers/specs/2026-10-04-odoo19-enterprise-wave-0-foundation-governance-design.md` |
| Implementation pack | In progress | `docs/superpowers/plans/2026-10-04-odoo19-enterprise-wave-0-foundation-governance-implementation-plan.md` |
| Handoff to Wave 1 | Draft | `docs/superpowers/programs/odoo19-enterprise/governance/wave-1-handoff-baseline.md` |
```

- [ ] **Step 4: ตรวจ whitespace และ validator ซ้ำ**

Run:

```bash
git diff --check
python tools/program_blueprint/check_program_workspace.py
```

Expected:

```text
No trailing whitespace errors
Program workspace is complete.
```

- [ ] **Step 5: Commit งานนี้**

```bash
git add docs/superpowers/programs/odoo19-enterprise/README.md docs/superpowers/programs/odoo19-enterprise/backlog/domain-spec-index.md
git commit -m "docs(program): link Wave 0 artifact pack"
```

### Task 6: ปิดงานด้วยการตรวจครบแพ็กเกจ

**Files:**
- Modify: `docs/superpowers/programs/odoo19-enterprise/governance/wave-0-readiness-assessment.md`

- [ ] **Step 1: รัน test ทั้งไฟล์ของ validator**

Run:

```bash
python -m pytest tools/program_blueprint/tests/test_check_program_workspace.py -q
```

Expected:

```text
7 passed
```

- [ ] **Step 2: รัน validator ของ workspace จริง**

Run:

```bash
python tools/program_blueprint/check_program_workspace.py
```

Expected:

```text
Program workspace is complete.
```

- [ ] **Step 3: ตรวจ placeholder ใน artifact ใหม่**

Run:

```bash
python -c "from pathlib import Path; root = Path(r'c:\odoo-dev\odoo19\.worktrees\odoo19-enterprise-program'); files = [root / 'docs/superpowers/programs/odoo19-enterprise/foundation/repository-and-addon-baseline.md', root / 'docs/superpowers/programs/odoo19-enterprise/foundation/environment-and-delivery-baseline.md', root / 'docs/superpowers/programs/odoo19-enterprise/foundation/production-readiness-baseline.md', root / 'docs/superpowers/programs/odoo19-enterprise/reporting/kpi-reporting-baseline.md', root / 'docs/superpowers/programs/odoo19-enterprise/reporting/role-based-dashboard-blueprint.md', root / 'docs/superpowers/programs/odoo19-enterprise/governance/wave-0-readiness-assessment.md', root / 'docs/superpowers/programs/odoo19-enterprise/governance/wave-1-handoff-baseline.md']; bad = ['TODO', 'TBD', 'placeholder']; hits = [(str(path), token) for path in files for token in bad if token in path.read_text(encoding='utf-8')]; print(hits)"
```

Expected:

```text
[]
```

- [ ] **Step 4: อัปเดต readiness assessment จาก Draft เป็น Ready**

ปรับตารางสถานะใน `docs/superpowers/programs/odoo19-enterprise/governance/wave-0-readiness-assessment.md` ให้ได้ผลลัพธ์สุดท้ายแบบนี้:

```md
| Area | Status | Owner | Notes |
| --- | --- | --- | --- |
| Governance baseline | Ready | Program delivery lead | Baseline artifacts committed and linked |
| Technical platform baseline | Ready | Program engineering lead | Repository, environment, and production docs complete |
| Production readiness baseline | Ready | Architecture lead | Baseline ready for Wave 1 refinement |
| KPI/reporting baseline | Ready | Business sponsor | KPI and dashboard blueprint published |
| Wave 1 handoff | Ready | Program delivery lead | Handoff package available |
```

- [ ] **Step 5: Commit งานปิดแพ็กเกจ**

```bash
git add docs/superpowers/programs/odoo19-enterprise/governance/wave-0-readiness-assessment.md
git commit -m "docs(program): finalize Wave 0 readiness package"
```

## Self-Review Checklist

- Spec coverage:
  - Program foundation -> Task 2, Task 4, Task 5
  - Technical platform baseline -> Task 2
  - Production readiness baseline -> Task 2
  - KPI/reporting baseline -> Task 3
  - Dashboard blueprint -> Task 3
  - Exit criteria and handoff -> Task 4, Task 6
- Placeholder scan:
  - แผนนี้ไม่มี `TODO`, `TBD`, `implement later`, หรือคำสั่งกำกวมที่ไม่มีไฟล์และคำสั่งจริง
- Type consistency:
  - ใช้ชื่อไฟล์เดียวกันทั้งแผน ได้แก่ `repository-and-addon-baseline.md`, `environment-and-delivery-baseline.md`, `production-readiness-baseline.md`, `kpi-reporting-baseline.md`, `role-based-dashboard-blueprint.md`, `wave-0-readiness-assessment.md`, `wave-1-handoff-baseline.md`

