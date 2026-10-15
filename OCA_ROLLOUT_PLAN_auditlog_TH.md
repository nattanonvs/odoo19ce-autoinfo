# แผนติดตั้ง / โรลเอาต์ — โมดูล `auditlog` (OCA Audit Log)

> ⚠️ **PROPOSED CHANGE — NOT EXECUTED**
> เอกสารนี้เป็น **แผน** เท่านั้น ยังไม่มีการติดตั้ง อัปเกรด แก้ไข config/สิทธิ์ หรือรีสตาร์ตบริการใด ๆ ทุกคำสั่งในเอกสารนี้เป็น *ข้อเสนอ* ที่ต้องได้รับอนุมัติก่อนดำเนินการ

| หัวข้อ | ค่า |
| --- | --- |
| โมดูล | Audit Log |
| ชื่อเทคนิค | `auditlog` |
| Repository | `OCA/server-tools` → `third_party/oca/server-tools/auditlog` |
| เวอร์ชัน (manifest) | `19.0.2.0.0` |
| License | AGPL-3 |
| Dependencies | `base` (เท่านั้น — ไม่มี dependency ภายนอก/pip เพิ่ม) |
| `application` | `True` |
| หมวด OCA | B — Monitoring & Anomaly Detection |
| ลำดับความสำคัญ | **P1** |
| ความเสี่ยง | **MEDIUM** |
| สถานะความเข้ากันได้ | Manifest ตรง 19.0 · รันไทม์ **COMPATIBILITY NOT VERIFIED (runtime)** |

---

## 1. เหตุผลและเป้าหมาย

**ปัญหาที่แก้:** ปัจจุบันระบบไม่มีบันทึกการตรวจสอบการเขียน/ลบข้อมูลเลย ทำให้:
- ไม่สามารถตอบคำถาม "ใครแก้/ลบเรกคอร์ดนี้ เมื่อไร ค่าเดิมคืออะไร" ได้
- ISO 9001 ต้องการการตรวจสอบย้อนหลังของเอกสารควบคุม
- ไม่มีหลักฐานประกอบการตรวจสอบทางการเงิน/ภาษี

**ผลลัพธ์ที่ต้องการ (Owner Value):**
1. ตรวจสอบย้อนหลังได้ระดับฟิลด์ (ค่าเก่า → ค่าใหม่) พร้อมผู้ใช้/เวลา/IP
2. มีหลักฐานสำหรับ ISO 9001 และการตรวจสอบภายใน
3. ระบุความผิดปกติ (anomaly) เช่น การแก้ไขย้อนหลัง การลบผิดพลาด

**สิ่งที่อยู่นอกขอบเขต (Out of scope):**
- ไม่ใช่ระบบอนุมัติ (ใช้ `base_tier_validation` ที่มีอยู่)
- ไม่ใช่ monitoring ระดับ infrastructure (ใช้ `sentry` แยก)
- ไม่แทนที่ field tracking ของ Odoo (`mail.thread`) — ใช้ร่วมกัน

---

## 2. ข้อกำหนดเบื้องต้น (Prerequisites)

| # | รายการ | สถานะที่ต้องยืนยัน |
| --- | --- | --- |
| 1 | submodule `third_party/oca/server-tools` มีอยู่และ checkout branch 19.0 | พบแล้ว (ตรวจ manifest แล้ว) |
| 2 | `addons_path` รวม `third_party/oca/server-tools` | พบแล้วใน `odoo.conf` |
| 3 | ไม่มี Python dependency เพิ่ม | ยืนยัน: depends เพียง `base` |
| 4 | มี backup ฐานข้อมูล + filestore ที่กู้คืนได้ก่อนติดตั้ง | ต้องทำก่อน (ดูข้อ 5) |
| 5 | พื้นที่ดิสก์เพียงพอสำหรับตาราง log + retention | ต้องประเมิน |
| 6 | ยืนยันว่า `auditlog` = "to install" ในสคีมา 19.0.1.3 | ต้องตรวจ `ir_module_module` |

**หมายเหตุ License:** โมดูลเป็น AGPL-3 — ใช้ภายในองค์กร (ไม่แจกจ่าย/ไม่เปิดเป็นบริการสาธารณะ) ไม่ก่อภาระเผยแพร่ซอร์ส แต่ควรบันทึกไว้ในการทบทวนสิทธิ์

---

## 3. รูปแบบข้อมูลและองค์ประกอบที่จะเกิดขึ้น

จากซอร์สจริงของโมดูล:

**โมเดล (ตารางใหม่):**
- `auditlog.rule` — กฎการตรวจสอบ (โมเดลเป้าหมาย, ฟิลด์ที่บันทึก, การ subscribe)
- `auditlog.log` — หัวบันทึก (โมเดล/เรกคอร์ด/การดำเนินการ/ผู้ใช้/เวลา)
- `auditlog.log.line` — รายละเอียดระดับฟิลด์ (ค่าเก่า/ค่าใหม่)
- `auditlog.log.line.view` — มุมมองประกอบ
- `auditlog.http.request` — ข้อมูล HTTP request (IP, method, URL)
- `auditlog.http.session` — ข้อมูล session ที่เกี่ยวข้อง
- `auditlog.autovacuum` (wizard) — ลบ log เก่า

**กลุ่มสิทธิ์ (Odoo 19 ใช้ `res.groups.privilege` + `privilege_id`):**
- `auditlog.group_auditlog_user` — อ่าน log เท่านั้น (ผ่าน action "View Logs" บนเรกคอร์ดที่ถูกติดตาม)
- `auditlog.group_auditlog_manager` — จัดการกฎการตรวจสอบ
- `base.group_system` (ERP Administrator) → สืบทอด `group_auditlog_manager` อัตโนมัติ

**Scheduled Action (สร้างให้ แต่ปิดไว้):**
- ชื่อ `Auto-vacuum audit logs`, code `model.autovacuum(180)`, รอบ 1 วัน, `active = False`
- ต้องเปิดใช้งานเอง + ตั้ง retention ตามนโยบาย

**Migration:** มี `migrations/19.0.1.0.0/post-migration.py` (ทำงานอัตโนมัติตอนอัปเกรด)

**เมนู:** Settings / Technical / Audit / Rules และ Settings / Technical / Audit / Logs

---

## 4. ลำดับสภาพแวดล้อม (ตามนโยบาย 5 สภาพแวดล้อมของโครงการ)

ห้ามติดตั้งบน Production ก่อนผ่านขั้นก่อนหน้า:

```
Local Dev → Shared Dev/Integration → Test/QA → UAT/Training → Production
```

| สภาพแวดล้อม | เป้าหมายของรอบนี้ |
| --- | --- |
| Local Dev (Windows) | ติดตั้ง + ตั้งกฎ + ทดสอบฟังก์ชัน + วัดผลกระทบ |
| Shared Dev/Integration | ยืนยันว่าไม่ขัดกับโมดูลกำหนดเอง/OCA ที่ติดตั้ง |
| Test/QA | ทดสอบภาระงาน (write volume) + autovacuum |
| UAT/Training | ผู้ตรวจสอบ/MR ใช้งานจริง, ตรวจ ACL |
| Production | เปิดใช้จริงหลังผ่าน UAT + มีแผนย้อนกลับ |

---

## 5. ขั้นตอนติดตั้ง (PROPOSED — ยังไม่ดำเนินการ)

### ขั้นที่ 1 — Pre-flight (อ่านเท่านั้น)
- [ ] ยืนยันเวอร์ชันจริง: `ir_module_module` มี `auditlog` state = `uninstalled`/ยังไม่มี
- [ ] ตรวจว่ารายการที่ติดตั้ง ~234 ไม่มีโมดูลที่ดึงตารางทับซ้อน
- [ ] ตรวจพื้นที่ดิสก์และขนาด DB ปัจจุบัน
- [ ] บันทึก baseline: จำนวนเรกคอร์ดในตารางที่จะถูกติดตาม + เวลาตอบสนองปัจจุบัน

### ขั้นที่ 2 — Backup (บังคับก่อนติดตั้ง)
- [ ] `pg_dump` ฐานข้อมูล `odoo19` (ใช้ `.pgpass` หรือ prompt แบบ interactive — **ห้ามใส่รหัสผ่านใน command line**)
- [ ] สำรอง filestore `C:\odoo-dev\odoo19\data`
- [ ] ทดสอบกู้คืนบนฐานข้อมูลชั่วคราว

### ขั้นที่ 3 — ติดตั้งโมดูล
ทางเลือก A (UI — แนะนำบน Dev):
- Apps → Update Apps List → ค้นหา "Audit Log" → Install

ทางเลือก B (CLI — แนะนำบน Integration/QA):
```
python odoo-bin -c odoo.conf -d odoo19 -i auditlog --stop-after-init
```
(ปรับพาธ `odoo-bin`/`odoo.conf` ตามสภาพแวดล้อม Windows/Linux)

### ขั้นที่ 4 — รีสตาร์ตและตรวจสอบ
- [ ] รีสตาร์ตบริการ Odoo (Windows service / systemd)
- [ ] ตรวจ `odoo_server.log` ว่าไม่มี ERROR/WARNING จาก `auditlog`
- [ ] ยืนยัน Registry โหลดครบ (จำนวนโมดูลเท่าเดิม +1)

### ขั้นที่ 5 — ตั้งค่าหลังติดตั้ง
- [ ] เปิดใช้งาน `Auto-vacuum audit logs` (Scheduled Actions) และตั้ง retention ตามนโยบาย
- [ ] กำหนดผู้ใช้เข้ากลุ่ม `Auditlog Manager` (ผู้ดูแลระบบเท่านั้น)
- [ ] กำหนดผู้ใช้เข้ากลุ่ม `Auditlog User` (ผู้ตรวจสอบภายใน/บัญชี — อ่านเท่านั้น)
- [ ] พิจารณา PostgreSQL autovacuum ของตาราง `auditlog_log*` (โมดูลอ้างถึงการปรับค่านี้ใน description)

---

## 6. การกำหนดขอบเขตโมเดล (Model Scoping Matrix)

> หลักการ: **เลือกเฉพาะโมเดลที่สำคัญ** — ไม่เปิดทั้งระบบ เพื่อควบคุม write amplification
> ทุกกฎใหม่ต้อง "Subscribe" จึงจะเริ่มบันทึก

| ลำดับ | โมเดล | เหตุผล | ระดับ |
| --- | --- | --- | --- |
| 1 | `sale.order` | สัญญา/ใบเสนอราคา, ส่วนลด, เงื่อนไข | สูง |
| 2 | `account.move` | ใบแจ้งหนี้/ใบกำกับภาษี — การเงิน/ภาษี | สูง |
| 3 | `account.payment` | การชำระเงิน/เช็ค/ค่าธรรมเนียม | สูง |
| 4 | `purchase.order` | จัดซื้อ, ราคา, ผู้ขาย | สูง |
| 5 | `res.partner` | เครดิต/แบล็คลิสต์ (กำหนดฟิลด์ที่ติดตาม) | สูง |
| 6 | `sales.contract` (od19) | วงเงิน/การใช้จริงตามสัญญาหลัก | สูง |
| 7 | `account.cheque` / `account.cheque.book` (od19) | สมุดเช็ค | กลาง |
| 8 | `iso.document` (od19) | เอกสารควบคุม ISO — ตรวจสอบย้อนหลัง | กลาง |
| 9 | `account.asset` (OCA) | การตัดจำหน่าย/โอนสินทรัพย์ | กลาง |
| 10 | `product.return` (od19) | RMA/การคืนสินค้า | กลาง |

**โมเดลที่ควร "ยกเว้น" (ห้ามติดตาม):** `mail.message`, `mail.tracking.value`, `mail.followers`, `bus.bus`, `ir.logging`, `ir.cron`, `ir.attachment` (ปริมาณสูง), และตาราง `auditlog.*` เอง

**สำหรับ `res.partner`:** ไม่ควรติดตามทุกฟิลด์ — เลือกเฉพาะ `credit_limit`, สถานะแบล็คลิสต์, เงื่อนไขการชำระ เนื่องจากมี write ปริมาณสูง

---

## 7. ผลกระทบและแนวทางปรับประสิทธิภาพ

| ประเด็น | ผลกระทบ | แนวทาง |
| --- | --- | --- |
| Write amplification | ทุก create/write/unlink ของโมเดลที่ติดตามจะเขียนเพิ่ม (หัว + บรรทัดต่อฟิลด์ที่เปลี่ยน) | จำกัดโมเดล/ฟิลด์ (ข้อ 6) |
| ขนาด DB | ตาราง `auditlog_log*` โตต่อเนื่อง | เปิด autovacuum cron + ตั้ง retention |
| `workers = 0` (threaded) | การวัดผลกระทบต้องวัดในโหมดรันไทม์จริง | วัดก่อน/หลังบน Integration; พิจารณา `workers=N` แยกเป็นอีกงาน |
| การลบ (unlink) | พฤติกรรมการบันทึกการลบ (รวม cascade/SQL-level) | **ต้องยืนยันในขั้นทดสอบ** — ระบุ COMPATIBILITY NOT VERIFIED |
| PostgreSQL autovacuum | ตาราง log อาจทำให้ autovacuum ทำงานหนัก | พิจารณาปรับ per-table autovacuum |
| ขนาดตารางล็อกของ DB | เพิ่มขึ้นจาก baseline | เทียบ baseline ข้อ 5.1 |

---

## 8. ความปลอดภัยและการเข้าถึง

- **อ่าน log:** เฉพาะกลุ่ม `auditlog.group_auditlog_user` ขึ้นไป
- **จัดการกฎ:** เฉพาะกลุ่ม `auditlog.group_auditlog_manager` (ผู้ดูแลระบบได้มาอัตโนมัติ)
- **ระวัง:** log อาจมีข้อมูลอ่อนไหว (ค่าเก่า/ใหม่ของฟิลด์การเงิน) → จำกัดผู้เข้าถึง
- **ห้าม** ให้สิทธิ์ Manager แก่ผู้ใช้ทั่วไป เพราะสามารถปิด/แก้กฎเพื่อลบร่องรอยได้
- พิจารณาแยกกลุ่มสำหรับ "ผู้ตรวจสอบภายใน/ISO" แบบอ่านอย่างเดียว
- ตรวจสอบว่าไม่มี record rule ของโมดูลกำหนดเองที่บังเอิญเปิด/ปิดการเข้าถึง `auditlog.*`

---

## 9. เกณฑ์การยอมรับ (Acceptance Criteria)

ต้องผ่านทุกข้อบน Integration/QA ก่อนไป UAT:

1. แก้ไขเรกคอร์ด `sale.order` → เกิด `auditlog.log` + `log.line` ที่บันทึกค่าเก่า/ใหม่ถูกต้อง
2. สร้าง/แก้ `account.move` → บันทึกครบพร้อมผู้ใช้และเวลา
3. ลบเรกคอร์ดที่ติดตาม → มีบันทึกการลบ (**ต้องยืนยันว่าทำงานจริง**)
4. เปิด action "View Logs" บนเรกคอร์ด → เห็นเฉพาะ log ของเรกคอร์ดนั้น
5. โมเดลที่ **ไม่ได้** สร้างกฎ → ไม่เกิด log (ยืนยันว่าไม่ leak)
6. ผู้ใช้ที่ไม่มีกลุ่ม `Auditlog User` → เข้าเมนู Logs ไม่ได้
7. `Auto-vacuum` ทำงาน: ลบ log เก่ากว่า N วันตามที่ตั้ง
8. ไม่มี ERROR/WARNING ใหม่ใน `odoo_server.log` หลังรีสตาร์ต
9. เวลาตอบสนองของ write หลักไม่แย่ลงเกินเกณฑ์ที่ยอมรับ (วัดจาก baseline ข้อ 5.1)

*(โมดูลมีชุดทดสอบของตัวเองในโฟลเดอร์ `tests/` — สามารถอ้างอิงเป็นแนวทางได้)*

---

## 10. การตรวจสอบหลังติดตั้ง (Monitoring)

- ตรวจขนาดตาราง `auditlog_log`, `auditlog_log_line` รายสัปดาห์
- ตรวจว่า cron autovacuum ทำงานจริง (ไม่มี = DB โตไม่หยุด)
- ดู `odoo_server.log` ว่าไม่มี warning จาก auditlog
- เมื่อติดตั้ง `sentry`/`scheduler_error_mailer` แล้ว จะได้การแจ้งเตือนอัตโนมัติ

---

## 11. แผนย้อนกลับ (Rollback)

| สถานการณ์ | การดำเนินการ |
| --- | --- |
| โหลดโมดูลล้มเหลว | ตรวจ log, ยังไม่ต้องถอน; แก้ dependency/พาธ |
| ประสิทธิภาพแย่เกินเกณฑ์ | ปิด (unsubscribe) กฎโมเดลที่หนักก่อน — ไม่ต้องถอนโมดูล |
| ต้องถอนทั้งหมด | Uninstall ผ่าน Apps → **ตาราง `auditlog.*` และประวัติ log จะหาย** → ต้อง export log ก่อนถอน |
| ฐานข้อมูลเสียหาย | กู้คืนจาก backup ในข้อ 5.2 |

**คำเตือนสำคัญ:** การถอนโมดูลทำให้ **สูญเสียประวัติการตรวจสอบทั้งหมด** — ต้องพิจารณาเก็บถาวรแยกก่อน

---

## 12. ความเสี่ยงและแนวทางบรรเทา

| ความเสี่ยง | ระดับ | แนวทางบรรเทา |
| --- | --- | --- |
| Write latency เพิ่มจากการติดตามมากเกินไป | MEDIUM | จำกัดโมเดล/ฟิลด์ + วัดก่อน/หลัง |
| DB โตไม่หยุด (ไม่เปิด autovacuum) | MEDIUM | เปิด cron + retention + ตรวจรายสัปดาห์ |
| ผู้มีสิทธิ์ Manager ปิดร่องรอย | MEDIUM | จำกัดกลุ่มแคบ + ตรวจการเปลี่ยนกฎผ่าน `sentry`/audit ของ Odoo |
| สูญเสีย log เมื่อถอนโมดูล | MEDIUM | export ก่อนถอน + backup |
| พฤติกรรมการบันทึก unlink ไม่ตรงคาดหวัง | MEDIUM | ทดสอบยืนยันใน QA ก่อน UAT (เกณฑ์ข้อ 9.3) |
| ความเข้ากันได้รันไทม์กับ 19.0 ยังไม่พิสูจน์ | MEDIUM | ติดตั้งบน Local/Integration ก่อนเสมอ |

---

## 13. รายการงานตามลำดับ (Task Checklist — ไม่ระบุเวลา)

- [ ] T1 Pre-flight checks + baseline (ข้อ 5.1)
- [ ] T2 Backup DB + filestore + ทดสอบกู้คืน (ข้อ 5.2)
- [ ] T3 ติดตั้งบน Local Dev (ข้อ 5.3)
- [ ] T4 รีสตาร์ต + ตรวจ log/registry (ข้อ 5.4)
- [ ] T5 สร้างกฎตาม Model Scoping Matrix (ข้อ 6)
- [ ] T6 ตั้งกลุ่มสิทธิ์ (ข้อ 8)
- [ ] T7 เปิด autovacuum cron + retention (ข้อ 5.5)
- [ ] T8 ทดสอบตามเกณฑ์การยอมรับ (ข้อ 9)
- [ ] T9 วัดผลกระทบประสิทธิภาพ เทียบ baseline (ข้อ 7)
- [ ] T10 ย้ำบน Shared Dev/Integration → Test/QA → UAT ตามลำดับ (ข้อ 4)
- [ ] T11 เตรียม rollback + export log (ข้อ 11)
- [ ] T12 อนุมัติ go/no-go ก่อน Production

---

## 14. การอนุมัติและหลักฐานที่ต้องเก็บ (Discovery Evidence)

| ผู้รับผิดชอบ | หน้าที่ |
| --- | --- |
| Config owner | ยืนยัน `odoo.conf`/addons_path ไม่เปลี่ยนนอกแผน |
| Deployment owner | รันขั้นตอนติดตั้ง + เก็บหลักฐานทุกรอบ |
| Security reviewer | ตรวจกลุ่ม `Auditlog Manager/User` และการเข้าถึง log |
| Backup owner | ยืนยัน backup + restore สำเร็จก่อนติดตั้ง |
| Incident first responder | เฝ้าระหว่างติดตั้ง Production |

**หลักฐานที่ต้องเก็บทุกรอบ:** ผล pre-flight, log การติดตั้ง, ภาพหน้าจอกฎที่สร้าง, ผลทดสอบเกณฑ์ยอมรับ, ค่า perf ก่อน/หลัง, ผลทดสอบ restore

---

## 15. ภาคผนวก — คำสั่งอ้างอิง (PROPOSED — ยังไม่รัน)

ติดตั้ง (CLI):
```
python odoo-bin -c odoo.conf -d odoo19 -i auditlog --stop-after-init
```
อัปเดตโมดูลภายหลัง:
```
python odoo-bin -c odoo.conf -d odoo19 -u auditlog --stop-after-init
```
ตรวจสถานะโมดูล (อ่านเท่านั้น — ผ่าน UI: Apps / Technical / Modules) หรือ SQL:
```sql
SELECT name, state, latest_version FROM ir_module_module WHERE name = 'auditlog';
```
ตรวจขนาดตาราง log (อ่านเท่านั้น):
```sql
SELECT pg_size_pretty(pg_total_relation_size('auditlog_log')),
       pg_size_pretty(pg_total_relation_size('auditlog_log_line'));
```

> หมายเหตุ: ห้ามใส่รหัสผ่านฐานข้อมูลใน command line ให้ใช้ `.pgpass` หรือ interactive prompt เท่านั้น

---

**สรุป:** แผนนี้อ้างอิงซอร์สจริงของ `auditlog` 19.0.2.0.0 (depends เพียง `base`, มีกลุ่มสิทธิ์ `Auditlog User/Manager`, cron autovacuum ปิดไว้โดยค่าเริ่มต้น) ความเสี่ยงหลักคือผลกระทบประสิทธิภาพและขนาด DB ซึ่งควบคุมได้ด้วยการจำกัดขอบเขตโมเดลและ retention — **ยังไม่มีการดำเนินการใด ๆ ตามแผนนี้**
