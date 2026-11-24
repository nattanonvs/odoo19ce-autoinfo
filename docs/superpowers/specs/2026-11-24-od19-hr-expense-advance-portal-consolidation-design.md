# เอกสารออกแบบ: รวมระบบ ใบเบิก / เงินทดรอง / ค่าใช้จ่ายพนักงาน เป็นโครงเดียว — Odoo 19 CE

- **วันที่:** 2026-11-24
- **รหัสงาน:** OD19-EXPENSE-CONSOLIDATION
- **สถานะ:** ออกแบบ (design) — ยังไม่เริ่มเขียนโค้ด
- **โมดูลที่แตะ:** `od19_hr_expense_portal`, `od19_hr_expense_claim` (จากสาขา), `od19_hr_expense_enhanced`, `od19_hr_expense_thai`, `od19_hr_advance`, `od19_approval_center`
- **ไม่แตะ:** Odoo core (`addons/`), `third_party/oca/`
- **เอกสารที่เกี่ยวข้อง / ที่ถูก supersede บางส่วน:**
  - [2026-11-20-od19-hr-expense-claim-batch-design.md](file:///c:/odoo-dev/odoo19/docs/superpowers/specs/2026-11-20-od19-hr-expense-claim-batch-design.md) — หัวใบ `od19.expense.claim` (K1–K8) — **เอกสารนี้ต่อยอดและแก้ K3 (แนบหลักฐาน)**
  - [2026-11-06-od19-hr-expense-reimbursement-design.md](file:///c:/odoo-dev/odoo19/docs/superpowers/specs/2026-11-06-od19-hr-expense-reimbursement-design.md)
  - คู่มือเดิม: `docs/od19_hr_expense_portal_user_guide_20261107.md`, `docs/od19_hr_expense_advance_user_guide_20261119.html`

---

## 0. คำตอบผู้ใช้ที่ล็อกทิศทาง (2026-11-24)

| # | คำถาม | คำตอบ | ผลต่อดีไซน์ |
|---|---|---|---|
| 1 | รวม 5 ชิ้นส่วนอย่างไร | **จัดการรวมกันให้สอดคล้อง** | ใช้ "หัวใบ" เป็นจุดเดียว, ไม่ทิ้งของเดิมที่ยังจำเป็น |
| 2 | ให้พนักงานขอ advance จาก portal ได้ไหม | **ใช่** | เพิ่มเส้นทาง advance ฝั่งพนักงาน (portal) |
| 3 | cash state กับ advance | **รวมเป็นแนวคิดเดียว** | ตัด `od19_cash_state` แยก + ยุบ `od19.hr.advance` เข้าแนวคิดเดียวกัน |
| 4 | การแนบหลักฐาน | **ไม่บังคับแนบ แต่ต้องมี analytic** | ถอดข้อบังคับแนบไฟล์ออกจาก `action_submit`; คงบังคับ `analytic_distribution` |
| 5 | ผลลัพธ์ | **ออกแบบ** | เอกสารนี้ (ยังไม่เขียนโค้ด) |
| 6 | เคสเงินสดย่อย (ฝ่ายบัญชีทำแทน) | **คงเมนู Employee Expenses ไว้ แต่ดัดแปลงให้ดีขึ้น** | เพิ่ม `claim_type=petty_cash` + `claim_source`; เมนู vendor ปรับเป็น *ศูนย์งานฝ่ายบัญชี* (§10.3) |

---

## 1. บทสรุปผู้บริหาร (Executive Summary)

ปัจจุบันระบบเบิกเงิน/เงินทดรอง/ค่าใช้จ่ายพนักงาน **กระจัดกระจายเป็น 6 ชิ้น** ที่ทำงานคาบเกี่ยวกัน:
พนักงานยื่นได้ 3 ทาง, จ่ายเงินพนักงาน 3 กลไก, ข้อมูลอนุมัติอยู่ 3 ที่, และมี "หัวใบ" (`od19.expense.claim`) ถูกสร้างไว้แล้วบนสาขาที่ยังไม่ merge

ดีไซน์นี้รวมทุกอย่างเป็น **โครงเดียว 2 แกน**:

1. **แกนเอกสาร = "ใบเบิก" ใบเดียว (`od19.expense.claim`)** เป็นทั้ง *จุดยื่น* และ *จุดอนุมัติ* ของทุกเรื่องเงิน-พนักงาน
   โดยมีฟิลด์ `claim_type` แยก **ขอเบิกคืน (reimbursement)** กับ **ขอเงินทดรองล่วงหน้า (advance)** — ไม่มีเอกสารคู่ขนานอีก
2. **แกนเงิน = "ยอดเงินทดรอง/เงินสดค้างมือพนักงาน" แนวคิดเดียว** — ยุบ `od19_cash_state` (ระดับบรรทัด) และ `od19.hr.advance` (เอกสารแยก) ให้เหลือ "วงเงินที่บริษัทจ่ายให้พนักงานถือไว้ → ถูกใช้ไป (เคลียร์ด้วยค่าใช้จ่าย) → คืนส่วนที่เหลือ" อยู่ที่หัวใบใบเดียว

หลักการที่ยึด (ตามคำตอบผู้ใช้ 5 ข้อ):
- **จุดเดียว**: ทุกการเบิกเงินผ่าน `od19.expense.claim` (ไม่มี 3 ช่องทางอีก)
- **บังคับ analytic ไม่บังคับแนบ**: ส่งอนุมัติต้องมี `analytic_distribution` ครบทุกรายการ แต่ **ไม่บังคับ** แนบไฟล์
- **cash/advance = แนวคิดเดียว**: lifecycle เดียวสำหรับเงินที่พนักงานถืออยู่
- **พนักงานทำได้จาก portal**: ทั้งขอเบิกคืนและขอเงินทดรอง
- **รองรับเงินสดย่อย**: ฝ่ายบัญชีสร้างใบแทนพนักงานได้ (`claim_source=on_behalf`) และมี *ศูนย์งานฝ่ายบัญชี* แยก (§10.3)

---

## 2. สภาพปัจจุบันและความซ้ำซ้อน (As-Is)

### 2.1 ชิ้นส่วนที่มีอยู่ (ยืนยันจากโค้ดจริง)

| # | ชิ้นส่วน | ชนิด | หน้าที่หลัก | ไฟล์หลัก |
|---|---|---|---|---|
| 1 | `hr.expense` (core CE) | Core | บรรทัดค่าใช้จ่าย + บัญชี; **v19 ตัด `hr.expense.sheet` ออก** เหลือรายการแบน | [hr_expense.py](file:///c:/odoo-dev/odoo19/addons/hr_expense/models/hr_expense.py) |
| 2 | `od19_hr_expense_enhanced` | Custom | เอกสารไทย/VAT/ใบรับรองแทนใบเสร็จ/เบี้ยเลี้ยง ม.42(3)/Mileage/สมุดรถ/**cash state**/WHT/XLSX/มอบหมายอนุมัติ | [hr_expense.py](file:///c:/odoo-dev/odoo19/custom_addons/od19_hr_expense_enhanced/models/hr_expense.py), [account_payment.py](file:///c:/odoo-dev/odoo19/custom_addons/od19_hr_expense_enhanced/models/account_payment.py) |
| 3 | `od19_hr_expense_thai` | Custom | วิธีจ่ายคืน + **จ่ายคืนจริงด้วย account.payment + reconcile** + **tier 3 ชั้นบน `hr.expense`** + กลุ่ม CEO | [hr_expense.py](file:///c:/odoo-dev/odoo19/custom_addons/od19_hr_expense_thai/models/hr_expense.py), [tier_definition_data.xml](file:///c:/odoo-dev/odoo19/custom_addons/od19_hr_expense_thai/data/tier_definition_data.xml) |
| 4 | `od19_hr_expense_portal` | Custom | Wizard ยื่นเร็ว `od19.expense.quick.create`, portal `/my/expenses`, Kanban | [portal.py](file:///c:/odoo-dev/odoo19/custom_addons/od19_hr_expense_portal/controllers/portal.py), [od19_expense_quick_create.py](file:///c:/odoo-dev/odoo19/custom_addons/od19_hr_expense_portal/models/od19_expense_quick_create.py) |
| 5 | `od19_hr_advance` | Custom | เอกสาร `od19.hr.advance` **แยกต่างหาก**: อนุมัติ 2 ชั้น, จ่ายจริง, เคลียร์+คืนเงิน | [hr_advance.py](file:///c:/odoo-dev/odoo19/custom_addons/od19_hr_advance/models/hr_advance.py) |
| 6 | `od19_hr_expense_claim` **(สาขา `feature/od19_hr_expense_claim` ยังไม่ merge)** | Custom | หัวใบ `od19.expense.claim` + tier 3 ชั้นที่หัวใบ + `od19_claim_id` บนบรรทัด | [od19_expense_claim.py](file:///c:/odoo-dev/odoo19/custom_addons/od19_hr_expense_claim/models/od19_expense_claim.py) |

### 2.2 ความซ้ำซ้อนที่ต้องแก้

| # | เรื่อง | สภาพ | ผลกระทบ |
|---|---|---|---|
| D1 | **3 ช่องทางยื่นเบิก** | (ก) portal `/my/expenses` สร้าง `hr.expense` เดี่ยว (ข) wizard `quick.create` สร้าง `hr.expense` เดี่ยว (ค) หัวใบ `od19.expense.claim` บนสาขา | พนักงาน/แอดมินสับสนว่าใช้ทางไหน; ข้อมูลอนุมัติไม่ตรงกัน |
| D2 | **2 หัวใบอนุมัติคู่ขนาน** | `hr.expense` มี tier 3 ชั้น (ของ `_thai`) **และ** `od19.expense.claim` มี tier 3 ชั้นอีกชุด | ใบเดียวกันอาจถูกอนุมัติ 2 ระดับ; ถอด tier ออกจาก `hr.expense` ต้องทำ (ตาม claim design) แต่ยังไม่ทำ |
| D3 | **3 กลไกจ่ายเงินพนักงาน** | (ก) `od19.hr.advance.action_pay` (ข) `_thai._od19_create_reimbursement_payment` ต่อบรรทัด (ค) core `action_pay` | กระทบยอด/เจ้าหนี้พนักงานหลายทาง; ตรวจสอบยาก |
| D4 | **cash state vs advance ซ้อนกัน** | `od19_cash_state` (not_received→received→used→returned) บนบรรทัด **และ** advance state (paid→cleared) | แนวคิด "เงินอยู่มือพนักงาน" ซ้ำ 2 ที่ (คำตอบ #3: รวม) |
| D5 | **ข้อมูลอนุมัติกระจาย** | tier definition อยู่ที่ `hr.expense` (3 ชั้น), `od19.hr.advance` (2 ชั้น), `od19.expense.claim` (3 ชั้น) | สายอนุมัติไม่สอดคล้อง; Approval Center ชี้ได้ทีละ model |
| D6 | **"Employee Expenses" (เมนู vendor)** | core `menu_hr_expense_account_employee_expenses` (parent `account.menu_finance_payables`) ชี้ `hr.expense` ทุกสถานะ รวม draft | **คงไว้** — มีประโยชน์กับงานฝ่ายบัญชี (โดยเฉพาะเงินสดย่อย/ทำใบแทน) แต่ **ดัดแปลงเป็น "ศูนย์งานฝ่ายบัญชี"** ที่ชี้ใบเบิก + กรองตามงานบัญชี (§10.3) |

### 2.3 ช่องว่างความครอบคลุมข้อมูล (Data Coverage)

| # | จุด | สภาพ | สรุปดีไซน์ |
|---|---|---|---|
| C1 | แนบหลักฐาน | portal/wizard เดิมแนบไม่ได้; หัวใบสาขา **บังคับ** แนบ ≥1 ไฟล์ | **ถอดบังคับแนบ** (คำตอบ #4) → เพิ่มช่องแนบแบบ optional ที่ portal |
| C2 | Analytic | portal/wizard เดิม **ไม่ตั้ง** analytic; หัวใบสาขาบังคับ | **คงบังคับ analytic** ทุกรายการทั้งหลังบ้านและ portal |
| C3 | Advance ฝั่งพนักงาน | ไม่มี route ของพนักงาน (มีแต่หลังบ้าน) | เพิ่ม `/my/advances` + ฟอร์มขอทดรอง (คำตอบ #2) |
| C4 | เลขที่/วันที่ใบกำกับภาษี รายบรรทัด | หัวใบสาขาไม่มี | เพิ่มฟิลด์อ้างอิงเอกสารรายบรรทัด (ดู §5.3) |
| C5 | กันรายการซ้ำ | อ่อน | เพิ่มกติกากันใบซ้ำ (พนักงาน+วันที่+ยอด) ระดับหัวใบ |
| C6 | Cash/Advance | 2 แนวคิด | ยุบเป็นแนวคิดเดียว (§7) |

---

## 3. หลักการออกแบบ (Design Principles)

1. **จุดเดียว (Single Entry Point)** — ทุกคำขอเงินของพนักงาน = `od19.expense.claim` ใบเดียว; `hr.expense` ทำหน้าที่เป็น *บรรทัด* เท่านั้น ไม่ใช่เอกสารที่ยื่นได้เอง
2. **หัวใบคือด่านอนุมัติ** — อนุมัติ 3 ชั้นทำที่หัวใบครั้งเดียว (ตาม claim design); บรรทัดไม่ถูกอนุมัติซ้ำ
3. **ภาษี/บัญชีอยู่ที่บรรทัด** — หัวใบไม่คำนวณ VAT/WHT เอง (คงความถูกต้องของ GL)
4. **บังคับ analytic ไม่บังคับแนบ** — ส่งอนุมัติต้องมี `analytic_distribution` ครบ; ไฟล์แนบเป็น optional
5. **cash/advance = แนวคิดเดียว** — "วงเงินที่พนักงานถืออยู่" ติดตามที่หัวใบใบเดียว
6. **ไม่แตะ core / ไม่แตะ `third_party`** — ปรับผ่าน custom addons เท่านั้น
7. **ย้อนกลับได้ (reversible)** — ของเดิม (advance model, `od19_cash_state`) ไม่ลบทันทีในเฟสแรก ให้ deprecate แล้ว map ก่อน

---

## 4. สถาปัตยกรรมเป้าหมาย (To-Be)

```
┌───────────────────────────────────────────────────────────────┐
│  ชั้น UX                                                        │
│  od19_hr_expense_portal : portal /my/expenses + /my/advances    │
│                            + wizard ยื่นเร็ว (สร้างหัวใบ+บรรทัด)  │
└───────────────────────────────┬───────────────────────────────┘
                                │
┌───────────────────────────────┴───────────────────────────────┐
│  od19_hr_expense_claim  ★ จุดเดียว (หัวใบ = เอกสาร + ด่านอนุมัติ)│
│   • od19.expense.claim (reimbursement | advance)               │
│   • tier 3 ชั้นที่หัวใบ (ย้าย/รวมจาก _thai และ _advance)        │
│   • ฟิลด์เชื่อม: od19_claim_id บน hr.expense                    │
│   • กลไกจ่าย/เคลียร์/คืนเงิน (รวมจาก _thai + _advance)          │
└───────────────────────────────┬───────────────────────────────┘
                                │ ต่อยอด (ไม่แก้โครง)
┌───────────────────────────────┴───────────────────────────────┐
│  od19_hr_expense_enhanced : เอกสารไทย/VAT/ใบรับรอง/เบี้ยเลี้ยง/ │
│                             Mileage/สมุดรถ/WHT (ต่อบรรทัด)      │
│  od19_approval_center     : มุมมองผู้อนุมัติรวมศูนย์ (source=claim)│
│  hr.expense (core CE)     : บรรทัด + บัญชี (ไม่แก้)              │
└───────────────────────────────────────────────────────────────┘
```

### 4.1 ที่ตั้งความรับผิดชอบหลังรวม

| เรื่อง | ที่อยู่ใหม่ | เดิม |
|---|---|---|
| หัวใบ + สายอนุมัติ | `od19_hr_expense_claim` | กระจายที่ `_thai` (บน hr.expense) + `_advance` |
| ยื่นเบิก (หลังบ้าน/portal) | `od19_hr_expense_claim` + `_portal` | `_portal` (hr.expense เดี่ยว) |
| ขอเงินทดรอง | `od19.expense.claim` (`claim_type=advance`) | `od19.hr.advance` (model แยก) |
| จ่ายคืนพนักงาน | กลไกใน claim (รวมจาก `_thai` + `_advance`) | 2 ที่ |
| Cash/Advance lifecycle | ฟิลด์ที่หัวใบ (§7) | `od19_cash_state` + advance state |
| ภาษี/เอกสารไทย | `od19_hr_expense_enhanced` (ต่อบรรทัด) | คงเดิม |

### 4.2 Dependency ของ `od19_hr_expense_claim` (ปรับจากเดิม)

```
hr_expense, hr_expense_tier_validation, base_tier_validation,
base_tier_validation_forward, od19_hr_expense_thai,
od19_hr_expense_enhanced, od19_accounting_features,
od19_hr_advance (ช่วงเปลี่ยนผ่าน — ดู §13), od19_approval_center, mail
```

---

## 5. โมเดลข้อมูลเป้าหมาย

### 5.1 หัวใบ `od19.expense.claim` (ขยายจากสาขา)

ฟิลด์เดิม (คงไว้): `name`, `employee_id`, `department_id`, `company_id`, `currency_id`, `date`, `submit_date`, `approval_date`, `transfer_date`, `line_ids`, `total_amount`, `note`, `state`

**เพิ่มฟิลด์ใหม่:**

| ฟิลด์ | ชนิด | ใช้ทำอะไร |
|---|---|---|
| `claim_type` | Selection `reimbursement` / `advance` / `petty_cash` | แยก ขอเบิกคืน / ขอเงินทดรอง / เงินสดย่อย (คำตอบ #1, #2 + เคสฝ่ายบัญชี #6) |
| `claim_source` | Selection `self_service` / `on_behalf` | ใครสร้าง: พนักงานยื่นเอง vs ฝ่ายบัญชีทำแทน (`petty_cash` บังคับ `on_behalf`) |
| `cash_fund_id` | Many2one `account.journal` (type `cash`) | กองทุนเงินสดย่อย (เมื่อ `claim_type=petty_cash`) |
| `submitted_for_id` | Many2one `hr.employee` | พนักงานที่เบิกแทน (เมื่อ `claim_source=on_behalf`) — ค่าเริ่ม = `employee_id` |
| `purpose` | Char | วัตถุประสงค์ (จำเป็นเมื่อ `advance`) |
| `advance_account_id` | Many2one `account.account` | บัญชีลูกหนี้พนักงาน/เงินทดรอง (จำเป็นเมื่อ `advance`) — ย้ายจาก `od19.hr.advance` |
| `payment_id` | Many2one `account.payment` | รายการจ่ายจริงให้พนักงาน |
| `journal_id` | Many2one `account.journal` | สมุดที่ใช้จ่าย |
| `payment_method` | Selection `cash/bank_transfer/cheque` | วิธีจ่ายคืน (ย้ายจาก `_thai`) |
| `reimbursement_date` | Date | วันที่จ่ายคืนจริง |
| `cash_state` | Selection (ดู §7) | สถานะเงินค้างมือพนักงาน (รวมแนวคิด) |
| `cleared_amount` / `remaining_amount` | Monetary (compute+store) | ยอดใช้ไป/ยอดคงเหลือ (ย้ายจาก advance) |
| `clear_move_id` / `clear_date` | Many2one/Date | รายการเคลียร์ยอด |
| `clearing_claim_ids` | One2many `od19.expense.claim` (`advance_id`) | ใบเบิกคืนที่นำมาเคลียร์กับใบทดรองนี้ |
| `advance_id` | Many2one `od19.expense.claim` | (ฝั่งใบเบิกคืน) ผูกกลับไปยังใบทดรองที่เคลียร์ |
| `attachment_ids` | Many2many `ir.attachment` (ผ่าน mail.thread) | ไฟล์แนบ **optional** |

> **หมายเหตุ `payment_mode`:** คงไว้ (`own_account`/`company_account`) ตาม claim design; เพิ่มความสัมพันธ์กับ `claim_type` — `advance` บังคับ `company_account` (บริษัทจ่ายก่อน)

### 5.2 บรรทัด `hr.expense` (เพิ่มจากสาขา)

| ฟิลด์ | ชนิด | หมายเหตุ |
|---|---|---|
| `od19_claim_id` | Many2one `od19.expense.claim` (`ondelete=cascade`, index) | หัวใบ (มีแล้วจากสาขา) |
| `od19_hr_advance_id` | Many2one `od19.expense.claim` | **เปลี่ยนปลายทาง** จาก `od19.hr.advance` → claim (ดู §7.3) |

### 5.3 ฟิลด์อ้างอิงเอกสารรายบรรทัด (แก้ช่องว่าง C4)

เพิ่มใน `od19_hr_expense_enhanced` (ต่อบรรทัด):

| ฟิลด์ | ชนิด | หมายเหตุ |
|---|---|---|
| `od19_supplier_doc_number` | Char | เลขที่ใบกำกับ/ใบเสร็จของผู้ขาย |
| `od19_supplier_doc_date` | Date | วันที่เอกสาร |
| `od19_supplier_tax_id` | Char | เลขผู้เสียภาษีผู้ขาย (เมื่อ VAT หักได้) |

> ฟิลด์เหล่านี้ตอบคำถาม "ความครอบคลุมข้อมูลเพียงพอไหม" — จำเป็นสำหรับภาษีซื้อ/ตรวจสอบย้อนหลัง แต่ **ไม่บังคับ** ตอนส่ง (ตามคำตอบ #4)

---

## 6. สถานะและเส้นทางเอกสาร (State Machines)

### 6.1 เส้นทาง A — ขอเบิกคืน (reimbursement)

```
draft ─submit─▶ submitted ─(tier 3 ชั้นที่หัวใบ)─▶ approved ─พนักงานยืนยัน─▶ sent
   │                                               │
   │                                            บัญชี post
   ▼                                               ▼
refused ◀─refuse── (submitted|approved)          posted ─จ่ายคืน─▶ paid ─▶ closed
```

- บรรทัด (`hr.expense.approval_state`) ถูก propagate: `submitted` → `approved` เมื่อหัวใบอนุมัติครบ (ตาม claim design §7)
- บัญชีกด **Post Journal Entries** ที่หัวใบ → โพสต์บรรทัด (core เดิม)

### 6.2 เส้นทาง B — ขอเงินทดรอง (advance)

```
draft ─submit─▶ submitted ─(tier ที่หัวใบ)─▶ approved ─จ่ายเงิน─▶ paid
                                                                  │
                              (พนักงานยื่นใบเบิกคืนมาเคลียร์)      │
                              ─────────────────────────────▶ partially_cleared
                                                                  │
                                                     เคลียร์ครบ ─▶ cleared
                                          คืนส่วนที่เหลือ ─▶ returned / settled
```

- `advance` ไม่มี `line_ids` ตอนสร้าง; บรรทัดจะถูกเพิ่ม (หรือผูกเข้ามา) ตอน **เคลียร์** ผ่านใบเบิกคืนที่อ้าง `advance_id`
- `remaining_amount = amount − cleared_amount`; `cash_state` เดินตาม §7

### 6.3 สายอนุมัติ (tier) — รวมให้สอดคล้อง (แก้ D5)

ใช้ tier definition ชุดเดียวบน `od19.expense.claim` (3 ชั้น เหมือน claim design):

| ลำดับ | ชั้น | กลุ่ม | sequence |
|---|---|---|---|
| 1 | หัวหน้าแผนก | `hr_expense.group_hr_expense_manager` | 30 |
| 2 | ฝ่ายบัญชี | `account.group_account_manager` | 20 |
| 3 | CEO | `od19_hr_expense_thai.group_od19_expense_ceo_approver` | 10 |

**ปรับจากเดิมเพื่อให้ "สอดคล้อง" (คำตอบ #1):**
- `tier.definition` 3 ชั้นของ `_thai` (บน `hr.expense`) → **ย้าย/ลบ** (ตาม claim design)
- `tier.definition` 2 ชั้นของ `od19_hr_advance` → **รวมเป็นชุดเดียว**; ถ้าต้องการให้ advance ใช้เกณฑ์ต่าง → ใช้ `definition_domain` บนหัวใบ ตาม `claim_type`
  - ตัวอย่าง: advance ≤ วงเงินที่กำหนด → ใช้ 2 ชั้น (หัวหน้าแผนก+บัญชี); advance เกินวงเงิน → ครบ 3 ชั้น (เพิ่ม CEO)
- Approval Center source เปลี่ยนเป็น `od19.expense.claim` (strategy `tier_validation`) — ตาม claim design K8

> ทั้งนี้ **ไม่แตะ** `third_party/oca/`; ทำได้โดยลบ/เพิ่ม `tier.definition` ใน data ของโมดูลเราเอง

### 6.4 เส้นทาง C — เงินสดย่อย (petty_cash, ฝ่ายบัญชีทำแทน)

```
draft ─submit─▶ submitted ─(อนุมัติเบา/auto)─▶ approved ─จ่ายจากกองทุน─▶ paid
                                                                        │
                                    ใช้หมด/ปิด (cash_state=settled) ────▶ closed
```

- `claim_type=petty_cash`, `claim_source=on_behalf` — **ฝ่ายบัญชีสร้างแทนพนักงาน** (ผู้ทำเบิกเงินสดย่อย)
- ใช้ `cash_fund_id` (สมุดเงินสดย่อย) และ `advance_account_id` ชุดเดียวกับ advance
- **อนุมัติเบา**: ใช้ `definition_domain` ให้ใช้แค่ชั้นหัวหน้าแผนก + บัญชี (ข้าม CEO) เว้นแต่ยอดเกินวงเงิน
- เงินเดินตามแนวคิด cash state เดียวกับ advance (§7) → **reinforce คำตอบ #3**

---

## 7. การรวม cash state กับ advance เป็นแนวคิดเดียว (คำตอบ #3)

### 7.1 แนวคิดเดียว: "วงเงินที่พนักงานถืออยู่" (Employee-held funds)

แนวคิดเดียวที่ครอบทั้งสามกรณี (advance · petty cash · company-paid cash):

```
ยังไม่จ่าย ─▶ จ่ายให้พนักงานแล้ว ─▶ ถูกใช้ไป (เคลียร์ด้วยค่าใช้จ่าย) ─▶ คืนส่วนที่เหลือ ─▶ ปิด
```

| สถานะ (รวม) | ความหมาย | เดิมมาจาก |
|---|---|---|
| `not_issued` | ยังไม่จ่ายเงินให้พนักงาน | advance: `approved`; cash state: `not_received` |
| `issued` | จ่ายให้พนักงานแล้ว (ถือเงินอยู่) | advance: `paid`; cash state: `received`; **petty_cash: จ่ายจากกองทุน** |
| `partially_used` | ใช้ไปบางส่วน (เคลียร์บางส่วน) | advance: (ใหม่); cash state: `used` |
| `settled` | เคลียร์/คืน/ปิดครบแล้ว | advance: `cleared`; cash state: `returned`; **petty_cash: ปิดกอง** |

> **เงินสดย่อย = กรณีที่ 3 ของแนวคิดนี้** (ไม่ใช่ระบบใหม่): "บริษัทจ่ายเงินให้พนักงานถือไว้ แล้วใช้/ปิด" เหมือนทดรอง เพียงแต่ *ฝ่ายบัญชีเป็นคนสร้างใบ* — ยิ่งตอกย้ำว่าควรมีแนวคิดเงินเดียว (§7)

### 7.2 ฟิลด์ที่ทำให้เป็นแนวคิดเดียว

- **ที่หัวใบ `od19.expense.claim`:** `cash_state` (ตามตาราง §7.1) + `cleared_amount` + `remaining_amount`
  - `claim_type=advance` → เกิด cash_state ตั้งแต่ตอนจ่าย (`issued`)
  - `claim_type=petty_cash` → เกิด cash_state ตอนจ่ายจากกองทุน (`issued`) → ใช้/ปิด
  - `claim_type=reimbursement` → **ไม่ใช้** cash_state (พนักงานออกเงินเอง ไม่มีเงินค้างมือ) เว้นแต่ตั้งค่าบริษัทให้ "จ่ายเงินสดก่อน" (legacy company_account)

### 7.3 สิ่งที่ถูกยุบ/เลิกใช้

| ของเดิม | การจัดการ | เหตุผล |
|---|---|---|
| `od19.hr.advance` (model + views + menu + tier) | **deprecate** → ย้าย logic (`action_pay`, `cleared_amount`, `remaining_amount`, wizard เคลียร์) เข้า `od19.expense.claim`; คง model ไว้ช่วงเปลี่ยนผ่านเพื่อ migrate ข้อมูล แล้วเลิกใช้ | คำตอบ #3 "รวม" |
| `od19_cash_state` (บน `hr.expense`) | **เลิกใช้เป็นฟิลด์แยก**; ข้อมูลย้ายไป `od19.expense.claim.cash_state` | คำตอบ #3 |
| `od19.expense.return.cash` (wizard คืนเงิน) | **ปรับให้ผูกกับหัวใบ** (ไม่ใช่ `hr.expense`) | ให้ตรงแนวคิดเดียว |
| `od19.hr.advance.clear` (wizard) | **ปรับให้เป็น "เคลียร์ใบทดรองด้วยใบเบิกคืน"** ที่หัวใบ | ให้ตรงแนวคิดเดียว |

### 7.4 เส้นทางเงิน (บัญชี) ของแนวคิดรวม

| จังหวะ | รายการบัญชี |
|---|---|
| จ่ายทดรอง (advance) | เดบิต `advance_account_id` (ลูกหนี้พนักงาน) / เครดิต เงินสด-ธนาคาร |
| เคลียร์ด้วยค่าใช้จ่าย | เดบิต ค่าใช้จ่าย (ต่อบรรทัด core) / เครดิต `advance_account_id` |
| คืนเงินส่วนที่เหลือ | เดบิต เงินสด-ธนาคาร / เครดิต `advance_account_id` (reconcile ปิดยอด) |
| เบิกคืน (reimbursement) | เดบิต ค่าใช้จ่าย / เครดิต เจ้าหนี้พนักงาน แล้วจ่ายคืนด้วย `account.payment` + reconcile (กลไก `_thai` เดิม) |

> ใช้กลไก `od19_hr_expense_enhanced`/`od19_hr_expense_thai` ที่มีอยู่ (WHT, reconcile) ต่อ ไม่สร้างใหม่

---

## 8. Portal (คำตอบ #2)

### 8.1 Routes เป้าหมาย

| Route | หน้าที่ | สถานะ |
|---|---|---|
| `/my/expenses` | รายการใบเบิกคืนของพนักงาน (kanban/list) | ปรับจากเดิม (เดิมแสดง `hr.expense` เดี่ยว) |
| `/my/expenses/new` | ยื่นใบเบิกคืน (หลายบรรทัด + analytic + แนบไฟล์ optional) | ปรับ |
| `/my/expenses/<id>` | รายละเอียด + timeline อนุมัติ 3 ชั้น | ปรับ |
| `/my/expenses/<id>/submit` | ส่งอนุมัติ (ผ่าน `claim.action_submit`) | ปรับ |
| **`/my/advances`** | **รายการใบขอทดรองของพนักงาน** | **ใหม่** |
| **`/my/advances/new`** | **ขอเงินทดรอง (จำนวน, วัตถุประสงค์, บัญชีทดรอง)** | **ใหม่** |
| **`/my/advances/<id>`** | รายละเอียด + สถานะเงินคงเหลือ/เคลียร์ | **ใหม่** |
| `/my/expenses/help` | คู่มือในพอร์ทัล | คง |
| `/my/expenses/distance` | คำนวณระยะทาง (mileage) | คง |

### 8.2 หลักความปลอดภัย (คงเดิม)

- ทุก query ถูกกรองด้วย domain เจ้าของ: `[('employee_id.user_id', '=', request.env.user.id)]`
- `employee_id` ถูกบังคับจาก `request.env.user.employee_id` เสมอ (ยื่นแทนผู้อื่นไม่ได้)

### 8.3 ฟอร์มยื่นเบิก (portal) — เพิ่มความครอบคลุมข้อมูล (แก้ C1, C2)

- **Analytic บังคับ**: เลือก analytic account ต่อบรรทัด (ตัวเลือกมาจาก `account.analytic.account` ที่ผู้ใช้เข้าถึงได้)
- **แนบไฟล์ optional**: ช่อง `attachment_ids` (ไม่บังคับ) — อัปโหลดรูปจากมือถือได้
- **หลายบรรทัดในใบเดียว**: เพิ่ม/ลบบรรทัดได้ในหน้าเดียว
- **ฟิลด์อ้างอิงเอกสาร** (optional): เลขที่/วันที่เอกสารผู้ขาย (§5.3)
- เลือก `claim_type` ได้ (ใบเบิกคืน / ขอทดรอง) หรือแยกแท็บ

### 8.4 Wizard ยื่นเร็ว (ปรับ)

`od19.expense.quick.create` เปลี่ยน `action_create_expense` ให้ **สร้างหัวใบ + บรรทัด** (แทน `hr.expense` เดี่ยว) และเพิ่มฟิลด์ analytic — ตาม claim design เฟส 2

---

## 9. การบังคับ analytic / ไม่บังคับแนบ (คำตอบ #4)

แก้ `od19.expense.claim.action_submit()` (จากสาขา):

| เงื่อนไข | เดิม (สาขา) | ใหม่ |
|---|---|---|
| ต้องมีอย่างน้อย 1 บรรทัด | ✔ บังคับ | ✔ คงไว้ |
| `analytic_distribution` ครบทุกรายการ | ✔ บังคับ | ✔ **คงไว้ (บังคับ)** |
| แนบไฟล์ ≥1 ไฟล์ | ✔ **บังคับ** | ✖ **ถอดออก (ไม่บังคับ)** |

**ผลข้างเคียงที่ต้องจัดการ:**
- บังคับ analytic ทั้งหลังบ้าน (ฟอร์มหัวใบ) และ portal (ต้องส่ง analytic จากฟอร์ม) และ wizard
- สำหรับ `claim_type=advance`: ไม่มีบรรทัดตอนสร้าง → การบังคับ analytic **ไม่ใช้** กับ advance ตอน submit (บังคับ analytic ตอน "เคลียร์" ที่มีบรรทัดจริง)

---

## 10. เมนูและสิทธิ์ (แก้ D6)

### 10.1 เมนูเป้าหมาย

| เมนู | ที่ตั้ง | ชี้ไป | หมายเหตุ |
|---|---|---|---|
| Expenses (app root) | `hr_expense.menu_hr_expense_root` | `action_od19_expense_claim_my` | ตาม claim design (แอปรวมเปิดที่ใบเบิก) |
| ใบเบิกของฉัน | ใต้ root | `action_od19_expense_claim_my` | seq 2 |
| ใบเบิกทั้งหมด | ใต้ root | `action_od19_expense_claim_all` | seq 3, groups manager+account |
| **ใบขอเงินทดรอง** | ใต้ root | action กรอง `claim_type=advance` | (รวมจาก `menu_od19_hr_advance`) |
| **เงินสดย่อย (ฝ่ายบัญชี)** | ใต้ root (groups บัญชี) | action กรอง `claim_type=petty_cash` | ทางลัดไปศูนย์งานฝ่ายบัญชี |
| **Employee Expenses** (vendor) | `account.menu_finance_payables` | **`action_od19_expense_claim_accounting`** | **ดัดแปลง D6**: เป็น *ศูนย์งานฝ่ายบัญชี* ตาม §10.3 |
| ~~`menu_hr_expense_my_expenses`~~ | core | — | `active=False` (ตาม claim design) |
| ~~`menu_od19_hr_advance`~~ | `_advance` | — | `active=False` (ยุบเข้า claim) |

### 10.2 สิทธิ์ (ir.rule / groups)

| กลุ่ม | เห็นอะไร |
|---|---|
| พนักงาน | ใบเบิก/คำขอทดรองของตัวเอง (`employee_id.user_id = uid`) |
| ผู้อนุมัติ 3 ชั้น | ใบที่ค้างในชั้นของตน (ผ่าน `tier.review.reviewer_ids`) |
| ฝ่ายบัญชี/ผู้จัดการ | ทั้งหมด (รวมเมนู Employee Expenses) |

### 10.3 ศูนย์งานฝ่ายบัญชี — "Employee Expenses" (ดัดแปลง ไม่ทิ้ง)

**แนวคิด:** เดิมเมนูนี้คือ *รายการ `hr.expense` ดิบ* (มีประโยชน์ เพราะฝ่ายบัญชีต้องทำงานกับทุกสถานะ) — **คงไว้แต่ยกระดับเป็น workspace** ที่ทำงานครบจบในที่เดียว

**Action:** `action_od19_expense_claim_accounting` (model claim) — default filter เฉพาะงานที่ต้องลงบัญชี/จ่าย

**ตัวกรองพร้อมใช้ (search filters):**

| ตัวกรอง | เงื่อนไข |
|---|---|
| รออนุมัติฝ่ายบัญชี | tier ชั้นบัญชี = current |
| อนุมัติครบ รอลงบัญชี | `state = approved` |
| รอจ่ายคืน | `state = posted` และ `claim_type = reimbursement` |
| เงินสดย่อย | `claim_type = petty_cash` |
| ฝ่ายบัญชีทำแทน | `claim_source = on_behalf` |
| รอเคลียร์ทดรอง/เงินสดย่อย | `cash_state in (issued, partially_used)` |

**คอลัมน์:** วันที่ · เลขที่ · พนักงาน · ประเภท (badge) · แหล่งที่มา · ยอด · สถานะอนุมัติ · สถานะจ่าย · คงเหลือ

**ปุ่มหลัก (header + mass action):**
- **สร้างใบเบิกแทนพนักงาน** (`claim_source = on_behalf`, บังคับเลือกพนักงาน)
- **สร้างใบเงินสดย่อย** (ลัด: `claim_type = petty_cash` + กองทุน `cash_fund_id`)
- **บันทึกบัญชี (Post)** หลายใบพร้อมกัน
- **จ่ายคืน (Register Payment)** หลายใบพร้อมกัน
- ส่งออก **XLSX**

> **เหตุผลที่คงเมนูนี้:** เคสเงินสดย่อยที่ *ฝ่ายบัญชีเป็นผู้ทำเรื่องเบิกให้* ไม่ได้มาจาก self-service ของพนักงาน — จึงต้องมี "บ้าน" ของงานฝ่ายบัญชีแยกจากเส้นทางพนักงาน

---

## 11. Approval Center

- source `od19.approval.source` ปรับให้ **มีรายการเดียวชี้ `od19.expense.claim`** (strategy `tier_validation`) แทนที่แยก `hr.expense` + `od19.hr.advance`
- ใช้กลไก `_od19_classify_tier_for_approver` ที่มีอยู่ (อ่าน `tier.review`) — ไม่ต้องแก้กลไก
- ผล: ผู้อนุมัติเห็นทั้งใบเบิกคืนและใบขอทดรองในกล่องเดียว

---

## 12. บัญชี/กระทบยอด (สรุปใช้ของเดิม)

| กรณี | กลไก | ที่มีอยู่ |
|---|---|---|
| พนักงานออกเงินเอง (เบิกคืน) | `account.payment` + reconcile เจ้าหนี้พนักงาน | `od19_hr_expense_thai` |
| บริษัทจ่ายตรง | สร้าง entry ตอน post | core |
| **เงินทดรอง** | จ่ายล่วงหน้า → เดบิต `advance_account_id`; เคลียร์/คืนทีหลัง | **ย้ายจาก `od19_hr_advance`** |
| WHT | `od19_wht_*` บน `account.payment` | `od19_hr_expense_enhanced` |
| VAT / ใบรับรองแทนใบเสร็จ / เบี้ยเลี้ยง / Mileage | ต่อบรรทัด | `od19_hr_expense_enhanced` |

---

## 13. การย้ายข้อมูลและช่วงเปลี่ยนผ่าน (Migration)

- **ข้อมูลจริงปัจจุบัน:** `puat` ไม่มี `hr.expense`/`tier.review` ค้าง (ตาม claim design K7); `pdev` มี `hr.expense` (ข้อมูล dev)
- **แผน migrate:**
  1. วันที่ claim module ติดตั้ง → สร้างฟิลด์ทั้งหมด + ย้าย `tier.definition`
  2. `od19.hr.advance` ที่มีอยู่ → สร้าง `od19.expense.claim` ให้ (`claim_type=advance`) แล้ว map `od19_hr_advance_id` บนบรรทัด → `advance_id`
  3. `od19_cash_state` เดิม → map เป็น `claim.cash_state`
  4. deprecate (ซ่อนเมนู/`active=False`) โมเดลเดิม — **ไม่ลบทันที** เพื่อความปลอดภัย
- **ช่วงเปลี่ยนผ่าน:** `od19_hr_advance` ยังอยู่ใน dependency เพื่อ migrate; เลิกใช้เมื่อข้อมูลย้ายครบ (เฟสถัดไป)

---

## 14. แผนส่งมอบ (Phases)

| เฟส | เนื้อหา | ผลลัพธ์ที่ตรวจได้ |
|---|---|---|
| **P1 — หัวใจรวม** | merge `od19_hr_expense_claim` เข้า main; ย้าย tier 3 ชั้นมาหัวใบ; ถอด tier บน `hr.expense`; ถอดบังคับแนบ + คงบังคับ analytic | ยื่น 1 ใบ หลายบรรทัด → อนุมัติที่หัวใบครั้งเดียว; ส่งได้แม้ไม่แนบไฟล์ แต่ต้องมี analytic |
| **P2 — ยุบ advance + cash (+ petty cash)** | เพิ่ม `claim_type=advance`/`petty_cash` + `claim_source` + `cash_state` + `cleared/remaining` + `cash_fund_id`; ย้าย logic จาก `od19.hr.advance` + wizard เคลียร์/คืนเงิน; deprecate model เดิม | ขอทดรอง/เงินสดย่อย-จ่าย-เคลียร์-คืน อยู่ที่หัวใบใบเดียว |
| **P3 — Portal ครบ** | ปรับ `/my/expenses` เป็นใบเบิก; เพิ่ม `/my/advances`; analytic picker + แนบไฟล์ optional | พนักงานยื่น/ติดตามทั้ง 2 ประเภทจากมือถือ |
| **P4 — เมนู/สิทธิ์/Approval Center** | ทำ *ศูนย์งานฝ่ายบัญชี Employee Expenses* (§10.3) + ปุ่มทำใบแทน/เงินสดย่อย; ซ่อนเมนูเดิม; source Approval Center → claim; เพิ่มฟิลด์อ้างอิงเอกสาร | ฝ่ายบัญชีมี workspace ครบ + ผู้อนุมัติเห็นใบเบิกที่เดียว |
| **P5 — hardening** | รายงาน XLSX ระดับใบ, i18n, คู่มือ, กันรายการซ้ำ (C5) | ตามความจำเป็น |

> ทุกเฟส: เขียนเทสต์ก่อน (TDD) และผ่าน test gate ก่อนไปเฟสถัดไป (ตาม AGENTS.md)

---

## 15. เกณฑ์ยอมรับ (Acceptance Criteria)

- [ ] ทุกคำขอเงินของพนักงานผ่าน `od19.expense.claim` จุดเดียว (ทั้งเบิกคืนและทดรอง)
- [ ] อนุมัติ 3 ชั้นทำ **ที่หัวใบครั้งเดียว**; จำนวนครั้ง = 3/ใบ (ไม่ขึ้นกับจำนวนบรรทัด)
- [ ] `action_submit` **บังคับ analytic** ทุกรายการ แต่ **ไม่บังคับแนบไฟล์**
- [ ] พนักงานขอ/ติดตาม **เงินทดรอง** ได้จาก portal (`/my/advances`)
- [ ] cash state + advance เป็นแนวคิดเดียว (`cash_state` ที่หัวใบ); ไม่มี `od19_cash_state` แยกบนบรรทัดอีก
- [ ] เมนู "Employee Expenses" (vendor) เป็น *ศูนย์งานฝ่ายบัญชี* ที่ชี้ใบเบิก (ไม่ใช่ `hr.expense` ดิบ); ไม่มีเมนูซ้ำ
- [ ] ฝ่ายบัญชี **สร้างใบแทนพนักงาน** (`claim_source=on_behalf`) + **เงินสดย่อย** (`claim_type=petty_cash`) ได้จากเมนูนี้
- [ ] เงินสดย่อยใช้ cash state แนวคิดเดียวกับทดรอง (ไม่มี "กลไกเงิน" ที่ 4)
- [ ] ภาษี/บัญชีไทย (VAT/WHT/ใบรับรอง/เบี้ยเลี้ยง/Mileage) ทำงานครบต่อบรรทัด
- [ ] ไม่แตะ Odoo core และ `third_party/oca/`
- [ ] เทสต์ผ่านทุกเฟส

---

## 16. ประเด็นที่ต้องยืนยัน / ตัดสินใจเพิ่ม (Open Questions)

| # | ประเด็น | ตัวเลือก |
|---|---|---|
| Q1 | `claim_type` แยกเป็น 2 เอกสาร หรือเอกสารเดียวมี type | **เสนอ: เอกสารเดียว + `claim_type`** (สอดคล้องคำตอบ "รวม") |
| Q2 | ลบ `od19.hr.advance` ทันที หรือ deprecate | **เสนอ: deprecate + migrate ก่อน** (ปลอดภัย) |
| Q3 | tier ของ advance: 2 ชั้น หรือ 3 ชั้นเหมือนใบเบิก | **เสนอ: ชุดเดียว 3 ชั้น + `definition_domain` ตามยอด** |
| Q4 | portal แยกแท็บ (เบิกคืน/ทดรอง) หรือคนละ route | **เสนอ: คนละ route (`/my/expenses`, `/my/advances`) + ลิงก์ถึงกัน** |
| Q5 | เกณฑ์ "ใบซ้ำ" (C5) ใช้พนักงาน+วันที่+ยอด หรือไม่ | รอตัดสิน |
| Q6 | เงินสดย่อย: เป็น `claim_type` แยก หรือใช้ advance + flag | **เสนอ: `claim_type=petty_cash` แยก** (ชัดเรื่องกองทุน/บัญชี) |
| Q7 | อนุมัติเงินสดย่อย: 2 ชั้น (ข้าม CEO) เป็นค่าเริ่ม หรือ 3 ชั้น | **เสนอ: 2 ชั้น (หัวหน้าแผนก+บัญชี) เว้นแต่ยอดเกินวงเงิน** |

---

## 17. ภาคผนวก: จุดอ้างอิงโค้ด

- **Core (อ่านเท่านั้น):** [hr_expense.py](file:///c:/odoo-dev/odoo19/addons/hr_expense/models/hr_expense.py) · [hr_expense_views.xml](file:///c:/odoo-dev/odoo19/addons/hr_expense/views/hr_expense_views.xml) (เมนู `menu_hr_expense_account_employee_expenses`)
- **หัวใบ (สาขา):** [od19_expense_claim.py](file:///c:/odoo-dev/odoo19/custom_addons/od19_hr_expense_claim/models/od19_expense_claim.py) · [tier_definition_data.xml](file:///c:/odoo-dev/odoo19/custom_addons/od19_hr_expense_claim/data/tier_definition_data.xml) · [views](file:///c:/odoo-dev/odoo19/custom_addons/od19_hr_expense_claim/views/od19_expense_claim_views.xml)
- **Enhanced:** [hr_expense.py](file:///c:/odoo-dev/odoo19/custom_addons/od19_hr_expense_enhanced/models/hr_expense.py) · [account_payment.py](file:///c:/odoo-dev/odoo19/custom_addons/od19_hr_expense_enhanced/models/account_payment.py) · [expense_return_cash.py](file:///c:/odoo-dev/odoo19/custom_addons/od19_hr_expense_enhanced/wizards/expense_return_cash.py)
- **Thai:** [hr_expense.py](file:///c:/odoo-dev/odoo19/custom_addons/od19_hr_expense_thai/models/hr_expense.py) · [tier_definition_data.xml](file:///c:/odoo-dev/odoo19/custom_addons/od19_hr_expense_thai/data/tier_definition_data.xml)
- **Portal:** [portal.py](file:///c:/odoo-dev/odoo19/custom_addons/od19_hr_expense_portal/controllers/portal.py) · [od19_expense_quick_create.py](file:///c:/odoo-dev/odoo19/custom_addons/od19_hr_expense_portal/models/od19_expense_quick_create.py)
- **Advance (จะยุบ):** [hr_advance.py](file:///c:/odoo-dev/odoo19/custom_addons/od19_hr_advance/models/hr_advance.py) · [hr_expense.py](file:///c:/odoo-dev/odoo19/custom_addons/od19_hr_advance/models/hr_expense.py) · [views](file:///c:/odoo-dev/odoo19/custom_addons/od19_hr_advance/views/hr_advance_views.xml)
- **Approval Center:** [od19_approval_source.py](file:///c:/odoo-dev/odoo19/custom_addons/od19_approval_center/models/od19_approval_source.py) (strategy `tier_validation`)
