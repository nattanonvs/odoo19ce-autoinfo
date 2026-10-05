# Sales OCA Installation Recommendations by Wave

วันที่: 2026-10-05
สถานะ: Recommended for Wave planning
รหัสเอกสาร: W1-SALES-OCA-RECOMMEND
ผู้อ่านหลัก: Owner/Management + Sales Lead + Billing Lead + Technical Lead
อ้างอิงหลัก:
- `docs/superpowers/specs/2026-10-04-odoo19-enterprise-wave-1-sales-contract-core-design.md`
- `docs/superpowers/programs/odoo19-enterprise/sales/oca-fit-gap.md`
- `docs/superpowers/programs/odoo19-enterprise/sales/addon-boundaries.md`

## 1. วัตถุประสงค์

เอกสารนี้ใช้สรุปคำแนะนำการติดตั้ง OCA ด้าน Sales สำหรับโครงการ Odoo 19 CE โดยตอบ 3 คำถามพร้อมกัน:

- ตัวไหน `ควรติดตั้ง`
- ตัวไหน `น่าสนใจแต่ควรรอ`
- ตัวไหน `ยังไม่ควรติดตั้ง`

เอกสารนี้ยังทำหน้าที่ map โมดูล OCA เข้ากับ `wave ที่เหมาะ` เพื่อให้การตัดสินใจไม่หลุดจากขอบเขตของ `Sales Contract Core`

## 2. หลักคิดที่ใช้ตัดสิน

ใช้หลักคิดเดียวกันทุกโมดูล:

1. ต้องสอดคล้องกับแนวทาง `OCA First, Custom Second`
2. ต้องไม่ดึง `Stock/Delivery detail` และ `Accounting detail` เข้ามาในแกน `Sales Contract Core` เร็วเกินไป
3. ถ้าเป็นโมดูลที่มี dependency พร้อมและช่วยลด custom ที่เราต้องเขียน ควรพิจารณาก่อน
4. ถ้าเป็นโมดูลที่แตะ policy กว้างมากหรือดึง workflow ข้าม bounded context มากเกินไป ให้เลื่อนไป wave ถัดไป

## 3. แบบที่ 1: ตารางสำหรับตัดสินใจเชิงธุรกิจ

| โมดูล | คำแนะนำ | คุณค่าทางธุรกิจ | wave ที่เหมาะ |
| --- | --- | --- | --- |
| `base_user_role` | ควรติดตั้ง | แยกบทบาท Sales / Billing / Manager ชัด ลดความเสี่ยงสิทธิ์ปนกัน | Wave 1 |
| `sale_blanket_order` | ควรติดตั้ง | รองรับรูปแบบสัญญา/Blanket ที่ตรงกับธุรกิจ | Wave 1 |
| `sale_order_revision` | ควรติดตั้ง | เก็บ revision ของเอกสารขายและใช้ trace การเปลี่ยนแปลง | Wave 1 |
| `sale_delivery_state` | ควรติดตั้ง | ช่วยให้เห็นสถานะส่งมอบก่อนถึง billing readiness | Wave 1 |
| `sale_exception` | ควรติดตั้ง | ใช้ block/exception rule เมื่อเอกสารหรือ policy ยังไม่ครบ | Wave 1 |
| `sale_order_line_price_source` | น่าสนใจมาก | เพิ่ม traceability ของราคาว่ามาจาก pricelist หรือ manual override | Wave 2 |
| `sale_invoice_to_partner` | น่าสนใจมาก | รองรับกรณีผู้สั่งงานไม่ใช่ผู้รับ invoice/ผู้จ่ายเงินจริง | Wave 2 |
| `sale_invoice_blocking` | น่าสนใจมาก | คุมว่า “ยังห้ามออก invoice” จนกว่าหลักฐานพร้อม | Wave 2 |
| `sale_order_type` | น่าสนใจแต่ต้องระวัง | ช่วยแยก One-time / Contract / Blanket ได้ดี แต่มีผลต่อ policy หลายเรื่อง | Wave 3 |
| `sale_invoice_frequency` | น่าสนใจแต่ควรรอ | ช่วยเรื่องรอบวางบิลรายครั้ง/รวมรอบ แต่ยังต้องมี orchestration เพิ่ม | Wave 3 |
| `sale_substate` | น่าสนใจแต่ควรรอ | ทำสถานะย่อย เช่น รอเอกสาร/รอ sign-off ได้ดี | Wave 3 |
| `sale_cancel_reason` | เสริมได้ | ช่วยวิเคราะห์ดีลที่ยกเลิกหรืองานหลุด | Wave 3 |
| `sale_advance_payment` | ยังไม่ควร | ดึง accounting เข้ามาเร็วเกินไปสำหรับ Sales Core | Not now |
| `sale_manual_delivery` | ยังไม่ควร | ดึง logistics flow เข้ามาปะปนกับ sales core | Not now |
| `sale_stock_delivery_state` | ยังไม่ควร | ผูก stock ลึกเกินไปสำหรับ wave นี้ | Not now |
| `sale_automatic_workflow` | ยังไม่ควร | เสี่ยง auto workflow ก่อน governance และ evidence policy นิ่ง | Not now |

## 4. แบบที่ 2: ตารางเชิงเทคนิค

| โมดูล | Repo | Dependency สำคัญ | ใช้ตอบ requirement ไหน | ประโยชน์ทางเทคนิค | ความเสี่ยง/ข้อควรระวัง | wave ที่เหมาะ |
| --- | --- | --- | --- | --- | --- | --- |
| `base_user_role` | `server-backend` | ไม่มีซับซ้อนมาก | แยกบทบาท Sales/Billing/Manager | governance ดีขึ้น | ต้องออกแบบ role matrix ให้ชัด | Wave 1 |
| `sale_blanket_order` | `sale-blanket` | ตาม repo OCA | Contract-based / Blanket | ลดการทำ commercial instrument เองทั้งหมด | ต้อง bridge เข้ากับ contract core ของเรา | Wave 1 |
| `base_revision` | `server-ux` | ใช้คู่ `sale_order_revision` | Sale Revision / Version Control | เป็นฐาน revision มาตรฐาน | ต้องคุม UX ของ revision | Wave 1 |
| `sale_order_revision` | `sale-workflow` | `base_revision` | Trace การแก้ quotation / order | เก็บประวัติการเปลี่ยนแปลงได้ชัด | ต้องกำหนดจุดเชื่อมกับ approval ให้ดี | Wave 1 |
| `sale_delivery_state` | `sale-workflow` | ไม่มีซับซ้อนมาก | Delivery status ก่อน billing readiness | เบาและต่อยอดง่าย | อย่าสับสนกับ billing readiness ของ custom | Wave 1 |
| `base_exception` | `server-tools` | ใช้คู่ `sale_exception` | Exception/approval rules | เป็นฐานกฎตรวจสอบก่อนเดิน flow | ต้องออกแบบ rule set ไม่ให้บวม | Wave 1 |
| `sale_exception` | `sale-workflow` | `base_exception` | เอกสารไม่ครบ / policy ไม่ผ่าน | harden sales flow ได้ดี | ต้องระวัง UX ไม่ให้ bypass ง่าย | Wave 1 |
| `sale_order_line_price_source` | `sale-workflow` | ไม่หนัก | Audit และ trace แหล่งที่มาของราคา | visibility เรื่อง pricing ดีมาก | ไม่ได้คุม pricing logic เอง | Wave 2 |
| `sale_invoice_to_partner` | `sale-workflow` | sale/accounting related | buyer != payer | รองรับ invoice partner แยกจากคู่ค้าเชิงพาณิชย์ | ต้อง map ให้ไม่ชนกับ Commercial Customer / Project Owner | Wave 2 |
| `sale_invoice_blocking` | `sale-workflow` | invoice flow | แยก commercial approval ออกจาก billing readiness | block invoice ได้ตรง | ต้อง bridge เข้ากับ billing trigger จริงของเรา | Wave 2 |
| `sale_order_type` | `sale-workflow` | แตะ policy หลายจุด | แยกประเภท order mode | ลด custom config logic ได้มาก | มีผลข้างเคียงกว้าง ควรใช้หลัง flow ชัด | Wave 3 |
| `sale_invoice_frequency` | `sale-workflow` | invoice flow | วางบิลรายครั้ง/รวมรอบ | เป็นฐาน grouping/frequency | ไม่ใช่ auto-invoice สำเร็จรูป | Wave 3 |
| `sale_substate` + `base_substate` | `sale-workflow` + `server-ux` | `base_substate` | รอเอกสาร / รอ sign-off | ทำสถานะย่อยโดยไม่บวม state หลัก | ถ้า governance ไม่ดีจะเกิดสถานะย่อยรก | Wave 3 |
| `sale_cancel_reason` | `sale-workflow` | ไม่หนัก | วิเคราะห์ lost business | ช่วย owner reporting | เป็นฟีเจอร์เสริม ไม่ใช่แกนหลัก | Wave 3 |
| `sale_tier_validation` | `sale-workflow` | `base_tier_validation` | multi-step approval | น่าสนใจในอนาคต | ยัง `deferred` เพราะ baseline 19.0 ยังไม่ชัด | Deferred |
| `sale_invoice_plan` | `sale-workflow` | ตาม baseline 19.0 ที่ยังไม่ชัด | invoice scheduling | น่าสนใจในอนาคต | ยัง `deferred` เพราะ baseline 19.0 ยังไม่ชัด | Deferred |

## 5. ตาราง Shortlist สำหรับติดตั้งจริง

### 5.1 ติดตั้งใน Wave 1

| ลำดับ | โมดูล | เหตุผลหลัก | หมายเหตุ |
| --- | --- | --- | --- |
| 1 | `base_user_role` | เป็นฐาน governance ของบทบาท | ติดตั้งก่อนเปิดใช้สิทธิ์เชิงธุรกิจ |
| 2 | `sale_blanket_order` | ตรงกับงานขายแบบกรอบ/Blanket | เป็นฐาน contract instrument |
| 3 | `base_revision` | dependency ของ revision | ติดตั้งคู่กับ revision |
| 4 | `sale_order_revision` | รองรับ Sale Revision/Version Control | ใช้กับเอกสารขายที่เปลี่ยนบ่อย |
| 5 | `sale_delivery_state` | เพิ่มสถานะส่งมอบที่เบาและ useful | ใช้เป็น delivery status snapshot |
| 6 | `base_exception` | dependency ของ exception rules | ติดตั้งก่อนใช้ rule |
| 7 | `sale_exception` | harden sales flow ด้วย business rules | ใช้ผ่าน bridge ให้เข้ากับ policy ของเรา |

### 5.2 Shortlist รอบถัดไป

| ลำดับ | โมดูล | เหตุผลที่น่าสนใจ | เงื่อนไขก่อนติดตั้ง |
| --- | --- | --- | --- |
| 8 | `sale_order_line_price_source` | เพิ่ม traceability เรื่องราคา | ติดตั้งได้หลัง Wave 1 core นิ่ง |
| 9 | `sale_invoice_to_partner` | รองรับ buyer กับ payer คนละราย | ต้อง confirm business role mapping ให้ชัด |
| 10 | `sale_invoice_blocking` | เพิ่มวินัยการ block invoice | ต้อง map เข้ากับ billing readiness ของเรา |

### 5.3 Candidate ระยะถัดไป

| ลำดับ | โมดูล | เหตุผล | จังหวะที่เหมาะ |
| --- | --- | --- | --- |
| 11 | `sale_order_type` | จัด type ของ order ได้เป็นระบบมากขึ้น | หลัง flow หลักนิ่ง |
| 12 | `sale_invoice_frequency` | ช่วยจัดรอบวางบิล | หลัง billing policy ชัด |
| 13 | `sale_substate` + `base_substate` | เพิ่มสถานะย่อยแบบคุม governance | หลัง state หลักนิ่ง |
| 14 | `sale_cancel_reason` | เก็บสาเหตุงานหลุดเพื่อวิเคราะห์ | หลัง reporting framework นิ่ง |

## 6. คำแนะนำเชิง rollout

### 6.1 รอบที่ควรทำทันที

ติดตั้งเฉพาะกลุ่ม `Wave 1` ก่อน เพื่อให้ได้ประโยชน์สูงสุดโดยไม่ดึง complexity ข้ามโดเมน:

- `base_user_role`
- `sale_blanket_order`
- `base_revision`
- `sale_order_revision`
- `sale_delivery_state`
- `base_exception`
- `sale_exception`

### 6.2 รอบถัดไปที่คุ้มค่า

เมื่อ `Sales Contract Core` นิ่งและทีมเข้าใจ process ใหม่แล้ว ค่อยพิจารณา:

- `sale_order_line_price_source`
- `sale_invoice_to_partner`
- `sale_invoice_blocking`

### 6.3 สิ่งที่ยังไม่ควรรีบ

ยังไม่ควรดึงเข้ามาใน wave แรก:

- `sale_order_type`
- `sale_invoice_frequency`
- `sale_substate`
- `sale_tier_validation`
- `sale_invoice_plan`
- `sale_advance_payment`
- `sale_manual_delivery`
- `sale_stock_delivery_state`
- `sale_automatic_workflow`

## 7. สรุปคำตัดสิน

ถ้าต้องการแนวทางที่ `ปลอดภัย + คุ้มค่า + ตรงกับ requirement ตอนนี้` ให้ใช้ shortlist ดังนี้:

- Wave 1: `base_user_role`, `sale_blanket_order`, `base_revision`, `sale_order_revision`, `sale_delivery_state`, `base_exception`, `sale_exception`
- Wave 2: `sale_order_line_price_source`, `sale_invoice_to_partner`, `sale_invoice_blocking`
- Wave 3: `sale_order_type`, `sale_invoice_frequency`, `sale_substate`, `sale_cancel_reason`

และให้คง `sale_tier_validation` กับ `sale_invoice_plan` เป็น `deferred` จนกว่าจะยืนยัน baseline 19.0 ได้ชัดเจน
