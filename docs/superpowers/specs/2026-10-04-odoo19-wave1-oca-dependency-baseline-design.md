# Odoo 19 CE Wave 1 OCA Dependency Baseline

## Control Metadata
- Child spec ID: W1-OCA-BASELINE
- Wave: Wave 1 (Commercial and financial core)
- Status: Approved — OCA dependency baseline locked for Wave 1
- Owner: Commercial domain lead
- Reviewer: Technical supervisor
- Approvers: Business owner; Technical supervisor
- Canonical path: `docs/superpowers/specs/2026-10-04-odoo19-wave1-oca-dependency-baseline-design.md`
- Source backlog row: `docs/superpowers/programs/odoo19-enterprise/backlog/domain-wave-matrix.md`
- Target edition: Odoo 19 Community Edition (CE)
- Date: 2026-10-04
- Primary readers: ทีมเทคนิค + ผู้ตัดสินใจด้านสถาปัตยกรรม
- Traceability note: filename/path และบาง program paths ยังใช้คำว่า `enterprise` เพื่อความต่อเนื่องของเอกสารเดิม แต่ baseline ที่อนุมัติแล้วของโครงการนี้คือ Odoo 19 CE
- Related:
  - `docs/superpowers/programs/odoo19-enterprise/sales/oca-fit-gap.md`
  - `docs/superpowers/specs/2026-10-04-odoo19-enterprise-wave-1-sales-contract-core-design.md`
  - `custom_addons/od19_sales_oca_bridge_workflow/__manifest__.py`

## 1. เป้าหมาย

เอกสารนี้ใช้ล็อก baseline ของ OCA dependencies สำหรับงาน Wave 1 - Sales Contract Core
โดยยึดหลัก `OCA First, Custom Second` แบบที่ติดตั้งและทดสอบได้จริงใน environment ปัจจุบัน
ไม่ใช่อ้างชื่อโมดูลไว้ล่วงหน้าโดยที่ dependency chain ยังไม่ครบ

## 2. ปัญหาที่พบ

จากการตรวจสภาพแวดล้อมใน worktree ปัจจุบัน พบว่าแผน OCA fit-gap เดิมยังมี 3 ปัญหา:

1. บางโมดูลในเอกสารยังไม่มี source repo ที่ clone มาใน `third_party/oca`
2. บางโมดูลมี dependency chain ข้าม repo แต่ยังไม่ได้ดึง repo ต้นทางเข้ามา
3. ชื่อโมดูลบางตัวในเอกสารไม่ตรงกับชื่อที่มีอยู่จริงใน branch ปัจจุบัน

ผลคือถ้าใส่ dependency แบบ hard ทันที จะทำให้ install หรือ test matrix พัง

## 3. Baseline ที่อนุมัติให้เดินต่อ

### 3.1 Required now

กลุ่มนี้ถือเป็น OCA baseline ที่ควรเตรียมให้พร้อมในรอบถัดไป:

| Module | Repo | เหตุผล |
| --- | --- | --- |
| `base_user_role` | `OCA/server-backend` | ใช้แยกบทบาทงานขายและวางบิล |
| `sale_delivery_state` | `OCA/sale-workflow` | ใช้สถานะส่งมอบระหว่างทางก่อน billing readiness |
| `base_revision` | `OCA/server-ux` | เป็น dependency ของ `sale_order_revision` |
| `sale_order_revision` | `OCA/sale-workflow` | ใช้ revision ของ quotation / order |
| `base_exception` | `OCA/server-tools` | เป็น dependency ของ `sale_exception` |
| `sale_exception` และโมดูล approval ที่พึ่ง `base_exception` ซึ่งต้องใช้จริง | `OCA/sale-workflow` | ใช้เป็นฐาน exception / approval rule แทน custom approval engine |
| `sale_blanket_order` | `OCA/sale-blanket` | ใช้เป็นฐานเอกสารเชิงพาณิชย์ของ contract-based sale |

### 3.2 Deferred pending confirmation

กลุ่มนี้ยังไม่ถือเป็น baseline ของ Wave 1 รอบนี้ จนกว่าจะยืนยัน branch/repo/compatibility สำหรับ Odoo 19 ได้ชัด:

| Module | สถานะที่ต้องการ |
| --- | --- |
| `sale_invoice_plan` | deferred ไว้ก่อนจนกว่าจะยืนยัน 19.0 baseline ที่ใช้ได้จริง |
| `sale_tier_validation` | deferred ไว้ก่อนจนกว่าจะยืนยัน 19.0 baseline และ dependency `base_tier_validation` |

## 4. กติกาการ adopt

ใช้กติกาเดียวกันทุกโมดูล:

1. ถ้าเขียนไว้ใน `depends`, source และ dependency ของมันต้องมีอยู่จริงใน workspace
2. ถ้าจะ claim ว่า adopt แล้ว ต้องติดตั้งได้จริงและอยู่ใน test matrix
3. ถ้ายังไม่พร้อม ให้ระบุเป็น `deferred` หรือ `optional integration` ห้ามระบุเป็น adopted baseline

## 5. การปรับ fit-gap เดิม

เอกสาร fit-gap เดิมควรถูกปรับตามนี้:

1. เปลี่ยน `sale_delivery_status` เป็น `sale_delivery_state`
2. เปลี่ยน source ของ `sale_blanket_order` จาก `OCA/sale-workflow` เป็น `OCA/sale-blanket`
3. เพิ่ม dependency notes ว่า `sale_order_revision` ต้องมี `base_revision`
4. เพิ่ม dependency notes ว่า approval rule family ต้องมี `base_exception`
5. เปลี่ยน `sale_invoice_plan` และ `sale_tier_validation` เป็น `deferred pending 19.0 confirmation`

## 6. แนวทาง implementation รอบถัดไป

เมื่อเริ่มลงมือ:

1. clone repo OCA ที่ขาดเข้ามาใน `third_party/oca`
2. ขยาย `addons-path` และ test stack ให้รวม repo ใหม่
3. อัปเดต `od19_sales_oca_bridge_workflow` ให้ bridge กับ `sale_order_revision`, `sale_exception` family, และ `sale_blanket_order`
4. อัปเดตเอกสาร fit-gap ให้ตรงกับ baseline จริง
5. รัน targeted test matrix ใหม่หลังเติม dependency ครบ

## 7. นอกขอบเขตของรอบนี้

สิ่งที่ยังไม่ทำในรอบนี้:

- port โมดูล OCA จาก 18.0 มา 19.0 เอง
- ทำ custom approval engine ใหม่แทน OCA
- เปิดใช้ invoice plan หรือ tier validation โดยไม่มี baseline ยืนยันแล้ว
