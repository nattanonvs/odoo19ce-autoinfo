# Odoo 19 CE Wave 1: Purchase Procurement Core

## Control Metadata
- Child spec ID: W1-PURCHASE-PROCUREMENT
- Wave: Wave 1
- Status: Draft
- Owner: Procurement domain lead
- Reviewer: Technical supervisor
- Approvers: Business owner; Technical supervisor
- Canonical path: `docs/superpowers/specs/2026-10-06-odoo19-enterprise-wave-1-purchase-procurement-core-design.md`
- Source backlog row: `docs/superpowers/programs/odoo19-enterprise/backlog/domain-wave-matrix.md`
- Date: 2026-10-06
- Primary readers: ฝ่ายจัดซื้อ, ฝ่ายขาย, ฝ่ายคลัง, ฝ่ายบัญชี, ผู้อนุมัติ, ผู้บริหาร, ทีมเทคนิค

## Discovery Evidence
- Current-state references:
  - `docs/superpowers/specs/2026-10-04-odoo19-ce-enterprise-blueprint-design.md`
  - `docs/superpowers/specs/2026-10-04-odoo19-enterprise-wave-1-sales-contract-core-design.md`
  - `docs/superpowers/specs/2026-10-05-odoo19-enterprise-wave-1-contacts-partner-roles-design.md`
  - `docs/superpowers/programs/odoo19-enterprise/governance/wave-1-handoff-baseline.md`
  - `docs/superpowers/programs/odoo19-enterprise/discovery/current-state-inventory.md`
  - `Odoo15Backup/odoo15_oca_mapping.xlsx`
- Evidence coverage gaps:
  - ยังไม่มี inventory เชิงลึกของ flow จัดซื้อเดิมจาก Odoo 15 แบบเอกสารต่อเอกสาร
  - ยังไม่มีหลักฐานครบถ้วนของ approval matrix เดิม, vendor master policy, และ receiving exceptions จากระบบเดิม
  - ยังไม่มี mapping เชิงข้อมูลของ PR, RFQ, PO, receipt, service acceptance, และ vendor bill แบบ field-by-field

## Delivery Controls
- Dependencies:
  - Wave 0 governance baseline approved
  - Wave 1 Sales Contract Core baseline approved
  - Wave 1 Contacts baseline approved
  - ต้องไม่ทำให้ boundary ระหว่าง Purchase, Inventory, และ Accounting สับสน
- Gate readiness:
  - Spec-ready: รูปแบบการเริ่มเอกสาร, approval policy, line semantics, และ receiving split ถูกนิยามชัด
  - Plan-ready: ขอบเขต addon ชัด, integration points ชัด, และไม่มีความกำกวมเรื่อง internal procurement กับ project procurement
  - Build-ready: ผู้ใช้อนุมัติ child spec, policy เรื่อง approval ทุกใบชัด, และรู้แน่ชัดว่างานใดเป็นของ Inventory/Accounting

## 1. สรุปสั้น ๆ

Child spec นี้ออกแบบแกน `Purchase` สำหรับ Wave 1 ให้รองรับพร้อมกัน 2 โลกการใช้งาน:

- งานจัดซื้อเพื่อใช้ภายในองค์กร
- งานจัดซื้อที่ผูกกับงานขายหรือโครงการของลูกค้า

จุดสำคัญคือระบบต้องไม่มองการจัดซื้อเป็นแค่ back-office อย่างเดียว แต่ต้องเป็น procurement core ที่เชื่อมกับบริบทเชิงพาณิชย์ได้จริง โดยยังรักษา boundary ให้ชัดว่า:

- Purchase ดูแลคำขอซื้อ, การเลือก vendor, การขออนุมัติ, และการสร้าง commitment กับ vendor
- Inventory ดูแล movement และ receipt ของสินค้า
- Accounting ดูแล vendor bill, ภาษี, การลงบัญชี, และการจ่ายเงิน

## 2. เป้าหมายของ Child Spec นี้

- รองรับทั้ง `PR -> PO` และ `Direct PO`
- รองรับทั้ง `internal procurement` และ `project/sale-linked procurement`
- ทำให้ `PO line` อ้างบริบทงานได้ชัดว่าใช้ภายในหรือผูกกับโครงการ/งานขายใด
- บังคับ `approval ทุกใบ` เป็น baseline กลางของ Wave 1
- แยกกติกา `สินค้า` และ `บริการ` ให้ชัดเจนตั้งแต่ระดับเอกสารจัดซื้อ
- คุมงบแบบ `เตือนก่อน ไม่บล็อก` เพื่อช่วยผู้อนุมัติตัดสินใจโดยไม่ทำให้หน้างานหยุดแข็ง
- วางฐานให้ Inventory และ Accounting มาต่อได้ โดยไม่ดึง logic ของสองโดเมนนั้นเข้ามาปนใน Purchase

## 3. ขอบเขตของ Child Spec

### 3.1 สิ่งที่อยู่ในก้อนนี้

- การรองรับเส้นทาง `Purchase Requisition` และ `Direct Purchase Order`
- การกำหนด purpose หรือ procurement intent ระดับ `PO line`
- การผูก `PO line` เข้ากับ `project` หรือ `sale context` เมื่อเป็นงานโครงการ
- การกำหนด approval baseline ที่ใช้กับทุกเอกสารจัดซื้อสำคัญ
- การแยกสินค้าและบริการออกจากกันใน flow จัดซื้อ
- การวาง warning model เมื่อมีสัญญาณเกินงบหรือเกินกรอบอ้างอิง
- การกำหนด status หลักของ procurement ตั้งแต่ขอซื้อจนถึงพร้อมส่งต่อ receipt/bill
- รายงานหรือ KPI ขั้นต่ำที่ช่วยเจ้าของและผู้บริหารเห็นภาระผูกพันและความเสี่ยง

### 3.2 สิ่งที่ยังไม่ลงลึกในก้อนนี้

- stock reservation, picking rules, putaway, และ movement detail ฝั่งคลัง
- vendor bill posting, tax mapping, account mapping, payment, และ reconciliation
- supplier evaluation เชิงลึก เช่น scorecard เต็มรูปแบบหรือ tender engine เต็มระบบ
- contract procurement ระยะยาวเชิงซับซ้อน เช่น call-off agreement หลายชั้น
- การออกแบบ UI รายฟอร์มหรือรายกระดาษแบบเฉพาะลูกค้า
- migration script เชิงเทคนิคแบบ field-by-field จาก Odoo 15

## 4. Current-State Summary

จาก baseline ที่มีอยู่แล้ว:

- Sales รองรับทั้งงานขายทั่วไปและงานขายผูกสัญญา/โครงการ
- Contacts แยก role ของคู่ค้าเชิงพาณิชย์ได้แล้ว เช่น commercial customer, project owner, contractor
- แต่ยังไม่มี child spec ที่ทำให้ procurement มี semantics ของตัวเองและเชื่อมกับงานโครงการได้เป็นระบบ

ถ้าไม่มี Purchase baseline ที่ชัด จะเกิดปัญหาตามมา:

- รายการสั่งซื้อที่เป็นของใช้ภายในกับของโครงการปะปนกัน
- ผู้อนุมัติมองไม่ออกว่ากำลังอนุมัติ procurement เพื่ออะไร
- สินค้าและบริการอาจถูกปฏิบัติเหมือนกันทั้งที่หลักฐานการรับไม่เหมือนกัน
- Inventory และ Accounting ต้องเดา intent ของเอกสารย้อนหลังจาก memo หรือ free text

## 5. Keep / Refactor / Replace / Retire

### 5.1 Keep

- Keep โครงมาตรฐาน Odoo ด้าน `purchase` และเอกสาร `RFQ/PO`
- Keep แนว `OCA First, Custom Second`
- Keep หลักการแยก bounded context ระหว่าง Purchase, Inventory, และ Accounting

### 5.2 Refactor

- Refactor ความหมายของเอกสารจัดซื้อจากการเป็นเพียง PO ไปเป็น procurement flow ที่มี intent ชัด
- Refactor การผูกงานโครงการจากการจดจำกันเอง ไปเป็น reference ที่ระดับ line

### 5.3 Replace

- Replace การตัดสินใจอนุมัติจากความเข้าใจส่วนบุคคล ด้วย baseline ที่ `ทุกใบต้องอนุมัติ`
- Replace การใช้ free text ระบุว่า "ซื้อเพื่อโครงการอะไร" ด้วย line semantics ที่ตรวจสอบได้

### 5.4 Retire

- Retire แนวคิดที่ให้ Purchase เป็นแค่ธุรการหลังบ้านโดยไม่ผูกกับ owner value
- Retire การปฏิบัติต่อบริการเหมือนสินค้าทุกกรณี

## 6. Future-State Design

### 6.1 Procurement Modes

Purchase ใน Wave 1 ต้องรองรับ 2 โหมดหลักพร้อมกัน:

- `Internal Procurement`
  ใช้สำหรับของใช้ภายใน, เครื่องมือ, วัสดุสำนักงาน, หรือค่าใช้จ่ายที่ไม่ผูกกับลูกค้าโดยตรง
- `Project / Sale-linked Procurement`
  ใช้สำหรับของหรือบริการที่ซื้อมาเพื่อรองรับงานขาย, งานสัญญา, หรือโครงการของลูกค้า

ทั้งสองโหมดต้องใช้ procurement core เดียวกัน แต่ต้องแยก intent ให้ชัดเพื่อรองรับการอนุมัติ, การติดตาม, และการวิเคราะห์ต้นทุน

### 6.2 Entry Documents Baseline

Wave 1 ต้องรองรับทั้ง:

- `PR -> Approval -> RFQ/PO`
- `Direct PO -> Approval`

หลักการคือ:

- ถ้าเป็นความต้องการที่มาจากผู้ใช้งานภายในและต้องการควบคุมก่อนซื้อ ให้เริ่มจาก `PR`
- ถ้าเป็นกรณีเร่งด่วนหรืออยู่ในมือผู้จัดซื้อโดยตรง สามารถสร้าง `PO` ได้ตรง
- ไม่ว่ามาจากเส้นทางใด เอกสารที่สร้าง commitment กับ vendor ต้องผ่าน approval ทุกใบ

### 6.3 PO Line Semantics

ระดับ `PO line` ต้องอธิบายได้อย่างน้อยว่า:

- เป็นรายการสำหรับใช้งานภายใน หรือผูกกับงานลูกค้า
- ถ้าผูกกับงานลูกค้า ผูกกับ `project`, `sale order`, หรือ procurement context ใด
- เป็น `สินค้า` หรือ `บริการ`
- มี budget reference หรือ amount reference อะไรที่ควรใช้เตือนผู้อนุมัติ

การผูกที่ระดับ line สำคัญเพราะ PO หนึ่งใบอาจมีหลายรายการและแต่ละรายการอาจมีวัตถุประสงค์ต่างกัน

### 6.4 Product vs Service Split

Wave 1 ต้องแยกกติกา `สินค้า` และ `บริการ` ชัดเจน:

- `สินค้า`
  ต้องส่งต่อไปยัง receipt/inventory flow ตามกติกาของคลัง
- `บริการ`
  ไม่ควรถูกบังคับให้ผ่าน stock receipt แบบเดียวกับสินค้า แต่ต้องมีหลักฐานการรับบริการหรือ service evidence ที่เหมาะสมก่อนส่งต่อให้บัญชี

Purchase domain ต้องเพียงระบุ intent และ readiness criteria ขั้นต้น ส่วนรายละเอียด execution ของ receipt/service acceptance ให้เป็นความรับผิดชอบของ Inventory หรือ Accounting ตามประเภทงาน

### 6.5 Approval Baseline

baseline ของ Wave 1 คือ `อนุมัติทุกใบ`

หลักการ:

- PR ที่ใช้งานจริงต้องมี approval
- Direct PO ต้องมี approval ก่อนกลายเป็น commitment ที่มีผล
- RFQ/PO ที่มีการแก้ไขสาระสำคัญหลังอนุมัติ ควรกลับเข้าสู่การทบทวนตาม policy
- ผู้อนุมัติต้องเห็น purpose, line context, vendor, และสัญญาณงบก่อนตัดสินใจ

Wave 1 ยังไม่จำเป็นต้องลงลึก approval matrix ซับซ้อนหลายชั้น หากยังไม่มีหลักฐานครบ แต่ต้องยืนยันหลักการ `ไม่มีเอกสารซื้อที่ข้ามการอนุมัติ`

### 6.6 Budget Warning Policy

กติกางบใน Wave 1 ใช้แบบ `เตือนก่อน ไม่บล็อก`

สิ่งที่ระบบควรทำ:

- แจ้งเตือนเมื่อ PO หรือ line อ้างอิงโครงการที่มีงบใกล้เต็มหรือเกินกรอบ
- แจ้งเตือนเมื่อไม่มี budget reference ทั้งที่ line นั้นถูกระบุว่าเป็นงานโครงการ
- ให้ผู้อนุมัติยังสามารถอนุมัติได้ หากมีเหตุผลทางธุรกิจ

เหตุผลของแนวนี้คือ:

- สถานะ budget truth ใน Wave 1 ยังอาจกระจายอยู่หลายโดเมน
- ถ้าบล็อกทันทีอาจทำให้งานจริงหยุดทั้งที่ข้อมูลอ้างอิงยังไม่พร้อมเต็มที่

## 7. Document Lifecycle

วงจรเอกสารขั้นต่ำที่ควรอธิบายได้:

- `Draft`
- `To Approve`
- `Approved`
- `Sent to Vendor` หรือ `Committed`
- `Partially Received / Service Pending`
- `Fully Received / Service Accepted`
- `Ready for Billing Handoff`
- `Closed` หรือ `Cancelled`

ไม่จำเป็นต้องใช้ชื่อสถานะตามนี้เป๊ะ แต่ต้องมีความหมายเทียบเคียงได้เพื่อใช้สื่อสารข้ามทีม

## 8. Vendor and Partner Model

Purchase child spec นี้จะไม่สร้าง vendor master ใหม่ แต่จะ reuse `res.partner` ที่ถูกยกระดับจาก Contacts แล้ว

แนวทาง baseline:

- vendor เป็น partner ที่ถูกใช้งานในบริบทจัดซื้อ
- company/contact hierarchy ใช้กติกาเดียวกับ Contacts
- vendor contact ใช้สำหรับสื่อสารเชิงปฏิบัติการ แต่เอกสารสัญญาหรือ commitment หลักควรอ้าง company record

ถ้าต้องมี vendor-specific policy เพิ่ม เช่น payment term หรือ tax defaults ให้ถือเป็นส่วนต่อยอดที่ต้องออกแบบโดยไม่ขัดกับ partner master baseline

## 9. ความสัมพันธ์กับ Wave 1 Sales

Purchase child spec นี้ต้องเชื่อมกับ Sales แบบช่วยกัน ไม่ใช่ดึงกันไปมา

หลักการคือ:

- Sales เป็นคนกำหนด commercial context
- Purchase เป็นคนบริหาร sourcing, vendor commitment, และ procurement traceability
- ถ้า line ใดเป็นงานโครงการ ต้องอ้าง commercial context ให้ชัด แต่ Purchase ไม่รับ ownership ของ contract logic

จุดที่ต้องระวัง:

- ห้ามย้าย contract rules จาก Sales มาซ่อนไว้ใน Purchase
- ห้ามให้ Inventory ต้องเดา intent ของ line จาก free text
- ห้ามให้ Accounting เป็นจุดแรกที่เพิ่งมารู้ว่า PO เป็นของโครงการไหน

## 10. Reporting และ KPI Needs

Wave 1 - Purchase ต้องรองรับ owner value อย่างน้อยในมุมต่อไปนี้:

- มูลค่า procurement commitments แยก `internal` กับ `project-linked`
- มูลค่า PO ที่รออนุมัติ
- มูลค่า PO ที่เกินกรอบงบหรือมี budget warning
- มูลค่าแยก `สินค้า` กับ `บริการ`
- backlog ของรายการที่สั่งแล้วแต่ยังรับไม่ครบ หรือบริการที่ยังไม่มีหลักฐานรับครบ

สัญญาณเตือนขั้นต่ำที่ควรมี:

- เอกสารค้างอนุมัติ
- โครงการที่มีการจัดซื้อเกินกรอบบ่อย
- บริการที่มี PO แล้วแต่ไม่มี service evidence พร้อมส่งต่อ
- vendor commitment ที่ค้างรับเป็นเวลานาน

## 11. Security และ Approval Model

- ใช้สิทธิ์ Odoo และ role separation เป็นฐาน เช่น requester, buyer, approver, receiver
- แม้ `ทุกใบต้องอนุมัติ` แต่ไม่จำเป็นต้องให้คนเดียวกันเป็น requester, buyer, และ approver
- ต้องออกแบบให้ผู้อนุมัติเห็นข้อมูลพอสำหรับการตัดสินใจโดยไม่ต้องเปิดหลายเอกสารเองทั้งหมด
- approval log และการเปลี่ยนสถานะสำคัญควรตรวจสอบย้อนหลังได้

## 12. Migration Assumptions

- Odoo 15 เดิมเป็น reference สำหรับ flow และ master data ไม่ใช่ของที่ต้องย้ายแบบตรงตัว
- PR flow, direct PO flow, และ approval flow อาจต้องแตกเป็น migration workstream แยกจาก implementation หลัก
- ข้อมูล reference ที่ระดับ line เช่น project/sale link อาจต้องมี mapping rule พิเศษระหว่าง migration
- service acceptance evidence จากระบบเดิมอาจไม่ได้อยู่ในรูปข้อมูลที่พร้อมใช้ทันที

## 13. Training Impact

ผู้ใช้งานที่เกี่ยวข้องต้องเข้าใจอย่างน้อย:

- เมื่อใดควรเริ่มจาก `PR` และเมื่อใดสร้าง `PO` ตรงได้
- ความต่างระหว่าง procurement เพื่อใช้ภายในกับ procurement เพื่อโครงการ
- วิธีระบุ purpose และ reference ของ `PO line`
- ความต่างของการรับ `สินค้า` กับ `บริการ`
- วิธีอ่าน budget warning ก่อนอนุมัติ

## 14. Test Strategy

อย่างน้อยต้องมี test 4 กลุ่ม:

- model tests สำหรับ procurement intent, line semantics, และสถานะเอกสารหลัก
- workflow tests สำหรับ `PR -> PO` และ `Direct PO`
- approval tests เพื่อยืนยันว่าเอกสารถูกยืนยันหรือ commit โดยไม่ผ่าน approval ไม่ได้
- integration tests กับ Sales/Contacts และ smoke tests ที่ยืนยัน boundary กับ Inventory/Accounting ยังชัด

## 15. Known Unknowns

- approval matrix เชิงมูลค่า, หน่วยงาน, หรือประเภทเอกสารจะละเอียดแค่ไหนใน production จริง
- service acceptance evidence ควรถือโดย Purchase, Inventory, หรือ Accounting ในบางกรณีที่เป็นบริการกึ่งพัสดุ
- budget reference truth จะมาจาก project budget, sales budget, หรือ accounting controls เป็นหลัก
- vendor master policy เดิมมีข้อยกเว้นหรือ duplicate patterns อะไรบ้าง

## 16. Gate Readiness Summary

### 16.1 Spec-ready

ถือว่า spec-ready เมื่อ:

- baseline เรื่อง `PR + Direct PO`, `approval ทุกใบ`, `line-level project link`, และ `สินค้า/บริการแยกกัน` ได้รับความเห็นชอบ
- ขอบเขตของ Purchase ไม่ทับกับ Inventory และ Accounting
- procurement modes สำหรับ internal กับ project-linked ถูกนิยามชัด

### 16.2 Plan-ready

ถือว่า plan-ready เมื่อ:

- ผู้ใช้ review child spec นี้แล้ว
- ไม่มีความกำกวมเรื่อง document entry model และ line semantics
- integration points กับ Sales, Contacts, Inventory, และ Accounting ถูกระบุชัด

### 16.3 Build-ready

ถือว่า build-ready เมื่อ:

- implementation plan ถูกเขียนและอนุมัติ
- ขอบเขต addon หรือ OCA modules ฝั่ง Purchase ถูกยืนยัน
- policy approval, warning, และ receiving split ถูกแตกเป็นงานย่อยที่ทำได้จริง

## 17. คำตัดสินของ Child Spec นี้

Wave 1 - Purchase ควรถูกออกแบบเป็น `procurement core` ที่รองรับพร้อมกันทั้งงานใช้ภายในและงานผูกโครงการ โดยใช้ approval ทุกใบ, line-level procurement intent, และการแยกสินค้า/บริการเป็นแกน

แนวทางนี้สมดุลที่สุดระหว่าง:

- การคุมภายใน
- ความยืดหยุ่นหน้างาน
- ความสามารถในการผูกต้นทุนกับบริบทธุรกิจ
- ความพร้อมในการส่งต่อไปยัง Inventory และ Accounting ใน wave เดียวกัน
