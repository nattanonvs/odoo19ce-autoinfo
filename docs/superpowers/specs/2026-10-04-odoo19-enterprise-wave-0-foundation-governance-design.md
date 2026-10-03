# Odoo 19 CE Wave 0: Foundation, Technical Platform, and KPI Baseline

วันที่: 2026-10-04
สถานะ: รอผู้ใช้ทบทวน
รหัสสเปก: W0-FOUNDATION
ผู้อ่านหลัก: ทีมเทคนิค + เจ้าของ/ผู้อนุมัติ
อ้างอิงหลัก:
- `docs/superpowers/specs/2026-10-04-odoo19-ce-enterprise-blueprint-design.md`
- `docs/superpowers/programs/odoo19-enterprise/backlog/domain-wave-matrix.md`
- `docs/superpowers/programs/odoo19-enterprise/backlog/domain-spec-index.md`

## 1. สรุปสั้น ๆ

Wave 0 คือการวาง "ฐาน" ของโครงการ Odoo 19 CE ใหม่ก่อนเริ่มออกแบบงานธุรกิจจริงใน Wave 1 เป็นต้นไป

Wave นี้ยังไม่ใช่งานสร้างระบบธุรกิจรายแผนก เช่น Sales, Purchase, Inventory หรือ Accounting แบบลงรายละเอียดธุรกรรม

Wave นี้มีหน้าที่ทำ 4 เรื่องใหญ่ให้ชัดก่อน:

- วางกติกาของโครงการ
- วางฐานทางเทคนิคและสภาพแวดล้อมตั้งแต่ dev ถึง production
- วางฐาน KPI, รายงาน, และแดชบอร์ดรายบทบาท
- วางเงื่อนไขส่งต่องานไป Wave 1 โดยไม่ต้องกลับมาถกหลักการเดิมอีก

พูดง่าย ๆ คือ:
"Wave 0 ไม่ได้สร้างงานขาย งานซื้อ หรืองานคลัง"
แต่ Wave 0 สร้าง "ราง" ที่ทำให้ทุก wave ถัดไปสร้างได้ถูกต้อง ดูแลง่าย และอัปเกรดง่าย

## 2. เป้าหมายของ Wave 0

Wave 0 ต้องทำให้ทีมทั้งฝั่งธุรกิจและฝั่งเทคนิคเห็นตรงกันในเรื่องต่อไปนี้:

- ระบบใหม่จะถูกพัฒนาอย่างไร
- ห้ามทำอะไรบ้าง เช่น การแก้ core ของ Odoo โดยตรง
- ใช้มาตรฐานอะไรเป็นหลัก เช่น OCA-first
- สภาพแวดล้อม dev, test, UAT, training, production จะเป็นอย่างไร
- เจ้าของเงินและผู้บริหารควรเห็น KPI, รายงาน, และสัญญาณเตือนอะไร
- Wave 1 ต้องเริ่มจากอะไร และยึดกติกาใดเป็น baseline

## 3. ขอบเขตของ Wave 0

Wave 0 ครอบคลุม:

- Program foundation
- Technical platform baseline
- Production readiness baseline
- KPI and reporting baseline
- Dashboard blueprint รายบทบาท
- Exit criteria และ handoff ไป Wave 1

Wave 0 ไม่ครอบคลุม:

- รายละเอียด process รายธุรกรรมของ Sales, Purchase, Inventory, Accounting
- การออกแบบฟิลด์รายหน้าจอ
- การเขียนโค้ด custom module รายโดเมน
- การทำ migration mapping ราย field
- การสร้าง dashboard จริงใน Odoo

## 4. Program Foundation

ส่วนนี้คือกติกาหลักของโครงการ

### 4.1 หลักการที่ต้องยึด

- อัปเกรดเวอร์ชันในอนาคตได้ง่าย
- บำรุงรักษาได้ง่าย
- เขียนโค้ดให้อ่านง่ายและส่งต่องานได้
- ไม่แก้ Odoo core โดยตรง
- โมดูลต้องติดตั้งและถอนได้โดยไม่ทำให้ระบบพัง
- ใช้ OCA ก่อน custom เสมอเมื่อมีทางเลือกที่เหมาะสม

### 4.2 กติกาการตัดสินใจ

ทุก requirement ใหม่ต้องผ่านคำถามตามลำดับนี้:

1. Odoo มาตรฐานทำได้หรือไม่
2. OCA มีหรือไม่
3. ถ้ามี OCA ทำไมจึงไม่ใช้
4. ถ้าจำเป็นต้อง custom จริง จะทำให้ถอดออกได้หรือไม่

### 4.3 กติกาการ review

ก่อนเริ่มงานจริงในแต่ละโดเมน ต้องมี:

- child spec ที่อนุมัติแล้ว
- ผู้รับผิดชอบชัดเจน
- ผู้ตรวจหลักทางเทคนิคชัดเจน
- ผู้อนุมัติฝั่งธุรกิจและเทคนิคชัดเจน
- หลักฐานประกอบการตัดสินใจชัดเจน

## 5. Technical Platform Baseline

ส่วนนี้กำหนดว่าทีมจะสร้างระบบบนฐานแบบไหน

### 5.1 โครงสร้าง repository

ต้องแยกของสำคัญออกจากกันอย่างชัดเจน เช่น:

- เอกสารโปรแกรม
- specs
- plans
- custom addons
- deployment/config
- tests
- migration utilities

หลักคิดคือ:
repo ต้องสะท้อน architecture ไม่ใช่สะท้อนความสะดวกเฉพาะหน้า

### 5.2 ขอบเขตของ addon

หนึ่ง addon ควรมีหน้าที่ชัดเจนหนึ่งเรื่องหลัก

ไม่ควรทำ addon ขนาดใหญ่ที่รวมหลายโดเมนเข้าด้วยกัน เพราะจะทำให้:

- ดูแลยาก
- ถอดออกยาก
- dependency ซับซ้อน
- อัปเกรดยาก

### 5.3 สภาพแวดล้อม

Wave 0 นี้กำหนดว่าอย่างน้อยต้องมี:

- Local Dev
- Shared Dev / Integration
- Test / QA
- UAT / Training
- Production

และแต่ละสภาพแวดล้อมต้องตอบได้ว่า:

- ใช้ทำอะไร
- ใครเข้าถึงได้
- ใช้ข้อมูลประเภทไหน
- เปลี่ยนแปลงอย่างไร
- ใครอนุมัติ

### 5.4 คุณภาพขั้นต่ำก่อน merge/deploy

ต้องมี baseline ขั้นต่ำ เช่น:

- lint
- tests
- install/uninstall checks
- dependency review
- security review
- upgrade note

Wave 0 ยังไม่จำเป็นต้องออกแบบ pipeline ลึกทุกขั้น
แต่ต้องกำหนดให้ชัดว่าอะไรคือ minimum gate ของโครงการ

## 6. Production Readiness Baseline

แม้ยังไม่ deploy production ใน Wave 0 แต่ต้องกำหนดภาพเป้าหมาย production ตั้งแต่ตอนนี้

### 6.1 สิ่งที่ต้องนิยาม

- production topology โดยรวม
- configuration ownership
- secrets handling
- logging and monitoring baseline
- backup and restore expectations
- audit and traceability baseline
- incident and rollback baseline

### 6.2 หลักคิดสำคัญ

ระบบใหม่ต้องไม่ออกแบบแบบ "พอ dev รันได้ก็พอ"

ต้องออกแบบโดยคิดล่วงหน้าว่าเมื่อถึง production แล้ว:

- ใครดูแล
- ใครอนุมัติ
- ถ้าเสียจะกู้คืนอย่างไร
- ถ้า deploy พลาดจะถอยกลับอย่างไร
- log และ alert สำคัญอยู่ตรงไหน

## 7. KPI, Reporting, and Dashboard Baseline

ส่วนนี้ตอบโจทย์หลักของเจ้าของเงินลงทุนโดยตรง

ระบบใหม่ต้องไม่ได้เป็นแค่ที่บันทึกข้อมูล
แต่ต้องเป็นเครื่องมือที่ช่วยให้ตัดสินใจได้ดีขึ้น

### 7.1 ระดับของ KPI

อย่างน้อยต้องแยกเป็น 3 ระดับ:

- Owner level
- Management level
- Operational level

### 7.2 หลักของรายงานที่ดี

รายงานสำคัญทุกตัวควรถูกนิยามว่า:

- ใช้ตอบคำถามอะไร
- ใครใช้
- ใช้ตัดสินใจอะไร
- อิงข้อมูลจากไหน
- อัปเดตบ่อยแค่ไหน
- drill-down ได้ถึงไหน

### 7.3 Signals และ Alerts

ระบบใหม่ควรมีทั้ง:

- health signals
- control alerts
- operational alerts

และทุก alert ควรมี:

- เงื่อนไขที่ทำให้เกิด
- ระดับความรุนแรง
- คนรับผิดชอบ
- วิธีตอบสนอง
- เส้นทางการ escalate

## 8. Dashboard Blueprint ตามบทบาท

Wave 0 นี้ต้องไปถึงระดับ blueprint/mocked content ของ dashboard รายบทบาท

### 8.1 Owner Dashboard

Owner dashboard ควรตอบคำถามหลัก เช่น:

- บริษัทกำลังโตหรือชะลอ
- เงินสดและรายรับเริ่มเสี่ยงหรือไม่
- จุดไหนกำลังกินกำไร
- หน่วยงานไหนมีสัญญาณผิดปกติ
- ตอนนี้ควรตัดสินใจอะไร

โซนหลักที่ควรมี:

- Executive summary
- Risk and alert zone
- Trend zone
- Business unit comparison
- Decision support
- Drill-down entry

### 8.2 Management Dashboard

Management dashboard ควรตอบคำถามว่า:

- ทีมทำได้ตามเป้าหมายหรือไม่
- bottleneck อยู่ตรงไหน
- อะไรใกล้หลุด SLA
- อะไรต้องเข้าไปแก้ก่อน

โซนหลักที่ควรมี:

- Performance summary
- Pipeline/workload
- Exception zone
- SLA/timeliness
- Manager action zone

### 8.3 Operational Lead Dashboard

Operational dashboard ควรตอบคำถามว่า:

- วันนี้มีอะไรต้องทำก่อน
- งานไหนติด
- งานไหนใกล้เลยกำหนด
- ระบบตรงไหนกำลังมีปัญหา

โซนหลักที่ควรมี:

- Today's priority queue
- Pending and stuck workflows
- Near deadline zone
- Execution health zone
- Operational actions

## 9. Deliverables ของ Wave 0

Wave 0 ควรส่งมอบอย่างน้อย:

- Wave 0 child spec ฉบับนี้
- Program foundation pack
- Technical platform baseline pack
- Production readiness baseline
- KPI and reporting baseline
- Dashboard blueprint รายบทบาท
- Handoff pack สำหรับ Wave 1
- Readiness assessment

## 10. Exit Criteria ของ Wave 0

Wave 0 จะถือว่าผ่านเมื่อ:

- governance baseline ถูกอนุมัติ
- technical platform baseline ถูกอนุมัติ
- production readiness baseline ถูกยอมรับในระดับ foundation
- KPI/reporting/dashboard baseline ถูก review และยอมรับ
- backlog control และ child spec control ใช้งานได้
- ระบุชัดว่า Wave 1 ต้องเริ่มจากอะไร

## 11. สิ่งที่ต้องส่งต่อให้ Wave 1

Wave 1 ต้องได้รับอย่างน้อย:

- Wave 0 child spec ที่อนุมัติแล้ว
- engineering standards
- review gates
- technical platform baseline
- production readiness baseline
- KPI/reporting baseline
- dashboard blueprint
- discovery baseline ที่มี known unknowns ชัดเจน

## 12. สิ่งที่ defer ไปได้

Wave 0 ยังไม่ต้องตอบรายละเอียดระดับ implementation เช่น:

- field mapping ราย field
- screen-level UI detail
- code design รายโมดูล
- migration script รายชุด
- dashboard implementation จริง

แต่ทุกเรื่องที่ defer ต้องระบุ owner และ wave ปลายทางให้ชัด

## 13. Definition of Done

Wave 0 ถือว่า done เมื่อ:

- เอกสารนี้ได้รับการอนุมัติ
- baseline ที่เกี่ยวข้องเชื่อมเข้าหากันได้จริง
- ทีมเทคนิคสามารถใช้แตก implementation plan ต่อได้
- เจ้าของ/ผู้อนุมัติสามารถใช้เอกสารนี้ review แนวทางธุรกิจและการลงทุนได้
- Wave 1 สามารถเริ่มต่อได้โดยไม่ต้องย้อนกลับมาถกหลักการพื้นฐานใหม่

## 14. ข้อสรุปแบบง่าย

ถ้าอธิบายแบบคนไม่มีพื้นฐานเทคนิค:

Wave 0 คือการ "ตั้งกติกา + ตั้งโครง + ตั้งเป้าหมายข้อมูล"
ก่อนจะเริ่มสร้างระบบงานจริง

มันเหมือนการสร้าง:

- แบบแปลนบ้าน
- กฎการก่อสร้าง
- รายการตรวจรับ
- ระบบไฟ น้ำ ความปลอดภัย
- และมุมมองที่เจ้าของบ้านอยากเห็น

ก่อนจะเริ่มก่อผนังและตกแต่งห้องจริง

ถ้า Wave 0 ดี:
- งานรอบต่อไปจะเร็วขึ้น
- คุมคุณภาพได้
- เปลี่ยนคนทำต่อได้
- อัปเกรดในอนาคตง่ายขึ้น

ถ้า Wave 0 อ่อน:
- ทุกทีมจะตีความเอง
- ระบบจะเริ่มมั่วตั้งแต่ต้น
- และจะกลายเป็น legacy ใหม่อีกครั้ง
