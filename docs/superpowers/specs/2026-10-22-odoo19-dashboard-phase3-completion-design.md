# Odoo 19 Dashboard — เฟส 3 (Completion & Domain Boards) Design

## Control Metadata
- Child spec ID: W6-DASH-PHASE3
- Wave: Cross-cutting reporting track (labeled Wave 6 — Internal Operations; outside the Wave 0–5 domain roadmap) — เฟส 3 ต่อจาก W6-DASH-PHASE2
- Status: Draft — authored 2026-10-22; ยังไม่ implement
- Owner: Business owner (reporting consumer)
- Reviewer: Technical supervisor
- Approvers: Business owner; Technical supervisor
- Target edition: Odoo 19 Community Edition (CE)
- Target module: `od19_dashboard` (`custom_addons/od19_dashboard`) + โมดูลรายโดเมนที่ลงทะเบียน data source
- Canonical path: `docs/superpowers/specs/2026-10-22-odoo19-dashboard-phase3-completion-design.md`
- Date: 2026-10-22
- Baseline source: [2026-10-16-odoo19-dashboard-phase2-presentation-design.md](2026-10-16-odoo19-dashboard-phase2-presentation-design.md)

## 0. ที่มาและหลักฐาน (Evidence)

สเปกเฟส 1 และเฟส 2 ถูกทำเครื่องหมาย **Implemented** แล้ว (module `od19_dashboard` v`19.0.3.0.0`) — ดู [domain-wave-matrix.md](../programs/odoo19-enterprise/backlog/domain-wave-matrix.md) และ [domain-spec-index.md](../programs/odoo19-enterprise/backlog/domain-spec-index.md) ดังนั้นเฟส 3 ไม่ได้เริ่มจาก "ยังทำไม่ครบสเปก" แต่เริ่มจาก **3 แหล่งที่มาที่ตรวจได้จริง**:

| # | แหล่งที่มา | หลักฐาน |
|---|---|---|
| A | Log hygiene ตอน verify runtime | รัน `--test-enable --test-tags /od19_dashboard,/od19_after_sales_reporting` บน `odoo19_pdev` (2026-10-22) พบ `DeprecationWarning` ของ API ที่ Odoo 19 เลิกใช้ |
| B | Deferred Topics ของ blueprint | [role-based-dashboard-blueprint.md L133-138](../programs/odoo19-enterprise/reporting/role-based-dashboard-blueprint.md#L133-L138) |
| C | Deferred Topics ของ KPI baseline | [kpi-reporting-baseline.md L233-238](../programs/odoo19-enterprise/reporting/kpi-reporting-baseline.md#L233-L238) |
| D | Dashboard รายโดเมนที่ยังไม่มี | มีแค่ consolidated after-sales; finance / logistics / HR ยังไม่มีบอร์ด |

### ผล verify ที่ได้แล้ว (2026-10-22, `odoo19_pdev`) — ปิด §0.A บางส่วน

```
odoo.tests.stats: od19_after_sales_reporting: 8 tests 1.87s
odoo.tests.stats: od19_dashboard: 153 tests 7.84s
odoo.tests.result: 0 failed, 0 error(s) of 135 tests when loading database 'odoo19_pdev'
```

Seed ที่ตรวจจาก DB จริง:

| Dashboard | Widgets |
|---|---|
| Owner Executive Dashboard | 9 |
| Management Performance Dashboard | 8 |
| Operations Daily Dashboard | 7 |
| After-Sales Service Dashboard | 17 |

พร้อม data source `od19.report.after.sales.*` ครบ 6 ตัว (ticket / warranty claim / service card / product return / qc inspection / csat period)

## 1. ขอบเขต

### ในขอบเขต (เฟส 3)

1. **Deprecated access API cleanup (§2.1)** — เปลี่ยน `check_access_rights()` + `check_access_rule()` เป็น `check_access()` ตาม Odoo 19
2. **ปิดงาน verify After-Sales Dashboard (§2.2)** — บันทึกผล verify บน `odoo19_pdev` และปิด "unknown" ใน wave-3 spec
3. **Dashboard รายโดเมนที่เหลือ (§3)** — Finance (Wave 2), Logistics/Goods Issue (Wave 4), HR Attendance (Wave 5)
4. **Presentation polish ที่ค้าง (§4)** — final layout, chart selection, real-time streaming
5. **Doc sync (§5)** — ปรับ Deferred Topics ใน blueprint/kpi baseline ให้ตรงกับสถานะจริง

### นอกขอบเขต

- Warehouse/ETL architecture — ไม่ใช่ขอบเขตของ dashboard builder (คงเป็น deferred ของสถาปัตยกรรมข้อมูล)
- Automated threshold tuning — ต้องมีข้อมูลย้อนหลังพอสมควรก่อน; เลื่อนออกไป
- Full metric dictionary ทุกโดเมน — ทำเป็นรายโดเมนตอนสร้างบอร์ด (§3) แทนการทำล่วงหน้าทั้งหมด

## 2. Log hygiene + ปิด verify

### 2.1 เปลี่ยนมาใช้ `check_access()` (Odoo 19)

Odoo 19 รวม `check_access_rights(operation)` และ `check_access_rule(operation)` เป็น `Model.check_access(operation)` ตัวเดียว (ดู `odoo/orm/models.py:4106`) ตัวเดิมถูกทำเครื่องหมาย deprecated since 18

จุดที่ต้องแก้ใน `od19_dashboard`:

| ไฟล์ | บรรทัด | จาก | เป็น |
|---|---|---|---|
| `models/dashboard.py` | 244–245 | `dashboard.check_access_rights("read")` + `dashboard.check_access_rule("read")` | `dashboard.check_access("read")` |
| `models/dashboard.py` | 819 | `model.check_access_rights("read")` | `model.check_access("read")` |
| `models/dashboard.py` | 1101 | `model.check_access_rights("read")` | `model.check_access("read")` |
| `models/dashboard_rule.py` | 103–104 | `target.check_access_rights("read")` + `target.dashboard_id.check_access_rights("read")` | `target.check_access("read")` + `target.dashboard_id.check_access("read")` |

- ยังคง catch `AccessError` เหมือนเดิม (พฤติกรรม fail-soft ไม่เปลี่ยน)
- ที่ L819 และ L1101 เป็นการเช็คระดับ model (recordset ว่าง) — `check_access("read")` บน recordset ว่างจะเช็คสิทธิ์ระดับ model ให้โดยอัตโนมัติ
- **ไม่มี schema change** ⇒ ไม่ต้องมี migration script

### 2.2 ปิดงาน verify After-Sales Dashboard

- เทสต์ 8 ตัวของ `od19_after_sales_reporting` ผ่านบน `odoo19_pdev` (2026-10-22)
- ตรวจ seed จาก DB จริง: After-Sales Service Dashboard (17 widgets) + 6 sources ครบ
- อัปเดต [wave-3 spec L52](../specs/2026-10-21-odoo19-enterprise-wave-3-sales-services-after-sales.md#L52) และ L241 จาก "ยังต้อง verify บน `odoo19_pdev`" เป็น "verified 2026-10-22"
- **ยังเหลือ (ต้องตัดสินใจ §6):** visual/browser check จริง — ผูกกับข้อ O1

## 3. Dashboard รายโดเมนที่เหลือ

หลักการ: แต่ละบอร์ดใช้ **data source whitelist เดิม** ของ `od19_dashboard` (ห้าม query model อิสระ) และยึดโครง zone ตาม blueprint (summary → alert → trend → detail → action)

| # | บอร์ด | Wave | Data source ที่ต้องลงทะเบียน | KPI หลัก |
|---|---|---|---|---|
| D1 | Finance Control Board | Wave 2 | `account.move.line` (AR/AP aging), `od19.cheque`, WHT register, petty cash | AR/AP aging, cheques ครบกำหนด, WHT ค้างนำส่ง, กระแสเงินสด |
| D2 | Logistics Board | Wave 4 | `stock.request.order` (goods issue), `stock.picking`, landed cost | ใบเบิกค้างอนุมัติ, picking ค้างส่ง, GI ต่อแผนก |
| D3 | HR Attendance Board | Wave 5 | `hr.attendance`, `hr.leave` | มาสาย/ขาด, ชั่วโมง OT, การลาค้างอนุมัติ |

- แต่ละบอร์ด seed ผ่านไฟล์ `data/<domain>_dashboard_data.xml` ในโมดูลรายโดเมน (แบบเดียวกับ after-sales)
- เมนูเข้าบอร์ดอยู่ใต้ root menu ของโดเมนนั้น
- **Open decision O2 (§6):** จะทำทั้ง 3 บอร์ดในเฟส 3 หรือทยอยทำตาม wave ที่ปิดจริง

## 4. Presentation polish ที่ค้าง

อ้างอิง Deferred Topics ของ blueprint:

| # | รายการ | แนวทางในเฟส 3 |
|---|---|---|
| P1 | Final screen layout / wireframe polish | จัด grid/ขนาด widget ให้ตรงลำดับความสำคัญของแต่ละ role; จำกัดจำนวน signal ต่อบอร์ด |
| P2 | Exact chart selection | กำหนด chart type คงที่ต่อชนิด KPI (trend → line, composition → pie, comparison → bar) |
| P3 | Real-time streaming behavior | **คงเป็น deferred** — บอร์ดปัจจุบัน refresh ตามการเปิดหน้า; real-time streaming ต้องมี websocket/bus เพิ่ม ซึ่งขัดหลัก Low-resource ⇒ ไม่ทำในเฟส 3 |
| P4 | Permission model ของ dashboard access | **ปิดแล้ว** — เฟส 2 เพิ่ม record rules ใน `security/dashboard_security.xml` ⇒ ปรับเอกสาร (§5) |

## 5. Doc sync

- `role-based-dashboard-blueprint.md` — Deferred Topics: ตัด "Permission model implementation for dashboard access" ออก (implemented ในเฟส 2); ระบุ P3 (real-time) คงเป็น deferred
- `kpi-reporting-baseline.md` — Deferred Topics: "Final dashboard UI implementation" ให้ชี้มาที่เฟส 3; "Full metric dictionary" เปลี่ยนเป็นรายโดเมน (§3)
- `domain-wave-matrix.md` / `domain-spec-index.md` — เพิ่มแถว `W6-DASH-PHASE3` สถานะ Draft
- `wave-3 spec` — ปิด L52/L241 ตาม §2.2

## 6. Open Decisions (ต้องให้เจ้าของงานตัดสิน)

| # | คำถาม | ทางเลือก |
|---|---|---|
| O1 | visual/browser check ของ After-Sales Dashboard | (ก) ตรวจผ่าน DB + เทสต์เท่านั้น (ทำแล้ว) / (ข) เปิด server แล้วตรวจผ่านเบราว์เซอร์จริงด้วย Chrome DevTools |
| O2 | ขอบเขตบอร์ดรายโดเมน | (ก) ทำทั้ง D1–D3 ในเฟส 3 / (ข) ทำ D1 (finance) ก่อน แล้วค่อย D2/D3 ตาม wave |
| O3 | Circular dependency warning (dashboard ถาวร) | (ก) คง fail-soft + เขียน log ระดับ debug แทน warning เพื่อลด noise / (ข) คง warning ไว้ |

## 7. การทดสอบ (Verification plan)

1. หลังแก้ §2.1 รันซ้ำ:
   ```
   .\venv19\Scripts\python.exe odoo-bin -c odoo.conf -d odoo19_pdev ^
     -u od19_dashboard,od19_after_sales_reporting --test-enable ^
     --test-tags /od19_dashboard,/od19_after_sales_reporting ^
     --stop-after-init --log-level=test --logfile=%TEMP%\od19_dash_phase3.log
   ```
2. เกณฑ์ผ่าน:
   - `0 failed, 0 error(s)` ทุกโมดูล
   - **ไม่มี** `DeprecationWarning: check_access_rights()` / `check_access_rule()` ใน log
3. ตรวจ seed ของบอร์ดใหม่ (D1–D3) ด้วย query `od19_dashboard` + `od19_dashboard_source` ให้ widget/source ครบ
4. ตรวจว่า widget ทุกตัวบนบอร์ดใหม่ประเมินค่าได้จริง (ไม่ขึ้น "no access" / "source not installed")

## 8. Version / Migration

- งาน §2.1 เป็น code-only ⇒ **ไม่ต้อง** bump version เฉพาะกรณีนี้
- ถ้ามี §3 (บอร์ดใหม่เป็น data records) ⇒ bump `19.0.3.0.0` → `19.0.4.0.0` และเพิ่ม `migrations/19.0.4.0.0/post-migrate.py` เฉพาะเมื่อมีการย้าย/rename record
