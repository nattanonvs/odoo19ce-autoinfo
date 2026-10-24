# Role Matrix — พนักงาน ↔ บทบาท (Odoo 15 → Odoo 19)

## Document Metadata

| Field | Value |
| --- | --- |
| Program | Odoo 19 CE Enterprise |
| Artifact path | `docs/superpowers/programs/odoo19-enterprise/discovery/role-matrix.md` |
| Artifact owner | Access-control owner (บัญชี/ผู้ดูแลสิทธิ์การเข้าถึง) |
| Artifact status | Draft รอผู้ใช้ตรวจและกรอกชื่อพนักงาน |
| Source of truth | `od19_role_catalog/data/od19_roles_*.xml` (43 บทบาท) |
| Related spec | `docs/superpowers/specs/2026-10-23-od19-access-control-and-roles-design.md` §7–§8 |
| Last updated | 2026-10-24 |

## 1. วัตถุประสงค์และวิธีใช้

เอกสารนี้เป็น **ใบงานสำหรับ migration** ใช้ผูกพนักงานจริงเข้า "บทบาท" (role) ของ Odoo 19
ตามแผนงานเฟส C งานนี้ **ไม่ auto-map** กลุ่มจาก Odoo 15 (ตามการตัดสินใจ D6) แต่ให้ผู้ใช้
กำหนดบทบาทด้วย Role Matrix นี้เป็นรายบุคคล

วิธีใช้:

1. ตรวจ "ทะเบียนบทบาท" (§3) ว่าครบและสื่อความหมายถูกต้อง แล้วอนุมัติ
2. กรอก "ใบงานผูกพนักงาน" (§4) — พนักงาน 1 คนมีได้หลายบทบาท (เพิ่มได้ตามหน้าที่งาน)
3. กรอก "ทะเบียนผู้เห็นทุกแผนก" (§5) — เฉพาะผู้ที่ต้องได้ `group_od19_department_all`
4. ตรวจ "ข้อควรระวัง SoD" (§6) และ "ผลข้างเคียงของ `base.group_system`" (§7) ก่อนอนุมัติ

> หลักการ 2 แกนแยกกัน: **บทบาท** คุมว่า "ทำอะไรได้" (function) — **แผนก** คุมว่า "เห็นของใคร" (scope)
> พนักงานทั่วไปจะติด `group_od19_department_scope` อัตโนมัติผ่าน `role_employee_base`

## 2. สัญลักษณ์

- `⬛` = บทบาทนี้ได้ `group_od19_department_all` → เห็นข้อมูลทุกแผนก
- `(⬛)` = ได้ `group_od19_department_all` **โดยอ้อม** (ผ่าน `base.group_system` ซึ่ง imply ไว้ — ดู §7)
- `🔺` = จุดควบคุม Separation of Duties (SoD) — ห้ามมอบรวมกับบทบาทที่ระบุใน §6
- `—` = ถูกจำกัดด้วยแผนกของตัวเอง (scope ปกติ)

## 3. ทะเบียนบทบาททั้งหมด (43 บทบาท / 10 ครอบครัว)

กลุ่มอ้างอิงกลางของ Layer 1 (`od19_security_roles`):

| กลุ่ม | ความหมาย |
| --- | --- |
| `group_od19_department_scope` | ถูกจำกัดการมองเห็นตามแผนกของตัวเอง (fail-safe: เอกสารที่ไม่ระบุแผนกเห็นได้) |
| `group_od19_department_all` | เห็นข้อมูลทุกแผนก ไม่ถูกจำกัดด้วย scope rule |
| `group_od19_role_manager` | จัดการบทบาทและมอบหมายบทบาทให้ผู้ใช้ |
| `group_od19_credit_approver` | อนุมัติวงเงินเครดิตลูกค้า (Right to Approve) |

### A. Governance / IT

| บทบาท | xml id | กลุ่มที่ให้ (implied) | แผนก | SoD |
| --- | --- | --- | --- | --- |
| ผู้จัดการระบบ | `role_system_manager` | `base.group_system`, `base.group_erp_manager`, `group_od19_department_all` | ⬛ | |
| ผู้ดูแลสิทธิ์การเข้าถึง | `role_access_administrator` | `group_od19_role_manager`, `base.group_user` | — | |
| ผู้ดูแลการเชื่อมต่อ | `role_integration_manager` | `od19_currency_rate_bot.group_currency_rate_bar_viewer` | — | |

### B. Sales

| บทบาท | xml id | กลุ่มที่ให้ (implied) | แผนก | SoD |
| --- | --- | --- | --- | --- |
| พนักงานขาย | `role_sales_user` | `sales_team.group_sale_salesman` | — | 🔺 |
| ผู้จัดการขาย | `role_sales_manager` | `sales_team.group_sale_manager` | — | 🔺 |
| ผู้อำนวยการขาย | `role_sales_director` | `od19_sales_oca_bridge_workflow.group_sale_director`, `sales_team.group_sale_manager` | — | 🔺 |
| ผู้ตรวจสอบเครดิต | `role_credit_reviewer` | `od19_sales_customer_risk_gate.group_od19_credit_reviewer`, `group_od19_credit_approver` | — | 🔺 **ห้ามให้กับพนักงานขาย** |
| เจ้าหน้าที่โครงการขาย | `role_sales_project_officer` | `project.group_project_user`, `sales_team.group_sale_salesman` | — | |

### C. Purchase

| บทบาท | xml id | กลุ่มที่ให้ (implied) | แผนก | SoD |
| --- | --- | --- | --- | --- |
| เจ้าหน้าที่จัดซื้อ | `role_purchase_user` | `purchase.group_purchase_user` | — | |
| ผู้จัดการจัดซื้อ | `role_purchase_manager` | `purchase.group_purchase_manager` | — | |
| ผู้อำนวยการจัดซื้อ | `role_purchase_director` | `od19_purchase_procurement_core.group_purchase_director` | — | |

### D. Inventory & Logistics

| บทบาท | xml id | กลุ่มที่ให้ (implied) | แผนก | SoD |
| --- | --- | --- | --- | --- |
| เจ้าหน้าที่คลัง | `role_warehouse_user` | `stock.group_stock_user` | — | |
| ผู้จัดการคลัง | `role_warehouse_manager` | `stock.group_stock_manager`, `group_od19_department_all` | ⬛ | |
| เจ้าหน้าที่เบิกจ่ายสินค้า | `role_goods_issue_operator` | `stock_request.group_stock_request_user` | — | |
| เจ้าหน้าที่ขนส่ง | `role_transportation_officer` | `stock.group_stock_user` | — | |
| ผู้ตรวจสอบสต็อก | `role_inventory_counter` | `stock.group_stock_user` | — | |

### E. Accounting & Finance

| บทบาท | xml id | กลุ่มที่ให้ (implied) | แผนก | SoD |
| --- | --- | --- | --- | --- |
| นักบัญชี | `role_accountant` | `account.group_account_user`, `group_od19_department_all` | ⬛ | |
| ผู้จัดการการเงิน | `role_finance_manager` | `account.group_account_manager`, `group_od19_department_all`, `group_od19_credit_approver` | ⬛ | 🔺 **ห้ามมอบพร้อมบทบาทขาย** |
| แคชเชียร์ / เงินสดย่อย | `role_cashier` | `account.group_account_invoice`, `account.group_account_user` | — | |
| เจ้าหน้าที่เช็ค | `role_cheque_officer` | `account.group_account_invoice`, `account.group_account_user` | — | |
| เจ้าหน้าที่ภาษีหัก ณ ที่จ่าย | `role_wht_officer` | `base.group_user`, `account.group_account_user` | — | |

### F. After-Sales / Service

| บทบาท | xml id | กลุ่มที่ให้ (implied) | แผนก | SoD |
| --- | --- | --- | --- | --- |
| ที่ปรึกษาบริการ | `role_service_advisor` | `od19_helpdesk_extension.group_sales_service` | — | |
| ผู้ตรวจสอบคุณภาพ (QC) | `role_qc_inspector` | `base.group_user` | — | |
| ผู้ลงนามเอกสาร | `role_document_signer` | `od19_document_sign.group_od19_document_sign_user` | — | |
| ผู้จัดการลงนามเอกสาร | `role_document_signer_manager` | `od19_document_sign.group_od19_document_sign_manager` | — | |
| ผู้จัดการสัญญาบริการ | `role_service_manager` | `base.group_user`, `account.group_account_manager` | — | |

### G. Human Resources

| บทบาท | xml id | กลุ่มที่ให้ (implied) | แผนก | SoD |
| --- | --- | --- | --- | --- |
| เจ้าหน้าที่บุคคล | `role_hr_user` | `hr.group_hr_user` | — | |
| ผู้จัดการบุคคล | `role_hr_manager` | `hr.group_hr_manager`, `group_od19_department_all` | ⬛ | |
| ผู้ดูแลยานพาหนะ | `role_fleet_manager` | `fleet.fleet_group_manager` | — | |
| ผู้ดูแลห้องประชุม | `role_meeting_room_manager` | `od19_meeting_room_booking.group_meeting_room_manager` | — | |

### H. ISO / Quality / Risk

> บทบาทกลุ่มนี้ imply `base.group_system` (ตาม ACL จริงของโมดูล ISO) จึงได้
> `group_od19_department_all` **โดยอ้อม** → เห็นทุกแผนก (ดู §7)

| บทบาท | xml id | กลุ่มที่ให้ (implied) | แผนก | SoD |
| --- | --- | --- | --- | --- |
| ผู้ควบคุมเอกสาร ISO | `role_document_controller` | `base.group_user`, `base.group_system` | (⬛) | |
| ผู้ตรวจประเมินภายใน | `role_internal_auditor` | `base.group_user`, `base.group_system` | (⬛) | |
| ผู้รับผิดชอบความเสี่ยง | `role_risk_owner` | `base.group_user`, `base.group_system` | (⬛) | |
| กรรมการทบทวนฝ่ายบริหาร | `role_management_review_member` | `base.group_user`, `base.group_system` | (⬛) | |
| ผู้ดูแลคุณภาพผู้ขาย | `role_supplier_quality_officer` | `base.group_user`, `base.group_system` | (⬛) | |

### I. Reporting & Dashboard

| บทบาท | xml id | กลุ่มที่ให้ (implied) | แผนก | SoD |
| --- | --- | --- | --- | --- |
| ผู้ใช้แดชบอร์ด | `role_dashboard_user` | `od19_dashboard.group_od19_dashboard_user` | — | |
| ผู้จัดการแดชบอร์ด | `role_dashboard_manager` | `od19_dashboard.group_od19_dashboard_manager` | — | |
| ผู้ดูรายงาน (Jasper) | `role_reporting_viewer` | `account.group_account_invoice` | — | |
| นักวิเคราะห์รายงาน | `role_reporting_analyst` | `group_od19_department_all`, `account.group_account_invoice` | ⬛ | |

### J. Support & Collaboration (บทบาทพื้นฐาน)

| บทบาท | xml id | กลุ่มที่ให้ (implied) | แผนก | SoD |
| --- | --- | --- | --- | --- |
| พนักงานทั่วไป | `role_employee_base` | `base.group_user`, `group_od19_department_scope` | — | `is_default = True` |
| ผู้ใช้ห้องประชุม | `role_meeting_room_user` | `od19_meeting_room_booking.group_meeting_room_user` | — | |
| ผู้ใช้ Helpdesk ภายใน | `role_helpdesk_internal` | `od19_helpdesk_extension.group_internal_helpdesk` | — | |
| ผู้ใช้ Knowledge | `role_knowledge_user` | `base.group_user`, `document_knowledge.group_document_user` | — | |

**รวม 43 บทบาท ใน 10 ครอบครัว**

## 4. ใบงาน: ผูกพนักงาน ↔ บทบาท

> กรอกชื่อพนักงานจริง 1 แถวต่อ 1 บทบาท (พนักงานคนเดียวมีหลายแถวได้)
> `บทบาท (xml id)` ต้องตรงกับ §3 — ใช้ชื่อ xml id เพื่อลดความกำกวม

| # | ชื่อ-นามสกุล | แผนก (`od19_department_id`) | บทบาท (xml id) | อีเมล | กลุ่ม Odoo 15 เดิม (อ้างอิง) | ผู้ตรวจ/วันที่ |
| --- | --- | --- | --- | --- | --- | --- |
| 1 |  |  |  |  |  |  |
| 2 |  |  |  |  |  |  |
| 3 |  |  |  |  |  |  |
| 4 |  |  |  |  |  |  |
| 5 |  |  |  |  |  |  |

## 5. ทะเบียนผู้เห็นทุกแผนก (`group_od19_department_all`) — Task C2

### 5.1 เกณฑ์การคัดเลือก

ผู้ใช้ที่จะได้ `group_od19_department_all` มี 2 ทาง:

| ทาง | แหล่งที่มา | ได้กลุ่ม |
| --- | --- | --- |
| **ทางตรง (role ⬛)** | บทบาทที่ imply `group_od19_department_all` | `role_system_manager`, `role_warehouse_manager`, `role_accountant`, `role_finance_manager`, `role_hr_manager`, `role_reporting_analyst` |
| **ทางอ้อม (`base.group_system`)** | บทบาทที่ imply `base.group_system` (กลุ่ม ISO ทั้ง 5) + ผู้ใช้ที่ตั้ง `base.group_system` เอง | `role_document_controller`, `role_internal_auditor`, `role_risk_owner`, `role_management_review_member`, `role_supplier_quality_officer` |

หลักการ: ให้เฉพาะ **บัญชี / คลัง / ผู้บริหาร / ผู้ดูแลระบบ / ผู้ตรวจสอบภายใน** ที่จำเป็นต้องเห็นข้อมูล
ข้ามแผนกจริง ๆ — พนักงานปฏิบัติงานทั่วไปต้อง **ไม่** ได้กลุ่มนี้ เพื่อให้ scope rule ทำงาน

### 5.2 ตารางลงทะเบียน

| # | ชื่อ-นามสกุล | บทบาทที่ได้ | เหตุผลที่ต้องเห็นทุกแผนก | ทางที่ได้ | ผู้อนุมัติ/วันที่ |
| --- | --- | --- | --- | --- | --- |
| 1 |  |  |  |  |  |
| 2 |  |  |  |  |  |
| 3 |  |  |  |  |  |

## 6. Separation of Duties (บังคับ)

| กติกา | บทบาท A | ห้ามมอบพร้อม | เหตุผล |
| --- | --- | --- | --- |
| SoD-1 เครดิต | `role_credit_reviewer` | `role_sales_user`, `role_sales_manager`, `role_sales_director`, `role_sales_project_officer` | ฝ่ายขายห้ามอนุมัติวงเงินเครดิตเอง |
| SoD-2 เครดิต | `role_finance_manager` (ได้ `group_od19_credit_approver`) | บทบาทขายใด ๆ ข้างต้น | "ไม่มีการอนุมัติเครดิต ไม่มีการขาย" |

> การตรวจอัตโนมัติมีใน `od19_role_catalog/tests/test_role_catalog.py` (`test_no_sales_credit_overlap`)

## 7. ข้อควรระวัง: `base.group_system` imply `group_od19_department_all`

ใน `od19_security_roles/security/od19_security_groups.xml` กลุ่ม `base.group_system`
ถูกกำหนดให้ imply ทั้ง `group_od19_role_manager` และ `group_od19_department_all`

ผลที่ตามมา (ต้องรับทราบก่อนอนุมัติ):

- บทบาท ISO ทั้ง 5 (กลุ่ม H) imply `base.group_system` → **เห็นทุกแผนกโดยอัตโนมัติ**
  จึงไม่ถูกจำกัดด้วย department scope
- บทบาท `role_system_manager` และ `role_access_administrator` ที่ imply `base.group_system`/`group_od19_role_manager`
  ก็ได้ `group_od19_department_all` ด้วยเช่นกัน
- งานเฟส B เพิ่ม **all rule** `[(1, '=', 1)]` ให้ทุกโมเดลที่มี department rule เพื่อให้ผู้ที่ได้
  `group_od19_department_all` ชนะ scope rule ได้จริง (กฎระดับกลุ่มถูก OR กัน)

ถ้าธุรกิจต้องการให้บทบาท ISO ถูกจำกัดตามแผนก จะต้องทบทวน ACL ของโมดูล ISO
(ปัจจุบันให้สิทธิ์ระดับผู้จัดการแก่ `base.group_system`) — **นอกขอบเขต** ของงานชุดนี้

## 8. References

- Spec: `docs/superpowers/specs/2026-10-23-od19-access-control-and-roles-design.md` (§7 Role Matrix, §8 Record Rules)
- Plan: `docs/superpowers/plans/2026-10-23-od19-access-control-and-roles-implementation-plan.md` (เฟส C)
- Role data: `custom_addons/od19_role_catalog/data/od19_roles_governance.xml`, `od19_roles_operations.xml`, `od19_roles_backoffice.xml`
- กลุ่มกลาง Layer 1: `custom_addons/od19_security_roles/security/od19_security_groups.xml`
- เทสต์ที่เกี่ยวข้อง: `custom_addons/od19_fleet_accounting/tests/test_department_scope.py`, `custom_addons/od19_role_catalog/tests/test_role_catalog.py`
