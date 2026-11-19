# เอกสารออกแบบ: ใบลดหนี้ (Credit Note) ถูกต้องครบวงจร — รวมปุ่มซ้ำ + คัดลอกรายการ + อ้างอิงเอกสารต้นทาง (เฟสเดียว)

- **วันที่:** 2026-11-19
- **Child spec ID:** OD19-DNCN-CREDIT-NOTE (โดเมน Accounting / DN–CN)
- **โมดูลที่แตะ:** `od19_accounting_dncn` (แก้หลัก), `od19_accounting_operational_closure` (แก้), `od19_thai_tax_reports` (แก้), `od19_etax_invoice` (แก้), `od19_reporting_jasper` (ตรวจ/อ่านเท่านั้น) — **ไม่แตะ Odoo core**
- **สถานะ:** Approved — implemented (CN-1…CN-9 ครบ; เทสต์ผ่าน 2026-11-19)
- **ผู้เกี่ยวข้อง:** ฝ่ายบัญชีลูกหนี้ (AR) / เจ้าหนี้ (AP) / ผู้จัดการบัญชี / ฝ่ายภาษี / ไอที–แอดมิน
- **Canonical path:** `docs/superpowers/specs/2026-11-19-od19-accounting-dncn-credit-note-design.md`

---

## 1. บทสรุป (Summary)

โมดูล `od19_accounting_dncn` มีปุ่ม **"Credit Note"** บนหัวใบแจ้งหนี้ที่ Post แล้ว แต่ **ปุ่มนี้ไม่ทำงานอย่างที่คู่มือและผู้ใช้คาดหวัง** จากการตรวจโค้ดจริงพบชุดปัญหาที่เชื่อมโยงกัน 4 กลุ่ม:

1. **ปุ่มซ้ำ 2 ปุ่ม** — ปุ่ม native ของ Odoo (`action_reverse`) และปุ่ม custom (`action_create_credit_note`) ปรากฏพร้อมกันบนใบแจ้งหนี้ `out_invoice`/`in_invoice` ที่ Post แล้ว
2. **ปุ่ม custom ไม่คัดลอกรายการ** — เปิดฟอร์มเปล่าโดยไม่อ่าน `invoice_line_ids` ต่างจากปุ่ม **Debit Note** ที่คัดลอกรายการให้ (ราคา 0) ทำให้ผู้ใช้ได้ใบลดหนี้ว่างและ **ไม่มีการ reverse รายการเดินบัญชีเลย**
3. **ใบลดหนี้เปล่าไม่ถูก reconcile** — `_od19_reconcile_with_parent()` ต้องมีบรรทัด ≥ 2 บรรทัดจึงจับคู่ได้ ใบเปล่าจึงคืน `False` เงียบ ๆ → ยอดค้างลูกหนี้/เจ้าหนี้ไม่ถูกหักลบ
4. **"Source Document" แสดงเลขตัวเอง** — ฟิลด์ `od19_source_document` fallback ไป `self.name` ขัดความหมายของ "เอกสารต้นทาง"

งานนี้ **รวมทุกอย่างเป็นเฟสเดียว** เพื่อให้ใบลดหนี้ "คัดลอกรายการ → reverse บัญชี → reconcile → พิมพ์ได้ (ทั้ง ม.86/9-10 และ e-Tax)" ครบในรอบเดียว โดย **reuse ความสามารถ core** (`_reverse_moves()`) แทนการเขียน copy loop เอง

> **หลักการสำคัญ:** ใช้ [AccountMove._reverse_moves()](../../../addons/account/models/account_move.py) ของ Odoo core เป็นกลไกกลางในการออกใบลดหนี้/ใบกลับด้าน เพื่อได้ทั้ง **การคัดลอกบรรทัด** ตาม business fields และ **การ reverse รายการบัญชีที่ถูกต้อง** โดยไม่ต้องดูแล logic ซ้ำเอง

> **ไม่แตะปุ่ม Debit Note:** ตรวจแล้วว่าปุ่ม DN ([action_create_debit_note](../../../custom_addons/od19_accounting_dncn/models/account_move.py)) ทำงานถูกต้อง (คัดลอกรายการ ราคา 0 เป็นดีไซน์ตั้งใจ เพื่อกรอกยอดเพิ่มหนี้เอง) และตามหลักการ "1 commit = 1 โดเมน" จึง **ไม่แก้ DN ในงานนี้**

---

## 2. ปัญหาและความต้องการ (Problem)

### 2.1 สภาพปัจจุบัน (ยืนยันจากโค้ดจริง)

| # | ประเด็น | หลักฐาน | สภาพ |
|---|---|---|---|
| 1 | ปุ่ม Credit Note ซ้ำ 2 ปุ่ม | native [account_move_views.xml](../../../addons/account/views/account_move_views.xml) ปุ่ม `action_reverse` (แสดงเมื่อ `move_type in out_invoice/in_invoice` และ `state == posted`) + custom [account_move_views.xml](../../../custom_addons/od19_accounting_dncn/views/account_move_views.xml) ปุ่ม `action_create_credit_note` (`invisible="state != 'posted' or dncn"`) | เห็น 2 ปุ่มพร้อมกันบนใบที่ Post แล้ว |
| 2 | ปุ่ม custom ไม่คัดลอกบรรทัด | [action_create_credit_note()](../../../custom_addons/od19_accounting_dncn/models/account_move.py) ส่งคืนแค่ `act_window` + context (ไม่มี `invoice_line_ids`) | เปิดฟอร์มว่าง ต้องพิมพ์บรรทัดใหม่เอง |
| 3 | ปุ่ม custom ไม่ reverse รายการบัญชี | เช่นเดียวกับ (2) — ไม่เรียก `_reverse_moves()` และไม่ตั้ง GL | GL ของใบเดิมไม่ถูกหักลบจากปุ่มนี้ |
| 4 | doc-vs-code gap | [ODOO19_USER_MANUAL_TH.md](../../../ODOO19_USER_MANUAL_TH.md) ระบุ *"Credit Note — คัดลอกรายการและแมปประเภทเอกสาร"* | คู่มือบอกคัดลอก แต่โค้ดไม่ทำ |
| 5 | ใบลดหนี้เปล่าไม่ reconcile | [_od19_reconcile_with_parent()](../../../custom_addons/od19_accounting_dncn/models/account_move.py) → [_od19_reconcile_move_lines()](../../../custom_addons/od19_accounting_features/models/account_move.py) คืน `False` เมื่อ `len(lines) < 2` | CN เปล่า: ยอดค้างไม่ถูกหักลบ เงียบ |
| 6 | Source Document fallback ผิด | [_od19_get_source_document()](../../../custom_addons/od19_accounting_operational_closure/models/account_move.py) คืน `invoice_origin or ref or name` | ไม่มี origin/ref → แสดงเลขตัวเอง |
| 7 | ฝั่งผู้ขายไม่มีรายงาน QWeb อ้างอิงใบลดหนี้ | [tax_invoice_forms.xml](../../../custom_addons/od19_thai_tax_reports/report/tax_invoice_forms.xml) block "อ้างอิงใบกำกับภาษีเดิม" จำกัด `move_type in ('out_invoice','out_refund')` | ใบลดหนี้ฝั่ง vendor (`in_refund`) ไม่มีบล็อกนี้ |
| 8 | e-Tax ไม่ผูกเอกสารต้นทางอัตโนมัติ | [action_od19_create_etax_document()](../../../custom_addons/od19_etax_invoice/models/account_move.py) สร้างเอกสารโดยไม่ตั้ง `source_document_id` ([ฟิลด์](../../../custom_addons/od19_etax_invoice/models/etax_document.py)) | "Corrected Document" ว่าง ต้องเลือกมือ |
| 9 | Jasper credit note อ่าน `parent_id` เท่านั้น | [credit_note_form.jrxml](../../../custom_addons/od19_reporting_jasper/jrxml/credit_note_form.jrxml) `parent_move.id = invoice.parent_id` | ถ้าไม่ตั้ง `parent_id` → พิมพ์แสดง `-` |

> **หมายเหตุ (9):** `_reverse_moves()` ของ core ตั้งเพียง `move_type`, `reversed_entry_id`, `partner_id` — **ไม่ตั้ง `parent_id`** จึงต้อง `write()` เพิ่ม `parent_id` หลังเรียก ไม่งั้น Jasper และปุ่ม stat "Parent Invoice" จะว่าง

### 2.2 ความต้องการ (Requirements)

- **R1** บนใบแจ้งหนี้/บิลที่ Post แล้ว ต้องเหลือ **ปุ่ม Credit Note ปุ่มเดียว** ที่ทำงานถูกต้อง
- **R2** ปุ่ม Credit Note ต้อง **คัดลอกรายการ** จากเอกสารต้นทาง (ผ่าน `_reverse_moves()` เพื่อให้ GL ถูก reverse)
- **R3** ใบลดหนี้ต้องผูก **`parent_id` + `reversed_entry_id`** เพื่อให้รายงานทุกตัว (QWeb / Jasper / e-Tax) อ้างเลขใบเดิมได้
- **R4** รองรับ **ทั้งลูกค้าและผู้ขาย** (`out_refund` และ `in_refund`) จากปุ่มเดียวกัน
- **R5** หลัง Post ใบลดหนี้ ต้อง **reconcile กับใบเดิม** ให้ยอดค้างหักลบจริง (รวมใบลดหนี้ที่ผู้ใช้แก้ไขเป็นบางส่วน)
- **R6** รองรับ **ใบลดหนี้บางส่วน (partial CN)** — ผู้ใช้แก้จำนวน/ราคาในฉบับร่างก่อน Post แล้ว reconcile ตามยอดจริง
- **R7** ฟิลด์ **Source Document** ต้องหมายถึง *เอกสารต้นทาง* จริง (ไม่ fallback ไปเลขตัวเอง)
- **R8** **ไม่ทำลายพฤติกรรมเดิม**: ปุ่ม Debit Note / Remaster และ constraint เหตุผล (`_check_dncn_reason`) คงเดิม
- **R9** ไม่แตะ Odoo core; เพิ่ม/แก้เฉพาะ addons ของโปรเจกต์

### 2.3 นิยามคำสำคัญ

- **Credit Note (ใบลดหนี้)** = เอกสารที่ออกเพื่อลดยอดใบกำกับภาษีเดิม (ม.86/10) Odoo แทนด้วย `out_refund` (ฝั่งลูกค้า) / `in_refund` (ฝั่งผู้ขาย)
- **`_reverse_moves()`** = เมธอด core ที่ reverse ใบ (คัดลอกบรรทัด + map ประเภทใบกลับด้าน + ผูก `reversed_entry_id`)
- **`parent_id`** = ใบต้นทางที่ DN/CN นี้สังกัด (ฟิลด์ของ `od19_accounting_dncn`) — ต่างจาก `reversed_entry_id` ที่ core ใช้
- **partial CN** = ใบลดหนี้ที่ลดเพียงบางส่วนของใบเดิม (จำนวน/ราคาต่ำกว่าเดิม)

---

## 3. หลักการอ้างอิงจากแหล่งน่าเชื่อถือ (Standards Basis)

| หัวข้อ | สาระสำคัญ | แหล่ง |
|---|---|---|
| ใบลดหนี้/ใบเพิ่มหนี้ (ม.86/9–10) | ต้องระบุ "เลขที่/วันที่ของใบกำกับภาษีเดิม" และ "เหตุผล" ที่ออกใบ | ประมวลรัษฎากร / ข้อกำหนด e-Tax |
| กลไก reverse มาตรฐาน Odoo | ใบกลับด้านต้อง flip เครื่องหมายบัญชีและผูกเอกสารต้นทาง (`reversed_entry_id`); ใบประเภท invoice ใช้ `copy` + `TYPE_REVERSE_MAP` | [account_move.py (core)](../../../addons/account/models/account_move.py) |
| ผูกเอกสารต่อเนื่อง (audit trail) | เอกสารต้นทาง → เอกสารกลับด้าน ต้องเชื่อมไม่ขาด (traceability) | SOX/ISO 9001 (สอดคล้องแนวทางเดิมของโปรเจกต์) |
| กระทบยอดลูกหนี้/เจ้าหนี้ | ใบลดหนี้ที่ยังไม่ match ทำให้ยอดค้างไม่ตรง (AR/AP aging คลาดเคลื่อน) | แนวปฏิบัติ AP/AR ทั่วไป |

---

## 4. ดีไซน์ (Design) — เฟสเดียว

### 4.1 ปุ่ม Credit Note ให้คัดลอกรายการ + reverse บัญชี (R2, R3, R4)

**เปลี่ยน** `action_create_credit_note()` จาก *เปิดฟอร์มว่าง* → *สร้างใบลดหนี้ฉบับร่างที่มีบรรทัดคัดลอกแล้ว* ด้วย `_reverse_moves()`:

```python
def action_create_credit_note(self):
    """Create a Credit Note (ใบลดหนี้) — customer and vendor."""
    self.ensure_one()
    default_values = {
        "journal_id": self.journal_id.id,
        "date": fields.Date.context_today(self),
        "invoice_date": fields.Date.context_today(self),
        "ref": _("Reversal of: %s", self.name),
        "invoice_origin": self.name,   # Source Document ชี้ใบเดิม
    }
    new_move = self._reverse_moves([default_values], cancel=False)
    new_move.write({
        "dncn": "cn",
        "parent_id": self.id,          # จำเป็นสำหรับ Jasper / stat button
        "reason_id": self.reason_id.id if self.reason_id else False,
        "remark": self.remark,
        "partner_tax_name": self.partner_id.tax_name or self.partner_id.name,
        "partner_branch_code": self.partner_id.branch_code,
    })
    return {
        "type": "ir.actions.act_window",
        "name": "Credit Note",
        "res_model": "account.move",
        "res_id": new_move.id,
        "view_mode": "form",
        "target": "current",
    }
```

- `_reverse_moves()` ให้ `out_refund`/`in_refund` อัตโนมัติผ่าน `TYPE_REVERSE_MAP` → **รองรับลูกค้า+ผู้ขายในปุ่มเดียว (R4)**
- คัดลอกบรรทัดตาม business fields (`include_business_fields=True`) → **ได้บรรทัด (R2)**
- เอกสารใหม่เป็น **ฉบับร่าง** ให้ผู้ใช้ตรวจ/แก้ก่อน Post (สอดคล้อง R6)
- **ต้อง `write()` `parent_id` หลังเรียก** เพราะ core ไม่ตั้งให้ (ดู §2.1 ข้อ 9)

**ไลน์ที่สังเกต:** `_reverse_moves()` รับ `default_values_list` ต่อ move; ต้องส่ง list ให้ครบตามจำนวน record (ในปุ่มนี้ `self.ensure_one()` จึงส่ง `[default_values]`)

### 4.2 ซ่อนปุ่ม native ที่ซ้ำ (R1)

เพิ่ม xpath ใน [views/account_move_views.xml](../../../custom_addons/od19_accounting_dncn/views/account_move_views.xml) เพื่อซ่อนปุ่ม native เฉพาะบริบทที่ปุ่ม custom ครอบอยู่แล้ว:

```xml
<xpath expr="//button[@name='action_reverse']" position="attributes">
    <attribute name="invisible">1</attribute>
</xpath>
```

> ทางเลือกที่ปลอดภัยกว่า: ซ่อนเฉพาะเมื่อ `move_type in ('out_invoice','in_invoice')` (ตามที่ปุ่ม custom ครอบ) — แต่เนื่องจากปุ่ม native ปรากฏเฉพาะสองประเภทนี้อยู่แล้ว การซ่อนทั้งหมดจึงปลอดผลข้างเคียง

### 4.3 กระทบยอดกับใบเดิมหลัง Post (R5, R6)

- คง `action_post()` ที่เรียก `_od19_reconcile_with_parent()` หลัง `super().action_post()` เฉพาะ `dncn == "cn"`
- เมื่อใบลดหนี้ **มีบรรทัดแล้ว** (จาก §4.1) รายการ receivable/payable จะครบ 2 ฝั่ง → `_od19_reconcile_move_lines()` จับคู่สำเร็จ (**แก้บั๊ก "CN เปล่าไม่หักยอด")**
- **partial CN:** ผู้ใช้แก้จำนวน/ราคาให้ต่ำกว่าใบเดิมก่อน Post — `reconcile()` จะ partial-match ตามยอดจริงเสมอ (Odoo รองรับ partial reconcile ที่ระดับบรรทัด) → ยอดคงเหลือของใบเดิมสะท้อนส่วนที่ลดจริง
- **Fallback:** `parent = self.parent_id or self.reversed_entry_id` คงไว้ (กันกรณีข้อมูลเก่าที่มีแต่ `reversed_entry_id`)

### 4.4 แก้ความหมาย Source Document (R7)

แก้ [_od19_get_source_document()](../../../custom_addons/od19_accounting_operational_closure/models/account_move.py):

```python
def _od19_get_source_document(self):
    self.ensure_one()
    return self.invoice_origin or self.ref or False   # เดิม: ... or self.name
```

- ตัด fallback ไป `self.name` (เลขตัวเอง) — ถ้าไม่มีเอกสารต้นทางจริงให้เว้นว่าง
- **ต้องอัปเดตเทสต์ที่ยืนยัน fallback เดิม**: [test_cash_reconciliation.py](../../../custom_addons/od19_accounting_operational_closure/tests/test_cash_reconciliation.py) (ยืนยันว่า fallback = `self.name`) → เปลี่ยนเป็นยืนยันค่าว่างเมื่อไม่มี origin/ref
- (ทางเลือกพิจารณา) เพิ่ม `@api.depends('parent_id','reversed_entry_id')` และ fallback ไปเลขใบต้นทางเมื่อมี เพื่อให้ CN/DN แสดงเลขใบเดิมเสมอ — ตัดออกจากเฟสนี้ถ้าเสี่ยงกระทบเทสต์อื่น

### 4.5 ฝั่งผู้ขาย + รายงาน QWeb (R4)

- ปุ่มเดียวรองรับ `in_refund` แล้วจาก §4.1
- ขยาย condition ใน [tax_invoice_forms.xml](../../../custom_addons/od19_thai_tax_reports/report/tax_invoice_forms.xml) ให้บล็อก "อ้างอิงใบกำกับภาษีเดิม" + "เหตุผล" แสดงบน **ใบลดหนี้/เพิ่มหนี้ฝั่งผู้ขาย** ด้วย:

```xml
<div class="row mb-4"
     t-if="o.move_type in ('out_invoice', 'out_refund', 'in_invoice', 'in_refund') and (o.dncn or od19_src)">
```

- **ข้อควรระวัง:** `account.report_invoice_document` เป็นรายงานใบกำกับภาษีฝั่งขาย — ต้องยืนยันว่าเทมเพลตนี้ถูกใช้กับใบกำกับภาษีที่ผู้ขายออกให้เราได้จริง มิฉะนั้นให้ทำเทมเพลต/งานพิมพ์แยก ระบุเป็น **ขั้นตอนตรวจสอบก่อนลงมือ**

### 4.6 ผูก e-Tax Corrected Document อัตโนมัติ (R3)

แก้ [action_od19_create_etax_document()](../../../custom_addons/od19_etax_invoice/models/account_move.py) ให้ตั้ง `source_document_id` อัตโนมัติเมื่อ move นี้เป็น DN/CN ที่มีใบต้นทาง:

```python
parent = self.parent_id or self.reversed_entry_id
source_document = parent.od19_etax_document_ids[:1] if parent else self.env["od19.etax.document"]
document = self.env["od19.etax.document"].create({
    "move_id": self.id,
    "company_id": self.company_id.id,
    "document_type": self._od19_etax_default_type(),
    "source_document_id": source_document.id or False,
})
```

- เขียนเฉพาะเมื่อสร้างใหม่ (ไม่ทับเอกสารที่ผู้ใช้เลือกเอง)
- ถ้าใบต้นทางไม่มี e-Tax document → เว้นว่าง (คงพฤติกรรมเดิม)

### 4.7 ไม่แตะ Debit Note / Remaster (R8)

- คง `action_create_debit_note()` (คัดลอกรายการ ราคา 0) และ `action_remaster_invoice()` ตามเดิม
- คง `_check_dncn_reason` และ guard ใน `action_post()` ตามเดิม

### 4.8 ไฟล์ที่แตะ

| ไฟล์ | การเปลี่ยนแปลง |
|---|---|
| `custom_addons/od19_accounting_dncn/models/account_move.py` | แก้ `action_create_credit_note()` → ใช้ `_reverse_moves()` + `write()` DNCN fields (§4.1) |
| `custom_addons/od19_accounting_dncn/views/account_move_views.xml` | ซ่อนปุ่ม native `action_reverse` (§4.2) |
| `custom_addons/od19_accounting_dncn/tests/test_dncn.py` | เพิ่ม/แก้เทสต์ CN (คัดลอกบรรทัด, parent_id, reconcile, vendor) |
| `custom_addons/od19_accounting_operational_closure/models/account_move.py` | แก้ `_od19_get_source_document()` (§4.4) |
| `custom_addons/od19_accounting_operational_closure/tests/test_cash_reconciliation.py` | อัปเดตความคาดหวัง Source Document (§4.4) |
| `custom_addons/od19_thai_tax_reports/report/tax_invoice_forms.xml` | ขยาย condition ให้ครอบฝั่งผู้ขาย (§4.5) |
| `custom_addons/od19_etax_invoice/models/account_move.py` | ผูก `source_document_id` อัตโนมัติ (§4.6) |
| `ODOO19_USER_MANUAL_TH.md` | ปรับถ้อยคำให้ตรงกับพฤติกรรมจริงหลังแก้ |

> `od19_reporting_jasper/jrxml/credit_note_form.jrxml` **ไม่แก้** — อ่าน `parent_id` อยู่แล้ว และงานนี้ตั้ง `parent_id` ให้ครบ (§4.1)

---

## 5. ขอบเขต (Scope)

### 5.1 ในขอบเขต (เฟสเดียว)
- ปุ่ม Credit Note คัดลอกรายการ + reverse บัญชี ผ่าน `_reverse_moves()` + ตั้ง `parent_id` (§4.1)
- ซ่อนปุ่ม native ที่ซ้ำ (§4.2)
- reconcile หลัง Post ให้ทำงานกับใบที่มีบรรทัด + partial CN (§4.3)
- แก้ความหมาย Source Document (§4.4)
- รองรับฝั่งผู้ขาย + ขยายรายงาน QWeb (§4.5, ภายใต้เงื่อนไขยืนยันเทมเพลตก่อน)
- ผูก e-Tax Corrected Document อัตโนมัติ (§4.6)
- เทสต์ TDD ครบ + อัปเดตคู่มือ

### 5.2 นอกขอบเขต (Out of scope)
- **ไม่แก้ปุ่ม/ลอจิก Debit Note และ Remaster** (§4.7)
- ไม่แก้ Odoo core
- ไม่เปลี่ยนโครงสร้างฟิลด์ `dncn`/`parent_id` (schema คงเดิม)
- ไม่ทำ approval/workflow เพิ่มบน DN/CN (ถ้าต้องการ แยกสเปค)
- ไม่ปรับ Jasper JRXML (อ่าน `parent_id` ได้อยู่แล้ว)

---

## 6. ความปลอดภัยและสิทธิ์ (Security)

- ปุ่ม Credit Note คงใช้สิทธิ์เดียวกับ `account.move` ที่มีอยู่ (ไม่เพิ่มกลุ่มใหม่)
- `write()` ฟิลด์ DNCN เกิดขึ้นภายใน action ของ record ที่ผู้ใช้มีสิทธิ์อยู่แล้ว
- การแก้ Source Document เป็นการเปลี่ยน **การแสดงผล** ไม่เปลี่ยนข้อมูลที่เก็บ (compute store จาก origin/ref)
- e-Tax `source_document_id` เป็นฟิลด์บน `od19.etax.document` — ต้องมีสิทธิ์เดิมของโมดูลอยู่แล้ว
- ยึดหลักเดิม: ไม่ฝัง credential, ไม่แตะไฟล์ secret

---

## 7. การจัดการข้อผิดพลาด (Error handling)

- ถ้าเรียกปุ่ม CN บนเอกสารที่ยังไม่ Post → ปุ่ม invisible อยู่แล้ว (กันที่ UI); ถ้าเรียกผ่านโค้ดบน draft → ปุ่มต้องคืน `UserError` ที่อ่านรู้เรื่อง (พิจารณา `ensure_one` + guard state)
- ถ้าใบต้นทางมี `payment_state='paid'` แล้ว → ยังออกใบลดหนี้ได้ (แนวปฏิบัติทางบัญชี) — ไม่บล็อก แต่ต้อง reconcile ได้เมื่อ Post
- ถ้า `_od19_reconcile_with_parent()` คืน `False` (เช่น ยอดไม่ตรง/คนละ partner) → **log `_logger.info`** ระบุสาเหตุ (ปัจจุบันเงียบ — เพิ่มให้ตรวจสอบได้ ไม่ throw)
- ไม่มี call ภายนอก (offline-tolerant ตามค่าเริ่มต้นโปรเจกต์)

---

## 8. การทดสอบ (Testing / TDD)

| ระดับ | เนื้อหา |
|---|---|
| `od19_accounting_dncn` (TransactionCase) | (1) กดปุ่ม CN บน `out_invoice` ที่ Post → ได้ `out_refund` ที่ **มีบรรทัดคัดลอก**; (2) `parent_id` และ `reversed_entry_id` = ใบเดิม, `dncn='cn'`; (3) Post CN → บรรทัด receivable ของใบเดิม+CN ถูก reconcile (`full_reconcile_id` เดียว, `amount_residual = 0`); (4) **vendor**: ปุ่ม CN บน `in_invoice` → ได้ `in_refund` + reconcile ฝั่ง payable; (5) **partial CN** แก้ราคาให้ต่ำกว่าเดิม → residual ของใบเดิมเหลือตามส่วนลดจริง; (6) เหตุผลยังบังคับก่อน Post |
| `od19_accounting_operational_closure` (TransactionCase) | Source Document: ไม่มี origin/ref → ว่าง; มี `invoice_origin` → ใช้ค่านั้น; CN/DN → ตรวจค่าตามดีไซน์ §4.4 (อัปเดตเทสต์เดิม) |
| `od19_etax_invoice` (TransactionCase) | สร้าง e-Tax document ของ CN ที่มีใบต้นทาง → `source_document_id` ผูกอัตโนมัติ; ใบต้นทางไม่มี e-Tax → ว่าง |
| รายงาน (manual/optional) | เรนเดอร์ QWeb ใบลดหนี้ฝั่งขายและ (ถ้ายืนยันเทมเพลต) ฝั่งผู้ขาย → แสดงเลขใบเดิม+เหตุผล; Jasper credit note form → เลขใบเดิมไม่เป็น `-` |
| คำสั่งรัน | `.\run-tests.ps1 -Module od19_accounting_dncn,od19_accounting_operational_closure,od19_etax_invoice -Database odoo19_t_<AGENT_ID> -HttpPort <ของตัวเอง>` |

> **บทเรียนเดิม:** รันเทสต์ด้วยพอร์ต/DB แยกจาก dev server เพื่อกันชนกัน (§6 AGENTS.md)

---

## 9. เกณฑ์ยอมรับ (Acceptance Criteria)

1. บนใบแจ้งหนี้/บิลที่ Post แล้ว เหลือ **ปุ่ม Credit Note ปุ่มเดียว** (ไม่มีปุ่ม native ซ้ำ)
2. กดปุ่ม Credit Note → ได้ใบลดหนี้ **มีบรรทัดคัดลอกจากใบเดิม** (ราคาเท่าเดิม ผู้ใช้แก้ได้ก่อน Post)
3. ใบลดหนี้มี `parent_id`, `reversed_entry_id` = ใบเดิม, `dncn='cn'` ครบ
4. หลัง Post ใบลดหนี้ (เต็มจำนวน) → ยอดค้างของใบเดิมถูกหักลบ (reconcile สำเร็จ, `0 failed`)
5. หลัง Post ใบลดหนี้ (บางส่วน) → ยอดค้างใบเดิมเหลือตามส่วนที่ลดจริง
6. ปุ่มเดียวรองรับทั้งลูกค้า (`out_refund`) และผู้ขาย (`in_refund`) และ reconcile ฝั่งที่ถูกต้อง
7. ฟิลด์ **Source Document** แสดงเอกสารต้นทางจริง และ **ไม่** fallback ไปเลขตัวเอง
8. รายงาน QWeb ใบลดหนี้แสดง "เลขที่/วันที่ใบกำกับภาษีเดิม" + "เหตุผล" ครบ
9. e-Tax document ของใบลดหนี้ผูก `source_document_id` อัตโนมัติเมื่อมีใบต้นทาง
10. ปุ่ม Debit Note / Remaster และ constraint เหตุผล ทำงานเหมือนเดิม (regression ไม่พัง)
11. ไม่แก้ไฟล์ Odoo core; เทสต์ที่แตะผ่านทั้งหมด (`0 failed, 0 error(s)`)

---

## 10. Task Breakdown (เฟสเดียว)

| ID | Task | Owner (role) | Acceptance criteria | ไฟล์ที่แตะ |
|---|---|---|---|---|
| CN-1 | เขียนเทสต์ CN ใหม่ก่อน (RED): คัดลอกบรรทัด, parent_id, reconcile, vendor, partial | Backend dev | เทสต์ §8 (1)–(6) เขียนครบและ fail ก่อนแก้ | `od19_accounting_dncn/tests/test_dncn.py` |
| CN-2 | เปลี่ยน `action_create_credit_note()` → `_reverse_moves()` + `write()` DNCN | Backend dev | เกณฑ์ 2, 3 ผ่าน | `od19_accounting_dncn/models/account_move.py` |
| CN-3 | ซ่อนปุ่ม native `action_reverse` | Backend dev | เกณฑ์ 1 ผ่าน | `od19_accounting_dncn/views/account_move_views.xml` |
| CN-4 | ตรวจ/เสริม reconcile หลัง Post + log เมื่อไม่สำเร็จ | Backend dev | เกณฑ์ 4, 5 ผ่าน | `od19_accounting_dncn/models/account_move.py` |
| CN-5 | แก้ `_od19_get_source_document()` + อัปเดตเทสต์ที่ยึด fallback เดิม | Backend dev | เกณฑ์ 7 ผ่าน | `od19_accounting_operational_closure/models/account_move.py`, `.../tests/test_cash_reconciliation.py` |
| CN-6 | ขยาย QWeb ให้ครอบฝั่งผู้ขาย (หลังยืนยันเทมเพลต) | Backend dev | เกณฑ์ 8 ผ่าน | `od19_thai_tax_reports/report/tax_invoice_forms.xml` |
| CN-7 | ผูก e-Tax `source_document_id` อัตโนมัติ | Backend dev | เกณฑ์ 9 ผ่าน | `od19_etax_invoice/models/account_move.py` |
| CN-8 | อัปเดตคู่มือ + task A6 ใน remediation plan ให้ตรงจริง | Tech writer/Backend dev | คู่มือตรงพฤติกรรมใหม่ | `ODOO19_USER_MANUAL_TH.md`, `docs/superpowers/plans/2026-10-21-...remediation...md` |
| CN-9 | Deploy `odoo19_pdev` (`-u` โมดูลที่แตะ) + restart + commit แยกโดเมน + push | Backend dev | เทสต์ 0 failed; commit แยกโดเมน | — (ตาม AGENTS.md §11) |

> **หมายเหตุ governance:** ทุกงานที่ปิด task ต้องอัปเดตสถานะในตารางนี้ **พร้อมโค้ด** ใน commit เดียวกัน

---

## 11. ความเสี่ยงและข้อพิจารณา (Risks)

| ความเสี่ยง | ระดับ | การบรรเทา |
|---|---|---|
| `_reverse_moves()` ไม่ตั้ง `parent_id` → Jasper/stat button ว่าง | สูง | `write({'parent_id': self.id})` หลังเรียก (บังคับ); เทสต์ยืนยัน |
| ใบเดิมที่จ่ายหมดแล้ว ออก CN แล้ว reconcile สร้าง residual ผิด | กลาง | เทสต์ partial + full; ให้ `reconcile()` จัดการ partial; log เมื่อไม่สำเร็จ |
| ซ่อนปุ่ม native ทำผู้ใช้บางคนที่เคยใช้ native หาย | ต่ำ | ปุ่ม custom แทนได้ครบ (ฝั่งลูกค้า+ผู้ขาย); แจ้งใน release note/คู่มือ |
| ขยาย QWeb domain ไปฝั่งผู้ขายแล้วเทมเพลตไม่รองรับ layout | กลาง | ยืนยันเทมเพลตก่อน (CN-6); ถ้าไม่รองรับให้ทำเทมเพลตแยก |
| แก้ Source Document กระทบเทสต์/ที่อื่นที่พึ่ง fallback `name` | กลาง | อัปเดตเทสต์เจาะจง; รัน regression ของ `od19_accounting_operational_closure` ทั้งโมดูล |
| แก้หลายโมดูลในงานเดียว → commit หลุดโดเมน | กลาง | commit แยกโดเมนตาม §4 AGENTS.md (CN fix / source doc / etax / docs) |
| ใบลดหนี้ซ้ำกับ flow native `action_reverse` ที่ยังเรียกได้ตาม API | ต่ำ | ตรวจว่าไม่มีจุดอื่นเรียก `action_reverse`; คงไว้ที่ระดับ API แต่ซ่อนที่ UI |

---

## 12. Traceability & Update Order (Governance)

- **Design source of truth:** เอกสารนี้ (สำหรับใบลดหนี้ DNCN)
- **อ้างอิงงานเดิม:** [business-flow remediation plan](../../../docs/superpowers/plans/2026-10-21-odoo19-business-flow-remediation-implementation-plan.md) Task A6 (สถานะ DONE — ต้อง verify; สเปคนี้คือการ verify + แก้ให้ครบ)
- **Work-state:** ใช้ตาราง §10 เป็น task board ชั่วคราว ผูก task-state กับ commit
- **Exec plan:** หากเริ่มลงมือ ควรมีไฟล์คู่กันใน `docs/superpowers/plans/` (เช่น `2026-11-19-od19-accounting-dncn-credit-note-implementation-plan.md`)

**ลำดับการอัปเดตเมื่ออนุมัติ:**
1. อัปเดต **เอกสารนี้** ก่อนเมื่อ scope/ดีไซน์เปลี่ยน
2. เริ่มโค้ดแบบ TDD ตาม §10 (CN-1 → CN-9)
3. sync คู่มือ + task A6
4. deploy `odoo19_pdev` + commit แยกโดเมน + push (AGENTS.md §11)

**Commit coupling:** ปิด task ใด = อัปเดตสถานะ task ใน commit เดียวกับโค้ด

**Drift checks:**
- หนึ่งข้อสรุป = หนึ่ง source of truth (เอกสารนี้สำหรับ design)
- สถานะ task ต้องตรงกับโค้ดจริง ณ commit
- ถ้า Odoo core เปลี่ยนพฤติกรรม `_reverse_moves()` ในอนาคต ให้ทบทวนดีไซน์ §4.1 ใหม่
