# Odoo 19 Dashboard — เฟส 2 (Presentation & Reuse) Design

ต่อเนื่องจากสเปกเฟส 1: `2026-10-16-odoo19-dashboard-formula-and-status-rules-design.md`

สเปกเฟส 1 ส่งมอบ formula engine และ status rule engine สำหรับ widget ประเภท KPI
สเปกนี้ทำ 6 ข้อที่เฟส 1 ระบุว่า "นอกขอบเขต" (§2 L92–98) ให้ครบ

| # | หัวข้อ | สรุปแนวทาง |
|---|---|---|
| 1 | เงื่อนไขซ่อน/แสดง widget | ฟิลด์ `visible_expression` บน widget ประเมินด้วย safe_eval |
| 2 | ข้อความเตือน (alert message) | ฟิลด์ `alert_message` บน rule แสดงเมื่อกฎนั้นเข้าเงื่อนไข |
| 3 | Conditional formatting ของกราฟและ list | กฎสถานะประเมินต่อ bucket / ต่อแถว ให้สีตามสถานะ |
| 4 | กฎประเมิน "ต่อ bucket" ของกราฟ | ใช้ rule table เดิม ประเมินซ้ำต่อ bucket |
| 5 | คลังสูตรใช้ซ้ำข้าม widget | model ใหม่ `od19.dashboard.formula` + โหมด `library` |
| 6 | widget ข้าม dashboard + cross-source | ผ่อน constraint + slot อ้าง measure ข้าม source |

---

## 1. โมเดลข้อมูล

### 1.1 Model ใหม่ `od19.dashboard.formula`

| Field | Type | หน้าที่ |
|---|---|---|
| `name` | Char, required | ชื่อสูตรที่ผู้ใช้เห็นใน dropdown |
| `expression` | Char, required | expression ที่ประเมินด้วย safe_eval |
| `description` | Text | คำอธิบายว่าสูตรนี้ใช้ทำอะไร |
| `company_id` | Many2one `res.company`, required | ขอบเขตบริษัท |
| `active` | Boolean | เปิด/ปิดการใช้งาน |

- `_order = "name, id"`, `_description = "Dashboard Named Formula"`
- `_name_company_default` — `unique(name, company_id)`
- `_to_meta()` → `{"id", "name", "expression", "description", "names": [ชื่อที่ต้องผูก]}`
  โดย `names` = `expression_names(expression) - IMPLICIT_NAMES - ALLOWED_CALLS`

### 1.2 เพิ่มบน `od19.dashboard.widget`

| Field | Type | Default | หน้าที่ |
|---|---|---|---|
| `formula_id` | Many2one `od19.dashboard.formula`, `ondelete="restrict"` | — | สูตรจากคลัง ใช้เมื่อ `formula_mode = library` |
| `visible_expression` | Char | — | เงื่อนไขซ่อน/แสดง; ว่าง = แสดงเสมอ |

- `FORMULA_MODES` เพิ่ม `("library", "Library formula")`
- `_allowed_names()` เพิ่ม `set(self._formula_slot_map())` เพื่อให้ชื่อ slot ของสูตรคลังผ่าน whitelist

### 1.3 เพิ่มบน `od19.dashboard.widget.rule`

| Field | Type | หน้าที่ |
|---|---|---|
| `alert_message` | Char | ข้อความที่แสดงบน widget เมื่อกฎนี้เข้าเงื่อนไข |

- `_to_values()` เพิ่ม `alert_message`
- `_check_compare_widget` ผ่อน: ยังห้ามอ้างตัวเอง แต่ **อนุญาตให้อ้าง widget ข้าม dashboard** (ต้องบริษัทเดียวกันและผู้ใช้อ่านได้)

---

## 2. Formula engine — ส่วนขยาย

### 2.1 โหมด `library`

- `_effective_expression()` → `self.formula_id.expression` (หรือ `"0"` เมื่อไม่ผูกสูตร)
- `_formula_slot_map()` ผ่อนการกรอง key: ในโหมด `library` รับชื่อใด ๆ ที่เป็น identifier
  (โหมด `preset` / `custom` ยังคงรับเฉพาะ `a`–`e`, `w1`, `w2`)
- value ของ slot มี 3 รูปแบบ:
  - `"amount_total"` — measure บน source ของ widget เอง
  - `2` (number) — ค่าน้ำหนัก literal
  - `{"source_id": 3, "measure_key": "amount_total"}` — **cross-source**

### 2.2 Cross-source (ข้อ 6)

- `_aggregate_requests()` ข้าม slot ที่เป็น dict (ไม่ใช่การอ่านจาก model ของ widget)
- `_external_slot_values()` อ่าน `_read_group` จาก model ของ source ปลายทาง **โดยไม่มี domain**
  (ค่าข้ามโมเดลไม่ผูกกับช่วงเวลาของ widget) แล้วส่งเข้า context ผ่าน `_formula_extra()`
- `_validate_formula_config()` ตรวจ `measure_key` ของ slot ภายนอกกับ source ปลายทาง

### 2.3 Cross-dashboard widget reference (ข้อ 6)

- `_dependency_ids()` คืน id ของ widget ที่อ้าง **ทุก dashboard** (rule `compare_widget_id` + `widget_<id>`)
- `_local_dependency_ids()` = ตัดเฉพาะ widget ใน dashboard เดียวกัน (ใช้กับ `_compute_order()`)
- `Od19Dashboard._check_no_cycle()` เดินกราฟแบบ transitive closure ข้าม dashboard แล้วทำ topological sort
- `Od19Dashboard._resolve_dependency_values()` เติมค่า widget ภายนอกเข้า `widget_values` แบบ lazy
  พร้อม stack guard (เจอ cycle → ปล่อยค่าเป็น None, fail soft)

---

## 3. Status rule engine — ส่วนขยาย

### 3.1 ขอบเขตใหม่

| widget type | การประเมินกฎ |
|---|---|
| `kpi` | ค่าเดียวของ widget (ตามเฟส 1) |
| `bar` / `line` / `pie` | **ต่อ bucket** — แต่ละ bucket ได้สถานะของตัวเอง |
| `list` | **ต่อแถว** — แต่ละแถวได้สถานะของตัวเอง |

- สถานะระดับ widget = สถานะที่ "รุนแรงที่สุด" ของ bucket/แถว (`red` > `yellow` > `green` > `grey`)
- ถ้าไม่มี bucket/แถว → `grey`

### 3.2 ข้อความเตือน

- `_evaluate_rules(context)` คืน `(status, status_source, message)`
- bucket/แถวที่เข้าเงื่อนไขเก็บ `status` + `message` ของตัวเอง
- widget เก็บ `status_message` = ข้อความของ bucket/แถวที่รุนแรงที่สุด (หรือของกฎที่ match บนค่า widget)

### 3.3 Conditional display (ข้อ 1)

- `visible_expression` ประเมินด้วย context: `value`, `goal`, `count_records`, `widget_<id>`, slot/measure ที่ใช้ได้
- ผลลัพธ์ falsy (0 / False) → `visible = False`
- widget ที่ซ่อนจะไม่ถูก render บน dashboard แต่ใน edit mode แสดงเป็น placeholder
- validation: `_validate_formula_config()` ตรวจ `visible_expression` ด้วย `_allowed_names() | {"value"}`

---

## 4. Meta ที่ส่งให้ builder

`get_builder_meta()` เพิ่ม:

- `formulas` — `[formula._to_meta()]`
- `status_colors` — `{status: "#RRGGBB"}` ให้ client ระบายสีกราฟ/list
- `formula_modes` มี `library` เพิ่ม

---

## 5. Front-end

- **builder_dialog**: เพิ่มโหมด Library formula + dropdown สูตร, slot table ที่ derive จากชื่อในสูตร,
  ช่อง Visibility, คอลัมน์ Alert message ในตารางกฎ (แสดงตารางกฎทุก widget type), preview ต่อ bucket
- **dashboard_action**: ซ่อน widget เมื่อ `visible === false` (ยกเว้น edit mode),
  ระบายสี bar / line dot / pie slice / list row ตาม `status` ของ bucket/แถว, แสดง alert banner
- **scss**: alert banner, hidden placeholder, list row status

---

## 6. Security

`ir.model.access.csv` เพิ่ม 3 บรรทัด (`od19.dashboard.formula`):

- viewer (`base.group_user`) — read
- user (`group_od19_dashboard_user`) — read/write/create/unlink
- manager (`group_od19_dashboard_manager`) — full

`dashboard_security.xml` เพิ่ม record rules 3 ข้อ: read (shared/own company) / designer / manager

---

## 7. Migration / version

- `__manifest__.py` version `19.0.2.0.0` → `19.0.3.0.0`
- ฟิลด์ใหม่ทั้งหมดมี default ⇒ Odoo เติมคอลัมน์ให้เอง ไม่ต้องมี migration script
- `visible_expression` default `''` ⇒ widget เดิมยังแสดงเสมอ (พฤติกรรมเดิม)

---

## 8. การทดสอบ

- `test_dashboard_formula.py` — helper ล้วน (เพิ่ม: expression_names ของสูตรคลัง)
- `test_dashboard_rules.py` — rule model (แก้ `test_rule_rejects_cross_dashboard_widget` → อนุญาต),
  `alert_message` ใน `_to_values`
- `test_dashboard_engine.py` — engine (เพิ่ม: library mode, cross-source slot, per-bucket status,
  conditional display, cross-dashboard value)
- รัน: `venv19\Scripts\python.exe odoo-bin -c odoo.conf -d odoo19 -u od19_dashboard --test-enable --test-tags /od19_dashboard --stop-after-init --log-level=test --logfile=<tmp>`
