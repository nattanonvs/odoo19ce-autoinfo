# เอกสารออกแบบ: ใบเบิกค่าใช้จ่ายแบบรวมหลายรายการ (Expense Claim Header) — Odoo 19 CE

- **วันที่:** 2026-11-21 (rev3 — ล็อก K7/K8 + เริ่มส่งมอบ Phase 1 และ Phase 2)
- **รหัสงาน:** OD19-EXPENSE-CLAIM
- **โมดูลที่แตะ:** สร้างใหม่ `od19_hr_expense_claim`; แก้ `od19_hr_expense_thai`, `od19_hr_expense_portal`, `od19_approval_center`, `od19_role_catalog` (ไม่แตะ Odoo core และไม่แตะ `third_party/oca/`)
- **สถานะ:** ล็อกทิศทางแล้ว (approved direction) — **Phase 1 + Phase 2 เขียนโค้ดและเทสต์ผ่านแล้ว** (Phase 3–4 ยังไม่เริ่ม)
- **ผู้เกี่ยวข้อง:** พนักงานผู้เบิก / หัวหน้าแผนก / ฝ่ายบัญชี / CEO / ฝ่ายไอที–แอดมิน
- **แนวทางที่เลือก:** ทำ "ใบเบิกรวม" = เอกสารหัวใบ (Expense Claim) รวมหลายรายการ แล้ว **อนุมัติที่หัวใบครั้งเดียว**
- **ข้อตัดสินใจที่ล็อกแล้ว (2026-11-20):** K1 = โมดูลใหม่ `od19_hr_expense_claim` · K2 = ทีละใบก่อน (batch ข้ามใบเป็นเฟส 4) · K3 = บังคับทุกการเบิกผ่านหัวใบ (ใบละ ≥1 บรรทัด) · K4 = โพสต์บัญชีที่บรรทัด (core เดิม) สั่งจากหัวใบ
- **เจตนาหลักของผู้ใช้ (สำคัญ):** ไม่ได้กังวลแค่ผู้อนุมัติกดซ้ำ ๆ แต่ **กังวลประสบการณ์ของ "คนเบิก"** ว่าต้องเป็นระบบ เป็นมิตร ไม่วุ่นวายหลายขั้นตอน — รวมหลายรายการไว้ในใบเบิกเดียวให้จบง่าย

---

## 1. บทสรุป (Summary)

ปัจจุบันพนักงานสร้างค่าใช้จ่ายเป็น `hr.expense` **ทีละรายการ** และแต่ละรายการต้องผ่านการอนุมัติ **3 ชั้นตามลำดับ** (หัวหน้าแผนก → บัญชี → CEO) โดยใช้ OCA `tier.validation` ที่ติดตั้งบน `hr.expense` โดยตรง

ผลคือ: **เบิก 20 รายการ = ผู้อนุมัติแต่ละชั้นกดอนุมัติ 20 ครั้ง** (CEO 20 ครั้ง, บัญชี 20 ครั้ง, หัวหน้าแผนก 20 ครั้ง) เพราะ:

- Odoo 19 **ยกเลิก `hr.expense.sheet` (Expense Report)** แล้ว — ไม่มีหัวใบที่รวมหลายรายการอีกต่อไป แต่ละ `hr.expense` เป็นเอกสารแยก
- `tier.validation` ทำบน **รายการเดียว** (`validate_tier()` เป็น `ensure_one()`) และอนุมัติแบบ batch ผ่าน tier ไม่ได้

งานนี้จึง **สร้างหัวใบ "ใบเบิก" (`od19.expense.claim`) ขึ้นใหม่** เพื่อรวมหลายบรรทัด (`hr.expense`) แล้วย้ายการอนุมัติ 3 ชั้นไปที่ **หัวใบ** — ผู้อนุมัติเห็นและอนุมัติ **1 ครั้งต่อใบเบิก** แทนที่จะอนุมัติทีละบรรทัด

**เป้าหมายเชิงผลลัพธ์**

- พนักงานยื่น "ใบเบิก 1 ใบ" ที่มีหลายบรรทัดค่าใช้จ่ายได้ (หรือบรรทัดเดียวก็ได้)
- ผู้อนุมัติ 3 ชั้นอนุมัติ **ที่หัวใบครั้งเดียว** → ลดจำนวนครั้งการอนุมัติลงเท่าจำนวนบรรทัด
- หน้าจอ/พอร์ทัลพนักงานยื่นและติดตามที่ระดับ "ใบเบิก"
- ไม่แตะ core Odoo และไม่แตะ `third_party/oca/`
- งานบัญชี/ภาษีไทยเดิม (VAT, WHT, ใบรับรองแทนใบเสร็จ, เบี้ยเลี้ยง, Mileage, จ่ายคืนพนักงาน) ทำงานต่อได้ครบ

---

## 2. สภาพปัจจุบันและช่องว่าง (Problem)

### 2.1 สิ่งที่มีอยู่แล้ว (ยืนยันจากโค้ดจริง)

| ส่วน | สถานะ | รายละเอียด |
|---|---|---|
| `addons/hr_expense` (core CE) | มี | `hr.expense` + state `draft→submitted→approved→posted→in_payment→paid` (+`refused`); **ไม่มี** `hr.expense.sheet` แล้ว; `action_submit` / `action_approve` / `action_post` รองรับ multi-record |
| `third_party/oca/tier-validation/hr_expense_tier_validation` | มี | ติด mixin `tier.validation` บน `hr.expense` (`_state_field="approval_state"`, `_state_from=["submitted"]`, `_state_to=["approved"]`); ห้ามแก้ไฟล์นี้ |
| `third_party/oca/tier-validation/base_tier_validation` | มี | `validate_tier()` เป็น **`ensure_one()`** → อนุมัติทีละ record เท่านั้น |
| `od19_hr_expense_thai` | มี | `tier.definition` 3 รายการบน `hr.expense` (seq 30/20/10, เงื่อนไข `[(1,'=',1)]` = ทุกใบ), กลุ่ม CEO, จ่ายคืนพนักงานจริง + reconcile |
| `od19_hr_expense_enhanced` | มี | เอกสารไทย/VAT/ใบรับรองแทนใบเสร็จ/เบี้ยเลี้ยง ม.42(3)/Mileage/สมุดรถ/XLSX/WHT |
| `od19_hr_expense_portal` | มี | wizard ยื่นเบิกเร็ว `od19.expense.quick.create`, portal `/my/expenses`, Kanban "ใบเบิกของฉัน" (ระดับ `hr.expense`) |
| `od19_approval_center` | มี | source `hr.expense` เป็น `strategy: tier_validation` (อ่าน `tier.review`) |

### 2.2 ช่องว่างเทียบกับความต้องการ

| # | ประเด็น | สภาพปัจจุบัน | ผลกระทบ |
|---|---|---|---|
| G1 | ไม่มีหัวใบรวมหลายรายการ | Odoo 19 ตัด `hr.expense.sheet` ออก | พนักงานยื่นทีละรายการ กระจัดกระจาย |
| G2 | อนุมัติทีละบรรทัด | tier ผูกกับ `hr.expense` + `validate_tier()` เป็น `ensure_one()` | CEO/บัญชี/หัวหน้าแผนก อนุมัติซ้ำ ๆ ตามจำนวนบรรทัด |
| G3 | ไม่มีมุมมอง "ใบเบิก" สำหรับติดตาม | Kanban/portal อ่านที่ `hr.expense` | ผู้เบิกและผู้อนุมัติไม่เห็นภาพรวมต่อใบ |
| G4 | การจ่ายคืนกระจัดกระจาย | จ่ายคืนทีละ `hr.expense` | การเงินต้องจ่าย/กระทบยอดทีละบรรทัด |

---

## 3. ความต้องการ (Requirements)

- **R1** มีเอกสารหัวใบ **"ใบเบิก"** (`od19.expense.claim`) ที่รวมบรรทัดค่าใช้จ่าย (`hr.expense`) ได้หลายบรรทัด
- **R2** การอนุมัติ 3 ชั้น (หัวหน้าแผนก → บัญชี → CEO) ทำที่ **หัวใบครั้งเดียว** ไม่ใช่ต่อบรรทัด
- **R3** ลดจำนวนครั้งการอนุมัติต่อใบเบิกจาก "เท่าจำนวนบรรทัด" เหลือ "3 ครั้งต่อใบ" (ชั้นละ 1)
- **R4** เมื่อหัวใบอนุมัติครบ 3 ชั้น → ทุกบรรทัดถูกทำเครื่องหมายอนุมัติ (พร้อมบันทึกบัญชีต่อ)
- **R5** รองรับใบเบิกที่มีบรรทัดเดียวได้ (พนักงานไม่ต้องสร้างหัวใบแยกสำหรับเรื่องเล็ก ๆ)
- **R6** คงคุณสมบัติภาษี/บัญชีไทยเดิมครบ: VAT, WHT, ใบรับรองแทนใบเสร็จ, เบี้ยเลี้ยง ม.42(3), Mileage, จ่ายคืนพนักงาน
- **R7** พนักงานยื่นและติดตามได้ทั้งหลังบ้าน และพอร์ทัล (มือถือ)
- **R8** ไม่แตะ Odoo core และไม่แตะ `third_party/oca/`
- **R9** ยอดรวมของใบเบิก = ผลรวมยอดบรรทัด และแสดงให้ตรวจสอบก่อนส่ง
- **R10** ผู้อนุมัติมอบหมายต่อ (Forward) ให้ผู้อื่นในกลุ่มได้ เหมือนเดิม

---

## 4. ขอบเขต (Scope)

### 4.1 ในขอบเขต (In scope)

| # | รายการ | พื้นผิว | เฟส |
|---|---|---|---|
| 1 | โมเดลหัวใบ `od19.expense.claim` + ฟิลด์ `od19_claim_id` บน `hr.expense` | Backend | 1 |
| 2 | ย้าย `tier.definition` 3 ชั้นจาก `hr.expense` → `od19.expense.claim` | Backend | 1 |
| 3 | ฟอร์ม/ทรี/Kanban หัวใบ (backend) + เมนู "ใบเบิกของฉัน" / "ใบเบิกทั้งหมด" | Backend | 1 |
| 4 | การซิงก์สถานะหัวใบ → บรรทัด (อนุมัติ/ปฏิเสธ/โพสต์) | Backend | 1 |
| 5 | ปรับ wizard ยื่นเบิกเร็วให้สร้างเป็นหัวใบ + บรรทัด | Backend | 2 |
| 6 | ปรับ Kanban/มุมมองพนักงานเดิมจากรายการ → ใบเบิก | Backend | 2 |
| 7 | ปรับ Approval Center source → `od19.expense.claim` | Backend | 2 |
| 8 | ปรับ portal `/my/expenses` ให้แสดงเป็นใบเบิก | Portal | 3 |
| 9 | ตัวเลือกจ่ายคืนพนักงาน "ระดับใบเบิก" (payment เดียวต่อใบ) | Backend | 3 |
| 10 | เทสต์ TDD ทุกชั้น | Tests | ทุกเฟส |

### 4.2 นอกขอบเขต (Out of scope)

- ไม่แก้ core `hr.expense` โครงสร้างหลัก และไม่แตะ `third_party/oca/`
- ไม่ทำ batch approve **ข้ามใบ** ในเฟสนี้ (อนุมัติทีละใบเบิก; batch ข้ามใบเป็นตัวเลือกเฟสถัดไป — ดู K2)
- ไม่ทำ OCR/สแกนใบเสร็จ
- ไม่เปลี่ยนหลักการบัญชี/ภาษีเดิม (ใช้กลไกของ `od19_hr_expense_enhanced` / `od19_hr_expense_thai` ต่อ)

---

## 5. สถาปัตยกรรมและที่ตั้งโมดูล (Design)

```
┌────────────────────────────────────────────────────────────┐
│  ชั้น UX                                                     │
│  od19_hr_expense_portal  : wizard ยื่นเบิกเร็ว + portal      │
│  (แก้: wizard สร้างเป็น "หัวใบ + บรรทัด"; portal แสดงหัวใบ)  │
└───────────────────────────┬────────────────────────────────┘
                            │
┌───────────────────────────┴────────────────────────────────┐
│  od19_hr_expense_claim  (ใหม่)  ← หัวใจงานนี้                │
│  - od19.expense.claim (หัวใบ) + tier.validation 3 ชั้น       │
│  - ฟิลด์ od19_claim_id บน hr.expense                         │
│  - views / security / tier.definition (ย้ายมาจาก _thai)     │
└───────────────────────────┬────────────────────────────────┘
                            │ ต่อยอด
┌───────────────────────────┴────────────────────────────────┐
│  od19_hr_expense_enhanced : เอกสารไทย/VAT/เบี้ยเลี้ยง/Mileage│
│  od19_hr_expense_thai     : จ่ายคืนพนักงาน + reconcile       │
│  od19_approval_center     : มุมมองผู้อนุมัติรวมศูนย์           │
│  od19_role_catalog        : กลุ่มสิทธิ์ (CEO)                │
│  hr.expense (core CE)     : บรรทัดค่าใช้จ่าย + บัญชี          │
└────────────────────────────────────────────────────────────┘
```

| โมดูล | สถานะ | ความรับผิดชอบ / สิ่งที่แก้ |
|---|---|---|
| `od19_hr_expense_claim` | **ใหม่** v19.0.1.0.0 | โมเดลหัวใบ + tier 3 ชั้น + views + security + เทสต์ |
| `od19_hr_expense_thai` | แก้ | **ย้าย/ลบ** `tier.definition` 3 รายการที่เคยชี้ `hr.expense` ออก (ย้ายไปหัวใบ); คง logic จ่ายคืนเดิม; คงกลุ่ม CEO |
| `od19_hr_expense_portal` | แก้ | wizard ยื่นเบิกเร็วสร้างหัวใบ + บรรทัด; Kanban/portal อ่านหัวใบ |
| `od19_approval_center` | แก้ข้อมูล | เปลี่ยน source จาก `hr.expense` → `od19.expense.claim` |
| `od19_role_catalog` | แก้ | คงบทบาท CEO (ไม่เปลี่ยน) — ตรวจว่า imply กลุ่ม CEO ถูกต้อง |
| `hr_expense` (core) | **ไม่แก้** | ใช้ `hr.expense` เป็นบรรทัดตามเดิม |

**Dependency ของโมดูลใหม่ `od19_hr_expense_claim`:**
`hr_expense`, `hr_expense_tier_validation`, `base_tier_validation`, `base_tier_validation_forward`, `od19_hr_expense_thai` (ดึง `od19_hr_expense_enhanced` มาด้วย), `mail`

> **หมายเหตุ:** การถอด `tier.definition` ออกจาก `hr.expense` ทำได้โดย **ลบ record ในไฟล์ data ของ `od19_hr_expense_thai`** เท่านั้น (ไม่ต้องแก้ `third_party/oca/`) — mixin `tier.validation` ยังอยู่บน `hr.expense` แต่เมื่อไม่มี definition ที่เข้าเงื่อนไข `need_validation` จะเป็น `False` จึงไม่สร้าง review และไม่บล็อกการแก้ไข

---

## 6. โมเดลข้อมูล (Data Model)

### 6.1 หัวใบใหม่ `od19.expense.claim`

| ฟิลด์ | ชนิด | หมายเหตุ |
|---|---|---|
| `name` | Char (sequence) | เลขที่ใบเบิก เช่น `EXP/2026/0001` |
| `employee_id` | Many2one `hr.employee` | ผู้เบิก (default = พนักงานของ user ปัจจุบัน) |
| `department_id` | Many2one `hr.department` | related จากพนักงาน (ใช้หา approver ชั้น 1) |
| `company_id`, `currency_id` | Many2one | จากบริษัท/payment |
| `date` | Date | วันที่เอกสาร (default = วันนี้) |
| `submit_date`, `approval_date` | Datetime | เวลายื่น/เวลาอนุมัติครบ |
| `line_ids` | One2many `hr.expense` (`od19_claim_id`) | บรรทัดค่าใช้จ่าย (ต้องมี ≥ 1) |
| `total_amount` | Monetary (compute+store) | ผลรวม `total_amount` ของบรรทัด |
| `payment_mode` | Selection | `own_account` / `company_account` — ต้องตรงกันทุกบรรทัด |
| `payment_method` | Selection | วิธีจ่ายคืน (จาก `od19_hr_expense_thai`) |
| `state` | Selection | `draft` / `submitted` / `approved` / `posted` / `paid` / `refused` |
| `review_ids`, `validation_status`, `need_validation` | (mixin) | จาก `tier.validation` |
| `note` / `attachment_ids` | Text / Mail | หมายเหตุ + ไฟล์แนบ (ผ่าน `mail.thread`) |

**ข้อกำหนด:** `state` ต้องเป็น `_state_field` ของ mixin (`_state_from = ['submitted']`, `_state_to = ['approved']`) เพื่อให้ tier ทำงานเหมือนที่ทำกับ `hr.expense` ปัจจุบัน

### 6.2 เพิ่มฟิลด์บน `hr.expense` (บรรทัด)

| ฟิลด์ | ชนิด | หมายเหตุ |
|---|---|---|
| `od19_claim_id` | Many2one `od19.expense.claim` (`ondelete='cascade'`, index) | หัวใบที่บรรทัดนี้สังกัด |
| `od19_claim_state` | Char/Selection (related) | สถานะหัวใบเพื่อแสดงในมุมมองบรรทัด (optional) |

> ฟิลด์เดิมทั้งหมดของ `hr.expense` (รวมที่เพิ่มโดย `od19_hr_expense_enhanced` / `_thai`) **คงอยู่ครบ** — บรรทัดยังมี VAT/WHT/ประเภทเอกสาร/เบี้ยเลี้ยง/Mileage ต่อบรรทัด

---

## 7. สถานะและเส้นทางเอกสาร + การอนุมัติ

### 7.1 สถานะหัวใบ ↔ บรรทัด

| สถานะหัวใบ | ใครทำต่อ | ผลกับบรรทัด (`hr.expense.approval_state`) |
|---|---|---|
| `draft` | พนักงานแก้ไข/ส่ง | `False`/`draft` |
| `submitted` (ยังไม่ครบ tier) | ผู้อนุมัติตามลำดับ | `submitted` |
| `approved` (ครบ 3 ชั้น) | บัญชีบันทึกบัญชี | **`approved`** (ทุกบรรทัด) |
| `posted` | การเงินจ่ายคืน | state ของบรรทัด = `posted` |
| `paid` | — | จ่ายคืนแล้ว |
| `refused` | พนักงานแก้ไข/ส่งใหม่ | `refused` (ทุกบรรทัด) |

### 7.2 การอนุมัติ 3 ชั้นบนหัวใบ (OCA `tier.validation`)

- โมเดล `od19.expense.claim` inherit `tier.validation`
- `tier.definition` 3 รายการ (ย้ายมาจาก `od19_hr_expense_thai` โดยเปลี่ยน `model_id` → `od19.expense.claim`):

| ลำดับอนุมัติ | ชั้น | กลุ่มผู้อนุมัติ | `sequence` |
|---|---|---|---|
| 1 (ก่อน) | หัวหน้าแผนก | `hr_expense.group_hr_expense_manager` | 30 |
| 2 | ฝ่ายบัญชี | `account.group_account_manager` | 20 |
| 3 (สุดท้าย) | CEO | `od19_hr_expense_thai.group_od19_expense_ceo_approver` | 10 |

- ตอน `state='submitted'` → พนักงานกด **Request Validation** → สร้าง `tier.review` 3 รายการ → ผู้อนุมัติแต่ละชั้นกด **Validate** ตามลำดับ (ข้ามขั้นไม่ได้ เหมือนพฤติกรรมปัจจุบัน)
- **Forward** เปิดด้วย `has_forward = True` (เหมือนเดิม)
- เมื่อ review ครบ → `validation_status = 'validated'` → หัวใบเขียน `state='approved'` และ **propagate** ไปบรรทัดด้วย `line_ids.write({'approval_state': 'approved'})`

> **หมายเหตุการกระทบ core:** core `hr.expense._check_can_create_move()` บังคับว่าบรรทัดต้อง `state='approved'` ก่อนโพสต์ — การ propagate `approval_state='approved'` จากหัวใบจะทำให้โพสต์ได้ตามปกติ โดย **ไม่ต้องเรียก core `action_approve`** เพื่อเลี่ยงการอนุมัติซ้ำซ้อนที่ระดับบรรทัด

### 7.3 การโพสต์/จ่าย

- **โพสต์:** บัญชีกด **"Post Journal Entries"** ที่หัวใบ → ระบบเรียก `line_ids.action_post()` (กลไก core เดิม) หรือปล่อยให้โพสต์ที่บรรทัดตามเดิม (แล้วแต่ K4)
- **จ่ายคืนพนักงาน:** เฟส 1-2 คงจ่ายคืนต่อบรรทัด (กลไก `od19_hr_expense_thai` เดิม); เฟส 3 เพิ่มปุ่ม **"จ่ายคืนทั้งใบ"** สร้าง `account.payment` เดียวต่อใบเบิกแล้ว reconcile ทุกบรรทัด

---

## 8. บัญชีและภาษี (ใช้ของเดิมทั้งหมด)

| กรณี | กลไก | ที่มีอยู่ |
|---|---|---|
| พนักงานออกเงินเอง (`own_account`) | จ่ายคืนด้วย `account.payment` + reconcile กับเจ้าหนี้พนักงาน | `od19_hr_expense_thai` |
| บริษัทออกเงิน (`company_account`) | ไม่ต้องจ่ายคืน (สร้าง payment/entry ตอนโพสต์) | core |
| VAT (ภาษีซื้อ) | `tax_ids` **ต่อบรรทัด** | core + enhanced |
| ใบรับรองแทนใบเสร็จรับเงิน | `od19_document_type = payment_certificate` → บังคับ VAT = 0 | `od19_hr_expense_enhanced` |
| เบี้ยเลี้ยง ม.42(3) | `od19_is_per_diem` + วงเงิน + เหตุผล | `od19_hr_expense_enhanced` |
| หัก ณ ที่จ่าย (WHT) | ตามที่จัดเตรียมไว้ | `od19_hr_expense_enhanced` |
| ค่าเดินทางตามระยะทาง (Mileage) | ยอด = ระยะทาง × อัตรา; ไม่มี VAT/ไม่หัก WHT | `od19_hr_expense_enhanced` |

> **หลักการ:** ทุกอย่างที่คำนวณภาษี/บัญชี **อยู่ที่บรรทัด** เหมือนเดิม หัวใบเป็นเพียง "ตัวรวม + ด่านอนุมัติ" ไม่คำนวณภาษีเอง → ลดความเสี่ยงทางบัญชี

---

## 9. UX พนักงาน (หลังบ้าน + พอร์ทัล)

> **UX คือหัวใจของงานนี้** — เป้าหมายไม่ใช่แค่ลดจำนวนครั้งที่ผู้อนุมัติกด แต่ว่า **"คนเบิก" ต้องรู้สึกเป็นระบบ เป็นมิตร และจบในไม่กี่ขั้นตอน** การรวมหลายรายการไว้ในใบเบิกเดียวคือกลไกหลักที่ทำให้เรื่องนี้เกิดขึ้นจริง

### 9.1 หลักการ

- พนักงานคิดเป็น "ใบเบิก 1 ใบ" ที่มีหลายบรรทัด (หรือบรรทัดเดียว) — **ไม่ต้องสร้างเอกสารซ้ำ ๆ ทีละรายการ**
- เพิ่ม/ลบบรรทัดในใบเดียวกันได้ในที่เดียว ไม่ต้องออกไปสร้างใหม่แล้วกลับมา
- เห็นยอดรวมของใบชัดเจนก่อนส่ง
- เห็น "รอใคร" ที่หัวใบ (หัวหน้าแผนก/บัญชี/CEO) ไม่ใช่แค่ `submitted`
- **ลดจำนวนขั้นตอนให้สั้นที่สุด** — ยื่นใบเบิกจบได้ในหน้าจอเดียว (≤ 4 ขั้นตอน)

### 9.2 หลังบ้าน (Backend)

- เมนู **"ใบเบิกของฉัน"** (Kanban/List หัวใบ จัดกลุ่มตาม `state`) และ **"ใบเบิกทั้งหมด"** (สำหรับแอดมิน/บัญชี)
- ฟอร์มหัวใบ: ส่วนหัว (พนักงาน/วันที่/วิธีจ่าย/ยอดรวม) + ส่วนบรรทัด (`line_ids` แก้ไขได้) — ใช้ฟิลด์ของ `od19_hr_expense_enhanced`/`_thai` ในฟอร์มบรรทัด
- ปุ่ม: **Submit → Request Validation → Validate ×3 → Post Journal Entries → (Reimburse)**

### 9.3 Wizard ยื่นเบิกเร็ว (ปรับของเดิม)

- `od19.expense.quick.create` (ใน `od19_hr_expense_portal`) ปรับให้สร้าง **หัวใบ + บรรทัด** แทนการสร้าง `hr.expense` เดี่ยว
- คงกลไกค่าเริ่มต้นอัตโนมัติ (หมวดค่าใช้จ่าย → `tax_ids`/บัญชี/ประเภทเอกสาร) และโหมด Mileage
- รองรับ "เพิ่มอีกบรรทัด" ในใบเดียวกันก่อนส่ง

### 9.4 พอร์ทัล (เฟส 3)

- `/my/expenses` แสดงเป็น **ใบเบิก** (รายการ/รายละเอียด) พร้อม timeline การอนุมัติ 3 ชั้น
- ฟอร์มยื่นเบิกแบบ responsive (ถ่าย/แนบรูปจากมือถือได้)
- พนักงานที่ไม่มีสิทธิ์หลังบ้านเห็นเฉพาะใบเบิกของตัวเอง

---

## 10. สิทธิ์และความปลอดภัย

- **พนักงาน:** เห็น/แก้ใบเบิกของตัวเอง (`employee_id.user_id = user` หรือ `create_uid = user`)
- **ผู้อนุมัติ 3 กลุ่ม:** เห็นใบเบิกที่ค้างในชั้นของตน (tier validation จัดการผ่าน `tier.review.reviewer_ids`)
- **บัญชี/ผู้ดูแล:** เห็นทั้งหมด
- **ir.rule:** เพิ่มกฎบน `od19.expense.claim` (ของตัวเอง) + กฎผู้อนุมัติ/บัญชี (ทั้งหมด)
- **BOM/ความปลอดภัย:** ไม่มี credential ฝังในโค้ด; ใช้ RBAC กลางตามโครงเดิม

---

## 11. การย้ายข้อมูล (Migration)

- **เฟส 1:** ยังไม่มีข้อมูลจริงบน `odoo19_pdev`/`odoo19_puat` → ตรวจก่อน ถ้าไม่มี ก็ไม่ต้องเขียน migration
- **ถ้ามีข้อมูลจริง:** เขียน migration `post-migrate` เพื่อ
  1. ลบ `tier.review` ที่ค้างของ `hr.expense` (ถ้ามี)
  2. (ทางเลือก) ห่อ `hr.expense` ที่ยัง active ให้เป็นใบเบิกบรรทัดเดียว
- **ลำดับโหลด data:** `tier.definition` ของหัวใบต้องโหลดหลังโมเดล/กลุ่ม CEO พร้อมแล้ว

---

## 12. แผนการส่งมอบ (Phases)

| เฟส | เนื้อหา | ผลลัพธ์ที่ตรวจได้ |
|---|---|---|
| **Phase 1** | โมเดลหัวใบ + `od19_claim_id` + ย้าย tier 3 ชั้นมาที่หัวใบ + ฟอร์ม/ทรี/Kanban + sync สถานะไปบรรทัด | ยื่นใบเบิก 1 ใบที่มี 3 บรรทัด → อนุมัติ 3 ชั้น **ที่หัวใบครั้งเดียว** → บรรทัดได้ `approved` ครบ |
| **Phase 2** | ปรับ wizard ยื่นเบิกเร็ว + Kanban พนักงาน + Approval Center source → หัวใบ | พนักงานยื่นใบเบิกหลายบรรทัดได้จบใน ≤ 4 ขั้น; Approval Center แสดงใบเบิก |
| **Phase 3** | Portal แสดงเป็นใบเบิก + จ่ายคืนระดับใบเบิก | พนักงานยื่น/ติดตามจากมือถือ; การเงินจ่ายคืนทั้งใบครั้งเดียว |
| **Phase 4** | Polish: รายงาน XLSX ระดับใบ, i18n, คู่มือ, (ทางเลือก) batch approve ข้ามใบ | ตามความจำเป็น |

การส่งมอบทำ **ตามเฟส** — แต่ละเฟสมีเทสต์ผ่านก่อนไปเฟสถัดไป

---

## 13. การทดสอบ (TDD)

| # | กรณีทดสอบ | ระดับ |
|---|---|---|
| T1 | สร้างหัวใบ + 3 บรรทัด → ยอดรวม = ผลรวมบรรทัด | TransactionCase |
| T2 | ยื่นใบเบิก → Request Validation สร้าง review 3 รายการ เรียง seq 1,2,3 | TransactionCase |
| T3 | อนุมัติข้ามขั้นไม่ได้ (CEO ก่อนลำดับ → ไม่ผ่าน) | TransactionCase |
| T4 | อนุมัติครบ 3 ชั้น → หัวใบ `state='approved'` **และบรรทัดทุกตัว `approval_state='approved'`** | TransactionCase |
| T5 | จำนวนครั้งการอนุมัติ = 3 ต่อใบ (ไม่ใช่ 3×จำนวนบรรทัด) | TransactionCase |
| T6 | ปฏิเสธที่หัวใบ → บรรทัดทุกตัว `refused` | TransactionCase |
| T7 | โพสต์บรรทัดจากหัวใบสำเร็จ (core `action_post`) เมื่ออนุมัติครบ | TransactionCase |
| T8 | `hr.expense` ไม่ถูก tier บล็อกการแก้ไขอีก (ไม่มี definition บน `hr.expense`) | TransactionCase |
| T9 | พนักงานเห็นเฉพาะใบเบิกของตัวเอง (หลังบ้าน + portal) | TransactionCase / HttpCase |
| T10 | ภาษี/เบี้ยเลี้ยง/Mileage/ใบรับรองแทนใบเสร็จ ยังทำงานครบต่อบรรทัด | TransactionCase |
| T11 | จ่ายคืนระดับใบเบิก (เฟส 3) → เจ้าหนี้ทุกบรรทัดถูก reconcile ปิดยอด | TransactionCase |

---

## 14. ความเสี่ยงและประเด็นต้องยืนยัน (Open Questions)

**ล็อกแล้ว (2026-11-20):**

| # | ประเด็น | ข้อสรุปที่ล็อก |
|---|---|---|
| K1 ✅ | **ที่ตั้งโมดูล** | สร้าง **โมดูลใหม่ `od19_hr_expense_claim`** (แยกขอบเขต ย้อนกลับง่าย ย้าย tier ออกมาชัด) |
| K2 ✅ | **อนุมัติทีละใบ หรือ batch ข้ามใบ** | เฟส 1–3 **ทีละใบ** (หัวใบ = 1 การอนุมัติ) · เฟส 4 ค่อยเพิ่ม batch ข้ามใบ (extend `validate_tier` multi-record ในโมดูลเรา) |
| K3 ✅ | **บังคับหัวใบทุกครั้งไหม** | **บังคับทุกการเบิกผ่านหัวใบ** (ใบละ ≥1 บรรทัด) — เส้นทางเดียว ตรงเจตนา "รวมให้จบง่าย" · เบิกรายการเดี่ยว = หัวใบบรรทัดเดียวอัตโนมัติ |
| K4 ✅ | **โพสต์บัญชีที่หัวใบหรือบรรทัด** | **โพสต์ที่บรรทัด** (กลไก core เดิม) สั่งจากหัวใบ — รักษาความถูกต้องของ GL ต่อบรรทัด |
| K7 ✅ | **ข้อมูลอนุมัติเดิม** ใน `odoo19_pdev`/`odoo19_puat` | **ตรวจแล้ว 2026-11-21 (อ่านอย่างเดียว)** — `puat`: `hr.expense` 0 แถว + `tier.review` ของ `hr.expense` 0 แถว → **ไม่ต้อง migration ข้อมูล** (migration ที่มีมีแค่ลบ `tier.definition` เดิม ซึ่งปลอดภัยเพราะไม่มี review อ้างถึง); `pdev`: `hr.expense` 33 แถว (ข้อมูล dev, ไม่มี `tier.review` ค้าง) |
| K8 ✅ | **Approval Center** อ่าน `tier.review` ที่ model ไหน | **เปลี่ยน source เป็น `od19.expense.claim` แล้ว (Phase 2)** — source เดิม (`hr.expense`) ถูกแทนที่ด้วยหัวใบ (migration `19.0.1.2.0` repoint บน DB เดิม + `post_init_hook` seed หัวใบตอนติดตั้งใหม่) |

**ยังเปิดอยู่ (ตัดสินตอนทำแต่ละเฟส):**

| # | ประเด็น | แนวทาง / ตัวเลือก |
|---|---|---|
| K5 | **ฟิลด์ `manager_id` ของ core ยังมีอยู่** (core มี approver เดี่ยวต่อบรรทัด) | ตั้งให้หัวใบเป็นผู้ตัดสิน → propagate `approval_state` ตรง ไม่เรียก core `action_approve` ซ้ำ |
| K6 | **`payment_mode` ผสมกันในใบเดียว** (own/company) | จำกัดให้ใบเบิกหนึ่งใบใช้ `payment_mode` เดียว (validate error ถ้าผสม) |
| K9 | **ลำดับ sequence ของ tier บนโมเดลใหม่** | ทดสอบด้วย T2/T3 ก่อนสรุปค่า (อ้างพฤติกรรม OCA เดิม 30/20/10) |

---

## 15. เกณฑ์ยอมรับ (Acceptance Criteria)

- [ ] พนักงานสร้างใบเบิก 1 ใบที่มีหลายบรรทัดค่าใช้จ่ายได้ (หรือบรรทัดเดียวก็ได้)
- [ ] ใบเบิกทุกใบผ่านการอนุมัติครบ 3 ชั้นตามลำดับ **ที่หัวใบ** และข้ามขั้นไม่ได้
- [ ] **จำนวนครั้งการอนุมัติ = 3 ต่อใบเบิก** (ไม่ขึ้นกับจำนวนบรรทัด)
- [ ] เมื่อหัวใบอนุมัติครบ → บรรทัดทุกตัวเป็น `approved` และโพสต์บัญชีได้ตามปกติ
- [ ] ภาษี/บัญชีไทย (VAT, WHT, ใบรับรองแทนใบเสร็จ, เบี้ยเลี้ยง, Mileage) ทำงานครบต่อบรรทัด
- [ ] พนักงานที่ไม่มีสิทธิ์หลังบ้านยื่นและติดตามใบเบิกผ่าน portal บนมือถือได้
- [ ] Approval Center แสดงใบเบิกให้ผู้อนุมัติแต่ละชั้น
- [ ] เทสต์ T1–T11 ผ่านทั้งหมด
- [ ] ไม่มีการแก้ไขไฟล์ใน Odoo core (`odoo/`, `addons/`) และใน `third_party/oca/`

---

## 16. ภาคผนวก: จุดอ้างอิงโค้ด

- **core (อ่านเท่านั้น):** [hr_expense.py](file:///c:/odoo-dev/odoo19/addons/hr_expense/models/hr_expense.py) — `action_submit` (L1132), `action_approve` (L1153), `action_post` (L1168), `_do_approve` (L1452), `_check_can_create_move` (L1445)
- **core list batch actions:** [list.js](file:///c:/odoo-dev/odoo19/addons/hr_expense/static/src/views/list.js) — `displaySubmit/displayApprove/displayPost`
- **OCA tier (อ่านเท่านั้น):** [hr_expense.py](file:///c:/odoo-dev/odoo19/third_party/oca/tier-validation/hr_expense_tier_validation/models/hr_expense.py) — `_state_field="approval_state"`, `_state_from=["submitted"]`, `_state_to=["approved"]`; [tier_validation.py](file:///c:/odoo-dev/odoo19/third_party/oca/tier-validation/base_tier_validation/models/tier_validation.py) — `validate_tier()` (L662, `ensure_one`), `_validate_tier()` (L547)
- **tier definitions ปัจจุบัน (จะย้าย):** [tier_definition_data.xml](file:///c:/odoo-dev/odoo19/custom_addons/od19_hr_expense_thai/data/tier_definition_data.xml)
- **กลุ่ม CEO + การจ่ายคืน:** [hr_expense.py](file:///c:/odoo-dev/odoo19/custom_addons/od19_hr_expense_thai/models/hr_expense.py), [hr_expense_security.xml](file:///c:/odoo-dev/odoo19/custom_addons/od19_hr_expense_thai/security/hr_expense_security.xml)
- **เอกสารไทย/เบี้ยเลี้ยง/Mileage:** [hr_expense.py](file:///c:/odoo-dev/odoo19/custom_addons/od19_hr_expense_enhanced/models/hr_expense.py)
- **wizard ยื่นเบิกเร็ว + portal:** [od19_expense_quick_create.py](file:///c:/odoo-dev/odoo19/custom_addons/od19_hr_expense_portal/models/od19_expense_quick_create.py), [portal.py](file:///c:/odoo-dev/odoo19/custom_addons/od19_hr_expense_portal/controllers/portal.py)
- **Approval Center:** [od19_approval_source.py](file:///c:/odoo-dev/odoo19/custom_addons/od19_approval_center/models/od19_approval_source.py) — strategy `tier_validation` (L310)
- **สเปกที่เกี่ยวข้อง:** [2026-11-06-od19-hr-expense-reimbursement-design.md](file:///c:/odoo-dev/odoo19/docs/superpowers/specs/2026-11-06-od19-hr-expense-reimbursement-design.md), [2026-11-06-od19-hr-expense-approval-plan.md](file:///c:/odoo-dev/odoo19/docs/superpowers/plans/2026-11-06-od19-hr-expense-approval-plan.md)
