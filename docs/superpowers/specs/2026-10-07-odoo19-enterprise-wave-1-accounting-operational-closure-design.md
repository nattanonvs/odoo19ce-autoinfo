# Odoo 19 CE Wave 1: Accounting Operational Closure

## Control Metadata
- Child spec ID: W1-ACCOUNTING-OP-CLOSURE
- Wave: Wave 1
- Status: Approved design baseline
- Owner: Accounting domain lead
- Reviewer: Technical supervisor
- Approvers: Business owner; Technical supervisor
- Target edition: Odoo 19 Community Edition (CE)
- Canonical path: `docs/superpowers/specs/2026-10-07-odoo19-enterprise-wave-1-accounting-operational-closure-design.md`
- Historical filename note: the filename/path still contains `enterprise` for continuity with earlier planning artifacts; the approved product target is Odoo 19 CE, not Odoo Enterprise.
- Source backlog row: `docs/superpowers/programs/odoo19-enterprise/backlog/domain-wave-matrix.md`
- Date: 2026-10-07
- Primary readers: ฝ่ายบัญชี, ฝ่ายขาย, ฝ่ายจัดซื้อ, ฝ่ายคลัง, ผู้บริหาร, ผู้อนุมัติ, ทีมเทคนิค

## Approval Traceability
- ผู้ใช้อนุมัติ child spec ก่อนหน้าเรื่อง `Customer Risk and Credit Gate` แล้ว และสั่งให้เริ่ม `Wave 1 - Accounting` ต่อทันทีเมื่อ 2026-10-07
- ผู้ใช้ยืนยันให้ใช้ขอบเขต `Mixed Core` สำหรับ Accounting ใน Wave 1
- ผู้ใช้ยืนยันให้รองรับ `Full Cash Cycle`
- ผู้ใช้ยืนยันว่าความสำเร็จหลักของก้อนนี้คือ `Operational Closure`
- แนวทางที่ได้รับอนุมัติคือแยก child spec นี้เป็น 3 แกนในก้อนเดียว:
  - `AR Closure`
  - `AP Closure`
  - `Cash and Reconciliation Baseline`

## Discovery Evidence
- Current-state references:
  - `docs/superpowers/specs/2026-10-04-odoo19-ce-enterprise-blueprint-design.md`
  - `docs/superpowers/specs/2026-10-04-odoo19-enterprise-wave-1-sales-contract-core-design.md`
  - `docs/superpowers/specs/2026-10-05-odoo19-enterprise-wave-1-contacts-partner-roles-design.md`
  - `docs/superpowers/specs/2026-10-06-odoo19-enterprise-wave-1-purchase-procurement-core-design.md`
  - `docs/superpowers/specs/2026-10-07-odoo19-enterprise-wave-1-inventory-execution-control-design.md`
  - `docs/superpowers/specs/2026-10-07-odoo19-enterprise-wave-1-customer-risk-credit-gate-design.md`
  - `docs/superpowers/plans/2026-10-04-odoo19-ce-enterprise-blueprint-master-plan.md`
  - Odoo 15 production reference source: `C:\odoo-dev\odoo19\Odoo15Backup\odoo`
  - Odoo 15 reference mapping file: `C:\odoo-dev\odoo19\Odoo15Backup\odoo15_oca_mapping.xlsx`
- Evidence coverage gaps:
  - ยังไม่มี current-state inventory เชิงลึกของ account chart, tax configuration, journal policy, และ payment workflow จากระบบเดิมแบบ field-by-field
  - ยังไม่มีหลักฐานยืนยันเต็มรูปแบบของ reconciliation policy เดิม, write-off policy, และ cash/bank exception handling
  - ยังไม่มีรายการรายงาน owner-facing finance reports จาก Odoo 15 ที่ผ่านการคัดว่า `Keep/Refactor/Retire` ครบทุกฉบับ

## Delivery Controls
- Dependencies:
  - Wave 0 governance baseline approved
  - Wave 1 Sales Contract Core baseline approved
  - Wave 1 Contacts baseline approved
  - Wave 1 Purchase Procurement Core baseline approved
  - Wave 1 Inventory baseline approved at design level and used as operational boundary for accounting handoff
  - Wave 1 Customer Risk and Credit Gate baseline approved at design level
  - ต้องรักษา boundary ระหว่าง Accounting กับ Wave 2 finance controls ให้ชัด
- Gate readiness:
  - Spec-ready: นิยาม AR, AP, cash, reconciliation, posting baseline, และ owner KPIs ชัดโดยไม่ปน deep finance controls
  - Plan-ready: ขอบเขต addon/model/report/security/integration points ชัด และรู้ว่าอะไรอยู่ใน Wave 1 หรือ defer ไป Wave 2
  - Build-ready: ผู้ใช้อนุมัติ child spec นี้แล้วในระดับ design baseline และยืนยันว่า accounting baseline นี้เพียงพอสำหรับปิด commercial core ของ Wave 1

## 1. สรุปสั้น ๆ

Child spec นี้ออกแบบ `Accounting` สำหรับ Wave 1 ให้เป็นก้อน `Operational Closure` ที่ทำให้ธุรกรรมหลักของบริษัทเดินครบเส้นจากโดเมนต้นทางเข้าสู่บัญชี โดยครอบพร้อมกันทั้ง:

- `AR Closure`
- `AP Closure`
- `Cash and Reconciliation Baseline`
- `Posting and Tax Baseline`
- `Owner-facing finance closure KPIs`

จุดยืนสำคัญของก้อนนี้คือ:

- ไม่ทำ Accounting ให้เป็นเพียงที่ปลายทางรับเอกสารแบบเดาเอา
- ไม่ปล่อยให้ Sales, Purchase, และ Inventory ส่งสถานะที่คลุมเครือเข้ามา
- ไม่ดึง deep finance control จาก Wave 2 เข้ามาปนจนก้อนนี้บวมเกินจำเป็น

พูดง่าย ๆ คือ Wave 1 - Accounting ต้องทำให้บริษัทตอบได้จริงว่า:

- อะไรพร้อมออก invoice แล้ว
- อะไรพร้อมรับ vendor bill แล้ว
- อะไรรับเงินแล้วหรือจ่ายเงินแล้ว
- อะไร reconcile แล้วหรือยัง
- ลูกหนี้ เจ้าหนี้ และเงินสดที่ยังค้างอยู่มีสถานะอย่างไร

## 2. เป้าหมายของ Child Spec นี้

- ปิดเส้นทาง `Sales -> Billing readiness -> Customer Invoice -> Payment -> Reconciliation`
- ปิดเส้นทาง `Purchase/Receipt -> Vendor Bill -> Payment -> Reconciliation`
- ทำให้ posting และ tax baseline ของธุรกรรมหลักมีทิศทางที่ชัดและสม่ำเสมอ
- ทำให้สถานะ handoff จาก Sales, Purchase, และ Inventory เข้าบัญชีไม่ต้องตีความจาก memo หรือ free text
- ทำให้ owner มองเห็นสถานะ `billable backlog`, `open receivable`, `open payable`, และ `cash application status`
- รักษา boundary ว่า `Wave 2` ยังเป็นบ้านของ controls เชิงลึก เช่น credit limits, overdue hold, approval tiers, และ exception governance

## 3. ขอบเขตของ Child Spec

### 3.1 สิ่งที่อยู่ใน Wave 1

- `AR Closure`
  - customer invoice baseline
  - customer payment baseline
  - receivable reconciliation baseline
- `AP Closure`
  - vendor bill baseline
  - vendor payment baseline
  - payable reconciliation baseline
- `Cash and Reconciliation Baseline`
  - register payment / receive payment
  - bank or cash journal baseline
  - partial/full reconciliation ในกรณีใช้งานทั่วไป
- `Posting and Tax Baseline`
  - account mapping ขั้นจำเป็น
  - tax mapping ขั้นจำเป็น
  - journal posting สำหรับเอกสารหลัก
- `Operational Handoff`
  - readiness signal จาก Sales, Purchase, Inventory
  - document states ที่ใช้ส่งงานเข้าบัญชี
- `Owner KPI and Reporting`
  - รายงานขั้นต่ำที่ช่วยปิด commercial core ของ Wave 1

### 3.2 สิ่งที่ defer ไป Wave 2

- credit limit และ customer credit exposure controls
- overdue hold และ receivable escalation rules
- cheque controls แบบเชิงลึก
- advance flows แบบเต็มรูปแบบ
- approval tiers สำหรับ finance exceptions
- treasury/control dashboard ขั้นลึก
- write-off governance ขั้นสูงและ exception reconciliation policy หลายชั้น

### 3.3 สิ่งที่ยังไม่ลงลึกในก้อนนี้

- statutory localization เชิงลึกเกินกว่าที่จำเป็นต่อ baseline
- consolidation หรือ intercompany accounting
- fixed asset, deferred revenue, หรือ budgeting engine
- financial planning and analysis platform
- collection workflow แบบหลายขั้นและหลายทีม
- tax engine พิเศษนอก baseline มาตรฐานที่จำเป็นต่อธุรกิจจริง

## 4. Current-State Summary

จาก baseline ที่ออกแบบและพัฒนาไปแล้ว:

- `Sales` เริ่มตอบโจทย์ commercial context, contract policy, billing trigger, และ evidence readiness
- `Customer Risk and Credit Gate` เริ่มคุมสิทธิ์ขายและปิด pain point เรื่องขายเครดิตก่อนอนุมัติ
- `Purchase` เริ่มแยก procurement intent, approval, และ readiness ของ line semantics
- `Inventory` เริ่มเป็นแหล่ง truth ของ movement และ counting

แต่ถ้ายังไม่มี Accounting child spec ที่ชัด จะเกิดปัญหาต่อเนื่องทันที:

- รายการที่ `พร้อมวางบิล` ในฝั่ง Sales จะไม่รู้ว่าควรเข้า invoice อย่างไร
- receipt และ service acceptance จาก Purchase จะไม่รู้ว่าพร้อมรับ vendor bill แค่ไหน
- movement truth จาก Inventory จะไม่รู้ว่ากระทบ invoice, bill, และ payment follow-up อย่างไร
- ผู้บริหารจะเห็นเพียง activity ทางการค้า แต่ไม่เห็นการปิด loop ทางการเงินจริง

ดังนั้น Accounting ของ Wave 1 ต้องทำหน้าที่เป็น `closure layer` ของ commercial core ไม่ใช่แค่จุดลงบัญชีอย่างเดียว

## 5. Keep / Refactor / Replace / Retire

### 5.1 Keep

- Keep โครงมาตรฐานของ Odoo ด้าน `account`, `account.move`, `payment`, และ reconciliation เป็น baseline
- Keep หลัก `OCA First, Custom Second`
- Keep boundary ว่า Sales, Purchase, Inventory เป็นเจ้าของต้นทางของธุรกรรม ส่วน Accounting เป็นเจ้าของ accounting truth

### 5.2 Refactor

- Refactor การส่งต่องานเข้าบัญชีจากการตีความหน้างาน ไปเป็น readiness signals ที่ชัด
- Refactor การติดตามลูกหนี้และเจ้าหนี้จากรายงานแยกส่วน ไปเป็นภาพ closure ที่เชื่อมกับธุรกรรมต้นทาง
- Refactor การมอง payment เป็นเพียงการบันทึกรับ/จ่าย ไปเป็นส่วนหนึ่งของ closure status

### 5.3 Replace

- Replace การรับรู้ invoice/bill readiness จากคำบอกเล่าหรือไฟล์แนบกระจัดกระจาย ด้วยสถานะที่ตรวจสอบได้
- Replace การปล่อยให้ cash application และ reconciliation เป็นงานตามหลังแบบไม่มี baseline ด้วยขั้นตอนมาตรฐานที่วัดผลได้

### 5.4 Retire

- Retire แนวคิดที่ให้ Accounting ต้องเดา intent ของเอกสารจาก free text
- Retire การปิดบัญชีเชิงปฏิบัติการแบบไม่มี owner KPI ที่เชื่อมกับธุรกิจ
- Retire การยัด deep finance controls ทั้งหมดเข้ามาใน Wave 1 จนขอบเขตแตก

## 6. Future-State Design

### 6.1 Accounting as Operational Closure

Wave 1 - Accounting ต้องถูกออกแบบเป็น `operational closure core` ซึ่งหมายความว่า:

- ธุรกรรมต้นทางต้องส่งเข้าบัญชีได้อย่างมีความหมาย
- Accounting ต้องรู้ว่าเอกสารไหนพร้อมรับช่วงต่อ
- Accounting ต้องปิดวงจรไปถึง payment และ reconciliation ขั้น baseline ได้
- ผู้บริหารต้องเห็นสถานะเปิด/ปิดของเงินที่เกี่ยวกับธุรกรรมหลัก

Accounting ใน Wave 1 จึงไม่ใช่แค่ `posting layer` และไม่ใช่ `finance control engine` เต็มรูปแบบ แต่เป็นสะพานที่ทำให้ commercial core ปิด loop ได้จริง

### 6.2 AR Closure Baseline

ฝั่งลูกหนี้ต้องรองรับอย่างน้อย:

- การรับ handoff จาก `Ready to Bill` หรือ signal ที่เทียบเท่า
- การสร้าง `Customer Invoice`
- การติดตามสถานะ invoice เช่น draft, posted, paid, partially paid
- การรับชำระเงินจากลูกค้า
- การทำ reconciliation ขั้น baseline ระหว่าง invoice กับ payment

หลักการสำคัญ:

- Sales เป็นเจ้าของ commercial truth ว่ารายการพร้อมวางบิลหรือยัง
- Accounting เป็นเจ้าของ invoice truth ว่าออก invoice, รับเงิน, และ reconcile แล้วหรือยัง
- customer risk gate ส่งผลต่อการขายก่อน invoice แต่ไม่ควรทำให้ Accounting ต้องกลับไปตัดสินเชิงการค้าแทน Sales

### 6.3 AP Closure Baseline

ฝั่งเจ้าหนี้ต้องรองรับอย่างน้อย:

- การรับ handoff จาก Purchase และ Inventory ว่าเอกสารใดพร้อมรับ bill หรือพร้อมตรวจรับบริการ
- การสร้าง `Vendor Bill`
- การติดตามสถานะ bill เช่น draft, posted, paid, partially paid
- การจ่ายเงินให้ vendor
- การทำ reconciliation ขั้น baseline ระหว่าง bill กับ payment

หลักการสำคัญ:

- Purchase เป็นเจ้าของ commitment กับ vendor
- Inventory เป็นเจ้าของ goods receipt truth สำหรับสินค้า
- Accounting เป็นเจ้าของ vendor bill truth, payment truth, และ payable closure

### 6.4 Cash and Reconciliation Baseline

ใน Wave 1 ให้ถือว่าการรับเงิน/จ่ายเงินและ reconciliation เป็นส่วนหนึ่งของ baseline จริง แต่ต้องคุมให้อยู่ระดับปฏิบัติการหลัก ไม่ใช่ระดับ exception engine

ขอบเขตขั้นต่ำ:

- รับเงินลูกหนี้ได้
- จ่ายเงินเจ้าหนี้ได้
- รองรับ payment journals ขั้นพื้นฐาน
- ทำ partial/full reconciliation ได้ในกรณีทั่วไป
- แสดงสถานะคงค้างที่ owner และผู้ปฏิบัติงานเข้าใจได้

สิ่งที่ยังไม่ลงลึก:

- multi-step approval สำหรับ payment exceptions
- advanced bank operations
- cheque control เชิงลึก
- collection strategy แบบหลายชั้น

### 6.5 Posting and Tax Baseline

Wave 1 ต้องกำหนด baseline ให้ชัดอย่างน้อยในเรื่อง:

- account mapping ขั้นจำเป็นสำหรับ invoice, bill, payment
- tax mapping ขั้นจำเป็นของธุรกรรมหลัก
- journal policy ขั้นจำเป็น
- ความสม่ำเสมอของการ post เอกสารหลัก

ก้อนนี้ไม่จำเป็นต้องออกแบบทุกกรณีทางบัญชีอย่าง exhaustive แต่ต้องตอบได้ว่า:

- ธุรกรรมขายลงบัญชีทิศทางใด
- ธุรกรรมซื้อและเจ้าหนี้ลงบัญชีทิศทางใด
- payment และ reconciliation ปิดเอกสารอย่างไร

### 6.6 Handoff Matrix Between Domains

#### Sales -> Accounting

Sales ต้องส่งต่ออย่างน้อย:

- commercial customer
- project or contract context ถ้ามีผลต่อการรายงาน
- billing trigger readiness
- evidence status
- payment term ที่ใช้จริง

Accounting ต้องรับช่วงต่อเพื่อ:

- ออก customer invoice
- ติดตาม receivable
- รับเงินและ reconcile

#### Purchase -> Accounting

Purchase ต้องส่งต่ออย่างน้อย:

- vendor
- procurement intent
- line semantics ที่เกี่ยวกับงานภายในหรือโครงการ
- purchase commitment status

Accounting ต้องรับช่วงต่อเพื่อ:

- รับ vendor bill
- ตรวจ payable baseline
- จ่ายเงินและ reconcile

#### Inventory -> Accounting

Inventory ต้องส่งต่ออย่างน้อย:

- receipt truth
- delivery truth ในจุดที่สัมพันธ์กับ billing readiness
- returns consequence baseline
- movement evidence ที่มีผลต่อ invoice/bill readiness

Accounting ต้องใช้ข้อมูลนี้เพื่อ:

- ไม่ออกเอกสารสวนกับ physical truth
- เห็นผลของ return ต่อ invoice/bill follow-up
- แยก accounting truth ออกจาก movement truth โดยไม่ขัดกัน

### 6.7 Returns Consequence Baseline

Wave 1 ต้องอธิบายผลกระทบทางบัญชีของ return อย่างน้อยในระดับ operational meaning:

- `customer return`
  - อาจกระทบ invoice follow-up, credit note decision, หรือ open receivable review
- `return to vendor`
  - อาจกระทบ vendor bill follow-up, debit note/credit handling, หรือ open payable review

child spec นี้ยังไม่บังคับเอกสารบัญชีทุกชนิดของ return แต่ต้องล็อกว่า Accounting ต้องเห็น return consequence อย่างชัด ไม่ใช่ปล่อยให้เป็นเรื่องของคลังล้วน ๆ

### 6.8 Payment Terms and Credit Baseline

Wave 1 ต้องเชื่อมกับ `Customer Risk and Credit Gate` โดยใช้หลักดังนี้:

- payment term ที่ใช้บนเอกสารขายต้องสอดคล้องกับสิทธิ์เครดิตของ partner
- customer invoice ต้องสะท้อนเงื่อนไขการชำระที่ได้รับอนุญาตจริง
- Accounting รับช่วงต่อจาก credit gate ไม่ใช่ย้อนกลับไป override policy การขายเอง

deep controls เช่น:

- credit limit
- overdue hold
- approval tiers

ต้อง defer ไป Wave 2 ตามที่อนุมัติไว้แล้ว

## 7. Recommended Data and Process Baseline

### 7.1 AR Objects

อย่างน้อยต้องนิยามความสัมพันธ์ชัดระหว่าง:

- `sale.order` หรือ readiness dataset
- `account.move` สำหรับ customer invoice
- payment objects
- reconciliation result

### 7.2 AP Objects

อย่างน้อยต้องนิยามความสัมพันธ์ชัดระหว่าง:

- `purchase.order`
- receipt or service acceptance signal
- `account.move` สำหรับ vendor bill
- payment objects
- reconciliation result

### 7.3 Status Vocabulary

Wave 1 ควรมีภาษากลางที่สื่อสารข้ามทีมได้ เช่น:

- `Ready to Bill`
- `Invoiced`
- `Collected`
- `Ready for Vendor Billing`
- `Billed`
- `Paid`
- `Reconciled`

ไม่จำเป็นต้องใช้ label เหล่านี้ตรงตัวทั้งหมด แต่ระบบต้องมีความหมายเทียบเคียงได้

## 8. Security and Approval Model

- `Sales`
  - เห็นสถานะ billing และ receivable ที่เกี่ยวกับลูกค้าของตัวเองได้
  - ออก invoice หรือรับเงินได้เฉพาะตามสิทธิ์ที่องค์กรกำหนด
  - ไม่ควรแก้ posting/reconciliation truth โดยอิสระ
- `Purchase`
  - เห็นสถานะ vendor billing และ payable ที่เกี่ยวกับ procurement flow ได้
  - ไม่ควรเป็น owner ของ vendor payment หรือ accounting posting
- `Inventory`
  - ส่ง movement truth และ returns consequence signal
  - ไม่ควรเป็น owner ของ invoice/bill posting
- `Accounting`
  - เป็น owner ของ invoice, bill, payment, reconciliation, และ accounting states
  - เป็น owner ของ account/tax mapping baseline

approval model ใน Wave 1 ควรยึดที่:

- ต้นทางอนุมัติธุรกรรมเชิงธุรกิจในโดเมนของตน
- Accounting อนุมัติหรือควบคุมจุดบัญชีที่มีผลต่อ posting/cash/reconciliation ตามสิทธิ์ที่องค์กรกำหนด

approval tiers เชิงลึกของ finance exceptions ให้ defer ไป Wave 2

## 9. Reporting and KPI Needs

owner-facing KPIs ขั้นต่ำของ Wave 1 ควรมี:

- `Billable Backlog`
- `Open Receivable`
- `Overdue Receivable` ในระดับการมองเห็น ไม่ใช่ hold policy เชิงลึก
- `Open Payable`
- `Due Payable`
- `Cash Application Status`
- `Unreconciled Customer Items`
- `Unreconciled Vendor Items`

หลักคิดคือ Wave 1 ต้องทำให้ owner เห็นภาพปิดวงจรของธุรกิจ ไม่ใช่เห็นแค่ยอดขายหรือยอดซื้อแยกส่วน

## 10. Boundary with Wave 2

สิ่งที่อยู่ใน Wave 1 คือ:

- operational accounting closure
- invoice/bill/payment/reconciliation baseline
- essential posting and tax mapping
- owner closure KPIs

สิ่งที่ไป Wave 2 คือ:

- finance controls เชิงลึก
- credit control เชิงตัวเลข
- exception approval matrix
- cheque and advance specialization
- richer finance analytics

เหตุผลของ boundary นี้คือ:

- ถ้าดึง controls เชิงลึกเข้ามาใน Wave 1 มากเกินไป จะทำให้ closure ของ commercial core ช้า
- ถ้าไม่ทำ payment/reconciliation baseline ใน Wave 1 เลย จะปิดคำว่า `Operational Closure` ไม่ได้จริง

## 11. Migration Assumptions

- ข้อมูลลูกหนี้และเจ้าหนี้เดิมต้องถูกคัดว่าอะไรคือ open items ที่ยังมีความหมายจริง
- payment และ reconciliation เดิมอาจมีรูปแบบพิเศษที่ยังไม่ควรถูกยกมาทั้งหมดโดยอัตโนมัติ
- account and tax mapping จากระบบเดิมต้องถูกใช้เป็น reference ไม่ใช่คัดลอกโดยไม่ตรวจเหตุผล
- รายงานการเงินเดิมจาก Odoo 15 ต้องผ่านการคัด `Keep/Refactor/Retire` ตาม owner value ก่อน rebuild

## 12. Training Impact

ทีมที่ได้รับผลกระทบโดยตรง:

- ฝ่ายบัญชี
- ฝ่ายขาย
- ฝ่ายจัดซื้อ
- ฝ่ายคลัง
- ผู้บริหาร

หัวข้ออบรมขั้นต่ำ:

- handoff จาก Sales/Purchase/Inventory เข้าบัญชี
- invoice/bill readiness คืออะไร
- วิธีรับเงินและจ่ายเงินตาม baseline ใหม่
- วิธีอ่านสถานะ open items และ reconciled items
- วิธีใช้ owner KPIs เพื่อติดตาม closure จริง

## 13. Build Guidance for the Next Plan

เมื่อแตก implementation plan ให้ยึดหลักดังนี้:

- แยกงานเป็นอย่างน้อย 3 streams:
  - AR closure
  - AP closure
  - cash and reconciliation baseline
- เพิ่ม stream เสริมสำหรับ:
  - posting/tax mapping baseline
  - owner reporting
- ทุก stream ต้องมี integration checkpoints กับ Sales, Purchase, Inventory, และ Credit Gate
- ห้ามพ่วง Wave 2 finance controls เข้ามาในแผน build ของ Wave 1
- ทุก addon หรือ customization ต้องติดตั้ง/ถอนออกได้โดยไม่แตะ Odoo core

## 14. Final Recommendation

recommendation ของ child spec นี้คือ:

- ให้ `Wave 1 - Accounting` เป็นก้อน `Operational Closure` จริง ไม่ใช่แค่ invoice shell
- ให้รับ `Full Cash Cycle` ในระดับ baseline เพื่อปิด loop เชิงปฏิบัติการของธุรกรรมหลัก
- ให้กัน deep finance controls ไว้ใน `Wave 2` อย่างชัดเจน

ถ้าทำตามนี้ Wave 1 จะปิด commercial core ได้จริงจากปลายธุรกรรมถึงปลายเงิน โดยยังรักษาความคุมขอบเขตและความอัปเกรดง่ายของระบบไว้ได้
