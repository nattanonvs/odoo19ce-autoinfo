# แผนติดตั้ง / โรลเอาต์ — โมดูล OCA กลุ่ม P1 ชุดที่เหลือ (8 โมดูล)

> ⚠️ **PROPOSED CHANGE — NOT EXECUTED**
> เอกสารนี้เป็น **แผน** เท่านั้น **ยังไม่มีการติดตั้ง อัปเกรด ถอน แก้ไข config/สิทธิ์/record rule หรือรีสตาร์ตบริการใด ๆ**
> ทุกคำสั่งในเอกสารนี้เป็น *ข้อเสนอ* ที่ต้องได้รับอนุมัติก่อนดำเนินการ
> ฉบับนี้เป็นภาคต่อของ [OCA_ROLLOUT_PLAN_auditlog_TH.md](file:///c:/odoo-dev/odoo19/OCA_ROLLOUT_PLAN_auditlog_TH.md) โดยใช้โครงสร้าง 15 หัวข้อเดียวกัน

---

## ภาพรวมชุด P1 ที่เหลือ

เรียงตาม **ความเสี่ยงจากน้อยไปมาก** (แนะนำให้ติดตั้งตามลำดับนี้ เพื่อสร้างชั้นความปลอดภัย/ย้อนกลับก่อนแตะโมดูลที่เสี่ยงสูง)

| # | โมดูล | หมวด | ความเสี่ยง | pip เพิ่ม | depends เพิ่ม | เหตุผลหลัก |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `base_cron_exclusion` | Performance | LOW | ไม่มี | `base` | แก้ปัญหา cron ทับซ้อน (workers=0) |
| 2 | `scheduler_error_mailer` | Monitoring | LOW | ไม่มี | `mail` | แจ้งเตือน cron ล้มเหลวทางอีเมล |
| 3 | `base_export_manager` | Security | LOW–MEDIUM | ไม่มี | `web` | คุมสิทธิ์/โปรไฟล์การ export |
| 4 | `session_db` | Infrastructure | MEDIUM | ไม่มี | (patch, ใช้ `base`) | เก็บ session ลง DB |
| 5 | `sentry` | Monitoring | MEDIUM–HIGH | `sentry_sdk>=2.0.0,<=2.22.0` | `base` | Error tracking + alerting |
| 6 | `auto_backup` | Prevention | MEDIUM–HIGH | `paramiko<4.0.0`, `pysftp`, `cryptography` | `mail` | สำรอง DB อัตโนมัติ |
| 7 | `bi_sql_editor` | Reporting | MEDIUM–HIGH | ไม่มี | `spreadsheet_dashboard`, `sql_request_abstract` | รายงาน SQL/materialized view |
| 8 | `database_cleanup` | Utilities (destructive) | HIGH | ไม่มี | `base` | ล้างขยะ DB/module/field |

**หมายเหตุความเข้ากันได้:** ทุกโมดูลเป็น manifest `19.0.x` (ยืนยันแล้ว) แต่ **ระดับรันไทม์ยังไม่พิสูจน์ → COMPATIBILITY NOT VERIFIED (runtime)** ทุกจุด

---

# 1) `base_cron_exclusion` — Base Cron Exclusion

| หัวข้อ | ค่า |
| --- | --- |
| Repository | `OCA/server-tools` → `third_party/oca/server-tools/base_cron_exclusion` |
| เวอร์ชัน | `19.0.1.0.0` |
| License | LGPL-3 |
| Dependencies | `base` เท่านั้น |
| pip เพิ่ม | ไม่มี |
| Development status | **Production/Stable** |
| หมวด | A — Performance & Optimization |
| ลำดับความสำคัญ | **P1** |
| ความเสี่ยง | **LOW** |
| สถานะความเข้ากันได้ | Manifest ตรง 19.0 · รันไทม์ **COMPATIBILITY NOT VERIFIED (runtime)** |

**1. เหตุผลและเป้าหมาย** — ระบบรัน `workers = 0` (threaded) ซึ่งทำให้ cron ที่ทำงานพร้อมกันทับซ้อนกันได้ (บทเรียนเดิม: ความไม่เสถียรของ cron ทับซ้อน) โมดูลนี้ให้เลือกได้ว่า scheduled action ใด **ห้ามทำงานพร้อมกัน** เพื่อลด lock contention และการเขียนทับกันเอง — เป้าหมาย: cron ที่แข่งทรัพยากรกัน (เช่น autovacuum, sync, mail) ไม่รันซ้อน

**2. ข้อกำหนดเบื้องต้น** — submodule `server-tools` (พบแล้ว) · `addons_path` รวมพาธ (พบแล้ว) · ไม่มี pip เพิ่ม · มี backup ก่อนติดตั้ง

**3. องค์ประกอบที่จะเกิด** — ฟิลด์เพิ่มบน `ir.cron` (เลือก cron ที่ไม่ควรทำงานพร้อมกัน) + ไฟล์ view `views/ir_cron_view.xml` · **ไม่มีตาราง/โมเดลใหม่** · ไม่มีกลุ่มสิทธิ์ใหม่

**4. ลำดับสภาพแวดล้อม** — Local Dev → Shared Dev → Test/QA → UAT → Production (ตามนโยบาย 5 สภาพแวดล้อม)

**5. ขั้นตอนติดตั้ง (PROPOSED)**
- 5.1 Pre-flight: บันทึก baseline ของ cron ที่ทำงานถี่/หนัก (รายชื่อ + เวลา)
- 5.2 Backup DB + filestore + ทดสอบกู้คืน
- 5.3 ติดตั้ง: `python odoo-bin -c odoo.conf -d odoo19 -i base_cron_exclusion --stop-after-init`
- 5.4 รีสตาร์ต + ตรวจ `odoo_server.log` ว่าไม่มี ERROR/WARNING ใหม่
- 5.5 ตั้งค่า: ผูก cron ที่แข่งทรัพยากรกันเข้าด้วยกัน

**6. การตั้งค่า** — เลือกคู่/กลุ่ม cron ที่ควร "exclude" กัน เช่น cron sync ภายนอกกับ cron สร้างรายงานหนัก, ให้ cron สำคัญไม่ถูกกันเวลาโดยไม่จำเป็น

**7. ผลกระทบประสิทธิภาพ** — positive: ลด overlap/lock · ข้อควรระวัง: ถ้าตั้ง exclusion ผิด อาจทำให้ cron บางตัว "รอ" นานขึ้น → ตรวจคิว/`nextcall`

**8. ความปลอดภัย** — ไม่มีผลต่อ ACL (ไม่มีโมเดลใหม่) · จำกัดเฉพาะผู้ดูแลระบบที่แก้ `ir.cron`

**9. เกณฑ์การยอมรับ**
1. cron ที่ผูก exclusion ไม่รันพร้อมกันจริง (ดู log/เวลา)
2. cron อื่นไม่ได้รับผลกระทบ
3. ไม่มี ERROR/WARNING ใหม่ใน log
4. จำนวนโมดูลหลังติดตั้ง +1, registry โหลดครบ

**10. Monitoring** — เฝ้า `nextcall` ของ cron ที่ผูก exclusion ว่าคิวไม่ยาวผิดปกติ · ตรวจ log ว่าไม่มี cron ค้าง

**11. Rollback** — ถอนผ่าน Apps ได้ (ไม่มีการทำลายข้อมูล) หรือเพียงเลิกตั้งค่า exclusion · DB/filestore ปลอดภัยจาก backup 5.2

**12. ความเสี่ยง**

| ความเสี่ยง | ระดับ | บรรเทา |
| --- | --- | --- |
| ตั้ง exclusion ผิด → cron รอนาน | LOW | ทดสอบบน Integration, เริ่มจากคู่น้อย |
| รันไทม์กับ 19.0 ยังไม่พิสูจน์ | LOW | ติดตั้งบน Local/Integration ก่อน |

**13. Task Checklist** — T1 baseline cron · T2 backup+restore · T3 ติดตั้ง Local · T4 รีสตาร์ต+ตรวจ log · T5 ตั้ง exclusion · T6 ทดสอบเกณฑ์ยอมรับ · T7 ย้ำ Integration→QA→UAT · T8 rollback plan · T9 go/no-go

**14. การอนุมัติ/หลักฐาน** — Deployment owner เก็บ log ติดตั้ง + รายการ cron ที่ตั้ง exclusion · Config owner ยืนยัน config ไม่เปลี่ยน

**15. ภาคผนวกคำสั่ง (PROPOSED)**
```
python odoo-bin -c odoo.conf -d odoo19 -i base_cron_exclusion --stop-after-init
```
```sql
SELECT name, state, latest_version FROM ir_module_module WHERE name = 'base_cron_exclusion';
```

---

# 2) `scheduler_error_mailer` — Scheduler Error Mailer

| หัวข้อ | ค่า |
| --- | --- |
| Repository | `OCA/server-tools` → `third_party/oca/server-tools/scheduler_error_mailer` |
| เวอร์ชัน | `19.0.1.0.0` |
| License | AGPL-3 |
| Dependencies | `mail` |
| pip เพิ่ม | ไม่มี |
| Hook | มี `post_init_hook` |
| หมวด | B — Monitoring & Anomaly Detection |
| ลำดับความสำคัญ | **P1** |
| ความเสี่ยง | **LOW** |
| สถานะความเข้ากันได้ | Manifest ตรง 19.0 · รันไทม์ **COMPATIBILITY NOT VERIFIED (runtime)** |

**1. เหตุผลและเป้าหมาย** — ปัจจุบัน cron ที่ล้มเหลวจะเงียบ (เหลือเพียง traceback ใน log) โมดูลนี้ผูกอีเมลเทมเพลตแจ้งเตือนเข้ากับ `ir.cron` ทุกตัว → ผู้ดูแลได้รับอีเมลเมื่อ scheduled action ล้มเหลว — เป้าหมาย: ไม่มี cron ล้มเหลวแบบเงียบ

**2. ข้อกำหนดเบื้องต้น** — `mail` ติดตั้งแล้ว (มีอยู่) · มี outgoing mail server ที่ใช้งานได้ · มีผู้รับอีเมลแจ้งเตือน · backup ก่อนติดตั้ง

**3. องค์ประกอบที่จะเกิด** — อีเมลเทมเพลต `scheduler_error_mailer.scheduler_error_mailer` (จาก `data/ir_cron_email_tpl.xml`) · view เพิ่มบน `ir.cron` (`views/ir_cron.xml`) · **`post_init_hook` จะเขียน `email_template_id` ให้ `ir.cron` ทุกตัว (รวมที่ inactive)** โดยอัตโนมัติ · ไม่มีตารางใหม่

**4. ลำดับสภาพแวดล้อม** — Local Dev → Shared Dev → Test/QA → UAT → Production

**5. ขั้นตอนติดตั้ง (PROPOSED)**
- 5.1 Pre-flight: ยืนยัน outgoing mail server ทำงาน (ส่งทดสอบ)
- 5.2 Backup DB + filestore
- 5.3 ติดตั้ง: `python odoo-bin -c odoo.conf -d odoo19 -i scheduler_error_mailer --stop-after-init`
- 5.4 รีสตาร์ต + ตรวจ log; ยืนยัน `post_init_hook` ตั้งเทมเพลตครบ
- 5.5 ตั้งค่า: เลือกผู้รับ/ทดสอบ trigger อีเมล (อาจใช้ cron ทดสอบที่ล้มเหลวโดยตั้งใจ)

**6. การตั้งค่า** — ตรวจว่าเทมเพลต `scheduler_error_mailer.scheduler_error_mailer` มีผู้รับถูกต้อง · พิจารณาแยกผู้รับต่อ cron ถ้าจำเป็น · ยืนยันว่าไม่เกิดอีเมลสแปมจาก cron ที่ล้มเหลวเป็นประจำ

**7. ผลกระทบประสิทธิภาพ** — ไม่มีนัยสำคัญ (ทำงานเฉพาะตอน error) · ระวัง: ถ้า cron ล้มเหลวถี่จะได้อีเมลจำนวนมาก → ตั้งผู้รับเป็นกลุ่ม/distribution list

**8. ความปลอดภัย** — อีเมลข้อผิดพลาดอาจมี traceback ข้อมูลธุรกิจ → จำกัดผู้รับภายในองค์กร · ไม่เพิ่มสิทธิ์ผู้ใช้ (ผู้ใช้ทั่วไปไม่เห็น `ir.cron`)

**9. เกณฑ์การยอมรับ**
1. cron ที่ล้มเหลว → ส่งอีเมลแจ้งเตือนจริง
2. เทมเพลตถูกผูกกับ `ir.cron` ทุกตัวหลังติดตั้ง
3. cron ที่ทำงานปกติ → ไม่มีอีเมล
4. ไม่มี ERROR/WARNING ใหม่ใน log

**10. Monitoring** — ตรวจว่ามีอีเมลแจ้งเตือนเข้ามาจริงในกล่องผู้ดูแล · เฝ้า cron ที่ล้มเหลวซ้ำ (อาจเป็นสัญญาณปัญหาจริง)

**11. Rollback** — ถอนผ่าน Apps ได้ (ไม่มีข้อมูลถูกทำลาย) · เทมเพลต/ฟิลด์ถูกถอดออก · DB ปลอดภัยจาก backup

**12. ความเสี่ยง**

| ความเสี่ยง | ระดับ | บรรเทา |
| --- | --- | --- |
| อีเมลล้นจาก cron ที่ล้มเหลวถี่ | LOW | ตั้งผู้รับเป็นกลุ่ม + แก้ cron ต้นเหตุ |
| Traceback ถูกส่งออกนอก (ถ้าผู้รับภายนอก) | LOW | ใช้ผู้รับภายในเท่านั้น |
| รันไทม์กับ 19.0 ยังไม่พิสูจน์ | LOW | ติดตั้ง Local/Integration ก่อน |

**13. Task Checklist** — T1 ยืนยัน mail server · T2 backup · T3 ติดตั้ง Local · T4 รีสตาร์ต+ตรวจ hook · T5 ตั้งผู้รับ+ทดสอบ · T6 ทดสอบเกณฑ์ยอมรับ · T7 ย้ำ Integration→QA→UAT · T8 rollback plan · T9 go/no-go

**14. การอนุมัติ/หลักฐาน** — เก็บภาพหน้าจอเทมเพลต + ตัวอย่างอีเมลแจ้งเตือนจริง + log ติดตั้ง

**15. ภาคผนวกคำสั่ง (PROPOSED)**
```
python odoo-bin -c odoo.conf -d odoo19 -i scheduler_error_mailer --stop-after-init
```
```sql
SELECT c.id, c.name, c.email_template_id FROM ir_cron c WHERE c.email_template_id IS NULL;
```

---

# 3) `base_export_manager` — Manage model export profiles

| หัวข้อ | ค่า |
| --- | --- |
| Repository | `OCA/server-ux` → `third_party/oca/server-ux/base_export_manager` |
| เวอร์ชัน | `19.0.1.0.0` |
| License | AGPL-3 |
| Dependencies | `web` |
| pip เพิ่ม | ไม่มี |
| Hook | มี `post_init_hook` (inverse `ir.exports.line.name`) |
| Assets | ESM: `base_export_manager/static/src/views/list/list_controller.esm.js` |
| หมวด | G — Access Rights & Security |
| ลำดับความสำคัญ | **P1** |
| ความเสี่ยง | **LOW–MEDIUM** |
| สถานะความเข้ากันได้ | Manifest ตรง 19.0 · รันไทม์ **COMPATIBILITY NOT VERIFIED (runtime)** |

**1. เหตุผลและเป้าหมาย** — Odoo core ให้ทุกคน export ข้อมูลได้กว้าง (ความเสี่ยง data exfiltration / mass export) โมดูลนี้เพิ่ม **โปรไฟล์การ export** ต่อโมเดล และ **จำกัดฟิลด์ที่แต่ละกลุ่มผู้ใช้ส่งออกได้** — เป้าหมาย: คุมการส่งออกข้อมูลอ่อนไหว (ลูกค้า, ราคา, การเงิน)

**2. ข้อกำหนดเบื้องต้น** — `web` (core) · มี backup · ต้องเข้าใจว่ามี `ir.exports` อยู่เดิม (โมดูลจะ inverse ค่า `name` เดิมใน `ir.exports.line`)

**3. องค์ประกอบที่จะเกิด** — โมเดล `ir.exports` (โปรไฟล์) + `ir.exports.line` (ฟิลด์) ถูกขยาย · view เพิ่มบน `ir.exports`, `ir.model`, `ir.model.access`, `res.groups` · asset ESM ใน backend · `post_init_hook` ปรับข้อมูลเก่าให้สอดคล้อง

**4. ลำดับสภาพแวดล้อม** — Local Dev → Shared Dev → Test/QA → UAT → Production

**5. ขั้นตอนติดตั้ง (PROPOSED)**
- 5.1 Pre-flight: ตรวจว่ามี `ir.exports` เดิม/ผู้ใช้ที่ถูกจำกัดการ export
- 5.2 Backup DB + filestore
- 5.3 ติดตั้ง: `python odoo-bin -c odoo.conf -d odoo19 -i base_export_manager --stop-after-init`
- 5.4 รีสตาร์ต + ตรวจ log; ยืนยัน `post_init_hook` ทำงานไม่มี error
- 5.5 ตั้งค่า: สร้างโปรไฟล์ export ต่อโมเดล + ผูกกับกลุ่มผู้ใช้

**6. การตั้งค่า** — กำหนดว่าโมเดลใด "บังคับใช้โปรไฟล์" (ผู้ใช้เลือกฟิลด์เองไม่ได้) และจำกัดฟิลด์อ่อนไหว (เช่น `credit_limit`, ต้นทุน) ไม่ให้กลุ่มทั่วไปส่งออก

**7. ผลกระทบประสิทธิภาพ** — ไม่มีนัยสำคัญ (จำกัดอยู่ที่หน้าจอ export) · asset ESM โหลดที่ backend list view เท่านั้น

**8. ความปลอดภัย** — เป็น **มาตรการป้องกัน**โดยตรง: ลดความเสี่ยง mass export · ต้องทดสอบว่าผู้ใช้ที่ไม่มีสิทธิ์ไม่สามารถ export ฟิลด์ต้องห้ามได้จริง (ทั้ง UI และ RPC) · ยืนยันว่าไม่ปิดกั้นการ export ที่ชอบด้วยกฎหมายของบัญชี/ผู้ตรวจสอบ

**9. เกณฑ์การยอมรับ**
1. ผู้ใช้กลุ่มที่ถูกจำกัด → เลือกฟิลด์ต้องห้ามในหน้า export ไม่ได้
2. การ export ผ่าน UI ใช้โปรไฟล์ที่กำหนด
3. ผู้ใช้ที่ได้รับอนุญาต export ได้ตามปกติ
4. `post_init_hook` ไม่ทำให้ข้อมูล `ir.exports.line` เดิมเสียหาย
5. ไม่มี ERROR/WARNING ใหม่ใน log

**10. Monitoring** — ตรวจ log การ export ที่ถูกปฏิเสธ (ถ้ามี) · ทบทวนโปรไฟล์เมื่อมีโมเดล/ฟิลด์ใหม่

**11. Rollback** — ถอนผ่าน Apps ได้ (โปรไฟล์/ฟิลด์ถูกถอด) · **ควร export รายการโปรไฟล์ไว้ก่อนถอน** · DB ปลอดภัยจาก backup

**12. ความเสี่ยง**

| ความเสี่ยง | ระดับ | บรรเทา |
| --- | --- | --- |
| จำกัดเข้มเกิน → ขวางงานบัญชี/ตรวจสอบ | MEDIUM | ทดสอบกับกลุ่มจริงใน UAT |
| ผู้ใช้ bypass ผ่าน RPC/import | MEDIUM | ทดสอบ RPC + ใช้ร่วมกับ record rules |
| `post_init_hook` ผิดพลาดกับข้อมูลเก่า | LOW | backup + ทดสอบบน Integration |
| รันไทม์กับ 19.0 (asset ESM) ยังไม่พิสูจน์ | MEDIUM | ตรวจหน้า list/export บน Local |

**13. Task Checklist** — T1 สำรวจ `ir.exports` เดิม · T2 backup · T3 ติดตั้ง Local · T4 รีสตาร์ต+ตรวจ hook/asset · T5 สร้างโปรไฟล์+ผูกกลุ่ม · T6 ทดสอบ UI+RPC · T7 ย้ำ Integration→QA→UAT · T8 rollback+export โปรไฟล์ · T9 go/no-go

**14. การอนุมัติ/หลักฐาน** — Security reviewer ยืนยันผลทดสอบการจำกัดฟิลด์ · เก็บภาพหน้าจอโปรไฟล์ + ผลทดสอบ RPC

**15. ภาคผนวกคำสั่ง (PROPOSED)**
```
python odoo-bin -c odoo.conf -d odoo19 -i base_export_manager --stop-after-init
```
```sql
SELECT name, state, latest_version FROM ir_module_module WHERE name = 'base_export_manager';
```

---

# 4) `session_db` — Store sessions in DB

| หัวข้อ | ค่า |
| --- | --- |
| Repository | `OCA/server-tools` → `third_party/oca/server-tools/session_db` |
| เวอร์ชัน | `19.0.1.0.0` |
| License | LGPL-3 |
| Dependencies | (manifest **ไม่มีคีย์ `depends`** → ค่าเริ่มต้นเป็น `base`) |
| pip เพิ่ม | ไม่มี |
| ลักษณะพิเศษ | **Monkey patch** `http.root.session_store` → `PGSessionStore` (ทำงานตอน import) |
| หมวด | A/D — Infrastructure |
| ลำดับความสำคัญ | **P1** |
| ความเสี่ยง | **MEDIUM** |
| สถานะความเข้ากันได้ | Manifest ตรง 19.0 · รันไทม์ **COMPATIBILITY NOT VERIFIED (runtime)** |

**1. เหตุผลและเป้าหมาย** — ปกติ Odoo เก็บ session เป็นไฟล์บนดิสก์ (filestore/sessions) ซึ่งมีปัญหากับ multi-process/การรีสตาร์ต/การย้ายเครื่อง โมดูลนี้ย้าย session ไปเก็บใน **ฐานข้อมูล PostgreSQL** — เป้าหมาย: session คงอยู่ข้ามรีสตาร์ต worker และจัดการรวมศูนย์ได้

**2. ข้อกำหนดเบื้องต้น** — Zip: submodule `server-tools` (พบแล้ว) · **ต้องเข้าใจว่าโมดูลนี้เป็น server-level patch** → โดยทั่วไปต้องให้โหลดผ่าน `server_wide_modules` (เช่น `web,session_db` หรือรวมกับ `sentry`) มิฉะนั้น patch อาจไม่ถูกนำไปใช้ · backup ก่อนติดตั้ง

**3. องค์ประกอบที่จะเกิด** — ไม่มีโมเดล/ตาราง Odoo ที่มองเห็น (อาจมีตาราง session ระดับ DB ที่ patch จัดการ) · ไม่มีกลุ่มสิทธิ์ใหม่ · **ไม่มี `data/security/view`** · มีชุดทดสอบ `tests/test_pg_session_store.py`

**4. ลำดับสภาพแวดล้อม** — Local Dev → Shared Dev → Test/QA → UAT → Production *(ต้องระวังเป็นพิเศษ: กระทบการล็อกอินทั้งระบบ)*

**5. ขั้นตอนติดตั้ง (PROPOSED)**
- 5.1 Pre-flight: บันทึกค่า `server_wide_modules` ปัจจุบัน และทดสอบว่าการล็อกอินเดิมทำงาน
- 5.2 Backup DB + filestore (สำคัญ: มี session เก่าอยู่ใน filestore)
- 5.3 ติดตั้ง: `python odoo-bin -c odoo.conf -d odoo19 -i session_db --stop-after-init`
- 5.4 เพิ่ม `session_db` เข้า `server_wide_modules` ใน `odoo.conf` (PROPOSED) แล้วรีสตาร์ต
- 5.5 ตรวจว่า: ล็อกอินใหม่ได้, session ใหม่ถูกเก็บใน DB, ไม่มี ERROR/WARNING ใหม่

**6. การตั้งค่า** — `server_wide_modules = web,session_db` (หรือรวมกับ `sentry` ถ้าติดตั้งแล้ว) · ยืนยัน `dbfilter = ^odoo19$` ยังถูกต้อง

**7. ผลกระทบประสิทธิภาพ** — session อ่าน/เขียนผ่าน DB → เพิ่ม query เล็กน้อยต่อ request · โดยทั่วไปดีขึ้นเมื่อมีหลาย worker · ต้องวัดบน Integration

**8. ความปลอดภัย** — session ใน DB ต้องเข้าถึงได้เฉพาะ role Odoo · ตรวจว่า session ที่ค้าง/หมดอายุถูกล้าง · **ความเสี่ยงสูงสุดคือกระทบการล็อกอินทั้งระบบ** → ต้องมี rollback ทันที (เอา `session_db` ออกจาก `server_wide_modules` แล้วรีสตาร์ต)

**9. เกณฑ์การยอมรับ**
1. ผู้ใช้ล็อกอิน/ออกได้ตามปกติ
2. session ถูกเก็บใน DB (ยืนยันได้) และคงอยู่ข้ามรีสตาร์ต worker
3. ไม่มี ERROR/WARNING ใหม่ใน log
4. session เก่าที่ค้างใน filestore ไม่ทำให้เกิดข้อผิดพลาด
5. `server_wide_modules` โหลดโมดูลสำเร็จ

**10. Monitoring** — เฝ้า log การล็อกอิน/สิทธิ์หลังติดตั้ง · ตรวจขนาดตาราง session และการล้าง session หมดอายุ

**11. Rollback** — **(เร็ว)** เอา `session_db` ออกจาก `server_wide_modules` → รีสตาร์ต → ระบบกลับไปใช้ session บนดิสก์ · ถอนโมดูลผ่าน Apps · กู้จาก backup ถ้าจำเป็น

**12. ความเสี่ยง**

| ความเสี่ยง | ระดับ | บรรเทา |
| --- | --- | --- |
| กระทบการล็อกอินทั้งระบบ | MEDIUM–HIGH | ทดสอบ Local/Integration ก่อน, มี rollback ทันที |
| patch ไม่ทำงาน (ไม่อยู่ใน server_wide_modules) | MEDIUM | ยืนยันค่า config + ตรวจ log ว่ามี "Monkey patching session store" |
| ไม่มี `depends` ทำ install พฤติกรรมต่างจากคาด | MEDIUM | ยืนยันด้วยการทดสอบบน Integration |
| รันไทม์กับ 19.0 ยังไม่พิสูจน์ | MEDIUM | ติดตั้ง Local/Integration ก่อน |

**13. Task Checklist** — T1 บันทึก `server_wide_modules` + ทดสอบ login baseline · T2 backup · T3 ติดตั้ง Local · T4 เพิ่ม server_wide_modules + รีสตาร์ต · T5 ตรวจ session ใน DB + login · T6 ทดสอบเกณฑ์ยอมรับ · T7 ย้ำ Integration→QA→UAT · T8 เตรียม rollback ทันที · T9 go/no-go

**14. การอนุมัติ/หลักฐาน** — Deployment owner เก็บ log รีสตาร์ต + หลักฐาน session ใน DB · Incident first responder เฝ้าระหว่างติดตั้ง Production

**15. ภาคผนวกคำสั่ง (PROPOSED)**
```
python odoo-bin -c odoo.conf -d odoo19 -i session_db --stop-after-init
```
```
; odoo.conf (PROPOSED)
server_wide_modules = web,session_db
```
```sql
SELECT name, state, latest_version FROM ir_module_module WHERE name = 'session_db';
```

---

# 5) `sentry` — Sentry (Error Tracking)

| หัวข้อ | ค่า |
| --- | --- |
| Repository | `OCA/server-tools` → `third_party/oca/server-tools/sentry` |
| เวอร์ชัน | `19.0.1.0.1` |
| License | AGPL-3 |
| Dependencies | `base` |
| pip เพิ่ม | **`sentry_sdk>=2.0.0,<=2.22.0`** (บังคับ) |
| Hook | **`post_load`** (โหลดตอน bootstrap เซิร์ฟเวอร์) |
| หมวด | B — Monitoring & Anomaly Detection |
| ลำดับความสำคัญ | **P1** |
| ความเสี่ยง | **MEDIUM–HIGH** |
| สถานะความเข้ากันได้ | Manifest ตรง 19.0 · รันไทม์ **COMPATIBILITY NOT VERIFIED (runtime)** |

**1. เหตุผลและเป้าหมาย** — ปัจจุบันข้อผิดพลาดระดับรันไทม์ (exception, traceback) อยู่แต่ใน `odoo_server.log` ไม่มีการแจ้งเตือน/รวบรวม โมดูลนี้เชื่อม Odoo เข้ากับ Sentry (หรือ self-hosted) เพื่อรวบรวม error และแจ้งเตือนเชิงรุก — เป้าหมาย: ตรวจจับความผิดปกติ/ข้อผิดพลาดก่อนผู้ใช้ร้องเรียน

**2. ข้อกำหนดเบื้องต้น**
- submodule `server-tools` (พบแล้ว)
- **ติดตั้ง pip ก่อน:** `pip install "sentry_sdk>=2.0.0,<=2.22.0"` (ไม่งั้น `post_load` จะ no-op เพราะ `HAS_SENTRY_SDK = False`)
- มี Sentry DSN (หรือ self-hosted) — ตามบันทึกเดิม **ยังรอ DSN**
- ตัดสินใจเรื่อง PDPA/PII: ต้องกรองข้อมูลส่วนบุคคลก่อนส่งออกนอกเครื่อง (ดูข้อ 8)

**3. องค์ประกอบที่จะเกิด** — ไม่มีตาราง/โมเดล Odoo · **patch WSGI** (`odoo.http.Application.__call__` ถูกห่อด้วย `SentryWsgiMiddleware`) · `ThreadingIntegration` · logging integration · ส่งข้อความ "Starting Odoo Server" ตอนบูต (ถ้า `sentry_startup_message` ไม่ใช่ False) · **ต้องเพิ่ม `sentry` เข้า `server_wide_modules`**

**4. ลำดับสภาพแวดล้อม** — Local Dev → Shared Dev → Test/QA → UAT → Production *(เริ่มจาก environment/DSN แยกต่อสภาพแวดล้อม)*

**5. ขั้นตอนติดตั้ง (PROPOSED)**
- 5.1 Pre-flight: ติดตั้ง `sentry_sdk` ใน venv ของทุก environment · เตรียม DSN
- 5.2 Backup DB + filestore
- 5.3 ติดตั้ง: `python odoo-bin -c odoo.conf -d odoo19 -i sentry --stop-after-init`
- 5.4 เพิ่ม `sentry` เข้า `server_wide_modules` + เพิ่มส่วน `[sentry]` ในไฟล์ config (PROPOSED) → รีสตาร์ต
- 5.5 ทดสอบ: สร้างข้อผิดพลาดทดสอบ (route/script) → ยืนยันว่ามี event ใน Sentry

**6. การตั้งค่า (PROPOSED)**
```
[options]
server_wide_modules = web,sentry          ; (ถ้าใช้ session_db ให้รวมด้วย)

[sentry]
sentry_dsn = https://<public_key>:<secret_key>@sentry.example.com/<project id>
sentry_enabled = true
sentry_logging_level = warn
sentry_exclude_loggers = werkzeug
sentry_ignore_exceptions = odoo.exceptions.AccessDenied,odoo.exceptions.AccessError,odoo.exceptions.MissingError,odoo.exceptions.RedirectWarning,odoo.exceptions.UserError,odoo.exceptions.ValidationError,odoo.exceptions.Warning,odoo.exceptions.except_orm
sentry_include_context = true
sentry_environment = production
sentry_release = <version>
sentry_startup_message = true
```
> ซอร์สจริงอ่านส่วน `[sentry]` จาก config (ผ่าน `server_environment` ถ้ามี หรือจากไฟล์ config ที่ระบุ) — ต้องยืนยันพาธ/วิธีโหลดบน Windows ก่อนใช้ 실제
> ตัวเลือกอื่น ๆ ตั้งได้โดยเติม prefix `sentry_` (เช่น `send_default_pii`, `traces_sample_rate`, `sample_rate`)

**7. ผลกระทบประสิทธิภาพ** — overhead เล็กน้อยต่อ request (WSGI middleware) · ระวัง `traces_sample_rate` สูงจะเพิ่มภาระ · แนะนำเริ่มที่ logging level `warn`

**8. ความปลอดภัย (สำคัญที่สุดของโมดูลนี้)**
- **PII/PDPA:** ตั้ง `send_default_pii = false` และพิจารณา `sentry_exclude_loggers` เพื่อไม่ส่งข้อมูลส่วนบุคคล/ธุรกิจออกนอกเครื่อง
- ตรวจ `processor.py` ที่จัดการ `sentry_dsn` ว่ามีการ mask ข้อมูลอ่อนไหว
- จำกัดผู้ที่เข้าถึง Sentry project (เห็น stack trace + context)
- DSN เป็น credential → เก็บในไฟล์ config ที่มีสิทธิ์จำกัด (ห้าม commit; ห้ามใส่ใน command line)
- ใช้ self-hosted Sentry หากข้อกำหนดข้อมูลเข้มงวด

**9. เกณฑ์การยอมรับ**
1. เกิดข้อผิดพลาดทดสอบ → มี event ใน Sentry พร้อม release/environment
2. ไม่มี PII รั่วไหลใน event (ตรวจ payload)
3. ข้อผิดพลาดที่ระบุใน `sentry_ignore_exceptions` → ไม่ถูกส่ง
4. ไม่มี ERROR/WARNING ใหม่ใน log (ยกเว้นข้อความ Sentry ที่คาดไว้)
5. `server_wide_modules` โหลด `sentry` สำเร็จ (ยืนยันว่ามี log/message "Starting Odoo Server")

**10. Monitoring** — ทบทวน Sentry issue เป็นประจำ · ตั้ง alert rule (เช่น error rate) · ตรวจว่า DSN/โควต้าไม่หมด

**11. Rollback** — เอา `sentry` ออกจาก `server_wide_modules` + รีสตาร์ต (หยุดส่งข้อมูลทันที) · ถอนโมดูลผ่าน Apps · **คำเตือน:** ไม่มีข้อมูล Odoo ถูกทำลาย แต่ event ที่ส่งไปแล้วอยู่ที่ Sentry

**12. ความเสี่ยง**

| ความเสี่ยง | ระดับ | บรรเทา |
| --- | --- | --- |
| ข้อมูลอ่อนไหว/PII รั่วออกนอกเครื่อง | **HIGH** | `send_default_pii=false` + กรอง logger + self-hosted |
| ขาด pip `sentry_sdk` → โมดูลเงียบไม่ทำงาน | MEDIUM | ติดตั้ง pip ก่อน + ตรวจ log |
| patch WSGI ขัดกับ `proxy_mode`/Nginx | MEDIUM | ทดสอบหลัง Nginx บน Integration |
| โควต้า Sentry/ค่าใช้จ่าย | LOW | ตั้ง sample rate + alert |
| รันไทม์กับ 19.0 ยังไม่พิสูจน์ | MEDIUM | ติดตั้ง Local/Integration ก่อน |

**13. Task Checklist** — T1 ติดตั้ง pip `sentry_sdk` ทุก env · T2 backup · T3 ติดตั้ง Local · T4 เพิ่ม server_wide_modules + `[sentry]` + รีสตาร์ต · T5 ทดสอบ event + ตรวจ PII · T6 ทดสอบหลัง Nginx (proxy_mode) · T7 ย้ำ Integration→QA→UAT · T8 rollback plan · T9 go/no-go

**14. การอนุมัติ/หลักฐาน** — Security reviewer ยืนยันการกรอง PII · เก็บภาพ event ใน Sentry + payload ที่ตรวจแล้ว

**15. ภาคผนวกคำสั่ง (PROPOSED)**
```
pip install "sentry_sdk>=2.0.0,<=2.22.0"
python odoo-bin -c odoo.conf -d odoo19 -i sentry --stop-after-init
```
> ห้ามใส่ DSN/รหัสผ่านใน command line — เก็บในไฟล์ config ที่มีสิทธิ์จำกัดเท่านั้น

---

# 6) `auto_backup` — Database Auto-Backup

| หัวข้อ | ค่า |
| --- | --- |
| Repository | `OCA/server-tools` → `third_party/oca/server-tools/auto_backup` |
| เวอร์ชัน | `19.0.1.0.1` |
| License | AGPL-3 |
| Dependencies | `mail` |
| pip เพิ่ม | **`paramiko<4.0.0`, `pysftp`, `cryptography`** (สำหรับ SFTP) |
| โมเดล | `db.backup` (`name`, `folder`, `days_to_keep`, `method`, `sftp_*`, `backup_format`) |
| Constraint | `days_to_keep >= 0` |
| หมวด | D — Prevention & Protection |
| ลำดับความสำคัญ | **P1** |
| ความเสี่ยง | **MEDIUM–HIGH** |
| สถานะความเข้ากันได้ | Manifest ตรง 19.0 · รันไทม์ **COMPATIBILITY NOT VERIFIED (runtime)** |

**1. เหตุผลและเป้าหมาย** — สำรองฐานข้อมูลอัตโนมัติตามรอบ (นโยบายเดิม: **ทุก 1 เดือน, เก็บ 365 วัน, โฟลเดอร์ `C:\odoo-dev\odoo19\backups`**) — เป้าหมาย: มีสำเนาสำรองที่กู้คืนได้สม่ำเสมอ ลดความเสี่ยงข้อมูลสูญหาย

**2. ข้อกำหนดเบื้องต้น**
- submodule `server-tools` · `mail` ติดตั้งแล้ว
- **ติดตั้ง pip:** `paramiko<4.0.0`, `pysftp`, `cryptography` (จำเป็นถ้าใช้ SFTP; ถ้าใช้ local เท่านั้นอาจยังถูกบังคับตรวจตอนติดตั้ง)
- มีพื้นที่ดิสก์เพียงพอ และโฟลเดอร์ backup มีสิทธิ์เขียน
- **⚠️ ความขัดแย้งที่ทราบแล้ว (จากบันทึกเดิม):** ใน Odoo 19 การตั้ง `list_db = False` (hardening) จะทำให้ `dump_db` ถูกบล็อก → `auto_backup` ทำงานล้มเหลว → **ต้องตัดสินใจเลือกระหว่าง hardening (`list_db=False`) กับ backup ในระบบ** หรือใช้ backup ภายนอกระบบแทน

**3. องค์ประกอบที่จะเกิด** — โมเดล `db.backup` (ตั้งค่าโฟลเดอร์/รอบ/retention/local-SFTP) · scheduled action (จาก `data/ir_cron.xml`) · mail subtype (`data/mail_message_subtype.xml`) สำหรับแจ้งผล · view + security csv · **ไม่มีกลุ่มสิทธิ์พิเศษใหม่**

**4. ลำดับสภาพแวดล้อม** — Local Dev → Shared Dev → Test/QA → UAT → Production *(ทดสอบ restore จริงทุกขั้น)*

**5. ขั้นตอนติดตั้ง (PROPOSED)**
- 5.1 Pre-flight: **ตัดสินใจเรื่อง `list_db`** ให้ชัด + ตรวจพื้นที่ดิสก์ + ยืนยันโฟลเดอร์ backup
- 5.2 Backup DB + filestore (**แบบ manual นอกโมดูลนี้**)
- 5.3 ติดตั้ง: `python odoo-bin -c odoo.conf -d odoo19 -i auto_backup --stop-after-init`
- 5.4 รีสตาร์ต + ตรวจ log
- 5.5 ตั้งค่า: สร้างเรกคอร์ด `db.backup` (folder = `C:\odoo-dev\odoo19\backups`, รอบ = รายเดือน, `days_to_keep = 365`) + เปิด cron + **ทดสอบกู้คืนจากไฟล์ที่สร้าง**

**6. การตั้งค่า** — `method = local` (แนะนำเริ่มต้น) หรือ `sftp` (ต้องมี `sftp_host/port/user/password หรือ private_key`) · `backup_format` (zip/dump) · ตั้งผู้รับอีเมลแจ้งผล · ยืนยันว่า cron ทำงานตามรอบ

**7. ผลกระทบประสิทธิภาพ** — การ dump DB เป็นภาระหนักชั่วคราว → ตั้งรอบในเวลาที่ระบบว่าง · ตรวจพื้นที่ดิสก์ต่อเนื่อง (retention 365 วัน + ขนาด DB)

**8. ความปลอดภัย**
- ไฟล์ backup มีข้อมูลทั้งระบบ → **ต้องเข้ารหัส/จำกัดสิทธิ์โฟลเดอร์** และห้ามวางในที่ web เข้าถึงได้
- SFTP credential เก็บเป็นความลับ (ห้าม commit)
- **ความขัดแย้ง hardening:** ถ้าปิด `list_db=False` โมดูลจะล้มเหลว → ต้องเลือกกลยุทธ์ (ดูข้อ 2)
- พิจารณาสำรองออกนอกเครื่อง (off-site/SFTP) ตามหลัก 3-2-1

**9. เกณฑ์การยอมรับ**
1. cron สร้างไฟล์ backup ในโฟลเดอร์ที่กำหนดตามรอบ
2. **กู้คืนสำเร็จ** บนฐานข้อมูลทดสอบจากไฟล์ที่สร้างจริง
3. retention: ไฟล์เก่ากว่า `days_to_keep` ถูกลบ
4. มีอีเมลแจ้งผล (สำเร็จ/ล้มเหลว)
5. ไม่มี ERROR/WARNING ใหม่ใน log
6. ยืนยันพฤติกรรมเมื่อ `list_db` ตามที่นโยบายกำหนด

**10. Monitoring** — ตรวจไฟล์ล่าสุดมีอยู่และขนาดสมเหตุผล · ตรวจว่ามีอีเมลแจ้งผลทุกครั้ง · เฝ้าพื้นที่ดิสก์

**11. Rollback** — ถอนผ่าน Apps ได้ (ไม่ทำลายข้อมูล) · **ไฟล์ backup ที่สร้างแล้วยังอยู่** · ถ้าไม่ต้องใช้แล้วควรเก็บไฟล์ล่าสุดไว้ก่อนถอน

**12. ความเสี่ยง**

| ความเสี่ยง | ระดับ | บรรเทา |
| --- | --- | --- |
| **`list_db=False` ทำให้ backup ล้มเหลว** | **HIGH** | ตัดสินใจนโยบายให้ชัด / ใช้ backup ภายนอก |
| ไฟล์ backup รั่ว/ไม่เข้ารหัส | HIGH | จำกัดสิทธิ์โฟลเดอร์ + off-site + encryption |
| พื้นที่ดิสก์เต็ม | MEDIUM | retention + ตรวจรายเดือน + off-site |
| กู้คืนไม่ได้จริง (ไม่เคยทดสอบ) | HIGH | ทดสอบ restore ทุกขั้น (เกณฑ์ข้อ 9.2) |
| SFTP/credential ผิดพลาด | MEDIUM | ทดสอบ connection ก่อนเปิด cron |
| รันไทม์กับ 19.0 ยังไม่พิสูจน์ | MEDIUM | ติดตั้ง Local/Integration ก่อน |

**13. Task Checklist** — T1 ตัดสินใจนโยบาย `list_db` + ตรวจดิสก์ · T2 backup manual + ทดสอบ restore · T3 ติดตั้ง pip + โมดูล Local · T4 รีสตาร์ต+ตรวจ log · T5 สร้าง `db.backup` + เปิด cron · T6 ทดสอบ backup + **restore จริง** · T7 ย้ำ Integration→QA→UAT · T8 rollback plan · T9 go/no-go

**14. การอนุมัติ/หลักฐาน** — Backup owner ยืนยัน restore สำเร็จ · เก็บรายการไฟล์ backup + log restore + ภาพการตั้งค่า `db.backup`

**15. ภาคผนวกคำสั่ง (PROPOSED)**
```
pip install "paramiko<4.0.0" pysftp cryptography
python odoo-bin -c odoo.conf -d odoo19 -i auto_backup --stop-after-init
```
```sql
SELECT name, state, latest_version FROM ir_module_module WHERE name = 'auto_backup';
SELECT id, name, folder, method, days_to_keep FROM db_backup;
```
> ห้ามใส่รหัสผ่านฐานข้อมูลใน command line ให้ใช้ `.pgpass` หรือ interactive prompt เท่านั้น

---

# 7) `bi_sql_editor` — BI SQL Editor

| หัวข้อ | ค่า |
| --- | --- |
| Repository | `OCA/reporting-engine` → `third_party/oca/reporting-engine/bi_sql_editor` |
| เวอร์ชัน | `19.0.2.0.1` |
| License | AGPL-3 |
| Dependencies | **`spreadsheet_dashboard`** (core — พบใน `addons/`) + **`sql_request_abstract`** (OCA reporting-engine — พบแล้ว) |
| pip เพิ่ม | ไม่มี |
| Hook | มี **`uninstall_hook`** (ตั้ง `bi.sql.view` ทั้งหมดกลับเป็น draft) |
| หมวด | F — Data Processing & Reporting |
| ลำดับความสำคัญ | **P1** |
| ความเสี่ยง | **MEDIUM–HIGH** |
| สถานะความเข้ากันได้ | Manifest ตรง 19.0 · รันไทม์ **COMPATIBILITY NOT VERIFIED (runtime)** |

**1. เหตุผลและเป้าหมาย** — ให้สร้าง **BI view จาก SQL** (normal หรือ materialized view) และทำรายงาน/แดชบอร์ดจากข้อมูล (ใช้ร่วมกับ `spreadsheet_dashboard`) — เป้าหมาย: รายงานวิเคราะห์ที่ยืดหยุ่นโดยไม่ต้องเขียนโมดูลใหม่ (คู่กับ `auditlog` เพื่อช่วยตรวจสอบ) — **เป็นทางเลือกแทน/หรือทดแทน `kpi` (ต้องเลือกอย่างเดียว — ดูข้อ 6 ของรายงานประเมิน)**

**2. ข้อกำหนดเบื้องต้น**
- submodule `reporting-engine` (พบแล้ว) · ยืนยันว่า `spreadsheet_dashboard` มีใน CE 19.0 (**พบแล้ว** ที่ `addons/spreadsheet_dashboard`)
- จะติดตั้ง `sql_request_abstract` เป็น dependency อัตโนมัติ (OCA) — ต้องยอมรับ
- **ต้องมี DB role แบบ read-only** สำหรับ SQL ที่รันจากผู้ใช้ (ลดความเสี่ยง) — ดูข้อ 8
- backup ก่อนติดตั้ง

**3. องค์ประกอบที่จะเกิด** — โมเดล `bi.sql.view` (และที่เกี่ยวข้องกับ `sql.request.abstract`) · security csv · view `views/view_bi_sql_view.xml` · demo (ไม่โหลดใน production) · **`uninstall_hook` จะตั้ง view ทั้งหมดเป็น draft ก่อนถอน**

**4. ลำดับสภาพแวดล้อม** — Local Dev → Shared Dev → Test/QA → UAT → Production

**5. ขั้นตอนติดตั้ง (PROPOSED)**
- 5.1 Pre-flight: ยืนยัน `spreadsheet_dashboard`/`sql_request_abstract` พร้อม · ทบทวนนโยบาย SQL + สิทธิ์
- 5.2 Backup DB + filestore
- 5.3 ติดตั้ง: `python odoo-bin -c odoo.conf -d odoo19 -i bi_sql_editor --stop-after-init` (จะติดตั้ง dependency ให้)
- 5.4 รีสตาร์ต + ตรวจ log
- 5.5 ตั้งค่า: สร้าง BI view ตัวอย่าง (normal view) → ทดสอบสร้าง materialized view + refresh + แสดงในแดชบอร์ด

**6. การตั้งค่า** — จำกัดผู้สร้าง BI view (กลุ่มเฉพาะ) · เลือก normal view สำหรับข้อมูลสด / materialized view สำหรับข้อมูลหนัก + ตั้งรอบ refresh · **ต้องเลือกอย่างเดียวระหว่าง `bi_sql_editor` กับโมดูล `kpi` เดิม** เพื่อเลี่ยงความซ้ำซ้อน

**7. ผลกระทบประสิทธิภาพ** — materialized view กินพื้นที่และต้อง refresh (ภาระตอน refresh) · query ที่เขียนไม่ดีจะหนัก DB → ต้อง review SQL · ใช้ read-only role เพื่อจำกัด

**8. ความปลอดภัย (สำคัญมาก)**
- โมดูลรัน **SQL ตามที่ผู้ใช้กำหนด** → ความเสี่ยงสูงสุดคือ SQL injection/แก้ข้อมูล
- จำกัดสิทธิ์สร้าง/แก้ BI view เฉพาะผู้ดูแล/นักวิเคราะห์ที่เชื่อถือได้
- **แนะนำใช้ DB role ที่อ่านได้อย่างเดียว** สำหรับ connection ที่รัน query (ถ้าสถาปัตยกรรมรองรับ)
- ทบทวน query ที่สร้างว่าไม่ดึงข้อมูลอ่อนไหวเกินจำเป็น และสอดคล้อง PDPA
- ตรวจว่าไม่มี record rule ของโมดูลกำหนดเองที่ขัดกับการเข้าถึง BI view

**9. เกณฑ์การยอมรับ**
1. สร้าง BI view (normal) สำเร็จและแสดงข้อมูลถูกต้อง
2. สร้าง materialized view + refresh สำเร็จ
3. แสดงผลในแดชบอร์ด/spreadsheet ได้
4. ผู้ใช้ที่ไม่มีสิทธิ์สร้าง/แก้ BI view → ถูกปฏิเสธ
5. `uninstall_hook` ทำงาน (ทดสอบตั้ง view เป็น draft) — **ทดสอบบน Integration เท่านั้น**
6. ไม่มี ERROR/WARNING ใหม่ใน log

**10. Monitoring** — ตรวจภาระ DB ตอน refresh · เฝ้าขนาด materialized view · ทบทวน SQL ที่มีอยู่เป็นระยะ

**11. Rollback** — ถอนผ่าน Apps (เรียก `uninstall_hook` ตั้ง view เป็น draft) · **ควรบันทึก SQL ของ BI view ไว้ก่อนถอน** (จะหายไปกับโมดูล) · DB ปลอดภัยจาก backup

**12. ความเสี่ยง**

| ความเสี่ยง | ระดับ | บรรเทา |
| --- | --- | --- |
| SQL ที่ผู้ใช้เขียนแก้/ลบข้อมูลได้ | **HIGH** | read-only role + จำกัดกลุ่ม + review |
| materialized view หนัก DB/พื้นที่ | MEDIUM | เลือก normal view + ตั้งรอบ refresh |
| ซ้ำซ้อนกับโมดูล `kpi` เดิม | MEDIUM | เลือกใช้เพียงตัวเดียว |
| dependency `sql_request_abstract` เพิ่มความซับซ้อน | LOW | ยอมรับ + ทดสอบบน Integration |
| `uninstall_hook` ลบ view ที่ใช้งานอยู่ | MEDIUM | ทดสอบบน Integration, สำรอง SQL |
| รันไทม์กับ 19.0 ยังไม่พิสูจน์ | MEDIUM | ติดตั้ง Local/Integration ก่อน |

**13. Task Checklist** — T1 ยืนยัน dependency + นโยบาย read-only · T2 backup · T3 ติดตั้ง Local (+deps) · T4 รีสตาร์ต+ตรวจ log · T5 สร้าง/ทดสอบ BI view + แดชบอร์ด · T6 ทดสอบสิทธิ์ + `uninstall_hook` บน Integration · T7 ตัดสินใจเรื่อง `kpi` (เลือกอย่างเดียว) · T8 ย้ำ Integration→QA→UAT · T9 rollback + สำรอง SQL · T10 go/no-go

**14. การอนุมัติ/หลักฐาน** — Security reviewer ยืนยันการจำกัดสิทธิ์ SQL · เก็บภาพ BI view + ผล refresh + สำเนา SQL

**15. ภาคผนวกคำสั่ง (PROPOSED)**
```
python odoo-bin -c odoo.conf -d odoo19 -i bi_sql_editor --stop-after-init
```
```sql
SELECT name, state, latest_version FROM ir_module_module WHERE name IN ('bi_sql_editor','sql_request_abstract');
```

---

# 8) `database_cleanup` — Database cleanup

| หัวข้อ | ค่า |
| --- | --- |
| Repository | `OCA/server-tools` → `third_party/oca/server-tools/database_cleanup` |
| เวอร์ชัน | `19.0.1.0.6` |
| License | AGPL-3 |
| Dependencies | `base` |
| pip เพิ่ม | ไม่มี |
| Wizards | purge: menus, modules, models, fields, columns, tables, data + create_indexes |
| หมวด | E — Utilities (Destructive) |
| ลำดับความสำคัญ | **P1** |
| ความเสี่ยง | **HIGH** |
| สถานะความเข้ากันได้ | Manifest ตรง 19.0 · รันไทม์ **COMPATIBILITY NOT VERIFIED (runtime)** |

**1. เหตุผลและเป้าหมาย** — เมื่อติดตั้ง/ถอนโมดูลหลายรอบ จะเหลือขยะใน DB (ตาราง/คอลัมน์/ฟิลด์/โมเดล/เมนู/ข้อมูล) โมดูลนี้ให้เครื่องมือ purge และสร้าง index เพื่อดูแลสุขภาพ DB — เป้าหมาย: DB สะอาดขึ้น (ใช้ **หลัง** การเปลี่ยนแปลงโมดูลครั้งใหญ่เท่านั้น)

**2. ข้อกำหนดเบื้องต้น**
- submodule `server-tools` (พบแล้ว) · backup ก่อนติดตั้ง
- **⚠️ เป็นโมดูลทำลายข้อมูล (destructive)** — purge สามารถลบตาราง/คอลัมน์/ข้อมูลได้ → **ห้ามรันบน Production โดยไม่มี backup ที่ทดสอบ restore และการอนุมัติชัดเจน**
- เข้าใจความหมายของแต่ละ wizard (dry-run ถ้ามี)

**3. องค์ประกอบที่จะเกิด** — wizard หลายตัว (`purge.wizard` + line ต่าง ๆ: menus/modules/models/fields/columns/tables/data) · `create.indexes` wizard · menu + security csv · **ไม่มีตารางธุรกิจใหม่** แต่ **มีอำนาจลบโครงสร้าง DB**

**4. ลำดับสภาพแวดล้อม** — Local Dev (ทดลอง+ทำความเข้าใจ) → Shared Dev → Test/QA → UAT → **Production (เฉพาะเมื่ออนุมัติ + backup พร้อม)**

**5. ขั้นตอนติดตั้ง (PROPOSED)**
- 5.1 Pre-flight: **แจ้งเตือนความเสี่ยงสูง** + เตรียม backup ที่ทดสอบ restore
- 5.2 Backup DB + filestore (บังคับ)
- 5.3 ติดตั้ง: `python odoo-bin -c odoo.conf -d odoo19 -i database_cleanup --stop-after-init`
- 5.4 รีสตาร์ต + ตรวจ log
- 5.5 ใช้งาน: เปิด purge wizard → **ทบทวนรายการที่ระบบเสนอ (dry-run) ก่อนกดยืนยันทุกครั้ง**

**6. การตั้งค่า** — จำกัดสิทธิ์เข้าถึง wizard เฉพาะผู้ดูแลระบบเท่านั้น · ใช้ `create_indexes` เพื่อเพิ่ม index ที่ขาด (ประโยชน์เชิงประสิทธิภาพ) · **ห้ามรัน purge แบบกวาดทั้งหมดโดยไม่ตรวจรายการ**

**7. ผลกระทบประสิทธิภาพ** — `create_indexes` เพิ่มประสิทธิภาพ query (แต่กินพื้นที่) · purge ลดขนาด DB — ทั้งสองมีภาระชั่วคราว ควรทำในเวลาว่าง

**8. ความปลอดภัย (สำคัญที่สุด)**
- **ความเสี่ยงสูงสุด: ลบข้อมูล/โครงสร้างถาวรโดยไม่สามารถย้อนกลับ** → ต้องมี backup + restore test + การอนุมัติต่อครั้ง
- จำกัดสิทธิ์กลุ่มให้แคบที่สุด (ผู้ดูแลระบบ)
- ทบทวนรายการที่ purge เสนอทีละรายการ (ไม่เชื่อรายการอัตโนมัติ 100%)
- ระวังการลบตาราง/คอลัมน์ที่ยังใช้โดยโมดูลกำหนดเอง `od19_*`

**9. เกณฑ์การยอมรับ**
1. ติดตั้งสำเร็จ ไม่มี ERROR/WARNING ใหม่ใน log
2. เข้าเมนู purge/index ได้เฉพาะผู้ดูแลระบบ
3. ทดสอบ `create_indexes` บน Integration สำเร็จ
4. ทดสอบ purge บนสำเนา DB (Integration) แล้วระบบยังทำงานปกติ
5. มี backup + restore test ล่าสุดกำกับก่อนใช้บน Production

**10. Monitoring** — ตรวจขนาด DB และสุขภาพหลัง purge · ตรวจว่า index ที่สร้างไม่ซ้ำซ้อน · บันทึกทุกการ purge (ใคร/เมื่อไร/อะไร)

**11. Rollback** — **ไม่มี undo** → ต้องกู้จาก backup เท่านั้น · ถอนโมดูลได้ (ตัว wizard หายไป) แต่ **ผลของการ purge ไม่ย้อนกลับ**

**12. ความเสี่ยง**

| ความเสี่ยง | ระดับ | บรรเทา |
| --- | --- | --- |
| ลบข้อมูล/ตารางถาวรผิดพลาด | **HIGH** | backup+restore test + อนุมัติต่อครั้ง + ทบทวนรายการ |
| ลบโครงสร้างที่โมดูล od19_* ยังใช้ | **HIGH** | ตรวจ dependency ก่อน purge |
| ผู้ใช้ไม่มีสิทธิ์เข้าถึง wizard | LOW | จำกัดกลุ่มแคบ |
| รันไทม์กับ 19.0 ยังไม่พิสูจน์ | MEDIUM | ทดสอบบนสำเนา DB/Integration ก่อน |

**13. Task Checklist** — T1 แจ้งความเสี่ยง + อนุมัติหลักการ · T2 backup + restore test · T3 ติดตั้ง Local (ทดลอง) · T4 รีสตาร์ต+ตรวจ log · T5 ทดสอบ `create_indexes` · T6 ทดสอบ purge บนสำเนา DB (Integration) · T7 จำกัดสิทธิ์กลุ่ม · T8 rollback plan (กู้จาก backup) · T9 อนุมัติ go/no-go ก่อน Production

**14. การอนุมัติ/หลักฐาน** — Backup owner ยืนยัน restore · Security reviewer ยืนยันกลุ่มสิทธิ์ · เก็บ log ทุกการ purge + ภาพรายการที่ purge

**15. ภาคผนวกคำสั่ง (PROPOSED)**
```
python odoo-bin -c odoo.conf -d odoo19 -i database_cleanup --stop-after-init
```
```sql
SELECT name, state, latest_version FROM ir_module_module WHERE name = 'database_cleanup';
```
> **คำเตือน:** อย่ารันคำสั่ง purge ผ่าน SQL ตรง ๆ — ใช้ wizard ใน UI เพื่อให้ระบบตรวจสอบ dependency
> ห้ามใส่รหัสผ่านฐานข้อมูลใน command line ให้ใช้ `.pgpass` หรือ interactive prompt เท่านั้น

---

## สรุปลำดับการติดตั้งที่แนะนำ (ยังไม่ดำเนินการ)

```
1. base_cron_exclusion     (LOW  — ฐาน, แก้ cron ทับซ้อน)
2. scheduler_error_mailer  (LOW  — แจ้งเตือน cron ล้มเหลว)
3. base_export_manager     (LOW–MEDIUM — คุม export)
4. session_db              (MEDIUM — ต้องมี rollback ทันที)
5. sentry                  (MEDIUM–HIGH — ต้องมี DSN + กรอง PII)
6. auto_backup             (MEDIUM–HIGH — ต้องแก้ปม list_db)
7. bi_sql_editor           (MEDIUM–HIGH — ต้องมี read-only role + เลือกแทน kpi)
8. database_cleanup        (HIGH — ทำลายข้อมูล, ทำหลังสุดและเมื่ออนุมัติ)
```

**ทุกโมดูลต้องผ่าน:** Local Dev → Shared Dev/Integration → Test/QA → UAT/Training → Production พร้อม backup + restore test ก่อนทุกครั้ง

> เอกสารนี้เป็น **PROPOSED CHANGE — NOT EXECUTED** ทั้งฉบับ ยังไม่มีการติดตั้ง แก้ไข config/สิทธิ์ หรือรีสตาร์ตบริการใด ๆ
