# Odoo 19 CE Wave 1: Contacts Partner Roles

## Control Metadata
- Child spec ID: W1-CONTACTS-PARTNER-ROLES
- Wave: Wave 1
- Status: Draft
- Owner: Commercial domain lead
- Reviewer: Technical supervisor
- Approvers: Business owner; Technical supervisor
- Canonical path: `docs/superpowers/specs/2026-10-05-odoo19-enterprise-wave-1-contacts-partner-roles-design.md`
- Source backlog row: `docs/superpowers/programs/odoo19-enterprise/backlog/domain-wave-matrix.md`
- Date: 2026-10-05
- Primary readers: ฝ่ายขาย, ผู้ดูแลข้อมูลคู่ค้า, ผู้จัดการฝ่ายขาย, ทีมเทคนิค

## Discovery Evidence
- Current-state references:
  - `docs/superpowers/specs/2026-10-04-odoo19-ce-enterprise-blueprint-design.md`
  - `docs/superpowers/specs/2026-10-04-odoo19-enterprise-wave-1-sales-contract-core-design.md`
  - `custom_addons/od19_sales_project_context/`
  - `custom_addons/od19_sales_contract_core/`
  - `custom_addons/od19_sales_reporting/`
  - `Odoo15Backup/odoo15_oca_mapping.xlsx`
- Evidence coverage gaps:
  - ยังไม่มี inventory ของ partner data quality จากระบบเดิมแบบครบถ้วน
  - ยังไม่มีข้อสรุปสุดท้ายเรื่องการใช้ company/contact hierarchy ในทุกแผนก
  - ยังไม่มีกติกา dedup และ merge records เชิงปฏิบัติการสำหรับ migration

## Delivery Controls
- Dependencies:
  - Wave 0 governance baseline approved
  - Wave 1 Sales Contract Core baseline approved
  - ต้องไม่ทำให้ `res.partner` usage ใน Sales regress
- Gate readiness:
  - Spec-ready: บทบาท partner, validation ขั้นพื้นฐาน, และผลกระทบต่อ Sales ถูกนิยามชัด
  - Plan-ready: มีขอบเขต addon ชัด, test strategy ชัด, และไม่มีความกำกวมเรื่อง model หลัก
  - Build-ready: ผู้ใช้อนุมัติ child spec, path และ owner ชัด, และรู้ว่าจะไม่แตะ logic โดเมนอื่นเกินจำเป็น

## 1. สรุปสั้น ๆ

Child spec นี้ออกแบบ `Contacts` สำหรับ Wave 1 ในมุมที่เป็นฐานข้อมูลคู่ค้ากลางของธุรกิจ โดยใช้ `res.partner` เป็นแกนหลักต่อไป และเพิ่มความหมายเชิงธุรกิจผ่าน partner roles ที่สะท้อนบทบาทจริงของคู่ค้าในงานขาย เช่น `Commercial Customer`, `Project Owner`, และ `Contractor`

จุดมุ่งหมายไม่ใช่สร้าง customer master ใหม่ แต่เป็นการยกระดับคุณภาพของ partner master data ให้โดเมน Sales ที่ทำไปแล้วใช้งานได้อย่างมีความหมาย, ค้นหาได้ง่าย, ตรวจสอบข้อมูลได้, และรองรับการ reuse ไปยังโดเมนอื่นใน Wave 1 ภายหลัง

## 2. เป้าหมายของ Child Spec นี้

- กำหนดว่า `res.partner` คือ canonical contact master ของ Wave 1
- ทำให้ระบบรู้จักบทบาทของคู่ค้าอย่างเป็นระบบ แทนการตีความจากชื่อหรือการใช้งานหน้างาน
- เพิ่ม validation ขั้นพื้นฐานเพื่อยกระดับคุณภาพข้อมูลโดยไม่ทำให้ข้อมูลเดิมใช้ไม่ได้ทั้งหมดในทันที
- ทำให้ทีมขายและผู้ดูแลข้อมูลค้นหา, กรอง, และตรวจสอบคู่ค้าได้ง่ายขึ้น
- รักษาความเข้ากันได้กับ `Wave 1 Sales Contract Core` ที่อ้าง partner อยู่แล้ว
- วางฐานสำหรับโดเมน `Purchase`, `Inventory`, และ `Accounting` ใน Wave 1 โดยไม่ดึง logic ของโดเมนเหล่านั้นเข้ามาปน

## 3. ขอบเขตของ Child Spec

### 3.1 สิ่งที่อยู่ในก้อนนี้

- การเสริม `res.partner` ด้วยบทบาทเชิงธุรกิจของคู่ค้า
- การกำหนดกติกาว่า partner หนึ่งรายสามารถมีหลายบทบาทได้
- การเพิ่ม field ธุรกิจขั้นต่ำที่จำเป็นต่อการใช้งานเชิงพาณิชย์
- การเพิ่ม validation ขั้นพื้นฐานสำหรับ partner ที่ถูกใช้งานในบทบาทสำคัญ
- การปรับปรุง form view, list view, search view, filter และ group by ของคู่ค้า
- การกำหนดหลักการ active/inactive สำหรับคู่ค้าที่ถูกอ้างในโดเมนขาย
- การยืนยัน compatibility กับโมดูล `od19_sales_project_context`, `od19_sales_contract_core`, และ `od19_sales_reporting`

### 3.2 สิ่งที่ยังไม่ลงลึกในก้อนนี้

- ระบบ dedup/merge คู่ค้าแบบอัตโนมัติ
- migration script เชิงลึกจาก Odoo 15
- vendor policy หรือ purchase-specific behavior
- accounting-specific partner control เช่น credit control, receivable policy, tax engine
- partner approval workflow เชิงบริหาร
- contact relationship model ขั้นสูง เช่น parent/child policy ที่ซับซ้อนเกินความจำเป็นของ Wave 1

## 4. Current-State Summary

ปัจจุบัน `Wave 1 Sales Contract Core` ใช้ `res.partner` ตรงอยู่แล้วในหลายจุด เช่น:

- `sale.order.partner_id` สำหรับคู่ค้าทางการค้า
- `sale.order.od19_project_owner_id` สำหรับเจ้าของโครงการ
- `od19.sales.project.contractor_ids` สำหรับกลุ่มผู้รับเหมาที่เกี่ยวข้อง
- รายงาน repeat business และ project revenue ที่อ้าง `commercial_customer_id` และ `project_owner_id`

สถานะนี้ทำให้ระบบเดินได้ แต่ยังมีข้อจำกัดสำคัญ:

- ความหมายของ partner แต่ละรายยังไม่ได้ถูกจัดการเป็นมาตรฐานระดับโดเมน Contacts
- การกรองและค้นหาคู่ค้าตามบทบาทธุรกิจยังไม่ชัดเจนพอ
- validation ของข้อมูลคู่ค้าเชิงธุรกิจยังอยู่กระจัดกระจายหรือยังไม่มี
- โดเมนอื่นใน Wave 1 ยังไม่มีฐาน partner semantics ที่พร้อม reuse

ดังนั้น Contacts child spec นี้มีหน้าที่ "ทำฐานข้อมูลคู่ค้าให้เป็นระบบ" โดยไม่รื้อโครงธุรกรรมของ Sales

## 5. Keep / Refactor / Replace / Retire

### 5.1 Keep

- Keep `res.partner` เป็น model หลักของ contact master
- Keep การอ้าง partner จากโมดูล Sales ที่สร้างไปแล้ว
- Keep แนวคิดการแยก `Commercial Customer`, `Project Owner`, และ `Contractor`

### 5.2 Refactor

- Refactor ความหมายของคู่ค้าจากการใช้ field เฉพาะโดเมนขายอย่างเดียว ไปเป็น semantics ระดับ Contacts
- Refactor search/filter/view ให้รองรับการทำงานจริงของทีมใช้งาน

### 5.3 Replace

- Replace การตีความบทบาทคู่ค้าแบบไม่เป็นระบบ ด้วย role fields ที่ชัดเจน

### 5.4 Retire

- Retire แนวคิดการสร้าง customer registry ใหม่ซ้อนกับ `res.partner` ใน Wave 1
- Retire การเก็บบทบาทคู่ค้าแบบ free text หรือใช้ชื่อกลุ่มอย่างไม่มีมาตรฐาน

## 6. Future-State Design

### 6.1 Canonical Model

`res.partner` ยังคงเป็น canonical model สำหรับคู่ค้า, ผู้ติดต่อ, และองค์กรใน Wave 1 ทั้งหมด โดย child spec นี้จะเสริม field และกติกาที่ช่วยบอกความหมายเชิงธุรกิจของ partner แต่ละรายให้ชัดขึ้น

แนวทางนี้ทำให้:

- ไม่เกิด model master ใหม่ที่ซ้ำซ้อน
- ไม่เพิ่ม hidden mapping ระหว่าง Contacts กับ Sales
- ยังคงความเข้ากันได้กับมาตรฐาน Odoo และ OCA

### 6.2 Partner Roles

สำหรับ Wave 1 ให้ใช้ role flags บน `res.partner` เป็นแนวทางหลัก เช่น:

- `od19_is_commercial_customer`
- `od19_is_project_owner`
- `od19_is_contractor`

เหตุผลที่เริ่มด้วย field flags:

- เบากว่า role engine เต็มรูปแบบ
- เข้าใจง่ายสำหรับทีมใช้งาน
- ทำ filter, search, และ validation ได้ตรงไปตรงมา
- เชื่อมกับ Sales ที่มีอยู่แล้วได้โดยไม่ต้องย้าย architecture ใหญ่

Partner หนึ่งรายสามารถมีได้มากกว่าหนึ่งบทบาท เพื่อสะท้อนโลกจริงที่บริษัทหนึ่งอาจเป็นทั้งผู้ว่าจ้างและเจ้าของโครงการในคนละบริบท

### 6.3 Business Fields ขั้นต่ำ

ฟิลด์ขั้นต่ำที่ child spec นี้คาดว่าจะต้องมีหรือทำให้ใช้งานได้ชัดเจนขึ้น ได้แก่:

- ชื่อคู่ค้า/ชื่อทางการค้า
- ประเภทองค์กรหรือบุคคล
- เลขทะเบียน/เลขผู้เสียภาษี ถ้ามี
- ช่องทางติดต่อหลัก
- ผู้รับผิดชอบภายใน ถ้าจำเป็นต่อการใช้งานเชิงพาณิชย์
- สถานะ active/inactive

child spec นี้จะไม่ขยาย field แบบเกินความจำเป็นของ Wave 1 และจะเน้น field ที่ช่วยยกระดับคุณภาพข้อมูลสำหรับงานขายและงานข้ามทีมเท่านั้น

## 7. Validation Model

validation ต้องมีเป้าหมายเพื่อเพิ่มคุณภาพข้อมูลโดยไม่ทำให้ข้อมูลเดิมเปิดใช้ไม่ได้ทั้งหมดทันที

กติกาขั้นต้นที่แนะนำ:

- partner ที่ถูก mark เป็น `Commercial Customer` ต้องมีข้อมูลระบุตัวตนและช่องทางติดต่อหลักอย่างน้อยขั้นต่ำ
- partner ที่ถูก mark เป็น `Project Owner` ต้องพร้อมถูกอ้างอิงใน `project context`
- partner ที่ถูก mark เป็น `Contractor` ต้องพร้อมใช้งานใน `sale.order` หรือรายงานที่เกี่ยวข้อง
- partner ที่ inactive ไม่ควรถูกเลือกใช้งานใหม่ใน flow หลัก ถ้าไม่มีเหตุผลพิเศษ

child spec นี้เน้น validation แบบ `basic guardrails` ไม่ใช่ `strict data policing`

## 8. User Experience และ Searchability

### 8.1 Views

ควรมีการปรับปรุง form/list/search views ของ `res.partner` เพื่อให้ผู้ใช้เห็นบทบาทและข้อมูลสำคัญได้ชัด

สิ่งที่ควรมี:

- section หรือกลุ่ม field สำหรับบทบาทของ partner
- field ธุรกิจขั้นต่ำที่อยู่ในตำแหน่งอ่านง่าย
- ตัวช่วยแยกข้อมูล active/inactive ให้สังเกตง่าย

### 8.2 Search / Filter / Grouping

ควรเพิ่ม filter สำคัญอย่างน้อย:

- Commercial Customers
- Project Owners
- Contractors
- Active
- Inactive

และควรมี groupings ที่ช่วยงานหน้างาน เช่น:

- แยกตามประเภท role
- แยกตาม company/person
- แยกตาม salesperson หรือผู้ดูแลข้อมูล ถ้ามีการใช้งานจริง

## 9. ความสัมพันธ์กับ Wave 1 Sales

Contacts child spec นี้ต้องไม่ทำให้โมดูลต่อไปนี้ regress:

- `od19_sales_project_context`
- `od19_sales_contract_core`
- `od19_sales_billing_evidence`
- `od19_sales_reporting`
- `od19_sales_oca_bridge_workflow`

หลักการคือ Contacts จะเป็นฐาน master data ส่วน Sales จะยังคงรับผิดชอบ transaction logic ต่อไป

จุดที่ต้องระวัง:

- ห้ามย้าย field จาก Sales กลับมา Contacts จนทำให้ dependency สลับทิศ
- ห้ามใส่ business policy ของ contract, billing, หรือ reporting ลงใน Contacts
- ห้ามสร้าง coupled workflow ระหว่าง partner role กับ sales transaction แบบแข็งเกินจำเป็น

## 10. Reporting และ KPI Needs

Wave 1 - Contacts ไม่ได้สร้าง owner dashboard ใหม่โดยตรง แต่ต้องรองรับข้อมูลพื้นฐานที่ทำให้รายงานของโดเมนขายน่าเชื่อถือขึ้น เช่น:

- การแยกฐานลูกค้าเชิงพาณิชย์ออกจากเจ้าของโครงการ
- การวิเคราะห์ repeat business บนฐาน role ที่ชัดเจน
- การทำความสะอาดกลุ่มคู่ค้าที่ควรใช้งานเชิงพาณิชย์จริง

ตัวชี้วัดขั้นต่ำที่ child spec นี้ควรช่วยให้เกิดในอนาคต:

- จำนวนคู่ค้าที่มี role พร้อมใช้งานจริง
- จำนวนคู่ค้าที่ข้อมูลไม่ครบตาม minimum business rule
- จำนวน partner inactive ที่ยังถูกอ้างใน flow สำคัญ

## 11. Security และ Approval Model

- ใช้ security ตามมาตรฐาน `res.partner` และสิทธิ์ผู้ใช้ Odoo เป็นแกนก่อน
- ไม่สร้าง approval workflow ใหม่ใน Wave 1 สำหรับการเปลี่ยน role ของ partner
- ถ้าจำเป็นให้ใช้ validation และ auditability ผ่าน chatter/tracking เท่าที่เหมาะสม

## 12. Migration Assumptions

- ระบบ Odoo 15 เดิมเป็น reference ไม่ใช่ของที่ต้องย้ายแบบตรงตัว
- ข้อมูล role ของคู่ค้าอาจต้องอาศัย mapping rule ในภายหลัง
- migration detail และ cleansing plan ละเอียด ให้ไปอยู่ใน implementation plan หรือ migration workstream แยก

## 13. Training Impact

ผู้ใช้ที่เกี่ยวข้องต้องเข้าใจอย่างน้อย:

- ความต่างระหว่าง `Commercial Customer`, `Project Owner`, และ `Contractor`
- วิธี mark บทบาทของ partner
- วิธีค้นหาและกรองคู่ค้าตาม role
- วิธีจัดการ active/inactive โดยไม่ทำลาย referential usage

## 14. Test Strategy

อย่างน้อยต้องมี test 3 กลุ่ม:

- model tests สำหรับ role assignment และ validation ขั้นพื้นฐาน
- view/search smoke tests เพื่อยืนยันว่า fields และ filters สำคัญโหลดได้
- compatibility tests เพื่อยืนยันว่า `Wave 1 Sales` ยังทำงานกับ partner ที่มี role flags ได้ตามปกติ

## 15. Known Unknowns

- จะใช้ boolean flags ทั้งหมด หรือควรเผื่อ model extension บางส่วนสำหรับ future waves
- ต้องการกติกาข้อมูลบังคับขั้นต่ำแยกตาม role ละเอียดแค่ไหน
- ต้องรองรับ company/contact hierarchy ระดับใดในแต่ละทีม
- migration rule จากข้อมูล partner เดิมควรแยกเป็น phase ย่อยหรือรวมกับ implementation plan

## 16. Gate Readiness Summary

### 16.1 Spec-ready

ถือว่า spec-ready เมื่อ:

- บทบาท partner หลักได้รับความเห็นชอบ
- ขอบเขตของ Contacts ไม่ทับกับ Sales
- แนวทาง `res.partner` enhancement ได้รับการยืนยัน

### 16.2 Plan-ready

ถือว่า plan-ready เมื่อ:

- ผู้ใช้ review child spec นี้แล้ว
- ไม่มีความกำกวมเรื่อง canonical model และ role strategy
- test strategy เพียงพอสำหรับกัน regression ต่อ Sales

### 16.3 Build-ready

ถือว่า build-ready เมื่อ:

- implementation plan ถูกเขียนและอนุมัติ
- ตกลงขอบเขต addon ของ Contacts ชัดเจน
- รู้แน่ชัดว่าจะไม่พ่วง Purchase, Inventory, และ Accounting logic เข้ามาในรอบนี้

## 17. คำตัดสินของ Child Spec นี้

Wave 1 - Contacts ควรเริ่มจาก `partner roles on res.partner` แบบเรียบง่ายและควบคุม scope เข้ม เพื่อสร้าง master data semantics ที่ชัดสำหรับธุรกิจ โดยไม่รื้อ `Wave 1 Sales` ที่ทำไปแล้ว

แนวทางนี้เป็นแนวทางที่สมดุลที่สุดระหว่าง:

- ความเร็วในการส่งมอบ
- ความเสถียรของ architecture
- ความเข้ากันได้กับ Odoo/OCA
- ความพร้อมสำหรับการ reuse ไปยังโดเมนอื่นใน Wave 1
