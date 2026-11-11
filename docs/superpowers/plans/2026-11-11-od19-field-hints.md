# OD19 Field Hints Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** แสดงข้อความตัวอย่าง/คำแนะนำ/คำเตือนสีเทาอ่อนในช่องกรอกว่างของทุกฟอร์มใน Odoo 19 โดยไม่บันทึกเป็นข้อมูลจริงและไม่แก้ Odoo Core

**Architecture:** โมดูลใหม่ `od19_field_hints` ฝั่ง Server สร้างชุด config (คำนำหน้า, ตารางข้อความอัตโนมัติตามชนิดฟิลด์, override รายฟิลด์, รายการฟิลด์สำคัญ, รายชื่อโมเดล `od19_*`) แล้วฉีดเข้า `session_info` ฝั่ง Client patch getter `fieldComponentProps` ของ `Field` component เพื่อเติมค่า `props.placeholder` เฉพาะ widget ที่รองรับและเฉพาะเมื่อช่องว่าง

**Tech Stack:** Odoo 19 CE, Python 3 (AbstractModel, res.config.settings, ir.http), OWL 2 / JavaScript, SCSS, PowerShell 7 (`run-tests.ps1`)

อ้างอิงดีไซน์: `docs/superpowers/specs/2026-11-11-od19-field-hints-design.md`

---

## ข้อเท็จจริงที่ยืนยันจากซอร์สจริง (ใช้ในแผนนี้)

- `Field` ถูก export จาก `@web/views/fields/field` และ getter `fieldComponentProps` อยู่ที่ [field.js](file:///c:/odoo-dev/odoo19/addons/web/static/src/views/fields/field.js#L410-L468)
- Odoo ส่งค่า placeholder ให้ widget ผ่าน `fieldInfo.attrs.placeholder` → `fieldInfo.placeholder` ([field.js](file:///c:/odoo-dev/odoo19/addons/web/static/src/views/fields/field.js#L428-L432))
- widget ที่รองรับ placeholder และส่งคีย์ `placeholder` ออกมาเสมอ (แม้ค่าเป็น `undefined`) เช่น char, selection, many2one → ใช้ `"placeholder" in props` ตรวจสอบได้อย่างปลอดภัย
- `patch()` รองรับการ patch getter และเรียกของเดิมผ่าน `super` ได้ ([patch.js](file:///c:/odoo-dev/odoo19/addons/web/static/src/core/utils/patch.js#L100-L116))
- session config ฝั่ง client อ่านได้แบบ synchronous: `import { session } from "@web/session"` → `session.od19_field_hints`
- `ir.http.session_info()` เป็น instance method ที่ override ได้ ([ir_http.py](file:///c:/odoo-dev/odoo19/addons/web/models/ir_http.py#L84-L176))
- `Field._modules` เก็บชื่อโมดูลที่นิยาม/สืบทอดฟิลด์นั้น ([fields.py](file:///c:/odoo-dev/odoo19/odoo/orm/fields.py#L263))
- `run-tests.ps1` บังคับ `-u <Module>` + `-d <Database>` + `--data-dir` + `--http-port` + `--test-enable` + `--test-tags` ([run-tests.ps1](file:///c:/odoo-dev/odoo19/run-tests.ps1#L101-L111))

## โครงสร้างไฟล์

| ไฟล์ | ความรับผิดชอบ |
|---|---|
| `custom_addons/od19_field_hints/__manifest__.py` | metadata + assets bundle |
| `custom_addons/od19_field_hints/__init__.py` | import models |
| `custom_addons/od19_field_hints/models/__init__.py` | import โมเดลย่อย |
| `custom_addons/od19_field_hints/models/od19_field_hints.py` | ค่าคงที่ + สร้าง client config + หาโมเดล `od19_*` |
| `custom_addons/od19_field_hints/models/res_config_settings.py` | สวิตช์ 2 ตัวใน Settings |
| `custom_addons/od19_field_hints/models/ir_http.py` | ฉีด config เข้า `session_info` |
| `custom_addons/od19_field_hints/views/res_config_settings_views.xml` | หน้าจอ Settings |
| `custom_addons/od19_field_hints/static/src/js/od19_field_hints.js` | patch `Field` เพื่อเติม placeholder |
| `custom_addons/od19_field_hints/static/src/scss/od19_field_hints.scss` | สีเทาอ่อนของ placeholder |
| `custom_addons/od19_field_hints/tests/test_field_hints.py` | unit test ทั้งหมด |

---

## Task 0: Pre-flight และสร้าง worktree (Tier 2 — ต้องถือ lease)

**Files:** ไม่มี (งานระดับ git/lock)

- [ ] **Step 1: ตรวจ HEAD และสถานะ**

Run:
```powershell
git log -1 --oneline
git status -sb
```
Expected: บันทึก HEAD ไว้ (ค่าเริ่มต้นของงานนี้คือ `ddba0e007ed` บน branch `19.0`)

- [ ] **Step 2: ตรวจ lease ที่ต้องใช้**

Run:
```powershell
pwsh -File .\agent-lock.ps1 -Action Status
```
Expected: ไม่มี lease ของ `git:worktree` ค้างอยู่ (ถ้ามีและยังไม่หมดอายุ → หยุด รายงานผู้ใช้)

- [ ] **Step 3: จับ lease `git:worktree`**

Run:
```powershell
pwsh -File .\agent-lock.ps1 -Action Acquire -Resource git:worktree -AgentId trae-od19_field_hints -Ttl 3600
```
Expected: สร้างไฟล์ `.agent-locks/git-worktree.lock` สำเร็จ

- [ ] **Step 4: สร้าง worktree + branch**

Run:
```powershell
git worktree add c:\odoo-dev\od19_field_hints -b feature/od19_field_hints 19.0
```
Expected: worktree ใหม่ที่ `c:\odoo-dev\od19_field_hints` บน branch `feature/od19_field_hints`

- [ ] **Step 5: เตรียม venv และ odoo.conf ใน worktree**

`venv19` และ `odoo.conf` ถูก `.gitignore` จึงไม่มีใน worktree ใหม่ ต้องเชื่อม/คัดลอก:

Run:
```powershell
if (-not (Test-Path 'c:\odoo-dev\od19_field_hints\venv19')) {
    New-Item -ItemType Junction -Path 'c:\odoo-dev\od19_field_hints\venv19' -Target 'c:\odoo-dev\odoo19\venv19'
}
$conf = Get-Content 'c:\odoo-dev\odoo19\odoo.conf' -Raw
$conf = $conf -replace 'C:\\odoo-dev\\odoo19\\addons',      'C:\odoo-dev\od19_field_hints\addons'
$conf = $conf -replace 'C:\\odoo-dev\\odoo19\\odoo\\addons', 'C:\odoo-dev\od19_field_hints\odoo\addons'
$conf = $conf -replace 'C:\\odoo-dev\\odoo19\\custom_addons','C:\odoo-dev\od19_field_hints\custom_addons'
$conf | Set-Content 'c:\odoo-dev\od19_field_hints\odoo.conf' -Encoding UTF8
```
Expected: มี `venv19` (junction) และ `odoo.conf` ใน worktree โดย `addons_path` ชี้ไปที่ worktree

- [ ] **Step 6: ตรวจว่า addons path ใช้งานได้**

Run:
```powershell
Select-String -Path 'c:\odoo-dev\od19_field_hints\odoo.conf' -Pattern 'od19_field_hints' | ForEach-Object { $_.Line }
Test-Path 'c:\odoo-dev\od19_field_hints\custom_addons'
```
Expected: เห็นพาธ `C:\odoo-dev\od19_field_hints\custom_addons` และไดเรกทอรีมีอยู่จริง

- [x] **Step 7: เตรียม DB ทดสอบส่วนตัว (bootstrap ครั้งเดียว)**

เทสต์ใน Task 3 ตรวจว่าโมเดลที่ถูกขยายโดยโมดูล `od19_*` (เช่น `res.partner`) ถูกตรวจพบ
จึงต้องมีโมดูล `od19_*` อย่างน้อยหนึ่งตัวที่เพิ่มฟิลด์ให้ `res.partner` อยู่ใน DB ทดสอบ
ใช้ `od19_partner_document_sequence` (depends แค่ `base`) เป็นโมดูลประกอบ

Run (ใน `c:\odoo-dev\od19_field_hints`):
```powershell
& .\venv19\Scripts\python.exe .\odoo-bin -c .\odoo.conf -d odoo19_t_od19_field_hints -i od19_partner_document_sequence --data-dir .\data --http-port 8090 --stop-after-init --logfile .\data_bootstrap.log
```
Expected: exit code 0 และ `od19_partner_document_sequence` = `installed` ใน DB ทดสอบ

> หมายเหตุ: ถ้ามี path ของ `third_party\oca\*` ที่ไม่มีอยู่ใน worktree Odoo จะเตือนแต่ยังรันต่อได้
> **งานทั้งหมดหลังจากนี้ให้ทำภายใน `c:\odoo-dev\od19_field_hints`**

---

## Task 1: โครงโมดูล + ทดสอบว่าโมดูลติดตั้งได้

**Files:**
- Create: `custom_addons/od19_field_hints/__manifest__.py`
- Create: `custom_addons/od19_field_hints/__init__.py`
- Create: `custom_addons/od19_field_hints/models/__init__.py`
- Create: `custom_addons/od19_field_hints/tests/__init__.py`
- Test: `custom_addons/od19_field_hints/tests/test_field_hints.py`

- [ ] **Step 1: เขียนเทสต์ที่จะล้มเหลวก่อน**

`custom_addons/od19_field_hints/tests/test_field_hints.py`:
```python
# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestFieldHints(TransactionCase):
    def test_model_is_available(self):
        """โมดูลต้องลงทะเบียน AbstractModel od19.field.hints ให้เรียกใช้ได้"""
        config = self.env["od19.field.hints"]._get_client_config()
        self.assertTrue(config["enabled"])
```

`custom_addons/od19_field_hints/tests/__init__.py`:
```python
from . import test_field_hints
```

- [ ] **Step 2: รันเทสต์เพื่อยืนยันว่าล้มเหลว**

Run (ใน `c:\odoo-dev\od19_field_hints`):
```powershell
pwsh -File .\run-tests.ps1 -Module od19_field_hints -Database odoo19_t_od19_field_hints -HttpPort 8090 -Clean
```
Expected: FAIL — โมดูล `od19_field_hints` ยังไม่มี (Odoo รายงานว่าไม่พบโมดูล หรือ test หา `_get_client_config` ไม่เจอ)

- [ ] **Step 3: สร้าง manifest และโครงโมดูล**

`custom_addons/od19_field_hints/__manifest__.py`:
```python
# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

{
    "name": "OD19 Field Hints",
    "version": "19.0.1.0.0",
    "author": "OD19",
    "category": "Productivity",
    "summary": "ข้อความตัวอย่าง/คำแนะนำ/คำเตือนสีเทาในช่องกรอกของ Odoo 19",
    "license": "LGPL-3",
    "depends": ["base_setup", "web"],
    "data": [
        "views/res_config_settings_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "od19_field_hints/static/src/scss/od19_field_hints.scss",
            "od19_field_hints/static/src/js/od19_field_hints.js",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
```

`custom_addons/od19_field_hints/__init__.py`:
```python
from . import models
```

`custom_addons/od19_field_hints/models/__init__.py`:
```python
from . import od19_field_hints
from . import res_config_settings
from . import ir_http
```

`custom_addons/od19_field_hints/models/od19_field_hints.py`:
```python
# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import models

from odoo.tools import str2bool


class Od19FieldHints(models.AbstractModel):
    _name = "od19.field.hints"
    _description = "OD19 Field Hints Config"

    def _get_client_config(self):
        params = self.env["ir.config_parameter"].sudo()
        return {
            "enabled": str2bool(params.get_param("od19_field_hints.enabled", "True")),
        }
```

`custom_addons/od19_field_hints/models/res_config_settings.py` (ไฟล์ว่างเปล่าชั่วคราวเพื่อให้ import ผ่าน):
```python
# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"
```

`custom_addons/od19_field_hints/models/ir_http.py` (ไฟล์ว่างเปล่าชั่วคราวเพื่อให้ import ผ่าน):
```python
# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"
```

`custom_addons/od19_field_hints/views/res_config_settings_views.xml`:
```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo/>
```

> manifest อ้าง `static/src/js` และ `static/src/scss` ที่จะสร้างจริงใน Task 6
> ถ้าการติดตั้งโมดูลล้มเหลวเพราะไม่พบไฟล์ asset ให้สร้างไฟล์ว่าง 2 ไฟล์นี้ก่อน:
> `static/src/js/od19_field_hints.js` และ `static/src/scss/od19_field_hints.scss`

- [ ] **Step 4: รันเทสต์เพื่อยืนยันว่าผ่าน**

Run:
```powershell
pwsh -File .\run-tests.ps1 -Module od19_field_hints -Database odoo19_t_od19_field_hints -HttpPort 8090 -Clean
```
Expected: PASS — `0 failed, 0 error(s)` (ใน `data_test_run.log`)

> สำหรับโมดูลที่ **ยังไม่เคยติดตั้ง** ใน DB ทดสอบ `run-tests.ps1` (ส่ง `-u` = upgrade เท่านั้น)
> จะไม่ติดตั้งโมดูลใหม่ให้ (Odoo จะเตือน `invalid module names, ignored`) ต้องติดตั้งครั้งแรกก่อน:
> ```powershell
> & .\venv19\Scripts\python.exe .\odoo-bin -c .\odoo.conf -d odoo19_t_od19_field_hints -i od19_field_hints --data-dir .\data --http-port 8090 --stop-after-init --logfile .\install_od19_field_hints.log
> ```
> ทำแล้วใน Task 1 — โมดูลถูกติดตั้งใน DB ทดสอบแล้ว จึงใช้ `-u` ได้ตามปกติใน Task ถัดไป

- [ ] **Step 5: Commit**

```powershell
git add -- custom_addons/od19_field_hints/__manifest__.py custom_addons/od19_field_hints/__init__.py custom_addons/od19_field_hints/models/__init__.py custom_addons/od19_field_hints/models/od19_field_hints.py custom_addons/od19_field_hints/models/res_config_settings.py custom_addons/od19_field_hints/models/ir_http.py custom_addons/od19_field_hints/views/res_config_settings_views.xml custom_addons/od19_field_hints/tests/__init__.py custom_addons/od19_field_hints/tests/test_field_hints.py
git commit -m "feat(od19_field_hints): scaffold module with config model"
```

---

## Task 2: ตารางข้อความอัตโนมัติ + คำนำหน้า + override

**Files:**
- Modify: `custom_addons/od19_field_hints/models/od19_field_hints.py`
- Test: `custom_addons/od19_field_hints/tests/test_field_hints.py`

- [ ] **Step 1: เขียนเทสต์ที่จะล้มเหลวก่อน**

เพิ่มใน `tests/test_field_hints.py` (ภายในคลาสเดิม):
```python
    def test_auto_hints_cover_common_types(self):
        config = self.env["od19.field.hints"]._get_client_config()
        auto = config["auto"]
        self.assertEqual(auto["date"], ["example", "วว/ดด/ปปปป"])
        self.assertEqual(auto["monetary"], ["example", "0.00"])
        self.assertEqual(auto["many2one"], ["hint", "เลือกจากรายการ"])
        self.assertEqual(config["default"], ["hint", "ระบุข้อมูล"])

    def test_prefixes(self):
        config = self.env["od19.field.hints"]._get_client_config()
        self.assertEqual(config["prefixes"]["example"], "ตัวอย่าง:")
        self.assertEqual(config["prefixes"]["hint"], "แนะนำ:")
        self.assertEqual(config["prefixes"]["warning"], "สำคัญ:")

    def test_overrides_shape(self):
        config = self.env["od19.field.hints"]._get_client_config()
        entry = config["overrides"]["res.partner"]["name"]
        self.assertEqual(entry["kind"], "example")
        self.assertTrue(entry["text"].startswith("เช่น:"))
```

- [ ] **Step 2: รันเทสต์เพื่อยืนยันว่าล้มเหลว**

Run:
```powershell
pwsh -File .\run-tests.ps1 -Module od19_field_hints -Database odoo19_t_od19_field_hints -HttpPort 8090
```
Expected: FAIL — `KeyError: 'auto'`

- [ ] **Step 3: เพิ่มค่าคงที่และขยาย `_get_client_config`**

แทนที่เนื้อหา `models/od19_field_hints.py` ด้วย:
```python
# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import models
from odoo.tools import str2bool

# คำนำหน้าตามชนิดข้อความ (kind -> prefix)
PREFIXES = {
    "example": "ตัวอย่าง:",
    "hint": "แนะนำ:",
    "warning": "สำคัญ:",
}

# ข้อความอัตโนมัติตามชนิดฟิลด์: type -> (kind, เนื้อความ)
AUTO_HINTS = {
    "char": ("example", "ระบุข้อความ"),
    "text": ("hint", "พิมพ์รายละเอียด"),
    "html": ("hint", "พิมพ์รายละเอียด"),
    "date": ("example", "วว/ดด/ปปปป"),
    "datetime": ("example", "วว/ดด/ปปปป ชช:นน"),
    "monetary": ("example", "0.00"),
    "float": ("example", "0.00"),
    "integer": ("example", "0"),
    "many2one": ("hint", "เลือกจากรายการ"),
    "many2many": ("hint", "เลือกจากรายการ"),
    "one2many": ("hint", "เลือกจากรายการ"),
    "selection": ("hint", "เลือกจากรายการ"),
    "email": ("example", "name@example.com"),
    "phone": ("example", "0X-XXX-XXXX"),
    "url": ("example", "https://example.com"),
}
DEFAULT_HINT = ("hint", "ระบุข้อมูล")

# ข้อความเจาะจงรายฟิลด์: model -> {field: (kind, เนื้อความ)}
OVERRIDES = {
    "res.partner": {
        "name": ("example", "เช่น: บริษัท Auto Info จำกัด"),
        "vat": ("example", "เช่น: 0105551234567"),
        "email": ("example", "เช่น: contact@auto-info.co.th"),
        "phone": ("example", "เช่น: 02-123-4567"),
    },
}

# ฟิลด์สำคัญที่อยากมีข้อความแม้ไม่ required: model -> [field]
IMPORTANT_FIELDS = {
    "res.partner": ["ref", "website"],
}


class Od19FieldHints(models.AbstractModel):
    _name = "od19.field.hints"
    _description = "OD19 Field Hints Config"

    def _get_client_config(self):
        params = self.env["ir.config_parameter"].sudo()
        return {
            "enabled": str2bool(params.get_param("od19_field_hints.enabled", "True")),
            "apply_core": str2bool(params.get_param("od19_field_hints.apply_core", "False")),
            "prefixes": PREFIXES,
            "auto": {key: list(value) for key, value in AUTO_HINTS.items()},
            "default": list(DEFAULT_HINT),
            "overrides": {
                model: {
                    field: {"kind": kind, "text": text}
                    for field, (kind, text) in fields.items()
                }
                for model, fields in OVERRIDES.items()
            },
            "important": IMPORTANT_FIELDS,
            "custom_models": [],
        }
```

- [ ] **Step 4: รันเทสต์เพื่อยืนยันว่าผ่าน**

Run:
```powershell
pwsh -File .\run-tests.ps1 -Module od19_field_hints -Database odoo19_t_od19_field_hints -HttpPort 8090
```
Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add -- custom_addons/od19_field_hints/models/od19_field_hints.py custom_addons/od19_field_hints/tests/test_field_hints.py
git commit -m "feat(od19_field_hints): add auto hint table and per-field overrides"
```

---

## Task 3: หาโมเดลของโมดูล `od19_*` (scope)

**Files:**
- Modify: `custom_addons/od19_field_hints/models/od19_field_hints.py`
- Test: `custom_addons/od19_field_hints/tests/test_field_hints.py`

- [ ] **Step 1: เขียนเทสต์ที่จะล้มเหลวก่อน**

เพิ่มใน `tests/test_field_hints.py`:
```python
    def test_custom_models_detects_od19_fields(self):
        """โมเดลที่มีฟิลด์จากโมดูล od19_* ต้องถูกตรวจพบ"""
        config = self.env["od19.field.hints"]._get_client_config()
        self.assertIn("res.partner", config["custom_models"])

    def test_custom_models_excludes_pure_core_models(self):
        """โมเดล Core ล้วน ๆ ต้องไม่อยู่ในรายการ"""
        config = self.env["od19.field.hints"]._get_client_config()
        self.assertNotIn("ir.ui.view", config["custom_models"])
```

- [ ] **Step 2: รันเทสต์เพื่อยืนยันว่าล้มเหลว**

Run:
```powershell
pwsh -File .\run-tests.ps1 -Module od19_field_hints -Database odoo19_t_od19_field_hints -HttpPort 8090
```
Expected: FAIL — `custom_models` ยังเป็น `[]`

> หมายเหตุ: เทสต์นี้ต้องมีโมดูล `od19_*` ที่เพิ่มฟิลด์ให้ `res.partner` อยู่ใน DB ทดสอบด้วย
> DB ทดสอบถูก bootstrap ไว้แล้วด้วย `od19_partner_document_sequence` (ดู Task 0 Step 7)
> ถ้า DB ถูกล้างใหม่ ให้รัน bootstrap ซ้ำก่อน

- [ ] **Step 3: เพิ่มเมธอด `_get_custom_models`**

ใน `models/od19_field_hints.py` เพิ่ม `import` และเมธอด:
```python
from odoo import models, tools
from odoo.tools import str2bool
```

เพิ่มเมธอดในคลาส `Od19FieldHints` (ก่อน `_get_client_config`):
```python
    @tools.ormcache()
    def _get_custom_models(self):
        """ชื่อโมเดลทั้งหมดที่มีฟิลด์ซึ่งนิยาม/สืบทอดโดยโมดูล od19_*"""
        result = set()
        for model_name, model in self.env.registry.items():
            for field in model._fields.values():
                if any(module.startswith("od19_") for module in (field._modules or ())):
                    result.add(model_name)
                    break
        return tuple(sorted(result))
```

แก้ `"custom_models": []` ใน `_get_client_config` เป็น:
```python
            "custom_models": list(self._get_custom_models()),
```

- [ ] **Step 4: รันเทสต์เพื่อยืนยันว่าผ่าน**

Run:
```powershell
pwsh -File .\run-tests.ps1 -Module od19_field_hints -Database odoo19_t_od19_field_hints -HttpPort 8090
```
Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add -- custom_addons/od19_field_hints/models/od19_field_hints.py custom_addons/od19_field_hints/tests/test_field_hints.py
git commit -m "feat(od19_field_hints): detect models extended by od19 modules"
```

---

## Task 4: สวิตช์ใน Settings

**Files:**
- Modify: `custom_addons/od19_field_hints/models/res_config_settings.py`
- Modify: `custom_addons/od19_field_hints/views/res_config_settings_views.xml`
- Test: `custom_addons/od19_field_hints/tests/test_field_hints.py`

- [ ] **Step 1: เขียนเทสต์ที่จะล้มเหลวก่อน**

เพิ่มใน `tests/test_field_hints.py`:
```python
    def test_settings_toggle_enabled(self):
        settings = self.env["res.config.settings"].create({"od19_field_hints_enabled": False})
        settings.execute()
        config = self.env["od19.field.hints"]._get_client_config()
        self.assertFalse(config["enabled"])
        self.env["ir.config_parameter"].sudo().set_param("od19_field_hints.enabled", "True")

    def test_settings_toggle_apply_core(self):
        settings = self.env["res.config.settings"].create({"od19_field_hints_apply_core": True})
        settings.execute()
        config = self.env["od19.field.hints"]._get_client_config()
        self.assertTrue(config["apply_core"])
        self.env["ir.config_parameter"].sudo().set_param("od19_field_hints.apply_core", "False")
```

- [ ] **Step 2: รันเทสต์เพื่อยืนยันว่าล้มเหลว**

Run:
```powershell
pwsh -File .\run-tests.ps1 -Module od19_field_hints -Database odoo19_t_od19_field_hints -HttpPort 8090
```
Expected: FAIL — ไม่รู้จักฟิลด์ `od19_field_hints_enabled`

- [ ] **Step 3: เพิ่มฟิลด์และหน้าจอ Settings**

`models/res_config_settings.py`:
```python
# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    od19_field_hints_enabled = fields.Boolean(
        string="ข้อความแนะนำในช่องกรอก",
        config_parameter="od19_field_hints.enabled",
        default=True,
        help="แสดงข้อความตัวอย่าง/คำแนะนำ/คำเตือนสีเทาในช่องที่ยังว่างอยู่ "
        "เป็นเพียงข้อความแสดงผล ไม่ถูกบันทึกเป็นข้อมูลจริง "
        "(ต้องรีเฟรชหน้าเว็บหลังเปลี่ยนค่า)",
    )
    od19_field_hints_apply_core = fields.Boolean(
        string="ใช้กับโมดูลมาตรฐาน (Core/OCA) ด้วย",
        config_parameter="od19_field_hints.apply_core",
        default=False,
        help="ถ้าปิด จะแสดงเฉพาะโมดูล od19_* ของเรา",
    )
```

`views/res_config_settings_views.xml`:
```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>

    <record id="res_config_settings_view_form_field_hints" model="ir.ui.view">
        <field name="name">res.config.settings.view.form.field.hints</field>
        <field name="model">res.config.settings</field>
        <field name="inherit_id" ref="base_setup.res_config_settings_view_form"/>
        <field name="arch" type="xml">
            <xpath expr="//app[@name='general_settings']" position="inside">
                <block title="ข้อความแนะนำในช่องกรอก" id="od19_field_hints_settings">
                    <setting
                        id="od19_field_hints_enabled_setting"
                        string="ข้อความแนะนำในช่องกรอก"
                        help="แสดงข้อความตัวอย่าง/คำแนะนำ/คำเตือนเป็นสีเทาในช่องที่ยังว่างอยู่ ไม่บันทึกเป็นข้อมูลจริง"
                        groups="base.group_system">
                        <field name="od19_field_hints_enabled"/>
                        <div class="text-muted mt8">
                            <field name="od19_field_hints_apply_core"/>
                        </div>
                    </setting>
                </block>
            </xpath>
        </field>
    </record>

</odoo>
```

- [ ] **Step 4: รันเทสต์เพื่อยืนยันว่าผ่าน**

Run:
```powershell
pwsh -File .\run-tests.ps1 -Module od19_field_hints -Database odoo19_t_od19_field_hints -HttpPort 8090
```
Expected: PASS (XML ผ่านการตรวจ well-formed และ view ถูก inherit สำเร็จ)

- [ ] **Step 5: Commit**

```powershell
git add -- custom_addons/od19_field_hints/models/res_config_settings.py custom_addons/od19_field_hints/views/res_config_settings_views.xml custom_addons/od19_field_hints/tests/test_field_hints.py
git commit -m "feat(od19_field_hints): add settings toggles for enabling hints and core scope"
```

---

## Task 5: ฉีด config เข้า `session_info`

**Files:**
- Modify: `custom_addons/od19_field_hints/models/ir_http.py`
- Test: `custom_addons/od19_field_hints/tests/test_field_hints.py`

- [ ] **Step 1: เขียนเทสต์ที่จะล้มเหลวก่อน**

เพิ่มใน `tests/test_field_hints.py`:
```python
    def test_session_info_contains_field_hints(self):
        """config ต้องถูกส่งไปกับ session_info เพื่อให้ฝั่ง client อ่านได้แบบ synchronous"""
        from odoo.http import Request

        info = self.env["ir.http"].session_info()
        self.assertIn("od19_field_hints", info)
        self.assertIn("custom_models", info["od19_field_hints"])
```

- [ ] **Step 2: รันเทสต์เพื่อยืนยันว่าล้มเหลว**

Run:
```powershell
pwsh -File .\run-tests.ps1 -Module od19_field_hints -Database odoo19_t_od19_field_hints -HttpPort 8090
```
Expected: FAIL — `KeyError: 'od19_field_hints'`

- [ ] **Step 3: override `session_info`**

`models/ir_http.py`:
```python
# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    def session_info(self):
        result = super().session_info()
        result["od19_field_hints"] = self.env["od19.field.hints"]._get_client_config()
        return result
```

> ถ้าเทสต์ล้มเหลวเพราะ `session_info()` ต้องมี `request` ให้ตัด `from odoo.http import Request` ที่ไม่ได้ใช้ออก
> และเรียกผ่าน `self.env["ir.http"].session_info()` เท่านั้น

- [ ] **Step 4: รันเทสต์เพื่อยืนยันว่าผ่าน**

Run:
```powershell
pwsh -File .\run-tests.ps1 -Module od19_field_hints -Database odoo19_t_od19_field_hints -HttpPort 8090
```
Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add -- custom_addons/od19_field_hints/models/ir_http.py custom_addons/od19_field_hints/tests/test_field_hints.py
git commit -m "feat(od19_field_hints): expose config through session_info"
```

---

## Task 6: patch ฝั่ง Client + SCSS

**Files:**
- Create: `custom_addons/od19_field_hints/static/src/js/od19_field_hints.js`
- Create: `custom_addons/od19_field_hints/static/src/scss/od19_field_hints.scss`
- Test: `custom_addons/od19_field_hints/tests/test_field_hints.py`

- [ ] **Step 1: เขียนเทสต์ที่จะล้มเหลวก่อน**

เพิ่มใน `tests/test_field_hints.py`:
```python
    def test_assets_are_wired_into_backend_bundle(self):
        assets = self.env["ir.qweb"]._get_asset_content("web.assets_backend")[0]
        urls = [asset["url"] for asset in assets]
        self.assertIn("/od19_field_hints/static/src/js/od19_field_hints.js", urls)
        self.assertIn("/od19_field_hints/static/src/scss/od19_field_hints.scss", urls)

    def test_patch_guards_placeholder_injection(self):
        """patch ต้องตรวจว่ามีคีย์ placeholder และยังว่าง ก่อนเติมค่า"""
        from pathlib import Path

        from odoo.modules.module import get_module_path

        source = (
            Path(get_module_path("od19_field_hints"))
            / "static/src/js/od19_field_hints.js"
        ).read_text(encoding="utf-8")
        self.assertIn("fieldComponentProps", source)
        self.assertIn('"placeholder" in props', source)
        self.assertIn("session.od19_field_hints", source)
```

- [ ] **Step 2: รันเทสต์เพื่อยืนยันว่าล้มเหลว**

Run:
```powershell
pwsh -File .\run-tests.ps1 -Module od19_field_hints -Database odoo19_t_od19_field_hints -HttpPort 8090
```
Expected: FAIL — ไม่พบไฟล์ asset

- [ ] **Step 3: สร้างไฟล์ JS และ SCSS**

`static/src/js/od19_field_hints.js`:
```js
import { session } from "@web/session";
import { patch } from "@web/core/utils/patch";
import { Field } from "@web/views/fields/field";

/**
 * คำนวณข้อความ hint ของฟิลด์หนึ่ง ๆ
 * กติกา: ใช้ override ก่อน ถ้าไม่มีให้ใช้ required (สำคัญ:) หรือฟิลด์สำคัญ (auto)
 * คืนค่า null เมื่อฟิลด์ไม่เข้าเงื่อนไข
 */
export function buildHint(config, model, name, fieldType, required) {
    if (!config || !config.enabled) {
        return null;
    }
    const isCustom = (config.custom_models || []).includes(model);
    if (!isCustom && !config.apply_core) {
        return null;
    }
    const override = config.overrides && config.overrides[model] && config.overrides[model][name];
    const important = ((config.important && config.important[model]) || []).includes(name);
    if (!override && !required && !important) {
        return null;
    }
    const auto = (config.auto && config.auto[fieldType]) || config.default;
    const kind = override ? override.kind : required ? "warning" : auto[0];
    const body = override ? override.text : auto[1];
    const prefix = (config.prefixes && config.prefixes[kind]) || "";
    return `${prefix} ${body}`.trim();
}

patch(Field.prototype, {
    get fieldComponentProps() {
        const props = super.fieldComponentProps;
        // เฉพาะช่องที่แก้ไขได้ และ widget รองรับ placeholder และยังว่างอยู่
        if (!props.readonly && "placeholder" in props && !props.placeholder) {
            const record = this.props.record;
            const meta = record.fields[this.props.name];
            const hint = buildHint(
                session.od19_field_hints,
                record.resModel,
                this.props.name,
                this.type,
                Boolean(meta && meta.required)
            );
            if (hint) {
                props.placeholder = hint;
            }
        }
        return props;
    },
});
```

`static/src/scss/od19_field_hints.scss`:
```scss
.o_field_widget input::placeholder,
.o_field_widget textarea::placeholder {
    color: #9ca3af;
    opacity: 1;
}
```

- [ ] **Step 4: รันเทสต์เพื่อยืนยันว่าผ่าน**

Run:
```powershell
pwsh -File .\run-tests.ps1 -Module od19_field_hints -Database odoo19_t_od19_field_hints -HttpPort 8090
```
Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add -- custom_addons/od19_field_hints/static/src/js/od19_field_hints.js custom_addons/od19_field_hints/static/src/scss/od19_field_hints.scss custom_addons/od19_field_hints/tests/test_field_hints.py
git commit -m "feat(od19_field_hints): patch Field component to inject gray placeholders"
```

---

## Task 7: ตรวจสอบด้วยตาและรันเทสต์เต็มรอบ

**Files:** ไม่มี (verification)

- [ ] **Step 1: รันเทสต์เต็มรอบแบบสะอาด**

Run:
```powershell
pwsh -File .\run-tests.ps1 -Module od19_field_hints -Database odoo19_t_od19_field_hints -HttpPort 8090 -Clean
```
Expected: `0 failed, 0 error(s)` และไม่มี traceback ใน `data_test_run.log`

- [ ] **Step 2: ตรวจสอบด้วยตา (manual)**

1. เปิด Odoo (dev/prod 8070) ด้วยโมดูล `od19_field_hints` ที่ติดตั้งแล้ว
2. เปิดฟอร์มที่มีฟิลด์ required เช่น Contacts → สร้างใหม่ → ช่อง `ชื่อ` ต้องมีข้อความเทา `ตัวอย่าง: เช่น: บริษัท Auto Info จำกัด`
3. เปิด Settings → เปิด `ใช้กับโมดูลมาตรฐาน (Core/OCA) ด้วย` → รีเฟรช → เปิดฟอร์ม Core (เช่น Sale Order ใหม่) → ต้องเห็นข้อความเทาในช่อง required
4. ปิด `ข้อความแนะนำในช่องกรอก` → รีเฟรช → ข้อความเทาต้องหายทั้งหมด
5. กรอกค่าจริงในช่อง → ข้อความเทาต้องหายไป และค่าไม่ถูกบันทึกเป็นข้อความ hint

Expected: ทั้ง 5 ข้อเป็นไปตามที่ระบุ

- [ ] **Step 3: ตรวจว่าไม่มีค่าจริงถูกเขียน**

Run:
```powershell
git status -sb
git diff --stat
```
Expected: ไม่มีไฟล์ข้อมูล/DB ถูกแก้ และไม่มีไฟล์ `.agent-locks/` ถูก track

- [ ] **Step 4: ปล่อย lease และสรุปผล**

Run:
```powershell
pwsh -File .\agent-lock.ps1 -Action Release -Resource git:worktree -AgentId trae-od19_field_hints
```
Expected: ไฟล์ `.agent-locks/git-worktree.lock` ถูกลบ

- [ ] **Step 5: รายงานผล**

รายงาน: AGENT_ID (`trae-od19_field_hints`), branch `feature/od19_field_hints`, commit SHA ทุกตัว, ไฟล์ที่แตะ, lease ที่จับ/ปล่อย, คำสั่งที่รันจริง, ผลลัพธ์จริง — ห้ามอ้างผลที่ยังไม่ได้รัน

---

## Self-Review

**1. Spec coverage**

| ข้อกำหนดในสเปก | งานที่รองรับ |
|---|---|
| ข้อความผสม (auto + override) | Task 2 |
| ครอบคลุมทุกโมดูล + สวิตช์ + ค่าเริ่มต้นเฉพาะ `od19_*` | Task 3, Task 4 |
| required + ฟิลด์สำคัญ | Task 6 (`buildHint`) |
| 3 ความหมาย + สีเทาเหมือนกัน | Task 2 (`PREFIXES`), Task 6 (SCSS) |
| ตารางข้อความอัตโนมัติตามชนิด | Task 2 |
| ลำดับความสำคัญ override > required > auto | Task 6 (`buildHint`) |
| แสดงเฉพาะช่องว่าง, ไม่แสดง readonly, ไม่ทับ placeholder เดิม | Task 6 (เงื่อนไข guard) |
| Settings 2 สวิตช์ | Task 4 |
| ไม่แก้ Core, ไม่เขียนค่าจริง | โครงสร้างทั้งหมด (patch + placeholder เท่านั้น) |
| การทดสอบ | Task 1–6 |

ไม่มีช่องว่างของข้อกำหนด

**2. Placeholder scan:** ไม่มี TBD/TODO — ทุก step มีโค้ดหรือคำสั่งจริง

**3. Type consistency:** ชื่อคีย์ config ตรงกันทั้ง Python และ JS: `enabled`, `apply_core`, `prefixes`, `auto`, `default`, `overrides`, `important`, `custom_models` · ชื่อเมธอด `_get_client_config`, `_get_custom_models` ใช้ตรงกันทุก task · ฟิลด์ settings `od19_field_hints_enabled`, `od19_field_hints_apply_core` ตรงกับ `config_parameter` ที่ใช้ใน Task 4
