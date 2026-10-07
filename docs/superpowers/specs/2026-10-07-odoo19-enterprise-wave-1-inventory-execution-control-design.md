# Odoo 19 CE Wave 1: Inventory Execution and Control

## Control Metadata
- Child spec ID: W1-INVENTORY-EXECUTION-CONTROL
- Wave: Wave 1
- Status: In review
- Owner: Inventory and warehouse domain lead
- Reviewer: Technical supervisor
- Approvers: Business owner; Technical supervisor
- Canonical path: `docs/superpowers/specs/2026-10-07-odoo19-enterprise-wave-1-inventory-execution-control-design.md`
- Source backlog row: `docs/superpowers/programs/odoo19-enterprise/backlog/domain-wave-matrix.md`
- Date: 2026-10-07
- Primary readers: ฝ่ายคลัง, ฝ่ายขาย, ฝ่ายจัดซื้อ, ฝ่ายบัญชี, ผู้อนุมัติ, ผู้บริหาร, ทีมเทคนิค

## Approval Traceability
- Design baseline was refined through scoped clarification on 2026-10-07.
- User approved the recommended `Execution-Plus Control` approach on 2026-10-07.
- User approved all three design sections on 2026-10-07 before this written child spec was produced.

## Discovery Evidence
- Current-state references:
  - `docs/superpowers/programs/odoo19-enterprise/discovery/current-state-inventory.md`
  - `docs/superpowers/specs/2026-10-04-odoo19-ce-enterprise-blueprint-design.md`
  - `docs/superpowers/specs/2026-10-04-odoo19-enterprise-wave-1-sales-contract-core-design.md`
  - `docs/superpowers/specs/2026-10-05-odoo19-enterprise-wave-1-contacts-partner-roles-design.md`
  - `docs/superpowers/specs/2026-10-06-odoo19-enterprise-wave-1-purchase-procurement-core-design.md`
  - `Odoo15Backup/odoo15_oca_mapping.xlsx`
  - Odoo standard modules `stock` and `purchase_stock`
- Evidence coverage gaps:
  - ยังไม่มีเอกสารยืนยัน current-state แบบละเอียดของ warehouse map, location hierarchy, และ movement exceptions จาก Odoo 15
  - ยังไม่มีหลักฐานครบถ้วนของ return scenarios, damaged goods handling, และ approval policy ฝั่ง stock adjustment เดิม
  - ยังไม่มี field-by-field migration map สำหรับ picking, move line, lot, serial, quant, และ inventory adjustment

## Delivery Controls
- Dependencies:
  - Wave 0 governance baseline approved
  - Wave 1 Sales Contract Core baseline approved
  - Wave 1 Contacts baseline approved
  - Wave 1 Purchase Procurement Core baseline approved
  - ต้องรักษา boundary ระหว่าง Purchase, Inventory, Accounting, และ Wave 4 Logistics ให้ชัด
- Gate readiness:
  - Spec-ready: ขอบเขต movement, returns, counting, traceability, และ boundary ระหว่างโดเมนถูกนิยามชัด
  - Plan-ready: addon boundaries, reporting baseline, security model, และ migration assumptions ถูกอธิบายชัดพอให้แตกงานได้
  - Build-ready: ผู้ใช้ review child spec นี้แล้ว และไม่มีความกำกวมเรื่อง movement ownership, counting controls, และ handoff ไป Accounting

## 1. สรุปสั้น ๆ

Child spec นี้ออกแบบแกน `Inventory` ของ Wave 1 ให้เป็น `execution and control core` ของคลัง โดยครอบทั้ง:

- `receipt`
- `delivery`
- `internal transfer`
- `returns`
- `lot/serial by need`
- `full audit counting`

หัวใจของก้อนนี้ไม่ใช่แค่ทำให้ของ "ขยับได้" แต่ต้องทำให้ระบบตอบได้ว่า:

- ของอยู่ที่ไหน
- เข้ามาเมื่อไร
- ออกไปเมื่อไร
- คืนกลับมาอย่างไร
- ยอดคงเหลือเชื่อถือได้แค่ไหน
- ความคลาดเคลื่อนของ stock เกิดจากอะไร

โดเมนนี้ต้องทำให้คลังเป็นแหล่งความจริงของ `physical movement` และ `stock accuracy` โดยไม่ดึง logic ของ `Purchase`, `Sales Contract`, `Service Execution`, หรือ `Accounting Posting` เข้ามาปะปนเกินจำเป็น

## 2. เป้าหมายของ Child Spec นี้

- วาง baseline ของคลังสำหรับ `movement execution` ที่ใช้ได้จริงใน Wave 1
- รองรับ `receipt`, `delivery`, `internal transfer`, และ `returns` เป็น flow หลักของธุรกิจ
- รองรับ `counting and audit control` ในระดับจริงจัง ไม่ใช่แค่ปรับยอดแบบไม่มีร่องรอย
- รองรับ `lot/serial` เฉพาะสินค้าหรือกลุ่มสินค้าที่ business จำเป็นต้องติดตาม
- ทำให้ movement สำคัญทุกตัวมี `traceability` และ `movement evidence`
- ทำให้ผู้บริหารเห็น backlog, stock mismatch, และจุดที่ทำให้เงินจมในคลัง
- วางฐานให้ `Accounting` และ `Wave 4 Logistics` มาต่อยอดได้ โดยไม่ทำให้ Inventory กลายเป็นโมดูลรวมทุกอย่าง

## 3. ขอบเขตของ Child Spec

### 3.1 สิ่งที่อยู่ในก้อนนี้

- การรับสินค้าเข้าคลังจาก vendor หรือแหล่งอ้างอิงที่ถูกต้อง
- การส่งสินค้าออกเพื่อรองรับงานขายหรือโครงการ
- การโอนย้ายสินค้าระหว่าง location หรือ warehouse
- การคืนสินค้าอย่างน้อยใน 2 ทิศทาง:
  - `return to vendor`
  - `customer return`
- การติดตาม movement evidence และ document reference สำหรับ movement สำคัญ
- การกำหนดว่า item ใดต้องใช้ `lot/serial tracking`
- การตรวจนับ stock, ตรวจ variance, ปรับยอด, และ review audit trail
- การสรุปสถานะเชิงธุรกิจของ movement และ counting
- รายงาน/KPI ขั้นต่ำของคลังที่ช่วยผู้ปฏิบัติการและผู้บริหารตัดสินใจ

### 3.2 สิ่งที่ยังไม่ลงลึกในก้อนนี้

- replenishment planning, orderpoints, route optimization, และ warehouse planning ขั้นสูง
- transport scheduling, routing, shipment orchestration, และ logistics extensions เชิงลึก
- accounting detail เช่น valuation policy เชิงบัญชี, journal posting, tax/account mapping, และ reconciliation
- service execution detail ที่ไม่ใช่ stock movement
- automation ซับซ้อนแบบ multi-step warehouse orchestration ที่ควรรอ Wave ถัดไป
- migration script เชิงเทคนิคแบบ field-by-field

## 4. Current-State Summary

จาก baseline ปัจจุบันของโครงการ:

- `Sales` กำหนด commercial context และ billing-relevant context
- `Contacts` กำหนด partner role model ที่เสถียรขึ้นแล้ว
- `Purchase` กำหนด procurement intent, line semantics, approval, และการแยกสินค้า/บริการไว้แล้ว
- แต่ `Inventory` ยังไม่มี child spec ที่นิยามชัดว่า movement และ stock accuracy จะถูกคุมอย่างไรใน Wave 1

ถ้าไม่มี Inventory baseline ที่ชัด จะเกิดปัญหาทันที:

- Purchase commit ของเข้ามาแล้ว แต่คลังไม่มีหลักในการรับและ trace ที่เป็นระบบ
- Sales รู้ว่าต้องส่งของ แต่ movement evidence และ stock truth ไม่ชัด
- Accounting ต้องรับ handoff จากสถานะที่เดาไม่ได้ว่า "รับจริงหรือยัง" หรือ "ส่งจริงหรือยัง"
- ผู้บริหารมองไม่เห็น stock mismatch, backlog, และสินค้าที่ทำให้เงินจม

## 5. Keep / Refactor / Replace / Retire

### 5.1 Keep

- Keep โครงมาตรฐานของ Odoo ด้าน `stock`
- Keep หลัก `OCA First, Custom Second`
- Keep การแยก bounded context ระหว่าง Purchase, Inventory, Accounting, และ Logistics Extensions
- Keep การใช้ reference document จากโดเมนต้นทาง เช่น PO, SO, project context โดยไม่ duplicate business meaning

### 5.2 Refactor

- Refactor มุมมองคลังจาก "แค่เก็บจำนวน" ไปเป็น `movement execution + control`
- Refactor การตรวจนับจากงานเฉพาะกิจ ไปเป็น flow audit ที่มีสถานะและผู้รับผิดชอบชัด
- Refactor การติดตาม lot/serial จากการใช้เฉพาะจุด ไปเป็น policy-based tracking ตามสินค้าจำเป็น

### 5.3 Replace

- Replace การเดาว่าของเคลื่อนไหวอย่างไรจาก memo หรือคำพูด ด้วย movement trace ที่ตรวจสอบได้
- Replace การปรับยอด stock แบบไม่มีเหตุผลอ้างอิง ด้วย count variance และ review trail
- Replace การมองคลังเป็น back-office เฉย ๆ ด้วยคลังที่สร้าง owner value ได้

### 5.4 Retire

- Retire แนวคิดที่ให้ movement สำคัญเกิดได้โดยไม่มี evidence
- Retire การทำ stock adjustment แบบไม่รู้ว่าใครทำ เมื่อไร และเพราะอะไร
- Retire การบังคับใช้ lot/serial กับทุกสินค้าโดยไม่มีเหตุผลทางธุรกิจ

## 6. Future-State Design

### 6.1 Inventory Baseline Model

Wave 1 - Inventory ต้องถูกออกแบบเป็น `execution and control core` ไม่ใช่แค่ระบบเก็บคงเหลือ และยังไม่ใช่ logistics platform เต็มรูปแบบ

ความหมายของ baseline นี้คือ:

- ต้องทำ movement หลักได้จริง
- ต้องคุม stock accuracy ได้จริง
- ต้องตรวจสอบย้อนหลังได้จริง
- ต้องส่งต่อข้อมูลให้โดเมนอื่นได้อย่างมี boundary

### 6.2 Movement Scope Baseline

movement ที่ถือเป็น `must-have` ของ Wave 1 มีดังนี้:

- `Receipt`
  รับสินค้าเข้าคลังจาก vendor หรือ inbound source ที่ถูกต้อง
- `Delivery`
  ส่งสินค้าออกเพื่อรองรับงานขายหรือโครงการ
- `Internal Transfer`
  ย้ายของระหว่าง location หรือ warehouse
- `Returns`
  รองรับทั้งคืนไป vendor และรับคืนกลับจากลูกค้า

ทุก movement ข้างต้นต้องมีสถานะพื้นฐานที่บอกได้อย่างน้อยว่า:

- `waiting`
- `ready`
- `done`
- `exception`

### 6.3 Inbound / Receipt Control

receipt ต้องรองรับอย่างน้อย:

- รับสินค้าตาม PO หรือ reference ที่ถูกต้อง
- ตรวจจำนวนที่รับจริงเทียบกับที่คาด
- ผูก location ปลายทางให้ชัด
- รองรับ lot/serial ถ้าสินค้านั้นถูกกำหนดว่าต้อง track
- เก็บผู้รับ, เวลา, quantity, source reference, และ evidence ที่จำเป็น

Inventory domain ต้องถือว่า receipt เป็นจุดที่ `physical truth` เริ่มเปลี่ยน ไม่ใช่จุดที่ Accounting truth เปลี่ยนเสมอไป

### 6.4 Outbound / Delivery Control

delivery ต้องรองรับอย่างน้อย:

- จอง/เตรียมสินค้าจาก stock truth ที่มีอยู่
- ส่งของออกตาม reference document ที่ชัด
- เก็บ movement evidence เพื่อบอกว่ามีการเคลื่อนของออกจริง
- แยก movement exception ออกจาก commercial exception

Sales ต้องเป็นเจ้าของ commercial trigger ของการขาย แต่ Inventory ต้องเป็นเจ้าของ truth ว่าของออกจริงหรือยัง

### 6.5 Internal Transfer Control

internal transfer เป็น baseline สำคัญ เพราะถ้าไม่คุม:

- ของอาจอยู่ผิด location
- stock balance ของแต่ละคลังจะไม่น่าเชื่อถือ
- count variance จะสูงโดยไม่รู้ต้นเหตุ

ดังนั้น transfer ต้องมี:

- source location
- destination location
- quantity
- responsible user
- date/time
- reason หรือ reference ที่เหมาะสม

### 6.6 Return Flows Baseline

Wave 1 ต้องรองรับ return อย่างน้อย 2 แบบ:

- `Return to Vendor`
  ใช้เมื่อสินค้ามีปัญหา, ส่งเกิน, หรือคืนตามข้อตกลงกับ vendor
- `Customer Return`
  ใช้เมื่อมีการรับคืนสินค้าจากลูกค้าหรือปลายทางกลับเข้าคลัง

สิ่งที่ Inventory ต้องตอบได้:

- ของคืนมาจากไหน
- คืนไปหาใคร
- คืนเพราะอะไร
- quantity เท่าไร
- สุดท้าย stock truth ถูกอัปเดตอย่างไร

child spec นี้ยังไม่ลงลึก credit/debit/accounting consequence ของ returns

### 6.7 Lot / Serial by Need

baseline ที่ตกลงกันคือ `lot/serial by need`

นั่นแปลว่า:

- ไม่บังคับ tracking กับทุก item
- ต้องกำหนดหลักเกณฑ์ว่า item ใดจำเป็นต้อง track
- item ที่อยู่ในกลุ่มนี้ต้องมี movement trace ละเอียดขึ้น

ตัวอย่างเหตุผลที่อาจต้องใช้ lot/serial:

- ของมูลค่าสูง
- ของที่มีความเสี่ยงเรื่องคุณภาพ
- ของที่ต้อง trace ย้อนหลังได้
- ของที่มีข้อกำหนดเชิงรับประกันหรือ compliance

### 6.8 Counting and Audit Control

baseline ที่ผู้ใช้เลือกคือ `Full Audit Counting`

ดังนั้น Inventory ใน Wave 1 ต้องไม่หยุดที่การมีปุ่มปรับยอด แต่ต้องมี `audit counting flow` อย่างชัดเจน

สถานะเชิงธุรกิจขั้นต่ำของ count flow:

- `count scheduled`
- `counted`
- `variance found`
- `adjusted`
- `reviewed`

หลักการของ count flow:

- ต้องรู้ว่านับอะไร นับที่ไหน และโดยใคร
- ต้องแยกผลนับจริงออกจากค่าคงเหลือเดิม
- ถ้ามี variance ต้องมีเหตุผลหรือคำอธิบายที่ตรวจสอบย้อนหลังได้
- การปรับยอดควรมีการ review ตามระดับความสำคัญ

### 6.9 Count Governance

แม้ child spec นี้ยังไม่บังคับ implementation ละเอียดระดับ workflow engine แต่ต้องล็อกหลักการดังนี้:

- count sheet หรือ count scope ต้องชัด
- variance ไม่ควรถูกลบกลบด้วยการปรับยอดเงียบ ๆ
- คนที่นับกับคนที่ review ไม่จำเป็นต้องเป็นคนเดียวกันเสมอ
- การนับรอบสำคัญควรตรวจสอบย้อนหลังได้ว่า:
  - เริ่มเมื่อไร
  - จบเมื่อไร
  - variance เกิดจาก item ใด
  - ปรับยอดเมื่อไร
  - ใคร review

### 6.10 Movement Evidence

movement สำคัญทุกตัวควรมี evidence ขั้นต่ำ เช่น:

- ผู้ทำรายการ
- วันเวลา
- source
- destination
- quantity
- product
- lot/serial ถ้ามี
- reference document
- exception reason ถ้ามี

หลักการนี้สำคัญมาก เพราะเป็นจุดที่ทำให้ Inventory กลายเป็นระบบที่ audit ได้จริง ไม่ใช่แค่หน้าจอเคลื่อนของ

## 7. Boundary กับโดเมนอื่น

### 7.1 Boundary กับ Purchase

`Purchase` รับผิดชอบ:

- procurement intent
- vendor commitment
- approval ก่อนรับของ
- procurement context

`Inventory` รับผิดชอบ:

- receipt execution
- physical stock truth
- location truth
- receipt evidence
- stock accuracy หลังของเข้าหรือ movement ภายใน

Purchase ไม่ควรกลายเป็นที่ถือ truth ว่าของเข้าคลังจริงแล้วหรือยัง

### 7.2 Boundary กับ Sales

`Sales` รับผิดชอบ:

- commercial commitment
- order context
- customer/project context
- billing trigger policy ฝั่ง commercial

`Inventory` รับผิดชอบ:

- delivery execution
- movement evidence
- stock deduction truth
- return intake truth

Sales ไม่ควรเป็นคนถือ truth ว่าของออกจริงแล้วหรือไม่

### 7.3 Boundary กับ Accounting

`Accounting` รับผิดชอบ:

- valuation/accounting posting
- vendor bill
- customer invoice
- tax/account mapping
- payment/reconciliation

`Inventory` รับผิดชอบ:

- movement status
- stock quantity truth
- evidence ที่ทำให้ downstream รู้ว่า movement เกิดขึ้นจริง

Inventory ต้องส่งต่อ `readiness signal` ให้ Accounting ได้ แต่ไม่รับ ownership เรื่อง posting

### 7.4 Boundary กับ Wave 4 Logistics

Wave 4 จะค่อยรับเรื่องเช่น:

- transport orchestration
- stock request extensions
- routing and logistics extensions
- scheduling complexity

Wave 1 - Inventory จึงไม่ควรถูกออกแบบให้ต้องแบก logistics complexity เหล่านี้ตั้งแต่ต้น

## 8. Reporting และ KPI Needs

Wave 1 - Inventory ต้องสร้าง owner value อย่างน้อยในมุมต่อไปนี้:

- `Stock On Hand`
  ปริมาณคงเหลือแยก warehouse/location
- `Movement Backlog`
  incoming, outgoing, internal, และ return movements ที่ยังค้าง
- `Stock Accuracy`
  ภาพรวมของ variance จาก counting
- `Receipt/Delivery Aging`
  movement ที่ค้างผิดปกติ
- `Exception Monitor`
  movement หรือ count ที่ติดปัญหา trace, variance, หรือ exception reason
- `Tracking Visibility`
  แยกสินค้าที่ต้อง lot/serial tracking กับสินค้าทั่วไป

### 8.1 Owner Signals ที่ต้องเห็น

ผู้บริหารควรเห็นอย่างน้อย:

- ของค้างรับ
- ของค้างส่ง
- ของที่วนคืนผิดปกติ
- จุดที่ stock mismatch สูง
- สินค้าหรือคลังที่ทำให้เงินจม
- movement bottleneck ที่ทำให้ operation ช้า

### 8.2 โยงกับมุมโครงการและงานขาย

Inventory ต้องช่วยให้เห็นมุมโครงการ/งานขายได้ในระดับที่เหมาะสม เช่น:

- delivery ของงานโครงการใดค้างอยู่
- receipt อะไรผูกกับ procurement ของงานโครงการ
- return อะไรเกี่ยวกับลูกค้าหรือปลายทางใด

แต่ต้องไม่ย้าย contract logic หรือ revenue logic เข้ามาอยู่ใน Inventory

## 9. Security และ Control Model

อย่างน้อยควรมีบทบาทเชิงหน้าที่ดังนี้:

- `Receiver / Storekeeper`
  ดูแลรับของ, เคลื่อนของ, ยืนยัน movement
- `Delivery Operator`
  ดูแลเตรียมและส่งของออก
- `Count Operator`
  ดูแลการนับ stock
- `Count Reviewer / Approver`
  ตรวจ review variance หรือ adjustment ตาม policy
- `Manager`
  เห็น exception และ KPI ภาพรวม

หลักการ control:

- ผู้ทำ movement กับผู้ review count ไม่จำเป็นต้องเป็นคนเดียวกัน
- stock adjustment สำคัญควรมีร่องรอยการ review
- exception ต้องไม่หายไปจากระบบโดยไม่มีเหตุผล

## 10. Migration Assumptions

- Odoo 15 ใช้เป็น reference ของ flow และ data pattern ไม่ใช่ template ที่ต้องย้ายแบบตรงตัว
- warehouse/location structure เดิมอาจต้องถูกทำความสะอาดก่อนย้าย
- lot/serial เดิมอาจมีข้อมูลไม่สม่ำเสมอ จึงต้องกำหนดกติกากลุ่มสินค้าที่ track ให้ชัด
- movement และ adjustment เดิมอาจมี free-text reasoning ที่ไม่พอสำหรับ model ใหม่
- ถ้าจะย้าย history บางส่วน ต้องตัดสินใจให้ชัดว่าอะไรคือ operationally useful history และอะไรคือ archive-only

## 11. Training Impact

ต้องมี training อย่างน้อย 2 สาย:

- `Movement Operations`
  สำหรับ receipt, delivery, transfer, returns
- `Audit Counting`
  สำหรับ count preparation, count execution, variance review, และ adjustment review

หัวข้อที่ผู้ใช้งานต้องเข้าใจ:

- movement แต่ละแบบต่างกันอย่างไร
- เมื่อไรต้องใช้ lot/serial
- เมื่อไรถือว่า movement เสร็จสมบูรณ์
- count variance ต้องจัดการอย่างไร
- adjustment แบบใดต้อง review

## 12. Test Strategy

อย่างน้อย implementation plan ต้องเตรียม test ดังนี้:

- model tests สำหรับ movement status, traceability, และ lot/serial policy
- workflow tests สำหรับ receipt, delivery, internal transfer, และ returns
- counting tests สำหรับ scheduled count, variance, adjustment, และ review trail
- integration tests ที่ยืนยัน boundary กับ Purchase, Sales, และ Accounting
- reporting/smoke tests สำหรับ KPI หลักและ exception visibility

## 13. Known Unknowns

- warehouse map เดิมจาก Odoo 15 ซับซ้อนแค่ไหน
- return scenarios เชิงธุรกิจมีกรณีพิเศษมากน้อยเพียงใด
- adjustment approval threshold ต้องละเอียดถึงระดับมูลค่าหรือระดับคลังหรือไม่
- lot/serial by need จะถูกตัดสินจาก master data rule แบบใด
- movement evidence บางกรณีต้องใช้ attachment หรือแค่ structured fields ก็พอ

## 14. Definition of Done ระดับสเปก

จะถือว่า child spec นี้พร้อมส่งต่อไปขั้นทำแผน เมื่ออย่างน้อยเงื่อนไขต่อไปนี้ครบ:

- ขอบเขต `receipt`, `delivery`, `internal transfer`, `returns`, และ `counting` ชัด
- baseline `lot/serial by need` ชัด
- `full audit counting` ถูกนิยามเป็น control model ชัด
- boundary กับ `Purchase`, `Sales`, `Accounting`, และ `Wave 4 Logistics` ชัด
- reporting/KPI และ owner signals ชัด
- migration/training assumptions ชัด
- ไม่ขัดกับหลัก `OCA First`, `No core modification`, และ modular install/uninstall safety

## 15. Gate Readiness Summary

### 15.1 Spec-ready

ถือว่า spec-ready เมื่อ:

- movement scope และ count model ได้รับความเห็นชอบ
- ขอบเขตนอกก้อนถูกระบุชัด
- owner signals ขั้นต่ำถูกยืนยันแล้ว

### 15.2 Plan-ready

ถือว่า plan-ready เมื่อ:

- ผู้ใช้ review เอกสารนี้แล้ว
- ไม่มีความกำกวมเรื่อง movement ownership และ count governance
- integration points กับ Purchase, Sales, และ Accounting ถูกระบุพอให้แตกงานได้

### 15.3 Build-ready

ถือว่า build-ready เมื่อ:

- implementation plan ถูกเขียนและอนุมัติ
- addon boundaries และ OCA fit-gap ถูกยืนยัน
- test strategy ถูกแตกเป็นงานย่อยที่ทำได้จริง

## 16. คำตัดสินของ Child Spec นี้

Wave 1 - Inventory ควรถูกออกแบบเป็น `inventory execution and control core` ที่เน้น movement truth และ stock accuracy พร้อมกัน

แนวทางที่เหมาะที่สุดสำหรับ Wave 1 คือ:

- ครอบ movement หลักครบ
- รองรับ returns
- ใช้ `lot/serial` เฉพาะที่จำเป็น
- ใช้ `full audit counting` เป็นแกน control
- รักษา boundary กับ Purchase, Sales, Accounting, และ Wave 4 ให้ชัด

แนวทางนี้ให้สมดุลระหว่าง:

- ความพร้อมใช้งานหน้างาน
- ความน่าเชื่อถือของ stock
- ความสามารถในการตรวจสอบย้อนหลัง
- ความพร้อมในการต่อยอดสู่ accounting handoff และ logistics extensions ใน wave ถัดไป
