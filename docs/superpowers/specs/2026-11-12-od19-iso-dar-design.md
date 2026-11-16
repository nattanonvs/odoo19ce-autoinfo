# เอกสารออกแบบ: ระบบออกใบ DAR (Document Action Request)

- **วันที่:** 2026-11-12
- **โมดูลแรก:** `od19_iso_dar`
- **โมดูลในขอบเขต:** `od19_iso_dar` (ใหม่), `od19_iso_document_control` (inherit เพิ่ม smart button)
- **Branch:** `feature/od19_iso_dar` (ตาม AGENTS.md §9) · worktree `c:\odoo-dev\od19_iso_dar`
- **สถานะ:** รอตรวจสอบ (Draft for review)
- **ผู้เกี่ยวข้อง:** Document Controller / แผนกเจ้าของเอกสาร / ISO / IT

---

## 1. บทสรุป (Summary)

สร้าง **ระบบออกใบ DAR (Document Action Request)** สำหรับร้องขอ "ดำเนินการกับเอกสารควบคุม ISO" ตามมาตรฐาน ISO 9001 — เป็น **เอกสารนำส่งคำขอ** ที่แยกจากตัวเอกสารควบคุมเอง โดยครอบคลุม 6 ประเภทคำขอ (ออกใหม่ / แก้ไข / ยกเลิก / สำเนาควบคุม / สำเนาไม่ควบคุม / อื่น ๆ) พร้อม **workflow อนุมัติ 4 ขั้น** ที่สอดคล้องกับ `od19.iso.document` เดิม และลงทะเบียนเข้าสู่ **Approval Center** ที่มีอยู่แล้ว

เป้าหมายหลัก:

| # | เป้าหมาย | ตัวชี้วัด |
|---|---|---|
| 1 | มีเส้นทางร้องขอที่ตรวจสอบย้อนกลับได้ | ทุกการเปลี่ยนแปลงเอกสาร ISO มีใบ DAR อ้างอิง 100% |
| 2 | อนุมัติเป็นลำดับขั้นและตรวจสิทธิ์ได้ | ผู้อนุมัติแต่ละขั้นถูกตรวจสิทธิ์ทุกครั้ง (ยกเว้น system) |
| 3 | ลดงานมือหลังอนุมัติ | แก้ไข→เพิ่ม Rev. อัตโนมัติ · ยกเลิก→obsolete อัตโนมัติ |
| 4 | เห็นสถานะคำขอรวมศูนย์ | DAR ทุกใบปรากฏใน Approval Center (pending/incoming/done) |
| 5 | เอกสารพิมพ์ได้ตามฟอร์มองค์กร | QWeb PDF ฟอร์ม DAR + ช่องลงนาม 4 ช่อง ฟอนต์ไทยถูกต้อง |

---

## 2. ปัญหาและความต้องการ

### 2.1 สถานะปัจจุบัน

| # | เรื่อง | สภาพจริง |
|---|---|---|
| 1 | การขอสร้าง/แก้/ยกเลิกเอกสาร ISO | ไม่มีเอกสาร "ใบคำขอ" แยก — ทำผ่านการคุย/อีเมล ไม่มีเลขที่อ้างอิง |
| 2 | การอนุมัติ | `od19.iso.document` มี workflow 4 ขั้นครบ แต่ใช้กับ "ตัวเอกสาร" โดยตรง ไม่มีขั้น "คำขอก่อนสร้าง" |
| 3 | การขอสำเนา | ไม่มีทะเบียนสำเนาควบคุม/ไม่ควบคุม |
| 4 | การตรวจสอบย้อนกลับ | ไม่มีร่องรอยว่า "ใครขอ · อนุมัติเมื่อไร · เพราะเหตุใด" |
| 5 | การรวมศูนย์ | DAR (ถ้ามี) ไม่ปรากฏใน Approval Center ทำให้เจ้าหน้าที่ต้องดูหลายที่ |

### 2.2 ข้อเท็จจริงจากโมดูลเดิมที่ต้องใช้ (ตรวจจากซอร์สจริง)

| เรื่อง | หลักฐาน |
|---|---|
| workflow 4 ขั้นของเอกสาร ISO (`draft→review→approval→final_approval→approved` + `rejected`/`obsolete`) | `custom_addons/od19_iso_document_control/models/iso_document.py` |
| เมธอดตรวจสิทธิ์ผู้อนุมัติ `_check_approval_role(expected_user_field)` (ยกเว้น `base.group_system`) | `iso_document.py` (action_review_approve / action_approve / action_final_approve) |
| สร้างรหัสเอกสาร `"%s-%s-%s" % (prefix, dept_code, number)` โดย dept_code จาก `hr.department.code` (fallback `"XX"`) + `ir.sequence` padding 3 | `iso_document.py` (`_generate_document_code`) |
| revision history + `action_new_revision()` (เพิ่ม revision แล้ว reset เป็น draft) | `iso_document.py` + `od19.iso.document.revision` |
| `action_mark_obsolete()` ตั้ง OBSOLETE + `active=False` | `iso_document.py` |
| ประกาศ `ir.sequence` แบบ `noupdate=1` · padding 3 · company_id=False | `custom_addons/od19_iso_document_control/data/ir_sequence_data.xml` |
| Approval Center รับ "แหล่งอนุมัติ" ผ่าน data XML (`od19.approval.source` + `od19.approval.step`) — strategy `field`, `requester_field`, `submitted_date_field`, `rejected_states`, `success_states`, SLA | `custom_addons/od19_approval_center/data/approval_sources.py` |
| โมดูลที่ต้องพึ่งพาติดตั้งบน `odoo19_pdev` แล้ว | `_mods_odoo19_pdev.txt` |

> **นัยสำคัญ:** งานนี้เป็น **การต่อยอด ไม่ใช่การสร้างใหม่** — ลอกรูปแบบ workflow/รหัส/สิทธิ์จาก `od19.iso.document` และลงทะเบียน Approval Center แบบ data-only (ไม่ต้องแก้โค้ดโมดูลอื่น)

### 2.3 ความต้องการ

- **R1** ต้องมีเอกสาร "ใบ DAR" ที่มีเลขที่เฉพาะ (`DC{ปี ค.ศ. 2 หลัก}-{ลำดับ}`) และตรวจสอบย้อนกลับได้
- **R2** ต้องรองรับ 6 ประเภทคำขอ โดยแต่ละประเภทมีผลหลังอนุมัติที่ต่างกัน
- **R3** ต้องมี workflow อนุมัติ 4 ขั้น และตรวจสิทธิ์ผู้อนุมัติแต่ละขั้น
- **R4** หลังอนุมัติ ต้องทำผลอัตโนมัติตามประเภท (แก้ไข→เพิ่ม Rev. + คงอนุมัติ · ยกเลิก→obsolete · ออกใหม่→wizard ให้ Document Controller ยืนยัน)
- **R5** ต้องลงทะเบียนใน Approval Center เพื่อดูสถานะรวมศูนย์
- **R6** ต้องพิมพ์เป็น PDF ฟอร์ม DAR ภาษาไทย (ฟอนต์ Sarabun) + ช่องลงนาม 4 ช่อง
- **R7** ต้องแยกการเข้าถึงตามแผนก (fail-safe: เห็นเอกสารที่ไม่ระบุแผนก)
- **R8** ต้องไม่แตะไฟล์ core และไม่ต้อง `-u` โมดูล `od19_iso_document_control` เว้นแต่จำเป็น (ลดความเสี่ยง regression)

---

## 3. ขอบเขต

### 3.1 ในขอบเขต

| ด้าน | รายละเอียด |
|---|---|
| ใบ DAR | หัวเอกสาร · เลขที่ · ประเภทคำขอ · เอกสารอ้างอิง · แผนก/หมวด/มาตรฐาน ISO · เหตุผล · ผู้รับผิดชอบ 4 บทบาท |
| รายการเปลี่ยนแปลง | บรรทัดรายการเปลี่ยนแปลง/ผลกระทบ (1 DAR : N รายการ) |
| Workflow | 4 ขั้น + rejected/cancelled/closed · ตรวจสิทธิ์ต่อขั้น |
| ผลหลังอนุมัติ | แก้ไข→เพิ่ม Rev.+คงอนุมัติ · ยกเลิก→obsolete · ออกใหม่→wizard · สำเนา→ทะเบียนสำเนา |
| ทะเบียนสำเนา | โมเดล `od19.iso.dar.copy.record` (ควบคุม/ไม่ควบคุม) |
| เอกสารพิมพ์ | QWeb PDF ฟอร์ม DAR (ท้ายเอกสาร ISO เดิม + ฟอนต์ Sarabun) |
| การรวมศูนย์ | ลงทะเบียนเป็น approval source ใน Approval Center (3 ขั้น + SLA 5 วัน) |
| สิทธิ์ | 3 กลุ่ม + record rule ตามแผนก |
| Smart button | ปุ่มบน `od19.iso.document` แสดงจำนวน/รายการ DAR ที่อ้างอิง |

### 3.2 นอกขอบเขต (เฟสนี้)

- **โหมดเร่งด่วน (Deviation)** — ตัดออก (ไม่มีวันหมดอายุ, ไม่มี cron close-out)
- ระบบลายเซ็นอิเล็กทรอนิกส์ — มีอยู่แล้วที่ `od19_document_sign`
- การแก้ไฟล์ core ของ Odoo ทุกกรณี
- การ migrate ข้อมูลจาก Odoo 15 (งานนี้เป็นระบบใหม่ใน Odoo 19 ล้วน)

### 3.3 การพึ่งพา

| ประเภท | รายการ |
|---|---|
| Core | `base`, `mail`, `hr`, `web` |
| โปรเจกต์ | `od19_iso_document_control` (แม่แบบ + เอกสารอ้างอิง) · `od19_approval_center` (รวมศูนย์) · `od19_thai_font_support` (ฟอนต์ PDF) · `od19_security_roles` (ขอบเขตแผนก) |
| Python | ไม่มีไลบรารีเพิ่มนอกเหนือจากที่มีในโปรเจกต์ |

---

## 4. หลักการออกแบบ

1. **ต่อยอด ไม่สร้างใหม่** — ลอกรูปแบบ workflow/รหัส/สิทธิ์จาก `od19.iso.document` โดยไม่แก้โมดูลนั้น (ยกเว้น inherit เพิ่ม smart button อย่างเดียว)
2. **ไม่แตะ core และไม่ `-u` โมดูล ISO เดิมโดยไม่จำเป็น** — ลดความเสี่ยง regression ≈ 0
3. **config-driven integration** — ลงทะเบียน Approval Center ด้วย data XML ล้วน ไม่แก้โค้ดโมดูล approval_center
4. **automatic ต้องตรวจสอบได้** — ทุกผลอัตโนมัติ (เพิ่ม Rev./obsolete) บันทึกใน log/note ของ DAR
5. **ยืนยัน 2 จังหวะกับงานที่กระทบเอกสารจริง** — "ออกใหม่" ให้ Document Controller ยืนยันก่อนสร้างเอกสาร
6. **ไทยเป็นหลัก** — label สองภาษาไทย/อังกฤษ และฟอนต์ Sarabun ใน PDF
7. **แยกโดเมนชัดเจน** — DAR เป็นโมดูลใหม่ ไม่ปนกับ `od19_iso_document_control`

---

## 5. สถาปัตยกรรม

### 5.1 การแบ่งโมดูล

```
od19_iso_dar   ← แกนกลาง: ใบ DAR + workflow 4 ขั้น + รายการเปลี่ยนแปลง + ทะเบียนสำเนา + PDF + approval source
   └─ inherit od19.iso.document  (เพิ่ม dar_ids / dar_count + smart button เท่านั้น)
```

| โมดูล | depends |
|---|---|
| `od19_iso_dar` | `base`, `mail`, `hr`, `web`, `od19_iso_document_control`, `od19_approval_center`, `od19_thai_font_support`, `od19_security_roles` |

### 5.2 โครงไฟล์ (โดยย่อ)

```
od19_iso_dar/
├── __init__.py · __manifest__.py
├── models/
│   ├── od19_iso_dar.py               # โมเดลหลัก + workflow
│   ├── od19_iso_dar_change_line.py   # รายการเปลี่ยนแปลง/ผลกระทบ
│   ├── od19_iso_dar_copy_record.py   # ทะเบียนสำเนา
│   └── od19_iso_document.py          # inherit เพิ่ม dar_ids / dar_count
├── wizard/
│   └── od19_iso_dar_create_document.py  # สร้างเอกสารใหม่จาก DAR (prefill)
├── views/
│   ├── od19_iso_dar_views.xml        # list/kanban/form/search
│   ├── od19_iso_dar_copy_views.xml
│   ├── od19_iso_document_views.xml   # smart button
│   └── menu.xml                      # ใต้ ISO Management → ควบคุมเอกสาร
├── report/
│   ├── od19_iso_dar_report.xml       # QWeb PDF
│   └── od19_iso_dar_report_template.xml
├── security/
│   ├── od19_iso_dar_groups.xml
│   ├── ir.model.access.csv
│   └── od19_department_rule.xml      # record rule ตามแผนก
├── data/
│   ├── ir_sequence_data.xml          # ir.sequence รหัส od19.iso.dar
│   ├── approval_source_data.xml      # ลงทะเบียน Approval Center
│   ├── mail_template_data.xml
│   └── ir_cron_data.xml              # เตือน SLA คำขอค้าง
├── tests/
│   └── test_od19_iso_dar.py
└── i18n/th.po
```

---

## 6. โครงสร้างข้อมูล

### 6.1 ฟิลด์บน `od19.iso.dar`

| ฟิลด์ | ชนิด | หมายเหตุ |
|---|---|---|
| `name` | Char | เลขที่ DAR (`DC26-001`) — สร้างจาก `ir.sequence` |
| `request_type` | Selection | `new` / `revise` / `obsolete` / `copy_controlled` / `copy_uncontrolled` / `other` |
| `document_id` | M2o `od19.iso.document` | เอกสารอ้างอิง (ไม่บังคับเฉพาะประเภท `new`/`other`) |
| `category_id` | M2o `od19.iso.document.category` | ประเภทเอกสารเป้าหมาย |
| `department_id` | M2o `hr.department` | แผนกเจ้าของคำขอ (ใช้กับ record rule) |
| `standard_ids` | M2m `od19.iso.standard` | มาตรฐานที่เกี่ยวข้อง |
| `iso_clause` | Char | ข้อกำหนด ISO ที่อ้างอิง |
| `reason` | Text | เหตุผล/ความจำเป็น |
| `description` | Html | รายละเอียดคำขอ |
| `status` | Selection | `draft`/`review`/`approval`/`final_approval`/`approved`/`rejected`/`cancelled`/`closed` |
| `requester_id` | M2o `res.users` | ผู้ขอ (default = ผู้สร้าง) |
| `reviewer_id` | M2o `res.users` | ผู้อนุมัติขั้น review |
| `approver_id` | M2o `res.users` | ผู้อนุมัติขั้น approval |
| `final_approver_id` | M2o `res.users` | ผู้อนุมัติขั้น final_approval |
| `effective_date` | Date | วันที่มีผล |
| `reject_reason` | Text | เหตุผลที่ถูกตีกลับ |
| `change_line_ids` | O2m `od19.iso.dar.change.line` | รายการเปลี่ยนแปลง |
| `copy_record_ids` | O2m `od19.iso.dar.copy.record` | ทะเบียนสำเนา |
| `attachment_ids` | M2m `ir.attachment` | เอกสารแนบ |
| `company_id` | M2o `res.company` | บริษัท (multi-company safe) |

### 6.2 โมเดลใหม่

| โมเดล | ฟิลด์หลัก | หน้าที่ |
|---|---|---|
| `od19.iso.dar` | ตาม 6.1 | ใบ DAR หลัก + workflow |
| `od19.iso.dar.change.line` | `dar_id`, `field_changed`, `before_value`, `after_value`, `impact`, `note` | รายการเปลี่ยนแปลง/ผลกระทบ |
| `od19.iso.dar.copy.record` | `dar_id`, `copy_type` (controlled/uncontrolled), `recipient_id`, `copy_number`, `issued_date`, `note` | ทะเบียนสำเนา |

### 6.3 เมธอดสำคัญบน `od19.iso.dar`

| เมธอด | หน้าที่ |
|---|---|
| `create(vals)` | สร้างเลขที่ `DC{ปี}-{ลำดับ}` ผ่าน `ir.sequence` |
| `_check_approval_role(expected_user_field)` | ตรวจสิทธิ์ผู้อนุมัติแต่ละขั้น (ยกเว้น `base.group_system`) — ลอกรูปแบบจาก `od19.iso.document` |
| `action_submit_for_review()` | draft → review |
| `action_review_approve()` / `action_review_reject()` | review → approval / rejected |
| `action_approve()` / `action_approve_reject()` | approval → final_approval / rejected |
| `action_final_approve()` | final_approval → approved + **เรียก `_apply_approval_effect()`** |
| `action_final_reject()` | final_approval → rejected |
| `action_cancel()` | ยกเลิกก่อนอนุมัติขั้นสุดท้าย → cancelled |
| `action_close()` | approved → closed (ปิดใบ) |
| `action_reset_to_draft()` | กลับ draft (ตามขั้นที่อนุญาต) |
| `_apply_approval_effect()` | **แกนผลหลังอนุมัติ** — dispatch ตาม `request_type` (ดู §8) |

### 6.4 การใช้ของเดิมแทนการสร้างใหม่

| งาน | ใช้ของเดิม |
|---|---|
| รหัสเอกสาร ISO (เมื่อสร้างจาก DAR) | `od19.iso.document._generate_document_code()` |
| เพิ่ม revision ของเอกสารเดิม | `od19.iso.document.action_new_revision()` |
| เลิกใช้เอกสารเดิม | `od19.iso.document.action_mark_obsolete()` |
| ขอบเขตแผนก | `od19_security_roles.group_od19_department_scope` / `group_od19_department_all` |
| การรวมศูนย์อนุมัติ | `od19.approval.source` + `od19.approval.step` |
| ฟอนต์ PDF ไทย | `od19_thai_font_support` + ท้ายเอกสาร ISO เดิม |

---

## 7. ส่วนติดต่อผู้ใช้ (UI)

### 7.1 เมนู

อยู่ใต้ root `ISO Management` (`menu_iso_root`) → `ควบคุมเอกสาร` (`menu_iso_document_control`):

| เมนู | Action |
|---|---|
| ใบคำขอ DAR | `action_od19_iso_dar` |
| ทะเบียนสำเนา | `action_od19_iso_dar_copy` |
| รายงานสรุป DAR | `action_od19_iso_dar_report` (P4) |

### 7.2 หน้าจอหลัก (Form)

- **หัวฟอร์ม** (`oe_title`): H1 = เลขที่ DAR (เด่น) · H2 = ประเภทคำขอ
- **ปุ่มสถานะ** (statusbar) ตาม workflow 4 ขั้น + ปุ่ม Print / Cancel / Close
- **กลุ่มข้อมูล**: ประเภทคำขอ · เอกสารอ้างอิง · แผนก/หมวด/มาตรฐาน · วันที่มีผล
- **แท็บ**: รายการเปลี่ยนแปลง · ทะเบียนสำเนา · เอกสารแนบ · ประวัติ/บันทึก (chatter)

### 7.3 Kanban / Search

- Kanban จัดกลุ่มตาม `status` และ `request_type`
- Search: filter ตามประเภท/แผนก/สถานะ · group by แผนก/ประเภท/ผู้อนุมัติ
- ฟิลด์ custom ขึ้นต้นด้วย `od19_` ตามมาตรฐานโปรเจกต์

### 7.4 Smart button บน `od19.iso.document`

เพิ่มปุ่ม "ใบ DAR" แสดง `dar_count` เปิดดู `dar_ids` (inherit view อย่างเดียว)

### 7.5 สิทธิ์

| กลุ่ม | สิทธิ์ |
|---|---|
| `group_iso_dar_user` | อ่าน/สร้าง/แก้ ใบของตัวเอง · ไม่อนุมัติ · ไม่ลบ |
| `group_iso_dar_controller` | จัดการทะเบียนสำเนา · ยืนยันสร้างเอกสารใหม่ |
| `group_iso_dar_manager` | อนุมัติขั้นสุดท้าย + ตั้งค่า + ลบ |

Record rule ตามแผนก (`od19_department_rule.xml`):
- `['|', ('department_id', '=', user.od19_department_id.id), ('department_id', '=', False)]` ผูก `group_od19_department_scope`
- `[(1, '=', 1)]` ผูก `group_od19_department_all`

### 7.6 การรวมศูนย์ (Approval Center)

ลงทะเบียน `od19.approval.source` (data XML ล้วน):

| ค่า | ตั้งเป็น |
|---|---|
| Model | `od19.iso.dar` |
| Strategy | `field` |
| Requester field | `requester_id` (fallback `create_uid`) |
| Submitted date field | `create_date` |
| Success states | `approved` |
| Rejected states | `rejected` |
| Steps | Review / Approval / Final approval |
| SLA | 5 วัน |

---

## 8. ลำดับการทำงาน (Data Flow)

### 8.1 วงจรหลัก

```
สร้างใบ DAR (draft · ได้เลข DC{ปี}-{ลำดับ})
   → ส่งตรวจ (review)          [reviewer_id]
   → อนุมัติขั้น 1 (approval)   [approver_id]
   → อนุมัติขั้น 2 (final_approval) [final_approver_id]
   → อนุมัติ (approved) → _apply_approval_effect() ตาม request_type
   → ปิดใบ (closed)
```

### 8.2 ผลหลังอนุมัติตามประเภท (`_apply_approval_effect`)

| `request_type` | ผลอัตโนมัติ |
|---|---|
| `new` | เปิด **wizard** สร้างเอกสารใหม่ (prefill จาก DAR) → Document Controller ยืนยัน → เรียก `od19.iso.document` create + `_generate_document_code()` |
| `revise` | เรียก `document_id.action_new_revision()` เพิ่ม Rev. + **คงสถานะอนุมัติ** (ไม่อนุมัติซ้ำ) |
| `obsolete` | เรียก `document_id.action_mark_obsolete()` → OBSOLETE + `active=False` |
| `copy_controlled` | สร้าง `od19.iso.dar.copy.record` (copy_type=controlled) |
| `copy_uncontrolled` | สร้าง `od19.iso.dar.copy.record` (copy_type=uncontrolled) |
| `other` | ไม่มีผลอัตโนมัติ (บันทึกเป็นหลักฐาน) |

### 8.3 SLA

- cron รายวันแจ้งเตือนคำขอที่ค้างเกิน 5 วันในแต่ละขั้น (ผ่าน `mail.activity` / template)

---

## 9. กติกาและการป้องกัน (Guards / Edge cases)

- **ตรวจสิทธิ์ทุกขั้น** ผ่าน `_check_approval_role` (ยกเว้น `base.group_system`)
- **ต้องมีผู้อนุมัติครบก่อนอนุมัติขั้นสุดท้าย** — ถ้าฟิลด์บทบาทว่าง ให้เตือน
- **`document_id` บังคับ** สำหรับ `revise` / `obsolete` / `copy_*` (ยกเว้น `new` / `other`)
- **กันการทำผลซ้ำ** — `_apply_approval_effect()` ทำงานครั้งเดียวเมื่อ status → approved (idempotent guard)
- **คงสถานะอนุมัติหลังเพิ่ม Rev.** — ไม่ reset เอกสารเดิมเป็น draft
- **`obsolete` ต้องยืนยัน** — แสดงข้อความยืนยันก่อนตั้ง `active=False`
- **ไม่มีฟิลด์วันหมดอายุ / ไม่มี cron close-out** (ตัดโหมดเร่งด่วนออกแล้ว)
- **ไม่แตะ core** — ใช้ inherit เท่านั้น
- **multi-company** — ตั้ง `company_id` ให้สอดคล้องกับเอกสารอ้างอิง

---

## 10. แผนการทดสอบ

Unit test บน DB ทดสอบส่วนตัว (`odoo19_t_<AGENT_ID>`) เกณฑ์ **0 failed / 0 error**:

| # | กรณีทดสอบ |
|---|---|
| T1 | สร้าง DAR ได้เลขที่รูปแบบ `DC{ปี 2 หลัก}-{NNN}` ถูกต้อง และลำดับไม่ซ้ำ |
| T2 | workflow 4 ขั้นเดินครบ: draft→review→approval→final_approval→approved |
| T3 | ตรวจสิทธิ์: ผู้ไม่มีสิทธิ์อนุมัติขั้นนั้นถูกปฏิเสธ |
| T4 | reject ในแต่ละขั้น → status = rejected + เก็บ `reject_reason` |
| T5 | `revise` → เอกสารเดิมได้ Rev. ใหม่ + คงสถานะอนุมัติ |
| T6 | `obsolete` → เอกสารเดิม status = obsolete + `active=False` |
| T7 | `new` → wizard prefill ถูกต้อง |
| T8 | `copy_controlled` / `copy_uncontrolled` → สร้างทะเบียนสำเนาถูกประเภท |
| T9 | record rule ตามแผนก: user เห็นเฉพาะแผนกตัวเอง + ที่ไม่ระบุแผนก |
| T10 | `_apply_approval_effect()` ไม่ทำงานซ้ำ (idempotent) |
| T11 | Smart button บน `od19.iso.document` แสดง `dar_count` ถูกต้อง |
| T12 | PDF ฟอร์ม DAR ออกได้ ฟอนต์ไทยถูกต้อง (smoke) |

---

## 11. การแบ่งเฟส

| เฟส | ขอบเขต | ผลลัพธ์ |
|---|---|---|
| **P1** | โครงโมดูล + `od19.iso.dar` + workflow 4 ขั้น + security/menu + approval source | สร้าง/อนุมัติใบ DAR ได้ + ปรากฏใน Approval Center |
| **P2** | `od19.iso.dar.change.line` + PDF ฟอร์ม DAR + smart button | พิมพ์ได้ + เห็นความเชื่อมโยงกับเอกสาร ISO |
| **P3** | `_apply_approval_effect()` (revise/obsolete) + wizard สร้างเอกสารใหม่ + cron SLA | ผลอัตโนมัติทำงานครบ |
| **P4** | ทะเบียนสำเนา (`od19.iso.dar.copy.record`) + รายงานสรุป | ครบทั้ง 6 ประเภทคำขอ |

---

## 12. การตัดสินใจที่ยืนยันแล้ว

| หัวข้อ | ข้อสรุป | วันที่ |
|---|---|---|
| ความหมาย DAR | Document Action Request (ISO) | 2026-11-12 |
| แนวทางสถาปัตยกรรม | โมดูลใหม่ `od19_iso_dar` (ไม่แก้ `od19_iso_document_control` เว้นแต่ inherit) | 2026-11-12 |
| จำนวนขั้นอนุมัติ | 4 ขั้น (เหมือน `od19.iso.document`) | 2026-11-12 |
| ประเภทคำขอ | 6 ประเภท: ออกใหม่/แก้ไข/ยกเลิก/สำเนาควบคุม/สำเนาไม่ควบคุม/อื่น ๆ | 2026-11-12 |
| ผลหลังอนุมัติ | ผสม: แก้ไข/ยกเลิกอัตโนมัติ · ออกใหม่ให้ Controller ยืนยัน | 2026-11-12 |
| การแก้ไข/เพิ่ม Revision | เพิ่ม Rev. + คงสถานะอนุมัติ (ไม่อนุมัติซ้ำ) | 2026-11-12 |
| เลขที่ใบ DAR | `DC{ปี ค.ศ. 2 หลัก}-{ลำดับ padding 3}` เช่น `DC26-001` | 2026-11-12 |
| โหมดเร่งด่วน (Deviation) | **ตัดออก** (ไม่มีวันหมดอายุ/ไม่มี cron close-out) | 2026-11-12 |

---

## 13. ความเสี่ยง

| # | ความเสี่ยง | แนวทางลด |
|---|---|---|
| 1 | inherit view `od19.iso.document` อาจชนกับ view ของโมดูลอื่น | ใช้ xpath เจาะจง + ระบุ priority |
| 2 | `ir.sequence` รหัสชนกับที่อื่น | ใช้ code เฉพาะ `od19.iso.dar` + `noupdate=1` |
| 3 | การเพิ่ม Rev. อัตโนมัติอาจกระทบเอกสารที่กำลังถูกแก้ | ตรวจ status เอกสารก่อนทำผล + แจ้งเตือนเมื่อไม่พร้อม |
| 4 | Approval Center ไม่แสดงใบถ้า state ไม่ตรง | ตั้ง `success_states`/`rejected_states` ให้ตรงกับ status จริง |
| 5 | Record rule ตามแผนกเข้มเกินจนผู้บริหารไม่เห็น | ใช้คู่ `group_od19_department_all` เหมือนโมดูลเดิม |

---

## 14. เรื่องที่ต้องได้รับการชี้ขาดก่อนเริ่ม P1

1. **ค่าเริ่มต้นของ `request_type`** เมื่อเปิดฟอร์มใหม่ — ตั้ง default เป็น `new` หรือให้เลือกเอง?
2. **ผู้มีสิทธิ์ "ยืนยันสร้างเอกสารใหม่"** — เฉพาะ `group_iso_dar_controller` หรือรวม manager?
3. **การส่งกลับ (reject) แล้วแก้ไข** — ให้กลับไปที่ `draft` หรือกลับไปขั้นก่อนหน้า?
