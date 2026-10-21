# Odoo 19 CE Wave 1: Project & Analytic Accounting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status:** Approved — อนุมัติโดยเจ้าของธุรกิจ 2026-10-20 (DD-1 = ทาง (ก)) และสั่งแก้ scope: Job Type = `Sale, Service, PM, Job` (ถอด `server` ออก)

**Goal:** ปิดช่องว่าง Project & Analytic Accounting ของ Wave 1 ให้ครบ 5 เรื่อง โดยไม่แก้ Odoo core:
0. ถอด Job Type `server` ออกให้ชุดประเภทตรงกับ legacy คือ `job`, `pm`, `service`, `sale` (คำสั่งเจ้าของธุรกิจ 2026-10-20)
1. เพิ่ม Job Type `sale` กลับตาม legacy (D1) และให้ Job Number ของประเภทนี้ใช้ sequence ของ salesperson
2. แก้เกณฑ์ Risk Level ให้เป็นชุดเดียวกับ legacy คือ `high ≥ 70`, `medium ≥ 40` (D2)
3. ทำ **Project P&L** ให้อ่านจาก `account.analytic.line` + `analytic_profitability` ของ Odoo 19 (D5/D6) และให้ Risk Report ใช้ตัวเลขชุดเดียวกัน
4. ให้ P&L แสดง 0 พร้อมคำเตือนเมื่อโครงการไม่มี Analytic Account (D7) พร้อม KPI คุณภาพข้อมูล

**Architecture:** เสริม standard `project.project` ต่อ ไม่สร้างโมเดลโครงการใหม่ และไม่สร้างโมดูล `od19_project_pnl` (D5) งานทั้งหมดอยู่ใน 2 โมดูลที่มีอยู่แล้ว:
- `od19_project_document_sequence` — Job Type `sale`, sequence ของ salesperson, Job Number algorithm
- `od19_project_enhanced` — P&L จาก analytic line, Risk Report (SQL view), P&L report wizard ตามช่วงวันที่, KPI menu actions

P&L มี **เจ้าของสูตรเดียวคือ `account.analytic.line`** โดยใช้ `analytic_profitability` ที่ core compute ให้ (Revenue/Cost/Uncategorized) — ห้ามประดิษฐ์เกณฑ์แยกรายได้/ต้นทุนเอง (D6)

**Tech Stack:** Odoo 19 CE, Python, XML, PostgreSQL, Odoo test framework, Git, Markdown

---

## Discovery Evidence

- Approved spec: `docs/superpowers/specs/2026-10-20-odoo19-enterprise-wave-1-project-analytic-accounting-design.md` (Child spec ID `W1-PROJECT-ANALYTIC`)
- Index row: `docs/superpowers/programs/odoo19-enterprise/backlog/domain-spec-index.md` (แถว W1-PROJECT-ANALYTIC)
- Legacy references (Odoo 15):
  - `Odoo15Backup/odoo/custom15_autoinfo/autoinfo_project/models/project_project.py` — `job_type == 'sale'` ใช้ `sale_person_id.jobno_sequence_id.next_by_id()`; ถ้าไม่มี sequence → `ValidationError('Please set sequence running for auto generate job number.')`
  - `Odoo15Backup/odoo/custom15_autoinfo/autoinfo_project/models/res_users.py` — `jobno_sequence_id = fields.Many2one('ir.sequence', check_company=True)` บน `res.users`
  - `Odoo15Backup/odoo/custom15_autoinfo/autoinfo_project_risk_report/models/project_risk_report.py` — `_order = "risk_score desc, margin_pct asc, project_name"`, เกณฑ์ risk `high ≥ 70 / medium ≥ 40`

### ยืนยันสัญญาของ Odoo 19 core (ตรวจโค้ดจริง 2026-10-20)

| ข้อเท็จจริง | หลักฐาน | ผลต่อการออกแบบ |
| --- | --- | --- |
| `analytic_profitability` เป็น Selection **non-stored** (`compute` + `search`), `_search_analytic_profitability` รองรับเฉพาะ operator `in` | [account_analytic_line.py](file:///c:/odoo-dev/odoo19/addons/account/models/account_analytic_line.py#L50-L59) L50-L59, L158-L169 | ใช้ใน domain ได้เฉพาะ `('analytic_profitability', 'in', [...])`; **ใช้ group-by ไม่ได้**; ใน SQL ต้อง replicate CASE |
| สูตร CASE มาตรฐานของ profitability (core เขียนไว้ให้ mirror ตรง ๆ) | [account_analytic_line.py](file:///c:/odoo-dev/odoo19/addons/account/models/account_analytic_line.py#L131-L156) L131-L156 (`_field_to_sql`) | คัดลอก CASE นี้ลง SQL view ให้ตรงกับ `_compute_analytic_profitability` |
| `general_account_id` เป็น **stored** M2o `account.account` | [account_analytic_line.py](file:///c:/odoo-dev/odoo19/addons/account/models/account_analytic_line.py#L19-L26) L19-L26 | JOIN `account_account aa ON aa.id = al.general_account_id` ได้ตรง ๆ |
| `account.analytic.line` มี `account_id` (analytic account), `date`, `company_id` | [analytic_line.py](file:///c:/odoo-dev/odoo19/addons/analytic/models/analytic_line.py#L16-L22) L16-L22, L174-L178, L204-L208 | ผูก P&L กับโครงการผ่าน `account_id = project.account_id`; กรองช่วงวันที่และบริษัทได้ |
| `account.move.line.parent_state` เป็น related **stored** | [account_move_line.py](file:///c:/odoo-dev/odoo19/addons/account/models/account_move_line.py#L69) L69 | กรอง posted ได้ทั้งใน domain และ SQL |
| เครื่องหมาย `amount` ของ analytic line | spec §6.6 (ยืนยันแล้ว) | `amount = -balance × distribution/100` ⇒ Revenue = `SUM(amount)`, Cost = `-SUM(amount)` |

### สถานะโค้ดปัจจุบัน (baseline ที่แก้ค้างอยู่ ยังไม่ commit)

| ไฟล์ | สิ่งที่ต้องแตะ |
| --- | --- |
| [project_project.py](file:///c:/odoo-dev/odoo19/custom_addons/od19_project_document_sequence/models/project_project.py) (`od19_project_document_sequence`) | L7-L12 `PROJECT_TYPE_SEQUENCE_MAP` (ถอด `server`), L33-L46 `od19_project_type` (ถอด `server`, เพิ่ม `sale`), L64-L72 `_get_project_sequence`, L96-L123 `create`, L125-L138 `write` |
| [hr_department.py](file:///c:/odoo-dev/odoo19/custom_addons/od19_project_document_sequence/models/hr_department.py) / [hr_department_views.xml](file:///c:/odoo-dev/odoo19/custom_addons/od19_project_document_sequence/views/hr_department_views.xml) / [ir_sequence_data.xml](file:///c:/odoo-dev/odoo19/custom_addons/od19_project_document_sequence/data/ir_sequence_data.xml) | ถอด `project_server_sequence_id` และ `project.server.*` 4 sequences |
| [res_users.py](file:///c:/odoo-dev/odoo19/custom_addons/od19_project_document_sequence/models/res_users.py) (`od19_project_document_sequence`) | เพิ่ม `project_sale_sequence_id` |
| [project_risk_report.py](file:///c:/odoo-dev/odoo19/custom_addons/od19_project_enhanced/models/project_risk_report.py) (`od19_project_enhanced`) | L41-L49 `_compute_margin_percent`, L65-L73 `_compute_risk_level`, L75-L184 `init()` SQL |
| [project_project.py](file:///c:/odoo-dev/odoo19/custom_addons/od19_project_analytic/models/project_project.py) (`od19_project_analytic`) | เจ้าของ `job_no`, `od19_department_id`, `account_id` auto-create — **ไม่ต้องแก้** |

จุดที่ hardcode เกณฑ์ risk: มีเพียง 2 บรรทัด ที่ [project_risk_report.py](file:///c:/odoo-dev/odoo19/custom_addons/od19_project_enhanced/models/project_risk_report.py#L68-L71) L68, L70 (grep แล้วทั้ง `custom_addons/` ไม่มีที่อื่น; `od19_iso_risk` เป็นโดเมน ISO คนละเรื่อง)

### ข้อเท็จจริงสภาพแวดล้อมที่ต้องถือ

- มี Odoo dev server รันอยู่ที่พอร์ต **8070** จาก workspace นี้ ⇒ **ห้าม `git checkout`/`git switch` ที่เปลี่ยนไฟล์ใน working tree**
- คำสั่งเทสต์มาตรฐาน (ต้องส่ง `--logfile` เอง เพราะ `odoo.conf` เขียนทับ) และใช้ `--http-port=8171` เลี่ยงการชนพอร์ต:
  ```powershell
  venv19\Scripts\python.exe odoo-bin -c odoo.conf -d odoo19 --http-port=8171 -u <module> --test-enable --test-tags /<module> --stop-after-init --log-level=test --logfile="$env:TEMP\<name>.log"
  ```
- `security/ir.model.access.csv` และ `data/*.xml` ถูก `.gitignore` บล็อก ⇒ ต้อง `git add -f` เมื่อ commit
- PowerShell profile ขึ้น `SecurityError` เป็น noise ทุกคำสั่ง — ตัดสินจาก exit code
- `odoo19` เป็น DB เทสต์ที่ตั้งไว้ (เทสต์ไม่ต้องรันบน `odoo19_pdev`)

---

## Design Decisions (ต้องการการยืนยันตอนอนุมัติ plan)

D1–D7 ถูกตัดสินแล้วในตัว spec. รายการต่อไปนี้คือรายละเอียดเชิง implement ที่ยังต้องยืนยัน **ครั้งเดียวตอนอนุมัติ plan**

1. **DD-1 — ฐานของ Margin % ที่ใช้คิด risk score (สำคัญสุด)**
   เพื่อทำตาม §5.2/§6.6 (Risk Report ต้องใช้ตัวเลขชุดเดียวกับ P&L) `margin_percent` จะเปลี่ยนจากสูตรเดิม `(contract_amount - actual_cost) / contract_amount` เป็นสูตร P&L: `(Revenue − Cost) ÷ Revenue × 100`
   - **ทางที่เสนอ (ก):** ถ้า `Revenue = 0` (โครงการยังไม่รับรู้รายได้) ให้ `margin_percent = 0` และ **ไม่คิดคะแนนความเสี่ยงจากเงื่อนไข margin** (กันโครงการระหว่างดำเนินการถูกตีเป็นความเสี่ยงสูงโดยไม่เป็นธรรม) แต่ยังแสดงค่า 0 และเตือน "ยังไม่มีรายได้"
   - ทางที่เสนอ (ข): ใช้สูตรตรงตัว — `Revenue = 0` ⇒ `margin_percent = 0` ⇒ ติดเงื่อนไข `margin < 15` ⇒ +40 คะแนน
   - ทางที่เสนอ (ค): คงสูตร contract-based เดิมไว้เป็น **`contract_margin_percent`** เพิ่มอีกคอลัมน์ และให้ risk ใช้ contract-based (ขัดกับ §5.2 เล็กน้อย แต่ต่อเนื่องจาก legacy ที่สุด)
   - **แนะนำ (ก)** — เป็นการตีความ §6.6 + §6.7 ที่ตรงที่สุดโดยไม่ทำให้ WIP กลายเป็นความเสี่ยงสูง

2. **DD-2 — P&L report ตามช่วงวันที่ (spec §7.1 + §11)**
   `od19.project.risk.report` เป็น SQL view (`_auto = False`) แบบยอดสะสมทั้งหมด จึงกรองช่วงวันที่ระดับ view ไม่ได้ ⇒ เพิ่ม **transient wizard** ชื่อ `od19.project.pnl.report` + line model `od19.project.pnl.report.line` **ภายใน `od19_project_enhanced`** (ไม่สร้างโมดูลใหม่ ตาม D5) โดยเรียกสูตร P&L ชุดเดียวกับ SQL view
   - ผลที่ต้องยอมรับ: สูตร P&L มี 2 implementation (SQL view = all-time, Python = ตามช่วงวันที่) ⇒ **บังคับมี consistency test** เปรียบเทียบสองทางในช่วงวันที่ครอบทั้งหมด (spec §11 ข้อ 4)

3. **DD-3 — sequence ของ Job Type `sale` อยู่บน `res.users`**
   เพิ่ม `res.users.project_sale_sequence_id` (`check_company=True`) แทนการเพิ่ม sequence บน `hr.department` (legacy เก็บบน `res.users` เป็น `jobno_sequence_id`) เพราะประเภท `sale` ไม่ผูกกับแผนก

4. **DD-4 — นโยบายไม่ fallback เงียบของ Job Type `sale` (D1)**
   ถ้าสร้างโครงการประเภท `sale` โดยไม่ส่ง `job_no` มา และ salesperson ไม่ได้ตั้ง sequence ⇒ raise `ValidationError` ทันที (ไม่สร้าง job_no ว่าง)
   ข้อยกเว้น: ถ้าผู้เรียกส่ง `job_no` มาเอง (import/migration) ⇒ ไม่ raise; และประเภทอื่น (`job/pm/service`) **คงพฤติกรรมเดิม** คือ job_no ว่างได้ถ้าไม่มีแผนก/ไม่มี sequence (spec §6.3)

5. **DD-5 — ถอด Job Type `server` ออกทั้งโดเมน (คำสั่งเจ้าของธุรกิจ 2026-10-20)**
   ชุด Job Type ต้องตรงกับ legacy: `job`, `pm`, `service`, `sale` เท่านั้น ⇒ ถอด `server`, `hr.department.project_server_sequence_id`, `project.server.*` sequences และค่า `server` ใน `job_type_values` ของ `od19_accounting_money_in_report`
   - ตรวจ DB `odoo19_pdev` แล้ว (2026-10-20): `project_project` ว่าง (ไม่มีแถวใช้ type ใด), `hr_department.project_server_sequence_id` เป็น NULL ทุกแถว, มีเพียง 4 ir.sequence `project.server.*` ที่ module สร้างเอง ⇒ ถอดได้ไม่เสียข้อมูล

---

## File Structure

**Modify**
- `custom_addons/od19_project_document_sequence/data/ir_sequence_data.xml` — ถอด `project.server.*` 4 sequences
- `custom_addons/od19_project_document_sequence/models/hr_department.py` — ถอด `project_server_sequence_id`
- `custom_addons/od19_project_document_sequence/views/hr_department_views.xml` — ถอดฟิลด์
- `custom_addons/od19_accounting_money_in_report/wizard/money_in_report_wizard.py` — ถอด `server` จาก `job_type_values`
- `custom_addons/od19_accounting_money_in_report/models/money_in_report_run.py` — ถอด `server` จาก `job_type_values`
- `custom_addons/od19_project_document_sequence/models/res_users.py` — เพิ่ม `project_sale_sequence_id`
- `custom_addons/od19_project_document_sequence/models/project_project.py` — Job Type `sale`, sequence ของ salesperson, create/write
- `custom_addons/od19_project_document_sequence/views/res_users_views.xml` — เพิ่มฟิลด์ในหน้า Project Sequence
- `custom_addons/od19_project_document_sequence/tests/test_project_document_sequence.py` — เทสต์ Job Type `sale`
- `custom_addons/od19_project_enhanced/models/project_risk_report.py` — P&L columns + threshold 70/40 + margin basis ใหม่
- `custom_addons/od19_project_enhanced/models/project_project.py` — เพิ่ม `_od19_get_pnl_values()`
- `custom_addons/od19_project_enhanced/views/project_risk_report_views.xml` — เพิ่มคอลัมน์ P&L/เตือน
- `custom_addons/od19_project_enhanced/security/ir.model.access.csv` — access ของ transient wizard
- `custom_addons/od19_project_enhanced/__manifest__.py` — เพิ่มไฟล์ view ใหม่
- `docs/superpowers/programs/odoo19-enterprise/backlog/domain-spec-index.md` — อัปเดต gate readiness
- `docs/superpowers/programs/odoo19-enterprise/backlog/domain-wave-matrix.md` — อัปเดตสถานะ row (ถ้ามี)

**Create**
- `custom_addons/od19_project_enhanced/models/project_pnl_report.py`
- `custom_addons/od19_project_enhanced/views/project_pnl_report_views.xml`
- `custom_addons/od19_project_enhanced/tests/__init__.py`
- `custom_addons/od19_project_enhanced/tests/test_project_risk_report.py`
- `custom_addons/od19_project_enhanced/tests/test_project_pnl.py`
- `custom_addons/od19_project_enhanced/tests/test_project_pnl_wizard.py`

**Reuse Without Code Changes**
- `addons/analytic/`, `addons/account/`, `addons/project/`, `addons/sale_project/`, `addons/hr_expense/`, `addons/purchase/`
- `custom_addons/od19_project_analytic/` (เจ้าของ `job_no`, `od19_department_id`, `account_id`)
- `custom_addons/od19_sales_project_context/`, `custom_addons/od19_accounting_money_in_report/` — regression test เท่านั้น

---

## Precondition

งานนี้ทำ **in-place** บน workspace หลัก `c:\odoo-dev\odoo19` (**ไม่ใช้ git worktree**) เพราะ baseline ของโมดูล project 10 ไฟล์ยังไม่ถูก commit และ worktree ใหม่จะไม่ได้รับไฟล์เหล่านั้น

1. ตรวจสถานะก่อนเริ่ม และ commit baseline ของงานที่เสร็จแล้วในโดเมน project ก่อน เพื่อให้ diff ของงานใหม่ตรวจได้:
   ```powershell
   git status --short
   git add custom_addons/od19_project_analytic custom_addons/od19_project_document_sequence custom_addons/od19_project_enhanced custom_addons/od19_sales_project_context custom_addons/od19_accounting_payment_fee
   git commit -m "chore(project): baseline project-domain refactor and payment fee force_balance fix"
   ```
2. สร้าง feature branch **โดยไม่เปลี่ยนไฟล์ใน working tree** (ปลอดภัยกับ dev server ที่พอร์ต 8070):
   ```powershell
   git switch -c feature/wave1-project-analytic-accounting
   ```
3. ห้าม `git checkout`/`git stash` ระหว่าง dev server รันอยู่

**ทดสอบ (ใช้ทุกระดับของงานนี้):**
```powershell
venv19\Scripts\python.exe odoo-bin -c odoo.conf -d odoo19 --http-port=8171 -u od19_project_document_sequence,od19_project_enhanced --test-enable --test-tags /od19_project_document_sequence,/od19_project_enhanced --stop-after-init --log-level=test --logfile="$env:TEMP\od19_w1_project.log"
```
แล้วอ่านผลจาก `$env:TEMP\od19_w1_project.log` (ห้ามพึ่ง stdout เพียงอย่างเดียว) — ต้องได้ `0 failed, 0 error(s)`

---

### Task 0: DD-5 — ถอด Job Type `server` ออกทั้งโดเมน

**Files:**
- Modify: `custom_addons/od19_project_document_sequence/models/project_project.py`
- Modify: `custom_addons/od19_project_document_sequence/models/hr_department.py`
- Modify: `custom_addons/od19_project_document_sequence/views/hr_department_views.xml`
- Modify: `custom_addons/od19_project_document_sequence/data/ir_sequence_data.xml`
- Modify: `custom_addons/od19_project_document_sequence/tests/test_project_document_sequence.py`
- Modify: `custom_addons/od19_accounting_money_in_report/wizard/money_in_report_wizard.py`
- Modify: `custom_addons/od19_accounting_money_in_report/models/money_in_report_run.py`

- [ ] **Step 1: ยืนยันว่าไม่มีข้อมูลจริงใช้ `server`** (ทำแล้ว 2026-10-20: `project_project` ว่าง, `hr_department.project_server_sequence_id` NULL ทั้งหมด)
- [ ] **Step 2: ถอด `server` จาก `PROJECT_TYPE_SEQUENCE_MAP` และ `od19_project_type`**
- [ ] **Step 3: ถอด `project_server_sequence_id` จาก `hr_department.py` และ view**
- [ ] **Step 4: ถอด 4 records `seq_project_server_*` (`project.server.ba/ta/ia/fdes`) จาก `ir_sequence_data.xml`**
- [ ] **Step 5: ถอด assert `project_server_sequence_id` ในเทสต์เดิม**
- [ ] **Step 6: ถอด `("server", "Server")` จาก `job_type_values` ทั้ง 2 ที่ แล้วรันเทสต์ `od19_accounting_money_in_report`**
- [ ] **Step 7: รันเทสต์ `od19_project_document_sequence` ให้เขียว**

---

### Task 1: D1 — Job Type `sale` และ sequence ของ salesperson

**Files:**
- Modify: `custom_addons/od19_project_document_sequence/models/res_users.py`
- Modify: `custom_addons/od19_project_document_sequence/models/project_project.py`
- Modify: `custom_addons/od19_project_document_sequence/views/res_users_views.xml`
- Test: `custom_addons/od19_project_document_sequence/tests/test_project_document_sequence.py`

- [ ] **Step 1: เขียนเทสต์ที่จะล้มเหลวก่อน**

เพิ่มใน `tests/test_project_document_sequence.py`:

```python
from odoo.exceptions import ValidationError


    def _sale_sequence(self, prefix="S%(y)s-"):
        return self.env["ir.sequence"].create({
            "name": "OD19 Sale Job No",
            "code": "od19.sale.job",
            "prefix": prefix,
            "padding": 4,
            "company_id": self.env.company.id,
        })

    def _sale_user(self, login, initials, sequence=None):
        return self.env["res.users"].create({
            "name": login,
            "login": login,
            "od19_initials": initials,
            "project_sale_sequence_id": sequence.id if sequence else False,
        })

    def test_sale_type_declared_in_selection(self):
        self.assertIn("sale", dict(
            self.env["project.project"]._fields["od19_project_type"].selection
        ))

    def test_sale_project_uses_salesperson_sequence_with_initials(self):
        user = self._sale_user("od19_sale_rep", "NV", self._sale_sequence())
        project = self.env["project.project"].create({
            "name": "Sale Direct Project",
            "od19_project_type": "sale",
            "od19_sale_person_id": user.id,
        })
        # sale job number = S + initials + YY + running number -> SNV26-0001
        self.assertTrue(project.job_no.startswith("SNV"))

    def test_sale_project_without_sequence_raises(self):
        user = self._sale_user("od19_sale_rep_noseq", "NS")
        with self.assertRaises(ValidationError):
            self.env["project.project"].create({
                "name": "Sale Project No Seq",
                "od19_project_type": "sale",
                "od19_sale_person_id": user.id,
            })

    def test_sale_project_with_explicit_job_no_does_not_raise(self):
        user = self._sale_user("od19_sale_rep_import", "IM")
        project = self.env["project.project"].create({
            "name": "Imported Sale Project",
            "od19_project_type": "sale",
            "od19_sale_person_id": user.id,
            "job_no": "SIM26-9999",
        })
        self.assertEqual(project.job_no, "SIM26-9999")

    def test_job_type_other_than_sale_does_not_require_sequence(self):
        # ไม่มีแผนกและไม่มี sequence -> job_no ว่างได้ ไม่ raise (พฤติกรรมเดิม)
        project = self.env["project.project"].create({
            "name": "No Dept Project",
            "od19_project_type": "pm",
        })
        self.assertFalse(project.job_no)

    def test_job_no_is_not_regenerated_on_write(self):
        user = self._sale_user("od19_sale_rep_write", "WR", self._sale_sequence())
        project = self.env["project.project"].create({
            "name": "Sale Project Write",
            "od19_project_type": "sale",
            "od19_sale_person_id": user.id,
        })
        original = project.job_no
        project.write({"od19_sale_person_id": self.env.uid})
        self.assertEqual(project.job_no, original)
```

- [ ] **Step 2: รันเทสต์ให้เห็นว่าแดง**

```powershell
venv19\Scripts\python.exe odoo-bin -c odoo.conf -d odoo19 --http-port=8171 -u od19_project_document_sequence --test-enable --test-tags /od19_project_document_sequence --stop-after-init --log-level=test --logfile="$env:TEMP\od19_w1_t1.log"
```
ต้องเห็น `test_sale_*` fail (ยังไม่มี field `project_sale_sequence_id`, ยังไม่มี type `sale`)

- [ ] **Step 3: เพิ่ม sequence field บน `res.users`**

`models/res_users.py`:

```python
class ResUsers(models.Model):
    _inherit = "res.users"

    od19_initials = fields.Char(...)  # คงเดิม (ใช้เป็น override ของอักษรย่อ)

    project_sale_sequence_id = fields.Many2one(
        "ir.sequence",
        string="Sale Project Job No. Sequence",
        check_company=True,
        help="Sequence that supplies the running counter for Sales-type project "
             "job numbers. The job number itself is built as "
             "S + initials + YY + running number, e.g. SNV26-0001, so the "
             "sequence prefix is ignored.",
    )

    def _od19_derive_initials(self):
        """Return initials taken from the user name, e.g. NV for Nattanai Vinyangkoon."""
        self.ensure_one()
        parts = (self.name or "").split()
        if not parts:
            return ""
        initials = parts[0][0]
        if len(parts) > 1:
            initials += parts[-1][0]
        return initials.upper()

    def _od19_job_no_initials(self):
        """Return the initials used in job numbers: manual value wins when set."""
        self.ensure_one()
        manual = (self.od19_initials or "").strip().upper()
        return manual or self._od19_derive_initials()
```

- [ ] **Step 4: เพิ่ม type `sale` และ branch การสร้าง Job Number**

`models/project_project.py` — ปรับ 3 จุด:

```python
import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

PROJECT_TYPE_SEQUENCE_MAP = {
    "job": ("J", "project_job_sequence_id"),
    "pm": ("PM", "project_pm_sequence_id"),
    "service": ("S", "project_service_sequence_id"),
    # 'sale' ใช้ sequence ของ salesperson เป็นตัวนับ running number เท่านั้น
    "sale": ("S", None),
}

# Sales-type job numbers are always built as S + initials + YY + running number,
# so the prefix configured on the salesperson sequence is ignored.
SALE_TYPE_PREFIX = "S"


def _build_sale_job_no(generated, initials, sequence_date=None):
    """Build a Sales-type job number: S + initials + YY + running number.

    The salesperson sequence only supplies the running counter, so its own prefix
    is ignored: 'JS26-0001' with initials NV becomes 'SNV26-0001'.
    """
    if not generated:
        return generated
    match = re.search(r'\d+\s*$', generated)
    running = match.group(0) if match else generated
    year = (sequence_date or fields.Date.today()).strftime("%y")
    return "%s%s%s-%s" % (SALE_TYPE_PREFIX, initials or "", year, running)
```

`od19_project_type` — ถอด `server` และเพิ่ม `sale`:

```python
        [
            ("job", "Job"),
            ("pm", "Preventive Maintenance"),
            ("service", "Service"),
            ("sale", "Sales"),
        ],
```

`_get_project_sequence()` รองรับ `sale`:

```python
    def _get_project_sequence(self):
        """Return the ir.sequence for this project's type.

        Sales-type projects use the salesperson's own sequence; the other
        types use the department sequence for that project type.
        """
        self.ensure_one()
        if self.od19_project_type == "sale":
            return self.od19_sale_person_id.project_sale_sequence_id or False
        if not self.od19_department_id:
            return False
        seq_field = PROJECT_TYPE_SEQUENCE_MAP.get(self.od19_project_type, (None, None))[1]
        if not seq_field:
            return False
        return getattr(self.od19_department_id, seq_field)
```

`create()` แยกเส้นทาง `sale` (DD-4):

```python
    @staticmethod
    def _od19_sequence_date(vals):
        if vals.get("date_start"):
            return fields.Date.to_date(vals["date_start"])
        return None

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("job_no"):
                continue
            project_type = vals.get("od19_project_type", "job")
            if project_type == "sale":
                sale_person = (
                    self.env["res.users"].browse(vals["od19_sale_person_id"])
                    if vals.get("od19_sale_person_id")
                    else self.env["res.users"]
                )
                sequence = sale_person.project_sale_sequence_id
                if not sequence:
                    raise ValidationError(
                        _("Set a Sale Project Job No. Sequence on the salesperson "
                          "before creating a Sales-type project.")
                    )
                generated = sequence.next_by_id(
                    sequence_date=self._od19_sequence_date(vals)
                )
                if generated:
                    vals["job_no"] = _build_sale_job_no(
                        generated,
                        sale_person._od19_job_no_initials(),
                        self._od19_sequence_date(vals),
                    )
                continue
            department_id = vals.get("od19_department_id")
            if department_id and project_type in PROJECT_TYPE_SEQUENCE_MAP:
                department = self.env["hr.department"].browse(department_id)
                seq_field = PROJECT_TYPE_SEQUENCE_MAP[project_type][1]
                sequence = getattr(department, seq_field) if seq_field else False
                if sequence:
                    sale_person_id = vals.get("od19_sale_person_id")
                    sale_person = (
                        self.env["res.users"].browse(sale_person_id)
                        if sale_person_id
                        else False
                    )
                    initials = sale_person.od19_initials if sale_person else ""
                    generated = sequence.next_by_id(
                        sequence_date=self._od19_sequence_date(vals)
                    )
                    if generated:
                        vals["job_no"] = _insert_initials_before_year(
                            generated, initials
                        )
        return super().create(vals_list)
```

`write()` — คงพฤติกรรมเดิม (regenerate เฉพาะเมื่อ `job_no` ว่าง) และเพิ่ม guard ไม่ให้ regenerate โครงการประเภท `sale` ที่ตั้งใจเว้นว่างไม่ได้ ⇒ ไม่ต้องแก้ เพียงยืนยันว่า `_generate_job_no()` ใช้ `_get_project_sequence()` ที่อัปเดตแล้ว

- [ ] **Step 5: เพิ่มฟิลด์ใน view ของผู้ใช้**

`views/res_users_views.xml` — วาง `project_sale_sequence_id` ต่อจาก `od19_initials` ในเพจ "Project Sequence" ที่มีอยู่ (ต้องมี `groups="base.group_no_one"` ตาม pattern เดิมของไฟล์)

- [ ] **Step 6: รันเทสต์ให้เขียว**

```powershell
venv19\Scripts\python.exe odoo-bin -c odoo.conf -d odoo19 --http-port=8171 -u od19_project_document_sequence --test-enable --test-tags /od19_project_document_sequence --stop-after-init --log-level=test --logfile="$env:TEMP\od19_w1_t1.log"
```
ต้องได้ `0 failed, 0 error(s)` และเทสต์เดิม 8 รายการต้องยังผ่าน

- [ ] **Step 7: ตรวจว่า `od19_accounting_money_in_report` ไม่พังจากการเพิ่มค่า selection**

```powershell
venv19\Scripts\python.exe odoo-bin -c odoo.conf -d odoo19 --http-port=8171 -u od19_accounting_money_in_report --test-enable --test-tags /od19_accounting_money_in_report --stop-after-init --log-level=test --logfile="$env:TEMP\od19_w1_t1b.log"
```
([money_in_report_builder.py](file:///c:/odoo-dev/odoo19/custom_addons/od19_accounting_money_in_report/models/money_in_report_builder.py#L86-L91) อ่าน `selection` ของ `od19_project_type` แบบ dynamic จึงต้องยืนยันว่ายังผ่าน)

---

### Task 2: D2 — แก้เกณฑ์ Risk Level เป็น 70/40

**Files:**
- Modify: `custom_addons/od19_project_enhanced/models/project_risk_report.py`
- Test: `custom_addons/od19_project_enhanced/tests/test_project_risk_report.py` (สร้างใหม่ + `tests/__init__.py`)

- [ ] **Step 1: เขียนเทสต์ที่จะล้มเหลวก่อน**

`tests/__init__.py`:
```python
from . import test_project_risk_report
from . import test_project_pnl
from . import test_project_pnl_wizard
```

`tests/test_project_risk_report.py`:
```python
from odoo.tests.common import TransactionCase


class TestProjectRiskLevel(TransactionCase):
    """Risk level thresholds must match the legacy contract: high >= 70, medium >= 40."""

    def _report(self, score):
        report = self.env["od19.project.risk.report"].new({"risk_score": score})
        report._compute_risk_level()
        return report.risk_level

    def test_level_boundaries(self):
        self.assertEqual(self._report(39), "low")
        self.assertEqual(self._report(40), "medium")
        self.assertEqual(self._report(69), "medium")
        self.assertEqual(self._report(70), "high")
        self.assertEqual(self._report(100), "high")

    def test_no_hardcoded_60_30_threshold_left(self):
        self.assertEqual(self._report(30), "low")
        self.assertEqual(self._report(60), "medium")
```

- [ ] **Step 2: รันเทสต์ให้เห็นว่าแดง**

```powershell
venv19\Scripts\python.exe odoo-bin -c odoo.conf -d odoo19 --http-port=8171 -u od19_project_enhanced --test-enable --test-tags /od19_project_enhanced --stop-after-init --log-level=test --logfile="$env:TEMP\od19_w1_t2.log"
```

- [ ] **Step 3: แก้ `_compute_risk_level`**

[project_risk_report.py](file:///c:/odoo-dev/odoo19/custom_addons/od19_project_enhanced/models/project_risk_report.py#L65-L73) L65-L73:

```python
    # Scoring contract (single source of truth, spec 6.7):
    # margin < 15 -> 40, overdue AR > 0 -> 30, past due date -> 30
    # level: high >= 70, medium >= 40, low < 40
    RISK_LEVEL_HIGH = 70
    RISK_LEVEL_MEDIUM = 40

    @api.depends("risk_score")
    def _compute_risk_level(self):
        for rec in self:
            if rec.risk_score >= self.RISK_LEVEL_HIGH:
                rec.risk_level = "high"
            elif rec.risk_score >= self.RISK_LEVEL_MEDIUM:
                rec.risk_level = "medium"
            else:
                rec.risk_level = "low"
```

- [ ] **Step 4: รันเทสต์ให้เขียว**

คำสั่งเดิมใน Step 2 → `0 failed, 0 error(s)`

---

### Task 3: D5/D6 — Project P&L จาก `account.analytic.line` ใน Risk Report

**Files:**
- Modify: `custom_addons/od19_project_enhanced/models/project_project.py` (เพิ่ม `_od19_get_pnl_values`)
- Modify: `custom_addons/od19_project_enhanced/models/project_risk_report.py` (fields + SQL view + margin)
- Test: `custom_addons/od19_project_enhanced/tests/test_project_pnl.py`

- [ ] **Step 1: เขียนเทสต์ที่จะล้มเหลวก่อน**

`tests/test_project_pnl.py` — ใช้ helper สร้างข้อมูลบัญชีจริง (invoice + vendor bill ผูก analytic):

```python
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestProjectPnl(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.dept = cls.env["hr.department"].create({"name": "PNL Dept"})
        cls.project = cls.env["project.project"].create({
            "name": "PNL Project",
            "od19_department_id": cls.dept.id,
        })
        cls.analytic = cls.project.account_id
        cls.partner = cls.env["res.partner"].create({"name": "PNL Customer"})
        cls.income = cls.env["account.account"].search(
            [("account_type", "=", "income"), ("company_ids", "in", cls.company.id)], limit=1
        )
        cls.expense = cls.env["account.account"].search(
            [("account_type", "=", "expense"), ("company_ids", "in", cls.company.id)], limit=1
        )

    def _analytic_line(self, account, amount, date=None, posted=True):
        """Create a move + analytic line, optionally posting the move."""
        ...
```

เทสต์ขั้นต่ำที่ต้องมี (ครอบ §11 ข้อ 3):

```python
    def test_revenue_and_cost_split_with_sign(self):
        # income 1000 on analytic -> revenue 1000, cost 0
        # expense 400 on analytic -> revenue 1000, cost 400, gross 600, margin 60%
        values = self.project._od19_get_pnl_values()
        self.assertAlmostEqual(values["revenue"], 1000.0, 2)
        self.assertAlmostEqual(values["cost"], 400.0, 2)
        self.assertAlmostEqual(values["gross_margin"], 600.0, 2)
        self.assertAlmostEqual(values["margin_percent"], 60.0, 2)

    def test_draft_move_is_excluded(self):
        # บรรทัดที่ move ยังเป็น draft ต้องไม่ถูกนับ
        ...

    def test_uncategorized_is_reported_separately(self):
        # บัญชีที่จัดประเภทไม่ได้ -> uncategorized_amount ไม่เท่ากับ 0
        ...

    def test_date_range_filters_lines(self):
        ...

    def test_zero_revenue_does_not_divide_by_zero(self):
        values = self.project._od19_get_pnl_values()
        self.assertEqual(values["margin_percent"], 0.0)

    def test_project_without_analytic_account_returns_zero_and_flag(self):
        project = self.env["project.project"].create({"name": "No Analytic"})
        project.account_id = False
        values = project._od19_get_pnl_values()
        self.assertFalse(values["has_analytic"])
        self.assertEqual(values["revenue"], 0.0)
        self.assertEqual(values["cost"], 0.0)
```

- [ ] **Step 2: รันเทสต์ให้เห็นว่าแดง**

```powershell
venv19\Scripts\python.exe odoo-bin -c odoo.conf -d odoo19 --http-port=8171 -u od19_project_enhanced --test-enable --test-tags /od19_project_enhanced --stop-after-init --log-level=test --logfile="$env:TEMP\od19_w1_t3.log"
```

- [ ] **Step 3: เพิ่มสูตร P&L ชุดเดียวบน `project.project`**

`models/project_project.py` (ใน `od19_project_enhanced`) — ต่อท้ายคลาสเดิม:

```python
    def _od19_get_pnl_values(self, date_from=None, date_to=None, company_ids=None):
        """Return project P&L values read from posted analytic lines.

        Single P&L contract for the whole domain (spec 6.6): revenue/cost are
        derived from account.analytic.line.analytic_profitability, which Odoo 19
        computes from the general account type. Never re-implement the
        revenue/cost classification here.
        """
        self.ensure_one()
        company_ids = company_ids or self.env.companies.ids
        result = {
            "analytic_account_id": self.account_id.id or False,
            "has_analytic": bool(self.account_id),
            "revenue": 0.0,
            "cost": 0.0,
            "gross_margin": 0.0,
            "margin_percent": 0.0,
            "uncategorized_amount": 0.0,
        }
        if not self.account_id:
            return result
        base_domain = [
            ("account_id", "=", self.account_id.id),
            ("company_id", "in", list(company_ids)),
            ("move_line_id", "!=", False),
            ("move_line_id.parent_state", "=", "posted"),
        ]
        if date_from:
            base_domain.append(("date", ">=", date_from))
        if date_to:
            base_domain.append(("date", "<=", date_to))

        def _sum(profitability):
            lines = self.env["account.analytic.line"].search(
                base_domain + [("analytic_profitability", "in", [profitability])]
            )
            return sum(lines.mapped("amount"))

        revenue = _sum("revenue")
        cost = -_sum("loss")
        result.update(
            revenue=revenue,
            cost=cost,
            gross_margin=revenue - cost,
            margin_percent=(revenue - cost) / revenue * 100.0 if revenue else 0.0,
            uncategorized_amount=_sum("uncategorized"),
        )
        return result
```

> หมายเหตุ: `analytic_profitability` ใช้ใน domain ได้เฉพาะ operator `in` (core `_search_analytic_profitability`)

- [ ] **Step 4: เพิ่มคอลัมน์ P&L และเขียน SQL view ใหม่**

`models/project_risk_report.py` — เพิ่ม field:

```python
    company_id = fields.Many2one("res.company", string="Company", readonly=True)
    analytic_account_id = fields.Many2one(
        "account.analytic.account", string="Analytic Account", readonly=True
    )
    revenue = fields.Float(string="Revenue", readonly=True)
    actual_cost = fields.Float(string="Actual Cost", readonly=True)   # จาก analytic line
    gross_margin = fields.Float(
        string="Gross Margin", compute="_compute_gross_margin", store=False
    )
    uncategorized_amount = fields.Float(string="Uncategorized", readonly=True)
    margin_percent = fields.Float(
        string="Margin %", compute="_compute_margin_percent", store=False
    )
    has_analytic = fields.Boolean(
        string="Has Analytic Account",
        compute="_compute_has_analytic", store=False,
    )
    pnl_warning = fields.Char(
        string="Warning", compute="_compute_pnl_warning", store=False
    )
```

compute ที่เปลี่ยน:

```python
    @api.depends("revenue", "actual_cost")
    def _compute_gross_margin(self):
        for rec in self:
            rec.gross_margin = rec.revenue - rec.actual_cost

    @api.depends("revenue", "actual_cost")
    def _compute_margin_percent(self):
        # P&L margin (spec 6.6): (Revenue - Cost) / Revenue * 100, guard divide-by-zero
        for rec in self:
            rec.margin_percent = (
                (rec.revenue - rec.actual_cost) / rec.revenue * 100.0
                if rec.revenue else 0.0
            )

    @api.depends("analytic_account_id")
    def _compute_has_analytic(self):
        for rec in self:
            rec.has_analytic = bool(rec.analytic_account_id)

    @api.depends("analytic_account_id", "revenue", "uncategorized_amount")
    def _compute_pnl_warning(self):
        for rec in self:
            if not rec.analytic_account_id:
                rec.pnl_warning = _("No analytic account — P&L shows 0.")
            elif not rec.revenue:
                rec.pnl_warning = _("No recognized revenue in the analytic lines yet.")
            elif rec.uncategorized_amount:
                rec.pnl_warning = _("Uncategorized analytic amounts must be reviewed.")
            else:
                rec.pnl_warning = False
```

`init()` — แทน `exp_agg` (hr_expense) ด้วย `pnl_agg` จาก analytic line และเพิ่มคอลัมน์:

```python
                SELECT
                    p.id AS id,
                    p.id AS project_id,
                    p.name AS project_name,
                    p.company_id AS company_id,
                    p.account_id AS analytic_account_id,
                    COALESCE(so_agg.contract_amount, 0.0) AS contract_amount,
                    COALESCE(ar_agg.invoiced_amount, 0.0) AS invoiced_amount,
                    COALESCE(pnl_agg.revenue, 0.0) AS revenue,
                    COALESCE(pnl_agg.cost, 0.0) AS actual_cost,
                    COALESCE(pnl_agg.uncategorized_amount, 0.0) AS uncategorized_amount,
                    COALESCE(po_agg.committed_cost, 0.0) AS committed_cost,
                    COALESCE(overdue_agg.overdue_ar, 0.0) AS overdue_ar
                FROM project_project p
                ...
                LEFT JOIN (
                    SELECT
                        al.account_id AS analytic_account_id,
                        SUM(CASE WHEN <profitability> = 'revenue' THEN al.amount ELSE 0.0 END) AS revenue,
                        SUM(CASE WHEN <profitability> = 'loss' THEN -al.amount ELSE 0.0 END) AS cost,
                        SUM(CASE WHEN <profitability> = 'uncategorized' THEN al.amount ELSE 0.0 END) AS uncategorized_amount
                    FROM account_analytic_line al
                    JOIN account_move_line aml ON aml.id = al.move_line_id
                    JOIN account_move am
                        ON am.id = aml.move_id
                        AND am.state = 'posted'
                    WHERE al.account_id IS NOT NULL
                    GROUP BY al.account_id
                ) pnl_agg ON pnl_agg.analytic_account_id = p.account_id
```

`<profitability>` ต้องเป็น CASE ที่คัดลอกจาก core [account_analytic_line.py](file:///c:/odoo-dev/odoo19/addons/account/models/account_analytic_line.py#L138-L156) L138-L156 ให้ตรงทุกตัวอักษร (รวม comment กำกับว่าต้อง sync กับ core):

```sql
                    CASE
                        WHEN (
                            SPLIT_PART(aa.account_type, '_', 1) = 'expense'
                            OR aa.account_type IN ('asset_current', 'asset_non_current', 'asset_fixed')
                            OR (aa.account_type IS NULL AND al.category NOT IN ('invoice', 'other'))
                            OR (aa.account_type IS NULL AND al.category = 'other' AND al.amount < 0)
                        ) THEN 'loss'
                        WHEN (
                            SPLIT_PART(aa.account_type, '_', 1) = 'income'
                            OR (aa.account_type IS NULL AND al.category = 'other' AND al.amount > 0)
                        ) THEN 'revenue'
                        ELSE 'uncategorized'
                    END
```
โดยมี `LEFT JOIN account_account aa ON aa.id = al.general_account_id` ใน subquery

และ `risk_score`/`margin_percent` ต้องคงกติกา **ห้ามใช้ non-stored computed field ใน `_order`** — คง `_order = "id"` ไว้

> DD-1: `_compute_risk_score` ต้องไม่ให้คะแนน margin เมื่อ `revenue == 0` (ถ้าเลือกทาง (ก)):
> ```python
>             if rec.revenue and rec.margin_percent < 15:
>                 score += 40
> ```

- [ ] **Step 5: ปรับ view ให้เห็น P&L และคำเตือน**

`views/project_risk_report_views.xml` — เพิ่มใน list หลัง `invoiced_amount`: `revenue`, `actual_cost`, `gross_margin`, `uncategorized_amount`, `margin_percent`, `pnl_warning` (ใช้ `decoration-danger` กับ `pnl_warning`) และเพิ่ม `revenue`/`gross_margin` เป็น measure ใน pivot

- [ ] **Step 6: รันเทสต์ให้เขียว**

```powershell
venv19\Scripts\python.exe odoo-bin -c odoo.conf -d odoo19 --http-port=8171 -u od19_project_enhanced --test-enable --test-tags /od19_project_enhanced --stop-after-init --log-level=test --logfile="$env:TEMP\od19_w1_t3.log"
```

---

### Task 4: D7 — Project P&L Report ตามช่วงวันที่ + KPI คุณภาพข้อมูล

**Files:**
- Create: `custom_addons/od19_project_enhanced/models/project_pnl_report.py`
- Create: `custom_addons/od19_project_enhanced/views/project_pnl_report_views.xml`
- Modify: `custom_addons/od19_project_enhanced/models/__init__.py`
- Modify: `custom_addons/od19_project_enhanced/__manifest__.py`
- Modify: `custom_addons/od19_project_enhanced/security/ir.model.access.csv`
- Test: `custom_addons/od19_project_enhanced/tests/test_project_pnl_wizard.py`

- [ ] **Step 1: เขียนเทสต์ที่จะล้มเหลวก่อน**

`tests/test_project_pnl_wizard.py`:
```python
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestProjectPnlWizard(TransactionCase):

    def test_generate_lines_for_selected_projects(self):
        wizard = self.env["od19.project.pnl.report"].create({
            "date_from": "2026-01-01",
            "date_to": "2026-12-31",
        })
        wizard.action_generate()
        self.assertTrue(wizard.line_ids)

    def test_wizard_warns_when_project_has_no_analytic(self):
        project = self.env["project.project"].create({"name": "Wizard No Analytic"})
        project.account_id = False
        wizard = self.env["od19.project.pnl.report"].create({
            "date_from": "2026-01-01",
            "date_to": "2026-12-31",
            "project_ids": [(6, 0, project.ids)],
        })
        wizard.action_generate()
        line = wizard.line_ids.filtered(lambda l: l.project_id == project)
        self.assertFalse(line.has_analytic)
        self.assertTrue(line.warning)

    def test_risk_report_and_pnl_agree_for_full_range(self):
        # ตรวจ spec 11 ข้อ 4: Risk Report (SQL view) และ P&L (Python) ต้องตรงกัน
        ...
```

- [ ] **Step 2: รันเทสต์ให้เห็นว่าแดง**

```powershell
venv19\Scripts\python.exe odoo-bin -c odoo.conf -d odoo19 --http-port=8171 -u od19_project_enhanced --test-enable --test-tags /od19_project_enhanced --stop-after-init --log-level=test --logfile="$env:TEMP\od19_w1_t4.log"
```

- [ ] **Step 3: สร้าง wizard**

`models/project_pnl_report.py`:

```python
from odoo import _, api, fields, models


class Od19ProjectPnlReport(models.TransientModel):
    _name = "od19.project.pnl.report"
    _description = "Project P&L Report"

    date_from = fields.Date(
        string="From", required=True,
        default=lambda self: fields.Date.context_today(self).replace(day=1),
    )
    date_to = fields.Date(
        string="To", required=True, default=fields.Date.context_today
    )
    company_ids = fields.Many2many(
        "res.company", string="Companies", default=lambda self: self.env.companies
    )
    project_ids = fields.Many2many(
        "project.project", string="Projects",
        help="เว้นว่างไว้เพื่อประมวลผลทุกโครงการ",
    )
    line_ids = fields.One2many(
        "od19.project.pnl.report.line", "wizard_id", string="Results"
    )

    def action_generate(self):
        self.ensure_one()
        self.line_ids.unlink()
        projects = self.project_ids or self.env["project.project"].search(
            [("company_id", "in", self.company_ids.ids)]
        )
        lines = []
        for project in projects:
            values = project._od19_get_pnl_values(
                date_from=self.date_from,
                date_to=self.date_to,
                company_ids=self.company_ids.ids,
            )
            lines.append((0, 0, dict(values, project_id=project.id)))
        self.line_ids = lines
        return {
            "type": "ir.actions.act_window",
            "name": _("Project P&L"),
            "res_model": "od19.project.pnl.report.line",
            "view_mode": "list",
            "domain": [("id", "in", self.line_ids.ids)],
            "target": "current",
        }


class Od19ProjectPnlReportLine(models.TransientModel):
    _name = "od19.project.pnl.report.line"
    _description = "Project P&L Report Line"

    wizard_id = fields.Many2one(
        "od19.project.pnl.report", ondelete="cascade", required=True
    )
    project_id = fields.Many2one("project.project", string="Project")
    analytic_account_id = fields.Many2one(
        "account.analytic.account", string="Analytic Account"
    )
    has_analytic = fields.Boolean(string="Has Analytic Account")
    revenue = fields.Float(string="Revenue")
    cost = fields.Float(string="Cost")
    gross_margin = fields.Float(string="Gross Margin")
    margin_percent = fields.Float(string="Margin %")
    uncategorized_amount = fields.Float(string="Uncategorized")
    warning = fields.Char(string="Warning", compute="_compute_warning")

    @api.depends("has_analytic", "revenue", "uncategorized_amount")
    def _compute_warning(self):
        for line in self:
            if not line.has_analytic:
                line.warning = _("No analytic account — P&L shows 0.")
            elif not line.revenue:
                line.warning = _("No recognized revenue yet.")
            elif line.uncategorized_amount:
                line.warning = _("Uncategorized amounts must be reviewed.")
            else:
                line.warning = False
```

เพิ่ม `from . import project_pnl_report` ใน `models/__init__.py`

- [ ] **Step 4: views + security + manifest**

`views/project_pnl_report_views.xml` — wizard form (`date_from`, `date_to`, `company_ids`, `project_ids`, ปุ่ม `action_generate` เป็น `type="object"` ชื่อ "Generate") + list view ของ `od19.project.pnl.report.line` (คอลัมน์ project, analytic, revenue, cost, gross_margin, margin_percent, uncategorized, warning) + `ir.actions.act_window` ของ wizard (`view_mode=form`, `target=new`) + `menuitem` ถัดจาก Risk Report (parent `project.menu_main_pm`, sequence 96)

`security/ir.model.access.csv` — เพิ่ม:
```
access_od19_project_pnl_report_user,od19.project.pnl.report.user,model_od19_project_pnl_report,project.group_project_user,1,1,1,1
access_od19_project_pnl_report_line_user,od19.project.pnl.report.line.user,model_od19_project_pnl_report_line,project.group_project_user,1,1,1,1
```
(ชื่อ access right ต้องไม่ซ้ำกับโมดูลอื่น — ตรวจด้วย grep ก่อน)

`__manifest__.py` — เพิ่ม `"views/project_pnl_report_views.xml"` ใน `data`

- [ ] **Step 5: เพิ่ม KPI คุณภาพข้อมูล (D7)**

`views/project_project_views.xml` (ของ `od19_project_enhanced`) — เพิ่ม `ir.actions.act_window` + `menuitem` 2 รายการบน `project.project`:
- "Projects without Job Number": domain `[('job_no', '=', False)]`
- "Projects without Analytic Account": domain `[('account_id', '=', False)]`

ทั้งสองใช้ view_mode `list,form` และ `create="false"` ใน list

- [ ] **Step 6: รันเทสต์ให้เขียว**

```powershell
venv19\Scripts\python.exe odoo-bin -c odoo.conf -d odoo19 --http-port=8171 -u od19_project_enhanced --test-enable --test-tags /od19_project_enhanced --stop-after-init --log-level=test --logfile="$env:TEMP\od19_w1_t4.log"
```

---

### Task 5: Task — Compatibility Regression (spec §11 ข้อ 4)

**Files:**
- Test: `custom_addons/od19_project_enhanced/tests/test_project_pnl_wizard.py` (เพิ่มเทสต์ consistency) และ/หรือ `od19_project_analytic/tests/`

- [ ] **Step 1: เขียนเทสต์ compatibility**

ต้องครอบ:
```python
    def test_sale_project_can_be_created_without_job_no_by_sale_project(self):
        # โครงการที่สร้างจาก sale_project ต้องไม่ล้มเหลวเพราะไม่มี job_no / แผนก
        ...

    def test_sales_project_context_owner_guard_still_raises(self):
        # od19_sales_project_context ยังบังคับว่า owner บน SO ต้องตรงกับ project
        ...

    def test_risk_report_order_has_no_non_stored_field(self):
        self.assertEqual(
            self.env["od19.project.risk.report"]._order, "id"
        )
```

- [ ] **Step 2: รัน regression ของโดเมน project ทั้งหมด**

```powershell
venv19\Scripts\python.exe odoo-bin -c odoo.conf -d odoo19 --http-port=8171 -u od19_project_analytic,od19_project_document_sequence,od19_project_enhanced,od19_sales_project_context,od19_accounting_money_in_report --test-enable --test-tags /od19_project_analytic,/od19_project_document_sequence,/od19_project_enhanced,/od19_sales_project_context,/od19_accounting_money_in_report --stop-after-init --log-level=test --logfile="$env:TEMP\od19_w1_all.log"
```
เกณฑ์ผ่าน: `0 failed, 0 error(s)` และจำนวนเทสต์ที่รัน ≥ 41 (baseline เดิม) + เทสต์ใหม่

- [ ] **Step 3: ตรวจ log ว่าไม่มี warning ใหม่**

อ่าน `$env:TEMP\od19_w1_all.log` — ต้องไม่มี `WARNING` ที่เกิดจากไฟล์ที่เราแก้ (noise เดิมของ `od19.job.application has no table` จาก `od19_website` ให้ตัดออก)

---

### Task 6: Task — Governance Docs และ Commit

**Files:**
- Modify: `docs/superpowers/programs/odoo19-enterprise/backlog/domain-spec-index.md`
- Modify: `docs/superpowers/programs/odoo19-enterprise/backlog/domain-wave-matrix.md` (ถ้ามี row ของ W1-PROJECT-ANALYTIC)

- [ ] **Step 1: อัปเดต index**

- แถว `W1-PROJECT-ANALYTIC`: เปลี่ยน status เป็น `Implemented 2026-<MM-DD> — D1–D7 implemented; tests passing`
- แถว `W1-COMMERCIAL-CORE`: อัปเดต gate readiness — Project & Analytic Accounting ผ่านแล้ว (เหลือ migration assumptions)
- Wave Sequencing Notes: ระบุว่า P&L ใช้ `account.analytic.line` + `analytic_profitability` และ risk threshold เป็น 70/40
- **ห้ามปล่อยข้อความล้าสมัย** (keep wave naming, child-spec IDs, path placeholders synchronized)

- [ ] **Step 2: ตรวจว่าไฟล์ที่ต้อง track ถูก add แบบ force**

```powershell
git add -f custom_addons/od19_project_enhanced/security/ir.model.access.csv
git add custom_addons/od19_project_document_sequence custom_addons/od19_project_enhanced docs/superpowers
git status --short
```

- [ ] **Step 3: Commit (Conventional Commits)**

```powershell
git commit -m "feat(project): add sale job type and analytic-based project P&L"
```
เนื้อความ commit ต้องระบุ: D1 sale job type + salesperson sequence, D2 risk threshold 70/40, D5/D6 P&L from analytic line, D7 warning + KPI

- [ ] **Step 4: รายงานผลต่อผู้ใช้**

สรุป: ไฟล์ที่แก้, จำนวนเทสต์ที่ผ่าน, ค่า DD-1 ที่เลือก, และงานค้าง P1 (`i18n/th.po` ของ 4 โมดูล project — ไม่อยู่ในขอบเขตแผนนี้; ส่งมอบแยกเมื่อ 2026-10-21, commit `30a6621f8b6`)

---

## Verification และ Exit Criteria

งานนี้ถือว่า **ผ่าน** เมื่อ:

1. `od19_project_type` มีค่า `job`, `pm`, `service`, `sale` เท่านั้น (ไม่มี `server`) และไม่มี `project_server_sequence_id` / `project.server.*` เหลืออยู่ทั้งในโค้ดและใน `job_type_values` — DD-5
2. `od19_project_type` มีค่า `sale` และ Job Number ประเภท `sale` ใช้ sequence ของ salesperson (มีเทสต์ยืนยัน) — D1
2. ไม่มี `ValidationError` แบบเงียบ: ถ้า salesperson ไม่มี sequence และไม่มี `job_no` ⇒ raise — D1/DD-4
3. `_compute_risk_level` เป็น `high ≥ 70`, `medium ≥ 40` และมีเทสต์ครอบเส้นแบ่ง 39/40 และ 69/70 — D2
4. `od19.project.risk.report` มีคอลัมน์ `revenue`, `actual_cost` (จาก analytic line), `gross_margin`, `uncategorized_amount`, `margin_percent` และได้ตัวเลขจาก `account.analytic.line` ที่ post แล้วเท่านั้น — D5/D6
5. ไม่มีโมดูล `od19_project_pnl` ถูกสร้าง — D5
6. P&L report กรองตามช่วงวันที่และบริษัทได้ และ Risk Report กับ P&L ให้ตัวเลขตรงกัน (consistency test ผ่าน) — §6.6/§11
7. โครงการที่ไม่มี Analytic Account ⇒ P&L = 0 พร้อมคำเตือน และมี KPI menu action นับโครงการที่ยังไม่มี Analytic Account / ไม่มี Job Number — D7
8. `name` ของโครงการไม่ถูกผสมกับ `job_no` — D3
9. ไม่มีไฟล์ Odoo core ถูกแก้ และไม่ดึง Wave 2/3 เข้ามา — Hard constraint
10. Regression: `od19_project_analytic` 6/6, `od19_project_document_sequence` 8/8 + ใหม่, `od19_sales_project_context` 4/4, `od19_accounting_money_in_report` 23/23 + เทสต์ใหม่ทั้งหมด ⇒ `0 failed, 0 error(s)`
11. index/wave matrix ถูกอัปเดตให้สอดคล้อง ไม่มีข้อความล้าสมัย

## Out of Scope (บันทึกไว้ ไม่ทำในรอบนี้)

- เอกสารบังคับก่อนเข้าพื้นที่ ~25 ฟิลด์ (D4) — Wave 3/4
- JasperReports ของ Job Assignment Report — Wave 2 (Dual Report Format)
- Project Site / Task Category / Timesheet (legacy `dtr_project`) — Wave 3/4
- Project Revision / Locking / Approval workflow
- Migration script สำหรับข้อมูลโครงการจาก Odoo 15 — migration workstream แยก (spec §9)
- `i18n/th.po` ของโมดูล project (งานค้าง P1) — **ส่งมอบแล้ว 2026-10-21** (commit `30a6621f8b6`; 4 โมดูล: `od19_project_analytic`, `od19_project_document_sequence`, `od19_sales_project_context`, `od19_project_enhanced`)

## Risks และ Mitigation

| ความเสี่ยง | Mitigation |
| --- | --- |
| สูตร P&L มี 2 implementation (SQL view vs Python wizard) แล้วเพี้ยนจากกัน | consistency test บังคับ (§11 ข้อ 4) + comment กำกับทั้งสองที่ว่าต้อง sync กับ core `_field_to_sql` |
| core เปลี่ยนสูตร `analytic_profitability` แล้ว SQL view เพี้ยน | comment ชี้ตรงไปที่ `addons/account/models/account_analytic_line.py` `_field_to_sql` + เทสต์ที่ยืนยันตัวเลขจาก analytic line จริง |
| เปลี่ยนฐาน Margin % ทำให้คะแนนความเสี่ยงเปลี่ยนจากเดิม | DD-1 ต้องยืนยันก่อนเริ่ม Task 3; มีเทสต์เส้นแบ่งและเทสต์ WIP (revenue = 0) |
| เพิ่มค่า selection `sale` แล้วรายงานอื่นพัง | Task 1 Step 7 รัน regression ของ `od19_accounting_money_in_report` (อ่าน selection แบบ dynamic) |
| แก้ไฟล์ระหว่างที่ dev server รันอยู่ | ห้าม checkout; ใช้ `-u` ผ่าน CLI ที่พอร์ต 8171; restart server เมื่อผู้ใช้พร้อม |
