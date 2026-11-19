# ข้อเสนอโครงการ: ระบบรู้ทันสุขภาพ Odoo 19 (System Health & Early Warning)

## Document Metadata

| ฟิลด์ | ค่า |
| --- | --- |
| ประเภทเอกสาร | ข้อเสนอเพื่อพิจารณา (Proposal) — **ยังไม่ได้รับอนุมัติ** |
| วันที่ | 2026-11-11 |
| ผู้จัดทำ | AGENT_ID `trae-odoo19` (worktree หลัก `c:\odoo-dev\odoo19`) |
| Commit ฐาน | `522ef2c86b1` — branch `19.0` |
| ระบบเป้าหมาย | Odoo 19 CE · พอร์ต `8070` · DB `odoo19_pdev` เป็นหลัก (`odoo19_puat` เฝ้าด้วย) |
| สถานะ | รอผู้ใช้ตัดสินใจตามข้อ 8 |
| ขอบเขตที่แตะ | เฉพาะ `docs/` (เอกสารนี้) — ยังไม่มีการแก้โค้ด/โมดูลใด ๆ |

---

## 0. สรุปสำหรับผู้บริหาร

ปัจจุบันระบบ Odoo 19 ของเรา **ไม่มีกลไกใดที่บอกได้เองว่า "ระบบกำลังมีปัญหาหรือล่มอยู่"** — ทุกอย่างรู้ต่อเมื่อมีคนไปเปิดดูเอง หรือมีผู้ใช้โทรมาแจ้ง หลักฐานที่เก็บได้ในวันนี้ (ข้อ 2) ชี้ตรงกันว่าเหตุการณ์นี้ **เกิดขึ้นจริงและยังคงอยู่**: งาน backup รายเดือนล้มเหลวมาตั้งแต่ 1 พ.ย. โดยไม่มีใครรู้, process ของ Ollama ค้างตั้งแต่ 9 พ.ย., และ ณ เวลาที่ตรวจ (01:43 น. 11 พ.ย.) ตัว Odoo (`:8070`) และ PostgreSQL (`:5432`) ไม่ได้ทำงานอยู่ แต่ไม่มีสัญญาณเตือนใด ๆ เกิดขึ้นเลย

ข้อเสนอนี้คือการวาง "ระบบประสาทรับความรู้สึก" ให้ Odoo 19 โดยยึดหลัก **รู้ก่อนผู้ใช้ แจ้งพร้อมสาเหตุ แก้ก่อนลุกลาม** และออกแบบให้ **ใช้ของที่มีอยู่แล้วเป็นฐาน** (ระบบแจ้งเตือนหลายช่องทาง, auditlog, Sentry, ชุดสคริปต์ STEP-*) โดยไม่แก้ไฟล์ core ของ Odoo

---

## 1. เป้าหมายและหลักการ

**เป้าหมาย**: ตรวจพบความผิดปกติของระบบ Odoo 19 และชั้นโครงสร้างพื้นฐานรอบตัวได้เอง ภายในไม่กี่นาที พร้อมข้อมูลที่พอตัดสินใจได้ ก่อนที่ผู้ใช้ทั้งองค์กรจะได้รับผลกระทบ

**หลักการออกแบบ 5 ข้อ**

1. **ทนต่อความล้มเหลวของตัวเอง** — ตัวเฝ้าระวังต้องไม่ใช่จุดล้มเหลวจุดใหม่ ต้องมีกลไกให้รู้ว่า "ตัวเฝ้าระวังเองตายแล้ว"
2. **ชั้นใน-ชั้นนอก** — ถ้า Odoo ล่ม ตัว Odoo ย่อมรายงานตัวเองไม่ได้ จึงต้องมีตัวเฝ้าที่อยู่ **นอก** กระบวนการ Odoo
3. **Local-first / ข้อมูลไม่ออกนอกเครื่อง** — ค่าเริ่มต้นประมวลผลในเครื่อง เปิดช่องทางภายนอก (เช่น Sentry) เฉพาะที่ผู้ใช้อนุมัติ
4. **อ่านอย่างเดียวโดยค่าเริ่มต้น** — ทุกการตรวจเป็นการอ่าน ไม่เขียนทับข้อมูลธุรกิจ และ **ไม่มีการสั่ง restart/ปิดบริการอัตโนมัติ** ในเฟสแรก ๆ
5. **ไม่รบกวน** — มีการยุบรวมสัญญาณซ้ำ (dedup) และสรุปรายวัน เพื่อไม่ให้เกิด "alert fatigue" จนคนเลิกสนใจสัญญาณจริง

---

## 2. หลักฐานจากระบบจริง (เก็บเมื่อ 2026-11-11 เวลา ~01:40–01:43 น.)

| # | สิ่งที่พบ | หลักฐาน / แหล่งอ้างอิง | ความหมายต่อข้อเสนอ |
| --- | --- | --- | --- |
| E1 | Odoo `:8070`, longpolling `:8072`, PostgreSQL `:5432` **ไม่ listen** ขณะที่ Nginx `:80` ยัง listen | `Get-NetTCPConnection -State Listen` (ภาคผนวก A1) | ระบบสามารถ **ล่มเงียบ** ได้ โดยไม่มีสัญญาณเตือน — ต้องมี uptime check |
| E2 | Scheduled Task `Odoo19 Monthly Backup` → `LastTaskResult = 1` (ล้มเหลว) รันล่าสุด 1 พ.ย. 03:00 | `Get-ScheduledTaskInfo` (A2) | backup รายเดือนล้มเหลว **โดยไม่มีใครรู้**; ไฟล์ใหม่สุดใน `backups/` คือ 2026-11-05 (ทำมือ) — ต้องมี freshness alert |
| E3 | Scheduled Task `Ollama Autostart` → `state = Running`, `LastTaskResult = 267009` ตั้งแต่ 9 พ.ย. 18:35 | `Get-ScheduledTask` (A2) | process/งานค้างค้างนานโดยไม่มีสัญญาณ — ต้องมี watchdog งานค้าง |
| E4 | `odoo_server.log` ขนาด 1.5 MB เขียนล่าสุด 2026-11-10 18:25 แล้วหยุด; 3,000 บรรทัดท้ายมี 211 WARNING โดยส่วนใหญ่เป็น `odoo.schema: Missing not-null constraint ...` | วิเคราะห์ log (A3) | สัญญาณรบกวนกลบ error จริง — ต้องจัดระดับ log และจัดการ warning เชิงสคีมา |
| E5 | มีการตั้งค่า Sentry แล้ว (`odoo.conf` section `[sentry]`: enabled, `environment=pre-uat`, `logging_level=error`) และโมดูล `sentry` มีอยู่ใน `third_party/oca/server-tools` | [odoo.conf](file:///c:/odoo-dev/odoo19/odoo.conf#L111-L124) | มีฐาน error tracking อยู่แล้ว แต่ครอบคลุมเฉพาะ error ในโค้ดแอป ไม่ครอบคลุม cron / ดิสก์ / backup / การล่มของทั้งระบบ (และยังต้องยืนยันว่าติดตั้งจริงใน DB) |
| E6 | ไม่พบ health endpoint / status page / cron watchdog / dedup / escalation ในระบบ | `custom_addons/` 108 โมดูล ไม่มีโมดูลด้าน monitoring/health | เป็นช่องว่างหลักที่ข้อเสนอนี้จะอุด |
| E7 | **ทุนเดิมที่ใช้ซ้ำได้**: `od19_notification_multi_channel` = "Unified notification gateway: Email + Odoo Inbox + LINE Messaging API" (มี queue + cron) | [__manifest__.py](file:///c:/odoo-dev/odoo19/custom_addons/od19_notification_multi_channel/__manifest__.py) | ใช้เป็น **ชั้นแจ้งเตือน** ได้ทันที ไม่ต้องสร้างใหม่ |
| E8 | มีชุดสคริปต์ปฏิบัติการอยู่แล้ว: `STEP-3-Start-Odoo19.ps1` (ตรวจ HTTP 200, เคลียร์ port), `STEP-4-Backup-Odoo19.ps1`, `term-health.ps1` (สุขภาพเครื่อง dev แบบอ่านอย่างเดียว), `STEP-TASKS-Setup-Odoo19.ps1` | [STEP-3-Start-Odoo19.ps1](file:///c:/odoo-dev/odoo19/STEP-3-Start-Odoo19.ps1), [term-health.ps1](file:///c:/odoo-dev/odoo19/term-health.ps1) | ใช้เป็นฐานของชั้นเฝ้าระวังภายนอกได้เลย (มี `Test-Port`, `Test-Http` ให้ reuse) |
| E9 | มี OCA `auditlog` และ `auto_backup` พร้อมใช้ใน `third_party/oca/server-tools` | สแกนไดเรกทอรี (A4) | เปิดใช้ audit trail ของการแก้ไขข้อมูลสำคัญได้ทันทีในเฟสถัดไป |

> หมายเหตุความน่าเชื่อถือ: E1–E4, E7–E9 เป็นผลจากการรันคำสั่งจริงในเครื่องนี้ (ดูภาคผนวก A) ส่วน E5 ยังต้องยืนยันสถานะติดตั้งในฐานข้อมูลจริง (จะทำได้เมื่อสแตกกลับมาทำงาน)

---

## 3. ช่องว่างที่ต้องอุด (Gap Analysis 6 มิติ)

| มิติ | สถานะปัจจุบัน | ความเสี่ยง | สิ่งที่ข้อเสนอจะเติม |
| --- | --- | --- | --- |
| **1. Availability** | ไม่มีตัวเฝ้า uptime ของ Odoo/PG/Nginx | ระบบล่มแล้วรู้ช้าเป็นชั่วโมง–เป็นวัน (E1) | ตรวจ TCP + HTTP 200 + service state ทุก 1–5 นาที |
| **2. Automation / Cron** | cron ของ Odoo และ Scheduled Task ล้ม/ค้างโดยไม่มีสัญญาณ | งานประจำไม่ทำงานเงียบ ๆ เช่น backup, คิดค่าเสื่อม, ทวงหนี้ (E2, E3) | cron heartbeat + lag check + dead-man switch |
| **3. Data & Backup** | backup ล้มเหลวไม่มีการแจ้งเตือน | เสี่ยงข้อมูลหายโดยไม่รู้ตัวจนถึงวันที่ต้องกู้ (E2) | freshness alert + ตรวจขนาดไฟล์ผิดปกติ + ทดสอบกู้ตามรอบ |
| **4. Resource / Capacity** | ไม่มีแนวโน้มการใช้ดิสก์ / ขนาด DB / filestore | ดิสก์เต็มหรือ DB บวมโดยไม่รู้ล่วงหน้า | threshold + แนวโน้มการเติบโตรายสัปดาห์ |
| **5. Error / Log quality** | log ปนสัญญาณรบกวน; ไม่มีที่รวม error; log ไม่หมุนขณะรัน | error จริงถูกกลบ; log โตจนค้นยาก (E4) | จัดระดับ log, กรอง warning เชิงสคีมา, หมุน log, ขยาย scope ของ Sentry |
| **6. Security / Audit** | มี `auditlog` พร้อมใช้แต่ยังไม่เปิด; ไม่มีการเฝ้าสิทธิ์/การเข้าถึงผิดปกติ | ตรวจสอบย้อนหลังไม่ได้เมื่อเกิดเหตุ (สอดคล้องนโยบาย ISO 9001 / NIST CSF) | เปิด audit ที่ model สำคัญ + เฝ้าเหตุการณ์ผิดปกติ |

---

## 4. สถาปัตยกรรมที่เสนอ (4 ชั้น)

```
┌─ ชั้น 4  AI TRIAGE (เฟสท้าย, ทางเลือก) ────────────────────────────┐
│  Ollama (ในเครื่อง) + od19_ai_assistant : สรุป log/เหตุการณ์เป็นไทย  │
│  เสนอสาเหตุที่เป็นไปได้ — อ่านอย่างเดียว ไม่สั่งแก้ไขอัตโนมัติ        │
└───────────────────────────▲───────────────────────────────────────┘
┌─ ชั้น 3  แจ้งเตือน & ยกระดับ ──────────────────────▲───────────────┐
│  reuse od19_notification_multi_channel: LINE + Odoo Inbox + Email   │
│  dedup ตาม fingerprint → escalation ตามเวลา → สรุปรายวัน 08:00       │
└───────────────────────────▲───────────────────────────────────────┘
┌─ ชั้น 2  WATCHDOG ภายนอก (PowerShell + Task Scheduler, ทุก 1–5 นาที)│
│  ตรวจความจริง "นอก" กระบวนการ Odoo: port/HTTP/service, งานตามเวลา,  │
│  log tail, ดิสก์, ความสดของ backup → ส่งผลเข้า Odoo ด้วย XML-RPC     │
│  ถ้า Odoo ล่ม → แจ้งเองผ่านช่องทางสำรอง (ทน offline: เขียน JSON คิว) │
└───────────────────────────▲───────────────────────────────────────┘
┌─ ชั้น 1  IN-PROCESS (โมดูลใหม่ od19_system_monitor) ───────────────┐
│  heartbeat, /od19/health, cron watchdog, mail/queue backlog,        │
│  ขนาด DB/filestore, rule engine, incident, dashboard, retention     │
│  ตรวจ "heartbeat ของชั้น 2" ด้วย → จับ watchdog ที่ตายเอง            │
└────────────────────────────────────────────────────────────────────┘
```

**ทำไมต้องมีทั้งชั้น 1 และชั้น 2**: ถ้า Odoo ล่ม ชั้น 1 ย่อมรายงานตัวเองไม่ได้ จึงต้องมีชั้น 2 ที่อยู่คนละกระบวนการรายงานแทน และในทางกลับกัน ชั้น 2 อาจตายเงียบ จึงให้ชั้น 1 เฝ้า heartbeat ของชั้น 2 — เป็นการเฝ้าซึ่งกันและกัน (mutual watchdog) เหลือเพียงกรณีที่ทั้งคู่ล่มพร้อมกัน ซึ่งจะถูกจับได้ด้วย "สรุปรายวันที่ไม่มาถึง"

---

## 5. ขอบเขต และสิ่งที่ **ไม่** ทำ (Non-goals)

- **ไม่แก้ไฟล์ core ของ Odoo** (`odoo/`, `addons/`) ตามกฎเหล็กของโปรเจกต์ — ทุกอย่างอยู่ใน `custom_addons/` และสคริปต์ของโปรเจกต์
- **ไม่ทำ auto-remediation ที่มีความเสี่ยง** — ไม่ restart Odoo `:8070`, ไม่ปิด Nginx, ไม่แก้ข้อมูลธุรกิจโดยอัตโนมัติ (สอดคล้อง AGENTS.md Tier 3 ข้อ 7 และนโยบาย "AI ห้ามอนุมัติ ห้ามจ่ายเงิน")
- **ไม่เก็บ credential ในซอร์สหรือสคริปต์** — อ่านค่าจาก `odoo.conf` ตอนรันเท่านั้น
- **ไม่ส่งข้อมูลออกนอกเครื่องเป็นค่าเริ่มต้น** — Sentry เป็นข้อยกเว้นที่ผู้ใช้เลือกเอง (ดูข้อ 8 D4)
- **ไม่แทนที่ของที่มีอยู่** — Sentry / auditlog / auto_backup ยังคงใช้งานร่วมกัน ไม่รื้อทิ้ง

---

## 6. แผนดำเนินการเป็นเฟส (P1–P5)

แต่ละเฟสมี "นิยามของความสำเร็จ" (DoD) ชัดเจน และ **จบในตัว** คือให้คุณค่าได้แม้ไม่ทำเฟสถัดไป

### P1 — Early Warning ที่เห็นผลเร็ว (ยังไม่ต้องเขียนโมดูล)
ส่งมอบ: สคริปต์ `od19-health-watch.ps1` + Scheduled Task (ทุก 1–5 นาที) + ซ่อมงานที่พังอยู่

การตรวจในรอบเดียว:
1. TCP/HTTP: `:8070` ตอบ HTTP 200 ที่ `/web/login`, `:8072`, `:5432`, `:80`
2. Service: `postgresql-x64-16`, Nginx
3. Scheduled Task: ผลรันล่าสุด + อายุการรันล่าสุดของ 3 งานหลัก (Auto Start / Backup / DDNS)
4. Log: นับ ERROR/CRITICAL เฉพาะส่วนที่เพิ่มใหม่ (จำ offset ล่าสุด) + แนบตัวอย่าง 3 บรรทัด
5. ดิสก์: เตือนเมื่อว่าง < 20 GB, วิกฤต < 10 GB
6. ความสดของ backup: ล่าสุดเกิน 25 ชั่วโมง = เตือน, เกิน 7 วัน = วิกฤต
7. Dead-man switch: เขียน heartbeat ของตัวเองทุกครั้งที่รัน

DoD: มี alert จริงอย่างน้อย 1 ครั้งที่ยืนยันได้ว่า "จับได้ก่อนผู้ใช้แจ้ง" (ทดสอบโดยปิด Odoo ชั่วคราวในหน้าต่างทดสอบ); heartbeat ของ watchdog ถูกตรวจโดยชั้น 1 หรือโดย digest รายวัน

### P2 — โมดูล `od19_system_monitor` (แกนกลาง)
ส่งมอบ: โมดูล Odoo ใหม่ (branch `feature/od19_system_monitor`)

- Model: `od19.health.check` (นิยามการตรวจ), `od19.health.result` (อนุกรมเวลา), `od19.health.rule` (เกณฑ์/ความรุนแรง/หน้าต่างเวลา), `od19.health.incident` (เปิด–รับทราบ–ปิด + บันทึกสาเหตุ), `od19.health.watchdog` (สถานะที่ชั้น 2 รายงานเข้ามา)
- Endpoint: `/od19/health` (JSON สั้น ไม่มีข้อมูลอ่อนไหว) และ `/od19/health/detail` (เฉพาะผู้ดูแล)
- ตัวตรวจในระบบ: cron heartbeat (งานไม่รันตามกำหนด), backlog ของคิวอีเมล/งานเข้า, ขนาด DB, ขนาด filestore, session store
- Dashboard: การ์ดสุขภาพระบบตามสไตล์ Dashboard ปัจจุบัน (List 25 / Bar 15 / Pie 12 / Trend 24)
- Retention: cron ล้างผลการตรวจเก่า (ค่าเริ่มต้น 90 วัน) เพื่อไม่ให้โตไม่จำกัด
- ความปลอดภัย: ใช้ RBAC จาก `od19_security_roles` (บทบาท "ผู้ดูแลระบบเฝ้าระวัง")

DoD: dashboard แสดงสถานะสด; endpoint ตอบถูกต้องและไม่รั่วข้อมูล; มี unit test ผ่าน 0 failed / 0 error บน DB ทดสอบของตัวเอง

### P3 — กฎ + การแจ้งเตือน + ยกระดับ
ส่งมอบ: rule engine และการส่งสัญญาณผ่าน `od19_notification_multi_channel`

- นิยามความรุนแรง 4 ระดับ (Info / Warning / Critical / Emergency)
- Dedup ด้วย fingerprint (ตรวจ+เป้าหมาย+หน้าต่างเวลา) เพื่อกันสัญญาณซ้ำ
- Escalation: ถ้าไม่มีการรับทราบภายใน N นาที → ยกระดับช่องทาง/ผู้รับ
- รับทราบ/เลื่อน (ack/snooze) + หน้าต่างซ่อมบำรุง (maintenance window)
- สรุปรายวัน 08:00 (สอดคล้องเวลาทำการ 08:00–17:00 จ.–ศ.)

DoD: ทดสอบยิงเหตุจำลอง 3 ระดับ แล้วได้การแจ้งเตือนถูกช่องทาง ถูกคน และไม่ซ้ำ; escalation ทำงานตามเวลา

### P4 — สุขอนามัยของ log และ observability
ส่งมอบ: log ที่อ่านง่าย หมุนได้ และ error ที่รวมศูนย์

- หมุน log ขณะรันได้ (ปัจจุบันบน Windows Odoo ถือไฟล์ log เปิดไว้ จึงหมุนตอนรันไม่ได้ — แก้ด้วยโมดูลที่ติดตั้ง log handler แบบหมุนเองจากฝั่ง custom ไม่แตะ core)
- ปรับ `log_handler` เพื่อกรอง warning เชิงสคีมาที่ไม่ actionable (เช่น `odoo.schema`)
- ลด warning `Missing not-null constraint` ที่ต้นเหตุ (แก้ที่โมดูลของเราให้ตรงกับ Odoo 19)
- ขยายขอบเขต Sentry ให้มีแท็กโมดูล/เวอร์ชัน และกรองสัญญาณรบกวน
- เปิด OCA `auditlog` กับ model สำคัญ และเปิดใช้ `auto_backup` เป็น backup ชั้นที่สอง (แทนที่งานที่ล้มเหลวอยู่)

DoD: ขนาด log โตไม่เกินเพดานที่กำหนด; warning ที่เหลือเป็นสัญญาณที่มีความหมาย; audit trail บันทึกได้จริง

### P5 — AI triage และแนวโน้มเชิงCapacity (เฟสท้าย, ทางเลือก)
ส่งมอบ: ผู้ช่วยวินิจฉัยภายในเครื่อง

- ใช้ Ollama + `od19_ai_assistant` สรุป log/เหตุการณ์เป็นภาษาไทย เสนอสาเหตุที่เป็นไปได้และจุดที่ควรตรวจต่อ
- โหมด A (อ่านอย่างเดียว) เป็นค่าเริ่มต้น — **ห้าม** สั่งแก้ไข/อนุมัติ/จ่ายเงินโดยเด็ดขาด
- พยากรณ์แนวโน้มดิสก์/DB ล่วงหน้าเป็นสัปดาห์

DoD: สรุปเหตุการณ์จริง 3 เคส แล้วผู้ใช้ให้คะแนน "มีประโยชน์และไม่หลอน"; ไม่มีการเรียกใช้เครื่องมือที่เขียนข้อมูล

---

## 7. ตัวชี้วัดความสำเร็จ (KPI)

| KPI | เป้าหมาย | วัดจาก |
| --- | --- | --- |
| สัดส่วนเหตุการณ์ที่ระบบตรวจพบเองได้ (auto-detected ratio) | ≥ 90% | เปรียบเทียบ incident ที่ระบบเปิด vs. ที่ผู้ใช้แจ้ง |
| เวลาตั้งแต่เกิดเหตุถึงรับรู้ (MTTA) | ≤ 5 นาที | `create_date` ของ incident |
| ความสดของ backup สูงสุด | ≤ 25 ชั่วโมง | ไฟล์ backup ใหม่สุด |
| สัญญาณเตือนเท็จ | ≤ 5 ครั้ง/วัน | incident ที่ปิดด้วยเหตุ "false positive" |
| เหตุการณ์ล่มที่ตรวจพบเอง | 100% | ทุกครั้งที่ uptime check ล้ม |

---

## 8. ประเด็นที่ต้องให้ผู้ใช้ตัดสินใจ

| # | ประเด็น | ตัวเลือก | ข้อแนะนำของผู้จัดทำ |
| --- | --- | --- | --- |
| D1 | ช่องทางแจ้งเตือนหลัก | LINE Messaging / Odoo Inbox / Email / Windows toast | LINE + Odoo Inbox เป็นหลัก (มีตัวเชื่อมอยู่แล้วใน E7), Email เป็นสำรอง |
| D2 | จังหวะการอนุมัติ | (ก) อนุมัติทั้งแผน P1–P5 (ข) อนุมัติเฉพาะ P1 แล้วประเมินต่อ (ค) ขอปรับขอบเขตก่อน | **(ข)** — P1 ให้คุณค่าเร็วและไม่แตะโค้ด Odoo เลย ความเสี่ยงต่ำที่สุด |
| D3 | ชื่อโมดูลและพื้นที่งาน | `od19_system_monitor` / `od19_health_monitor` / อื่น ๆ | `od19_system_monitor` → branch `feature/od19_system_monitor`, worktree `c:\odoo-dev\od19-monitor` |
| D4 | ใช้ Sentry ต่อหรือไม่ | (ก) ใช้ต่อคู่กับระบบใหม่ (ข) ปิด ใช้เฉพาะระบบภายในเครื่อง | (ก) ใช้ต่อ แต่จำกัดเฉพาะ error ในโค้ด เพื่อไม่ทิ้งความสามารถเดิม |
| D5 | ให้ระบบ "แก้เอง" ได้หรือไม่ | ไม่ให้เลย / ให้เฉพาะงานไม่เสี่ยง (เช่น ล้าง session store เก่า) / ให้ restart อัตโนมัติ | ไม่อนุญาต restart ใน P1–P3 — เปิดเป็นตัวเลือกที่ปิดไว้ก่อน |
| D6 | ระยะเก็บผลการตรวจ | 30 / 90 / 365 วัน | 90 วัน + สรุปยอดรายเดือนเก็บ 1 ปี |
| D7 | ระดับความรุนแรงและผู้รับผิดชอบในเวลาทำการ/นอกราชการ | ให้ระบุรายชื่อ + ช่วงเวลา | แยก 2 หน้าต่าง: ในเวลาทำการ (08:00–17:00 จ.–ศ.) และนอกราชการ |

---

## 9. ความเสี่ยง และการควบคุม

| ความเสี่ยง | ผลกระทบ | การควบคุม |
| --- | --- | --- |
| Alert fatigue — เตือนถี่จนคนเลิกดู | สัญญาณจริงถูกมองข้าม | dedup + จัดความรุนแรง + สรุปรายวัน + เกณฑ์ปรับได้ |
| ตัวเฝ้าระวังตายเอง | กลับไปเป็นระบบล่มเงียบเหมือนเดิม | mutual watchdog (ชั้น 1 เฝ้าชั้น 2) + digest ที่ต้องมาถึงทุกวัน |
| Odoo ล่ม = ชั้น 1 รายงานไม่ได้ | ไม่มีข้อมูลตอนจำเป็นที่สุด | ชั้น 2 รายงานผ่านช่องทางสำรองโดยไม่พึ่ง Odoo |
| การตรวจถี่เกินไปทำให้ระบบช้า | กระทบผู้ใช้ (โดยเฉพาะตอน workers=0) | อ่านอย่างเดียว + จัดกลุ่ม/สรุปก่อนบันทึก + ตั้งความถี่ตามความจำเป็น |
| ข้อมูลอ่อนไหวหลุดออกภายนอก | ผิดนโยบายข้อมูล/ISO | local-first; endpoint `/od19/health` ตัดข้อมูลอ่อนไหว; ตรวจสอบก่อนเปิดช่องทางภายนอก |
| แผนไปซ้อนกับงานที่ทีมทำอยู่ | ชนไฟล์/งานซ้ำ | AGENTS.md Resource-Scoped Lease + worktree แยก + ใช้ของเดิม (E7/E8/E9) แทนการสร้างใหม่ |

---

## 10. ภาคผนวก A — คำสั่งที่รันจริงและผลลัพธ์ (2026-11-11)

**A1** — ตรวจพอร์ตที่กำลัง listen

```powershell
foreach($p in 8070,8072,5432,80){ Get-NetTCPConnection -State Listen -LocalPort $p -ErrorAction SilentlyContinue }
```
ผล: `:8070 not listening` · `:8072 not listening` · `:5432 not listening` · `:80 LISTENING pid=32832`

**A2** — ตรวจ Scheduled Task

```powershell
Get-ScheduledTask | Where-Object { $_.TaskName -match 'Odoo|Ollama|Cloudflare' } | ForEach-Object { $i=Get-ScheduledTaskInfo -TaskName $_.TaskName; "$($_.TaskName) state=$($_.State) last=$($i.LastRunTime) result=$($i.LastTaskResult)" }
```
ผล: `Cloudflare DDNS - Odoo19 state=Ready last=11/11/2026 01:40:48 result=0` · `Odoo19 Auto Start state=Ready last=11/9/2026 18:35:25 result=0` · `Odoo19 Monthly Backup state=Ready last=11/1/2026 03:00:00 result=1` · `Ollama Autostart state=Running last=11/9/2026 18:35:25 result=267009`

**A3** — วิเคราะห์ log 3,000 บรรทัดท้าย

```powershell
Get-Content C:\odoo-dev\odoo19\odoo_server.log -Tail 3000 | Where-Object { $_ -match ' (CRITICAL|ERROR|WARNING) ' }
```
ผล: 211 WARNING / 0 ERROR / 0 CRITICAL; ตัวอย่างซ้ำ ๆ: `WARNING odoo19_pdev odoo.schema: Missing not-null constraint on purchase.order.od19_purchase_type`

**A4** — สแกนโมดูลที่เกี่ยวข้องที่มีอยู่

```powershell
Get-ChildItem C:\odoo-dev\odoo19\third_party -Directory -Recurse -Depth 2 | Where-Object { $_.Name -match 'sentry|auditlog|instrumentation|backup|monitor|health' }
```
ผล: `third_party/oca/server-tools/auditlog` · `third_party/oca/server-tools/auto_backup` · `third_party/oca/server-tools/sentry` · `third_party/oca/server-tools/test_auditlog`

**A5** — สถานะงานตามเวลาของโฟลเดอร์ backup

```powershell
Get-ChildItem C:\odoo-dev\odoo19\backups | Sort-Object LastWriteTime -Descending | Select-Object -First 5
```
ผล: ไฟล์ใหม่สุด `odoo19_puat_20261105_174853.dump` (5 พ.ย. 17:48) — ไม่มีไฟล์จากการรันตามกำหนดของเดือน พ.ย.

---

## 11. การปฏิบัติตาม AGENTS.md

| หัวข้อ | การปฏิบัติ |
| --- | --- |
| AGENT_ID | `trae-odoo19` |
| Tier ของงานนี้ | Tier 2 เฉพาะการเขียนไฟล์เอกสารกลาง (`docs/`) → จับ lease `file:docs/superpowers/plans/2026-11-11-od19-system-health-monitoring-proposal.md` (TTL 900s) แล้วปล่อยคืนเมื่อเขียนเสร็จ |
| ไม่แตะไฟล์ของผู้อื่น | worktree หลักมีไฟล์ที่ยังไม่ commit ของงานอื่นอยู่ — เอกสารนี้เป็นไฟล์ใหม่ ไม่แก้ไฟล์ใดที่มีอยู่ |
| ไม่ commit / ไม่ push | ไม่มีการ commit หรือ push ใด ๆ ในงานนี้ |
| การสร้างโมดูล (อนาคต) | เมื่อเริ่ม P2 จะสร้าง worktree `c:\odoo-dev\od19-monitor` + branch `feature/od19_system_monitor` และจับ lease `git:worktree` ตามข้อ 9 |
