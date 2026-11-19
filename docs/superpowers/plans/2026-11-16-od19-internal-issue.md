# ระบบจัดการเรื่องแจ้งปัญหาภายใน (od19_internal_issue) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** สร้างโมดูล `od19_internal_issue` ต่อยอด OCA `helpdesk_mgmt` ให้พนักงานแจ้ง "เรื่อง/ปัญหา" ผ่าน Backend/Portal/Email แล้วระบบจัดประเภท+มอบหมายทีมอัตโนมัติ เข้าคิวต่อทีม แสดงตำแหน่งคิวให้ผู้แจ้ง คิด priority ด้วยเกณฑ์กลาง (Impact × Urgency) และรองรับการขอแซงคิวด้วยการอนุมัติ 2 ชั้น

**Architecture:** โมดูลใหม่แบบ inherit-only ใต้ `custom_addons/od19_internal_issue` — **ไม่แก้โค้ด core/OCA** ใช้ `stage_id` ของ OCA เป็นสถานะ (ไม่สร้าง `state` ใหม่), เพิ่มฟิลด์ fairness/queue/privacy บน `helpdesk.ticket`, เพิ่มโมเดลใหม่ 2 ตัว (`helpdesk.routing.rule` สำหรับ route, `helpdesk.queue.request` สำหรับคำขอแซงคิว), และใช้ `notification.service` จาก `od19_notification_multi_channel` เป็น gateway แจ้งเตือน

**Tech Stack:** Odoo 19 CE · Python (`odoo.fields`, `api.depends`) · XML data/views · OCA `helpdesk_mgmt` + `base_tier_validation` · `od19_helpdesk_extension` · `od19_notification_multi_channel` · `od19_security_roles` · PowerShell 7 (`run-tests.ps1`)

**อ้างอิง spec:** `docs/superpowers/specs/2026-11-16-od19-internal-issue-design.md`

---

## 0. ข้อมูลสภาพแวดล้อมการทดสอบ

| ค่า | ค่าที่ใช้ |
|---|---|
| AGENT_ID | `trae-od19_internal_issue` |
| Worktree | `c:\odoo-dev\od19_internal_issue` (branch `feature/od19_internal_issue`) |
| DB ทดสอบ | `odoo19_t_internal_issue` |
| HTTP port | `8085` |
| คำสั่งรันเทสต์ | `pwsh -File .\run-tests.ps1 -Module od19_internal_issue -Database odoo19_t_internal_issue -HttpPort 8085` |

**ข้อกำหนดก่อนรันเทสต์แรก (สำคัญ):**
1. ต้องสร้าง DB ทดสอบจาก template ที่มี `helpdesk_mgmt`, `od19_helpdesk_extension`, `base_tier_validation`, `od19_notification_multi_channel`, `od19_security_roles` ติดตั้งแล้ว
2. รัน Odoo ด้วย `--data-dir` แยกเฉพาะของ worktree นี้ (`C:\odoo-dev\od19_internal_issue\data`) เพื่อเลี่ยงปัญหาเขียนไฟล์ทับกับ instance ที่แชร์ (พอร์ต 8070)
3. `dbfilter` ต้องเจาะจงฐานข้อมูลเดียว (`^odoo19_t_internal_issue$`) เพื่อให้ Odoo auto-select DB
4. **ห้ามรัน Odoo บนพอร์ต 8070 หรือ DB `odoo19_pdev`/`odoo19_puat`** ในขั้นเทสต์ (ดู AGENTS.md §0, §6)

---

## 1. ค่าที่ตัดสินใจล่วงหน้า (บันทึกไว้ล่วงหน้าเพื่อไม่ให้ agent ตัดสินใจเองระหว่างทาง)

| # | ประเด็น | ค่าที่เลือก | เหตุผล |
|---|---|---|---|
| D1 | สถานะ (stage) | ใช้ `stage_id` ของ OCA + สร้าง stage ไทย 6 ขั้นในโมดูลนี้ (ผูก `team_ids` เฉพาะทีมภายใน) | ไม่สร้าง `state` ใหม่ซ้อนกับ OCA; ไม่กระทบงานบริการลูกค้า |
| D2 | ฟิลด์แผนกอ้างอิง | ใช้ `visibility_department_id` (m2o `hr.department`) เป็นแผนกอ้างอิงเดียว — **ตัด `department_id` เดิมออก** | ตาม spec §2; ใช้ทั้ง visibility rule และ department-scope rule |
| D3 | ฟิลด์ผู้แจ้ง | `reported_by_id` (m2o `res.users`, default `env.user`) | ต้องรู้ user เพื่อหา "หัวหน้าแผนกผู้แจ้ง" และ privacy rule |
| D4 | ที่มาของ `priority` | compute+store จาก Impact×Urgency, `readonly=False`, `tracking=True` (manager override ได้ มี audit) | ตาม spec §9; tracking ให้ audit log |
| D5 | namespaces ของ config | `od19_internal_issue.jump_window_hours` (default 24) | ระยะเวลาเปิดปุ่ม "ขอแซงคิว" |
| D6 | ทีมภายใน | สร้าง 4 ทีมในโมดูลนี้: `IT Support`(it_support) / `ปรับปรุง`(improvement) / `ISO-CAPA`(iso_capa) / `กล่องกลาง Triage`(is_triage_team) | ตาม spec §3 route; แยกจาก `team_internal_it` ของ `od19_helpdesk_extension` |
| D7 | `base_tier_validation` | คง dependency ไว้ แต่ **ไม่ inherit** ใน Phase 1 | เตรียมไว้ให้ ISO/ปรับปรุง ใน Phase 2 |
| D8 | ลำดับคิว | `priority desc, queue_sequence asc, id asc` (FIFO) · แทรกคิวโดยตั้ง `queue_sequence` ต่ำกว่า `insert_before_id` | ตาม spec §8; FIFO ใช้ `queue_sequence` ที่ตั้งตอนสร้าง |

---

## 2. โครงไฟล์ปลายทาง (File Structure)

| ไฟล์ | ความรับผิดชอบ |
|---|---|
| `__init__.py` | โหลด `models` |
| `__manifest__.py` | metadata + depends + data list |
| `models/__init__.py` | โหลดโมเดลทั้งหมด |
| `models/internal_issue_common.py` | selection constants + `score_to_priority()` (ใช้ร่วมทุกโมเดล) |
| `models/helpdesk_ticket.py` | inherit `helpdesk.ticket`: ฟิลด์ fairness/privacy/queue + compute priority + compute queue position + create hook (route + jump window) + notification hooks |
| `models/helpdesk_ticket_team.py` | inherit `helpdesk.ticket.team`: `issue_stream` / `is_triage_team` / `weekly_priority_quota` |
| `models/helpdesk_ticket_category.py` | inherit `helpdesk.ticket.category`: `default_user_id` / `default_team_id` (คงไว้) |
| `models/helpdesk_routing_rule.py` | โมเดลใหม่ `helpdesk.routing.rule` + helper match |
| `models/helpdesk_queue_request.py` | โมเดลใหม่ `helpdesk.queue.request` + workflow อนุมัติ 2 ชั้น + cron expiry |
| `security/ir.model.access.csv` | สิทธิ์ระดับโมเดล (เติมจาก header ว่าง) |
| `security/internal_issue_security.xml` | visibility record rule (public/department/private) |
| `security/od19_department_rule.xml` | department-scope rule (ผูก `od19_security_roles`) |
| `data/internal_issue_data.xml` | teams 4 + stages ไทย 6 + routing rules ตัวอย่าง |
| `data/internal_issue_cron.xml` | cron หมดอายุคำขอแซงคิว |
| `views/helpdesk_ticket_views.xml` | inherit form/tree/search/kanban ของ ticket |
| `views/helpdesk_queue_request_views.xml` | list + form + action ของ `helpdesk.queue.request` |
| `views/helpdesk_routing_rule_views.xml` | list + form + action ของ `helpdesk.routing.rule` |
| `views/internal_issue_menus.xml` | submenu ใต้ Helpdesk + config |
| `tests/__init__.py` | โหลด test ทั้งหมด |
| `tests/test_helpdesk_ticket.py` | ฟิลด์ + fair priority |
| `tests/test_helpdesk_routing.py` | routing rule + Triage |
| `tests/test_helpdesk_queue.py` | queue ordering + position |
| `tests/test_helpdesk_queue_request.py` | อนุมัติ 2 ชั้น + insert + expiry |
| `tests/test_helpdesk_privacy.py` | record rules (own/department/private) |

---

# PHASE P1 — แกนระบบ (ฟิลด์ + route + คิว + fairness + privacy + notify)

## Task T01: โครงโมดูล + manifest + ติดตั้งครั้งแรก

**Files:**
- Modify: `custom_addons/od19_internal_issue/__manifest__.py`
- Modify: `custom_addons/od19_internal_issue/__init__.py`
- Modify: `custom_addons/od19_internal_issue/models/__init__.py`
- Modify: `custom_addons/od19_internal_issue/tests/__init__.py`
- Create: `custom_addons/od19_internal_issue/models/internal_issue_common.py`
- Create (stub): `models/helpdesk_ticket_team.py`, `models/helpdesk_routing_rule.py`, `models/helpdesk_queue_request.py`
- Create (stub): `security/ir.model.access.csv`, `security/internal_issue_security.xml`, `security/od19_department_rule.xml`, `data/internal_issue_data.xml`, `data/internal_issue_cron.xml`, `views/helpdesk_ticket_views.xml`, `views/helpdesk_queue_request_views.xml`, `views/helpdesk_routing_rule_views.xml`, `views/internal_issue_menus.xml`
- Create (stub): `tests/test_helpdesk_ticket.py`, `tests/test_helpdesk_routing.py`, `tests/test_helpdesk_queue.py`, `tests/test_helpdesk_queue_request.py`, `tests/test_helpdesk_privacy.py`

- [ ] **Step 1: เขียน `models/__init__.py` ใหม่**

```python
from . import internal_issue_common
from . import helpdesk_ticket
from . import helpdesk_ticket_category
from . import helpdesk_ticket_team
from . import helpdesk_routing_rule
from . import helpdesk_queue_request
```

- [ ] **Step 2: เขียน `models/internal_issue_common.py`**

```python
ISSUE_STREAM_SELECTION = [
    ("it_support", "ไอที/ระบบ (IT Support)"),
    ("improvement", "ข้อเสนอแนะปรับปรุง"),
    ("iso_capa", "คุณภาพ / ISO (CAPA)"),
    ("unsure", "ไม่แน่ใจ"),
]

IMPACT_SELECTION = [
    ("I1", "เฉพาะตัวเอง"),
    ("I2", "หลายแผนก / หลายคน"),
    ("I3", "กระทบทั้งบริษัท / ระบบหยุดทั้งระบบ"),
]

URGENCY_SELECTION = [
    ("U1", "ไม่กระทบ (ทำงานได้ตามปกติ)"),
    ("U2", "มีผล แต่มีงานแทนชั่วคราว"),
    ("U3", "หยุดงานทันที"),
]

VISIBILITY_SELECTION = [
    ("public", "สาธารณะ (ทุกคน)"),
    ("department", "เฉพาะแผนก"),
    ("private", "ส่วนตัว"),
]

CONSENT_SELECTION = [
    ("pending", "รอยินยอม"),
    ("accepted", "ยินยอม (เข้าคิว)"),
    ("jump_requested", "ขอแซงคิว"),
]

QUEUE_REQUEST_STATE = [
    ("draft", "ร่าง"),
    ("waiting_reporter_head", "รอหัวหน้าแผนกผู้แจ้ง"),
    ("waiting_team_head", "รอหัวหน้าทีมเจ้าของคิว"),
    ("approved", "อนุมัติแล้ว"),
    ("rejected", "ปฏิเสธ"),
    ("expired", "หมดอายุ"),
]

# score = Impact + Urgency (2..6) -> OCA priority ("0".."3")
# 6 -> P3 ด่วนวิกฤต, 5 -> P2 สูง, 3-4 -> P1 กลาง, 2 -> P0 ต่ำ
_SCORE_TO_PRIORITY = {6: "3", 5: "2", 4: "1", 3: "1", 2: "0"}

# ป้ายอธิบาย priority ที่คำนวณได้ (ใช้แสดงใน chatter/audit)
PRIORITY_LABEL = {
    "3": "ด่วนวิกฤต (P3)",
    "2": "สูง (P2)",
    "1": "กลาง (P1)",
    "0": "ต่ำ (P0)",
}


def score_to_priority(impact, urgency):
    """แปลง Impact × Urgency เป็นค่า priority ของ OCA ('0'..'3')."""
    i = int(impact[1]) if impact else 1
    u = int(urgency[1]) if urgency else 1
    return _SCORE_TO_PRIORITY.get(i + u, "1")
```

- [ ] **Step 3: เขียน `__init__.py`**

```python
from . import models
```

- [ ] **Step 4: เขียน `__manifest__.py`**

```python
{
    "name": "Internal Issue Management",
    "version": "19.0.1.0.0",
    "category": "Internal Operations",
    "summary": "ระบบรับแจ้งเรื่อง/ปัญหาภายใน พร้อมคิวที่เป็นธรรมและการแซงคิวแบบอนุมัติ 2 ชั้น",
    "description": """
Internal Issue Management
=========================
ต่อยอด OCA helpdesk_mgmt สำหรับงานภายในองค์กร:
- หมวดใหญ่ (issue_stream) + route อัตโนมัติ + กล่องกลาง (Triage)
- ความเป็นส่วนตัว public / แผนก / ส่วนตัว
- คิวต่อทีม (priority -> FIFO) + แสดงตำแหน่งคิวให้ผู้แจ้ง
- Fair priority: Impact x Urgency + โควตางานด่วน
- คำขอแซงคิว: อนุมัติ 2 ชั้น + ผู้อนุมัติเลือกตำแหน่งแทรก
- แจ้งเตือนหลายช่องทางผ่าน od19_notification_multi_channel
""",
    "author": "OD19",
    "website": "https://github.com/odoo/odoo",
    "license": "LGPL-3",
    "depends": [
        "helpdesk_mgmt",
        "od19_helpdesk_extension",
        "base_tier_validation",
        "hr",
        "mail",
        "od19_notification_multi_channel",
        "od19_security_roles",
    ],
    "data": [
        "security/internal_issue_security.xml",
        "security/od19_department_rule.xml",
        "security/ir.model.access.csv",
        "data/internal_issue_data.xml",
        "data/internal_issue_cron.xml",
        "views/helpdesk_ticket_views.xml",
        "views/helpdesk_queue_request_views.xml",
        "views/helpdesk_routing_rule_views.xml",
        "views/internal_issue_menus.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "icon": "/od19_internal_issue/static/description/icon.svg",
}
```

- [ ] **Step 5: สร้างไฟล์ที่ manifest อ้างถึงเป็น stub (valid ก่อน)**

เหตุผล: `__manifest__.py` อ้างไฟล์ทั้งหมด ถ้าไฟล์ยังไม่มี Odoo จะติดตั้งไม่ผ่าน ทำให้รันเทสต์ (`-u`) ไม่ได้

ไฟล์ stub ที่ root `<odoo></odoo>` ว่าง (XML):
`security/internal_issue_security.xml`, `security/od19_department_rule.xml`,
`data/internal_issue_data.xml`, `data/internal_issue_cron.xml`,
`views/helpdesk_ticket_views.xml`, `views/helpdesk_queue_request_views.xml`,
`views/helpdesk_routing_rule_views.xml`, `views/internal_issue_menus.xml`

เนื้อหาแต่ละไฟล์:

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
</odoo>
```

`security/ir.model.access.csv` (stub = เฉพาะ header):

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
```

- [ ] **Step 6: สร้างโมเดลใหม่เป็น stub (คลาสว่าง) เพื่อให้ `models/__init__.py` โหลดได้**

`models/helpdesk_ticket_team.py`

```python
from odoo import models


class HelpdeskTicketTeam(models.Model):
    _inherit = "helpdesk.ticket.team"
```

`models/helpdesk_routing_rule.py`

```python
from odoo import models


class HelpdeskRoutingRule(models.Model):
    _name = "helpdesk.routing.rule"
    _description = "Internal Issue Routing Rule"
```

`models/helpdesk_queue_request.py`

```python
from odoo import models


class HelpdeskQueueRequest(models.Model):
    _name = "helpdesk.queue.request"
    _description = "Internal Issue Queue Jump Request"
```

- [ ] **Step 7: เขียน `tests/__init__.py`**

```python
from . import test_helpdesk_ticket
from . import test_helpdesk_routing
from . import test_helpdesk_queue
from . import test_helpdesk_queue_request
from . import test_helpdesk_privacy
```

- [ ] **Step 8: สร้าง test stub ทั้ง 5 ไฟล์** (แต่ละไฟล์ใช้ template เดียวกัน)

`tests/test_helpdesk_ticket.py`, `tests/test_helpdesk_routing.py`, `tests/test_helpdesk_queue.py`, `tests/test_helpdesk_queue_request.py`, `tests/test_helpdesk_privacy.py`

```python
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPlaceholder(TransactionCase):
    def test_module_installed(self):
        self.assertIn("helpdesk.ticket", self.env)
```

- [ ] **Step 9: ติดตั้งโมดูลครั้งแรก (install) แล้วรันเทสต์**

หมายเหตุสำคัญ: `run-tests.ps1` ใช้ `-u` (update) ซึ่งอัปเกรดเฉพาะโมดูลที่ `state=installed` แล้วเท่านั้น โมดูลใหม่ที่ยังไม่ติดตั้งต้องใช้ `-i` ในรอบแรก (ถ้าเคยติดตั้ง scaffold เก่าแล้ว ให้ `-u` แทน)

Run (ครั้งแรก — ยังไม่เคยติดตั้ง):
`pwsh -Command "& .\venv19\Scripts\python.exe .\odoo-bin -c .\odoo.conf -d odoo19_t_internal_issue -i od19_internal_issue --data-dir C:\odoo-dev\od19_internal_issue\data --http-port 8085 --test-enable --test-tags /od19_internal_issue --stop-after-init --logfile .\data_test_run.log"`

Expected: PASS — ติดตั้งสำเร็จและเทสต์ `test_module_installed` ผ่านทั้ง 5 ไฟล์
(ตรวจ `.\data_test_run.log` ว่าไม่มี ERROR/Traceback จาก install)

- [ ] **Step 10: Commit**

```bash
git add custom_addons/od19_internal_issue
git commit -m "feat(od19_internal_issue): scaffold module skeleton"
```

---

## Task T02: ฟิลด์ `helpdesk.ticket` + Fair Priority (Impact × Urgency)

**Files:**
- Modify: `custom_addons/od19_internal_issue/models/helpdesk_ticket.py` (เขียนทับทั้งไฟล์)
- Modify: `custom_addons/od19_internal_issue/tests/test_helpdesk_ticket.py`

- [ ] **Step 1: เขียนเทสต์ที่ยังไม่ผ่าน (RED)**

เขียนทับ `tests/test_helpdesk_ticket.py`

```python
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestInternalIssueTicket(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Ticket = cls.env["helpdesk.ticket"]

    def _create_ticket(self, **overrides):
        vals = {"name": "Test Issue", "description": "<p>desc</p>"}
        vals.update(overrides)
        return self.Ticket.create(vals)

    def test_defaults(self):
        ticket = self._create_ticket()
        self.assertEqual(ticket.visibility, "public")
        self.assertEqual(ticket.reported_by_id, self.env.user)
        self.assertFalse(ticket.emergency)
        self.assertEqual(ticket.consent_state, "accepted")
        self.assertEqual(ticket.issue_stream, "unsure")

    def test_priority_matrix_low(self):
        ticket = self._create_ticket(impact="I1", urgency="U1")
        self.assertEqual(ticket.priority, "0")  # score 2 -> P0

    def test_priority_matrix_medium(self):
        ticket = self._create_ticket(impact="I2", urgency="U1")
        self.assertEqual(ticket.priority, "1")  # score 3 -> P1

    def test_priority_matrix_high(self):
        ticket = self._create_ticket(impact="I3", urgency="U2")
        self.assertEqual(ticket.priority, "2")  # score 5 -> P2

    def test_priority_matrix_critical(self):
        ticket = self._create_ticket(impact="I3", urgency="U3")
        self.assertEqual(ticket.priority, "3")  # score 6 -> P3

    def test_priority_recomputed_on_change(self):
        ticket = self._create_ticket(impact="I1", urgency="U1")
        self.assertEqual(ticket.priority, "0")
        ticket.impact = "I3"
        ticket.urgency = "U3"
        self.assertEqual(ticket.priority, "3")

    def test_jump_window_deadline_set_on_create(self):
        ticket = self._create_ticket()
        self.assertTrue(ticket.jump_window_deadline)
```

- [ ] **Step 2: รันเทสต์ให้เห็น FAIL**

Run: `pwsh -File .\run-tests.ps1 -Module od19_internal_issue -Database odoo19_t_internal_issue -HttpPort 8085`
Expected: FAIL — `AttributeError`/field `issue_stream`/`impact`/`urgency`/`emergency`/`consent_state` ไม่มีใน model (RED ที่ถูกต้อง)

- [ ] **Step 3: เขียน implement — เขียนทับ `models/helpdesk_ticket.py`**

```python
from datetime import timedelta

from odoo import _, api, fields, models

from .internal_issue_common import (
    CONSENT_SELECTION,
    IMPACT_SELECTION,
    ISSUE_STREAM_SELECTION,
    PRIORITY_LABEL,
    URGENCY_SELECTION,
    VISIBILITY_SELECTION,
    score_to_priority,
)


class HelpdeskTicket(models.Model):
    _inherit = "helpdesk.ticket"

    # --- การจัดประเภท (ผู้แจ้งเลือก) ---
    issue_stream = fields.Selection(
        ISSUE_STREAM_SELECTION,
        string="ประเภทเรื่อง",
        default="unsure",
        required=True,
        tracking=True,
        index=True,
        help="หมวดใหญ่ที่ผู้แจ้งเลือก ใช้ route เรื่องเข้าทีมที่ถูกต้อง",
    )

    # --- Fair priority: Impact x Urgency ---
    impact = fields.Selection(
        IMPACT_SELECTION,
        string="ผลกระทบ",
        default="I1",
        required=True,
        tracking=True,
    )
    urgency = fields.Selection(
        URGENCY_SELECTION,
        string="ความเร่งด่วน",
        default="U1",
        required=True,
        tracking=True,
    )
    priority = fields.Selection(
        compute="_compute_priority",
        store=True,
        readonly=False,
        default="1",
        tracking=True,
        help="คำนวณอัตโนมัติจาก Impact x Urgency (ผู้จัดการปรับได้ มี audit)",
    )
    emergency = fields.Boolean(
        string="ฉุกเฉิน",
        default=False,
        tracking=True,
        index=True,
        help="แจ้งเตือนทุกช่องทางทันที แต่การแทรกคิวยังต้องอนุมัติแซงคิว",
    )

    # --- ความเป็นส่วนตัว ---
    visibility = fields.Selection(
        VISIBILITY_SELECTION,
        string="การมองเห็น",
        default="public",
        required=True,
        tracking=True,
        index=True,
    )
    visibility_department_id = fields.Many2one(
        comodel_name="hr.department",
        string="แผนกที่มองเห็น",
        tracking=True,
        index=True,
    )
    reported_by_id = fields.Many2one(
        comodel_name="res.users",
        string="ผู้แจ้ง",
        default=lambda self: self.env.user,
        tracking=True,
        index=True,
    )

    # --- คิว ---
    queue_sequence = fields.Integer(
        string="ลำดับคิว",
        default=10,
        copy=False,
        index=True,
        help="ใช้เป็นตัวตัดสิน FIFO ภายใน priority เดียวกัน (ค่าน้อย = ก่อน)",
    )
    queue_position = fields.Integer(
        compute="_compute_queue_position",
        string="ตำแหน่งในคิว",
    )
    queue_ahead_count = fields.Integer(
        compute="_compute_queue_position",
        string="งานก่อนหน้า",
    )
    is_priority_inserted = fields.Boolean(
        string="ถูกแทรกคิว",
        default=False,
        copy=False,
        tracking=True,
    )
    insert_before_id = fields.Many2one(
        comodel_name="helpdesk.ticket",
        string="แทรกก่อนเรื่อง",
        copy=False,
    )

    # --- การยินยอม / หน้าต่างขอแซงคิว ---
    consent_state = fields.Selection(
        CONSENT_SELECTION,
        string="สถานะการยินยอม",
        default="accepted",
        tracking=True,
        help="ค่าเริ่มต้น = ยินยอมเข้าคิวอัตโนมัติ",
    )
    jump_window_deadline = fields.Datetime(
        string="เปิดให้ขอแซงคิวถึง",
        copy=False,
        help="หลังเวลานี้ ปุ่ม 'ขอแซงคิว' ปิด",
    )

    # --- Handoff -> Knowledge Base (Phase 2) ---
    kb_converted = fields.Boolean(string="แปลงเป็น KB แล้ว", default=False, copy=False)
    kb_article_ref = fields.Char(string="อ้างอิงบทความ KB", copy=False)

    # ------------------------------------------------------------------
    # Compute
    # ------------------------------------------------------------------
    @api.depends("impact", "urgency")
    def _compute_priority(self):
        for rec in self:
            rec.priority = score_to_priority(rec.impact, rec.urgency)

    @api.depends("team_id", "priority", "queue_sequence", "stage_id")
    def _compute_queue_position(self):
        for rec in self:
            rec.queue_position = 0
            rec.queue_ahead_count = 0
            if not rec.team_id or not rec.id:
                continue
            tickets = self.search(
                [
                    ("team_id", "=", rec.team_id.id),
                    ("stage_id.closed", "=", False),
                ],
                order="priority desc, queue_sequence asc, id asc",
            )
            ids = tickets.ids
            if rec.id in ids:
                position = ids.index(rec.id) + 1
                rec.queue_position = position
                rec.queue_ahead_count = position - 1

    # ------------------------------------------------------------------
    # Create / helper
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._apply_routing(vals)
            self._apply_fairness_log_context(vals)
        records = super().create(vals_list)
        for rec in records:
            rec._set_jump_window()
            rec._notify_created()
        return records

    def _apply_fairness_log_context(self, vals):
        """บันทึกเหตุผล priority ลง description ถ้ามีการตั้ง impact/urgency."""
        # nothing to mutate by default; hook for future audit (Phase 2)
        return vals

    def _set_jump_window(self):
        self.ensure_one()
        if self.jump_window_deadline:
            return
        hours = float(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("od19_internal_issue.jump_window_hours", 24)
        )
        self.jump_window_deadline = fields.Datetime.now() + timedelta(hours=hours)

    def _apply_routing(self, vals):
        """เติม team_id/category_id จาก issue_stream + routing rules (ดู T04)."""
        # implementation completed in Task T04
        return vals

    # ------------------------------------------------------------------
    # Notifications
    # ------------------------------------------------------------------
    def _get_notification_partners(self):
        self.ensure_one()
        partners = self.env["res.partner"]
        if self.user_id:
            partners |= self.user_id.partner_id
        if self.reported_by_id:
            partners |= self.reported_by_id.partner_id
        if self.partner_id:
            partners |= self.partner_id
        return partners

    def _notify_created(self):
        self.ensure_one()
        partners = self._get_notification_partners()
        if not partners:
            return
        self.env["notification.service"].notify(
            partners,
            _("เรื่อง %(number)s ถูกสร้างแล้ว") % {"number": self.number},
            event="issue_updated",
            subject=_("สร้างเรื่องใหม่: %s") % self.name,
        )

    def _notify_assigned(self):
        self.ensure_one()
        if not self.user_id:
            return
        self.env["notification.service"].notify(
            self.user_id.partner_id,
            _("คุณได้รับมอบหมายเรื่อง %(number)s: %(title)s")
            % {"number": self.number, "title": self.name},
            event="issue_assigned",
            subject=_("มอบหมายเรื่องใหม่"),
        )

    def write(self, vals):
        res = super().write(vals)
        if "user_id" in vals and vals["user_id"]:
            for record in self:
                record._notify_assigned()
        return res

    # ------------------------------------------------------------------
    # Display helper
    # ------------------------------------------------------------------
    def _priority_label(self):
        self.ensure_one()
        return PRIORITY_LABEL.get(self.priority, self.priority or "")
```

- [ ] **Step 4: รันเทสต์ให้เห็น PASS (GREEN)**

Run: `pwsh -File .\run-tests.ps1 -Module od19_internal_issue -Database odoo19_t_internal_issue -HttpPort 8085`
Expected: PASS — เทสต์ใน `test_helpdesk_ticket.py` ผ่านทั้งหมด (เทสต์ไฟล์อื่นเป็น placeholder)

- [ ] **Step 5: Commit**

```bash
git add custom_addons/od19_internal_issue/models/helpdesk_ticket.py custom_addons/od19_internal_issue/models/internal_issue_common.py custom_addons/od19_internal_issue/tests/test_helpdesk_ticket.py
git commit -m "feat(od19_internal_issue): add fairness/privacy/queue fields to ticket"
```

---

## Task T03: inherit `helpdesk.ticket.team`

**Files:**
- Modify: `custom_addons/od19_internal_issue/models/helpdesk_ticket_team.py`
- Test: ใช้ `tests/test_helpdesk_routing.py` ใน Task T04 (team fields ถูกทดสอบผ่าน routing)

- [ ] **Step 1: เขียน implement**

เขียนทับ `models/helpdesk_ticket_team.py`

```python
from odoo import fields, models

from .internal_issue_common import ISSUE_STREAM_SELECTION


class HelpdeskTicketTeam(models.Model):
    _inherit = "helpdesk.ticket.team"

    issue_stream = fields.Selection(
        ISSUE_STREAM_SELECTION,
        string="ประเภทเรื่องที่รับ",
        help="ใช้ route เรื่องอัตโนมัติเมื่อผู้แจ้งเลือก issue_stream นี้",
    )
    is_triage_team = fields.Boolean(
        string="กล่องกลาง (Triage)",
        default=False,
        help="รับเรื่องที่ผู้แจ้งเลือก 'ไม่แน่ใจ' เพื่อให้ agent จัดต่อ",
    )
    weekly_priority_quota = fields.Integer(
        string="โควตางานด่วน/สัปดาห์",
        default=5,
        help="เพดานจำนวนงาน priority สูงต่อสัปดาห์; เกินโควต้าต้องขออนุมัติแซงคิว",
    )
```

- [ ] **Step 2: ตรวจสอบ static**

Run: `pwsh -Command "& .\venv19\Scripts\python.exe -m py_compile .\custom_addons\od19_internal_issue\models\helpdesk_ticket_team.py"`
Expected: ไม่มี output (ผ่าน)

- [ ] **Step 3: Commit**

```bash
git add custom_addons/od19_internal_issue/models/helpdesk_ticket_team.py
git commit -m "feat(od19_internal_issue): add issue_stream/triage/quota to team"
```

---

## Task T04: `helpdesk.routing.rule` + auto-route on create

**Files:**
- Modify: `custom_addons/od19_internal_issue/models/helpdesk_routing_rule.py`
- Modify: `custom_addons/od19_internal_issue/models/helpdesk_ticket.py` (เติม `_apply_routing`)
- Modify: `custom_addons/od19_internal_issue/tests/test_helpdesk_routing.py`

- [ ] **Step 1: เขียนเทสต์ที่ยังไม่ผ่าน (RED)**

เขียนทับ `tests/test_helpdesk_routing.py`

```python
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestInternalIssueRouting(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Ticket = cls.env["helpdesk.ticket"]
        cls.Team = cls.env["helpdesk.ticket.team"]
        cls.Rule = cls.env["helpdesk.routing.rule"]

        cls.team_it = cls.Team.create(
            {"name": "IT Support (test)", "issue_stream": "it_support"}
        )
        cls.team_triage = cls.Team.create(
            {"name": "Triage (test)", "is_triage_team": True}
        )

    def test_route_by_issue_stream(self):
        ticket = self.Ticket.create(
            {"name": "Printer down", "issue_stream": "it_support"}
        )
        self.assertEqual(ticket.team_id, self.team_it)

    def test_route_unsure_to_triage(self):
        ticket = self.Ticket.create(
            {"name": "ไม่รู้ว่าใครดูแล", "issue_stream": "unsure"}
        )
        self.assertEqual(ticket.team_id, self.team_triage)

    def test_explicit_team_id_is_respected(self):
        ticket = self.Ticket.create(
            {"name": "Explicit", "issue_stream": "it_support", "team_id": self.team_triage.id}
        )
        self.assertEqual(ticket.team_id, self.team_triage)

    def test_routing_rule_keyword_fills_team(self):
        self.Rule.create(
            {
                "name": "Printer keyword",
                "keyword": "printer",
                "issue_stream": "unsure",
                "team_id": self.team_it.id,
                "sequence": 1,
            }
        )
        ticket = self.Ticket.create(
            {"name": "my printer is broken", "issue_stream": "unsure"}
        )
        self.assertEqual(ticket.team_id, self.team_it)
```

- [ ] **Step 2: รันเทสต์ให้เห็น FAIL**

Run: `pwsh -File .\run-tests.ps1 -Module od19_internal_issue -Database odoo19_t_internal_issue -HttpPort 8085`
Expected: FAIL — `helpdesk.routing.rule` ยังไม่มีฟิลด์/ไม่มี logic route (RED)

- [ ] **Step 3: เขียน implement — เขียนทับ `models/helpdesk_routing_rule.py`**

```python
from odoo import api, fields, models

from .internal_issue_common import ISSUE_STREAM_SELECTION


class HelpdeskRoutingRule(models.Model):
    _name = "helpdesk.routing.rule"
    _description = "Internal Issue Routing Rule"
    _order = "sequence, id"

    name = fields.Char(string="ชื่อกฎ", required=True)
    keyword = fields.Char(
        string="คำสำคัญ",
        required=True,
        help="ค้นหาแบบไม่สนตัวพิมพ์ในชื่อเรื่อง + รายละเอียด",
    )
    issue_stream = fields.Selection(
        ISSUE_STREAM_SELECTION,
        string="ประเภทเรื่อง",
        help="ปล่อยว่าง = ใช้กับทุกประเภท",
    )
    team_id = fields.Many2one(comodel_name="helpdesk.ticket.team", string="ทีมปลายทาง")
    category_id = fields.Many2one(
        comodel_name="helpdesk.ticket.category", string="หมวดปลายทาง"
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    @api.model
    def _match_text(self, text):
        """คืน rule แรกที่ keyword ปรากฏใน ``text`` (เรียงตาม sequence)."""
        text = (text or "").lower()
        if not text:
            return self.browse()
        for rule in self.search([("active", "=", True)], order="sequence, id"):
            if rule.keyword and rule.keyword.lower() in text:
                return rule
        return self.browse()
```

- [ ] **Step 4: เติม `_apply_routing` ใน `models/helpdesk_ticket.py`**

แทนที่เมธอด `_apply_routing` (เดิมเป็น stub) ด้วย:

```python
    def _apply_routing(self, vals):
        """เติม team_id/category_id/issue_stream อัตโนมัติจาก issue_stream + routing rules.

        ลำดับ:
        1) ผู้ส่งตั้ง team_id เอง -> เคารพ
        2) issue_stream -> ทีมที่ผูก stream นั้น
        3) 'unsure' -> ทีม Triage
        4) เสริมด้วย helpdesk.routing.rule (keyword) ถ้า team/category ยังว่าง
        """
        if vals.get("team_id"):
            return vals

        Team = self.env["helpdesk.ticket.team"]
        stream = vals.get("issue_stream") or "unsure"

        team = Team.browse()
        if stream == "unsure":
            team = Team.search([("is_triage_team", "=", True)], limit=1)
        else:
            team = Team.search([("issue_stream", "=", stream)], limit=1)

        # keyword rules (ใช้เมื่อยังไม่ได้ทีม หรือหา category เสริม)
        text = "%s %s" % (vals.get("name") or "", vals.get("description") or "")
        rule = self.env["helpdesk.routing.rule"]._match_text(text)
        if rule:
            if not team and rule.team_id:
                team = rule.team_id
            if not vals.get("category_id") and rule.category_id:
                vals["category_id"] = rule.category_id.id

        if team:
            vals["team_id"] = team.id
        return vals
```

- [ ] **Step 5: รันเทสต์ให้เห็น PASS (GREEN)**

Run: `pwsh -File .\run-tests.ps1 -Module od19_internal_issue -Database odoo19_t_internal_issue -HttpPort 8085`
Expected: PASS — เทสต์ routing ผ่านทั้งหมด

- [ ] **Step 6: Commit**

```bash
git add custom_addons/od19_internal_issue/models/helpdesk_routing_rule.py custom_addons/od19_internal_issue/models/helpdesk_ticket.py custom_addons/od19_internal_issue/tests/test_helpdesk_routing.py
git commit -m "feat(od19_internal_issue): add routing rules and auto-route on create"
```

---

## Task T05: คิวต่อทีม + ตำแหน่งคิว (priority → FIFO)

**Files:**
- Modify: `custom_addons/od19_internal_issue/tests/test_helpdesk_queue.py`

> หมายเหตุ: ฟิลด์และ compute ถูกใส่ไว้แล้วใน Task T02 — Task นี้คือ "ล็อกพฤติกรรมด้วยเทสต์" (behavior lock)

- [ ] **Step 1: เขียนเทสต์ (RED → ต้อง FAIL ถ้า compute ผิด)**

เขียนทับ `tests/test_helpdesk_queue.py`

```python
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestInternalIssueQueue(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Ticket = cls.env["helpdesk.ticket"]
        cls.Team = cls.env["helpdesk.ticket.team"]
        cls.team = cls.Team.create({"name": "Queue Team (test)", "is_triage_team": True})
        # stage ที่ยังไม่ปิด สำหรับทดสอบคิว
        stage = cls.env["helpdesk.ticket.stage"].search([("closed", "=", False)], limit=1)
        cls.stage = stage

    def _create(self, name, priority, queue_sequence=10):
        return self.Ticket.create(
            {
                "name": name,
                "team_id": self.team.id,
                "stage_id": self.stage.id,
                "priority": priority,
                "queue_sequence": queue_sequence,
            }
        )

    def test_order_priority_then_fifo(self):
        low = self._create("low", "0", 10)
        high = self._create("high", "3", 10)
        high2 = self._create("high2", "3", 20)
        # high (seq10) มาก่อน high2 (seq20) ตาม FIFO; ทั้งคู่อยู่ก่อน low
        self.assertEqual(high.queue_position, 1)
        self.assertEqual(high2.queue_position, 2)
        self.assertEqual(low.queue_position, 3)

    def test_ahead_count(self):
        first = self._create("first", "1", 10)
        second = self._create("second", "1", 20)
        self.assertEqual(first.queue_ahead_count, 0)
        self.assertEqual(second.queue_ahead_count, 1)

    def test_closed_stage_not_counted(self):
        a = self._create("a", "1", 10)
        closed_stage = self.env["helpdesk.ticket.stage"].search(
            [("closed", "=", True)], limit=1
        )
        b = self._create("b", "1", 20)
        b.stage_id = closed_stage
        self.assertEqual(b.queue_position, 0)
        self.assertEqual(a.queue_position, 1)
```

- [ ] **Step 2: รันเทสต์ให้เห็น FAIL/PASS**

Run: `pwsh -File .\run-tests.ps1 -Module od19_internal_issue -Database odoo19_t_internal_issue -HttpPort 8085`
Expected: PASS — ถ้า FAIL แสดงว่า `_compute_queue_position` ใน Task T02 ต้องแก้ให้ตรง ordering

- [ ] **Step 3: Commit**

```bash
git add custom_addons/od19_internal_issue/tests/test_helpdesk_queue.py
git commit -m "test(od19_internal_issue): lock queue ordering and position behavior"
```

---

## Task T06: `helpdesk.queue.request` + อนุมัติ 2 ชั้น + แทรกคิว + หมดอายุ

**Files:**
- Modify: `custom_addons/od19_internal_issue/models/helpdesk_queue_request.py`
- Modify: `custom_addons/od19_internal_issue/tests/test_helpdesk_queue_request.py`
- Modify: `custom_addons/od19_internal_issue/models/helpdesk_ticket.py` (เพิ่ม `action_request_jump`)

- [ ] **Step 1: เขียนเทสต์ที่ยังไม่ผ่าน (RED)**

เขียนทับ `tests/test_helpdesk_queue_request.py`

```python
from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestInternalIssueQueueRequest(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Ticket = cls.env["helpdesk.ticket"]
        cls.Team = cls.env["helpdesk.ticket.team"]
        cls.Request = cls.env["helpdesk.queue.request"]
        cls.team = cls.Team.create({"name": "QR Team (test)", "is_triage_team": True})
        cls.stage = cls.env["helpdesk.ticket.stage"].search(
            [("closed", "=", False)], limit=1
        )
        cls.reporter = cls.env["res.users"].create(
            {"name": "Reporter", "login": "reporter_issue_test"}
        )
        cls.head_a = cls.env["res.users"].create(
            {"name": "Head A", "login": "head_a_issue_test"}
        )
        cls.head_b = cls.env["res.users"].create(
            {"name": "Head B", "login": "head_b_issue_test"}
        )

    def _ticket(self, name, queue_sequence=10):
        return self.Ticket.create(
            {
                "name": name,
                "team_id": self.team.id,
                "stage_id": self.stage.id,
                "queue_sequence": queue_sequence,
                "reported_by_id": self.reporter.id,
            }
        )

    @patch("requests.post")
    def test_two_layer_approval_inserts_ticket(self, mock_post):
        mock_post.return_value.status_code = 200
        target = self._ticket("target")
        ticket = self._ticket("jumper", queue_sequence=50)

        request = self.Request.create(
            {
                "ticket_id": ticket.id,
                "requested_by": self.reporter.id,
                "reason": "ลูกค้ารออยู่",
                "approver_reporter_head_id": self.head_a.id,
                "approver_team_head_id": self.head_b.id,
                "insert_before_id": target.id,
            }
        )
        request.action_submit()
        self.assertEqual(request.state, "waiting_reporter_head")

        request.action_approve_reporter_head()
        self.assertEqual(request.state, "waiting_team_head")

        request.action_approve_team_head()
        self.assertEqual(request.state, "approved")
        ticket.invalidate_recordset()
        self.assertTrue(ticket.is_priority_inserted)
        self.assertEqual(ticket.insert_before_id, target)
        self.assertLess(ticket.queue_sequence, target.queue_sequence)

    @patch("requests.post")
    def test_expiry_when_deadline_passed(self, mock_post):
        mock_post.return_value.status_code = 200
        ticket = self._ticket("expire-me")
        request = self.Request.create(
            {
                "ticket_id": ticket.id,
                "requested_by": self.reporter.id,
                "reason": "urgent",
                "approver_reporter_head_id": self.head_a.id,
                "approver_team_head_id": self.head_b.id,
                "deadline": fields.Datetime.now() - timedelta(hours=1),
            }
        )
        request.action_submit()
        self.Request._cron_expire_stale_requests()
        request.invalidate_recordset()
        self.assertEqual(request.state, "expired")
```

- [ ] **Step 2: รันเทสต์ให้เห็น FAIL**

Run: `pwsh -File .\run-tests.ps1 -Module od19_internal_issue -Database odoo19_t_internal_issue -HttpPort 8085`
Expected: FAIL — `helpdesk.queue.request` ไม่มีฟิลด์/workflow (RED)

- [ ] **Step 3: เขียน implement — เขียนทับ `models/helpdesk_queue_request.py`**

```python
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .internal_issue_common import QUEUE_REQUEST_STATE


class HelpdeskQueueRequest(models.Model):
    _name = "helpdesk.queue.request"
    _description = "Internal Issue Queue Jump Request"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    name = fields.Char(string="เลขที่คำขอ", readonly=True, default="ใหม่")
    ticket_id = fields.Many2one(
        comodel_name="helpdesk.ticket",
        string="เรื่อง",
        required=True,
        ondelete="cascade",
    )
    requested_by = fields.Many2one(
        comodel_name="res.users",
        string="ผู้ขอ",
        default=lambda self: self.env.user,
        required=True,
    )
    reason = fields.Text(string="เหตุผลการขอแซงคิว", required=True)
    state = fields.Selection(
        QUEUE_REQUEST_STATE, string="สถานะ", default="draft", tracking=True
    )
    approver_reporter_head_id = fields.Many2one(
        comodel_name="res.users", string="หัวหน้าแผนกผู้แจ้ง"
    )
    approver_team_head_id = fields.Many2one(
        comodel_name="res.users", string="หัวหน้าทีมเจ้าของคิว"
    )
    reporter_head_approved = fields.Boolean(string="หัวหน้าแผนกอนุมัติ")
    team_head_approved = fields.Boolean(string="หัวหน้าทีมอนุมัติ")
    insert_before_id = fields.Many2one(
        comodel_name="helpdesk.ticket",
        string="แทรกก่อนเรื่อง",
        help="ผู้อนุมัติเลือกตำแหน่งแทรกในคิว",
    )
    deadline = fields.Datetime(string="หมดอายุเมื่อ")
    decision_note = fields.Text(string="บันทึกการตัดสินใจ")

    # ------------------------------------------------------------------
    # Workflow
    # ------------------------------------------------------------------
    def action_submit(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(_("ส่งได้เฉพาะคำขอสถานะร่างเท่านั้น"))
            if not rec.deadline:
                rec.deadline = fields.Datetime.now() + timedelta(hours=24)
            rec.state = "waiting_reporter_head"
            rec.ticket_id.consent_state = "jump_requested"
            rec._notify_approvers()

    def action_approve_reporter_head(self):
        for rec in self:
            if rec.state != "waiting_reporter_head":
                raise UserError(_("คำขอนี้ยังไม่พร้อมให้หัวหน้าแผนกอนุมัติ"))
            rec.reporter_head_approved = True
            rec.state = "waiting_team_head"
            rec._notify_approvers()

    def action_approve_team_head(self):
        for rec in self:
            if rec.state != "waiting_team_head":
                raise UserError(_("คำขอนี้ยังไม่พร้อมให้หัวหน้าทีมอนุมัติ"))
            rec.team_head_approved = True
            rec.state = "approved"
            rec._apply_insertion()
            rec._notify_outcome()

    def action_reject(self):
        for rec in self:
            rec.state = "rejected"
            rec.ticket_id.consent_state = "accepted"
            rec._notify_outcome()

    def _apply_insertion(self):
        self.ensure_one()
        ticket = self.ticket_id
        if not ticket:
            return
        if self.insert_before_id:
            ticket.queue_sequence = self.insert_before_id.queue_sequence - 1
        else:
            ticket.queue_sequence = 0
        ticket.is_priority_inserted = True
        ticket.insert_before_id = self.insert_before_id
        ticket.message_post(
            body=_("คำขอแซงคิว %(name)s อนุมัติครบแล้ว — ถูกแทรกคิวก่อน '%(before)s'")
            % {
                "name": self.name,
                "before": self.insert_before_id.name or "หัวคิว",
            }
        )

    # ------------------------------------------------------------------
    # Cron
    # ------------------------------------------------------------------
    @api.model
    def _cron_expire_stale_requests(self):
        now = fields.Datetime.now()
        stale = self.search(
            [
                ("state", "in", ("waiting_reporter_head", "waiting_team_head")),
                ("deadline", "!=", False),
                ("deadline", "<", now),
            ]
        )
        for rec in stale:
            rec.state = "expired"
            if rec.ticket_id:
                rec.ticket_id.consent_state = "accepted"
            rec._notify_outcome()

    # ------------------------------------------------------------------
    # Notifications
    # ------------------------------------------------------------------
    def _notify_approvers(self):
        self.ensure_one()
        partners = self.env["res.partner"]
        for user in (self.approver_reporter_head_id, self.approver_team_head_id):
            if user:
                partners |= user.partner_id
        if partners:
            self.env["notification.service"].notify(
                partners,
                _("คำขอแซงคิวเรื่อง %(number)s รอการอนุมัติ")
                % {"number": self.ticket_id.number or ""},
                event="issue_updated",
                subject=_("คำขอแซงคิวรออนุมัติ"),
            )

    def _notify_outcome(self):
        self.ensure_one()
        if not self.requested_by:
            return
        self.env["notification.service"].notify(
            self.requested_by.partner_id,
            _("คำขอแซงคิวเรื่อง %(number)s: %(state)s")
            % {
                "number": self.ticket_id.number or "",
                "state": dict(QUEUE_REQUEST_STATE).get(self.state, self.state),
            },
            event="issue_updated",
            subject=_("ผลการขอแซงคิว"),
        )
```

- [ ] **Step 4: เพิ่ม `action_request_jump` ใน `models/helpdesk_ticket.py`**

แทรกเมธอดนี้ต่อจาก `_set_jump_window`:

```python
    def action_request_jump(self):
        """เปิดคำขอแซงคิว (ถูกเรียกจากปุ่มบนฟอร์ม)."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "helpdesk.queue.request",
            "view_mode": "form",
            "target": "current",
            "context": {"default_ticket_id": self.id},
        }
```

- [ ] **Step 5: รันเทสต์ให้เห็น PASS (GREEN)**

Run: `pwsh -File .\run-tests.ps1 -Module od19_internal_issue -Database odoo19_t_internal_issue -HttpPort 8085`
Expected: PASS — เทสต์ queue request ผ่าน (2 ชั้น + expiry)

- [ ] **Step 6: Commit**

```bash
git add custom_addons/od19_internal_issue/models/helpdesk_queue_request.py custom_addons/od19_internal_issue/models/helpdesk_ticket.py custom_addons/od19_internal_issue/tests/test_helpdesk_queue_request.py
git commit -m "feat(od19_internal_issue): add two-layer queue jump approval"
```

---

## Task T07: Security — access rights + record rules

**Files:**
- Modify: `custom_addons/od19_internal_issue/security/ir.model.access.csv`
- Modify: `custom_addons/od19_internal_issue/security/internal_issue_security.xml`
- Modify: `custom_addons/od19_internal_issue/security/od19_department_rule.xml`
- Modify: `custom_addons/od19_internal_issue/tests/test_helpdesk_privacy.py`

> หมายเหตุ: แก้จาก scaffold เดิม — เปลี่ยน `department_id` → `visibility_department_id` (ดู D2) และเพิ่ม access สำหรับโมเดลใหม่

- [ ] **Step 1: เขียนเทสต์ที่ยังไม่ผ่าน (RED)**

เขียนทับ `tests/test_helpdesk_privacy.py`

```python
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestInternalIssuePrivacy(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Ticket = cls.env["helpdesk.ticket"]
        cls.user_a = cls.env["res.users"].create(
            {"name": "User A", "login": "priv_a_issue_test"}
        )
        cls.user_b = cls.env["res.users"].create(
            {"name": "User B", "login": "priv_b_issue_test"}
        )

    def _ticket(self, visibility, **overrides):
        vals = {
            "name": "priv",
            "visibility": visibility,
            "reported_by_id": self.user_a.id,
        }
        vals.update(overrides)
        return self.Ticket.create(vals)

    def test_public_visible_to_others(self):
        ticket = self._ticket("public")
        self.assertTrue(
            ticket.with_user(self.user_b).read(["name"])
        )

    def test_private_hidden_from_others(self):
        ticket = self._ticket("private")
        visible = self.Ticket.with_user(self.user_b).search(
            [("id", "=", ticket.id)]
        )
        self.assertFalse(visible)

    def test_private_visible_to_reporter(self):
        ticket = self._ticket("private")
        visible = self.Ticket.with_user(self.user_a).search(
            [("id", "=", ticket.id)]
        )
        self.assertEqual(visible, ticket)
```

- [ ] **Step 2: รันเทสต์ให้เห็น FAIL**

Run: `pwsh -File .\run-tests.ps1 -Module od19_internal_issue -Database odoo19_t_internal_issue -HttpPort 8085`
Expected: FAIL — `helpdesk.queue.request` ไม่มี access → error ตอน test setup/create; หรือ rule `visibility` อ้าง `department_id` ที่ไม่มีแล้ว (RED)

- [ ] **Step 3: เขียน `security/ir.model.access.csv`**

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_helpdesk_queue_request_user,helpdesk.queue.request.user,model_helpdesk_queue_request,base.group_user,1,1,1,0
access_helpdesk_queue_request_manager,helpdesk.queue.request.manager,model_helpdesk_queue_request,helpdesk_mgmt.group_helpdesk_manager,1,1,1,1
access_helpdesk_routing_rule_user,helpdesk.routing.rule.user,model_helpdesk_routing_rule,base.group_user,1,0,0,0
access_helpdesk_routing_rule_manager,helpdesk.routing.rule.manager,model_helpdesk_routing_rule,helpdesk_mgmt.group_helpdesk_manager,1,1,1,1
```

- [ ] **Step 4: เขียน `security/internal_issue_security.xml`**

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo noupdate="1">

    <!--
        Visibility rule for helpdesk.ticket:
        - public: everyone sees it
        - department: only users from the given (visibility) department
        - private: only the reporter or the assignee
    -->
    <record id="internal_issue_visibility_rule" model="ir.rule">
        <field name="name">Internal Issue: visibility control</field>
        <field name="model_id" ref="helpdesk_mgmt.model_helpdesk_ticket"/>
        <field name="domain_force">[
            '|', '|',
            ('visibility', '=', 'public'),
            '&amp;',
                ('visibility', '=', 'department'),
                ('visibility_department_id', 'in', [user.employee_id.department_id.id, False]),
            '&amp;',
                ('visibility', '=', 'private'),
                '|',
                    ('reported_by_id', '=', user.id),
                    ('user_id', '=', user.id)
        ]</field>
        <field name="groups" eval="[(4, ref('base.group_user'))]"/>
    </record>

</odoo>
```

- [ ] **Step 5: เขียน `security/od19_department_rule.xml`**

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <!-- ขอบเขตแผนก: ผู้ใช้ที่มี role แผนกจะเห็นเฉพาะเรื่องของแผนกตัวเอง
         และเรื่องที่ยังไม่ระบุแผนก (Fail-safe) -->
    <record id="rule_helpdesk_ticket_od19_department" model="ir.rule">
        <field name="name">Helpdesk Ticket: เฉพาะแผนกของตัวเอง / Own Department</field>
        <field name="model_id" ref="model_helpdesk_ticket"/>
        <field name="domain_force">['|', ('visibility_department_id', '=', user.od19_department_id.id), ('visibility_department_id', '=', False)]</field>
        <field name="groups" eval="[(4, ref('od19_security_roles.group_od19_department_scope'))]"/>
        <field name="perm_read" eval="True"/>
        <field name="perm_write" eval="True"/>
        <field name="perm_create" eval="False"/>
        <field name="perm_unlink" eval="True"/>
    </record>

    <!-- เห็นทุกแผนก: กฎระดับกลุ่มถูก OR กัน -> กลุ่มนี้ชนะ scope rule เสมอ -->
    <record id="rule_helpdesk_ticket_od19_department_all" model="ir.rule">
        <field name="name">Helpdesk Ticket: ทุกแผนก / All Departments</field>
        <field name="model_id" ref="model_helpdesk_ticket"/>
        <field name="domain_force">[(1, '=', 1)]</field>
        <field name="groups" eval="[(4, ref('od19_security_roles.group_od19_department_all'))]"/>
    </record>
</odoo>
```

- [ ] **Step 6: รันเทสต์ให้เห็น PASS (GREEN)**

Run: `pwsh -File .\run-tests.ps1 -Module od19_internal_issue -Database odoo19_t_internal_issue -HttpPort 8085`
Expected: PASS — เทสต์ privacy ผ่าน; ไม่มี warning "model has no access rules"

- [ ] **Step 7: Commit**

```bash
git add custom_addons/od19_internal_issue/security custom_addons/od19_internal_issue/tests/test_helpdesk_privacy.py
git commit -m "feat(od19_internal_issue): add access rights and privacy rules"
```

---

## Task T08: Data — teams 4 + stages ไทย 6 + routing rules + cron

**Files:**
- Modify: `custom_addons/od19_internal_issue/data/internal_issue_data.xml`
- Modify: `custom_addons/od19_internal_issue/data/internal_issue_cron.xml`

- [ ] **Step 1: เขียน `data/internal_issue_data.xml`**

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo noupdate="1">

    <!-- Teams (ภายใน) -->
    <record id="team_issue_it_support" model="helpdesk.ticket.team">
        <field name="name">IT Support</field>
        <field name="issue_stream">it_support</field>
        <field name="sequence">10</field>
        <field name="user_ids" eval="[(4, ref('base.user_admin'))]"/>
    </record>
    <record id="team_issue_improvement" model="helpdesk.ticket.team">
        <field name="name">ข้อเสนอแนะปรับปรุง</field>
        <field name="issue_stream">improvement</field>
        <field name="sequence">20</field>
    </record>
    <record id="team_issue_iso_capa" model="helpdesk.ticket.team">
        <field name="name">คุณภาพ / ISO (CAPA)</field>
        <field name="issue_stream">iso_capa</field>
        <field name="sequence">30</field>
    </record>
    <record id="team_issue_triage" model="helpdesk.ticket.team">
        <field name="name">กล่องกลาง (Triage)</field>
        <field name="is_triage_team" eval="True"/>
        <field name="sequence">40</field>
        <field name="user_ids" eval="[(4, ref('base.user_admin'))]"/>
    </record>

    <!-- Stages (ป้ายไทย) ผูกกับทีมภายในทั้งหมด -->
    <record id="stage_issue_new" model="helpdesk.ticket.stage">
        <field name="name">ใหม่</field>
        <field name="sequence">1</field>
        <field name="unattended" eval="True"/>
        <field name="team_ids" eval="[(6, 0, [ref('team_issue_it_support'), ref('team_issue_improvement'), ref('team_issue_iso_capa'), ref('team_issue_triage')])]"/>
    </record>
    <record id="stage_issue_assigned" model="helpdesk.ticket.stage">
        <field name="name">มอบหมายแล้ว</field>
        <field name="sequence">2</field>
        <field name="team_ids" eval="[(6, 0, [ref('team_issue_it_support'), ref('team_issue_improvement'), ref('team_issue_iso_capa'), ref('team_issue_triage')])]"/>
    </record>
    <record id="stage_issue_in_progress" model="helpdesk.ticket.stage">
        <field name="name">กำลังดำเนินการ</field>
        <field name="sequence">3</field>
        <field name="team_ids" eval="[(6, 0, [ref('team_issue_it_support'), ref('team_issue_improvement'), ref('team_issue_iso_capa'), ref('team_issue_triage')])]"/>
    </record>
    <record id="stage_issue_waiting" model="helpdesk.ticket.stage">
        <field name="name">รอผู้แจ้ง</field>
        <field name="sequence">4</field>
        <field name="team_ids" eval="[(6, 0, [ref('team_issue_it_support'), ref('team_issue_improvement'), ref('team_issue_iso_capa'), ref('team_issue_triage')])]"/>
    </record>
    <record id="stage_issue_resolved" model="helpdesk.ticket.stage">
        <field name="name">แก้ไขแล้ว</field>
        <field name="sequence">5</field>
        <field name="team_ids" eval="[(6, 0, [ref('team_issue_it_support'), ref('team_issue_improvement'), ref('team_issue_iso_capa'), ref('team_issue_triage')])]"/>
    </record>
    <record id="stage_issue_closed" model="helpdesk.ticket.stage">
        <field name="name">ปิด</field>
        <field name="sequence">6</field>
        <field name="closed" eval="True"/>
        <field name="fold" eval="True"/>
        <field name="team_ids" eval="[(6, 0, [ref('team_issue_it_support'), ref('team_issue_improvement'), ref('team_issue_iso_capa'), ref('team_issue_triage')])]"/>
    </record>

    <!-- Routing rules ตัวอย่าง (แก้/เพิ่มได้จาก Settings) -->
    <record id="routing_rule_it_network" model="helpdesk.routing.rule">
        <field name="name">IT: อินเทอร์เน็ต/เน็ตเวิร์ก</field>
        <field name="keyword">internet</field>
        <field name="issue_stream">it_support</field>
        <field name="sequence">10</field>
    </record>
    <record id="routing_rule_it_printer" model="helpdesk.routing.rule">
        <field name="name">IT: เครื่องพิมพ์</field>
        <field name="keyword">printer</field>
        <field name="issue_stream">it_support</field>
        <field name="sequence">20</field>
    </record>

    <!-- Config: ระยะเวลาเปิดปุ่มขอแซงคิว (ชั่วโมง) -->
    <record id="config_jump_window_hours" model="ir.config_parameter">
        <field name="key">od19_internal_issue.jump_window_hours</field>
        <field name="value">24</field>
    </record>

</odoo>
```

- [ ] **Step 2: เขียน `data/internal_issue_cron.xml`**

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="ir_cron_queue_request_expire" model="ir.cron">
        <field name="name">Internal Issue: Expire stale queue requests</field>
        <field name="model_id" ref="model_helpdesk_queue_request"/>
        <field name="state">code</field>
        <field name="code">model._cron_expire_stale_requests()</field>
        <field name="interval_number">1</field>
        <field name="interval_type">hours</field>
        <field name="numbercall">-1</field>
        <field name="active" eval="True"/>
    </record>
</odoo>
```

- [ ] **Step 3: รันเทสต์ (ตรวจว่า data โหลดได้ ไม่มี error)**

Run: `pwsh -File .\run-tests.ps1 -Module od19_internal_issue -Database odoo19_t_internal_issue -HttpPort 8085`
Expected: PASS — เทสต์เดิมยังผ่าน; log ไม่มี XML parse/loading error

- [ ] **Step 4: ตรวจ data ถูกสร้างจริง (manual)**

Run: `pwsh -Command "& .\venv19\Scripts\python.exe .\odoo-bin shell -c .\odoo.conf -d odoo19_t_internal_issue --data-dir C:\odoo-dev\od19_internal_issue\data --http-port 8085 --no-http"` แล้วพิมพ์:
`self.env.ref('od19_internal_issue.team_issue_triage').is_triage_team`
Expected: `True`

- [ ] **Step 5: Commit**

```bash
git add custom_addons/od19_internal_issue/data
git commit -m "feat(od19_internal_issue): add internal teams, thai stages and routing data"
```

---

## Task T09: Views — ticket inherit + queue request + routing rule

**Files:**
- Modify: `custom_addons/od19_internal_issue/views/helpdesk_ticket_views.xml`
- Modify: `custom_addons/od19_internal_issue/views/helpdesk_queue_request_views.xml`
- Modify: `custom_addons/od19_internal_issue/views/helpdesk_routing_rule_views.xml`

- [ ] **Step 1: เขียน `views/helpdesk_ticket_views.xml`**

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>

    <!-- Extend ticket form -->
    <record id="helpdesk_ticket_view_form_inherit_internal" model="ir.ui.view">
        <field name="name">helpdesk.ticket.form.internal</field>
        <field name="model">helpdesk.ticket</field>
        <field name="inherit_id" ref="helpdesk_mgmt.ticket_view_form"/>
        <field name="arch" type="xml">
            <xpath expr="//field[@name='category_id']" position="after">
                <field name="issue_stream"/>
                <field name="reported_by_id"/>
                <field name="visibility"/>
                <field name="visibility_department_id"
                       invisible="visibility != 'department'"/>
                <field name="emergency"/>
            </xpath>

            <xpath expr="//form/header" position="inside">
                <button name="action_request_jump" type="object"
                        string="ขอแซงคิว" class="btn-warning"
                        invisible="consent_state == 'jump_requested'"/>
            </xpath>

            <xpath expr="//notebook/page[@name='other_info']" position="after">
                <page string="ความเป็นธรรม &amp; คิว" name="internal_fairness">
                    <group>
                        <group string="เกณฑ์ความสำคัญ">
                            <field name="impact"/>
                            <field name="urgency"/>
                            <field name="priority" readonly="1"/>
                            <field name="emergency"/>
                        </group>
                        <group string="คิว">
                            <field name="queue_sequence"/>
                            <field name="queue_position" readonly="1"/>
                            <field name="queue_ahead_count" readonly="1"/>
                            <field name="is_priority_inserted" readonly="1"/>
                            <field name="insert_before_id" readonly="1"/>
                        </group>
                    </group>
                    <group>
                        <group string="ความเป็นส่วนตัว">
                            <field name="visibility"/>
                            <field name="visibility_department_id"/>
                            <field name="reported_by_id"/>
                        </group>
                        <group string="การยินยอม">
                            <field name="consent_state"/>
                            <field name="jump_window_deadline"/>
                        </group>
                    </group>
                    <group string="Knowledge Base (Phase 2)">
                        <field name="kb_converted"/>
                        <field name="kb_article_ref"/>
                    </group>
                </page>
            </xpath>
        </field>
    </record>

    <!-- Extend ticket list view -->
    <record id="ticket_view_tree_inherit_internal" model="ir.ui.view">
        <field name="name">helpdesk.ticket.list.internal</field>
        <field name="model">helpdesk.ticket</field>
        <field name="inherit_id" ref="helpdesk_mgmt.ticket_view_tree"/>
        <field name="arch" type="xml">
            <xpath expr="//field[@name='name']" position="after">
                <field name="issue_stream"/>
                <field name="queue_position"/>
                <field name="visibility"/>
                <field name="emergency" widget="boolean_toggle"/>
            </xpath>
        </field>
    </record>

    <!-- Extend ticket search view -->
    <record id="helpdesk_ticket_view_search_inherit_internal" model="ir.ui.view">
        <field name="name">helpdesk.ticket.search.internal</field>
        <field name="model">helpdesk.ticket</field>
        <field name="inherit_id" ref="helpdesk_mgmt.helpdesk_ticket_view_search"/>
        <field name="arch" type="xml">
            <xpath expr="//field[@name='name']" position="after">
                <field name="issue_stream"/>
                <field name="visibility"/>
                <field name="visibility_department_id"/>
                <field name="reported_by_id"/>
                <field name="emergency"/>
            </xpath>
            <xpath expr="//search/group[1]" position="inside">
                <filter string="ฉุกเฉิน" name="filter_emergency"
                        domain="[('emergency','=',True)]"/>
                <filter string="สาธารณะ" name="filter_public"
                        domain="[('visibility','=','public')]"/>
                <filter string="เฉพาะแผนก" name="filter_department"
                        domain="[('visibility','=','department')]"/>
                <filter string="ส่วนตัว" name="filter_private"
                        domain="[('visibility','=','private')]"/>
            </xpath>
        </field>
    </record>

</odoo>
```

- [ ] **Step 2: เขียน `views/helpdesk_queue_request_views.xml`**

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>

    <record id="view_helpdesk_queue_request_tree" model="ir.ui.view">
        <field name="name">helpdesk.queue.request.list</field>
        <field name="model">helpdesk.queue.request</field>
        <field name="arch" type="xml">
            <list string="คำขอแซงคิว">
                <field name="name"/>
                <field name="ticket_id"/>
                <field name="requested_by"/>
                <field name="approver_reporter_head_id"/>
                <field name="approver_team_head_id"/>
                <field name="state" widget="badge"/>
                <field name="deadline"/>
            </list>
        </field>
    </record>

    <record id="view_helpdesk_queue_request_form" model="ir.ui.view">
        <field name="name">helpdesk.queue.request.form</field>
        <field name="model">helpdesk.queue.request</field>
        <field name="arch" type="xml">
            <form string="คำขอแซงคิว">
                <header>
                    <button name="action_submit" type="object" string="ส่งคำขอ"
                            class="btn-primary" invisible="state != 'draft'"/>
                    <button name="action_approve_reporter_head" type="object"
                            string="หัวหน้าแผนกอนุมัติ" class="btn-success"
                            invisible="state != 'waiting_reporter_head'"/>
                    <button name="action_approve_team_head" type="object"
                            string="หัวหน้าทีมอนุมัติ" class="btn-success"
                            invisible="state != 'waiting_team_head'"/>
                    <button name="action_reject" type="object" string="ปฏิเสธ"
                            class="btn-danger"
                            invisible="state not in ('draft','waiting_reporter_head','waiting_team_head')"/>
                    <field name="state" widget="statusbar"
                           statusbar_visible="draft,waiting_reporter_head,waiting_team_head,approved"
                           statusbar_colors='{"rejected":"danger","expired":"warning"}'/>
                </header>
                <sheet>
                    <group>
                        <group>
                            <field name="ticket_id"/>
                            <field name="requested_by"/>
                            <field name="reason"/>
                        </group>
                        <group>
                            <field name="approver_reporter_head_id"/>
                            <field name="reporter_head_approved"/>
                            <field name="approver_team_head_id"/>
                            <field name="team_head_approved"/>
                        </group>
                    </group>
                    <group string="ตำแหน่งแทรก (ผู้อนุมัติเลือก)">
                        <field name="insert_before_id"/>
                        <field name="deadline"/>
                        <field name="decision_note"/>
                    </group>
                </sheet>
                <chatter/>
            </form>
        </field>
    </record>

    <record id="action_helpdesk_queue_request" model="ir.actions.act_window">
        <field name="name">คำขอแซงคิว</field>
        <field name="res_model">helpdesk.queue.request</field>
        <field name="view_mode">list,form</field>
        <field name="path">internal-issue-queue-requests</field>
    </record>

</odoo>
```

- [ ] **Step 3: เขียน `views/helpdesk_routing_rule_views.xml`**

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>

    <record id="view_helpdesk_routing_rule_tree" model="ir.ui.view">
        <field name="name">helpdesk.routing.rule.list</field>
        <field name="model">helpdesk.routing.rule</field>
        <field name="arch" type="xml">
            <list string="กฎการส่งเรื่อง" editable="bottom">
                <field name="sequence" widget="handle"/>
                <field name="name"/>
                <field name="keyword"/>
                <field name="issue_stream"/>
                <field name="team_id"/>
                <field name="category_id"/>
                <field name="active"/>
            </list>
        </field>
    </record>

    <record id="view_helpdesk_routing_rule_form" model="ir.ui.view">
        <field name="name">helpdesk.routing.rule.form</field>
        <field name="model">helpdesk.routing.rule</field>
        <field name="arch" type="xml">
            <form string="กฎการส่งเรื่อง">
                <sheet>
                    <group>
                        <field name="name"/>
                        <field name="keyword"/>
                        <field name="issue_stream"/>
                        <field name="team_id"/>
                        <field name="category_id"/>
                        <field name="sequence"/>
                        <field name="active"/>
                    </group>
                </sheet>
            </form>
        </field>
    </record>

    <record id="action_helpdesk_routing_rule" model="ir.actions.act_window">
        <field name="name">กฎการส่งเรื่องอัตโนมัติ</field>
        <field name="res_model">helpdesk.routing.rule</field>
        <field name="view_mode">list,form</field>
        <field name="path">internal-issue-routing-rules</field>
    </record>

</odoo>
```

- [ ] **Step 4: ติดตั้ง/อัปเดตและตรวจ XML valid**

Run: `pwsh -File .\run-tests.ps1 -Module od19_internal_issue -Database odoo19_t_internal_issue -HttpPort 8085`
Expected: PASS — ไม่มี XML parse error / ไม่มี `Field ... does not exist`

- [ ] **Step 5: Commit**

```bash
git add custom_addons/od19_internal_issue/views
git commit -m "feat(od19_internal_issue): add ticket, queue request and routing views"
```

---

## Task T10: Menus

**Files:**
- Modify: `custom_addons/od19_internal_issue/views/internal_issue_menus.xml`

- [ ] **Step 1: เขียน `views/internal_issue_menus.xml`**

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>

    <!-- Actions (เรื่องของฉัน / เรื่องทั้งหมด) -->
    <record id="action_internal_issue_my" model="ir.actions.act_window">
        <field name="name">เรื่องของฉัน</field>
        <field name="res_model">helpdesk.ticket</field>
        <field name="view_mode">list,kanban,form</field>
        <field name="domain">[('reported_by_id', '=', uid)]</field>
        <field name="context">{'search_default_filter_my_reported': 1}</field>
        <field name="path">internal-issue-my</field>
    </record>
    <record id="action_internal_issue_all" model="ir.actions.act_window">
        <field name="name">เรื่องทั้งหมด (ภายใน)</field>
        <field name="res_model">helpdesk.ticket</field>
        <field name="view_mode">list,kanban,form,pivot</field>
        <field name="path">internal-issue-all</field>
    </record>

    <!-- Submenu ใต้ Helpdesk (ไม่สร้างเมนูหลักซ้ำ) -->
    <menuitem id="menu_internal_issue_my"
              name="เรื่องของฉัน"
              parent="helpdesk_mgmt.helpdesk_ticket_main_menu"
              action="action_internal_issue_my"
              sequence="10"/>
    <menuitem id="menu_internal_issue_all"
              name="เรื่องภายในทั้งหมด"
              parent="helpdesk_mgmt.helpdesk_ticket_main_menu"
              action="action_internal_issue_all"
              sequence="20"/>
    <menuitem id="menu_internal_issue_queue_request"
              name="คำขอแซงคิว"
              parent="helpdesk_mgmt.helpdesk_ticket_main_menu"
              action="action_helpdesk_queue_request"
              sequence="30"/>

    <!-- Settings -->
    <menuitem id="menu_internal_issue_routing_rule"
              name="กฎการส่งเรื่องอัตโนมัติ"
              parent="helpdesk_mgmt.helpdesk_ticket_config_main_menu"
              action="action_helpdesk_routing_rule"
              sequence="50"/>

</odoo>
```

- [ ] **Step 2: รันเทสต์ + ตรวจเมนูโหลดได้**

Run: `pwsh -File .\run-tests.ps1 -Module od19_internal_issue -Database odoo19_t_internal_issue -HttpPort 8085`
Expected: PASS — ไม่มี `External ID not found` (parent menu `helpdesk_ticket_config_main_menu` ต้องมีอยู่จริง)

- [ ] **Step 3: Commit**

```bash
git add custom_addons/od19_internal_issue/views/internal_issue_menus.xml
git commit -m "feat(od19_internal_issue): add submenus under helpdesk"
```

---

## Task T11: แจ้งเตือนหลายช่องทาง (events)

**Files:**
- Modify: `custom_addons/od19_internal_issue/models/helpdesk_ticket.py`
- Test: `tests/test_helpdesk_ticket.py` (เพิ่มเคส)

- [ ] **Step 1: เพิ่มเทสต์ (RED)**

เพิ่มเมธอดใน `TestInternalIssueTicket` (ไฟล์ `tests/test_helpdesk_ticket.py`)

```python
    def test_emergency_creates_notification(self):
        ticket = self._create_ticket(emergency=True, user_id=self.env.user.id)
        queue = self.env["od19.notification.queue"].search(
            [("event", "=", "issue_updated")]
        )
        self.assertTrue(queue)

    def test_assign_notifies_assignee(self):
        ticket = self._create_ticket()
        ticket.write({"user_id": self.env.user.id})
        queue = self.env["od19.notification.queue"].search(
            [("event", "=", "issue_assigned")]
        )
        self.assertTrue(queue)
```

> หมายเหตุ: `notify()` เขียนลง `od19.notification.queue` โดยไม่มี network call จริง — เทสต์จึงไม่ต้อง mock `requests.post`

- [ ] **Step 2: รันเทสต์ให้เห็น FAIL**

Run: `pwsh -File .\run-tests.ps1 -Module od19_internal_issue -Database odoo19_t_internal_issue -HttpPort 8085`
Expected: FAIL — event `issue_updated`/`issue_assigned` ยังไม่ถูกส่ง (RED)

- [ ] **Step 3: เขียน implement — เติม event ใน `_notify_created` / `_notify_assigned`**

ใน `models/helpdesk_ticket.py` แก้ `_notify_created` ให้เลือก event ตาม `emergency`:

```python
    def _notify_created(self):
        self.ensure_one()
        partners = self._get_notification_partners()
        if not partners:
            return
        subject = (
            _("เรื่องฉุกเฉิน: %s") % self.name
            if self.emergency
            else _("สร้างเรื่องใหม่: %s") % self.name
        )
        self.env["notification.service"].notify(
            partners,
            _("เรื่อง %(number)s ถูกสร้างแล้ว") % {"number": self.number},
            event="issue_updated",
            subject=subject,
        )
```

แก้ `write()` ให้แจ้งเมื่อ priority เปลี่ยน (audit):

```python
    def write(self, vals):
        res = super().write(vals)
        if "user_id" in vals and vals["user_id"]:
            for record in self:
                record._notify_assigned()
        if "priority" in vals:
            for record in self:
                record.message_post(
                    body=_("ปรับความสำคัญเป็น %s") % record._priority_label()
                )
        return res
```

- [ ] **Step 4: รันเทสต์ให้เห็น PASS (GREEN)**

Run: `pwsh -File .\run-tests.ps1 -Module od19_internal_issue -Database odoo19_t_internal_issue -HttpPort 8085`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add custom_addons/od19_internal_issue/models/helpdesk_ticket.py custom_addons/od19_internal_issue/tests/test_helpdesk_ticket.py
git commit -m "feat(od19_internal_issue): wire multi-channel notifications"
```

---

## Task T12: Portal + Email channel (สิทธิ์ผู้แจ้ง + alias)

**Files:**
- Modify: `custom_addons/od19_internal_issue/views/helpdesk_ticket_views.xml` (เพิ่ม portal-safe view)
- Modify: `custom_addons/od19_internal_issue/data/internal_issue_data.xml` (เพิ่ม alias)

> หมายเหตุ (แก้ไขระหว่าง execute): OCA `helpdesk_mgmt` 19.0.1.3.1 **ไม่มี** view id `helpdesk_ticket_view_portal`; เทมเพลต portal จริงคือ `portal_helpdesk_ticket_page` (qweb, inherit `portal.portal_sidebar`, primary=True) ใน `views/helpdesk_ticket_templates.xml` — จึงต้องอ้าง id นี้แทน
> โมดูลนี้ต้อง (ก) ให้ผู้ใช้ base.group_user ที่ไม่ใช่ agent เห็น "เรื่องของฉัน" ได้ (ครอบคลุมแล้วด้วย T07 + T10) (ข) ตั้ง alias email ของทีม Triage ให้รับเรื่องทางอีเมล
>
> หมายเหตุ (แก้ไขระหว่าง execute): เทสต์เดิมที่วางไว้ (`test_reporter_sees_own_issue_via_search`) ซ้ำเชิงตรรกะกับ `test_private_visible_to_reporter` ที่มีอยู่แล้ว (บรรทัด 55 ของไฟล์) จึงเปลี่ยนเป็นเทสต์ที่ครอบคลุมครึ่งหลังของ T12 (email alias) แทน

- [ ] **Step 1: เขียนเทสต์ (RED)**

เพิ่มใน `tests/test_helpdesk_privacy.py`

```python
    def test_triage_email_alias_configured(self):
        alias = self.env.ref(
            "od19_internal_issue.alias_issue_triage", raise_if_not_found=False
        )
        self.assertTrue(alias, "ต้องมีบันทึก alias email ของทีม Triage")
        self.assertEqual(alias.alias_name, "internal-issue")
        self.assertEqual(alias.alias_model_id.model, "helpdesk.ticket")
        self.assertIn("issue_stream", alias.alias_defaults or "")
```

- [ ] **Step 2: เพิ่ม portal access view + alias**

เติมใน `views/helpdesk_ticket_views.xml` (ก่อน `</odoo>`) — ขยายเทมเพลต portal ของ OCA เพื่อโชว์ตำแหน่งคิวให้ผู้แจ้ง (ใช้ `<template>` = qweb view; ไม่ต้องระบุ `model`):

```xml
    <!-- Portal: แสดงตำแหน่งคิวให้ผู้แจ้ง -->
    <template id="portal_helpdesk_ticket_queue"
              inherit_id="helpdesk_mgmt.portal_helpdesk_ticket_page"
              name="Ticket Portal: queue position">
        <xpath expr="//div[@id='card_body']" position="inside">
            <div class="mb-3">
                <p>
                    ตำแหน่งในคิว: <span t-field="ticket.queue_position"/>
                    (มีงานก่อนหน้า <span t-field="ticket.queue_ahead_count"/> งาน)
                </p>
            </div>
        </xpath>
    </template>
```

เติมใน `data/internal_issue_data.xml` (ก่อน `</odoo>`) — alias email ของทีม Triage:

```xml
    <!-- Email alias: รับเรื่องเข้าทีม Triage -->
    <record id="alias_issue_triage" model="mail.alias">
        <field name="alias_name">internal-issue</field>
        <field name="alias_model_id" ref="helpdesk_mgmt.model_helpdesk_ticket"/>
        <field name="alias_defaults">{'issue_stream': 'unsure'}</field>
    </record>
```

- [ ] **Step 3: รันเทสต์ให้เห็น PASS (GREEN)**

Run: `pwsh -File .\run-tests.ps1 -Module od19_internal_issue -Database odoo19_t_internal_issue -HttpPort 8085`
Expected: PASS — และไม่มี error `View helpdesk_ticket_view_portal not found`

- [ ] **Step 4: Commit**

```bash
git add custom_addons/od19_internal_issue/views/helpdesk_ticket_views.xml custom_addons/od19_internal_issue/data/internal_issue_data.xml custom_addons/od19_internal_issue/tests/test_helpdesk_privacy.py
git commit -m "feat(od19_internal_issue): expose queue position to portal and add email alias"
```

---

## Task T13: ติดตั้งตรวจรับรวม + อัปเดตเวอร์ชัน

**Files:**
- Modify: `custom_addons/od19_internal_issue/__manifest__.py` (version → `19.0.1.0.1`)

- [ ] **Step 1: รันเทสต์ทั้งโมดูล (ต้องผ่านครบ)**

Run: `pwsh -File .\run-tests.ps1 -Module od19_internal_issue -Database odoo19_t_internal_issue -HttpPort 8085`
Expected: PASS — 0 failed / 0 error ทุกไฟล์ใน `tests/`

- [ ] **Step 2: ตรวจ log ว่าไม่มี warning ค้าง**

เปิด `data_test_run.log` (หรือ log ล่าสุด) แล้วยืนยัน:
- ไม่มี `WARNING ... no access rules for model`
- ไม่มี `Field ... does not exist`
- ไม่มี `External ID not found`

- [ ] **Step 3: อัปเดตเวอร์ชัน**

ใน `__manifest__.py` เปลี่ยน `"version": "19.0.1.0.0"` → `"version": "19.0.1.0.1"`

- [ ] **Step 4: ติดตั้ง/อัปเดตโมดูลบน DB เป้าหมาย**

ตาม AGENTS.md §11 — หลังผ่าน Unit Test ให้ติดตั้ง/อัปเดตได้ (ถือ lease `db:<ชื่อ>` ก่อนเสมอ และ `--stop-after-init`)
ก่อนอัปเดตให้ตรวจ `.agent-locks/app-install-counter.json` — ถ้าถึง 10 ครั้ง/10 แอป ให้หยุดถามผู้ใช้ก่อนว่าจะลง db ใด

Run: `pwsh -File .\run-tests.ps1 -Module od19_internal_issue -Database odoo19_t_internal_issue -HttpPort 8085`
Expected: PASS (อัปเดตเวอร์ชันใหม่โดยไม่พัง)

- [ ] **Step 5: Commit**

```bash
git add custom_addons/od19_internal_issue/__manifest__.py
git commit -m "chore(od19_internal_issue): bump version to 19.0.1.0.1"
```

---

## Self-Review (ทำหลังเขียนครบทุก Task)

**1. Spec coverage — ทุกหัวข้อใน spec ถูกครอบคลุมหรือยัง?**

| spec | Task ที่รองรับ |
|---|---|
| §1 dependency (`od19_helpdesk_extension` เพิ่มเข้า manifest) | T01 Step 4 |
| §2 ฟิลด์ `helpdesk.ticket` (issue_stream/impact/urgency/priority/emergency/visibility/visibility_department_id/queue_*/insert_*/consent/jump_window/kb_*) | T02 |
| §2 ฟิลด์ `helpdesk.ticket.team` | T03 |
| §2 `helpdesk.routing.rule` | T04 |
| §2 `helpdesk.queue.request` | T06 |
| §3 route (stream/triage/keyword) | T04 |
| §4 stages ไทย 6 ขั้น | T08 |
| §5 privacy + record rules | T07 |
| §6 notify | T02, T11 |
| §7 RBAC + submenu (ไม่สร้างเมนูซ้ำ) | T10 |
| §8 คิวต่อทีม + 2 ชั้น + timeout | T05, T06 |
| §9 fair priority (matrix + quota + emergency + audit) | T02, T11 (note: `weekly_priority_quota` เก็บค่าใน T03; การบังคับใช้โควต้าแบบเข้มเป็น Phase 2 — ดูข้อ 3) |
| §10 KB handoff | ฟิลด์ `kb_converted`/`kb_article_ref` (T02) — logic จริงเป็น Phase 2 |
| §11? (Phase 2) | นอกขอบเขต Phase 1 |
| §2 ช่องทาง Backend/Portal/Email | T09 (backend), T12 (portal+email) |
| Unit tests ตาม §"การทดสอบ" | T02, T04, T05, T06, T07, T11, T12 |

**2. Placeholder scan — มีคำต้องห้ามตกค้างหรือไม่?**
- ต้องไม่มี "TBD"/"TODO"/"implement later" ในไฟล์ plan นี้
- เมธอด `_apply_fairness_log_context` ใน T02 เป็น hook ที่คืน `vals` เฉย ๆ โดยเจตนา (ไม่ใช่ placeholder ที่ต้องเติม) — หรือเลือก **ลบเมธอดนี้ออก** ในระหว่าง execute เพื่อไม่ให้มี dead code
- `_apply_routing` ถูกประกาศ stub ใน T02 แล้วเติมจริงใน T04 — ระบุชัดแล้วทั้งสองที่

**3. Type consistency — ชื่อฟิลด์/เมธอดตรงกันทุก Task?**

| ชื่อ | ใช้ที่ | ชนิด |
|---|---|---|
| `issue_stream` | T02/T03/T04/T08 | selection it_support/improvement/iso_capa/unsure |
| `impact`,`urgency` | T02 | selection I1-I3 / U1-U3 |
| `priority` | T02/T05/T11 | selection "0".."3" (OCA) |
| `emergency` | T02/T09/T11 | boolean |
| `visibility_department_id` | T02/T07/T09 | m2o hr.department (แทน `department_id`) |
| `queue_sequence`/`queue_position`/`queue_ahead_count` | T02/T05/T06 | integer |
| `consent_state` | T02/T06 | pending/accepted/jump_requested |
| `jump_window_deadline` | T02 | datetime |
| `is_priority_inserted`/`insert_before_id` | T02/T06 | boolean / m2o |
| `_apply_routing` | T02(stub)/T04 | method(vals)->vals |
| `_notify_created`/`_notify_assigned` | T02/T11 | method |
| `_cron_expire_stale_requests` | T06/T08 | api.model method |
| `action_approve_reporter_head`/`action_approve_team_head` | T06/T09 | method |

**ประเด็นที่ต้องแจ้งผู้ใช้ก่อนเริ่ม (decision points):**
1. **โควตางานด่วน (`weekly_priority_quota`)**: Phase 1 เก็บค่าไว้และแสดงในตั้งค่า แต่ "บังคับเข้ม" (บล็อกการตั้ง priority สูงเมื่อเกินโควต้า) พิจารณาเป็น Phase 1 ครึ่งหรือ Phase 2 — แนะนำ **Phase 2** เพื่อลดความซับซ้อนรอบแรก
2. **`_apply_fairness_log_context`**: แนะนำ **ลบออก** ระหว่าง execute (ไม่ใช้)
3. **AGENT_ID / DB ทดสอบ**: ยืนยัน `trae-od19_internal_issue` / `odoo19_t_internal_issue` / port `8085`

---

## Execution Handoff

**Plan complete. สองทางเลือกในการ execute:**

**1. Subagent-Driven (แนะนำ)** — dispatch agent ย่อยทีละ Task, รีวิวระหว่างทาง, iterate เร็ว
   - ต้องมี REQUIRED SUB-SKILL: `superpowers:subagent-driven-development`

**2. Inline Execution** — execute ในเซสชันนี้เป็นชุด มี checkpoint ให้รีวิว
   - ต้องมี REQUIRED SUB-SKILL: `superpowers:executing-plans`

**ก่อนเริ่ม:** ยืนยันข้อ 3 ประการใน Self-Review (โควต้า / ลบ hook / AGENT_ID-DB-port) แล้วเลือกโหมด execution

---

## Follow-ups (deferred — หลัง Final Review)

**ที่มา:** final code review พบ 1 Critical (C1) + 4 Major (M1–M4) + 9 minors
**สถานะ:** C1 แก้แล้ว (commit `91808877a9d`); รายการที่เหลือเลื่อนเป็น follow-up ตามมติผู้ใช้

### Critical — แก้แล้ว
- **C1 (แก้แล้ว):** `helpdesk.queue.request` — `base.group_user` มี write/create และไม่มี `ir.rule`/`groups=` บน method ทำให้ผู้ใช้ใดก็อนุมัติ/ปฏิเสธคำขอแซงคิวได้
  - เพิ่ม `_check_approval_right()` (ผู้อนุมัติที่กำหนด หรือ `helpdesk_mgmt.group_helpdesk_manager`; superuser ผ่าน)
  - เพิ่ม default ผู้อนุมัติ: `_compute_approvers()` — หัวหน้าแผนกผู้แจ้ง (`hr.department.manager_id.user_id`) และหัวหน้าทีมเจ้าของคิว (`helpdesk.ticket.team.user_id`); fallback หัวหน้าทีมเมื่อผู้แจ้งไม่มีแผนก
  - test 4 รายการ (defaults + guard); รวม 41 tests ผ่าน

### Major — ยังค้าง (Phase 2 / follow-up)
- **M2:** `emergency` ไม่ fan-out แจ้งเตือนไปหัวหน้าทีม/Triage (spec §9 บรรทัด 155)
- **M3:** `write()` ไม่แจ้งเตือนเมื่อเปลี่ยน `stage_id` (spec §6 บรรทัด 117)
- **M4:** `internal_issue_visibility_rule` OR กับ OCA `helpdesk_ticket_user_rule` (`[(1,'=',1)]` ของ `group_helpdesk_user`) → สมาชิกทีมเห็น ticket ทั้งหมดรวม private

### Minors — ยังค้าง
- m1 ฟิลด์ซ้ำในฟอร์ม · m2 dead fields ใน `helpdesk_ticket_category.py` · m3 `_compute_queue_position` N+1 + depends ขาด `stage_id.closed` · m4 `_notify_assigned` ซ้ำ · m5 priority readonly ขัด help text · m6 audit priority ไม่ครอบ recompute · m7 คุณภาพ test (emergency test ไม่พิสูจน์ emergency; `assertIn("issue_stream", …)` ไม่ assert ค่า `'unsure'`) · m8 event=`"issue_updated"` ตอน create · m9 เมนูต่างจาก spec
- T11 minors (จาก session ก่อน): double-notify ใน `write()` · ความแม่นของ test บนแถว `queue` · `_priority_label()` คืน `""` · `_notify_assigned` ไม่ผ่าน `_get_notification_partners`

### หมายเหตุ (ไม่ใช่ defect)
- **M1 (`weekly_priority_quota` ไม่บังคับใช้):** ตั้งใจ — มติผู้ใช้ให้ "บังคับโควต้า = Phase 2" (Self-Review ข้อ 3.1); Phase 1 เก็บค่าฟิลด์ถูกต้อง
