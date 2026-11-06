# เอกสารออกแบบ: โมดูลกลางบันทึกร่างอัตโนมัติ (Offline Draft Hub) — `od19_offline_draft`

- **วันที่:** 2026-11-06 (rev1)
- **โมดูลที่แตะ:** สร้างใหม่ `od19_offline_draft` (ไม่แตะ Odoo core; โมดูลงานอื่น `_inherit` เพื่อเปิดใช้แบบ additive)
- **สถานะ:** รอตรวจสอบ (Draft for review)
- **ผู้เกี่ยวข้อง:** ผู้ใช้งานทุกส่วน (ฝ่ายขาย / จัดซื้อ / บริการ / บัญชี / พนักงาน) และฝ่ายไอที–แอดมิน
- **แนวทางที่เลือก:** แนวทาง 1 — Draft Hub (ตารางกลาง `od19.draft` + IndexedDB ฝั่ง client)

---

## 1. บทสรุป (Summary)

ผู้ใช้ต้องการกันข้อมูลสูญหายเมื่อ **เน็ตหลุด / refresh / ปิดหน้า / กดย้อนกลับ** ระหว่างกรอกฟอร์ม งานนี้จึงสร้าง **โมดูลกลาง 1 ตัว** ที่ทำหน้าที่ "บันทึกร่างอัตโนมัติ (Autosave) + กู้คืน (Restore)" ให้โมดูลงานอื่นเรียกใช้ โดยไม่ต้องแก้โค้ดงานนั้น

โมดูลนี้เป็น **T1 (Draft Autosave + Restore เต็มรูปแบบ)** ตามที่ตกลงกันไว้ — **ยังไม่รวม** การส่งอัตโนมัติเมื่อกลับออนไลน์ (Auto-submit ซึ่งเป็นขอบเขต T2) และ **ยังไม่ทำ** offline-first เต็มรูป (T3)

**เป้าหมายเชิงผลลัพธ์**

- เมื่อผู้ใช้กรอกฟอร์มแล้วเน็ตหลุด/ปิดหน้า/refresh แล้วกลับมา → ได้ร่างเดิมคืน พร้อมเลือก "กู้คืน / ทิ้ง"
- ทำงานได้ทั้ง **backend form (OWL)** และ **portal / มือถือ**
- เก็บแบบ **Hybrid**: เก็บฝั่ง client (IndexedDB) ก่อน แล้ว sync ขึ้น server เป็นระยะ/เมื่อออนไลน์
- รองรับ **ไฟล์แนบ/รูป** ในร่างด้วย
- **เปิดใช้เลือกได้เป็นรายโมเดล** (whitelist) ไม่รบกวนฟอร์มอื่น
- เป็นโมดูลกลางที่ต่อยอดไปทุกงานได้ (SO / PO / Purchase Request / Timesheet / Expense ฯลฯ)
- ไม่แตะ Odoo core; ทุกอย่างเป็นแบบ additive

---

## 2. สภาพปัจจุบันและช่องว่าง (Problem)

### 2.1 สิ่งที่มีอยู่แล้วใน Odoo 19

| กลไก | สถานะ | ข้อจำกัดที่เกี่ยวข้อง |
|---|---|---|
| Service Worker ของ web client (`addons/web/static/src/service_worker.js`) | มี | ทำงานเฉพาะ request แบบ navigate (GET เอกสาร) และเสิร์ฟหน้า `/odoo/offline` เท่านั้น — **ไม่แตะ RPC/POST** จึงไม่ได้กันข้อมูลฟอร์มหาย |
| POS Service Worker (`addons/point_of_sale/.../service_worker.js`) | มี | cache asset + ปล่อยให้ `web/dataset` ไปเก็บใน IndexedDB เอง — เป็นสถาปัตยกรรม offline เฉพาะของ POS ไม่ reusable |
| RPC endpoint `/web/dataset/call_kw` (`addons/web/controllers/dataset.py`) | มี | `type='jsonrpc', auth="user"` — ผูก session, ไม่มี idempotency key |

### 2.2 ช่องว่างเทียบกับความต้องการ

| # | ประเด็น | สภาพปัจจุบัน | ผลกระทบ |
|---|---|---|---|
| G1 | ฟอร์มไม่มี autosave | ต้องกดบันทึกเอง ถ้าลืม/เน็ตหลุด ข้อมูลหายทันที | เสียงานที่กรอกไปแล้ว โดยเฉพาะฟอร์มยาว |
| G2 | ไม่มีกลไกกู้คืนร่าง | ไม่มีที่เก็บค่าที่กรอกค้าง | ผู้ใช้ต้องกรอกใหม่ทั้งหมด |
| G3 | หน้า portal ไม่มีระบบร่าง | หน้า portal เป็น QWeb POST ธรรมดา | มือถือเน็ตหลุดบ่อย = เสียงานบ่อย |
| G4 | ไม่มีโมดูลกลางให้ reuse | ถ้าจะทำต้องเขียนซ้ำทุกโมดูล | งานซ้ำซ้อน ไม่เป็นมาตรฐานเดียวกัน |

> หมายเหตุ: Odoo มี autosave ในบางฟอร์ม (ผ่าน `mail.thread`) แต่เป็นกลไกเฉพาะของบางเอกสาร ไม่ใช่ระบบร่างทั่วไปที่กู้คืนได้ และไม่รองรับ portal

---

## 3. ความต้องการ (Requirements)

- **R1** บันทึกร่างอัตโนมัติ (Autosave) ตามกำหนดเวลาแบบ debounce (~2 วินาทีหลังหยุดพิมพ์) สำหรับฟอร์มที่เปิดใช้
- **R2** เมื่อเปิดฟอร์มที่มีร่างอยู่ ต้อง **แจ้งเตือนและให้เลือกกู้คืน / ทิ้ง** (ไม่กู้เงียบ)
- **R3** เมื่อกดบันทึกจริงสำเร็จ ต้องล้างร่างที่เกี่ยวข้องอัตโนมัติ
- **R4** ทำงานได้ทั้ง backend (OWL) และ portal / มือถือ
- **R5** เก็บแบบ Hybrid: client (IndexedDB) + server (`od19.draft`) และ sync ได้เมื่อออนไลน์
- **R6** รองรับ **ไฟล์แนบ/รูป** ในร่าง โดยจำกัดขนาด/จำนวน
- **R7** **เปิดใช้เลือกได้เป็นรายโมเดล** (whitelist) ไม่เปิดกับทุกฟอร์มอัตโนมัติ
- **R8** เก็บเฉพาะฟิลด์ที่แก้ไขจริง และ **ตัดฟิลด์ที่ห้ามเก็บ** (เช่น รหัสผ่าน) ออกได้
- **R9** ผู้ใช้เห็น/แก้ได้เฉพาะร่างของตัวเอง และภายใน company เดียวกัน (SoD: แยกหน้าที่)
- **R10** ร่างมีอายุ (TTL) และถูกล้างอัตโนมัติเมื่อหมดอายุ
- **R11** ไม่แตะ Odoo core; ทุกอย่างเป็นแบบ additive ผ่าน `_inherit`
- **R12** ต้องมี Unit Test ครอบคลุม logic ฝั่ง server และไม่กระทบ module อื่น

---

## 4. ขอบเขต (Scope)

### 4.1 ในขอบเขต (In scope)

- โมดูลกลาง `od19_offline_draft`
- โมเดล server `od19.draft` + ไฟล์แนบผ่าน `ir.attachment`
- OWL service ฝั่ง client + IndexedDB store + patch `FormController`
- แบนเนอร์/ไดอะล็อก "กู้คืน / ทิ้ง"
- ระบบ registry เปิดใช้รายโมเดล + ฉีดรายชื่อเข้า `session_info`
- ชุด asset สำหรับ portal (autosave ระดับฟิลด์)
- `ir.cron` ล้างร่างหมดอายุ
- Security: model access + record rule (own drafts)
- Unit test ฝั่ง Python

### 4.2 นอกขอบเขต (Out of scope)

- **Auto-submit เมื่อกลับออนไลน์** (ขอบเขต T2 — จะทำในเฟสถัดไปบนฐานนี้)
- **Offline-first เต็มรูป / conflict merge อัตโนมัติ** (ขอบเขต T3)
- การแก้ไข Flow เอกสารบัญชี/สต็อกให้ทำงานออฟไลน์ได้ (SO/PO confirm, ตัดสต็อก, ออกบิล — server ยังเป็น authority)
- การ sync ร่างข้ามผู้ใช้ (ร่างผูกกับผู้ใช้เท่านั้น)

---

## 5. สถาปัตยกรรม (Architecture)

### 5.1 ภาพรวม

```
[Backend OWL Form] ─┐
                    ├─► od19_draft Service (JS) ─► IndexedDB (client)
[Portal Page]  ─────┘            │
                                 │ sync (online / periodic)
                                 ▼
                      od19.draft (server model, JSON payload)
                                 │
                                 └─ ir.attachment (ไฟล์แนบ/รูป)
```

### 5.2 องค์ประกอบ (Components)

| องค์ประกอบ | หน้าที่ | อินเทอร์เฟซที่เปิดให้ใช้ |
|---|---|---|
| `od19.draft` (server model) | เก็บร่างฝั่ง server | `upsert_draft()`, `fetch_draft()`, `discard_draft()`, `mark_applied()` |
| `ir.http` (inherit) | ฉีดรายชื่อโมเดลที่เปิดใช้เข้า `session_info` | — |
| `od19_draft` (OWL service) | จัดการเก็บ/กู้/ sync ฝั่ง client | `save()`, `load()`, `clear()`, `list()` |
| `form_controller_patch` | ต่อเข้า lifecycle ของฟอร์ม OWL | — |
| Draft Banner / Dialog | แจ้งเตือน + ให้เลือกกู้คืน/ทิ้ง | — |
| `portal_autosave.js` | autosave ระดับฟิลด์บนหน้า portal | — |
| `ir.cron` | ล้างร่างหมดอายุ | — |

### 5.3 หลักการออกแบบ

- **แยกส่วน** — server model เก็บข้อมูลอย่างเดียว, service ฝั่ง client เก็บ logic การเก็บ/กู้, patch ทำหน้าที่เชื่อมกับ lifecycle ของฟอร์มเท่านั้น
- **Additive เท่านั้น** — โมดูลงานอื่นเปิดใช้ด้วย `_inherit` ตั้งค่า flag ไม่ต้องแก้โค้ด core
- **ไม่กู้เงียบ** — ผู้ใช้ต้องยืนยันทุกครั้งก่อนกู้ร่าง
- **Fail-safe** — ถ้า client store เขียนไม่ได้ หรือ sync ล้มเหลว ต้องไม่ทำให้ฟอร์มหลักพัง

---

## 6. โมเดลข้อมูล (Data Model)

### 6.1 `od19.draft` (server, Model ธรรมดา)

| ฟิลด์ | ชนิด | คำอธิบาย |
|---|---|---|
| `name` | Char | ป้ายอ่านง่าย เช่น `sale.order#42` (compute/store) |
| `model_name` | Char (index, required) | โมเดลเป้าหมาย เช่น `sale.order` |
| `res_id` | Integer (index) | `0` = ร่างของเรกคอร์ดใหม่ที่ยังไม่ถูกสร้าง |
| `user_id` | M2O `res.users` (required, index) | เจ้าของร่าง, default = current user |
| `company_id` | M2O `res.company` | company ของร่าง |
| `payload` | Json | ค่าฟิลด์ที่บันทึก (เฉพาะฟิลด์ที่แก้และไม่ถูก exclude) |
| `payload_version` | Integer | เวอร์ชัน schema ของ payload |
| `state` | Selection | `active` / `applied` / `discarded` / `expired` |
| `create_date` / `write_date` | Datetime | มาจาก Odoo |
| `expires_at` | Datetime | เวลาหมดอายุ (TTL) |

**ข้อกำหนด**

- **Unique constraint:** `(model_name, res_id, user_id)` เฉพาะร่างที่ยัง `state='active'` — มีร่างที่ยังใช้งานได้ไม่เกิน 1 ร่างต่อ 1 เรกคอร์ดต่อ 1 ผู้ใช้
- **วงจรสถานะ:** ร่างเกิดเป็น `active` → เมื่อบันทึกจริงตั้ง `applied` แล้ว **ลบเรกคอร์ดทันที** / เมื่อกดทิ้งตั้ง `discarded` แล้ว **ลบเรกคอร์ดทันที** / `expired` ใช้เมื่อ cron ล้าง (ลบเช่นกัน) — สถานะที่ไม่ใช่ `active` เป็นเพียงสถานะชั่วคราวก่อนลบ ไม่ได้ครองช่อง unique
- **ไฟล์แนบ:** ใช้ `ir.attachment` โดยตั้ง `res_model='od19.draft'`, `res_id=draft.id` — reuse ระบบเก็บ/ลบ/สิทธิ์ของ Odoo ไม่สร้างตาราง blob เอง
- **`payload_version`:** ใช้ตรวจความเข้ากันได้ ถ้าเวอร์ชันไม่ตรงกับที่โค้ดรองรับ ให้ **ทิ้งเงียบ ๆ** (ไม่กู้) เพื่อกันข้อมูลเพี้ยน

### 6.2 IndexedDB (client)

Object store หลัก:

| Store | Key | เก็บอะไร |
|---|---|---|
| `drafts` | `model_name + '|' + res_id + '|' + userId` | ค่าฟิลด์ (JSON), `updatedAt`, `dirty` |
| `attachments` | `draftKey + '|' + filename` | blob ของไฟล์แนบ/รูป |

- มี `version` ของ schema ฝั่ง client แยกจาก server
- เก็บเฉพาะฟิลด์ที่ **แก้จริง** (diff จากค่าเดิม) และไม่ถูก `od19_draft_exclude`

---

## 7. การไหลของข้อมูล (Data Flow)

1. **แก้ไขฟอร์ม** → debounce ~2 วินาที → เขียน IndexedDB (ทันที) → ถ้าออนไลน์ upsert ขึ้น `od19.draft`
2. **เปิดฟอร์ม** → อ่าน IndexedDB (เร็ว) → ถ้าไม่มีและยังออนไลน์ ดึงจาก server → มีร่าง = เด้งแบนเนอร์ "พบร่าง กู้คืน / ทิ้ง"
3. **กดบันทึกจริงสำเร็จ** → ล้าง local store + ตั้ง draft = `applied` แล้วลบ
4. **เลือกทิ้งร่าง** → ลบทั้ง local และ server
5. **หมดอายุ** → cron ฝั่ง server ล้าง; ฝั่ง client ตรวจ `expires_at` ก่อนกู้

**การ sync (Hybrid)**

- ทริกเกอร์: เมื่อเกิด event `online`, ทุก N วินาที (poll เบา), และตอนกดบันทึก
- ทิศทาง: client → server เป็นหลัก (upsert)
- ถ้า sync ล้มเหลว: เก็บต่อใน client + retry แบบ backoff (ไม่บล็อกผู้ใช้)

---

## 8. การเปิดใช้เป็นรายโมเดล (Enablement)

- Registry ฝั่ง Python กำหนดรายชื่อโมเดลที่เปิดใช้เริ่มต้น (เช่น `sale.order`, `purchase.order`, `purchase.request`, `account.analytic.line`)
- โมดูลงานอื่นเปิดใช้เพิ่มด้วย `_inherit` และตั้งค่า `_od19_draft_enabled = True` (additive ไม่แตะ core)
- `ir.http` (inherit) ฉีดรายชื่อที่เปิดใช้เข้า `session_info` → JS รู้ว่าฟอร์มไหนต้องทำงาน
- ฟิลด์ที่ห้ามเก็บ: ทำเครื่องหมายได้ที่ระดับฟิลด์ของโมเดลงาน (เช่น `od19_draft_exclude`) — ค่าเริ่มต้นตัดฟิลด์ประเภท password ออกเสมอ

---

## 9. รองรับ Portal

- หน้า portal เป็น QWeb (POST ธรรมดา) ไม่ใช่ OWL → ใช้ชุด asset แยก `portal_autosave.js`
- กลไก: hook `input`/`change` ของฟอร์ม → เก็บค่าลง `localStorage`/IndexedDB → กู้คืนเมื่อโหลดหน้า
- ไฟล์แนบในโหมด portal จำกัดเฉพาะ **รูปภาพขนาดเล็ก** (ตามข้อจำกัดของเบราว์เซอร์และขนาดที่ยอมรับได้)
- sync เข้า `od19.draft` ตัวเดียวกับฝั่ง backend (ผ่าน controller/route ที่ผูกสิทธิ์ผู้ใช้ปัจจุบัน)

---

## 10. การจัดการข้อผิดพลาดและกรณีขอบ (Error Handling / Edge Cases)

| กรณี | พฤติกรรม |
|---|---|
| ออฟไลน์ | เก็บใน client ต่อ + retry ด้วย backoff |
| มีร่างอยู่แต่เรกคอร์ดถูกแก้จากที่อื่น | เด้งเทียบให้ผู้ใช้เห็นเวลา/ผู้แก้ ก่อนตัดสินใจกู้ |
| เปิดหลายแท็บพร้อมกัน | last-write-wins + แจ้งเตือนว่าโดนเขียนทับ |
| ไฟล์แนบใหญ่เกินกำหนด | ข้ามไฟล์นั้น + แจ้งเตือน (ค่าเริ่มต้น ~5 MB/ไฟล์) |
| `payload_version` ไม่ตรง | ทิ้งร่างเงียบ ๆ ไม่กู้ |
| เรกคอร์ดปลายทางถูกลบ | ร่างถูกล้างอัตโนมัติ |
| session หมดอายุ | client เก็บร่างต่อ, หยุด sync จนกว่าจะ login ใหม่ |
| client store เขียนไม่ได้ | ฟอร์มหลักทำงานปกติ (fail-safe) + ไม่ throw |

---

## 11. ความปลอดภัย (Security)

- **Model access:** ผู้ใช้ทั่วไป read/write/create/unlink เฉพาะ `od19.draft` (ไม่ใช่ admin ทั้งหมด); การล้างด้วย cron ใช้ `sudo()`
- **Record rule:** เห็น/แก้ได้เฉพาะ `user_id = current user` และ `company_id in current companies`
- **ไฟล์แนบ:** อิงสิทธิ์ผ่าน draft (ผู้ใช้เข้าถึงแนบได้เฉพาะของร่างตัวเอง)
- **SoD:** แยกหน้าที่ — ร่างเป็นข้อมูลส่วนตัวของผู้ใช้ ไม่เปิดให้ผู้อื่นเห็น

---

## 12. การทดสอบ (Testing)

**ฝั่ง Python (`tests/test_od19_draft.py`)**

- upsert: สร้าง/อัปเดตร่างตาม unique constraint
- fetch: ดึงร่างของตัวเองเท่านั้น
- expire: cron ล้างร่างหมดอายุถูกต้อง
- access/record rule: ผู้ใช้อื่นเห็นร่างของเราไม่ได้
- payload_version: เวอร์ชันไม่ตรง → ไม่กู้
- mark_applied / discard: สถานะเปลี่ยนถูกต้อง

**ฝั่ง JS (QUnit)**

- service: `save()` → `load()` คืนค่าเดิม, `clear()` ล้างถูกต้อง
- ตรวจว่าเปิดใช้เฉพาะโมเดลใน whitelist

**คำสั่งรัน (ตาม convention โปรเจกต์)**

```
run-tests.ps1 -Module od19_offline_draft
```

---

## 13. โครงสร้างไฟล์ (File Layout)

```
custom_addons/od19_offline_draft/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── od19_draft.py            # โมเดล od19.draft + เมธอด upsert/fetch/discard/apply
│   └── ir_http.py               # ฉีด enabled models เข้า session_info
├── security/
│   ├── ir.model.access.csv
│   └── od19_draft_security.xml  # record rules (own drafts + company)
├── data/
│   └── ir_cron_data.xml         # ล้างร่างหมดอายุ
├── views/
│   └── od19_draft_views.xml
├── static/src/
│   ├── draft_service.js         # OWL service + IndexedDB + sync
│   ├── form_controller_patch.js # patch lifecycle ฟอร์ม
│   ├── draft_banner.js
│   ├── draft_banner.xml
│   └── offline_draft.scss
├── static/src/portal/
│   └── portal_autosave.js
└── tests/
    ├── __init__.py
    └── test_od19_draft.py
```

---

## 14. ค่าเริ่มต้นที่กำหนดไว้ (Defaults)

| หัวข้อ | ค่าเริ่มต้น |
|---|---|
| Debounce autosave | 2 วินาที |
| TTL ของร่าง | 7 วัน |
| ขนาดไฟล์แนบสูงสุด | ~5 MB/ไฟล์ |
| โมเดลที่เปิดใช้เริ่มต้น | `sale.order`, `purchase.order`, `purchase.request`, `account.analytic.line` |
| ฟิลด์ที่ตัดออกเสมอ | ฟิลด์ประเภท password และ binary ขนาดใหญ่ (ยกเว้นไฟล์แนบที่จัดการแยก) |

ค่าเหล่านี้ปรับได้ภายหลังโดยไม่กระทบสถาปัตยกรรม

---

## 15. เหตุผลการตัดสินใจ (Design Decisions)

- **ทำไม Draft Hub (ตารางกลาง) ไม่ใช่ per-model field:** reuse ได้ทุกโมดูล, คุมสิทธิ์/TTL ที่เดียว, รองรับ "ร่างก่อนสร้าง" ที่ยังไม่มี `res_id`, และไม่ต้องแก้โมเดลงานจำนวนมาก
- **ทำไมใช้ `ir.attachment`:** ได้ระบบเก็บ/ลบ/สิทธิ์ของ Odoo ฟรี ลดความซับซ้อนและความเสี่ยง
- **ทำไมไม่กู้เงียบ:** กันข้อมูลผิด ๆ ทับของจริง ผู้ใช้ต้องเป็นผู้ตัดสินใจ
- **ทำไมไม่รวม Auto-submit (T2) ในเฟสนี้:** ลดความเสี่ยงเรื่อง idempotency/session/ความถูกต้องทางบัญชี ให้พิสูจน์ T1 ให้แน่นก่อน แล้วต่อยอด T2 บนฐานนี้

---

## 16. ความเสี่ยงและข้อจำกัด (Risks & Limitations)

| # | ความเสี่ยง | ผลกระทบ | แนวทางลด |
|---|---|---|---|
| RS1 | ขนาดข้อมูลใน IndexedDB (โดยเฉพาะไฟล์แนบ) | เก็บไม่ได้/ช้า | จำกัดขนาด/จำนวน + ล้างเมื่อบันทึกสำเร็จ |
| RS2 | draft ค้างเยอะจากผู้ใช้ไม่กลับมา | เปลืองพื้นที่ server | TTL + cron ล้างอัตโนมัติ |
| RS3 | ผู้ใช้สับสนระหว่าง "ร่าง" กับ "บันทึกจริง" | เข้าใจผิดว่าบันทึกแล้ว | แบนเนอร์สถานะชัดเจน + ยืนยันตอนกู้ |
| RS4 | หลายแท็บเขียนทับกัน | ร่างเพี้ยน | last-write-wins + แจ้งเตือน |
| RS5 | เปิดใช้กับฟอร์มที่ compute หนัก | ประสิทธิภาพ | เปิดเป็นรายโมเดล (ไม่เปิดทั้งหมด) |

---

## 17. แผนการดำเนินงาน (Implementation Phases)

1. **เฟส 1 — Server foundation:** โมเดล `od19.draft` + security + cron + unit test
2. **เฟส 2 — Registry & session:** ระบบเปิดใช้รายโมเดล + ฉีด `session_info`
3. **เฟส 3 — Backend client:** OWL service + IndexedDB + patch ฟอร์ม + แบนเนอร์กู้คืน
4. **เฟส 4 — Portal:** `portal_autosave.js` + sync
5. **เฟส 5 — Hardening:** edge cases, retry/backoff, TTL, ประสิทธิภาพ

---

## 18. สรุป (Conclusion)

`od19_offline_draft` เป็น **โมดูลกลางชั้น T1** ที่ทำ Autosave + Restore แบบ Hybrid (IndexedDB + `od19.draft`) รองรับทั้ง backend และ portal รวมไฟล์แนบ เปิดใช้เป็นรายโมดูล และไม่แตะ Odoo core — ออกแบบให้เป็นฐานที่ต่อยอดไป **T2 (auto-submit)** และผูกกับโมดูลงานจริง (SO/PO/Purchase Request/Timesheet/Expense) ได้ในเฟสถัดไป
