# Odoo 19 CE Wave 5: HR and Operational Enablement

## Control Metadata
- Child spec ID: W5-HR-ENABLEMENT
- Wave: Wave 5
- Status: Implemented baseline — Attendances and ZKTeco integration delivered; HR Expense and Fleet already live
- Owner: HR operations lead
- Reviewer: Technical supervisor
- Approvers: Business owner; Technical supervisor
- Target edition: Odoo 19 Community Edition (CE)
- Canonical path: `docs/superpowers/specs/2026-10-15-odoo19-enterprise-wave-5-hr-operational-enablement.md`
- Source backlog row: `docs/superpowers/programs/odoo19-enterprise/backlog/domain-wave-matrix.md`
- Date: 2026-10-15
- Primary readers: ฝ่ายบุคคล, ฝ่ายบัญชี, ฝ่ายไอที, ผู้จัดการแผนก, ผู้อนุมัติ, ทีมเทคนิค

## Approval Traceability
- Scope baseline (Employees, Attendances, Time Off, HR Expense, Fleet) approved in the Wave Control Register on 2026-10-12.
- ZKTeco face/fingerprint terminal integration requested by the business owner on 2026-10-15.
- Attendance + ZKTeco implementation delivered and verified on 2026-10-15.

## Discovery Evidence
- Current-state references:
  - `docs/superpowers/programs/odoo19-enterprise/backlog/domain-wave-matrix.md` (Wave 5 scope and focus)
  - `docs/superpowers/specs/2026-10-04-odoo19-ce-enterprise-blueprint-design.md`
  - `Odoo15Backup/` legacy addons: `autoinfo_hr_expense`, `autoinfo_hr_expense_cash_tracking`, `autoinfo_fleet`
  - Odoo 19 standard modules `hr`, `hr_attendance`, `hr_holidays`, `hr_expense`, `fleet`, `hr_fleet`, `account_fleet`
- Verified current state (live database query, 2026-10-15):
  - `hr`, `hr_expense`, `fleet`, `hr_fleet`, `account_fleet`, `hr_org_chart` — installed in both `odoo19` and `odoo19_pdev`
  - `hr_attendance`, `hr_holidays`, `hr_work_entry` — were **not installed** before this wave
  - Custom modules already installed: `od19_hr_expense_thai`, `od19_hr_expense_enhanced`, `od19_fleet_accounting`, `od19_fleet_notification`
  - No ZKTeco / iClock / ADMS / biometric module existed in `addons/` or `custom_addons/`
  - Python package `pyzk` is **not** available in `venv19`; `requests` is available
- Evidence coverage gaps:
  - ยังไม่มี field-by-field migration map ของ `autoinfo_hr_expense` → `hr_expense`
  - ยังไม่มีตารางกะทำงาน (shift/roster) และ OT policy ที่ยืนยันเป็นลายลักษณ์อักษรจาก HR
  - ยังไม่มีข้อมูลรายการเครื่องสแกนจริง (รุ่น, จำนวนจุดติดตั้ง, หมายเลขเครื่อง) เพื่อผูกกับ device registry

## Delivery Controls
- Dependencies:
  - Wave 0 governance baseline approved
  - Wave 1 accounting baseline (สำหรับ Fleet → Accounting และ HR Expense posting)
  - OCA-First strategy: ใช้ standard `hr_expense` และ `fleet` แทนการเขียนโมดูลใหม่
- Gate readiness:
  - Spec-ready: ขอบเขต HR, attendance, time off, expense, fleet และขอบเขต integration ถูกนิยามชัด
  - Plan-ready: addon boundary, security model, device protocol และ test strategy อธิบายชัด
  - Build-ready: HR base modules ติดตั้งและตรวจสอบใน `odoo19` และ `odoo19_pdev` แล้ว; ZKTeco module พร้อมใช้งาน

## 1. สรุปสั้น ๆ

Child spec นี้ออกแบบแกน `HR and Operational Enablement` ของ Wave 5 ให้ครอบคลุม:

- `Employees` (ทะเบียนพนักงาน, โครงสร้างองค์กร)
- `Attendances` (ลงเวลาเข้า–ออก และการเชื่อมต่อเครื่องสแกน ZKTeco)
- `Time Off` (วันลาและอนุมัติ)
- `HR Expense` (ค่าใช้จ่ายพนักงาน — แทน legacy `autoinfo_hr_expense`)
- `Fleet` (ยานพาหนะ — แทน legacy `autoinfo_fleet`)

หัวใจของ Wave นี้คือทำให้ระบบตอบได้ว่า:

- ใครมาทำงานเมื่อไร ด้วยข้อมูลจากเครื่องสแกนหน้าจริง
- การลงเวลาเชื่อถือได้และตรวจสอบย้อนหลังได้หรือไม่
- วันลาและ OT คำนวณสอดคล้องกับเวลาเข้าออกจริงหรือไม่
- ค่าใช้จ่ายพนักงานและค่าใช้จ่ายรถยนต์ไหลเข้า Accounting ครบถ้วนหรือไม่

โดเมนนี้ต้องเป็นแหล่งความจริงของ `people time` และ `people cost` โดยไม่ดึง logic ของ Accounting posting, Sales หรือ Inventory เข้ามาปะปนเกินจำเป็น

## 2. เป้าหมายของ Child Spec นี้

- เปิดใช้งานโมดูล HR มาตรฐานของ Odoo 19 CE ให้ครบตาม scope ของ Wave 5
- รับข้อมูลลงเวลาจากเครื่องสแกนใบหน้า/ลายนิ้วมือ **ZKTeco** โดยไม่พึ่ง third-party cloud
- รักษาหลัก **No core modification** และ **OCA-First**
- ให้ทุก addon ติดตั้ง/ถอนได้โดยไม่กระทบเสถียรภาพระบบ
- เตรียมหลักฐานตรวจสอบ (audit trail) ของ punch ดิบทุกครั้งที่รับจากเครื่อง

## 3. ขอบเขตของ Child Spec

อยู่ใน scope:
- ติดตั้งและตั้งค่า `hr`, `hr_attendance`, `hr_holidays` บน `odoo19` และ `odoo19_pdev`
- โมดูลใหม่ `od19_hr_attendance_zkteco` สำหรับรับ punch จากเครื่อง ZKTeco
- Device registry และ punch log พร้อม matching พนักงานผ่าน Badge ID / PIN
- การ pair punch เป็น `hr.attendance` (`in_mode`/`out_mode` = `technical`)
- Scheduled action (cron) เป็น safety-net ประมวลผล punch ที่ค้าง

ไม่อยู่ใน scope:
- การแก้ไขไฟล์ core ของ Odoo
- การเขียน shift/roster engine ใหม่ (จะพิจารณาเป็น enhancement แยก หาก HR ยืนยันความต้องการ)
- การทำ custom payroll (Odoo CE ไม่มี payroll)
- Hardware procurement และการตั้งค่า router/firewall ของอุปกรณ์
- Payroll engine และการคำนวณเงินเดือน

## 4. Current-State Summary

- HR Expense และ Fleet ถูกติดตั้งและใช้งานแล้ว (Wave 5 partial) ผ่าน standard module + custom Thai extensions
- Attendances และ Time Off ยังไม่ถูกเปิดใช้งานเลย — เป็นช่องว่างหลักของ Wave
- ไม่มีช่องทางรับข้อมูลลงเวลาจากอุปกรณ์ภายนอก ระบบเดิม (Odoo 15) พึ่งการนำเข้าไฟล์/พิมพ์ manual
- เครื่อง ZKTeco ที่ใช้งานอยู่รองรับโปรโตคอล **ADMS / iClock (Push)** ซึ่งเรียกกลับมาที่ server ผ่าน HTTP

## 5. Keep / Refactor / Replace / Retire

- Keep
  - `hr_expense`, `fleet`, `hr_fleet`, `account_fleet` (standard)
  - `od19_hr_expense_thai`, `od19_hr_expense_enhanced`, `od19_fleet_accounting`, `od19_fleet_notification` (custom ที่ผ่านการตรวจสอบแล้ว)
- Refactor
  - การนำเข้าข้อมูลลงเวลา: เปลี่ยนจาก manual/ไฟล์ เป็น device push + log audit
- Replace
  - `autoinfo_hr_expense`, `autoinfo_hr_expense_cash_tracking` → `hr_expense` + `od19_hr_expense_*`
  - `autoinfo_fleet` → `fleet` + `od19_fleet_*`
- Retire
  - ขั้นตอนนำเข้าเวลาแบบ manual ที่ซ้ำซ้อน เมื่อ device integration ทำงานครบ

## 6. Future-State Design

### 6.1 Base modules
เปิดใช้งาน `hr_attendance` และ `hr_holidays` เป็นฐานของเวลาเข้า–ออกและวันลา โดยใช้ standard workflow ทั้งหมด (ไม่ override core)

### 6.2 ZKTeco Push Integration (ADMS / iClock)
โมดูล `od19_hr_attendance_zkteco` เปิด public HTTP endpoints ให้เครื่องเรียกเข้ามา:

| Endpoint | Method | หน้าที่ |
| --- | --- | --- |
| `/iclock/cdata` | GET | Handshake — ส่งคอนฟิกกลับ (`GET OPTION FROM: <SN>`, `TimeZone`, `Realtime=1`) |
| `/iclock/cdata` | POST | รับข้อมูล (`table=ATTLOG`) เป็น tab-separated payload |
| `/iclock/getrequest` | GET | ให้เครื่อง poll คำสั่งจาก server (ตอบ `OK` เมื่อไม่มีคำสั่ง) |
| `/iclock/ping` | GET/POST | Heartbeat |
| `/iclock/devicecmd` | POST | รับผลลัพธ์คำสั่ง |
| `/iclock/test` | GET/POST | Connectivity test |

การตั้งค่าฝั่งเครื่อง (Menu > Comm > Cloud Server / ADMS):
- Server Address = IP/host ของ Odoo
- Server Port = `http_port` ของ Odoo (8070)
- Enable Domain Name / ADMS = On

ลำดับการทำงาน:
1. เครื่อง handshake → ถ้ายังไม่รู้จัก SN จะ **auto-register** device (เมื่อเปิดสวิตช์ ZKTeco)
2. เครื่อง POST ATTLOG → ระบบแปลง timestamp (local → UTC ตาม timezone บริษัท) → บันทึกเป็น punch log
3. ถ้าเปิด `Process Punches Automatically` → pair เป็น `hr.attendance` ทันที
4. Cron `ZKTeco - Process Pending Punches` ทำหน้าที่ safety-net ทุก 15 นาที

### 6.3 Employee Matching
- ใช้ฟิลด์ที่ตั้งค่าได้ (`od19_zkteco_match_field`): **Badge ID** (`hr.employee.barcode`) หรือ **PIN** (`hr.employee.pin`)
- Punch ที่หา employee ไม่เจอ → state `no_employee` ไม่ทำให้ระบบล้ม และตรวจสอบ/แก้ไขได้จาก Punch Log

### 6.4 Attendance Pairing
- Punch แรกของพนักงาน = check-in (`in_mode = technical`)
- Punch ถัดไป = check-out ของรายการที่ยังเปิดอยู่ (`out_mode = technical`)
- ถ้า punch อยู่ในช่วง `Check-out Grace` หลัง check-in → ถือเป็น duplicate และไม่สร้าง record
- หากรณี overlap กับ attendance เดิม → ระบบบันทึกเป็น state `error` พร้อมข้อความ ไม่ throw ทิ้งทั้ง batch

### 6.5 Models
- `hr.attendance.device` — ทะเบียนเครื่อง (serial, comm key, location, last activity, online/offline)
- `hr.attendance.device.log` — punch ดิบทั้งหมด (identifier, punch time, punch/verify type, raw data, state)
- `res.company` / `res.config.settings` — สวิตช์และค่าตั้งค่า ZKTeco

## 7. Boundary กับโดเมนอื่น

- กับ Accounting: HR Expense และ Fleet cost ต้อง post ผ่าน `hr_expense` / `account_fleet` ตามมาตรฐาน ไม่เขียน posting logic เอง
- กับ Sales/Service: ไม่เกี่ยวข้อง — Wave 3 ใช้ OCA `helpdesk_mgmt` แยกต่างหาก
- กับ Operations: การลงเวลาเป็นข้อมูลต้นทางของ OT ซึ่งกระทบ payroll (นอก scope)
- กับ Inventory: Fleet ไม่ผูกกับ stock; อะไหล่ซ่อมใช้ purchase ปกติ

## 8. Reporting และ KPI Needs

- รายงานเวลาเข้า–ออกตามพนักงาน/แผนก/ช่วงวันที่
- อัตราการมาสาย (นับจาก 08:31 เป็นต้นไป ตาม decision logic ของบริษัท)
- Punch ที่ยังไม่ถูกประมวลผล (`state = draft`) และ punch ที่ผิดพลาด (`state = error`)
- สถานะเครื่อง: online/offline และ last activity เพื่อแจ้งเตือนเครื่องขาดการเชื่อมต่อ
- ค่าใช้จ่ายพนักงานและค่าใช้จ่ายยานพาหนะแยกตาม project/analytic (ผ่านโมดูลเดิม)

## 9. Security และ Control Model

- Endpoint `/iclock/*` ใช้ `auth='public'` + `csrf=False` และเรียกผ่าน `sudo()` เท่านั้น
- การเข้าถึงทะเบียนเครื่องและ punch log จำกัดด้วย `hr_attendance.group_hr_attendance_user` (อ่าน) และ `hr_attendance.group_hr_attendance_manager` (เขียน/ลบ)
- รองรับ Communication Key ต่อเครื่อง (ถ้าตั้งค่าไว้จะตรวจสอบ key ที่ส่งมา)
- Punch ดิบถูกเก็บถาวรเพื่อ audit ก่อนถูก pair เป็น attendance

## 10. Migration Assumptions

- ข้อมูลพนักงานและ master data อ้างอิงจาก Odoo 15 ในเชิง business flow เท่านั้น ไม่ยกโครงสร้างตารางเดิม
- Badge ID / PIN ต้องถูกตั้งค่าใน `hr.employee` ให้ตรงกับที่บันทึกในเครื่องสแกน
- ยอดวันลาคงเหลือจากระบบเดิมจะถูกยกมาเป็นยอดตั้งต้น (opening) ตามข้อตกลง HR

## 11. Training Impact

- HR: วิธีตั้งค่าเครื่องในหน้า Settings, วิธีตรวจ Punch Log และแก้ punch ที่ state ไม่ใช่ processed
- IT: วิธีตั้งค่า Cloud Server/ADMS บนเครื่อง ZKTeco, การเปิดพอร์ตให้เครื่องเข้าถึง Odoo
- พนักงาน: รับทราบว่าการสแกนหน้าคือการลงเวลาเข้า–ออกจริง

## 12. Test Strategy

- Unit/Integration tests (post-install) ใน `od19_hr_attendance_zkteco`:
  - serial number ต้องไม่ซ้ำ
  - ค้นหา device จาก serial
  - punch สร้าง check-in แล้วปิดด้วย check-out
  - punch ที่ไม่รู้จัก employee → `no_employee`
  - punch ซ้ำภายใน grace → `duplicate`
  - matching ด้วย PIN
  - cron ประมวลผล punch ที่ค้างทั้งหมด
- HTTP contract tests:
  - handshake `/iclock/cdata` (GET) ตอบ `GET OPTION FROM: <SN>`
  - upload ATTLOG (POST) ตอบ `OK: <n>`
  - `/iclock/ping` และ `/iclock/getrequest` ตอบ `OK`
- ผลการรัน: 10 tests ผ่านทั้งหมด บนฐานข้อมูล `odoo19`

## 13. Known Unknowns

- รายการเครื่องจริงและหมายเลข SN ที่จะ deploy
- Timezone ที่ตั้งบนเครื่องสแกนเทียบกับ timezone บริษัท
- นโยบาย OT และกะทำงานที่ยังไม่ยืนยัน
- แผนการยกยอดวันลาคงเหลือจากระบบเดิม

## 14. Definition of Done ระดับสเปก

- `hr_attendance` และ `hr_holidays` ติดตั้งใน `odoo19` และ `odoo19_pdev`
- `od19_hr_attendance_zkteco` ติดตั้งสำเร็จทั้งสองฐานข้อมูล และ log ไม่มี warning จากโมดูลนี้
- ทดสอบ 10 เคสผ่านทั้งหมด
- มีเมนู Configuration > ZKTeco Devices (Devices, Punch Logs) และ settings block ในหน้า Settings
- ไม่มีการแก้ไขไฟล์ core ของ Odoo

## 15. Gate Readiness Summary

- Spec-ready: ✅ ขอบเขตและ boundary ถูกนิยามชัด
- Plan-ready: ✅ addon boundary, protocol, security และ test strategy ชัด
- Build-ready: ✅ ติดตั้งและทดสอบผ่านบน `odoo19` และ `odoo19_pdev`

## 16. คำตัดสินของ Child Spec นี้

ใช้ standard `hr_attendance` + `hr_holidays` เป็นแกนเวลาและวันลา และเพิ่มโมดูล `od19_hr_attendance_zkteco` เป็นช่องทางรับข้อมูลจากเครื่องสแกน ZKTeco ผ่านโปรโตคอล ADMS/iClock (Push) โดยไม่แก้ไข core และไม่เพิ่ม dependency ภายนอกที่ยังไม่มีในสภาพแวดล้อม เหมาะกับบริบท Auto-Info ที่ต้องการ lean, stable, secure และดูแลรักษาง่ายในระยะยาว
