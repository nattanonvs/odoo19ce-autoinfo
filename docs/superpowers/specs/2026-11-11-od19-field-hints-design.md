# OD19 Field Hints Design (ข้อความตัวอย่าง/คำแนะนำในช่องกรอก)

Date: 2026-11-11
Module: `od19_field_hints` (ใหม่)
Scope: แสดงข้อความสีเทาอ่อนในช่องกรอกของทุกฟอร์ม เพื่อบอกตัวอย่างข้อมูล / คำแนะนำ / คำเตือน โดยไม่ใส่ค่าลงข้อมูลจริง และไม่แก้ Odoo Core

## ปัญหาและเป้าหมาย

ผู้ใช้ต้องการให้ทุกฟิลด์ที่ **บังคับกรอก** หรือ **ข้อมูลสำคัญ** มีข้อความตัวอย่าง/คำแนะนำ/คำเตือนแสดงเป็น **สีเทาอ่อน** อยู่ในช่องกรอกเอง (ในแบบเดียวกับ `placeholder` ของ HTML) เพื่อให้ผู้ใช้รู้ทันทีว่าควรกรอกอะไร

ข้อจำกัดสำคัญ:

- ต้อง **ไม่ใส่ค่าจริง** ลงในเรกคอร์ด — เป็นเพียงข้อความแสดงผลชั่วคราวที่หายไปเมื่อมีค่า
- ต้อง **ไม่แก้ไฟล์ Core** ของ Odoo (`odoo/`, `addons/`) ตามกฎโปรเจกต์
- ต้องครอบคลุม "ทุกเมนู ทุกโมดูล ทุกที่" โดยไม่ต้องเขียน XML รายฟิลด์ด้วยมือ
- สีเทาอ่อนเพียงอย่างเดียว — ไม่ต้องมีสีเตือนสีแดง/เหลืองแยก

## การตัดสินใจที่อนุมัติแล้ว

| # | ประเด็น | ที่เลือก |
|---|---|---|
| 1 | แหล่งที่มาของข้อความ | **C) ผสม** — สร้างอัตโนมัติจาก metadata เป็นค่าเริ่มต้น + ตาราง override สำหรับฟิลด์สำคัญ |
| 2 | ขอบเขตโมดูล | **B) ทุกโมดูลที่ติดตั้ง** แต่มีสวิตช์ใน Settings (ค่าเริ่มต้นแสดงเฉพาะ `od19_*`) |
| 3 | ฟิลด์ที่ได้รับข้อความ | **B) Required + ฟิลด์สำคัญที่คัดเลือกไว้** |
| 4 | รูปแบบข้อความ | **B) แยก 3 ความหมาย** (ตัวอย่าง / แนะนำ / สำคัญ) ด้วยคำนำหน้า แต่ใช้สีเทาอ่อนเหมือนกัน |

## Non-Goals

1. ไม่ใส่ค่าเริ่มต้นจริง (default value) ลงฟิลด์
2. ไม่แตะ validation หรือ required logic ของ Odoo
3. ไม่แตะ Odoo Core (`odoo/`, `addons/`)
4. ไม่ทำ tooltip/help ผ่าน `ir.model.fields.help` (คนละกลไกกับที่ต้องการ)
5. ไม่เปลี่ยนสีตามระดับความสำคัญ (ใช้เทาอ่อนเท่านั้น)

## ทางเลือกทางเทคนิค

**ทางที่ 1 (เลือกใช้) — OWL patch ที่ `Field` component**
patch getter `fieldComponentProps` ใน `addons/web/static/src/views/fields/field.js` เพื่อเติม `placeholder` ให้ช่องที่เข้าเงื่อนไข จุดนี้เป็นที่มาของ `fieldInfo.attrs.placeholder` ที่ Odoo รองรับอยู่แล้ว จึงได้พฤติกรรมสีเทาอ่อนตามมาตรฐาน

- ได้ครอบคลุมทุกฟิลด์ในทุกฟอร์มทันที
- patch จุดเดียว ไม่ต้องสร้าง view เป็นพันรายการ
- ไม่แตะ Core

**ทางที่ 2 — สร้าง ir.ui.view inheritance อัตโนมัติ**
ยิง `xpath` ใส่ `placeholder` ทุกฟิลด์ในทุกฟอร์ม — ใช้ attribute เนทีฟ แต่ต้องสร้าง view record จำนวนมาก เปราะและหนักตอนติดตั้ง ไม่เลือก

**ทางที่ 3 — ตั้ง `help` บน `ir.model.fields`**
ได้แค่ tooltip ตอน hover ไม่ใช่ข้อความในช่อง จึงไม่ตรงโจทย์ ไม่เลือก

## สถาปัตยกรรม (ทางที่ 1)

### 1. โมดูล
โมดูลใหม่ `od19_field_hints` ภายใต้ `custom_addons/` สิทธิ์เข้าถึง Settings เฉพาะ `base.group_system`

### 2. ฝั่ง Server (Python)

- `res.config.settings` เพิ่ม 2 ฟิลด์:
  - `od19_field_hints.enabled` — สวิตช์มาสเตอร์ (เปิด/ปิดทั้งระบบ)
  - `od19_field_hints.apply_core` — ค่าเริ่มต้น `False` → แสดงเฉพาะโมดูล `od19_*`; ถ้าเปิดจะรวม Core/OCA
- Registry builder สร้าง JSON กะทัดรัด `{model: {field: {kind, text}}}` จาก 3 แหล่ง:
  1. ตาราง `OVERRIDES` — ข้อความไทยเจาะจงรายฟิลด์
  2. รายการ `IMPORTANT_FIELDS` — ฟิลด์ที่อยากมีข้อความแม้ไม่ required
  3. ตัวสร้างอัตโนมัติตามชนิดฟิลด์ (fallback)
- Scope filter: อ่าน `ir.model.modules` เพื่อแยกโมดูล Core/OCA ออกจาก `od19_*`
- เงื่อนไขรับข้อความต่อฟิลด์: `required == True` **หรือ** อยู่ใน `IMPORTANT_FIELDS` **หรือ** มี override

### 3. ฝั่ง Client (JS)

- patch `Field.fieldComponentProps`: ถ้าช่องว่างและเข้าเงื่อนไขและยังไม่มี `placeholder` → เติม `props.placeholder`
- โหลด registry ครั้งเดียวตอน boot ผ่าน service (ไม่ยิงคำขอต่อฟิลด์)

### 4. CSS
ใช้สีเทาอ่อน (ค่าเริ่มต้นของ placeholder อยู่แล้ว) โดยกำหนดให้ชัดเจนที่ `#9CA3AF` เพื่อความสม่ำเสมอ

## กติกาสร้างข้อความอัตโนมัติ

| ชนิดฟิลด์ | ข้อความเริ่มต้น | kind |
|---|---|---|
| char | `ตัวอย่าง: ...` | example |
| text / html | `พิมพ์รายละเอียด...` | hint |
| date / datetime | `วว/ดด/ปปปป` | example |
| monetary / float | `0.00` | example |
| integer | `0` | example |
| many2one / many2many | `เลือก...` | hint |
| selection | `เลือก...` | hint |
| email | `name@example.com` | example |
| phone | `0X-XXX-XXXX` | example |
| อื่น ๆ | `ระบุ...` | hint |

## ชนิดข้อความ 3 แบบ

ทุกแบบใช้สีเทาอ่อนเหมือนกัน ต่างกันที่คำนำหน้า:

- `ตัวอย่าง:` — ข้อมูลตัวอย่างที่ควรกรอก (ค่าเริ่มต้นส่วนใหญ่)
- `แนะนำ:` — คำแนะนำการใช้งาน
- `สำคัญ:` — คำเตือน/เน้นความสำคัญ (ค่าเริ่มต้นของฟิลด์ required)

override กำหนด kind เองได้รายฟิลด์

**ลำดับความสำคัญของ kind และข้อความ** (จากสูงไปต่ำ):

1. `OVERRIDES` — กำหนดทั้ง kind และข้อความเอง
2. ฟิลด์ required (ที่ไม่มี override) — kind = `สำคัญ:`
3. ตัวสร้างอัตโนมัติตามชนิดฟิลด์ — kind = example/hint ตามตาราง

## พฤติกรรม

1. แสดงเฉพาะเมื่อช่อง **ว่าง** — เมื่อมีค่าจริง placeholder หายไปเอง
2. ไม่แสดงใน readonly
3. ไม่ทับค่าจริงและไม่เขียนลงฐานข้อมูล
4. ปิดสวิตช์มาสเตอร์แล้วหายทั้งหมดทันที
5. ฟิลด์ที่มี `placeholder` ใน view อยู่แล้ว → ไม่ทับ (ให้ค่าที่ dev ตั้งไว้ชนะ)

## ขอบเขตและ Settings

- ค่าเริ่มต้น: เฉพาะโมดูล `od19_*`
- เปิด `apply_core` ใน Settings → รวม Core/OCA
- ตำแหน่ง Settings: หน้า Settings ของโมดูล (Technical)

## ประสิทธิภาพและความเสี่ยง

- registry ส่งเฉพาะ override + รายการสำคัญ + กฎ ไม่ส่งทุกฟิลด์ → payload เล็ก
- patch จุดเดียวและอ่านค่าเร็ว (ทำงานตอน render prop เท่านั้น)
- ความเสี่ยงหลัก: ชื่อ/โครงสร้างภายในของ `Field` component เปลี่ยนใน Odoo เวอร์ชันใหม่ — คุมได้เพราะโปรเจกต์ล็อกที่ Odoo 19
- ไม่แตะข้อมูลจริง จึงไม่มีความเสี่ยงต่อความถูกต้องของข้อมูล

## การทดสอบ

- **Python unit test**
  - ตัวสร้างข้อความตามชนิดฟิลด์ (char/date/monetary/many2one/...)
  - scope filter (core vs `od19_*`, เคารพ `apply_core`)
  - เงื่อนไขรับข้อความ (required / important / override)
  - สวิตช์ enabled ปิด → registry ว่าง
- **JS / manual**
  - ตรวจว่า placeholder ปรากฏบนฟอร์มตัวอย่างจริง และหายเมื่อมีค่า
  - ตรวจว่า readonly ไม่แสดง

## ไฟล์ที่จะสร้าง (โดยประมาณ)

- `custom_addons/od19_field_hints/__manifest__.py`
- `custom_addons/od19_field_hints/__init__.py`
- `custom_addons/od19_field_hints/models/res_config_settings.py`
- `custom_addons/od19_field_hints/models/od19_field_hints.py` (registry builder)
- `custom_addons/od19_field_hints/views/res_config_settings_views.xml`
- `custom_addons/od19_field_hints/static/src/field_hints_patch.js`
- `custom_addons/od19_field_hints/static/src/field_hints.scss`
- `custom_addons/od19_field_hints/tests/test_field_hints.py`

## แผนสาขา/พื้นที่ทำงาน (ตาม AGENTS.md)

- worktree: `c:\odoo-dev\od19_field_hints`
- branch: `feature/od19_field_hints`
- `git worktree add/remove/prune` เป็น Tier 2 → ต้องถือ lease `git:worktree`
- commit รูปแบบ Conventional Commits และ `git add -- <path>` เท่านั้น
