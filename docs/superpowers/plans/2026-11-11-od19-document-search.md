# od19_document_search (P3) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ยกระดับ "คลังกลาง" ของ `od19_document_hub` ให้ค้นเจอเร็ว (เป้า 2 · ≤ 2 วินาที) โดยค้นได้ทั้ง **ชื่อไฟล์** และ **ข้อความในไฟล์ (ไทย)** ผ่านดัชนี `pg_trgm` ที่มีอยู่แล้ว พร้อม facets ครบรูป ป้ายไฟล์ซ้ำ และปุ่มจัดหมวดเป็นชุด — ไม่แตะไฟล์ core

**Architecture:** ต่อยอดจาก `od19_document_hub` (P1) ที่มีอยู่แล้ว — ฟิลด์ `od19_*` บน `ir.attachment`, โมเดล `od19.document.extract` (มี GIN trigram บน `text_content`) และดัชนี GIN trigram บน `ir.attachment.name` / btree บน `checksum` แผนนี้ **ไม่สร้างโมดูลใหม่** เพียงเพิ่ม (ก) ฟิลด์ค้นหาแบบไม่เก็บค่า + เมธอด `search` ที่รวมชื่อไฟล์กับเนื้อหาเข้าด้วยกันผ่าน join ไปยัง `od19.document.extract` (ข) facets/filters/group-by เต็มรูปใน search view (ค) ปุ่ม/wizard จัดหมวดเป็นชุด และ (ง) เทสต์ยืนยันว่าดัชนี trigram ถูกใช้จริง

**Tech Stack:** Odoo 19 (Python 3), PostgreSQL 16 + `pg_trgm`, `models.Index("USING gin (... gin_trgm_ops)")`, Odoo search view inheritance, TransientModel, PowerShell `run-tests.ps1`

**อ้างอิงสเปก:** [2026-11-11-od19-document-hub-design.md](../specs/2026-11-11-od19-document-hub-design.md) (§4 D4 trigram, §6.3 ดัชนี, §7.2 คลังกลาง, §10 แผนทดสอบ, §11 P3)

---

## ขอบเขตของแผนนี้

แผนนี้ครอบคลุม **P3 (ค้นหากลาง · เป้า 2) เท่านั้น** ตาม §11 ของสเปก — อยู่ในโมดูล `od19_document_hub`

- **อยู่ในขอบเขต:**
  - ค้นในเนื้อไฟล์ที่สกัดได้ (`od19.document.extract.text_content`) รวมกับการค้นชื่อไฟล์ในกล่องเดียว (trigram-accelerated)
  - facets ครบรูปตาม §7.2: วันที่ · หมวด · คู่ค้า · แผนก · ความลับ · ที่มา · สถานะ index (+ group-by ชุดเนื้อหาเดียวกันด้วย `checksum`)
  - ป้าย/คอลัมน์ไฟล์ซ้ำ + ขนาดไฟล์ในคลังกลาง
  - ปุ่ม "จัดหมวดเป็นชุด" (bulk categorize) สำหรับรายการที่เลือกหลายรายการ
  - เทสต์ยืนยันการใช้งานดัชนี trigram (`EXPLAIN` ต้องเห็น index scan) และความถูกต้องของการค้น
- **นอกขอบเขต (แผนอื่น):**
  - record rule กรองตาม `od19_confidentiality`/`od19_department_id` → `od19_document_governance` (P4) ตาม §5.1 + note ของแผน P1
  - นโยบายอายุ/บังคับใช้/legal hold/audit/GC/dashboard ตัววัด → P4/P5
  - side panel เปิดดูไฟล์แบบไม่ดาวน์โหลด (ปรับ UX เฉพาะทาง) → พิจารณาเฟสถัดไป เว้นแต่ใช้ปุ่ม preview มาตรฐานของ core
- **การพึ่งพา:** P1 (`od19_document_hub` บน `19.0` แล้ว) · extension `pg_trgm` (สร้างโดย `pre_init_hook` ของ hub) · ไม่เพิ่ม dependency Python
- **หมายเหตุ P3 ไม่ผูกกับ `od19_document_intake`:** เนื้อไฟล์จะถูกสกัดเข้าตาราง `od19.document.extract` โดย P2 (intake) หรือกรอกมือ/mlf ก็ได้ — เทสต์ของแผนนี้สร้างระเบียน `od19.document.extract` เอง

## ขั้นเตรียมการ (ทำครั้งเดียวก่อนเริ่ม)

- [ ] **เตรียม 1: สร้าง worktree + branch**

> ต้องถือ lease `git:worktree` ก่อน (Tier 2). ถ้าไม่ว่าง ให้รอจนหมดอายุ ห้าม break

```powershell
pwsh -File .\agent-lock.ps1 -Action Acquire -Resource git:worktree -AgentId trae-od19_document_search -Purpose "create worktree feature/od19_document_hub-search" -Ttl 600
git worktree add ..\od19_doc_search -b feature/od19_document_hub-search 19.0
```

- [ ] **เตรียม 2: ยืนยันว่า `od19_document_hub` ติดตั้งได้บน DB ทดสอบของตัวเอง**

Run:
```powershell
pwsh -File .\run-tests.ps1 -Module od19_document_hub -Database odoo19_t_doc_search -HttpPort 8083
```
Expected: PASS (เป็นฐานให้ P3 ต่อ)

- [ ] **เตรียม 3: ยืนยัน extension `pg_trgm` + ดัชนี trigram ของ hub**

Run:
```powershell
psql -U odoo -d odoo19_t_doc_search -c "SELECT extname FROM pg_extension WHERE extname='pg_trgm';"
psql -U odoo -d odoo19_t_doc_search -c "SELECT indexname FROM pg_indexes WHERE tablename IN ('ir_attachment','od19_document_extract') AND indexdef ILIKE '%gin%';"
```
Expected: มีแถว `pg_trgm` และมี index ที่มี `gin_trgm_ops` อย่างน้อย 2 ตัว (ชื่อ `name`, `text_content`)

> **หมายเหตุ AGENT_ID:** ใช้ `trae-od19_document_search` · DB ทดสอบ `odoo19_t_doc_search` · พอร์ต `8083` (hub=8081, intake=8082 — ห้ามซ้ำ)

---

## โครงสร้างไฟล์

```
custom_addons/od19_document_hub/
├── __manifest__.py                        # (modify) bump version 19.0.1.1.0
├── models/
│   ├── ir_attachment.py                   # (modify) od19_extract_ids + od19_search_text + search()
│   └── od19_document_bulk_category.py     # (create) wizard จัดหมวดเป็นชุด
├── views/
│   ├── ir_attachment_views.xml            # (modify) facets เต็มรูป + คอลัมน์ขนาด/ซ้ำ + search field
│   └── od19_document_bulk_category_views.xml  # (create) wizard form + act_window binding
├── security/
│   └── ir.model.access.csv                # (modify) สิทธิ์ wizard
├── tests/
│   ├── __init__.py                        # (modify) register test ใหม่
│   ├── test_document_search.py            # (create) ค้นชื่อ/เนื้อหา + facets
│   └── test_document_search_perf.py       # (create) ยืนยันการใช้ดัชนี trigram
└── i18n/
    └── th.po                              # (modify) เพิ่มคำแปลสตริงใหม่
```

**คำสั่งทดสอบที่ใช้ทั้งแผน** (DB ทดสอบส่วนตัวตาม AGENTS.md §6):
```powershell
pwsh -File .\run-tests.ps1 -Module od19_document_hub -Database odoo19_t_doc_search -HttpPort 8083
```

---

### Task 1: ค้นในเนื้อไฟล์ (trigram) + กล่องค้นรวมความ

**Files:**
- Modify: `custom_addons/od19_document_hub/models/ir_attachment.py`
- Create: `custom_addons/od19_document_hub/tests/test_document_search.py`
- Modify: `custom_addons/od19_document_hub/tests/__init__.py`

- [ ] **Step 1: เขียนเทสต์ก่อน (ให้แดง)**

`tests/test_document_search.py`
```python
# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo.tests.common import TransactionCase


class TestDocumentSearch(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Attachment = cls.env["ir.attachment"]
        cls.Extract = cls.env["od19.document.extract"]
        cls.att_name = cls.Attachment.create({
            "name": "ใบเสร็จค่าไฟฟ้า_มีนาคม.pdf",
            "raw": b"dummy",
        })
        cls.att_content = cls.Attachment.create({
            "name": "scan_0001.pdf",
            "raw": b"dummy",
        })
        cls.Extract.create({
            "attachment_id": cls.att_content.id,
            "text_content": "สัญญาจ้างเหมาประกอบตู้ หมายเลข PO-2569-0042",
            "engine": "manual",
        })

    def test_search_by_filename(self):
        """ค้นด้วยชื่อไฟล์ (ไทย) ต้องเจอ"""
        found = self.Attachment.search(
            [("od19_search_text", "ilike", "ใบเสร็จค่าไฟฟ้า")],
        )
        self.assertIn(self.att_name, found)

    def test_search_by_content(self):
        """ค้นด้วยข้อความในไฟล์ (ไทย) ต้องเจอ แม้ชื่อไฟล์ไม่ตรง"""
        found = self.Attachment.search(
            [("od19_search_text", "ilike", "PO-2569-0042")],
        )
        self.assertIn(self.att_content, found)
        self.assertNotIn(self.att_name, found)

    def test_search_combined_name_or_content(self):
        """กล่องเดียวค้นทั้งชื่อและเนื้อหา"""
        found = self.Attachment.search(
            [("od19_search_text", "ilike", "ประกอบตู้")],
        )
        self.assertIn(self.att_content, found)

    def test_extract_relation(self):
        """ir.attachment ต้องเห็น od19_extract_ids ย้อนกลับ"""
        self.assertEqual(len(self.att_content.od19_extract_ids), 1)

    def test_search_empty_term_returns_all(self):
        """ค่าว่างไม่กรองออก"""
        found = self.Attachment.search([("od19_search_text", "ilike", "")])
        self.assertIn(self.att_name, found)
        self.assertIn(self.att_content, found)
```

`tests/__init__.py` (เพิ่มบรรทัดต่อท้าย)
```python
from . import test_document_search
```

- [ ] **Step 2: รันเทสต์ให้เห็นว่าแดง**

Run: `pwsh -File .\run-tests.ps1 -Module od19_document_hub -Database odoo19_t_doc_search -HttpPort 8083`
Expected: FAIL — `Field 'od19_search_text' does not exist` / `od19_extract_ids` ไม่มี

- [ ] **Step 3: เพิ่มฟิลด์และเมธอดค้น**

`models/ir_attachment.py` — เพิ่มต่อจากบรรทัด `_od19_checksum_idx = ...` (ก่อน `@api.depends` ตัวแรก)

```python
    od19_extract_ids = fields.One2many(
        "od19.document.extract", "attachment_id", "ข้อความที่สกัดได้",
    )
    od19_search_text = fields.Char(
        "ค้นชื่อ/เนื้อหาไฟล์",
        compute="_compute_od19_search_text",
        search="_search_od19_search_text",
        store=False,
    )

    def _compute_od19_search_text(self):
        # ฟิลด์สำหรับค้นอย่างเดียว ไม่เก็บค่า
        for attachment in self:
            attachment.od19_search_text = False

    def _search_od19_search_text(self, operator, value):
        """กล่องค้นรวม: จับคู่ทั้งชื่อไฟล์และเนื้อหาที่สกัดได้ (ใช้ดัชนี trigram)

        ค่าว่าง/None = ไม่กรอง (คืนเงื่อนไขจริงทั้งหมด)
        """
        if not value:
            return []
        return [
            "|",
            ("name", "ilike", value),
            ("od19_extract_ids.text_content", "ilike", value),
        ]
```

- [ ] **Step 4: รันเทสต์ให้เขียว**

Run: `pwsh -File .\run-tests.ps1 -Module od19_document_hub -Database odoo19_t_doc_search -HttpPort 8083`
Expected: PASS — `0 failed, 0 error(s)` (จำนวนเทสต์เพิ่มขึ้น 5)

- [ ] **Step 5: Commit**

```powershell
git add custom_addons/od19_document_hub/models/ir_attachment.py custom_addons/od19_document_hub/tests/test_document_search.py custom_addons/od19_document_hub/tests/__init__.py
git commit -m "feat(od19_document_hub): search attachments by name and extracted content"
```

---

### Task 2: Facets เต็มรูป + คอลัมน์ขนาด/ซ้ำในคลังกลาง

**Files:**
- Modify: `custom_addons/od19_document_hub/views/ir_attachment_views.xml`

- [ ] **Step 1: เขียน search view ใหม่ (facets ครบรูป)**

แทนที่ record `view_attachment_search_od19_hub` ทั้งก้อนใน `views/ir_attachment_views.xml`

```xml
    <record id="view_attachment_search_od19_hub" model="ir.ui.view">
        <field name="name">ir.attachment.search.od19.hub</field>
        <field name="model">ir.attachment</field>
        <field name="inherit_id" ref="base.view_attachment_search"/>
        <field name="arch" type="xml">
            <field name="name" position="after">
                <field name="od19_search_text" string="ค้นชื่อ/เนื้อหาไฟล์"
                       filter_domain="[('od19_search_text', 'ilike', self)]"/>
                <field name="od19_category_id"/>
                <field name="od19_partner_id"/>
                <field name="od19_department_id"/>
                <field name="od19_confidentiality"/>
                <field name="od19_doc_date"/>
                <field name="od19_index_state"/>
            </field>
            <filter name="binary_filter" position="after">
                <filter name="od19_external" string="รับจากภายนอก"
                        domain="[('od19_origin','=','external')]"/>
                <filter name="od19_internal" string="สร้างจากระบบ"
                        domain="[('od19_origin','=','internal')]"/>
                <separator/>
                <filter name="od19_index_pending" string="รอสกัดข้อความ"
                        domain="[('od19_index_state','in',['pending','failed'])]"/>
                <separator/>
                <filter name="od19_confidential" string="ความลับขึ้นไป"
                        domain="[('od19_confidentiality','in',['confidential','secret'])]"/>
            </filter>
            <group position="inside">
                <filter name="od19_group_category" string="หมวดเอกสาร"
                        domain="[]" context="{'group_by':'od19_category_id'}"/>
                <filter name="od19_group_origin" string="ที่มา"
                        domain="[]" context="{'group_by':'od19_origin'}"/>
                <filter name="od19_group_department" string="แผนก"
                        domain="[]" context="{'group_by':'od19_department_id'}"/>
                <filter name="od19_group_partner" string="คู่ค้า"
                        domain="[]" context="{'group_by':'od19_partner_id'}"/>
                <filter name="od19_group_confidentiality" string="ระดับความลับ"
                        domain="[]" context="{'group_by':'od19_confidentiality'}"/>
                <filter name="od19_group_index_state" string="สถานะสกัดข้อความ"
                        domain="[]" context="{'group_by':'od19_index_state'}"/>
                <filter name="od19_group_checksum" string="แฟ้มเนื้อหาเดียวกัน"
                        domain="[]" context="{'group_by':'checksum'}"/>
            </group>
        </field>
    </record>
```

- [ ] **Step 2: เพิ่มคอลัมน์ขนาดไฟล์ + จำนวนระเบียนที่ใช้ไฟล์เดียวกัน ใน list view**

ใน record `view_attachment_tree_od19_hub` แก้ block `<field name="name" position="after">` เป็น

```xml
            <field name="name" position="after">
                <field name="od19_category_id"/>
                <field name="od19_origin"/>
                <field name="od19_doc_date"/>
                <field name="od19_confidentiality"/>
                <field name="file_size"/>
                <field name="od19_duplicate_count" string="ซ้ำ"/>
            </field>
```
และเพิ่ม decoration ระดับ list (ก่อน `<field name="name" position="after">`) เพื่อเน้นไฟล์ซ้ำ

```xml
            <list position="attributes">
                <attribute name="decoration-danger">od19_duplicate_count &gt; 0</attribute>
            </list>
```

- [ ] **Step 3: ตรวจ XML well-formed**

Run:
```powershell
pwsh -Command "Get-ChildItem custom_addons\od19_document_hub\views\*.xml | ForEach-Object { [xml](Get-Content $_.FullName -Raw) | Out-Null; Write-Host ('OK ' + $_.Name) }"
```
Expected: `OK` ทุกไฟล์

- [ ] **Step 4: รันเทสต์ (ต้องไม่พังจากการโหลด view)**

Run: `pwsh -File .\run-tests.ps1 -Module od19_document_hub -Database odoo19_t_doc_search -HttpPort 8083`
Expected: PASS — `0 failed, 0 error(s)`

- [ ] **Step 5: Commit**

```powershell
git add custom_addons/od19_document_hub/views/ir_attachment_views.xml
git commit -m "feat(od19_document_hub): add full search facets and library columns"
```

---

### Task 3: จัดหมวดเป็นชุด (bulk categorize)

**Files:**
- Create: `custom_addons/od19_document_hub/models/od19_document_bulk_category.py`
- Modify: `custom_addons/od19_document_hub/models/__init__.py`
- Create: `custom_addons/od19_document_hub/views/od19_document_bulk_category_views.xml`
- Modify: `custom_addons/od19_document_hub/__manifest__.py` (เพิ่ม data file)
- Modify: `custom_addons/od19_document_hub/security/ir.model.access.csv`
- Modify: `custom_addons/od19_document_hub/tests/test_document_search.py`

- [ ] **Step 1: เขียนเทสต์ก่อน (ให้แดง)**

เพิ่มใน `tests/test_document_search.py` (ภายในคลาส `TestDocumentSearch`)

```python
    def test_bulk_category_wizard(self):
        """wizard จัดหมวดเป็นชุด ต้องเขียนหมวดให้ทุกระเบียนที่เลือก"""
        category = self.env["od19.document.category"].create({
            "name": "ใบกำกับภาษี", "code": "SEARCH-001",
        })
        wizard = self.env["od19.document.bulk.category.wizard"].with_context(
            active_ids=(self.att_name + self.att_content).ids,
        ).create({"category_id": category.id})
        wizard.action_apply()
        self.assertEqual(self.att_name.od19_category_id, category)
        self.assertEqual(self.att_content.od19_category_id, category)
```

- [ ] **Step 2: รันเทสต์ให้เห็นว่าแดง**

Run: `pwsh -File .\run-tests.ps1 -Module od19_document_hub -Database odoo19_t_doc_search -HttpPort 8083`
Expected: FAIL — ไม่มีโมเดล `od19.document.bulk.category.wizard`

- [ ] **Step 3: สร้างโมเดล wizard**

`models/od19_document_bulk_category.py`
```python
# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class Od19DocumentBulkCategory(models.TransientModel):
    _name = "od19.document.bulk.category.wizard"
    _description = "จัดหมวดเอกสารเป็นชุด"

    category_id = fields.Many2one(
        "od19.document.category", "หมวดเอกสาร", required=True, ondelete="restrict",
    )

    def action_apply(self):
        self.ensure_one()
        attachments = self.env["ir.attachment"].browse(
            self.env.context.get("active_ids", []),
        )
        if attachments:
            attachments.write({"od19_category_id": self.category_id.id})
        return {"type": "ir.actions.act_window_close"}
```

`models/__init__.py` — เพิ่มบรรทัด (ให้อยู่หลัง `from . import ir_attachment`)
```python
from . import od19_document_bulk_category
```

- [ ] **Step 4: สร้าง view + ผูกเป็นปุ่มบน list**

`views/od19_document_bulk_category_views.xml`
```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="view_od19_document_bulk_category_form" model="ir.ui.view">
        <field name="name">od19.document.bulk.category.wizard.form</field>
        <field name="model">od19.document.bulk.category.wizard</field>
        <field name="arch" type="xml">
            <form string="จัดหมวดเป็นชุด">
                <group>
                    <field name="category_id"/>
                </group>
                <footer>
                    <button name="action_apply" type="object"
                            string="จัดหมวดให้รายการที่เลือก" class="btn-primary"/>
                    <button string="ยกเลิก" class="btn-secondary" special="cancel"/>
                </footer>
            </form>
        </field>
    </record>

    <record id="action_od19_document_bulk_category" model="ir.actions.act_window">
        <field name="name">จัดหมวดเป็นชุด</field>
        <field name="res_model">od19.document.bulk.category.wizard</field>
        <field name="view_mode">form</field>
        <field name="target">new</field>
        <field name="binding_model_id" ref="base.model_ir_attachment"/>
        <field name="binding_view_types">list</field>
    </record>
</odoo>
```

`__manifest__.py` — เพิ่มบรรทัดนี้ใน `data` **ก่อน** `views/ir_attachment_views.xml`
```python
        "views/od19_document_bulk_category_views.xml",
```

- [ ] **Step 5: เพิ่มสิทธิ์ wizard**

`security/ir.model.access.csv` — ต่อท้าย
```csv
access_od19_document_bulk_category_user,od19.document.bulk.category.wizard.user,model_od19_document_bulk_category_wizard,od19_document_hub.group_document_user,1,1,1,1
access_od19_document_bulk_category_manager,od19.document.bulk.category.wizard.manager,model_od19_document_bulk_category_wizard,od19_document_hub.group_document_manager,1,1,1,1
```

> **บทเรียนจาก P2:** โมเดล TransientModel ต้องมี access rule เสมอ ไม่เช่นนั้น log จะเตือน `have no access rules`

- [ ] **Step 6: รันเทสต์ให้เขียว**

Run: `pwsh -File .\run-tests.ps1 -Module od19_document_hub -Database odoo19_t_doc_search -HttpPort 8083`
Expected: PASS — `0 failed, 0 error(s)` และไม่มี warning `have no access rules`

- [ ] **Step 7: Commit**

```powershell
git add custom_addons/od19_document_hub/models/od19_document_bulk_category.py custom_addons/od19_document_hub/models/__init__.py custom_addons/od19_document_hub/views/od19_document_bulk_category_views.xml custom_addons/od19_document_hub/__manifest__.py custom_addons/od19_document_hub/security/ir.model.access.csv custom_addons/od19_document_hub/tests/test_document_search.py
git commit -m "feat(od19_document_hub): add bulk categorize wizard for library"
```

---

### Task 4: ยืนยันการใช้ดัชนี trigram + ประสิทธิภาพการค้น

**Files:**
- Create: `custom_addons/od19_document_hub/tests/test_document_search_perf.py`
- Modify: `custom_addons/od19_document_hub/tests/__init__.py`

- [ ] **Step 1: เขียนเทสต์ยืนยันดัชนี**

`tests/test_document_search_perf.py`
```python
# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo.tests.common import TransactionCase


class TestDocumentSearchPerf(TransactionCase):
    """ยืนยันว่าดัชนี GIN trigram มีจริงและถูกเลือกใช้เมื่อ seq scan ถูกปิด"""

    def _explain(self, sql, params=None):
        self.env.cr.execute("SET LOCAL enable_seqscan = off")
        self.env.cr.execute("EXPLAIN " + sql, params or ())
        return "\n".join(row[0] for row in self.env.cr.fetchall())

    def test_name_trigram_index_exists(self):
        self.env.cr.execute(
            "SELECT indexdef FROM pg_indexes "
            "WHERE tablename = 'ir_attachment' AND indexdef ILIKE '%gin_trgm_ops%';",
        )
        defs = " ".join(row[0] for row in self.env.cr.fetchall())
        self.assertIn("name", defs)

    def test_content_trigram_index_used(self):
        plan = self._explain(
            "SELECT id FROM od19_document_extract "
            "WHERE text_content ILIKE %s",
            ("%สัญญาจ้างเหมา%",),
        )
        self.assertIn("Index", plan)
        self.assertIn("gin", plan.lower())

    def test_name_trigram_index_used(self):
        plan = self._explain(
            "SELECT id FROM ir_attachment WHERE name ILIKE %s",
            ("%ใบเสร็จ%",),
        )
        self.assertIn("Index", plan)
        self.assertIn("gin", plan.lower())
```

`tests/__init__.py` (เพิ่มบรรทัดต่อท้าย)
```python
from . import test_document_search_perf
```

- [ ] **Step 2: รันเทสต์**

Run: `pwsh -File .\run-tests.ps1 -Module od19_document_hub -Database odoo19_t_doc_search -HttpPort 8083`
Expected: PASS — `0 failed, 0 error(s)`

> ถ้า `test_content_trigram_index_used` ล้มเพราะ planner ยังเลือก seq scan ให้ตรวจว่าดัชนีถูกสร้างจริง (query `pg_indexes` ใน Step 1) — ห้ามแก้ core หรือลดความเข้มของเทสต์โดยไม่มีหลักฐาน

- [ ] **Step 3: Commit**

```powershell
git add custom_addons/od19_document_hub/tests/test_document_search_perf.py custom_addons/od19_document_hub/tests/__init__.py
git commit -m "test(od19_document_hub): assert trigram indexes back content search"
```

---

### Task 5: คำแปลไทย + bump version

**Files:**
- Modify: `custom_addons/od19_document_hub/i18n/th.po`
- Modify: `custom_addons/od19_document_hub/__manifest__.py`

- [ ] **Step 1: เพิ่มคำแปลสตริงใหม่**

เติมต่อท้าย `i18n/th.po` (ก่อนบรรทัดสุดท้ายที่ไม่ใช่คอมเมนต์) โดยให้ msgid ตรงกับสตริงที่เพิ่มจริงใน Task 1–3 เช่น
```po

#. module: od19_document_hub
#: model:ir.model.fields,field_description:od19_document_hub.field_ir_attachment__od19_search_text
msgid "ค้นชื่อ/เนื้อหาไฟล์"
msgstr "ค้นชื่อ/เนื้อหาไฟล์"

#. module: od19_document_hub
#: model:ir.model,name:od19_document_hub.model_od19_document_bulk_category_wizard
msgid "จัดหมวดเอกสารเป็นชุด"
msgstr "จัดหมวดเอกสารเป็นชุด"
```

> หลังรันเทสต์ ให้ใช้ `odoo-bin --i18n-export` ดึง msgid จริงมาเติมให้ครบได้ (ไม่ต้องครบในรอบแรก)

- [ ] **Step 2: bump version**

`__manifest__.py` — เปลี่ยน `"version": "19.0.1.0.0"` เป็น
```python
    "version": "19.0.1.1.0",
```

- [ ] **Step 3: รันเทสต์สุดท้าย**

Run: `pwsh -File .\run-tests.ps1 -Module od19_document_hub -Database odoo19_t_doc_search -HttpPort 8083`
Expected: PASS — `0 failed, 0 error(s)` ไม่มี warning ที่ไม่คาดหมาย

- [ ] **Step 4: Commit**

```powershell
git add custom_addons/od19_document_hub/i18n/th.po custom_addons/od19_document_hub/__manifest__.py
git commit -m "chore(od19_document_hub): add thai terms and bump search version"
```

---

## Self-Review (ตรวจแผนกับสเปก §6–§11)

**1. Spec coverage:**

| สเปก | Task |
|---|---|
| §2.3 R4 ค้นเจอทั้งชื่อไฟล์และข้อความในไฟล์ รวมไทย | Task 1 |
| §6.3 ดัชนี GIN `pg_trgm` บน `name` และ `text_content` | มีแล้ว (P1) + ยืนยันใน Task 4 |
| §7.2 facets: วันที่ · หมวด · คู่ค้า · แผนก · ความลับ · ที่มา · สถานะ index | Task 2 |
| §7.2 ป้าย "ซ้ำ" เมื่อ `checksum` ซ้ำ | Task 2 (`od19_duplicate_count`, group-by `checksum`) |
| §7.2 ปุ่ม "จัดหมวดเป็นชุด" | Task 3 |
| §10 เกณฑ์ผ่าน 0 failed/0 error · ไม่มี warning · ไม่แก้ core | ทุก Task |
| §11 P3 = trigram + facets + ค้นในเนื้อไฟล์ (เป้า 2 ≤ 2 วินาที) | Task 1–4 |

**2. Placeholder scan:** ไม่มี `TBD`/`TODO` — ทุก step มีโค้ด/คำสั่งจริง

**3. Type consistency:**
- ชื่อโมเดล/ฟิลด์/เมธอดตรงกันทุก Task: `od19.document.extract.text_content`, `od19_extract_ids`, `od19_search_text`, `_search_od19_search_text`, `od19.document.bulk.category.wizard`, `action_apply`, `od19_duplicate_count`, `file_size`, `checksum`
- external id ของ binding ใช้ของ core จริง: `base.model_ir_attachment`
- external id ของ model ใหม่ที่ Odoo สร้างอัตโนมัติ: `model_od19_document_bulk_category_wizard`
- view record ที่สืบทอด: `base.view_attachment_search`, `base.view_attachment_tree` (มีใน core)

**ช่องว่างที่รู้ตัว (อยู่นอกแผนนี้โดยเจตนา):**
- record rule ตามความลับ/แผนก → `od19_document_governance` (P4) เพื่อไม่ให้ OR รวมกับ rule ของ core แล้วขยายสิทธิ์
- side panel เปิดดูไฟล์แบบไม่ดาวน์โหลด → ปรับ UX เฉพาะทาง พิจารณาเฟสถัดไป
- การวัดเวลา ≤ 2 วินาทีบนข้อมูลจริง → ทำใน P0 baseline/governance dashboard ไม่ใช่ unit test

---

## Execution Handoff

- เริ่มงานเป็น **Task 1..5 ตามลำดับ** — แต่ละ Task มีเทสต์ก่อนโค้ด (TDD) และ commit เดี่ยวตาม AGENTS.md §4
- **lease:** งานนี้บน DB ทดสอบส่วนตัว `odoo19_t_doc_search` + worktree ของตัวเอง = Tier 0/1 ไม่ต้องจับ lease (ยกเว้นตอน `git worktree add` ซึ่งเป็น Tier 2)
- ก่อน push: `git merge-base --is-ancestor origin/19.0 19.0` (FF-safe) แล้วขออนุมัติรวดเดียวตาม AGENTS.md §5 + ตั้ง `OD19_PUSH_APPROVED=1`
- หลังเสร็จ P3 → ไปต่อ **P4/P5 (`od19_document_governance`)** ตาม §11 โดยเขียนแผนแยกที่ `docs/superpowers/plans/2026-11-11-od19-document-governance.md`
