# 06. Quality (คุณภาพ · การทดสอบ · การรายงานผล)

> **EN**: Evidence before claims — never report results that were not actually run. · **TH**: ห้ามอ้างผลที่ยังไม่ได้รัน — ต้องมีหลักฐานจริงทุกครั้ง

## 1. Test gate

- **ต้องรัน Unit Test ให้ผ่านก่อน commit/push** (0 failed / 0 error) — บน DB ทดสอบของตัวเอง (`odoo19_t_<AGENT_ID>`)
- การทดสอบแบบขนานใช้ DB/พอร์ต/data-dir ของตัวเอง — ดู [02-isolation.md §6](02-isolation.md#6-parallel-testing-การทดสอบแบบขนาน)

## 2. Verify before claim (ยืนยันก่อนอ้างผล)

- อย่าเพิ่งสรุปว่าผ่าน/แก้เสร็จ ให้รันคำสั่งตรวจสอบจริงและดูผลลัพธ์ก่อน
- ผลลัพธ์ที่อ้างต้องมาจากคำสั่งที่รันจริงในรอบงานนั้น

## 3. การรายงานผลทุกครั้ง

ระบุให้ครบ:
- `AGENT_ID`
- commit SHA (ถ้ามี)
- ไฟล์ที่แตะ
- lease ที่จับ/ปล่อย
- คำสั่งที่รันจริง
- ผลลัพธ์จริง (รวม stage ของ Delivery Pipeline ปัจจุบัน)

**ห้ามอ้างผลที่ยังไม่ได้รัน**
