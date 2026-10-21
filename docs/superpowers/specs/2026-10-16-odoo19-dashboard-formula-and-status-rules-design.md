# Odoo 19 CE: Dashboard Formula Engine and Status Rule Engine

## Control Metadata
- Child spec ID: W6-DASH-FORMULA-RULES
- Wave: Cross-cutting reporting track (labeled Wave 6 — Internal Operations; outside the Wave 0–5 domain roadmap)
- Status: Implemented — formula engine and status rule engine delivered in module `od19_dashboard` (see `2026-10-16-odoo19-dashboard-formula-and-status-rules-implementation-plan.md`)
- Owner: Business owner (reporting consumer)
- Reviewer: Technical supervisor
- Approvers: Business owner; Technical supervisor
- Target edition: Odoo 19 Community Edition (CE)
- Target module: `od19_dashboard` (`custom_addons/od19_dashboard`)
- Canonical path: `docs/superpowers/specs/2026-10-16-odoo19-dashboard-formula-and-status-rules-design.md`
- Related specs:
  - `docs/superpowers/programs/odoo19-enterprise/reporting/role-based-dashboard-blueprint.md`
  - `docs/superpowers/programs/odoo19-enterprise/reporting/kpi-reporting-baseline.md`
- Date: 2026-10-16
- Primary readers: Business owner, management, operational leads, technical supervisor

## Approval Traceability
- Dashboard blueprint + in-browser builder delivered earlier (module `od19_dashboard`, version `19.0.1.0.0`).
- Business owner requested formula and result-condition capability on 2026-10-16.
- Design decisions confirmed with the business owner on 2026-10-16:
  - Formula authoring: preset formulas **and** advanced free-text expressions.
  - Conditions wanted: status/colour rules, show/hide widget, alert text, value-driven formatting — delivered in **2 phases**.
  - Formulas apply to **all widget types**, including per-group evaluation for charts.
  - Formula operands: measures of the **same source** plus **values of other widgets in the same dashboard**.
  - 14 preset formulas required (list in section 4).
  - A status rule compares the widget value against a constant, the goal, a percentage of the goal, **or another widget**, **or the previous / YtY / MtM / QtQ period**.
  - Conflicting rules: **first match wins**, ordered top-to-bottom, reorderable in the UI.
  - Existing `threshold_mode` / `warning_value` / `critical_value` data is **migrated automatically**; the legacy fields are removed.
  - When a formula fails: validation on save, and at runtime show `—` with an explanatory tooltip instead of breaking the dashboard.
  - **Live preview** required inside the formula editing screen: show the computed result and the expected number of records collected.
  - Authoring permission: any user with the Dashboard Designer role.

## Discovery Evidence
- Current-state references (verified by reading the code on 2026-10-16):
  - `custom_addons/od19_dashboard/models/dashboard.py`
    - `_fill_kpi_data` (lines 513–529) computes a single aggregate through one `_read_group` call and derives the previous-period delta through `_build_domain(..., previous=True)`.
    - `_build_domain` (615–635) and `_date_bounds` (637–686) support exactly two states: current period and `previous=True`.
    - `_compute_status` (688–702) is a hard-coded `if` chain driven by `threshold_mode`, `warning_value` and `critical_value`.
    - `_to_config` (423–447) is the exact dictionary contract consumed by the builder dialog.
    - `_get_widget_data` (452–511) already fails soft: a widget error becomes `message` + `status = grey` and never breaks the dashboard.
  - `custom_addons/od19_dashboard/models/dashboard_source.py`
    - Whitelist model `od19.dashboard.source` and `.source.field`; `_aggregate_spec` (114–124) returns a single aggregate spec (`field:agg`, or `__count`).
    - `_to_meta` (61–87) exposes `measures` with `key` equal to the raw field name, or `__count`.
  - `custom_addons/od19_dashboard/static/src/dashboard/builder_dialog.js` — `DEFAULT_CONFIG` (11–31) mirrors `_to_config`.
  - `custom_addons/od19_dashboard/static/src/dashboard/builder_dialog.xml` — sections Content / Data / Target & status / Layout.
  - `custom_addons/od19_dashboard/security/ir.model.access.csv` and `security/dashboard_security.xml` — ACL + record-rule pattern to follow for the new rule model.
  - `odoo/tools/safe_eval.py` lines 218–220 — `assert_valid_names` raises `NameError` for **any name containing two underscores**. `__count` therefore cannot be used as a variable name in a formula; an alias is mandatory.
- Verified constraints:
  - `od19_dashboard` manifest version is `19.0.1.0.0`; the module is installed and the seeded baseline dashboards carry widgets with thresholds.
  - `data/dashboard_data.xml` uses `noupdate="1"`, so existing seeded records are never overwritten by a module update — a migration script is required for existing databases.
  - Every widget of the seeded dashboards is owned by `__system__`; `base.group_system` implies `group_od19_dashboard_manager` (added earlier), so admins can design every dashboard.
- Evidence coverage gaps:
  - The `admin_passwd` in `odoo.conf` is a PBKDF2 hash, so interactive UI verification must be performed by the business owner.
  - No widget currently uses a cross-widget reference, so cross-widget behaviour is validated only by automated runtime tests in this phase.

## Delivery Controls
- Dependencies:
  - `od19_dashboard` `19.0.1.0.0` installed and verified.
  - Odoo 19 `safe_eval` semantics (no `__` in names, attribute access restricted) as documented above.
  - Existing whitelist model `od19.dashboard.source` remains the single source of allowed models and fields.
- Gate readiness:
  - Spec-ready: every open question answered in the Approval Traceability section.
  - Plan-ready: data model, expression context, evaluation order, migration path and test strategy are fixed below.
  - Build-ready: no unknown library or external service is required.

## 1. สรุปสั้น ๆ

สเปกนี้ออกแบบส่วนขยาย 2 ระบบให้กับ dashboard builder ที่มีอยู่แล้ว:

1. **Formula engine** — ผู้ใช้กำหนด "สูตร" ของ widget ได้ 3 โหมด: measure เดียว (พฤติกรรมเดิม), สูตรสำเร็จรูป 14 แบบ, และพิมพ์ expression เอง พร้อมอ้างค่าของ widget อื่นใน dashboard เดียวกันได้ และประเมินได้ทั้งแบบค่าเดียว (KPI/List) และแบบต่อกลุ่ม (กราฟ)
2. **Status rule engine** — แทนที่ threshold แบบ if-chain เดิม ด้วยตารางกฎที่เรียงลำดับได้ แต่ละแถวเทียบ "ค่าของ widget" กับค่าคงที่ / goal / % ของ goal / ค่าของ widget อื่น / ช่วงเวลาก่อนหน้า (previous, YtY, MtM, QtQ) แล้วกำหนดสถานะสี

ทั้งสองระบบทำงานฝั่ง server ภายใต้ whitelist ที่มีอยู่ และเพิ่ม **Live Preview** ในหน้าทำสูตร ที่แสดงผลลัพธ์ที่คำนวณจริงและจำนวน record ที่คาดว่าจะรวบรวมได้ ก่อนกดบันทึก

เป้าหมายเชิงธุรกิจ: ให้ผู้ใช้ธุรกิจนิยามตัวชี้วัดของตนเองได้เองโดยไม่ต้องเขียนโค้ด และไม่ต้องรอทีมเทคนิคทุกครั้งที่มีนิยามใหม่ เช่น อัตรากำไรต่อออเดอร์, % เทียบปีก่อน, หรือยอดค้างชำระเทียบเป้า

## 2. ขอบเขต

### ในขอบเขต (เฟส 1)
- Formula engine: 14 สูตรสำเร็จรูป + โหมดพิมพ์ expression เอง + โหมดผูกตัวแปรง่าย (a–e)
- การประเมินสูตรต่อกลุ่มสำหรับ bar / line / pie
- การอ้างค่าของ widget อื่นใน dashboard เดียวกัน พร้อมตรวจ cycle
- Status rule engine: ตารางกฎ, first-match-wins, การเทียบกับค่าคงที่ / goal / % ของ goal / widget อื่น / previous / YtY / MtM / QtQ — สำหรับ widget ประเภท KPI (ดูข้อ 5.0)
- `default_status` สำหรับกรณีไม่มีกฎใดเข้าเงื่อนไข
- Live Preview ในหน้าทำสูตร (ผลลัพธ์ + จำนวน record + สถานะ + alias ที่ใช้จริง)
- Migration อัตโนมัติของ threshold เดิมเป็น rule และลบ field เดิม
- ACL + record rules สำหรับ model ใหม่
- การทดสอบ runtime แบบ in-process และการตรวจ static asset

### นอกขอบเขต (เฟส 2)
- เงื่อนไขซ่อน/แสดง widget (conditional display)
- ข้อความเตือน / alert message บน widget
- Conditional formatting ของกราฟและแถวใน list
- กฎที่ประเมิน "ต่อ bucket" ของกราฟ (สีรายแท่ง/รายจุด)
- คลังสูตรใช้ซ้ำข้าม widget (named reusable formula) — พิจารณาเป็นแนวทาง 2 ที่ยังไม่เลือก
- ค่าของ widget อื่นคนละ dashboard และ cross-source formula (ข้าม model)

## 3. โมเดลข้อมูล

### 3.1 เพิ่มบน `od19.dashboard.widget`

| Field | Type | Default | หน้าที่ |
|---|---|---|---|
| `formula_mode` | Selection: `measure` / `preset` / `custom` | `measure` | โหมดการได้มาซึ่งค่า; `measure` = พฤติกรรมเดิม |
| `formula_type` | Selection 14 สูตร (ตารางในข้อ 4.2) | — | ใช้เมื่อ `formula_mode = preset` |
| `formula_slots` | Text (JSON) | `{}` | ผูก slot → measure key: `{"a": "amount_total", "b": "__count"}`; รองรับ slot `a`–`e` และ slot น้ำหนัก `w1`, `w2` |
| `formula_expression` | Char | — | expression ที่ประเมิน ใช้เมื่อ `formula_mode = custom` |
| `formula_basis` | Selection: `previous` / `yty` / `mtm` / `qtq` | `previous` | ฐานเปรียบเทียบของสูตร `growth` และ `cumulative_change` |
| `delta_basis` | Selection: `previous` / `yty` / `mtm` / `qtq` | `previous` | ฐานของป้าย Delta บน KPI (`show_delta`) |
| `default_status` | Selection: `red` / `yellow` / `green` / `grey` | `green` | สถานะเมื่อไม่มี rule ใดเข้าเงื่อนไข |
| `rule_ids` | One2many → `od19.dashboard.widget.rule` | — | ตารางกฎสถานะ/สี |

**ลบออก:** `threshold_mode`, `warning_value`, `critical_value`
**คงไว้:** `goal_value` (ใช้เป็นตัวแปร `goal` ในสูตรและกฎ)

### 3.2 Model ใหม่ `od19.dashboard.widget.rule`

- `_order = "sequence, id"`, `_description = "Dashboard Widget Status Rule"`
- Fields:
  - `widget_id` — Many2one `od19.dashboard.widget`, required, `ondelete="cascade"`, indexed
  - `sequence` — Integer, default 10
  - `name` — Char (ป้ายอธิบาย เช่น "ต่ำกว่าเป้า 20%")
  - `active` — Boolean, default True
  - `operator` — Selection: `>` `>=` `<` `<=` `==` `!=`
  - `compare_type` — Selection: `constant` / `goal` / `percent_of_goal` / `widget` / `prev` / `yty` / `mtm` / `qtq`
  - `compare_value` — Float (ใช้เมื่อ `compare_type = constant`)
  - `compare_percent` — Float (ใช้เมื่อ `compare_type = percent_of_goal`; 80 หมายถึง 80% ของ goal)
  - `compare_widget_id` — Many2one `od19.dashboard.widget` (ใช้เมื่อ `compare_type = widget`)
  - `status` — Selection: `red` / `yellow` / `green` / `grey`
- Constraints:
  - `compare_widget_id != widget_id` — widget ห้ามอ้างตัวเอง
  - `compare_widget_id.dashboard_id == widget_id.dashboard_id` — ต้องอยู่ dashboard เดียวกัน
  - `compare_type = widget` → `compare_widget_id` ต้องไม่ว่าง
  - `compare_type = constant` → ต้องระบุ `compare_value`; `compare_type = percent_of_goal` → ต้องระบุ `compare_percent`
- ด้านซ้ายของเงื่อนไขคือ **ค่าของ widget เจ้าของกฎ (`value`) เสมอ** — ไม่มี left operand ที่เลือกได้

### 3.3 Security

- `security/ir.model.access.csv` เพิ่ม 3 บรรทัด (ชื่อ access ต้องไม่ซ้ำกับโมดูลอื่น):
  - `access_od19_dashboard_widget_rule_view` — `od19.dashboard.widget.rule` — `group_od19_dashboard_user` — read
  - `access_od19_dashboard_widget_rule_designer` — write/create/unlink
  - `access_od19_dashboard_widget_rule_manager` — `group_od19_dashboard_manager` — full
- `security/dashboard_security.xml` เพิ่ม record rules 3 ข้อตาม pattern เดิม (read / designer / manager) โดยใช้ `widget_id.dashboard_id` เป็นตัวอ้างอิงสิทธิ์
- ลำดับการโหลดใน manifest: `dashboard_security.xml` ต้องมาก่อน `ir.model.access.csv` (ข้อกำหนดที่มีอยู่แล้ว)

## 4. Formula engine

### 4.1 หลักการประเมิน

1. เก็บรายการ aggregate spec ทั้งหมดที่ widget ต้องใช้ (จาก slot/measure ที่อ้าง) แล้วเรียก `_read_group` **ครั้งเดียวต่อ domain**
2. สร้าง context แล้วประเมิน expression ด้วย `safe_eval`
3. ตรวจ AST ก่อนประเมิน (ข้อ 7)
4. ถ้าผลลัพธ์เป็น `None` หรือเกิดข้อผิดพลาด → `value = None`, `status = grey`, `message` อธิบายสาเหตุ

สำหรับชาร์ต เรียก `_read_group(domain, [groupby_spec], [spec_a, spec_b, ...])` แล้วประเมิน expression **ต่อแถว** จึงได้สูตรแบบต่อกลุ่ม

### 4.2 สูตรสำเร็จรูป (14 แบบ)

| # | `formula_type` | ป้ายใน UI | expression ที่ระบบสร้าง |
|---|---|---|---|
| 1 | `ratio` | Ratio (A ÷ B) | `a / b` |
| 2 | `difference` | Difference (A − B) | `a - b` |
| 3 | `growth` | Growth % | `(a - b) / b * 100` (b = ค่าของ `formula_basis`) |
| 4 | `share` | Share % | `a / total_a * 100` (`total_a` = ผลรวมของ measure a ทั้งโดเมน) |
| 5 | `sum` | Sum | `a + b + c` (+ d, e) |
| 6 | `average` | Average | `(a + b + c) / 3` (หารด้วยจำนวน slot ที่ผูก) |
| 7 | `weighted_average` | Weighted Average | `(a * w1 + b * w2) / (w1 + w2)` |
| 8 | `percent_of_goal` | % of Goal | `a / goal * 100` |
| 9 | `min` | Min | `min(a, b)` |
| 10 | `max` | Max | `max(a, b)` |
| 11 | `cumulative_change` | Cumulative Change | ผลรวมสะสมของ (bucket − bucket ก่อนหน้า) ต่อ bucket — ใช้กับ line chart |
| 12 | `run_rate` | Run Rate | `a * days_in_period / days_elapsed` |
| 13 | `conversion_rate` | Conversion Rate | `a / b * 100` |
| 14 | `variance` | Variance | `abs(a - b)` |

สูตรที่ใช้ slot ให้ผู้ใช้ผูก measure กับ slot ผ่าน dropdown โดยระบบแสดง expression ที่สร้างให้ดู (read-only) เพื่อให้เห็นว่าคำนวณอะไร

ข้อกำหนดเฉพาะของบางสูตร:
- `cumulative_change` บน widget ประเภทกราฟ = ผลรวมสะสมของผลต่างระหว่าง bucket ต่อเนื่องกัน แสดงเป็นเส้นสะสม; บน widget ที่ไม่ใช่กราฟ = ผลรวมของผลต่างทุก bucket (ค่าเดียว)
- `share` ต้องยิงคำสั่งเพิ่ม 1 ครั้งเพื่อหา `total_a` (ผลรวมของ measure a ทั้งโดเมน)
- `run_rate` ต้องมี `date_key` และ `date_range` ที่มีขอบเขตชัดเจน (ไม่ใช่ `all_time`) จึงคำนวณ `days_in_period` / `days_elapsed` ได้; ถ้าไม่มี ให้ widget แสดง `—` พร้อมข้อความบอกให้เลือก date field และช่วงเวลา

### 4.3 Context ของ `safe_eval`

อนุญาตเฉพาะชื่อต่อไปนี้ (ไม่มี model, env, หรือ builtin อื่นนอกจาก `min`, `max`, `abs`, `round`):

| ชื่อ | ความหมาย |
|---|---|
| `<field_name>` | measure ของ source นั้น เช่น `amount_total` (ค่า aggregate ตาม `agg` ที่ตั้งใน source field) |
| `count_records` | alias ของ `__count` — **บังคับ** เพราะ `safe_eval` ห้ามชื่อที่มี `__` |
| `a`, `b`, `c`, `d`, `e` | slot ในโหมดง่าย |
| `w1`, `w2` | slot น้ำหนักของ `weighted_average` |
| `goal` | `goal_value` ของ widget |
| `total_a` | ผลรวมของ measure a ทั้งโดเมน (ใช้กับ `share`) |
| `widget_<id>` | ค่าที่คำนวณได้ของ widget อื่นใน dashboard เดียวกัน |

### 4.4 การอ้างค่าข้าม widget

- สร้าง dependency graph ของ widget ทั้งหมดใน dashboard (edge: widget → widget ที่อ้าง)
- เรียงลำดับการคำนวณแบบ topological เพื่อให้ widget ที่อ้างถูกคำนวณก่อน
- ตรวจ cycle ตอนบันทึก → ปฏิเสธพร้อมข้อความระบุ widget ที่วนกัน
- widget ที่อ้างจะถูกค้นจาก `widget_<id>`; ถ้า widget นั้นถูกลบหรือปิดใช้งาน → ถือเป็น dependency หาย (ข้อ 7)
- การอ้างข้าม dashboard และข้าม source **ไม่อยู่ในขอบเขต**

### 4.5 โหมดง่าย (a–e)

ผู้ใช้ผูก measure กับ slot ทีละตัวผ่าน dropdown สูงสุด 5 slot ระบบเก็บใน `formula_slots` และประกอบ expression ให้เองตาม `formula_type` หรือ — ถ้าเลือก `custom` — เปิดให้แก้ expression ที่อ้าง slot เหล่านั้นได้

## 5. Status rule engine

### 5.0 ขอบเขตการใช้งาน

กฎสถานะประเมินจาก "ค่าของ widget" ซึ่งมีเฉพาะ widget ที่ให้ค่าเดี่ยว (`kpi`) ในเฟสนี้

- widget ประเภท `bar` / `line` / `pie` / `list` ยังคงได้สถานะ `green` / `grey` แบบเดิม (ตามข้อมูลที่มี/ไม่มี)
- ในหน้าจอ builder ตาราง Status rules แสดงเมื่อ `widget_type = kpi` เท่านั้น
- การประเมินต่อ bucket/ต่อแถวของกราฟและ list อยู่ในเฟส 2 (conditional formatting)

### 5.1 ลำดับการตัดสิน

```text
_compute_status(value, ctx):
    for rule in rule_ids.filtered("active").sorted(sequence, id):
        if evaluate(rule, value, ctx):
            return rule.status            # แถวแรกที่เข้าเงื่อนไขชนะ
    return default_status
```

### 5.2 ค่าฝั่งขวาตาม `compare_type`

| `compare_type` | ค่าที่นำมาเทียบ |
|---|---|
| `constant` | `compare_value` |
| `goal` | `goal_value` |
| `percent_of_goal` | `goal_value * compare_percent / 100` |
| `widget` | ค่าที่คำนวณได้ของ `compare_widget_id` (ใช้ dependency graph) |
| `prev` | ค่าของ widget เองใน "ช่วงก่อนหน้า" (เลื่อนถอยหลังเท่าความยาวช่วง) |
| `yty` | ค่าของ widget เอง ช่วงเดียวกันของปีก่อน (Year-to-Year) |
| `mtm` | ค่าของ widget เองในเดือนปฏิทินก่อนหน้า (Month-to-Month) |
| `qtq` | ค่าของ widget เองในไตรมาสปฏิทินก่อนหน้า (Quarter-to-Quarter) |

ถ้าค่าฝั่งขวาคำนวณไม่ได้ (หารศูนย์ / dependency หาย / ไม่มีขอบเขตเวลา) → **ข้ามแถวนั้น** ถือว่าไม่เข้าเงื่อนไข

### 5.3 การเลื่อนช่วงเวลา — ขยาย `_date_bounds`

เปลี่ยนพารามิเตอร์ `previous=False` เป็น `shift=None` ที่รับค่า `previous` / `yty` / `mtm` / `qtq`:

- `previous` — เลื่อนถอยหลังเท่าความยาวของช่วงปัจจุบัน (พฤติกรรมเดิม, ต้องคงไว้เพื่อ backward compatibility ของ `delta`)
- `yty` — เลื่อน `start` และ `end` ถอยหลัง 1 ปีปฏิทิน จัดการกรณี 29 ก.พ. (ถ้าปีปลายทางไม่มีวันที่นั้น ให้ใช้ 28 ก.พ.)
- `mtm` — เดือนปฏิทินก่อนหน้าของ `start` และ `end` (จัดการความยาวเดือนไม่เท่ากันด้วยการยึดวันสุดท้ายของเดือนเมื่อจำเป็น)
- `qtq` — ไตรมาสปฏิทินก่อนหน้า
- ถ้า `date_range = all_time` หรือไม่มี `date_key` → ไม่มีขอบเขตเวลาให้เลื่อน → ไม่คืนเงื่อนไขวันที่ และ widget ที่ต้องใช้ `prev` / `yty` / `mtm` / `qtq` จะได้ข้อความบอกให้เลือกช่วงเวลาก่อน
- คงการจัดการ `date` เทียบกับ `datetime` (`00:00:00` / `23:59:59`) ตามเดิม

`delta_basis` ใช้กลไกเดียวกันนี้ผ่าน `_build_domain(..., shift=...)` แทน `previous=True`

### 5.4 การ migrate threshold เดิม

สำหรับ widget ที่มี `threshold_mode != none`:

- `higher_is_better`
  - rule 1: `operator = "<="`, `compare_type = constant`, `compare_value = critical_value`, `status = red`
  - rule 2: `operator = "<="`, `compare_type = constant`, `compare_value = warning_value`, `status = yellow`
  - `default_status = green`
- `lower_is_better`
  - rule 1: `operator = ">="`, `compare_type = constant`, `compare_value = critical_value`, `status = red`
  - rule 2: `operator = ">="`, `compare_type = constant`, `compare_value = warning_value`, `status = yellow`
  - `default_status = green`

ผลลัพธ์ต้องเทียบเท่าตรรกะเดิมของ `_compute_status` ในทุกช่วงค่า

## 6. Live Preview

### 6.1 RPC ใหม่

`od19.dashboard.preview_widget(values, date_range=None)` — `@api.model`, **ไม่เขียนฐานข้อมูล**

รับ draft config จาก builder (รูปแบบเดียวกับ `_to_config`) และคืน:

| Key | ความหมาย |
|---|---|
| `value` | ผลลัพธ์ที่คำนวณได้จริง (None ถ้าคำนวณไม่ได้) |
| `value_text` | ผลลัพธ์ที่จัดรูปแบบตาม `value_format` แล้ว |
| `record_count` | จำนวน record ที่คาดว่าจะรวบรวมได้ (`_read_group(domain, [], ["__count"])`) |
| `status` | สถานะที่ได้จาก rule engine |
| `status_source` | ป้ายระบุว่ามาจาก rule ใด (ชื่อ/sequence) หรือ `default_status` |
| `operands` | รายการ alias → `{label, value}` ที่ใช้จริงในการคำนวณ |
| `series_preview` | 5 bucket แรก (เฉพาะ widget ประเภทกราฟ) |
| `message` | คำอธิบายเมื่อคำนวณไม่ได้ |

- ตรวจสิทธิ์ read ของ model ต้นทางเหมือน `_get_widget_data`
- ใช้ validation ชุดเดียวกับการบันทึก

### 6.2 พฤติกรรมบนหน้าจอ

- แผงขวา "Preview" ในไดอะล็อก builder
- auto-refresh แบบ debounce 600 ms เมื่อค่า draft เปลี่ยน และมีปุ่ม Refresh
- แสดงผลลัพธ์ + จำนวน record + สถานะ + ตาราง alias ที่ใช้จริง
- แสดง expression ที่ระบบสร้างให้ (โหมด preset) เพื่อให้ผู้ใช้เห็นสูตรจริง

## 7. Security และ Validation

- ใช้ `safe_eval` เท่านั้น ห้าม `eval`
- ตรวจ AST ก่อนประเมิน อนุญาตเฉพาะ node: `Expression`, `Name`, `Constant`, `BinOp`, `UnaryOp`, `BoolOp`, `Compare`
  - การเรียกฟังก์ชัน (`Call`) อนุญาตเฉพาะชื่อ `min`, `max`, `abs`, `round`
  - node อื่นทั้งหมด (attribute access, subscript, comprehension, lambda, import ใด ๆ) → ปฏิเสธ
- Whitelist ชื่อตัวแปรตามข้อ 4.3 เท่านั้น ชื่ออื่น → `ValidationError` ที่ระบุชื่อที่ผิดและ widget ที่เกี่ยวข้อง
- ตรวจตอนบันทึก (validate on save):
  - syntax ของ expression และ AST whitelist
  - ชื่อตัวแปรทั้งหมดอยู่ใน whitelist
  - slot ที่สูตรต้องใช้ถูกผูกครบ (เช่น `ratio` ต้องมี `a` และ `b`)
  - ไม่มี cycle ของการอ้างข้าม widget
  - กฎของ rule model ผ่าน constraint ในข้อ 3.2
- พฤติกรรมตอนแสดงผล (fail soft):
  - หารศูนย์ / alias หาย / widget ที่อ้างถูกลบ หรือ cycle ที่หลุดเข้ามา → `value = None`, `status = grey`, `message` อธิบายสาเหตุ
  - widget อื่นใน dashboard ยังคำนวณและแสดงผลปกติ
- สิทธิ์: ผู้ใช้ที่มี Dashboard Designer role ตั้งสูตรและกฎได้ทั้งหมด ผ่าน `_check_edit_access()` ที่มีอยู่ + ACL ของ rule model
- ไม่มีการเพิ่มสิทธิ์ใหม่ใน `ir.model.access.csv` ที่ชนกับชื่อ access เดิม

## 8. Front-end

### 8.1 `builder_dialog.xml`

- หมวด **Content** — คงเดิม
- หมวด **Data** — แยกเป็น
  - **Measure** — dropdown measure เดิม (แสดงเมื่อ `formula_mode = measure`)
  - **Formula** — `formula_mode` → `formula_type` → ตาราง slot (`a`–`e` + น้ำหนัก) → `formula_basis`; เมื่อเลือก `custom` เพิ่ม textarea พร้อมปุ่มแทรกตัวแปรและตาราง alias ด้านล่าง
- หมวด **Target & status** — แทนที่ด้วย
  - `goal_value`
  - ตาราง **Status rules**: operator | compare type | ค่า/widget | สี | ↑↓ | ลบ และปุ่ม "Add rule"
  - `default_status`
  - `delta_basis` (แสดงเมื่อ `show_delta` เป็นจริง)
- หมวด **Layout** — คงเดิม (`grid_w` / `grid_h` พร้อมขอบเขตจาก `props.meta.grid`)

### 8.2 `builder_dialog.js`

- ขยาย `DEFAULT_CONFIG` ให้มี key ใหม่ทั้งหมดตาม `_to_config`
- เพิ่ม getter: `formulaModes`, `formulaTypes`, `compareTypes`, `operators`, `statuses`, `isFormula`, `isCustomFormula`, `isPresetFormula`, `needsWeight`, `slotRows`, `widgetOptions`
- ตั้งค่าเริ่มต้นของ slot/rule เมื่อผู้ใช้เปลี่ยน `formula_mode` หรือ `formula_type`
- เรียก `preview_widget` แบบ debounce 600 ms จาก `onChange` ของทุก field ที่มีผลต่อผลลัพธ์
- ส่ง `rule_ids` เป็นคำสั่ง One2many (`[[0, 0, {...}], [1, id, {...}], [2, id]]`) ผ่าน `create_widget` / `update_widget` ตามรูปแบบ Odoo ปัจจุบัน
- เลื่อนลำดับ rule ใน UI ใช้ pattern drag เดียวกับ widget (`onDragStart` / `onDragOver` / `onDrop`) แล้วส่ง `sequence` ใหม่พร้อมบันทึก

### 8.3 `dashboard_action.js`

- `_decorate` ต้องอ่าน `rule_ids` / `default_status` / `delta_basis` / `formula_*` จาก config ได้
- แสดง expression ที่ระบบสร้าง (ถ้ามี) เป็น tooltip บน widget ในโหมด Customize
- `get_builder_meta()` เพิ่ม: `formula_modes`, `formula_types`, `compare_types`, `operators`, `statuses`, `widget_options` (รายชื่อ widget ใน dashboard ปัจจุบันสำหรับ cross-reference)

### 8.4 `_to_config` และ payload ของ `_get_widget_data`

- `_to_config` เพิ่ม key: `formula_mode`, `formula_type`, `formula_slots`, `formula_expression`, `formula_basis`, `delta_basis`, `default_status`, `rule_ids` (เป็น list ของ `{id, sequence, name, operator, compare_type, compare_value, compare_percent, compare_widget_id, status}`)
- `_get_widget_data` เพิ่ม key: `value_text`, `record_count`, `status_source`, `formula_expression` (expression ที่ใช้จริง) — โดยไม่ลบ key เดิมที่ front-end ใช้อยู่

## 9. Migration และ Versioning

- bump `version` ใน `__manifest__.py` จาก `19.0.1.0.0` เป็น **`19.0.2.0.0`**
- เพิ่มโฟลเดอร์ `migrations/19.0.2.0.0/` (Odoo รันสคริปต์ในโฟลเดอร์ที่ `installed_version < folder_version <= new_version` จึงต้องใช้ version ใหม่ ไม่ใช่ version เดิม)
- **ข้อจำกัดที่ต้องออกแบบรอบรับ:** Odoo รัน `pre-` สคริปต์ *ก่อน* โหลดโค้ด/ปรับ schema และรัน `post-` *หลัง* ปรับ schema แล้ว ดังนั้นเมื่อถึง `post-migrate` คอลัมน์ `threshold_mode` / `warning_value` / `critical_value` ถูกลบไปแล้ว และ `migrate(cr, version)` ก็ไม่ได้รับ `env` มาให้ใช้ ORM ด้วย จึงต้องสำรองค่าผ่านตารางชั่วคราว
  1. `migrations/19.0.2.0.0/pre-migrate.py` — `def migrate(cr, version)` สร้างตารางชั่วคราว `od19_dashboard_threshold_backup(widget_id, threshold_mode, warning_value, critical_value)` แล้วคัดลอกค่าจากตาราง widget ด้วย raw SQL
  2. `migrations/19.0.2.0.0/post-migrate.py` — `def migrate(cr, version)` อ่านตารางชั่วคราว แล้ว `INSERT` แถวลง `od19_dashboard_widget_rule` ด้วย raw SQL ตามตรรกะในข้อ 5.4 พร้อมกำหนด `default_status = 'green'`; ตั้ง `formula_mode = 'measure'` และ `delta_basis = 'previous'` ให้ทุกแถวใน `od19_dashboard_widget`; สุดท้าย `DROP TABLE` ตารางชั่วคราว
  3. ติดตั้งใหม่ (fresh install) ไม่มีข้อมูลเดิม จึงไม่ต้องมี `post_init_hook` — ค่า default มาจาก field definition และ seed ใน `data/dashboard_data.xml`
- อัปเดต `data/dashboard_data.xml` (ซึ่งเป็น `noupdate="1"`) ให้ seed widget ใช้ rule แทน threshold และสาธิตสูตร preset อย่างน้อย 1 widget สำหรับการติดตั้งใหม่; ฐานข้อมูลเดิมได้ค่าจาก migration script
- อัปเดต `description` ใน manifest ให้สะท้อนสูตรและกฎแบบใหม่

## 10. แผนการทดสอบ

### 10.1 ระดับโมดูล
- ติดตั้งใหม่ (`-i od19_dashboard`) → EXITCODE 0 และ log ไม่มี warning ใหม่
- อัปเกรด (`-u od19_dashboard`) บนสำเนาฐานข้อมูลที่มี threshold เดิม → migration ทำงาน, ไม่มี record ตกค้าง
- ตรวจว่า field เดิมถูกลบและไม่มีโค้ด/วิวใดอ้างถึงแล้ว

### 10.2 Runtime แบบ in-process
ใช้รูปแบบเดิมของโครงการ (`sys.path.insert` + `config.parse_config` + `Registry("odoo19")` + `odoo.api.Environment` + `cr.rollback()`) เพื่อทดสอบ:
- ประเมินสูตรทั้ง 14 แบบกับ source จริง → ได้ค่าตัวเลข ไม่เป็น `None` (ยกเว้นกรณีตั้งใจให้ error)
- `count_records` ใช้งานได้ (พิสูจน์ว่า alias เลี่ยงข้อจำกัด `__` ของ `safe_eval`)
- โหมดง่าย `a`/`b` ให้ผลเท่ากับโหมดเต็มที่เขียนชื่อ field ตรง ๆ
- cross-widget: widget B อ้าง `widget_<A>` → ค่าตรงกับค่าของ A
- cycle detection → `ValidationError`
- rule engine: สร้าง 3 กฎที่เข้าเงื่อนไขพร้อมกัน → ต้องได้สีของแถวบนสุด; สลับ `sequence` แล้วผลเปลี่ยนตาม
- `compare_type` ทั้ง 8 แบบให้ค่าฝั่งขวาถูกต้อง
- YtY / MtM / QtQ: เลือก `this_month` แล้วตรวจขอบเขตวันที่ที่สร้างเทียบกับการคำนวณด้วยมือ
- `preview_widget` คืน `value`, `record_count`, `status`, `operands` ครบ
- migration: สร้าง widget แบบ threshold → รัน `migrate` → rule ถูกสร้างครบและ `_compute_status` ให้ผลเทียบเท่าเดิมทุกช่วงค่า
- `_read_group` ถูกเรียกครั้งเดียวต่อ domain ในโหมดสูตร (ตรวจด้วยการนับ query หรือ monkeypatch)

### 10.3 Front-end
- `node --check` ทุกไฟล์ JS ที่แก้
- ชื่อ template ใน JS ตรงกับ `t-name` ใน XML
- static asset ตอบ HTTP 200
- ตรวจว่าผู้ใช้ที่ไม่มีสิทธิ์ write ยังใช้ builder ไม่ได้ (AccessError ตามเดิม)

### 10.4 การทดสอบโดยผู้ใช้
- เปิด http://localhost:8070 → Dashboards → My Dashboards
- ทดสอบ: สร้าง widget ด้วยสูตร preset, พิมพ์สูตรเองในโหมด custom, เพิ่ม/ลบ/เลื่อนกฎสถานะ, ดู Live Preview ก่อนบันทึก
- ทดสอบสูตรต่อกลุ่มบนกราฟ และการอ้างค่าข้าม widget
- (ไม่ทราบรหัส admin จึงต้องให้ผู้ใช้ดำเนินการส่วนนี้)

## 11. ความเสี่ยงและการรับมือ

| ความเสี่ยง | ผลกระทบ | การรับมือ |
|---|---|---|
| `safe_eval` ห้ามชื่อที่มี `__` | สูตรที่ผู้ใช้เขียนด้วย `__count` จะ error ทันที | แมปเป็น alias `count_records` และแสดงในตาราง alias + ปุ่มแทรก; ข้อความ error ระบุให้ใช้ `count_records` |
| ประสิทธิภาพเมื่ออ้าง widget อื่นหลายตัว | dashboard โหลดช้าลง | เรียก `_read_group` ครั้งเดียวต่อ domain; จำกัดการอ้างเฉพาะ dashboard เดียวกัน; preview มี debounce |
| cycle จากการอ้างข้าม widget | dashboard ไม่สามารถคำนวณได้ | ตรวจ topological ตอนบันทึก และ fail soft ตอนแสดงผล |
| การเลื่อนช่วงเวลาปฏิทิน (YtY/MtM/QtQ) | ตัวเลขเทียบผิดช่วง | ยึดกฎที่ระบุในข้อ 5.3 และทดสอบขอบเขตวันที่ตรง ๆ |
| ลบ field เดิมทิ้ง | widget เดิมเสียสถานะสี | migration สร้าง rule เทียบเท่าเดิมทุกช่วงค่า + ทดสอบเทียบผล |
| `data/dashboard_data.xml` เป็น `noupdate="1"` | seed เดิมไม่อัปเดต | ใช้ migration script สำหรับฐานข้อมูลเดิม |
| สูตรซับซ้อนทำให้เกิด query หลายรอบบนกราฟ | ช้าลงตามจำนวน bucket | จำกัด slot สูงสุด 5 และรวม aggregate ในคำสั่งเดียว |

## 12. เกณฑ์ความสำเร็จ

- ผู้ใช้ที่มี Dashboard Designer role สร้างสูตรได้ทั้ง 14 แบบและสูตรที่พิมพ์เอง โดยไม่ต้องแก้โค้ด
- Live Preview แสดงผลลัพธ์และจำนวน record ก่อนบันทึก และตรงกับค่าที่แสดงจริงหลังบันทึก
- กฎสถานะแบบ first-match-wins ทำงานตามลำดับที่ผู้ใช้จัด และเทียบกับค่าคงที่ / goal / % ของ goal / widget อื่น / previous / YtY / MtM / QtQ ได้ครบ
- widget เดิมที่ตั้ง threshold ไว้ยังแสดงสีเดิมหลัง upgrade
- สูตรที่ผิดหรือคำนวณไม่ได้ทำให้เฉพาะ widget นั้นแสดง `—` พร้อมคำอธิบาย โดย dashboard ส่วนที่เหลือทำงานปกติ
- ไม่มีข้อผิดพลาดหรือ warning ใหม่ใน log จากการติดตั้ง/อัปเกรด
