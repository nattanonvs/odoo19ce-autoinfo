# OD19 Internal Issue Design (ระบบแจ้งปัญหา/ขอความช่วยเหลือภายใน)

Date: 2026-11-16
Module: `od19_internal_issue` (ใหม่ — ต่อยอด OCA `helpdesk_mgmt`)
Scope: ให้พนักงานแจ้งปัญหา/ขอความช่วยเหลือภายในบริษัทหรือในระบบ Odoo เป็น "หัวข้อ" แล้วระบบจัดคิว มอบหมาย และติดตามจนปิดได้อย่างโปร่งใสและเป็นธรรม

## ปัญหาและเป้าหมาย

1. **ไม่รู้จะแจ้งที่ไหน** — ปัญหาไอที/ระบบ, ข้อเสนอแนะปรับปรุง, ปัญหาคุณภาพ-ISO ตกหล่น ไม่มีที่รวมศูนย์
2. **คิวไม่ชัดเจน** — งานเข้าจำนวนมาก ลำดับไม่ชัด คนทำสับสนว่าอันไหนทำไปแล้ว/ควรทำอันไหนก่อน
3. **ผู้แจ้งอยากรู้ว่าต้องรอนานแค่ไหน** — ต้องการเห็น "อยู่คิวที่ N มีงานก่อนหน้า M งาน"
4. **ความสำคัญที่ไม่เป็นธรรม** — ทุกคนอ้างว่างานตัวเองสำคัญสุด ต้องมีเกณฑ์กลางที่เท่าเทียมและตรวจสอบได้
5. **การแซงคิว** — ถ้าจำเป็นต้องแซงจริง ต้องมีเส้นทางขออนุมัติที่ชัดเจนและมีผู้รับผิดชอบ

เป้าหมาย: พนักงานทุกคนมีช่องทางเดียวในการแจ้ง → ระบบจัดคิวตามเกณฑ์กลาง → โปร่งใส เห็นตำแหน่งคิวและเหตุผลของ priority

## การตัดสินใจที่อนุมัติแล้ว

| # | ประเด็น | ที่เลือก |
|---|---|---|
| 1 | ขอบเขต/วัตถุประสงค์ | **C) รวมศูนย์ที่เดียว** — ทั้ง IT Helpdesk + ข้อเสนอแนะปรับปรุง + ปัญหา ISO แล้วแยกประเภท/ทีมอัตโนมัติ |
| 2 | ช่องทางรับเรื่อง | **D) Backend + Portal + Email** |
| 3 | การแยกประเภท/มอบหมาย | **C + D) ผู้แจ้งเลือกหมวดใหญ่ + ระบบ route อัตโนมัติจากคำสำคัญ/หมวดย่อย + กล่องกลาง (Triage)** |
| 4 | ความลึกของกระบวนการ | **B) กลาง** — สถานะ ~6 ขั้น, ไม่บังคับอนุมัติ, มีธงฉุกเฉิน, เก็บวิธีแก้ไปต่อยอด KB |
| 5 | แนวทางสร้าง | **A) โมดูลใหม่ `od19_internal_issue`** แยกงานภายใน — งานบริการลูกค้าคงอยู่ที่ `od19_helpdesk_extension` |
| 6 | ผู้อนุมัติแซงคิว | **C) อนุมัติ 2 ชั้น** — หัวหน้าแผนกต้นสังกัดผู้แจ้ง + หัวหน้าทีมเจ้าของคิว ต้องเคาะครบ |
| 7 | โครงสร้าง/ลำดับคิว | **E) คิวต่อทีม, เรียง priority→FIFO, ลากปรับได้, แสดงตำแหน่งสด, งานที่อนุมัติแซงคิวถูกแทรกตามตำแหน่งที่เลือก** |
| 8 | ค่าเริ่มต้นการยินยอม + timeout | **C + 1) ถือว่ายินยอมอัตโนมัติ** + เปิดหน้าต่างกด "ขอแซงคิว" ได้ภายใน X ชม. · คำขอแซงคิวที่ค้างเกินกำหนด → คำขอหมดอายุ → ใช้คิวปกติไปก่อน |
| 9 | ความเท่าเทียมของ priority | **D) Impact × Urgency Matrix + FIFO + โควต้างานด่วน + audit log** |
| 10 | ความเป็นส่วนตัวของเรื่อง | คงไว้ตามเดิม: public / แผนก / ส่วนตัว (private) + record rules บังคับจริง |
| 11 | การแจ้งเตือน | คงไว้ตามเดิม: หลายช่องทางผ่าน `od19_notification_multi_channel` (Email + Inbox + LINE) |

## Non-Goals

1. ไม่แตะ Odoo Core (`odoo/`, `addons/`)
2. ไม่แก้ไขพฤติกรรมงานบริการลูกค้าใน `od19_helpdesk_extension` (ยกเว้นปรับ `team_type` ให้รองรับทีมภายในเพิ่ม)
3. ไม่ให้ AI/ระบบอนุมัติหรือตัดสินใจแทนคน — การอนุมัติแซงคิวเป็นมนุษย์กดทั้งหมด
4. ไม่ทำ SaaS/SLA ภายนอกใน Phase 1 (SLA เป็น Phase 2)
5. ไม่ให้ผู้แจ้งตั้ง priority ตัวเลขเองโดยตรง

## สถาปัตยกรรม

### 1. โมดูลและ dependency

โมดูลใหม่ `custom_addons/od19_internal_issue/` (มี manifest อยู่แล้ว — ต้องสร้างไฟล์ที่ประกาศไว้ให้ครบ)

dependency:
- `helpdesk_mgmt` (OCA) — โมเดลหลัก `helpdesk.ticket` / `helpdesk.ticket.team` / stages / categories / channels
- `od19_helpdesk_extension` — ใช้ `team_type` ร่วม (เพิ่ม dependency เข้า manifest จากเดิม)
- `base_tier_validation` (OCA) — ใช้กับ ISO/ปรับปรุงใน Phase 2
- `hr` — อ้าง `hr.department` / `hr.employee`
- `mail` — thread/activities
- `od19_notification_multi_channel` — gateway แจ้งเตือน
- `od19_security_roles` — RBAC รวมศูนย์

### 2. โมเดลและฟิลด์ใหม่

**`helpdesk.ticket` (inherit)**
- `issue_stream` (selection): `it_support` / `improvement` / `iso_capa` / `unsure` — หมวดใหญ่ที่ผู้แจ้งเลือก
- `impact` (selection): `I1` / `I2` / `I3`
- `urgency` (selection): `U1` / `U2` / `U3`
- `priority` — ใช้ของ OCA แต่คำนวณจาก Impact/Urgency (readonly ต่อผู้แจ้ง)
- `emergency` (boolean)
- `visibility` (selection): `public` / `department` / `private`
- `visibility_department_id` (m2o `hr.department`)
- ฟิลด์คิว: `queue_sequence` (integer, ตัวจัดลำดับจริงในทีม), `queue_position` (compute, ไม่ store), `queue_ahead_count` (compute, ไม่ store)
- `is_priority_inserted` (boolean), `insert_before_id` (m2o `helpdesk.ticket`)
- `consent_state` (selection): `pending` / `accepted` / `jump_requested` — ค่าเริ่มต้น `accepted`
- `jump_window_deadline` (datetime) — เปิดให้กด "ขอแซงคิว" ถึงเมื่อไร
- `kb_converted` (boolean), `kb_article_ref` (char) — handoff (Phase 2)
- ใช้ `resolution` (Html) ที่มีอยู่แล้วใน `od19_helpdesk_extension`

**`helpdesk.ticket.team` (inherit)**
- `issue_stream` (selection) — ทีมนี้รับ stream ไหน (ใช้ route)
- `is_triage_team` (boolean) — กล่องกลาง
- `weekly_priority_quota` (integer) — เพดานงานด่วนต่อสัปดาห์ (ค่าเริ่มต้นตั้งได้)

**โมเดลใหม่ `helpdesk.routing.rule`**
- `name`, `keyword` (char), `issue_stream` (selection), `team_id`, `category_id`, `sequence`, `active`
- ใช้ match คำสำคัญในหัวข้อ/รายละเอียด เพื่อเติม team/category/stream เมื่อยังว่าง

**โมเดลใหม่ `helpdesk.queue.request`** (คำขอแซงคิว)
- `ticket_id` (m2o), `requested_by` (m2o res.users), `reason` (text)
- `approver_reporter_head_id` + `approver_team_head_id` (m2o res.users, default จากต้นสังกัดผู้แจ้ง / หัวหน้าทีมเจ้าของคิว)
- `state` (selection): `draft` / `waiting_reporter_head` / `waiting_team_head` / `approved` / `rejected` / `expired`
- `reporter_head_approved` / `team_head_approved` (boolean)
- `insert_before_id` (m2o `helpdesk.ticket`) — ตำแหน่งแทรกที่ผู้อนุมัติเลือก
- `deadline` (datetime) — กำหนดหมดอายุคำขอ
- `decision_note` (text)

### 3. การแยกประเภท & Route

เมื่อสร้าง ticket:
1. ถ้าผู้ส่งตั้ง `team_id` เอง → เคารพ
2. ถ้าเลือก `issue_stream` → route ไปทีมที่ผูก stream นั้น (`helpdesk.ticket.team.issue_stream`)
3. ถ้าเลือก `unsure` → เข้า **Triage team** (`is_triage_team`)
4. เสริมด้วย `helpdesk.routing.rule`: match คำสำคัญในหัวข้อ/รายละเอียด เพื่อเติม team/category ให้ถ้ายังว่าง
5. แอดมิน/agent จัดต่อได้จากกล่อง Triage

### 4. สถานะ (Stages)

Data (ป้ายไทย): `ใหม่` → `มอบหมายแล้ว` → `กำลังดำเนินการ` → `รอผู้แจ้ง` → `แก้ไขแล้ว` → `ปิด`

### 5. ความเป็นส่วนตัว (Privacy)

- `visibility` = public / แผนก / ส่วนตัว
- Record rules:
  - ผู้แจ้งเห็นเฉพาะเรื่องของตัวเอง (+ public ในทีมที่เกี่ยวข้อง)
  - Agent เห็นเรื่องในทีมของตัวเอง
  - Manager เห็นทั้งหมด
  - `private` เห็นเฉพาะผู้แจ้ง + ผู้รับผิดชอบ + ผู้มีสิทธิ์ผู้จัดการ
  - `department` เห็นเฉพาะคนในแผนกที่กำหนด

### 6. การแจ้งเตือน

ผ่าน `od19_notification_multi_channel` ในเหตุการณ์:
- สร้างเรื่องใหม่ / มอบหมาย / อัปเดตสถานะ / emergency
- คำขอแซงคิว: แจ้งหัวหน้าทั้งสอง / แจ้งผู้แจ้งเมื่ออนุมัติ-ปฏิเสธ-หมดอายุ

### 7. สิทธิ์ & เมนู (RBAC)

- Groups: `Reporter` / `Agent` / `Manager` (ผูก `od19_security_roles`)
- ขยายเมนู Helpdesk เดิม **ไม่สร้างซ้ำ** — submenu: เรื่องของฉัน / IT Support / ปรับปรุง-ISO / Triage / ตั้งค่า

### 8. คิวงาน & คำขอแซงคิว

- **คิวต่อทีม** — แต่ละทีมมีลำดับคิวของตัวเอง
- **เกณฑ์เรียง (ค่าเริ่มต้น):** `priority` ก่อน → แล้ว FIFO (เวลาสร้าง) · หัวหน้า/agent ลากสลับได้
- **แสดงตำแหน่งให้ผู้แจ้ง:** `queue_position` + `queue_ahead_count` โชว์บน Portal และในฟอร์ม
- **การยินยอม:** เรื่องเข้าคิวทันที = ถือว่ายินยอม · เปิดหน้าต่างกด "ขอแซงคิว" ภายใน `jump_window_deadline` (X ชม. ตั้งได้) หลังจากนั้นปุ่มปิด
- **คำขอแซงคิว:**
  - ผู้แจ้งกด "ขอแซงคิว" + เหตุผล → สร้าง `helpdesk.queue.request`
  - อนุมัติ 2 ชั้น: หัวหน้าแผนกต้นสังกัดผู้แจ้ง + หัวหน้าทีมเจ้าของคิว (ต้องเคาะครบ)
  - ผู้อนุมัติเลือก `insert_before_id` (แทรกก่อน ticket ไหน)
  - อนุมัติครบ → ตั้ง `is_priority_inserted` + `insert_before_id` → จัด `queue_sequence` ใหม่
  - **Timeout:** ไม่เคาะภายใน `deadline` → คำขอ `expired` → เรื่องใช้คิวปกติไปก่อน

### 9. ความเท่าเทียมของ priority (Fair Priority)

**Impact:** I3 = กระทบทั้งบริษัท/ระบบหยุดทั้งระบบ · I2 = หลายแผนก/หลายคน · I1 = เฉพาะตัวเอง
**Urgency:** U3 = หยุดงานทันที · U2 = มีผลแต่มีงานแทนชั่วคราว · U1 = ไม่กระทบ

`score = Impact + Urgency` (2–6):

| score | priority | ป้าย |
|---|---|---|
| 6 | P3 | ด่วนวิกฤต |
| 5 | P2 | สูง |
| 3–4 | P1 | กลาง |
| 2 | P0 | ต่ำ |

กติกาเสริม:
- priority เท่ากัน → ตัดสินด้วย FIFO
- **โควต้างานด่วน** ต่อทีม/สัปดาห์ (`weekly_priority_quota`) — เกินโควต้าต้องเดินเส้นทางอนุมัติแซงคิว
- **Emergency flag** → แจ้งเตือนทุกช่องทางทันที + ส่งหัวหน้าทีม/Triage แต่การแทรกคิวยังต้องอนุมัติ
- ผู้แจ้งตั้งได้แค่ Impact/Urgency; ทุกการปรับ priority มี **audit log** และแสดงเหตุผล

### 10. Handoff → Knowledge Base (Phase 2)

ปุ่ม "แปลงเป็นบทความ KB" → สร้าง knowledge article (ปลายทางต้องยืนยัน: `od19_knowledge_enhanced` หรือโมดูล knowledge อื่น)

## Data Flow (สรุป)

```
ผู้แจ้ง (Backend/Portal/Email)
  → เลือก issue_stream + ตอบ Impact/Urgency + (visibility)
  → ระบบคำนวณ priority + route เข้าทีม (หรือ Triage)
  → เข้าคิว (queue_sequence) + แสดง queue_position/ahead_count ให้ผู้แจ้ง
  → [ถ้าต้องการ] ขอแซงคิว → อนุมัติ 2 ชั้น + เลือกตำแหน่งแทรก → จัดคิวใหม่
  → Agent รับงาน (Processing) → Waiting (รอผู้แจ้ง) → Resolved → Closed
  → [Phase 2] แปลงเป็นบทความ KB
```

## Edge Cases

- ผู้แจ้งไม่กดยินยอม/ไม่ตอบ → เรื่องใช้คิวปกติ (auto-consent) — ไม่ค้าง
- คำขอแซงคิวไม่มีใครเคาะทัน deadline → `expired` ใช้คิวปกติ
- ผู้แจ้งไม่มีแผนก/หัวหน้าแผนก → ใช้หัวหน้า default ของทีมเจ้าของคิวเป็นผู้อนุมัติชั้นแรกชั่วคราว (หรือตั้งค่า fallback)
- โควต้างานด่วนเต็ม → ปฏิเสธการตั้ง priority สูงโดยตรง ให้เดินเส้นทางขออนุมัติ

## การทดสอบ

Unit tests (บน DB ทดสอบของ agent):
- routing rule เติม team/category จากคำสำคัญถูกต้อง
- กล่อง Triage รับเรื่อง `unsure`
- คำนวณ priority จาก Impact × Urgency
- privacy record rules (own / department / private)
- emergency → มี notify
- queue ordering (priority→FIFO) + `queue_position` ถูกต้อง
- queue.request: 2 ชั้นเคาะครบ → `insert_before_id` → คิวจัดใหม่; เคาะไม่ครบ/หมดอายุ → ใช้คิวปกติ
- สร้าง ticket ผ่าน portal + email

## การแบ่งเฟส

**Phase 1 (แกน):** โมดูล+ฟิลด์, route (หมวดใหญ่+keyword+triage), สถานะ, privacy, RBAC+เมนู, notify, คิว & คำขอแซงคิว, fair priority, tests → ติดตั้งใช้งานได้จริง

**Phase 2:** tier validation (ISO/ปรับปรุง), KB handoff, SLA (`helpdesk_mgmt_sla`)

## อ้างอิงที่มีอยู่แล้วในโปรเจกต์

- OCA Helpdesk: `third_party/oca/helpdesk/`
- `custom_addons/od19_helpdesk_extension/` — งานบริการลูกค้า + `team_type`
- `custom_addons/od19_notification_multi_channel/` — gateway แจ้งเตือน
- `third_party/oca/tier-validation/base_tier_validation`
- `custom_addons/od19_security_roles/`
- `custom_addons/od19_internal_issue/__manifest__.py` (scaffold เดิม)
