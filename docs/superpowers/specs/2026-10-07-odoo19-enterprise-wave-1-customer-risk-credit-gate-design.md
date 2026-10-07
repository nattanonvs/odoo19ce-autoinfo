# Odoo 19 CE Wave 1: Customer Risk and Credit Gate

## Control Metadata
- Child spec ID: W1-CUSTOMER-RISK-CREDIT-GATE
- Wave: Wave 1
- Status: In review
- Owner: Commercial domain lead
- Reviewer: Technical supervisor
- Approvers: Business owner; Technical supervisor
- Canonical path: `docs/superpowers/specs/2026-10-07-odoo19-enterprise-wave-1-customer-risk-credit-gate-design.md`
- Source backlog row: `docs/superpowers/programs/odoo19-enterprise/backlog/domain-wave-matrix.md`
- Date: 2026-10-07
- Primary readers: ฝ่ายขาย, ผู้จัดการฝ่ายขาย, ฝ่ายบัญชี, ผู้อนุมัติ, ผู้บริหาร, ทีมเทคนิค

## Approval Traceability
- ปัญหาธุรกิจนี้ถูกยืนยันจากผู้ใช้เมื่อ 2026-10-07 ว่าปัจจุบันมีการขายเครดิตก่อนผ่านขั้นตอนอนุมัติจริง
- ผู้ใช้ยืนยันให้แยกขอบเขตเป็น 2 ชั้น:
  - Wave 1 ปิด pain point ด้วย risk gate พื้นฐาน
  - Wave 2 ค่อยต่อยอด deep credit controls เช่นวงเงิน, overdue hold, และ exception approval
- ผู้ใช้ยืนยันเพิ่มว่า:
  - ลูกค้า `Blacklist` ต้องถูก block ตั้งแต่ `Quotation` และ `Sales Order`
  - ลูกค้า `Credit Pending` ออก `Quotation` ได้ แต่ต้องใช้เฉพาะเงื่อนไข `เงินสด/โอนก่อน/COD`

## Discovery Evidence
- Current-state references:
  - `docs/superpowers/specs/2026-10-04-odoo19-ce-enterprise-blueprint-design.md`
  - `docs/superpowers/specs/2026-10-04-odoo19-enterprise-wave-1-sales-contract-core-design.md`
  - `docs/superpowers/specs/2026-10-05-odoo19-enterprise-wave-1-contacts-partner-roles-design.md`
  - `docs/superpowers/programs/odoo19-enterprise/backlog/domain-wave-matrix.md`
  - `docs/superpowers/programs/odoo19-enterprise/backlog/domain-spec-index.md`
  - Odoo 15 production reference source: `C:\odoo-dev\odoo19\Odoo15Backup\odoo`
  - Odoo 15 reference mapping file: `C:\odoo-dev\odoo19\Odoo15Backup\odoo15_oca_mapping.xlsx`
- Evidence coverage gaps:
  - ยังไม่มี inventory เอกสารขอเครดิตปัจจุบันแบบ field-by-field จากระบบเดิม
  - ยังไม่มีกติกาเชิงตัวเลขสำหรับวงเงินเครดิต, overdue days, และ exception threshold ที่ผ่านการอนุมัติจากฝ่ายการเงิน
  - ยังไม่มี matrix สิทธิ์อนุมัติแบบรายตำแหน่งสำหรับกรณียกเว้นเครดิต

## Delivery Controls
- Dependencies:
  - Wave 0 governance baseline approved
  - Wave 1 Sales Contract Core baseline approved
  - Wave 1 Contacts baseline approved
  - ต้องรักษา boundary ระหว่าง Sales, Contacts, Accounting, และ Wave 2 Finance Controls ให้ชัด
- Gate readiness:
  - Spec-ready: นิยามสถานะลูกค้า, จุด block, owner ของเครดิต, และการ split ระหว่าง Wave 1 กับ Wave 2 ชัดเจน
  - Plan-ready: รู้ขอบเขต model, security, workflow, document handling, และ validation rules โดยไม่ปน deep finance logic
  - Build-ready: ผู้ใช้ review child spec นี้แล้ว และยืนยันว่า policy การขายสำหรับ `Blacklist` และ `Credit Pending` ถูกต้องตามการใช้งานจริง

## 1. สรุปสั้น ๆ

Child spec นี้ออกแบบ `Customer Risk and Credit Gate` เพื่อหยุดปัญหาเชิงธุรกิจที่สำคัญที่สุดของบริษัทในตอนนี้ คือการที่ฝ่ายขายรับปากขายเครดิตก่อนที่ลูกค้าจะผ่านการตรวจและอนุมัติจากฝ่ายบัญชีจริง

future-state ที่ต้องการคือ:

- ลูกค้า `Blacklist` ต้องถูก block ตั้งแต่ `Quotation` และ `Sales Order`
- ลูกค้า `Credit Pending` ยังขายได้เฉพาะ `เงินสด/โอนก่อน/COD`
- ลูกค้า `Credit Approved` เท่านั้นที่ขายแบบเครดิตได้
- ฝ่ายบัญชีเป็น owner ของสถานะเครดิต
- ฝ่ายขายมีสิทธิ์เริ่มคำขอเครดิต แต่ไม่มีสิทธิ์อนุมัติเครดิตเอง

ก้อนนี้ตั้งใจเป็น `Wave 1 guardrail` เพื่อปิด pain point ที่กระทบความน่าเชื่อถือของบริษัททันที ส่วน deep credit controls เช่นวงเงิน, overdue hold, และ exception approval เชิงตัวเลข ให้ย้ายไป `Wave 2`

## 2. เป้าหมายของ Child Spec นี้

- หยุดการขายให้ลูกค้า `Blacklist` ตั้งแต่ต้นทาง
- หยุดการขายเครดิตก่อนผ่าน approval ที่ถูกต้อง
- แยกสิทธิ์และความรับผิดชอบของ `Sales` กับ `Accounting` ให้ชัด
- ทำให้ฝ่ายขายสื่อสารกับลูกค้าได้ตรงกับสิทธิ์จริงของลูกค้า ณ เวลานั้น
- วางฐานข้อมูล partner risk state ที่ต่อยอดไป `Wave 2` ได้โดยไม่ต้องรื้อใหม่
- รักษา bounded context ของ `Sales`, `Contacts`, และ `Accounting` ไม่ให้กลายเป็นโมดูลรวมทุกอย่าง

## 3. ขอบเขตของ Child Spec

### 3.1 สิ่งที่อยู่ใน Wave 1

- สถานะความเสี่ยงลูกค้าขั้นพื้นฐาน เช่น `Blacklist` และ `Not Blacklisted`
- สถานะคำขอเครดิต เช่น `Not Requested`, `Credit Pending`, `Credit Approved`, `Credit Rejected`
- จุด block ที่ `Quotation` และ `Sales Order`
- กติกาว่า `Credit Pending` ใช้ได้เฉพาะเงื่อนไข non-credit
- workflow การเริ่มคำขอเครดิตจากฝ่ายขายและการตรวจ/อนุมัติโดยฝ่ายบัญชี
- การเก็บเอกสารและ activity ขั้นพื้นฐานที่ใช้ตามงานขอเครดิต
- reporting และ KPI ขั้นต่ำสำหรับ owner และผู้จัดการที่ต้องเห็นสถานะคำขอเครดิต

### 3.2 สิ่งที่ defer ไป Wave 2

- `credit limit`
- `overdue hold`
- `dunning / receivable escalation`
- `exception approval` ตามวงเงินหรือระดับความเสี่ยง
- analytics เชิงการเงินขั้นลึก เช่น exposure, overdue aging by approval class, และเครดิตคงเหลือ

### 3.3 สิ่งที่ยังไม่ลงลึกในก้อนนี้

- scoring model เชิงการเงินแบบซับซ้อน
- integration กับบริษัทข้อมูลเครดิตภายนอก
- legal document automation หรือ e-sign สำหรับ credit agreement
- reconciliation หรือ account posting ทางบัญชี
- workflow การขายกรณีพิเศษนอกนโยบายที่ยังไม่ได้อนุมัติ governance

## 4. Current-State Summary

ปัจจุบันปัญหาหลักไม่ได้อยู่ที่ระบบออกเอกสารไม่ได้ แต่เกิดจากการที่:

- ฝ่ายขายสามารถเดินงานขายเร็วกว่ากระบวนการขอเครดิต
- การให้เครดิตจริงในทางปฏิบัติไม่ได้ถูกถือสิทธิ์โดยฝ่ายบัญชีอย่างเด็ดขาด
- ลูกค้าบางรายถูกแจ้งหรือถูกคาดหวังว่า “ขายเครดิตได้” ก่อนสถานะจะได้รับอนุมัติจริง
- เมื่อคำสั่งขายเกิดขึ้นแล้ว ฝ่ายบัญชีค่อยมารับรู้และพยายามแก้ทีหลัง ซึ่งสายเกินไป

ผลเสียทางธุรกิจคือ:

- บริษัทดูเหมือนรับปากเกินจริงหรือกลับคำกับลูกค้า
- เกิดความขัดแย้งระหว่างฝ่ายขายกับฝ่ายบัญชี
- ความเสี่ยงหนี้เสียถูกปล่อยให้เกิดก่อนระบบควบคุมทำงาน
- owner มองไม่เห็นสถานะคำขอเครดิตและความเสี่ยงที่กำลังก่อตัวล่วงหน้า

## 5. Keep / Refactor / Replace / Retire

### 5.1 Keep

- Keep `res.partner` เป็น canonical customer master
- Keep การใช้ `sale.order` เป็นเอกสารหลักของ Quotation และ Sales Order
- Keep แนวคิดที่ฝ่ายขายเป็นเจ้าของความสัมพันธ์กับลูกค้า แต่ไม่เป็น owner ของเครดิต

### 5.2 Refactor

- Refactor การสร้างลูกค้าใหม่จาก “ลูกค้าพร้อมขายทุกเงื่อนไข” ไปเป็น `Prospect / Pending Review`
- Refactor ขั้นตอนขอเครดิตให้กลายเป็น explicit workflow ที่ track ได้
- Refactor สิทธิ์การสื่อสารเรื่องเครดิตจากการตกลงปากเปล่าไปเป็นสถานะในระบบ

### 5.3 Replace

- Replace การขอเครดิตย้อนหลังหลังจากรับออเดอร์แล้ว ด้วย `approval-before-credit-sale`
- Replace การตรวจ blacklist แบบจำหรือรู้กันเอง ด้วย partner risk status ที่ block ได้ในระบบ

### 5.4 Retire

- Retire แนวคิดที่ฝ่ายขายอนุมัติเครดิตแทนบัญชีได้โดยพฤตินัย
- Retire การปล่อยให้ลูกค้า `Credit Pending` ใช้ payment term แบบเครดิต
- Retire การรับงานขายจากลูกค้า `Blacklist` แล้วค่อยแก้ภายหลัง

## 6. Future-State Functional Design

### 6.1 Partner Risk States

สำหรับ Wave 1 ให้แยก state สำคัญอย่างน้อย 2 มิติ:

- `Blacklist Status`
  - `normal`
  - `blacklisted`
- `Credit Request State`
  - `not_requested`
  - `pending`
  - `approved`
  - `rejected`

นอกจากนี้ควรมี field คำนวณเชิงธุรกิจอีกตัวที่อ่านง่ายสำหรับโดเมนขาย เช่น:

- `od19_credit_sale_allowed`
  - `true` เมื่อเครดิตได้รับอนุมัติและพร้อมใช้งาน
  - `false` ในทุกกรณีอื่น

แนวทางนี้ทำให้ระบบตอบคำถามได้ชัดว่า:

- ลูกค้ารายนี้ห้ามขายเลยหรือไม่
- ลูกค้ารายนี้ขายได้ แต่ต้องขายแบบเงินสดเท่านั้นหรือไม่
- ลูกค้ารายนี้ขายแบบเครดิตได้แล้วหรือยัง

### 6.2 Customer Lifecycle ในเชิงการค้า

future-state ของลูกค้าใหม่ควรเป็นดังนี้:

1. ฝ่ายขายสร้าง partner เป็น `Prospect`
2. ระบบถือว่าลูกค้ารายนี้ยังไม่มีสิทธิ์เครดิต
3. หากลูกค้าต้องการเครดิต ฝ่ายขายกด `Request Credit`
4. ฝ่ายบัญชีส่งเอกสารขอเครดิตให้ลูกค้า
5. ลูกค้าส่งเอกสารกลับ
6. ฝ่ายบัญชีตรวจเอกสารและตัดสินผล
7. ถ้าอนุมัติ จึงเปิดสิทธิ์ขายเครดิต
8. ถ้าไม่อนุมัติ ให้กลับไปขายแบบ non-credit เท่านั้น

### 6.3 Rules Matrix

#### ลูกค้า Blacklisted

- ห้ามสร้าง `Quotation`
- ห้ามยืนยัน `Sales Order`
- ผู้ใช้ต้องเห็นเหตุผลว่า block เพราะสถานะ `Blacklist`

#### ลูกค้า Credit Pending

- ออก `Quotation` ได้
- ใช้ได้เฉพาะ payment term แบบ `เงินสด/โอนก่อน/COD`
- ห้ามยืนยัน `Sales Order` ถ้าเอกสารนั้นใช้ payment term แบบเครดิต

#### ลูกค้า Credit Approved

- ออก `Quotation` ได้
- ออก `Sales Order` ได้
- ใช้ payment term แบบเครดิตได้ตาม policy ที่เปิดให้ใน Wave 1

#### ลูกค้า Credit Rejected

- ออก `Quotation` ได้
- ใช้ได้เฉพาะ payment term แบบ `เงินสด/โอนก่อน/COD`
- ห้ามขายแบบเครดิตจนกว่าจะมีคำขอใหม่และผ่าน approval

### 6.4 Quotation Control

ใน Wave 1 ระบบต้องควบคุม `Quotation` ดังนี้:

- ถ้า partner เป็น `blacklisted` ระบบต้อง block การสร้างหรือยืนยันเอกสารขายตั้งแต่ระดับ Quotation
- ถ้า partner อยู่ใน `pending` หรือ `rejected` และ payment term เป็นเครดิต ระบบต้อง block และอธิบายเหตุผลอย่างชัดเจน
- ถ้า partner ยังไม่ `approved` ฝ่ายขายยังสามารถเดิน Quotation ได้ แต่ต้องใช้เงื่อนไข non-credit เท่านั้น

หลักการสำคัญคือ:

- Quotation ยังเป็นเครื่องมือการขายได้
- แต่ห้ามใช้ Quotation เพื่อสร้างความเข้าใจผิดว่าบริษัทอนุมัติเครดิตแล้ว

### 6.5 Sales Order Control

`Sales Order` ต้องเข้มกว่าระดับ Quotation เพราะเป็นจุดที่เริ่ม commitment เชิงธุรกิจจริง

สำหรับ Wave 1:

- `Blacklisted` ต้องถูก block เสมอ
- `Credit Pending` ต้องถูก block ถ้า payment term เป็นเครดิต
- `Credit Approved` จึงจะผ่านได้ในกรณี credit sale

ถ้าเอกสารยังเป็น cash/prepaid/COD และ policy อื่นไม่ห้ามไว้ ระบบสามารถอนุญาตให้ไปต่อได้

### 6.6 Credit Request Workflow Ownership

workflow ฝั่งเครดิตต้องแยก owner ให้ชัด:

- `Sales`
  - สร้าง partner
  - เริ่มคำขอเครดิต
  - ติดตามลูกค้า
  - เห็นสถานะ แต่อนุมัติไม่ได้
- `Accounting`
  - ส่งเอกสาร
  - ตรวจเอกสาร
  - อนุมัติหรือปฏิเสธเครดิต
  - บันทึกหมายเหตุการพิจารณา

ในเชิงระบบ ฝั่งบัญชีควรเป็น role เดียวที่แก้สถานะจาก `pending` ไป `approved` หรือ `rejected` ได้

### 6.7 Document and Evidence Handling

Wave 1 ไม่จำเป็นต้องทำ document engine แบบซับซ้อน แต่ต้องมี baseline ที่ใช้ตามงานได้จริง:

- partner ต้องเก็บไฟล์แนบที่เกี่ยวกับการขอเครดิตได้
- ระบบต้องรองรับการสร้าง activity หรือ checklist ขั้นพื้นฐานให้บัญชีตามงานได้
- การอนุมัติต้องมี note อย่างน้อยว่าใครอนุมัติ เมื่อไร และมีข้อสังเกตอะไร

### 6.8 Exception Model

Wave 1 ไม่ควรเปิด exception model เชิงลึก เพราะจะทำให้ policy กลับมาหลวมอีกครั้ง

ดังนั้น baseline ของ Wave 1 คือ:

- ยังไม่สนับสนุน exception approval แบบเปิดกว้าง
- ถ้ามีกรณีพิเศษ ให้เก็บเป็น management override นอก flow ปกติ และต้องมีผู้มีอำนาจอนุมัติเป็นลายลักษณ์อักษร
- exception engine ที่เป็นระบบให้ย้ายไป `Wave 2`

## 7. Recommended Data Model

### 7.1 `res.partner`

field เชิงฟังก์ชันที่ควรมีอย่างน้อย:

- `od19_blacklist_status`
- `od19_blacklist_reason`
- `od19_credit_request_state`
- `od19_credit_sale_allowed`
- `od19_credit_requested_by`
- `od19_credit_review_owner_id`
- `od19_credit_review_date`
- `od19_credit_review_note`
- `property_payment_term_id` หรือ field ที่ใช้กำหนด default payment term ตามนโยบายที่อนุมัติ

### 7.2 `sale.order`

field เชิงฟังก์ชันที่ควรมีหรือคำนวณแสดง:

- current customer risk snapshot
- current credit state snapshot
- blocked reason ถ้าเอกสารถูกห้ามดำเนินต่อ
- indicator ว่าเอกสารนี้เป็น `credit sale` หรือ `non-credit sale`

### 7.3 Optional helper object

ถ้า implementation ต้องการความชัดเจนเชิง workflow สามารถมี helper object เช่น `customer credit request` แยกจาก partner ได้ แต่ child spec นี้ยังไม่บังคับว่าต้องมี model แยก หาก Odoo activity + partner fields เพียงพอใน Wave 1

หลักสำคัญคือ:

- partner เป็น source of truth ของสิทธิ์ขาย
- helper object เป็นเพียงที่เก็บ history ของคำขอ ถ้ามี

## 8. Security and Approval Model

- `Sales user`
  - create/edit partner ขั้นต้นได้
  - request credit ได้
  - อ่านสถานะเครดิตได้
  - แก้ผลอนุมัติไม่ได้
- `Accounting user`
  - อ่านและจัดการคำขอเครดิตได้
  - เปลี่ยนสถานะจาก `pending` เป็น `approved` หรือ `rejected` ได้
  - แก้ blacklist status ได้ตามสิทธิ์ที่กำหนด
- `Manager / technical override`
  - ใช้เฉพาะกรณีนโยบายกำหนดให้มีผู้อนุมัติพิเศษ

field ที่มีผลต่อการอนุญาตขาย เช่น blacklist และ credit approval ต้องไม่เปิดให้ฝ่ายขายแก้เองได้

## 9. Reporting and KPI Needs

owner-facing reporting ขั้นต่ำที่ควรมี:

- จำนวนลูกค้า `Credit Pending`
- อายุเฉลี่ยของคำขอเครดิตที่ยังไม่ปิด
- จำนวน `Quotation` ที่ถูก block เพราะ `Blacklist`
- จำนวน `Quotation/Sales Order` ที่ถูก block เพราะยังไม่ผ่านเครดิต
- จำนวนลูกค้า `Credit Rejected`

รายงานเหล่านี้ต้องช่วยตอบคำถามของผู้บริหารได้ว่า:

- pipeline ที่กำลังติดเพราะเครดิตมีมากแค่ไหน
- ทีมขายกำลังเจอ bottleneck ที่ขั้นตอนขอเครดิตหรือไม่
- มีความเสี่ยงด้านลูกหนี้ที่กำลังถูกกันไว้ได้ทันเวลาหรือไม่

## 10. Wave Split and Bounded Context

### 10.1 สิ่งที่อยู่ใน Wave 1 แน่นอน

- blacklist gate
- pending-credit cash-only rule
- approval ownership by accounting
- partner risk status
- sales document validation
- basic credit request workflow

### 10.2 สิ่งที่ต้องไป Wave 2

- credit limit
- overdue stop rules
- receivable-based credit hold
- approval tiers ตามวงเงิน
- exception workflow ที่เป็นระบบ
- advanced finance analytics

### 10.3 เหตุผลของการ split

การ split แบบนี้ทำให้:

- Wave 1 ปิด pain point ที่เสียความน่าเชื่อถือกับลูกค้าได้เร็ว
- Wave 1 ไม่บวมจนกลายเป็น accounting redesign แฝง
- Wave 2 ยังมีพื้นที่ชัดเจนสำหรับ finance controls ที่ต้องใช้การอนุมัติจากฝ่ายการเงินมากกว่าเดิม

## 11. Migration Assumptions

- ข้อมูล blacklist เดิมอาจต้องถูก clean และ normalize ก่อนย้ายเข้า state ใหม่
- ลูกค้าที่มีประวัติขอเครดิตค้างในระบบเดิมอาจต้อง map เป็น `pending` หรือ `approved` ตามเอกสารประกอบที่มีจริง
- ถ้าไม่มีหลักฐานเครดิตที่สมบูรณ์ ให้ default ไปที่ `non-credit sale`
- ห้ามตีความว่าลูกค้าเก่าทุกรายเป็น `Credit Approved` โดยอัตโนมัติ

## 12. Training Impact

ทีมที่ได้รับผลกระทบโดยตรง:

- ฝ่ายขาย
- ผู้จัดการฝ่ายขาย
- ฝ่ายบัญชี
- ผู้อนุมัติ

หัวข้ออบรมขั้นต่ำ:

- ความต่างระหว่าง `Prospect`, `Pending`, `Approved`, และ `Rejected`
- สิ่งที่ฝ่ายขายพูดได้และพูดไม่ได้กับลูกค้าเรื่องเครดิต
- วิธีเริ่มคำขอเครดิต
- วิธีที่บัญชีปิดคำขอเครดิต
- วิธีอ่านข้อความ block ใน Quotation และ Sales Order

## 13. Build Guidance for the Next Plan

เมื่อแตก implementation plan ให้ยึดหลักดังนี้:

- partner state เป็นศูนย์กลางของสิทธิ์ขาย
- sales document เป็นจุดบังคับ
- accounting เป็น owner ของ credit decision
- ห้ามยัด credit limit และ overdue logic เข้ามาใน Wave 1 implementation
- ออกแบบโมดูลให้ติดตั้ง/ถอนออกได้โดยไม่แตะ Odoo core

## 14. Final Recommendation

recommendation ของ child spec นี้คือ:

- ใส่ `Customer Risk and Credit Gate` เป็น baseline เสริมของ `Wave 1 commercial core`
- ให้มองมันเป็น `commercial guardrail` มากกว่า `finance engine`
- ใช้ `Wave 2` เป็นบ้านของ credit controls เชิงตัวเลขและ exception governance

ถ้าทำตามนี้ บริษัทจะหยุดปัญหา “ขายก่อนอนุมัติ” ได้เร็วที่สุด โดยไม่ทำให้ขอบเขตของ Wave 1 แตกกระจายหรือซ้อนกับโดเมนบัญชีเกินความจำเป็น
