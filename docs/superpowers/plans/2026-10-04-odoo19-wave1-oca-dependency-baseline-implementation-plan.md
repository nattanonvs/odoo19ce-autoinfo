# Odoo 19 Wave 1 OCA Dependency Baseline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** เติม OCA repositories และ dependencies ที่ขาดสำหรับ Wave 1 baseline, formalize OCA repos ที่ branch ปัจจุบันใช้งานจริงให้เป็น submodule แบบสมบูรณ์, อัปเดต fit-gap ให้ตรงกับของจริง, และขยาย `od19_sales_oca_bridge_workflow` ให้ bridge กับ OCA modules ที่พร้อมใช้งานจริงโดยไม่แก้ Odoo core

**Architecture:** ใช้แนวทาง `OCA-first, custom-second` แบบ conservative โดย formalize OCA repos ที่ branch ใช้งานจริงอยู่แล้ว (`sale-workflow`, `server-backend`) ร่วมกับการเติม baseline ที่ยืนยัน source และ dependency chain ได้จริงในรอบนี้ (`server-ux`, `server-tools`, `sale-blanket`) ให้เป็น submodule ที่มี `.gitmodules` และ branch mapping ชัดเจนก่อน แล้วค่อยเชื่อมผ่าน `od19_sales_oca_bridge_workflow` แบบ TDD เป็นชั้น optional integration แยกจาก sales core เดิม เพื่อไม่ให้ core addons ถูกบังคับด้วย dependency ที่ยังไม่พร้อม เช่น `sale_invoice_plan` และ `sale_tier_validation`

**Tech Stack:** Git worktree, Odoo 19 CE, Python, XML, Markdown, OCA `server-backend`, `server-ux`, `server-tools`, `sale-workflow`, `sale-blanket`, PostgreSQL, Odoo test framework

## Discovery Evidence

- Approved OCA dependency baseline spec: `docs/superpowers/specs/2026-10-04-odoo19-wave1-oca-dependency-baseline-design.md`
- Odoo 15 production reference source code: `C:\odoo-dev\odoo19\Odoo15Backup\odoo`
- Odoo 15 reference mapping file: `C:\odoo-dev\odoo19\Odoo15Backup\odoo15_oca_mapping.xlsx`
- Current OCA workspace target: `third_party/oca/`
- Existing Wave 1 bridge addon context: `custom_addons/od19_sales_oca_bridge_workflow/`

---

## File Structure

**Create**
- `third_party/oca/server-ux/`
- `third_party/oca/server-tools/`
- `third_party/oca/sale-blanket/`
- `.gitmodules`

**Modify**
- `docs/superpowers/programs/odoo19-enterprise/sales/oca-fit-gap.md`
- `custom_addons/od19_sales_oca_bridge_workflow/__manifest__.py`
- `custom_addons/od19_sales_oca_bridge_workflow/models/sale_order_bridge.py`
- `custom_addons/od19_sales_oca_bridge_workflow/views/sale_order_bridge_views.xml`
- `custom_addons/od19_sales_oca_bridge_workflow/tests/test_oca_bridge.py`

**Reuse Without Code Changes**
- `docs/superpowers/specs/2026-10-04-odoo19-wave1-oca-dependency-baseline-design.md`
- `custom_addons/od19_sales_oca_bridge_workflow/tests/__init__.py`
- `custom_addons/od19_sales_oca_bridge_workflow/models/__init__.py`

## Scope Note

แผนนี้ไม่พอร์ตโมดูลจาก `18.0` มา `19.0` เอง และไม่เปิดใช้ `sale_invoice_plan` หรือ `sale_tier_validation` ใน baseline รอบนี้ หากตรวจพบว่าของจริงยังไม่พร้อม แผนจะล็อกสถานะเป็น `deferred` ตามสเปกที่อนุมัติแล้ว

## Precondition

- ใช้งานใน worktree `c:\odoo-dev\odoo19\.worktrees\wave1-sales-contract-core`
- ใช้ Python จาก `c:\odoo-dev\odoo19\venv19\Scripts\python.exe`
- ใช้ config `c:\odoo-dev\odoo19\odoo.conf`
- sync OCA submodules ก่อนเริ่มทุก task ด้วย `git submodule update --init --recursive`
- ต้องไม่แก้ Odoo core และไม่แก้ addon OCA ตรง ๆ ถ้ายังไม่จำเป็น

### Task 1: Formalize OCA repositories ที่ branch ใช้งานจริง

**Files:**
- Modify: `.gitmodules`
- Reuse/track: `third_party/oca/sale-workflow/`
- Reuse/track: `third_party/oca/server-backend/`
- Create: `third_party/oca/server-ux/`
- Create: `third_party/oca/server-tools/`
- Create: `third_party/oca/sale-blanket/`

- [ ] **Step 1: ตรวจรายการ OCA repos ที่ branch ใช้อยู่จริงและสภาพ submodule ปัจจุบัน**

Run:

```bash
git ls-tree HEAD third_party/oca/sale-workflow third_party/oca/server-backend third_party/oca/server-ux third_party/oca/server-tools third_party/oca/sale-blanket
git submodule status
```

Expected: ยืนยันได้ว่า branch ใช้ `sale-workflow`, `server-backend`, `server-ux`, `server-tools`, `sale-blanket` อยู่จริงใน `third_party/oca` และเห็นชัดว่าถ้ายังมี gap ใน `.gitmodules` หรือสถานะ submodule ต้อง formalize ให้ตรงกับ baseline นี้

- [ ] **Step 2: เพิ่ม OCA repos ที่ยังขาดเข้า baseline ด้วย submodule**

Run:

```bash
git submodule add -b 19.0 https://github.com/OCA/server-ux.git third_party/oca/server-ux
git submodule add -b 19.0 https://github.com/OCA/server-tools.git third_party/oca/server-tools
git submodule add -b 19.0 https://github.com/OCA/sale-blanket.git third_party/oca/sale-blanket
git submodule update --init --recursive
```

Expected: ทั้ง 3 repo ถูก register และ checkout เป็น submodule ภายใต้ `third_party/oca`

- [ ] **Step 3: formalize submodule mapping สำหรับ repos ที่ branch ใช้งานจริง**

เขียน `.gitmodules` ให้ครบสำหรับ:

```ini
[submodule "third_party/oca/sale-workflow"]
	path = third_party/oca/sale-workflow
	url = https://github.com/OCA/sale-workflow.git
	branch = 19.0
[submodule "third_party/oca/server-backend"]
	path = third_party/oca/server-backend
	url = https://github.com/OCA/server-backend.git
	branch = 19.0
[submodule "third_party/oca/server-ux"]
	path = third_party/oca/server-ux
	url = https://github.com/OCA/server-ux.git
	branch = 19.0
[submodule "third_party/oca/server-tools"]
	path = third_party/oca/server-tools
	url = https://github.com/OCA/server-tools.git
	branch = 19.0
[submodule "third_party/oca/sale-blanket"]
	path = third_party/oca/sale-blanket
	url = https://github.com/OCA/sale-blanket.git
	branch = 19.0
```

- [ ] **Step 4: ตรวจว่าโมดูลเป้าหมายและ submodule status ใช้งานได้จริง**

Run:

```bash
git submodule status
dir third_party\oca\server-ux\base_revision
dir third_party\oca\server-tools\base_exception
dir third_party\oca\sale-blanket\sale_blanket_order
```

Expected: `git submodule status` ใช้งานได้โดยเห็น mapping ครบทั้ง 5 repos และพบโฟลเดอร์ `base_revision`, `base_exception`, และ `sale_blanket_order`

- [ ] **Step 5: Commit**

```bash
git add .gitmodules third_party/oca
git commit -m "chore(sales): add OCA dependency repositories for Wave 1 baseline"
```

### Task 2: อัปเดต OCA fit-gap ให้ตรงกับ baseline จริง

**Files:**
- Modify: `docs/superpowers/programs/odoo19-enterprise/sales/oca-fit-gap.md`

- [ ] **Step 1: เขียน test เชิงเอกสารด้วยการกำหนดผลลัพธ์ที่ต้องเห็น**

เกณฑ์ที่เอกสารต้องสะท้อน:

```text
- sale_delivery_state แทน sale_delivery_status
- sale_blanket_order มาจาก OCA/sale-blanket
- sale_order_revision ต้องมี base_revision
- sale_exception family ต้องมี base_exception
- sale_invoice_plan และ sale_tier_validation เป็น deferred
```

- [ ] **Step 2: ตรวจเอกสารปัจจุบันเพื่อยืนยันว่า fail ตามที่คาด**

Run:

```bash
git diff -- docs/superpowers/programs/odoo19-enterprise/sales/oca-fit-gap.md
```

Expected: ยังไม่มีการแก้ให้ตรง baseline ใหม่

- [ ] **Step 3: แก้เอกสาร fit-gap แบบขั้นต่ำ**

อัปเดตตารางและ bullet ให้มีสาระตามนี้:

```md
| `sale_delivery_state` | OCA/sale-workflow | Adopt | ใช้สถานะส่งมอบระหว่างทางก่อนถึง billing readiness |
| `sale_order_revision` | OCA/sale-workflow + OCA/server-ux | Adopt | ใช้ revision history ของ quotation / order โดยต้องมี `base_revision` |
| `sale_exception` | OCA/sale-workflow + OCA/server-tools | Adopt via bridge | ใช้ exception / approval rule โดยต้องมี `base_exception` |
| `sale_blanket_order` | OCA/sale-blanket | Adopt via bridge | ใช้เป็นฐานเอกสารเชิงพาณิชย์ของ contract-based sale |
| `sale_invoice_plan` | OCA/sale-workflow | Deferred | รอ confirm 19.0 baseline |
| `sale_tier_validation` | OCA/sale-workflow + OCA/server-ux | Deferred | รอ confirm 19.0 baseline และ `base_tier_validation` |
```

- [ ] **Step 4: ตรวจว่าเอกสารแก้ครบตาม design**

Run:

```bash
git diff -- docs/superpowers/programs/odoo19-enterprise/sales/oca-fit-gap.md
```

Expected: diff สะท้อน baseline ใหม่ครบทั้ง 5 จุด

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/programs/odoo19-enterprise/sales/oca-fit-gap.md
git commit -m "docs(sales): align OCA fit-gap with approved baseline"
```

### Task 3: ขยาย bridge addon ด้วย TDD สำหรับ revision, exception, blanket

**Files:**
- Modify: `custom_addons/od19_sales_oca_bridge_workflow/__manifest__.py`
- Modify: `custom_addons/od19_sales_oca_bridge_workflow/models/sale_order_bridge.py`
- Modify: `custom_addons/od19_sales_oca_bridge_workflow/views/sale_order_bridge_views.xml`
- Modify: `custom_addons/od19_sales_oca_bridge_workflow/tests/test_oca_bridge.py`

- [ ] **Step 1: เขียน failing tests สำหรับ bridge fields ใหม่**

เพิ่ม test ให้เช็ก field อย่างน้อย 3 ตัว:

```python
def test_sale_order_has_revision_bridge_fields(self):
    order = self.env["sale.order"]
    self.assertIn("od19_enable_revision", order._fields)

def test_sale_order_has_exception_bridge_fields(self):
    order = self.env["sale.order"]
    self.assertIn("od19_use_exception_rules", order._fields)

def test_sale_order_has_blanket_bridge_fields(self):
    order = self.env["sale.order"]
    self.assertIn("od19_use_blanket_order", order._fields)
```

- [ ] **Step 2: รัน test ให้ยืนยันว่า fail เพราะ field ยังไม่มี**

Run:

```bash
c:\odoo-dev\odoo19\venv19\Scripts\python.exe odoo-bin -c c:\odoo-dev\odoo19\odoo.conf -d test_w1_oca_bridge_red --test-enable -i sale,mail,base_user_role,sale_delivery_state,base_revision,sale_order_revision,base_exception,sale_exception,sale_blanket_order,od19_sales_project_context,od19_sales_contract_core,od19_sales_billing_evidence,od19_sales_reporting,od19_sales_oca_bridge_workflow --stop-after-init --addons-path="c:/odoo-dev/odoo19/.worktrees/wave1-sales-contract-core/addons,c:/odoo-dev/odoo19/.worktrees/wave1-sales-contract-core/odoo/addons,c:/odoo-dev/odoo19/.worktrees/wave1-sales-contract-core/custom_addons,c:/odoo-dev/odoo19/.worktrees/wave1-sales-contract-core/third_party/oca/server-backend,c:/odoo-dev/odoo19/.worktrees/wave1-sales-contract-core/third_party/oca/server-ux,c:/odoo-dev/odoo19/.worktrees/wave1-sales-contract-core/third_party/oca/server-tools,c:/odoo-dev/odoo19/.worktrees/wave1-sales-contract-core/third_party/oca/sale-workflow,c:/odoo-dev/odoo19/.worktrees/wave1-sales-contract-core/third_party/oca/sale-blanket" --test-tags od19_sales_oca_bridge_workflow
```

Expected: FAIL เพราะ field bridge ใหม่ยังไม่อยู่บน `sale.order`

- [ ] **Step 3: เขียน implementation แบบขั้นต่ำ**

เพิ่ม fields ใน `sale_order_bridge.py` อย่างน้อยตามนี้:

```python
od19_enable_revision = fields.Boolean(default=False)
od19_use_exception_rules = fields.Boolean(default=False)
od19_use_blanket_order = fields.Boolean(default=False)
```

เพิ่ม dependency ใน manifest:

```python
"base_revision",
"sale_order_revision",
"base_exception",
"sale_exception",
"sale_blanket_order",
```

เพิ่ม field ลง view หลังกลุ่ม field เดิม:

```xml
<field name="od19_enable_revision"/>
<field name="od19_use_exception_rules"/>
<field name="od19_use_blanket_order"/>
```

- [ ] **Step 4: รัน test ให้ยืนยันว่า pass**

Run:

```bash
c:\odoo-dev\odoo19\venv19\Scripts\python.exe odoo-bin -c c:\odoo-dev\odoo19\odoo.conf -d test_w1_oca_bridge_green --test-enable -i sale,mail,base_user_role,sale_delivery_state,base_revision,sale_order_revision,base_exception,sale_exception,sale_blanket_order,od19_sales_project_context,od19_sales_contract_core,od19_sales_billing_evidence,od19_sales_reporting,od19_sales_oca_bridge_workflow --stop-after-init --addons-path="c:/odoo-dev/odoo19/.worktrees/wave1-sales-contract-core/addons,c:/odoo-dev/odoo19/.worktrees/wave1-sales-contract-core/odoo/addons,c:/odoo-dev/odoo19/.worktrees/wave1-sales-contract-core/custom_addons,c:/odoo-dev/odoo19/.worktrees/wave1-sales-contract-core/third_party/oca/server-backend,c:/odoo-dev/odoo19/.worktrees/wave1-sales-contract-core/third_party/oca/server-ux,c:/odoo-dev/odoo19/.worktrees/wave1-sales-contract-core/third_party/oca/server-tools,c:/odoo-dev/odoo19/.worktrees/wave1-sales-contract-core/third_party/oca/sale-workflow,c:/odoo-dev/odoo19/.worktrees/wave1-sales-contract-core/third_party/oca/sale-blanket" --test-tags od19_sales_oca_bridge_workflow
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add custom_addons/od19_sales_oca_bridge_workflow
git commit -m "feat(sales): extend OCA bridge with revision exception and blanket support"
```

### Task 4: ปิดงานด้วย targeted matrix และ clean diff

**Files:**
- Modify: `custom_addons/od19_sales_oca_bridge_workflow/__manifest__.py`
- Modify: `custom_addons/od19_sales_oca_bridge_workflow/models/sale_order_bridge.py`
- Modify: `custom_addons/od19_sales_oca_bridge_workflow/views/sale_order_bridge_views.xml`
- Modify: `custom_addons/od19_sales_oca_bridge_workflow/tests/test_oca_bridge.py`
- Modify: `docs/superpowers/programs/odoo19-enterprise/sales/oca-fit-gap.md`

- [ ] **Step 1: รัน targeted matrix ของ sales core**

Run:

```bash
c:\odoo-dev\odoo19\venv19\Scripts\python.exe odoo-bin -c c:\odoo-dev\odoo19\odoo.conf -d test_w1_sales_core_after_oca --test-enable -i sale,mail,od19_sales_project_context,od19_sales_contract_core,od19_sales_billing_evidence,od19_sales_reporting --stop-after-init --addons-path="c:/odoo-dev/odoo19/.worktrees/wave1-sales-contract-core/addons,c:/odoo-dev/odoo19/.worktrees/wave1-sales-contract-core/odoo/addons,c:/odoo-dev/odoo19/.worktrees/wave1-sales-contract-core/custom_addons,c:/odoo-dev/odoo19/.worktrees/wave1-sales-contract-core/third_party/oca/server-backend,c:/odoo-dev/odoo19/.worktrees/wave1-sales-contract-core/third_party/oca/server-ux,c:/odoo-dev/odoo19/.worktrees/wave1-sales-contract-core/third_party/oca/server-tools,c:/odoo-dev/odoo19/.worktrees/wave1-sales-contract-core/third_party/oca/sale-workflow,c:/odoo-dev/odoo19/.worktrees/wave1-sales-contract-core/third_party/oca/sale-blanket" --test-tags od19_sales_project_context,od19_sales_contract_core,od19_sales_billing_evidence,od19_sales_reporting
```

Expected: PASS

- [ ] **Step 2: รัน targeted matrix ของ bridge stack**

Run:

```bash
c:\odoo-dev\odoo19\venv19\Scripts\python.exe odoo-bin -c c:\odoo-dev\odoo19\odoo.conf -d test_w1_sales_bridge_after_oca --test-enable -i sale,mail,base_user_role,sale_delivery_state,base_revision,sale_order_revision,base_exception,sale_exception,sale_blanket_order,od19_sales_project_context,od19_sales_contract_core,od19_sales_billing_evidence,od19_sales_reporting,od19_sales_oca_bridge_workflow --stop-after-init --addons-path="c:/odoo-dev/odoo19/.worktrees/wave1-sales-contract-core/addons,c:/odoo-dev/odoo19/.worktrees/wave1-sales-contract-core/odoo/addons,c:/odoo-dev/odoo19/.worktrees/wave1-sales-contract-core/custom_addons,c:/odoo-dev/odoo19/.worktrees/wave1-sales-contract-core/third_party/oca/server-backend,c:/odoo-dev/odoo19/.worktrees/wave1-sales-contract-core/third_party/oca/server-ux,c:/odoo-dev/odoo19/.worktrees/wave1-sales-contract-core/third_party/oca/server-tools,c:/odoo-dev/odoo19/.worktrees/wave1-sales-contract-core/third_party/oca/sale-workflow,c:/odoo-dev/odoo19/.worktrees/wave1-sales-contract-core/third_party/oca/sale-blanket" --test-tags od19_sales_oca_bridge_workflow
```

Expected: PASS

- [ ] **Step 3: ตรวจ clean diff**

Run:

```bash
git diff --check
git status --short
```

Expected: ไม่มี whitespace error และเหลือเฉพาะไฟล์ที่ตั้งใจแก้

- [ ] **Step 4: Commit verification state**

```bash
git add docs/superpowers/programs/odoo19-enterprise/sales/oca-fit-gap.md custom_addons/od19_sales_oca_bridge_workflow
git commit -m "test(sales): verify Wave 1 OCA dependency baseline"
```

## Self-Review

- ครอบคลุมสเปก baseline ที่อนุมัติแล้วครบทั้ง repo, fit-gap, bridge, และ targeted matrix
- ไม่มี placeholder แบบ `TBD` หรือ `TODO`
- ชื่อโมดูลสอดคล้องกันทั้งแผน: `sale_delivery_state`, `base_revision`, `base_exception`, `sale_blanket_order`
