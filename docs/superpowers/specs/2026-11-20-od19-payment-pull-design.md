# เอกสารออกแบบ: วิซาร์ด "ดึงเอกสารค้างจ่าย/ค้างรับ → สร้างใบสำคัญรออนุมัติ"

- **วันที่:** 2026-11-20
- **โมดูลที่เสนอ:** `od19_payment_pull` (ใหม่ · depends: `od19_accounting_payment_voucher_reports`)
- **สถานะ:** รอตรวจสอบ (Draft for review)
- **ผู้เกี่ยวข้อง:** ฝ่ายบัญชี (AP / AR) · ผู้อนุมัติการจ่าย (Payment Approver)
- **ที่มา:** ผู้ใช้ตั้งคำถามว่า "เมนู Payment ในบัญชี ไม่ต้องดึง bill มาทำจ่ายหรอ" → ยืนยันให้เพิ่มวิซาร์ดดึงทั้ง **ค้างจ่าย** และ **ค้างรับ**

---

## 1. บทสรุป (Summary)

เพิ่ม **วิซาร์ดเดียว** ที่เปิดได้จากเมนู "ใบสำคัญจ่าย — รออนุมัติ" (Payables) และ "ใบสำคัญรับเงิน — รออนุมัติ" (Receivables) เพื่อ:

1. แสดงรายการ **เอกสารค้าง** (ใบตั้งหนี้ผู้ขายค้างจ่าย / ใบแจ้งหนี้ลูกค้าค้างรับ) ที่ยังมียอดคงเหลือ
2. ให้ผู้ใช้ **ติ๊กเลือกหลายรายการ** และ **แก้ยอดที่จะจ่ายต่อรายการได้ (partial)**
3. กดปุ่มเดียว → สร้าง **ใบสำคัญจ่าย/รับ แบบร่าง (Draft)** เข้าสู่ขั้นตอนเดิม **เตรียมจ่าย → อนุมัติ → Post**

> **หลักการสำคัญ:** วิซาร์ดนี้ **ไม่ Post อะไรเอง** — สร้างแค่รายการร่าง แล้วให้ processo อนุมัติเดิมทำงานต่อ (สอดคล้อง SoD เตรียม/อนุมัติของโมดูล `od19_accounting_payment_voucher_reports`)

---

## 2. ปัญหาและความต้องการ (Problem)

### 2.1 สภาพปัจจุบัน

- เมนู "Payments" ของ core (ที่ OD19 เปลี่ยนชื่อเป็น "รายการจ่ายทั้งหมด / All Payments") เป็น **ทะเบียน/ประวัติ** ของ `account.payment` เท่านั้น — ไม่มีกลไกดึงบิล
- การสร้างรายการจ่ายทำได้เฉพาะ: (ก) เปิดบิลทีละใบ → **Register Payment**, หรือ (ข) เลือกหลายบิลในลิสต์ Bills → Actions → **Pay** (core batch)
- จึงไม่มี "จุดเดียว" ที่เปิดจากเมนูใบสำคัญ แล้วเลือกค้างจ่าย/ค้างรับหลายรายการพร้อมกันได้

### 2.2 ความต้องการ (Requirements)

- **R1** เปิดจากเมนูใบสำคัญจ่าย/รับ แล้วดึงเอกสารค้างได้ทั้งฝั่ง AP และ AR
- **R2** เลือกได้หลายเอกสาร + แก้ยอดจ่ายต่อรายการ (partial)
- **R3** เมื่อยืนยันแล้วได้ **ใบสำคัญแบบร่าง** ที่เข้าคิว "เตรียมจ่าย → อนุมัติ → Post" ของเดิม
- **R4** ยึดหลัก **1 ใบสำคัญต่อคู่ค้า** (รวมบิลของคู่ค้าเดียวกันเป็นใบเดียว)
- **R5** ไม่แตะ Odoo core · label สองภาษา ไทย/อังกฤษ · ต้องแม่นเรื่องยอดคงเหลือ (residual) และสกุลเงิน

---

## 3. ขอบเขต (Scope)

### 3.1 อยู่ในขอบเขต (Phase 1)

| ด้าน | เอกสาร | เงื่อนไข |
|---|---|---|
| AP (จ่าย) | `in_invoice` (ใบตั้งหนี้ผู้ขาย) | `state = posted` และ `amount_residual != 0` |
| AR (รับ) | `out_invoice` (ใบแจ้งหนี้ลูกค้า) | `state = posted` และ `amount_residual != 0` |

- ดึงได้เฉพาะ **บริษัทเดียว** ที่ active (`company_id` เดียวกับบริบทวิซาร์ด)
- ข้ามเอกสารที่ `payment_state = blocked` โดยปริยาย (และ/หรือมีตัวกรองแยก)

### 3.2 เฟส 2 (พิจารณาภายหลัง)

- ตัวเลือก **รวมใบลดหนี้/ใบเพิ่มหนี้** (`in_refund` / `out_refund`) เข้าไปหักกลบ
- ตัวกรองตาม **วันครบกำหนด (due date)** และ "เกินกำหนดแล้วเท่านั้น"
- พิมพ์ใบสำคัญชุด/ส่งอีเมลหลังสร้าง

### 3.3 นอกขอบเขต (Out of scope)

- การ Post / อนุมัติ อัตโนมัติจากวิซาร์ด
- การจ่ายข้ามบริษัท (`sibling companies`)
- การคิด WHT เอง — ใช้พฤติกรรม `account.payment.register` ของ core
- แก้ไขไฟล์ core ทุกกรณี

---

## 4. หลักการออกแบบ (Design Principles)

1. **Reuse ก่อนสร้างใหม่** — เรียก `account.payment.register` ภายใน พร้อมตั้ง `od19_prepare_payment = True` ทำให้ได้รายการร่าง + เก็บ `od19_pending_reconcile_line_ids` ผ่านกลไกเดิม
2. **วิซาร์ดเป็นเพียงตัวจัดชุด (orchestrator)** ไม่บรรจุตรรกะบัญชีเอง — ความถูกต้องของสกุลเงิน/ส่วนต่าง/บล็อกบิลมาจาก core
3. **Fail-safe** — เอกสารที่ไม่ posted / ยอดคงเหลือ ≤ 0 / blocked / ข้ามบริษัท ไม่เข้าในลิสต์
4. **ปลอดภัยตาม SoD** — สร้างได้แค่ Draft; การ Post ต้องผ่าน "เตรียมจ่าย → อนุมัติ" ของเดิม
5. **ไทย-English 2 ภาษา** ตามธรรมเนียมโครงการ · ฟิลด์ที่กำหนดเองขึ้นต้น `od19_`

---

## 5. สถาปัตยกรรม (Architecture)

### 5.1 โครงสร้างโมดูล

```
custom_addons/od19_payment_pull/
├── __manifest__.py                      # depends: account, od19_accounting_payment_voucher_reports
├── models/
│   └── account_payment.py               # (ถ้าจำเป็น) helper สรุป/ยืนยันชุดจ่าย — เริ่มจากว่าง
├── wizards/
│   ├── od19_payment_pull_wizard.py        # select + orchestrate
│   └── od19_payment_pull_wizard_line.py   # แถวเอกสารค้าง (ติ๊ก/แก้ยอด)
├── views/
│   └── od19_payment_pull_views.xml        # ฟอร์มวิซาร์ด + ปุ่มบนหัวลิสต์ใบสำคัญ + create="false"
├── security/ir.model.access.csv           # สิทธิ์ของ 2 โมเดล Transient
├── tests/
│   ├── test_payment_pull_ap.py
│   ├── test_payment_pull_ar.py
│   └── test_payment_pull_guards.py
└── i18n/th.po
```

### 5.2 จุดเชื่อมกับโมดูลเดิม (ไม่แก้ core)

| จุด | การเชื่อม |
|---|---|
| `od19_accounting_payment_voucher_reports.action_od19_payment_vouchers` | เพิ่ม **ปุ่มบนหัวลิสต์ (list header)** เปิดวิซาร์ด (AP) |
| `od19_accounting_payment_voucher_reports.action_od19_receipt_vouchers` | เพิ่มปุ่มบนหัวลิสต์เปิดวิซาร์ด (AR) |
| list view ของทั้งสอง action | ตั้ง `create="false"` เพื่อไม่ให้มีปุ่ม New ซ้ำ (ดู §7.1) |
| `account.payment.register` | เรียกใช้ภายในพร้อม `od19_prepare_payment=True` |

---

## 6. โครงสร้างข้อมูล (Transient Models)

### 6.1 `od19.payment.pull.wizard`

| ฟิลด์ | ชนิด | ค่าเริ่มต้น | หมายเหตุ |
|---|---|---|---|
| `payment_type` | Selection `outbound`/`inbound` | ตามเมนู | กำหนดทิศทาง (จ่าย/รับ) |
| `company_id` | Many2one `res.company` | บริษัทปัจจุบัน | บังคับ |
| `partner_id` | Many2one `res.partner` | – | ตัวกรอง (ว่าง = ทุกคู่ค้า) |
| `date_from` / `date_to` | Date | – | กรองช่วง **วันครบกำหนด** (Phase 2 เปิดใช้เต็ม) |
| `only_overdue` | Boolean | False | เฉพาะเกินกำหนด (Phase 2) |
| `include_refunds` | Boolean | False | รวมใบลดหนี้/เพิ่มหนี้ (Phase 2) |
| `journal_id` | Many2one `account.journal` | – | บังคับ · ต้องมีวิธีจ่ายทิศทางที่ตรง |
| `payment_date` | Date | วันนี้ | วันที่ของรายการจ่าย |
| `group_by_partner` | Boolean | **True** | ยึดตาม R4 (รวมต่อคู่ค้า) |
| `line_ids` | One2many `od19.payment.pull.wizard.line` | – | รายการเอกสารค้าง |
| `selected_count` | Integer (compute) | – | จำนวนที่ติ๊ก |
| `selected_amount` | Monetary (compute) | – | ยอดรวมที่จะจ่าย |
| `planned_voucher_count` | Integer (compute) | – | จำนวนใบสำคัญที่จะถูกสร้าง (ตามกติกาจัดกลุ่ม) |

### 6.2 `od19.payment.pull.wizard.line`

| ฟิลด์ | ชนิด | หมายเหตุ |
|---|---|---|
| `wizard_id` | Many2one | ondelete cascade |
| `selected` | Boolean | ติ๊กเลือก (default True) |
| `move_id` | Many2one `account.move` | readonly |
| `partner_id` | Many2one (related) | readonly |
| `invoice_date` | Date (related) | readonly |
| `date_due` | Date (related `invoice_date_due`) | readonly |
| `currency_id` | Many2one (related) | readonly |
| `amount_total` | Monetary | readonly |
| `amount_residual` | Monetary | readonly |
| `amount_to_pay` | Monetary | **แก้ได้** · default = residual |
| `is_partial` | Boolean (compute) | `amount_to_pay < amount_residual` |

> ทั้ง 2 โมเดลเป็น `TransientModel` → ต้องมีบรรทัดใน `ir.model.access.csv` (บทเรียนจาก `od19_document_intake` เรื่อง warning ใน log)

---

## 7. ส่วนติดต่อผู้ใช้ (UI)

### 7.1 จุดเข้าใช้งาน (Entry Point)

ผู้ใช้เลือก: **กดปุ่ม "New" แล้วเปิดวิซาร์ด** แทนฟอร์มเปล่า

> **ข้อจำกัดทางเทคนิค:** Odoo ไม่มี XML hook ให้ rebind พฤติกรรมปุ่ม "New" ของ list view โดยตรง (New ถูกสั่งจาก controller ฝั่ง JS)
> **แนวทางที่เลือก:** บน list view ของทั้งสอง action → ตั้ง `create="false"` (ซ่อน New เดิม) แล้ววาง **ปุ่มหลักบนหัวลิสต์** ชื่อ
> **"สร้างใบสำคัญจ่าย (ดึงเอกสาร) / New Voucher (Pull documents)"** เป็นทางเดียวที่ผู้ใช้กดจากเมนูนี้ ซึ่งให้ผลตรงกับความต้องการ (เปิดวิซาร์ดก่อนสร้าง) และไม่ต้องใช้ `js_class` ที่เปราะ
> *(ถ้าภายหลังต้องการดักปุ่ม New จริง ๆ ต้องทำผ่าน JS `js_class` ซึ่งจะแยกงานและประเมินความเสี่ยงอีกครั้ง)*

### 7.2 หน้าจอวิซาร์ด

- **Header:** ปุ่ม `ดึงรายการ / Pull` (primary) · `ยกเลิก / Cancel`
- **ส่วนตัวกรอง (ซ้าย):** คู่ค้า, ช่วงวันครบกำหนด, ช่องทางจ่าย (`journal_id`), วันที่จ่าย, "รวมใบลดหนี้"
- **ตารางรายการ:** ติ๊ก + คอลัมน์ คู่ค้า / เลขที่เอกสาร / วันที่ / ครบกำหนด / สกุลเงิน / ยอดรวม / **ยอดคงเหลือ** / **ยอดที่จะจ่าย (แก้ได้)**
- **สรุปท้าย:** "เลือก N รายการ · ยอดรวม X · จะสร้าง M ใบสำคัญ"
- เมื่อเปลี่ยนคู่ค้า/ช่องทาง → โหลดรายการใหม่ (ล้างที่เลือกไว้ กันข้อมูลค้าง — แนวเดียวกับ `od19_document_pull`)

### 7.3 หลังกด "ดึงรายการ"

- สร้างใบสำคัญร่างแล้ว **เปิดลิสต์ใบสำคัญ** กรองเฉพาะรายการที่เพิ่งสร้าง (`domain [('id','in',created_ids)]`)
- แสดง notification สรุป: "สร้างใบสำคัญจ่าย 3 ใบ (รวม 5 บิล)" + เตือนว่า **ยังต้องกด "เตรียมจ่าย" → "อนุมัติ" → "Post"**

---

## 8. ลำดับการทำงาน (Data Flow)

```
กดปุ่มบนหัวลิสต์ → เปิด od19.payment.pull.wizard (target: new)
→ โหลด line_ids = เอกสารค้างที่เข้าเงื่อนไข (state=posted, residual!=0, ไม่ blocked, บริษัทเดียว)
→ ผู้ใช้ติ๊กเลือก + แก้ amount_to_pay (partial ได้)
→ กด "ดึงรายการ" → action_pull():
     1) validate (R1–R5, ยอด 0 < amount_to_pay <= residual)
     2) จัดกลุ่ม (ดู §9 กติกาการจัดกลุ่ม):
        - บรรทัด "เต็มจำนวน" → กลุ่มตาม (partner_id, currency_id)
        - บรรทัด "partial" → แยกเป็นกลุ่มเดี่ยวต่อเอกสาร
     3) ต่อกลุ่ม: สร้าง account.payment.register
          .with_context(active_model='account.move', active_ids=<บิลในกลุ่ม>)
          .create({ journal_id, payment_date, od19_prepare_payment: True,
                    group_payment: <True ถ้ากลุ่มรวม>, amount: <ถ้า partial> })
          → _create_payments()
        ⇒ ได้ account.payment สถานะ draft + od19_prepare_state='draft'
          + od19_pending_reconcile_line_ids ชี้บรรทัดต้นทาง
     4) คืน action เปิดลิสต์ใบสำคัญที่เพิ่งสร้าง + notification สรุป
```

> กลไก `_od19_stage_prepared_payments` (มีอยู่แล้ว) จะกันไม่ให้ Post/Reconcile ทันที — รายการจะค้างเป็นร่างจนกว่าจะกด Post ในภายหลัง ซึ่ง `action_post()` จะเรียก `_od19_reconcile_staged_lines()` ให้เอง

---

## 9. กติกาและการป้องกัน (Guards / Edge Cases)

| กรณี | การจัดการ |
|---|---|
| **partial + การรวมกลุ่ม (สำคัญ)** | บรรทัดที่แก้ยอด (partial) **แยกเป็นใบสำคัญเดี่ยวต่อเอกสาร** เสมอ; บรรทัดเต็มจำนวนเท่านั้นที่รวมต่อคู่ค้า — เพราะ core register ไม่รองรับยอด partial ต่างกันหลายบิลในใบเดียวอย่างแม่นยำ |
| คู่ค้าเดียวกันแต่ **คนละสกุลเงิน** | จัดกลุ่มตาม (partner, **currency**) → แยกใบสำคัญต่อสกุลเงิน |
| เอกสาร `blocked` | ไม่โหลดเข้าในลิสต์ (และ register จะ raise ถ้าหลุดเข้าไป) |
| `amount_residual <= 0` | ไม่โหลดเข้าในลิสต์ |
| `amount_to_pay` ไม่ผ่านเงื่อนไข | `0 < amount_to_pay <= amount_residual` มิฉะนั้น raise `UserError` |
| ไม่ได้ติ๊กเลย | raise `UserError` |
| ช่องทางจ่ายไม่ตรงทิศทาง | กรอง `journal_id` ตาม inbound/outbound payment method |
| เอกสารข้ามบริษัท | ไม่โหลด (company filter) |
| ใบลดหนี้/เพิ่มหนี้ | Phase 2 (ตัวเลือก `include_refunds`) |
| ผู้ใช้กด Post ทันทีโดยไม่เตรียม/อนุมัติ | ถูกกันด้วย `_od19_check_prepare_approval` ของเดิม |

---

## 10. แผนการทดสอบ (Testing)

### 10.1 Unit / Integration (รันบน DB ทดสอบส่วนตัว)

- `test_payment_pull_ap.py`: 2 บิลผู้ขายรายเดียวกัน (เต็มจำนวน) → **1 ใบสำคัญ** ยอดรวมถูก; post → บิล both `paid`
- `test_payment_pull_ar.py`: ใบแจ้งหนี้ลูกค้า 2 ราย → **2 ใบสำคัญ (inbound)**
- `test_payment_pull_guards.py`:
  - partial 1 บิลในกลุ่ม → **แยกใบสำคัญเดี่ยว**, หลัง post residual ตรงยอดที่แก้
  - คนละสกุลเงิน → แยกใบสำคัญ
  - blocked / residual=0 / ไม่ติ๊ก / amount เกิน residual → guard ทำงาน
  - รายการที่สร้างเป็น draft และติด gate เตรียม/อนุมัติบน Post

### 10.2 เกณฑ์ผ่าน

- ครอบคลุม AP+AR × (เต็ม/partial/หลายสกุล) × guards
- ไม่มี warning ใน log (รวม access rules)
- รันผ่านบน DB ทดสอบของ agent (พอร์ต 8081–8099, `odoo19_t_trae-od19_payment_pull`)

---

## 11. การแบ่งเฟส (Phasing)

| เฟส | เนื้อหา | ผลลัพธ์ |
|---|---|---|
| **1** | วิซาร์ด AP+AR · จัดกลุ่มต่อคู่ค้า · partial · ปุ่มบนหัวลิสต์ · เทสต์ + guards | ใช้งานได้ครบตามความต้องการหลัก |
| **2** | ตัวเลือกใบลดหนี้/เพิ่มหนี้ · ตัวกรอง due date/เกินกำหนด · พิมพ์/ส่งใบสำคัญชุด | ความยืดหยุ่นเพิ่ม |

---

## 12. การตัดสินใจที่ยืนยันแล้ว (Resolved Decisions)

- **D1** จัดกลุ่ม = **1 ใบสำคัญต่อคู่ค้า** (ผู้ใช้ยืนยัน 2026-11-20) — พร้อมข้อยกเว้น partial/สกุลเงินตาม §9
- **D2** รองรับ **partial** (แก้ยอดต่อรายการได้) — ผู้ใช้ยืนยัน 2026-11-20
- **D3** จุดเข้า = ปุ่มสร้างที่เมนูใบสำคัญ (**"New เปิดวิซาร์ด"**) — ผู้ใช้ยืนยัน 2026-11-20 · implement ตาม §7.1
- **D4** สร้างเป็น **Draft** เท่านั้น ไม่ Post อัตโนมัติ (คง gate เตรียม/อนุมัติเดิม)

---

## 13. ความเสี่ยง (Risks)

| ความเสี่ยง | ระดับ | การบรรเทา |
|---|---|---|
| partial ในกลุ่มไม่แม่นยำ (กระจายยอดเพี้ยน) | สูง | กติกา: partial → แยกใบสำคัญเดี่ยว (ใช้ core register ต่อบิล) + เทสต์ปักพฤติกรรม |
| Odoo core เปลี่ยนพฤติกรรม register ในอนาคต | กลาง | แตะผ่าน API สาธารณะ + เทสต์ปัก; จำกัดผิวที่เรียก |
| ผู้ใช้สับสนกับปุ่ม New ที่หายไป | ต่ำ | ปุ่มหัวลิสต์ชื่อชัด + help text อธิบาย |
| คู่ค้าหลายสกุลเงินถูกเข้าใจว่ารวมได้ | กลาง | แสดงคอลัมน์สกุลเงิน + แยกใบสำคัญอัตโนมัติ |
