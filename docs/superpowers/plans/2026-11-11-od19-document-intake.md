# od19_document_intake Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** สร้างโมดูล `od19_document_intake` (P2 · เป้า 4) — กล่องรับเข้าเอกสาร ช่องทางรับเข้า (โฟลเดอร์เฝ้าดู/อีเมล alias/อัปโหลดยกชุด) การสกัดข้อความ (text layer → OCR) และการจัดหมวดด้วยกฎ → AI โดยไม่แตะไฟล์ core

**Architecture:** ต่อยอดจาก `od19_document_hub` (ใช้ `ir.attachment` ชั้น metadata เดิม, `od19.document.category`, `od19.document.extract`, `od19.report.archive.mixin`) เพิ่มโมเดลใหม่ 4 ตัว (`od19.document.channel`, `od19.document.classify.rule`, `od19.document.inbox`, `od19.document.intake.upload.wizard`/line) จัดการงานหนัก (สแกนโฟลเดอร์/สกัดข้อความ/จัดหมวด AI) เป็นคิวผ่าน `ir.cron` ไม่บล็อกผู้ใช้ (D5) และยืนยัน 2 จังหวะในกล่องรับเข้า

**Tech Stack:** Odoo 19 (Python 3), PostgreSQL 16 + `pg_trgm`, `pdfminer.six` (มีแล้ว), OCR เป็นตัวเลือกแบบ guard (`pytesseract`/`pdf2image`), ไคลเอนต์ AI เดิม `od19_ai_assistant.lib.client.chat_completion()`, PowerShell `run-tests.ps1`

**อ้างอิงสเปก:** [2026-11-11-od19-document-hub-design.md](../specs/2026-11-11-od19-document-hub-design.md)

---

## ขอบเขตของแผนนี้

แผนนี้ครอบคลุม **P2 (`od19_document_intake`) เท่านั้น** ตาม §11 ของสเปก

- โมดูลนี้ **depends** `od19_document_hub` + `od19_ai_assistant` (§5.1) — ไม่มี circular เพราะ `od19_ai_assistant` depends แค่ `base_setup`
- อยู่ในขอบเขต: ช่องทางรับเข้า · กล่องรับเข้า (staging) · กฎจัดหมวด · จัดหมวดด้วย AI · สกัดข้อความ (text layer/OCR แบบ pluggable) · cron สแกน/ประมวลผล · Kanban + wizard ยืนยัน/ผูก · อัปโหลดยกชุด
- **นอกขอบเขต (แผนอื่น):**
  - ค้นหา facet + ปรับแต่งตัวค้นภาษาไทยใน UI → P3
  - นโยบายอายุ/บังคับใช้/legal hold/audit/GC/dashboard ตัววัด → `od19_document_governance` (P4/P5)
  - ระบบสร้างรายงานภายใน (mixin) ทำเสร็จใน P1 แล้ว — แผนนี้เพียง **เข้าคิวสกัดข้อความ** ให้ attachment ที่ได้
- **นโยบายไฟล์ซ้ำ** (§14 ทางเลือก ข.): เมื่อ checksum+size ตรงกับของเดิม → **สร้างระเบียนใหม่แต่ชี้ไฟล์เดียวกัน** (core dedupe ชั้นไฟล์ให้แล้ว) บันทึกลง `log` ของ inbox

## ขั้นเตรียมการ (ทำครั้งเดียวก่อนเริ่ม)

- [ ] **เตรียม 1: สร้าง worktree + branch**

> ต้องถือ lease `git:worktree` ก่อน (Tier 2). ถ้าไม่ว่าง ให้รอจนหมดอายุ ห้าม break

```powershell
pwsh -File .\agent-lock.ps1 -Action Acquire -Resource git:worktree -AgentId trae-od19_document_intake -Purpose "create worktree feature/od19_document_intake" -Ttl 600
git worktree add ..\od19_doc_intake -b feature/od19_document_intake 19.0
```

- [ ] **เตรียม 2: ยืนยันว่า `od19_document_hub` + `od19_ai_assistant` ติดตั้งได้บน DB ทดสอบของตัวเอง**

Run:
```powershell
pwsh -File .\run-tests.ps1 -Module od19_document_hub -Database odoo19_t_doc_intake -HttpPort 8082
```
Expected: PASS (เป็นฐานให้ intake ต่อ)

- [ ] **เตรียม 3: ยืนยัน extension `pg_trgm` (ใช้ร่วมกับดัชนีของ hub)**

Run:
```powershell
psql -U odoo -d odoo19_t_doc_intake -c "SELECT extname FROM pg_extension WHERE extname='pg_trgm';"
```
Expected: มีแถว `pg_trgm` (สร้างโดย `pre_init_hook` ของ hub แล้ว)

> **หมายเหตุ AGENT_ID:** ใช้ `trae-od19_document_intake` · DB ทดสอบ `odoo19_t_doc_intake` · พอร์ต `8082` (ไม่ซ้ำกับ hub `8081`)

---

## โครงสร้างไฟล์

```
custom_addons/od19_document_intake/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── od19_document_channel.py           # ช่องทางรับเข้า + สแกนโฟลเดอร์ + cron
│   ├── od19_document_classify_rule.py     # กฎจัดหมวด
│   ├── od19_document_inbox.py             # กล่องรับเข้า (staging) + pipeline + alias
│   ├── ir_attachment.py                   # สกัดข้อความ (text layer → OCR hook)
│   └── od19_document_intake_wizard.py     # wizard ยืนยัน/ผูก + อัปโหลดยกชุด
├── views/
│   ├── od19_document_channel_views.xml
│   ├── od19_document_classify_rule_views.xml
│   ├── od19_document_inbox_views.xml
│   ├── od19_document_intake_wizard_views.xml
│   └── od19_document_intake_menus.xml
├── security/
│   └── ir.model.access.csv
├── data/
│   └── ir_cron_data.xml
├── tests/
│   ├── __init__.py
│   ├── test_document_intake_module.py
│   ├── test_document_intake_rules.py
│   ├── test_document_intake_ai.py
│   └── test_document_intake_extract.py
└── i18n/
    └── th.po
```

**คำสั่งทดสอบที่ใช้ทั้งแผน** (DB ทดสอบส่วนตัวตาม AGENTS.md §6):
```powershell
pwsh -File .\run-tests.ps1 -Module od19_document_intake -Database odoo19_t_doc_intake -HttpPort 8082
```

---

### Task 1: Module skeleton

**Files:**
- Create: `custom_addons/od19_document_intake/__init__.py`
- Create: `custom_addons/od19_document_intake/__manifest__.py`
- Create: `custom_addons/od19_document_intake/models/__init__.py`
- Create: `custom_addons/od19_document_intake/tests/__init__.py`
- Create: `custom_addons/od19_document_intake/tests/test_document_intake_module.py`

- [ ] **Step 1: เขียนไฟล์ package**

`custom_addons/od19_document_intake/__init__.py`
```python
# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from . import models
```

`custom_addons/od19_document_intake/models/__init__.py`
```python
# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
```

`custom_addons/od19_document_intake/tests/__init__.py`
```python
# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from . import test_document_intake_module
```

- [ ] **Step 2: เขียน manifest**

`custom_addons/od19_document_intake/__manifest__.py`
```python
# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

{
    "name": "OD19 Document Intake",
    "version": "19.0.1.0.0",
    "category": "Document Management",
    "summary": "กล่องรับเข้า ช่องทางรับเอกสาร การสกัดข้อความ และการจัดหมวดด้วยกฎ/AI",
    "author": "TRAE",
    "license": "LGPL-3",
    "depends": ["od19_document_hub", "od19_ai_assistant"],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_cron_data.xml",
        "views/od19_document_channel_views.xml",
        "views/od19_document_classify_rule_views.xml",
        "views/od19_document_inbox_views.xml",
        "views/od19_document_intake_wizard_views.xml",
        "views/od19_document_intake_menus.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
```

- [ ] **Step 3: เขียน smoke test (ยังต้องล้มเหลว)**

`custom_addons/od19_document_intake/tests/test_document_intake_module.py`
```python
# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDocumentIntakeModule(TransactionCase):
    """ตรวจว่าโมดูลติดตั้งได้ และ dependency พร้อม"""

    def test_models_registered(self):
        for model in (
            "od19.document.channel",
            "od19.document.classify.rule",
            "od19.document.inbox",
        ):
            self.assertIn(model, self.env)

    def test_hub_dependency_available(self):
        # ต้องใช้ของ hub ได้ (หมวด + extract)
        self.assertIn("od19.document.category", self.env)
        self.assertIn("od19.document.extract", self.env)
```

- [ ] **Step 4: รันเทสต์เพื่อยืนยันว่า FAIL**

Run: `pwsh -File .\run-tests.ps1 -Module od19_document_intake -Database odoo19_t_doc_intake -HttpPort 8082`
Expected: FAIL — ยังไม่มีโมเดล `od19.document.channel` (AccessError/KeyError)

- [ ] **Step 5: ยืนยัน manifest โหลดผ่าน (ยังไม่ต้องติดตั้งจริง)**

Run:
```powershell
python -c "import ast,io; ast.parse(io.open(r'custom_addons/od19_document_intake/__manifest__.py',encoding='utf-8').read())"
```
Expected: ไม่มี error (syntax ถูก)

- [ ] **Step 6: Commit**

```powershell
git add custom_addons/od19_document_intake/__init__.py custom_addons/od19_document_intake/__manifest__.py custom_addons/od19_document_intake/models/__init__.py custom_addons/od19_document_intake/tests/__init__.py custom_addons/od19_document_intake/tests/test_document_intake_module.py
git commit -m "feat(od19_document_intake): add module skeleton"
```

---

### Task 2: สิทธิ์เข้าถึงโมเดล (ใช้กลุ่มของ hub)

**Files:**
- Create: `custom_addons/od19_document_intake/security/ir.model.access.csv`

- [ ] **Step 1: เขียน access csv**

**ใช้กลุ่มเดิมของ hub** (`od19_document_hub.group_document_user` / `group_document_manager`) ไม่สร้างกลุ่มใหม่ เพื่อไม่ให้สิทธิ์ซ้ำซ้อน (สเปก §7.6)

`custom_addons/od19_document_intake/security/ir.model.access.csv`
```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_od19_document_channel_user,od19.document.channel.user,model_od19_document_channel,od19_document_hub.group_document_user,1,1,1,0
access_od19_document_channel_manager,od19.document.channel.manager,model_od19_document_channel,od19_document_hub.group_document_manager,1,1,1,1
access_od19_document_classify_rule_user,od19.document.classify.rule.user,model_od19_document_classify_rule,od19_document_hub.group_document_user,1,0,0,0
access_od19_document_classify_rule_manager,od19.document.classify.rule.manager,model_od19_document_classify_rule,od19_document_hub.group_document_manager,1,1,1,1
access_od19_document_inbox_user,od19.document.inbox.user,model_od19_document_inbox,od19_document_hub.group_document_user,1,1,1,0
access_od19_document_inbox_manager,od19.document.inbox.manager,model_od19_document_inbox,od19_document_hub.group_document_manager,1,1,1,1
```

> **หมายเหตุ:** wizard (TransientModel) ไม่ต้องใส่ access csv — Odoo ให้สิทธิ์ตามผู้ใช้ที่ล็อกอินอยู่แล้ว

- [ ] **Step 2: รันเทสต์**

Run: `pwsh -File .\run-tests.ps1 -Module od19_document_intake -Database odoo19_t_doc_intake -HttpPort 8082`
Expected: ยัง FAIL (โมเดลยังไม่มี) — access csv ถูกตรวจว่า parse ได้ตอนติดตั้ง

- [ ] **Step 3: Commit**

```powershell
git add custom_addons/od19_document_intake/security/ir.model.access.csv
git commit -m "feat(od19_document_intake): add model access rights using hub groups"
```

---

### Task 3: โมเดล `od19.document.channel` + สแกนโฟลเดอร์

**Files:**
- Create: `custom_addons/od19_document_intake/models/od19_document_channel.py`
- Modify: `custom_addons/od19_document_intake/models/__init__.py`

- [ ] **Step 1: เขียนโมเดล**

`custom_addons/od19_document_intake/models/od19_document_channel.py`
```python
# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import base64
import hashlib
import logging
import os

from odoo import api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

KIND_SELECTION = [
    ("folder", "โฟลเดอร์เฝ้าดู"),
    ("email_alias", "อีเมล (Alias)"),
    ("portal", "พอร์ทัล / อัปโหลด"),
]


class Od19DocumentChannel(models.Model):
    _name = "od19.document.channel"
    _description = "ช่องทางรับเอกสารเข้า"
    _order = "sequence, name"

    name = fields.Char("ชื่อช่องทาง", required=True)
    sequence = fields.Integer(default=10)
    kind = fields.Selection(KIND_SELECTION, "ประเภท", required=True, default="portal")
    path = fields.Char(
        "พาธโฟลเดอร์",
        help=r"พาธในเครื่องหรือ network share เช่น D:\Intake หรือ \\server\docs",
    )
    alias_id = fields.Many2one(
        "mail.alias", "อีเมล Alias", ondelete="restrict",
        help="Alias ที่ตั้ง Alias Model = od19.document.inbox",
    )
    default_category_id = fields.Many2one(
        "od19.document.category", "หมวดเริ่มต้น", ondelete="restrict",
        help="ใช้เมื่อกฎและ AI ไม่สรุปได้ (ยังไม่ถึงเกณฑ์ confidence)",
    )
    enable_ocr = fields.Boolean("เปิด OCR", default=True)
    enable_ai = fields.Boolean("เปิดจัดหมวดด้วย AI", default=True)
    active = fields.Boolean(default=True)
    last_scan_at = fields.Datetime("สแกนล่าสุด", readonly=True)
    last_error = fields.Text("ข้อผิดพลาดล่าสุด", readonly=True)

    @api.constrains("kind", "path", "alias_id")
    def _check_kind_config(self):
        for channel in self:
            if channel.kind == "folder" and not channel.path:
                raise ValidationError("ช่องทาง 'โฟลเดอร์เฝ้าดู' ต้องระบุพาธโฟลเดอร์")
            if channel.kind == "email_alias" and not channel.alias_id:
                raise ValidationError("ช่องทาง 'อีเมล (Alias)' ต้องผูก Alias")

    # ------------------------------------------------------------------
    # Folder scanning + cron
    # ------------------------------------------------------------------
    def _od19_scan_channel(self):
        """สแกนโฟลเดอร์ของช่องทางนี้ แล้วสร้าง inbox สำหรับไฟล์ใหม่"""
        self.ensure_one()
        created = 0
        if self.kind != "folder" or not self.path:
            return created
        if not os.path.isdir(self.path):
            self.last_error = "ไม่พบโฟลเดอร์: %s" % self.path
            return created

        Inbox = self.env["od19.document.inbox"]
        for filename in sorted(os.listdir(self.path)):
            filepath = os.path.join(self.path, filename)
            if not os.path.isfile(filepath):
                continue
            try:
                with open(filepath, "rb") as handle:
                    data = handle.read()
            except OSError as exc:
                self.last_error = "อ่านไฟล์ %s ไม่ได้: %s" % (filename, exc)
                continue
            checksum = hashlib.sha1(data).hexdigest()
            already = Inbox.search_count([
                ("channel_id", "=", self.id), ("checksum", "=", checksum),
            ])
            if already:
                continue
            Inbox.create({
                "name": filename[:200],
                "filename": filename[:200],
                "file": base64.b64encode(data),
                "checksum": checksum,
                "channel_id": self.id,
                "state": "new",
            })
            created += 1

        self.last_scan_at = fields.Datetime.now()
        self.last_error = False
        return created

    @api.model
    def _cron_scan_channels(self):
        """cron: ไล่ทุกช่องทางโฟลเดอร์ — ถ้าช่องทางใดล้ม ต้องไม่ทำให้ cron ทั้งรอบล้ม"""
        for channel in self.search([("kind", "=", "folder"), ("active", "=", True)]):
            try:
                channel._od19_scan_channel()
            except Exception as exc:  # noqa: BLE001 — guard ต่อช่องทางตามสเปก §9
                _logger.exception("od19_document_intake: สแกนช่องทาง %s ล้มเหลว", channel.name)
                channel.last_error = "สแกนล้มเหลว: %s" % exc
```

- [ ] **Step 2: เปิด import**

`custom_addons/od19_document_intake/models/__init__.py`
```python
# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from . import od19_document_channel
```

- [ ] **Step 3: รันเทสต์เพื่อยืนยันว่า PASS (smoke ผ่าน)**

Run: `pwsh -File .\run-tests.ps1 -Module od19_document_intake -Database odoo19_t_doc_intake -HttpPort 8082`
Expected: ยัง FAIL ที่ `od19.document.classify.rule`/`inbox` (จาก smoke test) — แต่ `od19.document.channel` ถูกสร้างแล้ว (ตรวจจาก traceback ว่าไม่ใช่ channel อีกต่อไป)

- [ ] **Step 4: Commit**

```powershell
git add custom_addons/od19_document_intake/models/od19_document_channel.py custom_addons/od19_document_intake/models/__init__.py
git commit -m "feat(od19_document_intake): add document channel model with folder scan"
```

---

### Task 4: โมเดล `od19.document.classify.rule`

**Files:**
- Create: `custom_addons/od19_document_intake/models/od19_document_classify_rule.py`
- Modify: `custom_addons/od19_document_intake/models/__init__.py`

- [ ] **Step 1: เขียนโมเดล**

`custom_addons/od19_document_intake/models/od19_document_classify_rule.py`
```python
# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields, models

TARGET_SELECTION = [
    ("filename", "ชื่อไฟล์"),
    ("text", "ข้อความในไฟล์"),
    ("partner", "ชื่อคู่ค้า"),
]


class Od19DocumentClassifyRule(models.Model):
    _name = "od19.document.classify.rule"
    _description = "กฎจัดหมวดเอกสารอัตโนมัติ"
    _order = "sequence, id"

    name = fields.Char("ชื่อกฎ", required=True)
    sequence = fields.Integer(default=10)
    target = fields.Selection(TARGET_SELECTION, "ตรวจจาก", required=True, default="filename")
    pattern = fields.Char(
        "คำ/รูปแบบ", required=True,
        help="ข้อความ (ไม่สนตัวพิมพ์) — ใช้ find ในเป้าหมายที่เลือก ไม่ใช้ regex",
    )
    category_id = fields.Many2one(
        "od19.document.category", "หมวดที่ได้", required=True, ondelete="cascade",
    )
    partner_id = fields.Many2one("res.partner", "คู่ค้าที่ได้", ondelete="set null")
    active = fields.Boolean(default=True)
```

- [ ] **Step 2: เปิด import**

`custom_addons/od19_document_intake/models/__init__.py`
```python
# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from . import od19_document_channel
from . import od19_document_classify_rule
```

- [ ] **Step 3: Commit**

```powershell
git add custom_addons/od19_document_intake/models/od19_document_classify_rule.py custom_addons/od19_document_intake/models/__init__.py
git commit -m "feat(od19_document_intake): add classification rule model"
```

---

### Task 5: โมเดล `od19.document.inbox` (fields + alias)

**Files:**
- Create: `custom_addons/od19_document_intake/models/od19_document_inbox.py`
- Modify: `custom_addons/od19_document_intake/models/__init__.py`

- [ ] **Step 1: เขียนโมเดล (โครง + alias + helper คำนวณ checksum)**

`custom_addons/od19_document_intake/models/od19_document_inbox.py`
```python
# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import base64
import hashlib
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

STATE_SELECTION = [
    ("new", "ใหม่"),
    ("processing", "กำลังประมวลผล"),
    ("to_review", "รอตรวจ"),
    ("linked", "ผูกแล้ว"),
    ("rejected", "ปฏิเสธ"),
    ("failed", "ผิดพลาด"),
]

CLASSIFY_METHOD_SELECTION = [
    ("rule", "กฎ"),
    ("ai", "AI"),
    ("manual", "คน"),
]

# เกณฑ์ผูกอัตโนมัติตามสเปก §8.1
CONFIDENCE_THRESHOLD = 70.0


class Od19DocumentInbox(models.Model):
    _name = "od19.document.inbox"
    _description = "กล่องรับเข้าเอกสาร (staging)"
    _inherit = ["mail.thread"]
    _order = "create_date desc, id desc"

    name = fields.Char("ชื่อเรื่อง", required=True, default="เอกสารเข้า", tracking=True)
    file = fields.Binary("ไฟล์", attachment=True)
    filename = fields.Char("ชื่อไฟล์")
    checksum = fields.Char("Checksum (SHA1)", index=True)
    channel_id = fields.Many2one(
        "od19.document.channel", "ช่องทาง", ondelete="set null", index=True,
    )
    state = fields.Selection(
        STATE_SELECTION, "สถานะ", default="new", required=True,
        tracking=True, index=True,
    )
    suggested_category_id = fields.Many2one(
        "od19.document.category", "หมวดที่เสนอ", ondelete="set null",
    )
    suggested_partner_id = fields.Many2one(
        "res.partner", "คู่ค้าที่เสนอ", ondelete="set null",
    )
    confidence = fields.Float("ความมั่นใจ (%)", digits=(5, 2))
    classify_method = fields.Selection(
        CLASSIFY_METHOD_SELECTION, "วิธีจัดหมวด", readonly=True,
    )
    attachment_id = fields.Many2one(
        "ir.attachment", "เอกสารแนบที่ผูก", ondelete="set null", readonly=True,
    )
    res_model = fields.Char("โมเดลปลายทาง", readonly=True)
    res_id = fields.Integer("รหัสปลายทาง", readonly=True)
    log = fields.Text("บันทึกการประมวลผล", readonly=True)

    _checksum_idx = models.Index("(checksum)")

    # ------------------------------------------------------------------
    # Email alias (sh่องทางอีเมล) — alias ตั้ง Alias Model = od19.document.inbox
    # ------------------------------------------------------------------
    @api.model
    def message_new(self, msg_dict, custom_values=None):
        values = dict(custom_values or {})
        subject = (msg_dict.get("subject") or "อีเมลเข้า").strip()
        values.setdefault("name", subject[:200])
        inbox = super().message_new(msg_dict, values)
        # ไฟล์แนบของอีเมลถูก mail.thread ผูกกับตัวระเบียนแล้ว — ใช้ไฟล์แรกเป็น staging
        attachment = self.env["ir.attachment"].search([
            ("res_model", "=", self._name), ("res_id", "=", inbox.id),
        ], limit=1)
        if attachment:
            inbox.write({
                "file": attachment.datas,
                "filename": attachment.name,
                "checksum": attachment.checksum,
            })
        return inbox

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _od19_compute_checksum(self):
        self.ensure_one()
        if self.checksum or not self.file:
            return self.checksum
        raw = self.file
        if isinstance(raw, str):
            raw = base64.b64decode(raw)
        self.checksum = hashlib.sha1(raw).hexdigest()
        return self.checksum

    def action_reject(self):
        self.write({"state": "rejected"})
```

- [ ] **Step 2: เปิด import**

`custom_addons/od19_document_intake/models/__init__.py`
```python
# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from . import od19_document_channel
from . import od19_document_classify_rule
from . import od19_document_inbox
```

- [ ] **Step 3: รันเทสต์ smoke เพื่อยืนยันว่า PASS**

Run: `pwsh -File .\run-tests.ps1 -Module od19_document_intake -Database odoo19_t_doc_intake -HttpPort 8082`
Expected: PASS — smoke test Task 1 ผ่านครบ (โมเดลทั้ง 3 ลงทะเบียนแล้ว)

- [ ] **Step 4: Commit**

```powershell
git add custom_addons/od19_document_intake/models/od19_document_inbox.py custom_addons/od19_document_intake/models/__init__.py
git commit -m "feat(od19_document_intake): add inbox staging model with alias support"
```

---

### Task 6: เครื่องยนต์กฎจัดหมวด (rules)

**Files:**
- Modify: `custom_addons/od19_document_intake/models/od19_document_inbox.py`
- Create: `custom_addons/od19_document_intake/tests/test_document_intake_rules.py`

- [ ] **Step 1: เขียนเทสต์ที่ล้มเหลว**

`custom_addons/od19_document_intake/tests/test_document_intake_rules.py`
```python
# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import base64

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestIntakeRules(TransactionCase):

    def setUp(self):
        super().setUp()
        self.category = self.env["od19.document.category"].create({
            "name": "ใบกำกับภาษีซื้อ", "code": "PUR_TAX",
        })
        self.channel = self.env["od19.document.channel"].create({
            "name": "พอร์ทัล", "kind": "portal",
        })

    def _make_inbox(self, name, text=None):
        return self.env["od19.document.inbox"].create({
            "name": name,
            "filename": name,
            "file": base64.b64encode((text or "x").encode("utf-8")),
            "channel_id": self.channel.id,
        })

    def test_rule_by_filename(self):
        self.env["od19.document.classify.rule"].create({
            "name": "ชื่อไฟล์มีคำว่า TAX",
            "target": "filename", "pattern": "tax", "category_id": self.category.id,
        })
        inbox = self._make_inbox("INV-TAX-2569.pdf")
        category, partner, confidence, method = inbox._od19_classify_by_rules()
        self.assertEqual(category, self.category)
        self.assertEqual(method, "rule")

    def test_rule_no_match_returns_empty(self):
        inbox = self._make_inbox("random.pdf")
        category, partner, confidence, method = inbox._od19_classify_by_rules()
        self.assertFalse(category)

    def test_rule_case_insensitive(self):
        self.env["od19.document.classify.rule"].create({
            "name": "PO", "target": "filename", "pattern": "po",
            "category_id": self.category.id,
        })
        inbox = self._make_inbox("PO-2601.pdf")
        category, _partner, _conf, method = inbox._od19_classify_by_rules()
        self.assertEqual(category, self.category)
```

- [ ] **Step 2: รันเทสต์เพื่อยืนยันว่า FAIL**

Run: `pwsh -File .\run-tests.ps1 -Module od19_document_intake -Database odoo19_t_doc_intake -HttpPort 8082`
Expected: FAIL — ยังไม่มีเมธอด `_od19_classify_by_rules`

- [ ] **Step 3: เพิ่มเมธอดจัดหมวดตามกฎ**

เพิ่มใน `custom_addons/od19_document_intake/models/od19_document_inbox.py` ภายในคลาส `Od19DocumentInbox` (ต่อจาก `action_reject`)
```python
    def _od19_rule_target_value(self, target, attachment=None):
        self.ensure_one()
        if target == "filename":
            return (self.filename or self.name or "").lower()
        if target == "partner":
            return (self.suggested_partner_id.name or "").lower()
        if target == "text" and attachment:
            extract = self.env["od19.document.extract"].search(
                [("attachment_id", "=", attachment.id)], limit=1,
            )
            return (extract.text_content or "").lower()
        return ""

    def _od19_classify_by_rules(self, attachment=None):
        """คืน (category, partner, confidence, method) หรือ (False, False, 0.0, 'rule')"""
        self.ensure_one()
        rules = self.env["od19.document.classify.rule"].search(
            [("active", "=", True)], order="sequence, id",
        )
        for rule in rules:
            haystack = self._od19_rule_target_value(rule.target, attachment)
            if haystack and rule.pattern.lower() in haystack:
                return rule.category_id, rule.partner_id, 100.0, "rule"
        empty = self.env["od19.document.category"]
        return empty, self.env["res.partner"], 0.0, "rule"
```

- [ ] **Step 4: รันเทสต์เพื่อยืนยันว่า PASS**

Run: `pwsh -File .\run-tests.ps1 -Module od19_document_intake -Database odoo19_t_doc_intake -HttpPort 8082`
Expected: PASS — `TestIntakeRules` ผ่าน 3 เคส

- [ ] **Step 5: Commit**

```powershell
git add custom_addons/od19_document_intake/models/od19_document_inbox.py custom_addons/od19_document_intake/tests/test_document_intake_rules.py
git commit -m "feat(od19_document_intake): add rule based classification"
```

---

### Task 7: จัดหมวดด้วย AI (mock test)

**Files:**
- Modify: `custom_addons/od19_document_intake/models/od19_document_inbox.py`
- Create: `custom_addons/od19_document_intake/tests/test_document_intake_ai.py`

- [ ] **Step 1: เขียนเทสต์ที่ล้มเหลว (mock `chat_completion`)**

`custom_addons/od19_document_intake/tests/test_document_intake_ai.py`
```python
# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import base64
from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.od19_ai_assistant.lib.client import AiClientError


@tagged("post_install", "-at_install")
class TestIntakeAi(TransactionCase):

    def setUp(self):
        super().setUp()
        self.category = self.env["od19.document.category"].create({
            "name": "ใบเสร็จรับเงิน", "code": "SAL_RECEIPT",
        })
        self.channel = self.env["od19.document.channel"].create({
            "name": "พอร์ทัล", "kind": "portal", "enable_ai": True,
        })
        self.inbox = self.env["od19.document.inbox"].create({
            "name": "receipt.pdf", "filename": "receipt.pdf",
            "file": base64.b64encode(b"receipt thai text"),
            "channel_id": self.channel.id,
        })

    def test_ai_returns_category(self):
        answer = '{"category_code": "SAL_RECEIPT", "confidence": 88}'
        with patch(
            "odoo.addons.od19_document_intake.models.od19_document_inbox.chat_completion",
            return_value=answer,
        ):
            category, _partner, confidence, method = self.inbox._od19_classify_with_ai()
        self.assertEqual(category, self.category)
        self.assertEqual(confidence, 88.0)
        self.assertEqual(method, "ai")

    def test_ai_endpoint_error_is_swallowed(self):
        with patch(
            "odoo.addons.od19_document_intake.models.od19_document_inbox.chat_completion",
            side_effect=AiClientError("boom"),
        ):
            category, _partner, confidence, method = self.inbox._od19_classify_with_ai()
        self.assertFalse(category)
        self.assertEqual(confidence, 0.0)
        self.assertEqual(method, "ai")

    def test_ai_unknown_category_is_ignored(self):
        answer = '{"category_code": "NOPE", "confidence": 95}'
        with patch(
            "odoo.addons.od19_document_intake.models.od19_document_inbox.chat_completion",
            return_value=answer,
        ):
            category, _partner, _conf, _method = self.inbox._od19_classify_with_ai()
        self.assertFalse(category)
```

- [ ] **Step 2: รันเทสต์เพื่อยืนยันว่า FAIL**

Run: `pwsh -File .\run-tests.ps1 -Module od19_document_intake -Database odoo19_t_doc_intake -HttpPort 8082`
Expected: FAIL — ยังไม่มีเมธอด `_od19_classify_with_ai` และยังไม่ import `chat_completion`

- [ ] **Step 3: เพิ่มโค้ดเรียก AI**

ที่หัวไฟล์ `custom_addons/od19_document_intake/models/od19_document_inbox.py` เพิ่ม import
```python
import json
import re

from odoo.addons.od19_ai_assistant.lib.client import AiClientError, chat_completion
```

> **หมายเหตุ path:** `od19_document_intake` **ไม่ใช่เจ้าของ** `lib/client.py` — ต้อง import จากโมดูล AI เต็มเส้น
> (`from odoo.addons.od19_ai_assistant.lib.client import ...`) เท่านั้น ห้ามใช้ `from ..lib.client`
> เพื่อให้ `patch()` ในเทสต์ชี้ที่ `odoo.addons.od19_document_intake.models.od19_document_inbox.chat_completion` ได้ถูกต้อง

เพิ่มเมธอดในคลาส `Od19DocumentInbox`
```python
    _AI_SYSTEM_PROMPT = (
        "คุณเป็นผู้ช่วยจัดหมวดเอกสารของบริษัทไทย "
        "ตอบกลับเป็น JSON เท่านั้นตามรูปแบบ "
        '{"category_code": "<รหัสหมวด>", "confidence": <0-100>}'
    )

    def _od19_classify_with_ai(self):
        """จัดหมวดด้วย AI — คืน (category, partner, confidence, 'ai') หรือค่าว่างเมื่อล้ม"""
        self.ensure_one()
        empty_category = self.env["od19.document.category"]
        empty_partner = self.env["res.partner"]

        categories = self.env["od19.document.category"].search(
            [("auto_classify", "=", True)], limit=50,
        )
        if not categories:
            return empty_category, empty_partner, 0.0, "ai"

        code_list = "\n".join("- %s: %s" % (c.code, c.name) for c in categories)
        sample = (self.filename or self.name or "")[:200]
        config = self.env["od19.ai.chat"]._get_ai_config()
        messages = [
            {"role": "system", "content": self._AI_SYSTEM_PROMPT},
            {"role": "user", "content": (
                "ชื่อไฟล์: %s\nหมวดที่มี:\n%s\n"
                "เลือกหมวดที่เหมาะสมที่สุด" % (sample, code_list)
            )},
        ]
        try:
            answer = chat_completion(
                config["base_url"], config["model"], messages,
                api_key=config.get("api_key"), timeout=config.get("timeout", 60),
            )
        except AiClientError as exc:
            _logger.warning("od19_document_intake: AI จัดหมวดไม่สำเร็จ: %s", exc)
            return empty_category, empty_partner, 0.0, "ai"

        match = re.search(r"\{.*\}", answer or "", re.DOTALL)
        if not match:
            return empty_category, empty_partner, 0.0, "ai"
        try:
            payload = json.loads(match.group(0))
        except ValueError:
            return empty_category, empty_partner, 0.0, "ai"

        category = categories.filtered(
            lambda c: c.code == str(payload.get("category_code", "")).strip()
        )[:1]
        if not category:
            return empty_category, empty_partner, 0.0, "ai"
        try:
            confidence = float(payload.get("confidence") or 0.0)
        except (TypeError, ValueError):
            confidence = 0.0
        return category, empty_partner, confidence, "ai"
```

- [ ] **Step 4: รันเทสต์เพื่อยืนยันว่า PASS**

Run: `pwsh -File .\run-tests.ps1 -Module od19_document_intake -Database odoo19_t_doc_intake -HttpPort 8082`
Expected: PASS — `TestIntakeAi` ผ่าน 3 เคส (mock ล้วน ไม่ต่อเน็ต)

- [ ] **Step 5: Commit**

```powershell
git add custom_addons/od19_document_intake/models/od19_document_inbox.py custom_addons/od19_document_intake/tests/test_document_intake_ai.py
git commit -m "feat(od19_document_intake): add AI based classification"
```

---

### Task 8: สกัดข้อความ (text layer → OCR hook) บน `ir.attachment`

**Files:**
- Create: `custom_addons/od19_document_intake/models/ir_attachment.py`
- Modify: `custom_addons/od19_document_intake/models/__init__.py`
- Create: `custom_addons/od19_document_intake/tests/test_document_intake_extract.py`

- [ ] **Step 1: เขียนเทสต์ที่ล้มเหลว**

`custom_addons/od19_document_intake/tests/test_document_intake_extract.py`
```python
# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import base64

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestIntakeExtract(TransactionCase):

    def _make_attachment(self, name, mimetype, content):
        return self.env["ir.attachment"].create({
            "name": name, "mimetype": mimetype,
            "datas": base64.b64encode(content),
        })

    def test_extract_plain_text(self):
        attachment = self._make_attachment(
            "note.txt", "text/plain", "ใบเสร็จรับเงิน ค่าบริการ".encode("utf-8"),
        )
        extract = attachment._od19_run_extraction()
        self.assertTrue(extract)
        self.assertIn("ค่าบริการ", extract.text_content)
        self.assertEqual(attachment.od19_index_state, "done")

    def test_extract_empty_content_creates_no_record(self):
        attachment = self._make_attachment("empty.txt", "text/plain", b"")
        extract = attachment._od19_run_extraction()
        self.assertFalse(extract)
        self.assertIn(attachment.od19_index_state, ("skipped", "done"))

    def test_extract_unsupported_mimetype_is_skipped(self):
        attachment = self._make_attachment(
            "photo.xyz", "application/octet-stream", b"\x00\x01\x02",
        )
        attachment._od19_run_extraction()
        self.assertEqual(attachment.od19_index_state, "skipped")

    def test_extract_large_file_is_skipped(self):
        content = b"a" * (26 * 1024 * 1024)  # เกิน MAX_EXTRACT_SIZE (25 MB)
        attachment = self._make_attachment("big.txt", "text/plain", content)
        attachment._od19_run_extraction()
        self.assertEqual(attachment.od19_index_state, "skipped")
```

- [ ] **Step 2: รันเทสต์เพื่อยืนยันว่า FAIL**

Run: `pwsh -File .\run-tests.ps1 -Module od19_document_intake -Database odoo19_t_doc_intake -HttpPort 8082`
Expected: FAIL — ยังไม่มีเมธอด `_od19_run_extraction`

- [ ] **Step 3: เขียนส่วนขยาย `ir.attachment`**

`custom_addons/od19_document_intake/models/ir_attachment.py`
```python
# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import io
import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)

# ข้ามการสกัดเมื่อไฟล์ใหญ่เกิน (กันหน่วยความจำ/timeout) — สเปก §9
MAX_EXTRACT_SIZE = 25 * 1024 * 1024
TEXT_MIMETYPES = ("text/plain", "text/csv", "text/html", "application/json")


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    def _od19_extract_text(self):
        """คืน (text, engine) — engine เป็น None เมื่อสกัดไม่ได้"""
        self.ensure_one()
        mimetype = (self.mimetype or "").lower()
        raw = self.raw or b""

        if mimetype in TEXT_MIMETYPES:
            return raw.decode("utf-8", "replace"), "core"
        if mimetype == "application/pdf":
            try:
                from pdfminer.high_level import extract_text
            except ImportError:  # pragma: no cover — มีใน requirements-od19.txt
                return "", None
            try:
                text = extract_text(io.BytesIO(raw))
            except Exception as exc:  # noqa: BLE001 — ไฟล์ PDF เสียหายต้องไม่ทำให้ cron ล้ม
                _logger.warning("od19_document_intake: สกัด PDF ไม่ได้ (%s): %s", self.name, exc)
                return "", None
            return text or "", "pdfminer"
        return "", None

    def _od19_ocr_text(self):
        """OCR เป็นตัวเลือก — คืน '' เมื่อไม่มี engine (ไม่ทำให้ติดตั้งล้ม)"""
        self.ensure_one()
        try:
            import pytesseract  # noqa: F401
            from pdf2image import convert_from_bytes
        except ImportError:
            _logger.info(
                "od19_document_intake: ไม่มี OCR engine — ข้ามการ OCR ไฟล์ %s", self.name,
            )
            return ""
        try:
            import pytesseract
            pages = convert_from_bytes(self.raw or b"")
            return "\n".join(pytesseract.image_to_string(p) for p in pages)
        except Exception as exc:  # noqa: BLE001
            _logger.warning("od19_document_intake: OCR ล้มเหลว (%s): %s", self.name, exc)
            return ""

    def _od19_run_extraction(self, channel=None):
        """สกัดข้อความ → เขียน od19.document.extract → ปรับ od19_index_state"""
        self.ensure_one()
        if self.file_size and self.file_size > MAX_EXTRACT_SIZE:
            self.od19_index_state = "skipped"
            return self.env["od19.document.extract"]

        text, engine = self._od19_extract_text()
        if not text and engine is None and channel and channel.enable_ocr:
            text, engine = self._od19_ocr_text(), "manual"
        if not text:
            self.od19_index_state = "skipped"
            return self.env["od19.document.extract"]

        extract = self.env["od19.document.extract"].create({
            "attachment_id": self.id,
            "text_content": text,
            "engine": engine or "manual",
            "lang": "th",
        })
        self.write({
            "od19_index_state": "done",
            "od19_indexed_at": fields.Datetime.now(),
        })
        return extract
```

- [ ] **Step 4: เปิด import**

`custom_addons/od19_document_intake/models/__init__.py`
```python
# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from . import od19_document_channel
from . import od19_document_classify_rule
from . import od19_document_inbox
from . import ir_attachment
```

- [ ] **Step 5: รันเทสต์เพื่อยืนยันว่า PASS**

Run: `pwsh -File .\run-tests.ps1 -Module od19_document_intake -Database odoo19_t_doc_intake -HttpPort 8082`
Expected: PASS — `TestIntakeExtract` ผ่าน 4 เคส

- [ ] **Step 6: Commit**

```powershell
git add custom_addons/od19_document_intake/models/ir_attachment.py custom_addons/od19_document_intake/models/__init__.py custom_addons/od19_document_intake/tests/test_document_intake_extract.py
git commit -m "feat(od19_document_intake): add text extraction with pluggable OCR hook"
```

---

### Task 9: Pipeline ประมวลผล + wizard ยืนยัน/ผูก + อัปโหลดยกชุด

**Files:**
- Modify: `custom_addons/od19_document_intake/models/od19_document_inbox.py`
- Create: `custom_addons/od19_document_intake/models/od19_document_intake_wizard.py`
- Modify: `custom_addons/od19_document_intake/models/__init__.py`

- [ ] **Step 1: เพิ่ม pipeline + สร้าง attachment บน `od19.document.inbox`**

เพิ่มใน `custom_addons/od19_document_intake/models/od19_document_inbox.py`
```python
    # ------------------------------------------------------------------
    # Pipeline
    # ------------------------------------------------------------------
    def _od19_create_attachment(self, category=None, res_model=None, res_id=None):
        """สร้าง ir.attachment จริงจากไฟล์ในกล่องรับเข้า แล้วปรับสถานะเป็น linked"""
        self.ensure_one()
        category = category or self.suggested_category_id or self.channel_id.default_category_id
        attachment = self.env["ir.attachment"].create({
            "name": self.filename or self.name,
            "datas": self.file,
            "res_model": res_model or self.res_model or False,
            "res_id": res_id or self.res_id or 0,
            "od19_origin": "external",
            "od19_category_id": category.id if category else False,
            "od19_partner_id": self.suggested_partner_id.id if self.suggested_partner_id else False,
            "od19_doc_date": fields.Date.context_today(self),
            "od19_index_state": "pending",
        })
        self.write({
            "attachment_id": attachment.id,
            "res_model": res_model or self.res_model,
            "res_id": res_id or self.res_id,
            "state": "linked",
        })
        return attachment

    def _od19_classify(self, attachment=None):
        """คืน (category, partner, confidence, method) — กฎก่อน แล้วค่อย AI"""
        self.ensure_one()
        category, partner, confidence, method = self._od19_classify_by_rules(attachment)
        if category:
            return category, partner, confidence, method
        if self.channel_id.enable_ai:
            category, partner, confidence, method = self._od19_classify_with_ai()
            if category:
                return category, partner, confidence, method
        default = self.channel_id.default_category_id
        if default:
            return default, self.env["res.partner"], 50.0, "rule"
        return self.env["od19.document.category"], self.env["res.partner"], 0.0, "rule"

    def _od19_process(self):
        """ประมวลผลรายการเดียว — ตรวจ MIME/ขนาด → checksum → จัดหมวด → ตัดสินใจ"""
        self.ensure_one()
        if self.state not in ("new", "failed"):
            return
        self.state = "processing"
        lines = []
        try:
            self._od19_compute_checksum()
            category, partner, confidence, method = self._od19_classify()
            self.write({
                "suggested_category_id": category.id if category else False,
                "suggested_partner_id": partner.id if partner else False,
                "confidence": confidence,
                "classify_method": method,
            })
            if category and confidence >= CONFIDENCE_THRESHOLD:
                attachment = self._od19_create_attachment(category)
                attachment._od19_run_extraction(self.channel_id)
                lines.append("ผูกอัตโนมัติด้วย %s (%.1f%%)" % (method, confidence))
            else:
                self.state = "to_review"
                lines.append("รอคนยืนยัน (%.1f%%)" % confidence)
        except Exception as exc:  # noqa: BLE001 — ต้องไม่ทำให้ cron ล้ม
            _logger.exception("od19_document_intake: ประมวลผล inbox %s ล้มเหลว", self.id)
            self.state = "failed"
            lines.append("ผิดพลาด: %s" % exc)
        self.log = "\n".join(lines)

    def action_process(self):
        for inbox in self:
            inbox._od19_process()

    @api.model
    def _cron_process_inbox(self):
        pending = self.search([("state", "in", ("new", "failed"))], limit=50)
        for inbox in pending:
            inbox._od19_process()
```

- [ ] **Step 2: เขียน wizard ยืนยัน/ผูก + อัปโหลดยกชุด**

`custom_addons/od19_document_intake/models/od19_document_intake_wizard.py`
```python
# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models

LINK_MODELS = [
    ("res.partner", "คู่ค้า"),
    ("account.move", "ใบกำกับ/บิล"),
    ("purchase.order", "ใบสั่งซื้อ"),
    ("sale.order", "ใบสั่งขาย"),
]


class Od19InboxLinkWizard(models.TransientModel):
    _name = "od19.document.inbox.link.wizard"
    _description = "ยืนยันและผูกเอกสารจากกล่องรับเข้า"

    inbox_id = fields.Many2one("od19.document.inbox", required=True, ondelete="cascade")
    category_id = fields.Many2one(
        "od19.document.category", "หมวดเอกสาร", required=True, ondelete="restrict",
    )
    resource_ref = fields.Reference("ผูกกับ", selection=LINK_MODELS)

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        inbox = self.env["od19.document.inbox"].browse(
            self.env.context.get("active_id"),
        )
        if inbox:
            values.setdefault("inbox_id", inbox.id)
            values.setdefault("category_id", inbox.suggested_category_id.id)
        return values

    def action_confirm(self):
        self.ensure_one()
        res_model = res_id = False
        if self.resource_ref:
            res_model, res_id = self.resource_ref._name, self.resource_ref.id
        attachment = self.inbox_id._od19_create_attachment(
            category=self.category_id, res_model=res_model, res_id=res_id,
        )
        attachment._od19_run_extraction(self.inbox_id.channel_id)
        self.inbox_id.write({"classify_method": "manual"})
        return {"type": "ir.actions.act_window_close"}


class Od19IntakeUploadLine(models.TransientModel):
    _name = "od19.document.intake.upload.line"
    _description = "บรรทัดอัปโหลดเอกสารยกชุด"

    wizard_id = fields.Many2one(
        "od19.document.intake.upload.wizard", required=True, ondelete="cascade",
    )
    file = fields.Binary("ไฟล์", required=True)
    filename = fields.Char("ชื่อไฟล์")


class Od19IntakeUploadWizard(models.TransientModel):
    _name = "od19.document.intake.upload.wizard"
    _description = "อัปโหลดเอกสารยกชุดเข้าช่องรับเข้า"

    channel_id = fields.Many2one(
        "od19.document.channel", "ช่องทาง", required=True, ondelete="cascade",
    )
    line_ids = fields.One2many(
        "od19.document.intake.upload.line", "wizard_id", "ไฟล์",
    )

    def action_upload(self):
        self.ensure_one()
        Inbox = self.env["od19.document.inbox"]
        created = Inbox
        for line in self.line_ids:
            created |= Inbox.create({
                "name": line.filename or "เอกสารเข้า",
                "filename": line.filename,
                "file": line.file,
                "channel_id": self.channel_id.id,
                "state": "new",
            })
        created.action_process()
        return {
            "type": "ir.actions.act_window",
            "name": "กล่องรับเข้า",
            "res_model": "od19.document.inbox",
            "view_mode": "kanban,form",
            "domain": [("id", "in", created.ids)],
        }
```

- [ ] **Step 3: เปิด import**

`custom_addons/od19_document_intake/models/__init__.py`
```python
# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from . import od19_document_channel
from . import od19_document_classify_rule
from . import od19_document_inbox
from . import ir_attachment
from . import od19_document_intake_wizard
```

- [ ] **Step 4: รันเทสต์**

Run: `pwsh -File .\run-tests.ps1 -Module od19_document_intake -Database odoo19_t_doc_intake -HttpPort 8082`
Expected: PASS — เทสต์เดิมทั้งหมดผ่าน (ยังไม่มีเทสต์ pipeline ในสเปก จึงตรวจเฉพาะว่า import ไม่พัง)

- [ ] **Step 5: Commit**

```powershell
git add custom_addons/od19_document_intake/models/od19_document_inbox.py custom_addons/od19_document_intake/models/od19_document_intake_wizard.py custom_addons/od19_document_intake/models/__init__.py
git commit -m "feat(od19_document_intake): add processing pipeline and intake wizards"
```

---

### Task 10: Views + เมนู + cron

**Files:**
- Create: `custom_addons/od19_document_intake/views/od19_document_channel_views.xml`
- Create: `custom_addons/od19_document_intake/views/od19_document_classify_rule_views.xml`
- Create: `custom_addons/od19_document_intake/views/od19_document_inbox_views.xml`
- Create: `custom_addons/od19_document_intake/views/od19_document_intake_wizard_views.xml`
- Create: `custom_addons/od19_document_intake/views/od19_document_intake_menus.xml`
- Create: `custom_addons/od19_document_intake/data/ir_cron_data.xml`

- [ ] **Step 1: view ช่องทาง**

`views/od19_document_channel_views.xml`
```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="view_od19_document_channel_tree" model="ir.ui.view">
        <field name="name">od19.document.channel.tree</field>
        <field name="model">od19.document.channel</field>
        <field name="arch" type="xml">
            <list string="ช่องทางรับเอกสาร">
                <field name="sequence" widget="handle"/>
                <field name="name"/>
                <field name="kind"/>
                <field name="default_category_id"/>
                <field name="enable_ocr"/>
                <field name="enable_ai"/>
                <field name="last_scan_at"/>
                <field name="active" invisible="1"/>
            </list>
        </field>
    </record>

    <record id="view_od19_document_channel_form" model="ir.ui.view">
        <field name="name">od19.document.channel.form</field>
        <field name="model">od19.document.channel</field>
        <field name="arch" type="xml">
            <form string="ช่องทางรับเอกสาร">
                <sheet>
                    <group>
                        <group>
                            <field name="name"/>
                            <field name="kind"/>
                            <field name="path"
                                   invisible="kind != 'folder'"/>
                            <field name="alias_id"
                                   invisible="kind != 'email_alias'"/>
                        </group>
                        <group>
                            <field name="default_category_id"/>
                            <field name="enable_ocr"/>
                            <field name="enable_ai"/>
                            <field name="last_scan_at"/>
                            <field name="active"/>
                        </group>
                    </group>
                    <group string="ข้อผิดพลาดล่าสุด">
                        <field name="last_error" nolabel="1" readonly="1"/>
                    </group>
                </sheet>
            </form>
        </field>
    </record>

    <record id="action_od19_document_channel" model="ir.actions.act_window">
        <field name="name">ช่องทางรับเอกสาร</field>
        <field name="res_model">od19.document.channel</field>
        <field name="view_mode">list,form</field>
    </record>
</odoo>
```

- [ ] **Step 2: view กฎจัดหมวด**

`views/od19_document_classify_rule_views.xml`
```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="view_od19_document_classify_rule_tree" model="ir.ui.view">
        <field name="name">od19.document.classify.rule.tree</field>
        <field name="model">od19.document.classify.rule</field>
        <field name="arch" type="xml">
            <list string="กฎจัดหมวด">
                <field name="sequence" widget="handle"/>
                <field name="name"/>
                <field name="target"/>
                <field name="pattern"/>
                <field name="category_id"/>
                <field name="partner_id"/>
                <field name="active" invisible="1"/>
            </list>
        </field>
    </record>

    <record id="view_od19_document_classify_rule_form" model="ir.ui.view">
        <field name="name">od19.document.classify.rule.form</field>
        <field name="model">od19.document.classify.rule</field>
        <field name="arch" type="xml">
            <form string="กฎจัดหมวด">
                <sheet>
                    <group>
                        <field name="name"/>
                        <field name="sequence"/>
                        <field name="target"/>
                        <field name="pattern"/>
                        <field name="category_id"/>
                        <field name="partner_id"/>
                        <field name="active"/>
                    </group>
                </sheet>
            </form>
        </field>
    </record>

    <record id="action_od19_document_classify_rule" model="ir.actions.act_window">
        <field name="name">กฎจัดหมวด</field>
        <field name="res_model">od19.document.classify.rule</field>
        <field name="view_mode">list,form</field>
    </record>
</odoo>
```

- [ ] **Step 3: view กล่องรับเข้า (Kanban + list + form)**

`views/od19_document_inbox_views.xml`
```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="view_od19_document_inbox_kanban" model="ir.ui.view">
        <field name="name">od19.document.inbox.kanban</field>
        <field name="model">od19.document.inbox</field>
        <field name="arch" type="xml">
            <kanban default_group_by="state">
                <field name="state"/>
                <field name="suggested_category_id"/>
                <field name="confidence"/>
                <templates>
                    <t t-name="card">
                        <div class="d-flex flex-column">
                            <strong><field name="name"/></strong>
                            <span t-if="record.suggested_category_id.value">
                                หมวด: <field name="suggested_category_id"/>
                            </span>
                            <span>ความมั่นใจ: <field name="confidence"/>%</span>
                        </div>
                    </t>
                </templates>
            </kanban>
        </field>
    </record>

    <record id="view_od19_document_inbox_tree" model="ir.ui.view">
        <field name="name">od19.document.inbox.tree</field>
        <field name="model">od19.document.inbox</field>
        <field name="arch" type="xml">
            <list string="กล่องรับเข้า">
                <field name="name"/>
                <field name="filename"/>
                <field name="channel_id"/>
                <field name="state"/>
                <field name="suggested_category_id"/>
                <field name="confidence"/>
                <field name="classify_method"/>
                <field name="create_date"/>
            </list>
        </field>
    </record>

    <record id="view_od19_document_inbox_form" model="ir.ui.view">
        <field name="name">od19.document.inbox.form</field>
        <field name="model">od19.document.inbox</field>
        <field name="arch" type="xml">
            <form string="กล่องรับเข้า">
                <header>
                    <button name="action_process" type="object" string="ประมวลผล"
                            class="oe_highlight" invisible="state not in ('new', 'failed')"/>
                    <button name="action_reject" type="object" string="ปฏิเสธ"
                            invisible="state in ('linked', 'rejected')"/>
                    <field name="state" widget="statusbar"/>
                </header>
                <sheet>
                    <group>
                        <group>
                            <field name="name"/>
                            <field name="filename"/>
                            <field name="file" filename="filename"/>
                            <field name="channel_id"/>
                        </group>
                        <group>
                            <field name="suggested_category_id"/>
                            <field name="suggested_partner_id"/>
                            <field name="confidence"/>
                            <field name="classify_method"/>
                            <field name="attachment_id"/>
                        </group>
                    </group>
                    <group string="บันทึกการประมวลผล">
                        <field name="log" nolabel="1" readonly="1"/>
                    </group>
                </sheet>
            </form>
        </field>
    </record>

    <record id="action_od19_document_inbox" model="ir.actions.act_window">
        <field name="name">กล่องรับเข้า</field>
        <field name="res_model">od19.document.inbox</field>
        <field name="view_mode">kanban,list,form</field>
    </record>

    <record id="action_od19_document_intake_upload" model="ir.actions.act_window">
        <field name="name">อัปโหลดยกชุด</field>
        <field name="res_model">od19.document.intake.upload.wizard</field>
        <field name="view_mode">form</field>
        <field name="target">new</field>
    </record>
</odoo>
```

- [ ] **Step 4: view wizard**

`views/od19_document_intake_wizard_views.xml`
```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="view_od19_document_inbox_link_wizard_form" model="ir.ui.view">
        <field name="name">od19.document.inbox.link.wizard.form</field>
        <field name="model">od19.document.inbox.link.wizard</field>
        <field name="arch" type="xml">
            <form string="ยืนยันและผูกเอกสาร">
                <group>
                    <field name="inbox_id" readonly="1"/>
                    <field name="category_id"/>
                    <field name="resource_ref"/>
                </group>
                <footer>
                    <button name="action_confirm" type="object" string="ยืนยันและผูก"
                            class="btn-primary"/>
                    <button string="ยกเลิก" class="btn-secondary" special="cancel"/>
                </footer>
            </form>
        </field>
    </record>

    <record id="view_od19_document_intake_upload_wizard_form" model="ir.ui.view">
        <field name="name">od19.document.intake.upload.wizard.form</field>
        <field name="model">od19.document.intake.upload.wizard</field>
        <field name="arch" type="xml">
            <form string="อัปโหลดยกชุด">
                <group>
                    <field name="channel_id"/>
                </group>
                <field name="line_ids">
                    <list editable="bottom">
                        <field name="filename"/>
                        <field name="file" filename="filename"/>
                    </list>
                </field>
                <footer>
                    <button name="action_upload" type="object" string="อัปโหลด"
                            class="btn-primary"/>
                    <button string="ยกเลิก" class="btn-secondary" special="cancel"/>
                </footer>
            </form>
        </field>
    </record>

    <record id="action_od19_document_inbox_link_wizard" model="ir.actions.act_window">
        <field name="name">ยืนยันและผูก</field>
        <field name="res_model">od19.document.inbox.link.wizard</field>
        <field name="view_mode">form</field>
        <field name="target">new</field>
    </record>
</odoo>
```

- [ ] **Step 5: เมนู (ต่อจาก root ของ hub)**

`views/od19_document_intake_menus.xml`
```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <menuitem id="menu_od19_document_inbox"
              name="กล่องรับเข้า"
              parent="od19_document_hub.menu_od19_document_root"
              action="action_od19_document_inbox"
              sequence="5"/>
    <menuitem id="menu_od19_document_intake_upload"
              name="อัปโหลดยกชุด"
              parent="od19_document_hub.menu_od19_document_root"
              action="action_od19_document_intake_upload"
              sequence="6"/>
    <menuitem id="menu_od19_document_channel"
              name="ช่องทางรับเอกสาร"
              parent="od19_document_hub.menu_od19_document_root"
              action="action_od19_document_channel"
              sequence="20"/>
    <menuitem id="menu_od19_document_classify_rule"
              name="กฎจัดหมวด"
              parent="od19_document_hub.menu_od19_document_root"
              action="action_od19_document_classify_rule"
              sequence="21"/>
</odoo>
```

> **หมายเหตุ:** `od19_document_hub.menu_od19_document_root` คือ root menu "ศูนย์เอกสาร" ที่สร้างใน P1 (ตรวจ id ให้ตรงก่อนใช้)

- [ ] **Step 6: cron สแกนโฟลเดอร์ + ประมวลผล inbox**

`data/ir_cron_data.xml`
```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <data noupdate="1">
        <record id="ir_cron_od19_scan_channels" model="ir.cron">
            <field name="name">OD19 Document: Scan intake channels</field>
            <field name="model_id" ref="model_od19_document_channel"/>
            <field name="state">code</field>
            <field name="code">model._cron_scan_channels()</field>
            <field name="interval_number">10</field>
            <field name="interval_type">minutes</field>
            <field name="active">True</field>
            <field name="nextcall" eval="(DateTime.today() + relativedelta(minutes=10)).strftime('%Y-%m-%d %H:%M:%S')"/>
        </record>

        <record id="ir_cron_od19_process_inbox" model="ir.cron">
            <field name="name">OD19 Document: Process intake inbox</field>
            <field name="model_id" ref="model_od19_document_inbox"/>
            <field name="state">code</field>
            <field name="code">model._cron_process_inbox()</field>
            <field name="interval_number">5</field>
            <field name="interval_type">minutes</field>
            <field name="active">True</field>
            <field name="nextcall" eval="(DateTime.today() + relativedelta(minutes=5)).strftime('%Y-%m-%d %H:%M:%S')"/>
        </record>
    </data>
</odoo>
```

- [ ] **Step 7: ตรวจ XML well-formed**

Run:
```powershell
Get-ChildItem custom_addons/od19_document_intake/views, custom_addons/od19_document_intake/data -Filter *.xml | ForEach-Object { [xml](Get-Content $_.FullName -Raw) | Out-Null; "OK $($_.Name)" }
```
Expected: พิมพ์ `OK` ทุกไฟล์ ไม่มี exception

- [ ] **Step 8: รันเทสต์ (ติดตั้ง view/menu/cron บน DB ทดสอบ)**

Run: `pwsh -File .\run-tests.ps1 -Module od19_document_intake -Database odoo19_t_doc_intake -HttpPort 8082`
Expected: PASS — ติดตั้ง view/menu/cron สำเร็จ 0 failed / 0 error

- [ ] **Step 9: Commit**

```powershell
git add custom_addons/od19_document_intake/views/od19_document_channel_views.xml custom_addons/od19_document_intake/views/od19_document_classify_rule_views.xml custom_addons/od19_document_intake/views/od19_document_inbox_views.xml custom_addons/od19_document_intake/views/od19_document_intake_wizard_views.xml custom_addons/od19_document_intake/views/od19_document_intake_menus.xml custom_addons/od19_document_intake/data/ir_cron_data.xml
git commit -m "feat(od19_document_intake): add views menus and scheduled jobs"
```

---

### Task 11: คำแปลไทย + OCR dependency (ตัวเลือก)

**Files:**
- Create: `custom_addons/od19_document_intake/i18n/th.po`
- Modify: `requirements-od19.txt`

- [ ] **Step 1: เขียนไฟล์คำแปลไทย (โครงเริ่มต้น)**

`custom_addons/od19_document_intake/i18n/th.po`
```po
# Thai translation for od19_document_intake
msgid ""
msgstr ""
"Project-Id-Version: od19_document_intake 19.0.1.0.0\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=UTF-8\n"
"Content-Transfer-Encoding: 8bit\n"
"Language: th\n"

#. module: od19_document_intake
#: model:ir.model,name:od19_document_intake.model_od19_document_inbox
msgid "กล่องรับเข้าเอกสาร (staging)"
msgstr "กล่องรับเข้าเอกสาร (staging)"

#. module: od19_document_intake
#: model:ir.model,name:od19_document_intake.model_od19_document_channel
msgid "ช่องทางรับเอกสารเข้า"
msgstr "ช่องทางรับเอกสารเข้า"
```

> หลังรันเทสต์ ให้ใช้ `odoo-bin` โหมด `--i18n-export` เพื่อดึง msgid ครบ แล้วเติมคำแปลไทย (ไม่ต้องครบในรอบแรก)

- [ ] **Step 2: เปิดใช้ OCR dependency (ตัวเลือก — คอมเมนต์ไว้ก่อน)**

`requirements-od19.txt` — เพิ่มต่อท้าย (คอมเมนต์ไว้ ไม่ให้ติดตั้งโดยอัตโนมัติ เพราะต้องมีไบนารีในเครื่อง)
```
# --- od19_document_intake (P2): OCR ตัวเลือก ---
# ต้องติดตั้ง tesseract-ocr + poppler ในเครื่องก่อนเปิดใช้ (V-9)
# pytesseract==0.3.13
# pdf2image==1.17.0
```

- [ ] **Step 3: รันเทสต์สุดท้าย**

Run: `pwsh -File .\run-tests.ps1 -Module od19_document_intake -Database odoo19_t_doc_intake -HttpPort 8082`
Expected: PASS — 0 failed / 0 error ไม่มี warning ใน log

- [ ] **Step 4: Commit**

```powershell
git add custom_addons/od19_document_intake/i18n/th.po requirements-od19.txt
git commit -m "chore(od19_document_intake): add thai translation and optional ocr deps"
```

---

## Self-Review (ตรวจแผนกับสเปก §5–§12)

**1. Spec coverage:**

| สเปก | Task |
|---|---|
| §5.1 depends `od19_document_hub` + `od19_ai_assistant` | Task 1 (manifest) |
| §6.2 `od19.document.channel` | Task 3 |
| §6.2 `od19.document.inbox` | Task 5 |
| §8.1 จัดหมวด: กฎ → AI | Task 6 + Task 7 |
| §8.1 สกัดข้อความ: text layer ก่อน → OCR | Task 8 |
| §8.1 เกณฑ์ confidence ≥ 70% ผูกอัตโนมัติ | Task 9 (`CONFIDENCE_THRESHOLD`) |
| §7.3 Kanban กล่องรับเข้า + wizard ยืนยัน/ผูก | Task 10 (kanban) + Task 9 (wizard) |
| §3.1 อัปโหลดยกชุด | Task 9 (upload wizard) |
| §3.1 ช่องทางอีเมล (alias) | Task 4 (`alias_id`) + Task 5 (`message_new`) |
| §9 guards (ไฟล์ใหญ่ข้าม, PDF ไม่มี text layer, ข้อความว่าง, โฟลเดอร์ถูกลบ, ไฟล์ซ้ำแบบ ข.) | Task 3, 8, 9 |
| §10 `test_document_intake_rules.py` + `test_document_intake_ai.py` | Task 6 + Task 7 |
| §12 D5 OCR/AI เป็นคิวผ่าน cron | Task 3 + Task 9 (ir.cron) + Task 10 |
| §12 D9 พาธโฟลเดอร์ (`channel.path`) | Task 3 |
| §14 ทางเลือก ข. (ไฟล์ซ้ำสร้างระเบียนใหม่) | Task 9 (`_od19_create_attachment` — hub นับ `od19_duplicate_count`) |

**2. Placeholder scan:** ไม่มี `TBD`/`TODO` — ทุก step มีโค้ด/คำสั่งจริง

**3. Type consistency:**
- ชื่อโมเดลตรงกันทุก Task: `od19.document.channel`, `od19.document.classify.rule`, `od19.document.inbox`, `od19.document.inbox.link.wizard`, `od19.document.intake.upload.wizard`, `od19.document.intake.upload.line`
- เมธอด: `_od19_scan_channel`, `_cron_scan_channels`, `_od19_classify_by_rules`, `_od19_classify_with_ai`, `_od19_classify`, `_od19_process`, `action_process`, `action_reject`, `_od19_create_attachment`, `_od19_run_extraction`, `_od19_extract_text`, `message_new` — ใช้ชื่อเดียวกันตลอด
- ค่าคงที่: `CONFIDENCE_THRESHOLD = 70.0`, `MAX_EXTRACT_SIZE = 25 MB`, `STATE_SELECTION` (new/processing/to_review/linked/rejected/failed) ตรงกับ §7.3
- XML `ref` ต้องตรงกับ id จริง: `od19_document_hub.menu_od19_document_root`, `model_od19_document_inbox`, `model_od19_document_channel`

**ช่องว่างที่รู้ตัว (อยู่นอกแผนนี้โดยเจตนา):**
- ค้นหา facet + ปรับดัชนีภาษาไทยใน UI → P3
- บังคับใช้นโยบายอายุ/legal hold/audit read-download/dashboard ตัววัด → `od19_document_governance` (P4/P5)
- OCR engine จริง (tesseract/poppler) — แผนนี้เตรียม hook แบบ guard ไว้แล้ว; เปิดใช้จริงเป็นงานติดตั้ง (V-9)
- bulk upload ขนาดใหญ่มาก (หลายพันไฟล์) — ใช้ cron `_cron_process_inbox` (limit 50/รอบ) ทยอยประมวลผล

---

## Execution Handoff

- เริ่มงานเป็น **Task 1..11 ตามลำดับ** — แต่ละ Task มีเทสต์ก่อนโค้ด (TDD) และ commit เดี่ยวตาม AGENTS.md §4
- **lease:** Task 3–10 (คิว/สแกนโฟลเดอร์/ประมวลผล) ถ้ารันบน DB ที่แชร์ต้องถือ `db:odoo19_pdev`; บน DB ทดสอบ `odoo19_t_doc_intake` ของตัวเองไม่ต้องจับ lease
- ก่อน push: `git merge-base --is-ancestor origin/19.0 19.0` (FF-safe) แล้วขออนุมัติรวดเดียวตาม AGENTS.md §5 + ตั้ง `OD19_PUSH_APPROVED=1`
- หลังเสร็จ P2 → ไปต่อ **P3 (ค้นหากลาง)** ตาม §11 โดยเขียนแผนแยกที่ `docs/superpowers/plans/2026-11-11-od19-document-search.md`
