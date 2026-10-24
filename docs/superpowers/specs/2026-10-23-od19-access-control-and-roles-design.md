# Odoo 19: โครงสร้างสิทธการเข้าถึงและบทบาทผู้ใช้ (Access Control & User Roles)

## Control Metadata

| รายการ | ค่า |
|---|---|
| Spec ID | W0-ACCESS-ROLES |
| Wave | Wave 0 — Foundation / Governance (ตัดขวางทุก Wave) |
| Status | อนุมัติแนวทางแล้ว (Approach C) — อยู่ระหว่างพัฒนา |
| Owner | Business owner (ผู้บริหารที่กำกับนโยบายสิทธิ์) |
| Reviewer | Technical supervisor |
| Approvers | Business owner; Technical supervisor |
| Target edition | Odoo 19 Enterprise (Greenfield) |
| วันที่ | 2026-10-23 |
| โมดูลที่เกี่ยวข้อง | `od19_security_roles` (ใหม่), `od19_role_catalog` (ใหม่), `base_user_role` (OCA) |

---

## Approval Traceability

| # | การตัดสินใจ | ผู้ยืนยัน | วันที่ |
|---|---|---|---|
| D1 | ดำเนินงาน 3 เฟส: A (บทบาท/กลุ่ม) → B (ACL + record rule) → C (ผูกผู้ใช้) | Business owner | 2026-10-23 |
| D2 | แกนบทบาทยึด "หน้าที่งาน" (คุมสิทธิ์) + "แผนก" เป็น record rule (คุมขอบเขต) | Business owner | 2026-10-23 |
| D3 | แหล่งความจริงของแผนก = `hr.employee.department_id` และ mirror ลง `res.users` | Business owner | 2026-10-23 |
| D4 | ร่าง Role Matrix ให้ก่อน (~30 บทบาท) แล้วให้ผู้ใช้ตรวจ | Business owner | 2026-10-23 |
| D5 | ขอบเขต record rule: เฉพาะโมเดลที่มี `department_id` เป็นเจ้าของข้อมูลจริง + SoD | Business owner | 2026-10-23 |
| D6 | ผู้ใช้ตั้งต้น: baseline จาก Odoo 15 + กำหนดบทบาทด้วย role matrix (ไม่ auto-map กลุ่มเดิม) | Business owner | 2026-10-23 |
| D7 | ที่อยู่โมดูล: แยก 2 โมดูล (`od19_security_roles` = Layer 1, `od19_role_catalog` = Layer 2) | Business owner | 2026-10-23 |
| D8 | วงเงินอนุมัติทั้ง SO/PO ใช้ฟิลด์บน `res.company` เป็นแหล่งความจริงเดียว | Business owner | 2026-10-23 |
| D9 | ขอบเขตแผนกแบบ "แผนกของตัวเอง" (`department_id = user.od19_department_id`) ไม่รวมแผนกลูก | Business owner | 2026-10-23 |

---

## Discovery Evidence

| หลักฐาน | แหล่งอ้างอิง | ข้อสรุป |
|---|---|---|
| OCA `base_user_role` มีอยู่บนดิสก์แล้ว | `third_party/oca/server-backend/base_user_role/__manifest__.py` (v19.0.1.3.1, Production/Stable, LGPL-3) | ใช้เป็นฐาน role engine ไม่ต้องเขียนเอง |
| `res.users.role` ใช้ `_inherits = {"res.groups": "group_id"}` | `base_user_role/models/role.py` L12–58 | บทบาท = กลุ่ม (ตั้ง `implied_ids` ได้ตรง) |
| Odoo 19 ใช้ `res.groups.privilege` แทน `category_id` | `odoo/addons/base/models/res_groups.py` | กลุ่มกลางใช้ `privilege_id` |
| Odoo 19 `res.users.employee_id` เป็น non-stored compute | `addons/hr/models/res_users.py` L64–65 | ต้อง mirror ลงฟิลด์ stored ใหม่ |
| `hr.department` core ไม่มี `code` | `addons/hr/models/hr_department.py` | `code` ถูกเพิ่มโดย custom หลายโมดูล |
| กลุ่ม custom ที่ประกาศเองในระบบ (9 กลุ่ม) | grep `<record ... model="res.groups">` ทั่ว `custom_addons/` | ต้องถูกอ้างจาก role catalog |
| ยังไม่มีโมดูลกลางนิยามบทบาทองค์กร | ไม่พบ `od19_security_roles` ใน `custom_addons/` | ช่องว่างที่สเปกนี้ปิด |
| Access readiness ยัง `Not Started` | `docs/superpowers/programs/odoo19-enterprise/discovery/access-readiness-checklist.md` | ปิดช่องว่างก่อน migration |

---

## Delivery Controls

| ข้อบังคับ | ที่มา | สถานะในสเปกนี้ |
|---|---|---|
| ห้ามแก้ไฟล์ Odoo core | engineering-standards | ปฏิบัติ — ทุกอย่างอยู่ใน custom module |
| OCA First / Custom Second | engineering-standards | ใช้ `base_user_role` เป็นฐาน |
| Explicit security model | engineering-standards | ทุกกลุ่ม/บทบาทมี ACL + record rule ระบุชัด |
| Security review ห้าม waive | review-gates.md | ผ่าน Gate 3/4 ก่อนติดตั้ง production |
| ฟิลด์ custom ต้องขึ้นต้น `od19_` | project rule | `od19_department_id`, `od19_department_all` ฯลฯ |

---

## 1. บทสรุป (Summary)

วางโครงสร้างสิทธิ์การเข้าถึงสำหรับ Odoo 19 Greenfield ด้วยโมเดล **สองแกน**:

- **แกนบทบาท (Role / Function)** — "คนนี้ทำงานอะไร" คุมด้วย `res.users.role` (OCA) ซึ่งภายในคือ `res.groups` + `implied_ids`
- **แกนแผนก (Department / Scope)** — "คนนี้เห็นข้อมูลของใคร" คุมด้วย record rule ที่ผูก `department_id` กับ `res.users.od19_department_id`

โดยแยกเป็น **2 โมดูล** เพื่อตัดปัญหา dependency วน:

| Layer | โมดูล | หน้าที่ | depends |
|---|---|---|---|
| 1 | `od19_security_roles` | privilege + ฟิลด์แผนกบน `res.users` + ตัวช่วย record rule + กลุ่ม bypass | `base`, `base_user_role`, `hr` |
| 2 | `od19_role_catalog` | สร้าง `res.users.role` ทั้งหมด (~30 บทบาท) เป็น **data เท่านั้น** + ผูก `implied_ids` กับกลุ่มธุรกิจ | โมดูลธุรกิจทั้งหมด + `od19_security_roles` |
| 3 | โมดูลธุรกิจ 62 ตัว | ACL + department record rule ของตัวเอง (เฟส B) | `od19_security_roles` |

> **หัวใจของการตัดสินใจ:** Layer 1 ไม่รู้จักกลุ่มธุรกิจเลย จึงไม่เกิด dependency วน — เฉพาะ Layer 2 เท่านั้นที่อ้างกลุ่มธุรกิจ (ผ่าน `implied_ids` ของ role)

---

## 2. ปัญหาและความต้องการ (Problem)

### 2.1 สภาพปัจจุบัน

| # | สภาพ | ผลกระทบ |
|---|---|---|
| 1 | 62 โมดูล custom ต่างคนต่างประกาศ `ir.model.access.csv` และ `res.groups` ของตัวเอง | ไม่มีภาพรวมว่า "ใครมีสิทธิ์อะไร" |
| 2 | 9 กลุ่ม custom กระจายอยู่คนละโมดูล ไม่มีลำดับชั้น | มอบสิทธิ์ให้พนักงานต้องติ๊กทีละกลุ่ม |
| 3 | ไม่มีแนวคิด "แผนก" ในระดับสิทธิ์ | ทุกคนที่เข้าถึงโมเดลเห็นข้อมูลทุกแผนก |
| 4 | ไม่มีการแยกหน้าที่ (SoD) เชิงบังคับ | ผู้ขายสามารถอนุมัติเครดิตของตัวเองได้ |
| 5 | `res.users.employee_id` ใน Odoo 19 เป็น non-stored | ใช้ใน record rule ตรง ๆ ไม่ได้ |

### 2.2 ความต้องการ

- **R1** มีประตูเดียว (single entry point) ในการมอบสิทธิ์ให้พนักงาน 1 คน
- **R2** บทบาทต้องสื่อความหมายทางธุรกิจ (เช่น "ผู้จัดการขาย") ไม่ใช่ศัพท์เทคนิค
- **R3** ขอบเขตข้อมูลต้องแยกตามแผนก โดยไม่ทำให้ฝ่ายที่ต้องเห็นภาพรวม (บัญชี/คลัง/ผู้บริหาร) มองไม่เห็น
- **R4** บังคับ Separation of Duties: ผู้ขายห้ามอนุมัติเครดิตของตัวเอง
- **R5** ต้องใช้ OCA เป็นฐาน ไม่เขียน role engine เอง
- **R6** ต้องติดตั้ง/ถอนได้ปลอดภัย ไม่แตะ core

---

## 3. ขอบเขต (Scope)

### 3.1 อยู่ในขอบเขต

| เฟส | เนื้อหา |
|---|---|
| **A** | โมดูล `od19_security_roles` + `od19_role_catalog` + Role Matrix + หน้าจอจัดการ |
| **B** | เพิ่ม/ตรวจ `ir.model.access.csv` และ department record rule ในโมดูลที่มี `department_id` เป็นเจ้าของข้อมูลจริง |
| **C** | เอกสาร Role Matrix สำหรับผูกผู้ใช้ Odoo 15 → บทบาทใหม่ (ทำร่วมกับงาน migration) |
| **D** | ย้ายวงเงินอนุมัติ SO/PO ให้เป็นฟิลด์บน `res.company` (แหล่งความจริงเดียว) |

### 3.2 นอกขอบเขต

- การเขียน role engine ใหม่ (ใช้ OCA `base_user_role`)
- การแก้ไขไฟล์ Odoo core
- การ auto-map กลุ่มจาก Odoo 15 มาเป็นบทบาทใหม่ (ตาม D6 — ใช้ role matrix กำหนดเอง)
- Field-level security (ขึ้นกับ `base_user_role` เป็นหลัก)

---

## 4. หลักการออกแบบ (Design Principles)

1. **OCA First** — `base_user_role` เป็นฐาน; ไม่มี role engine ของตัวเอง
2. **สองแกนแยกกันชัด** — บทบาทคุม "ทำอะไรได้", แผนกคุม "เห็นของใคร"
3. **Layer 1 ไม่รู้จักธุรกิจ** — ตัด dependency วนโดยสิ้นเชิง
4. **Data ไม่ใช่ Code** — บทบาททั้งหมดเป็น `ir.model.data` record ใน `od19_role_catalog` ปรับ/เพิ่มได้โดยไม่แก้ Python
5. **Fail-safe & Reversible** — ถอน `od19_role_catalog` ได้โดยไม่กระทบ Layer 1
6. **ไทยเป็นหลัก** — label ป้ายกำกับสองภาษา (ไทย/อังกฤษ)

---

## 5. สถาปัตยกรรม (Architecture)

```
Layer 2   od19_role_catalog           ~30 res.users.role (data เท่านั้น)
          depends: ทุกโมดูลธุรกิจ + od19_security_roles        ติดตั้ง "ท้ายสุด"

Layer 1   od19_security_roles         privilege + กลุ่มกลาง + res.users.od19_department_id
          depends: base, base_user_role, hr                    ติดตั้ง "ก่อน"

Layer 0   base_user_role (OCA) / hr / base
```

### 5.1 สกัด Cycle

จุดที่เสี่ยงวนคือ: "บทบาทต้องอ้างกลุ่มธุรกิจ" แต่ "โมดูลธุรกิจต้องอ้าง `od19_security_roles` (เพื่อใช้ฟิลด์แผนก)".

วิธีแก้: ให้บทบาททั้งหมดถูกสร้างใน **Layer 2** ซึ่งติดตั้งท้ายสุดและ `depends` โมดูลธุรกิจได้อย่างอิสระ ส่วน Layer 1 มีเพียงกลุ่มกลางที่ไม่ผูกกับธุรกิจ ⇒ ไม่มีทางวน

### 5.2 กลุ่มกลางที่ Layer 1 ให้บริการ

| Group (xml id) | หน้าที่ |
|---|---|
| `group_od19_department_scope` | ทุกบทบาท imply กลุ่มนี้ → ถูกจำกัดขอบเขตด้วยแผนก |
| `group_od19_department_all` | เห็นข้อมูลทุกแผนก (สำหรับ บัญชี/คลัง/ผู้บริหาร/ผู้ดูแลระบบ) — **ไม่** อยู่ใน scope rule |
| `group_od19_role_manager` | จัดการบทบาทและมอบหมายให้ผู้ใช้ได้ |
| `group_od19_credit_approver` | อนุมัติเครดิต (ครอบ Right to Approve ตามนโยบาย "No Credit Approval, No Credit Sale") |

---

## 6. โครงสร้างข้อมูล (Data Model)

### 6.1 `od19_security_roles` (Layer 1)

| โมเดล/ฟิลด์ | ชนิด | หมายเหตุ |
|---|---|---|
| `res.groups.privilege` `od19_role_privilege` | data | "OD19 Roles / บทบาท OD19" จัดกลุ่ม role ทั้งหมด |
| `res.users.od19_department_id` | Many2one `hr.department`, stored, index | mirror ของ `employee_id.department_id` |
| `res.users.od19_department_code` | Char, related | ใช้แสดงผลเร็ว |
| `hr.department.od19_member_user_ids` | One2many | ย้อนกลับจาก `res.users.od19_department_id` |

**กลไก mirror แผนก (D3):**

```
1. `res.users.create/write` → ถ้ามี `employee_id` → ตั้ง `od19_department_id = employee_id.department_id`
2. `hr.employee.write({"department_id": x})` → อัปเดตผู้ใช้ที่ผูกอยู่ (user_id) ให้ตรงกัน
3. cron รายวัน (ir.cron) กวาดปรับให้ตรงกันเป็นครั้งคราว (กันข้อมูลตกหล่นจาก import)
```

> ใช้ `hr.employee` เป็นแหล่งความจริง ⇒ แก้ที่แผนกของพนักงานคือจุดเดียว

### 6.2 `od19_role_catalog` (Layer 2)

สร้าง `res.users.role` ล้วน ๆ (ไม่มี Python model ใหม่) โดยแต่ละ record ระบุ:

| ฟิลด์ role | ค่า |
|---|---|
| `name` | ชื่อบทบาท เช่น "ผู้จัดการขาย" |
| `group_id/implied_ids` | กลุ่มธุรกิจที่บทบาทนี้ให้ |
| `group_privilege_id` | `od19_security_roles.od19_role_privilege` |
| `sequence` | ลำดับการแสดง |
| `is_default` | มอบอัตโนมัติให้ผู้ใช้ใหม่ (เฉพาะบทบาทพื้นฐาน) |

---

## 7. Role Matrix (ฉบับร่าง — รอผู้ใช้ตรวจ)

สัญลักษณ์: ✅ = ให้สิทธิ์, 🔺 = จุดควบคุม Separation of Duties, ⬛ = ได้ `group_od19_department_all`

### A. Governance / IT

| Role (ไทย) | xml id | กลุ่มที่ให้ | หมายเหตุ |
|---|---|---|---|
| ผู้จัดการระบบ | `role_system_manager` | `base.group_system`, `base.group_erp_manager`, `group_od19_department_all` | ⬛ |
| ผู้ดูแลสิทธิ์การเข้าถึง | `role_access_administrator` | `group_od19_role_manager`, `base.group_user` | จัดการบทบาท/ผู้ใช้ แต่ไม่ใช่ตั้งค่าระบบทั้งหมด |
| ผู้ดูแลการเชื่อมต่อ | `role_integration_manager` | `od19_currency_rate_bot.group_currency_rate_bar_viewer`, ZKTeco menu group | ดูแล bot/อุปกรณ์ |

### B. Sales

| Role | xml id | กลุ่มที่ให้ | หมายเหตุ |
|---|---|---|---|
| พนักงานขาย | `role_sales_user` | `sales_team.group_sale_salesman` | |
| ผู้จัดการขาย | `role_sales_manager` | `sales_team.group_sale_manager` | |
| ผู้อำนวยการขาย | `role_sales_director` | `od19_sales_oca_bridge_workflow.group_sale_director`, `sales_team.group_sale_manager` | อนุมัติ SO ≥ วงเงิน Director |
| **ผู้ตรวจสอบเครดิต** | `role_credit_reviewer` | `od19_sales_customer_risk_gate.group_od19_credit_reviewer`, `group_od19_credit_approver` | 🔺 **ห้ามให้ role นี้กับผู้ขาย** |
| เจ้าหน้าที่โครงการขาย | `role_sales_project_officer` | `project.group_project_user` + sales user | |

### C. Purchase

| Role | xml id | กลุ่มที่ให้ | หมายเหตุ |
|---|---|---|---|
| เจ้าหน้าที่จัดซื้อ | `role_purchase_user` | `purchase.group_purchase_user` | |
| ผู้จัดการจัดซื้อ | `role_purchase_manager` | `purchase.group_purchase_manager` | อนุมัติ PO < วงเงิน Director |
| ผู้อำนวยการจัดซื้อ | `role_purchase_director` | `od19_purchase_procurement_core.group_purchase_director` | อนุมัติ PO ≥ วงเงิน Director |

### D. Inventory & Logistics

| Role | xml id | กลุ่มที่ให้ | หมายเหตุ |
|---|---|---|---|
| เจ้าหน้าที่คลัง | `role_warehouse_user` | `stock.group_stock_user` | |
| ผู้จัดการคลัง | `role_warehouse_manager` | `stock.group_stock_manager`, `group_od19_department_all` | ⬛ |
| เจ้าหน้าที่เบิกจ่ายสินค้า | `role_goods_issue_operator` | `od19_goods_issue` menu group | ขอบเขตตามแผนก |
| เจ้าหน้าที่ขนส่ง | `role_transportation_officer` | `od19_transportation` menu group | |
| ผู้ตรวจสอบสต็อก | `role_inventory_counter` | `od19_inventory_audit_count` menu group | |

### E. Accounting & Finance

| Role | xml id | กลุ่มที่ให้ | หมายเหตุ |
|---|---|---|---|
| นักบัญชี | `role_accountant` | `account.group_account_user`, `group_od19_department_all` | ⬛ |
| ผู้จัดการการเงิน | `role_finance_manager` | `account.group_account_manager`, `group_od19_department_all`, `group_od19_credit_approver` | ⬛ ดู §7.1 |
| แคชเชียร์ / เงินสดย่อย | `role_cashier` | `od19_accounting_petty_cash` menu group, `account.group_account_user` | |
| เจ้าหน้าที่เช็ค | `role_cheque_officer` | `od19_accounting_cheque` menu group, `account.group_account_user` | |
| เจ้าหน้าที่ภาษีหัก ณ ที่จ่าย | `role_wht_officer` | `od19_thai_tax_reports` menu group, `account.group_account_user` | |

> **§7.1 SoD บัญชี:** `role_finance_manager` ได้ `group_od19_credit_approver` (อนุมัติวงเงินเครดิต) — **ห้าม** มอบพร้อม `role_sales_user`/`role_sales_manager` ให้บุคคลเดียวกัน

### F. After-Sales / Service

| Role | xml id | กลุ่มที่ให้ | หมายเหตุ |
|---|---|---|---|
| ที่ปรึกษาบริการ | `role_service_advisor` | `od19_helpdesk_extension.group_sales_service` | |
| ผู้ตรวจสอบคุณภาพ (QC) | `role_qc_inspector` | `od19_quality_control` menu group | |
| ผู้ลงนามเอกสาร | `role_document_signer` | `od19_document_sign.group_od19_document_sign_user` | |
| ผู้จัดการลงนามเอกสาร | `role_document_signer_manager` | `od19_document_sign.group_od19_document_sign_manager` | |
| ผู้จัดการสัญญาบริการ | `role_service_manager` | `od19_service_card`/`od19_service_warranty` menu group | |

### G. Human Resources

| Role | xml id | กลุ่มที่ให้ | หมายเหตุ |
|---|---|---|---|
| เจ้าหน้าที่บุคคล | `role_hr_user` | `hr.group_hr_user` | |
| ผู้จัดการบุคคล | `role_hr_manager` | `hr.group_hr_manager`, `group_od19_department_all` | ⬛ |
| ผู้ดูแลยานพาหนะ | `role_fleet_manager` | `fleet.fleet_group_manager` | |
| ผู้ดูแลห้องประชุม | `role_meeting_room_manager` | `od19_meeting_room_booking.group_meeting_room_manager` | |

### H. ISO / Quality / Risk

| Role | xml id | กลุ่มที่ให้ | หมายเหตุ |
|---|---|---|---|
| ผู้ควบคุมเอกสาร ISO | `role_document_controller` | ISO document control menu group | |
| ผู้ตรวจประเมินภายใน | `role_internal_auditor` | `od19_iso_internal_audit` menu group | |
| ผู้รับผิดชอบความเสี่ยง | `role_risk_owner` | `od19_iso_risk` menu group | |
| กรรมการทบทวนฝ่ายบริหาร | `role_management_review_member` | `od19_iso_management_review` menu group | |
| ผู้ดูแลคุณภาพผู้ขาย | `role_supplier_quality_officer` | `od19_iso_supplier_quality` menu group | |

### I. Reporting & Dashboard

| Role | xml id | กลุ่มที่ให้ | หมายเหตุ |
|---|---|---|---|
| ผู้ใช้แดชบอร์ด | `role_dashboard_user` | `od19_dashboard.group_od19_dashboard_user` | |
| ผู้จัดการแดชบอร์ด | `role_dashboard_manager` | `od19_dashboard.group_od19_dashboard_manager` | |
| ผู้ดูรายงาน (Jasper) | `role_reporting_viewer` | `od19_reporting_jasper` menu group | |
| นักวิเคราะห์รายงาน | `role_reporting_analyst` | `group_od19_department_all` + reporting viewer | ⬛ |

### J. Support & Collaboration (บทบาทพื้นฐาน)

| Role | xml id | กลุ่มที่ให้ | หมายเหตุ |
|---|---|---|---|
| พนักงานทั่วไป | `role_employee_base` | `base.group_user`, `group_od19_department_scope` | `is_default = True` |
| ผู้ใช้ห้องประชุม | `role_meeting_room_user` | `od19_meeting_room_booking.group_meeting_room_user` | |
| ผู้ใช้ Helpdesk ภายใน | `role_helpdesk_internal` | `od19_helpdesk_extension.group_internal_helpdesk` | |
| ผู้ใช้ Knowledge | `role_knowledge_user` | `od19_knowledge_enhanced` menu group | |

**รวม ≈ 40 บทบาท ใน 10 ครอบครัว**

---

## 8. Record Rules (ขอบเขตแผนก)

### 8.1 รูปแบบมาตรฐาน (D9 — แผนกของตัวเอง)

```xml
<record id="rule_<model>_od19_department" model="ir.rule">
    <field name="name">&lt;Model&gt;: เฉพาะแผนกของตัวเอง / Own Department</field>
    <field name="model_id" ref="model_<model>"/>
    <field name="domain_force">
        ['|', ('department_id', '=', user.od19_department_id.id), ('department_id', '=', False)]
    </field>
    <field name="groups" eval="[(4, ref('od19_security_roles.group_od19_department_scope'))]"/>
    <field name="perm_read" eval="True"/>
    <field name="perm_write" eval="True"/>
    <field name="perm_create" eval="False"/>
    <field name="perm_unlink" eval="True"/>
</record>
```

**กติกา:**
- เอกสารที่ `department_id = False` (ยังไม่ระบุแผนก) → ทุกคนเห็น (Fail-safe, ไม่ทำให้ข้อมูลหาย)
- ผู้ที่อยู่ `group_od19_department_all` ไม่ถูกจำกัด → แต่ละโมดูลจึงมี **all rule** คู่กันเสมอ:

```xml
<record id="rule_<model>_od19_department_all" model="ir.rule">
    <field name="name">&lt;Model&gt;: ทุกแผนก / All Departments</field>
    <field name="model_id" ref="model_<model>"/>
    <field name="domain_force">[(1, '=', 1)]</field>
    <field name="groups" eval="[(4, ref('od19_security_roles.group_od19_department_all'))]"/>
</record>
```

> **ทำไมต้องมี all rule แยก:** `role_employee_base` เป็น `is_default=True` และ imply
> `group_od19_department_scope` → ผู้ใช้ใหม่ทุกคนติด scope group แม้จะได้บทบาทที่ imply
> `group_od19_department_all` (บัญชี/คลัง/บริหาร) มาด้วย เนื่องจากกฎระดับกลุ่มถูก **OR** กัน
> all rule จึงทำให้กลุ่ม `group_od19_department_all` ชนะ scope rule เสมอ

### 8.2 โมเดลเป้าหมายในเฟส B

| โมดูล | โมเดล | ฟิลด์แผนก |
|---|---|---|
| `od19_goods_issue` | `stock.request.order` | `department_id` |
| `od19_project_analytic` | `project.project` | `od19_department_id` |
| `od19_iso_document_control` | `od19.iso.document` | `department_id` |
| `od19_iso_nonconformity` | `od19.iso.nonconformity` | `department_id` |
| `od19_iso_risk` | `od19.risk` | `department_id` |
| `od19_iso_training` | `od19.training` | `department_id` |
| `od19_iso_calibration` | `od19.calibration` | `department_id` |
| `od19_iso_internal_audit` | `od19.audit` | `auditee_department_id` |
| `od19_internal_issue` | `helpdesk.ticket` | `department_id` |
| `od19_announcement` | `od19.announcement` | `department_id` |
| `od19_fleet_accounting` | `fleet.vehicle` | `department_id` |

### 8.3 โมเดลที่ **ไม่** ใส่ department rule (และเหตุผล)

| โมเดล | เหตุผล |
|---|---|
| `sale.order` | `department_id` ใช้ "รันเลขเอกสาร" ผู้ใช้แก้ได้ → บายพาสกฎ; คลัง/บัญชี/บริการต้องเห็นทุกแผนก |
| `purchase.order` | เหตุผลเดียวกับ `sale.order` |
| `account.move` | ไม่มีฟิลด์แผนก (core) การเพิ่มคือแก้ schema ที่มี 24+ โมดูล inherit |
| `stock.picking` | มีเพียง `od19_goods_issue_department_id` เฉพาะ flow ใบเบิก → ใช้กับ `stock.request.order` แทน |
| `hr.expense` | แผนกมาจากพนักงานเจ้าของใบ → ใช้กลุ่ม HR/บัญชีเป็นตัวคุมแทน |

### 8.4 Separation of Duties (บังคับเชิงข้อมูล)

| กติกา | กลไก |
|---|---|
| ผู้ขายห้ามอนุมัติเครดิตของตัวเอง | `role_sales_*` ไม่ imply `group_od19_credit_approver`; ตรวจเพิ่มใน `od19_sales_customer_risk_gate` ว่าผู้อนุมัติต้องไม่ใช่ `user_id` ของ SO |
| บัญชีเท่านั้นที่อนุมัติวงเงิน | `group_od19_credit_approver` ให้เฉพาะ `role_credit_reviewer` และ `role_finance_manager` |
| ห้ามตั้งหนี้ก่อนจ่ายถูกข้าม | ตรวจใน `od19_accounting_features` (ดำเนินการแล้ว) → role ไม่ให้สิทธิ์บายพาส |

---

## 9. ส่วนติดต่อผู้ใช้ (UI)

| หน้าจอ | เนื้อหา |
|---|---|
| **Settings → Users → Roles** | ใช้ view ของ `base_user_role` โดยเพิ่มกลุ่ม privilege "OD19 Roles / บทบาท OD19" |
| **หน้าผู้ใช้ (tab Roles)** | เพิ่มแสดงบทบาท + แสดง "แผนก" (`od19_department_id`) แบบอ่านอย่างเดียว (mirror จากพนักงาน) |
| **รายงาน Role Matrix** | `ir.actions.act_window` บน `res.users.role` แบบ list + group by privilege |
| **เมนู** | Settings → Users & Companies → **Roles / บทบาท** (เพิ่มจาก OCA ให้เข้าถึงง่ายขึ้น) |

---

## 10. ลำดับการทำงาน (Data Flow)

### 10.1 ติดตั้งครั้งแรก

```
1. ติดตั้ง base_user_role (OCA)
2. ติดตั้ง od19_security_roles  → privilege + กลุ่มกลาง + ฟิลด์แผนก + cron mirror
3. ติดตั้งโมดูลธุรกิจทั้งหมด (มี depends od19_security_roles) → ir.rule แผนกของตัวเอง
4. ติดตั้ง od19_role_catalog    → สร้าง ~40 res.users.role
```

### 10.2 มอบสิทธิ์ให้พนักงาน 1 คน

```
ตั้ง hr.employee.department_id  →  cron/create hook mirror ลง res.users.od19_department_id
→ ที่หน้าผู้ใช้ เลือก role (เช่น ผู้จัดการขาย + ผู้ใช้แดชบอร์ด)
→ base_user_role.update_users()  →  groups = union(implied_ids ของทุก role)
```

### 10.3 แก้ไขสิทธิ์ของ role

```
แก้ implied_ids ที่ role  →  cron batch 2000 ของ base_user_role อัปเดตผู้ใช้ตามคาบ
```

---

## 11. กติกาและการป้องกัน (Guards / Edge Cases)

| กรณี | การจัดการ |
|---|---|
| ผู้ใช้ไม่มี `employee_id` | `od19_department_id = False` → ไม่ถูกจำกัดด้วย scope rule (fail-safe) |
| พนักงานย้ายแผนก | `hr.employee.write` → mirror ไปยัง user ทันที + บันทึกใน log |
| ผู้ใช้ผูกพนักงานหลายบริษัท | ใช้ `employee_id` ของบริษัทปัจจุบัน (`env.company`) |
| บทบาทถูกถอน | `base_user_role` recalculation จะถอน implied groups ให้เอง |
| ติดตั้ง `od19_role_catalog` แล้วมี role ชื่อซ้ำของเดิม | ใช้ `noupdate="1"` + xml id เฉพาะ ป้องกันชน |
| `privilege_id` ซ้ำ (Odoo 19 unique ต่อ privilege+name) | ตั้งชื่อ role ไม่ซ้ำใน privilege เดียวกัน |
| ถอน `od19_role_catalog` | role records ถูกลบ; ผู้ใช้ยังคงมีกลุ่มเดิม (ยอมรับได้) |
| ให้ `role_finance_manager` + `role_sales_user` คนเดียวกัน | แจ้งเตือน (constraint บน `res.users`) ตาม SoD |

---

## 12. แผนการทดสอบ (Testing)

### 12.1 Unit / Integration test (`od19_security_roles/tests`)

| ไฟล์ | ครอบคลุม |
|---|---|
| `test_roles_install.py` | ติดตั้งแล้วมี privilege + กลุ่มกลางครบ 4 กลุ่ม |
| `test_department_sync.py` | create/write user + write employee → mirror ถูกต้อง; cron sweep |
| `test_department_scope.py` | ผู้ใช้แผนก A เห็นเฉพาะเอกสาร A + เอกสาร `department_id=False`; ผู้มี `group_od19_department_all` เห็นทั้งหมด |
| `test_role_assignment.py` | มอบ role → implied groups ถูกเพิ่ม; ถอน role → ถูกลบ |

### 12.2 เกณฑ์ผ่าน

- เทสต์ผ่านทั้งหมดบน `odoo19_pdev`
- ไม่มี warning ใน log ตอน upgrade
- ติดตั้ง/ถอน `od19_role_catalog` ซ้ำได้โดยไม่ error
- Role Matrix ครอบคลุมกลุ่ม custom ทั้ง 9 กลุ่มในระบบ

---

## 13. การแบ่งเฟส (Phasing)

| เฟส | เนื้อหา | ผลลัพธ์ |
|---|---|---|
| **A** | `od19_security_roles` + `od19_role_catalog` + Role Matrix + เทสต์ | มอบสิทธิ์เป็นบทบาทได้ + mirror แผนก |
| **B** | department record rule ใน 11 โมเดล (§8.2) | แยกขอบเขตข้อมูลตามแผนก |
| **C** | เอกสาร Role Matrix สำหรับ migration + ผูกผู้ใช้ Odoo 15 | รู้ว่าใครได้บทบาทอะไร |
| **D** | วงเงินอนุมัติ SO/PO บน `res.company` | ตั้งวงเงินได้ที่เดียว |

---

## 14. การตัดสินใจที่ยืนยันแล้ว (Resolved Decisions)

- **D1** เฟส A → B → C (และ D เสริม) — Approval Traceability
- **D2** บทบาท = หน้าที่งาน; แผนก = record rule
- **D3** `hr.employee.department_id` เป็นแหล่งความจริง แล้ว mirror ลง `res.users`
- **D4** ร่าง Role Matrix ~40 บทบาทใน §7 ให้ผู้ใช้ตรวจ
- **D5** record rule เฉพาะ 11 โมเดลใน §8.2; ไม่แตะ SO/PO/Invoice/Picking (§8.3)
- **D6** ไม่ auto-map กลุ่มจาก Odoo 15 — ใช้ role matrix
- **D7** แยก 2 โมดูลตาม Layer
- **D8** วงเงินอนุมัติย้ายไป `res.company`
- **D9** ขอบเขตแผนก = แผนกของตัวเอง (ไม่รวมแผนกลูก)

---

## 15. ความเสี่ยง (Risks)

| ความเสี่ยง | ระดับ | การบรรเทา |
|---|---|---|
| บทบาท ~40 รายการสับสนสำหรับผู้ใช้ | กลาง | จัดกลุ่มด้วย `privilege` + เรียง sequence ตามครอบครัว + คู่มือสั้น |
| ติดตั้ง `od19_role_catalog` แล้วผู้ใช้มีกลุ่มไม่ครบ | สูง | เทสต์ตรวจว่า role ทุกตัวโหลดได้ + ตรวจ implied group ตรงตาม matrix |
| dependency วนระหว่าง Layer | สูง | Layer 1 ไม่ import/อ้างกลุ่มธุรกิจใด ๆ (ตรวจในเทสต์) |
| record rule ทำให้ผู้ใช้มองไม่เห็นงานที่ต้องทำ | สูง | Fail-safe ที่ `department_id = False` + มอบ `group_od19_department_all` ให้ฝ่ายที่ต้องเห็นภาพรวม |
| SoD ถูกละเมิดตอนผูกผู้ใช้จริง | สูง | constraint เตือน + ตรวจในเฟส C ทีละคน |
| ชื่อ role ซ้ำกับ `res.groups` เดิม → unique constraint | กลาง | ตั้งชื่อ role ให้ไม่ซ้ำใน privilege เดียวกัน |
