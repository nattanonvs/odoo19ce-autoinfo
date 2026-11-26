# ข้อเสนอเพื่อพิจารณา: แพลตฟอร์มบริการที่ปรับแต่งได้อิสระ (AutoInfo Service Center) บน Odoo 19 CE

- **วันที่:** 2026-11-26
- **รหัสงาน:** OD19-SC-PLATFORM
- **สถานะ:** **ข้อเสนอทิศทาง (proposal)** — ยังไม่เริ่มเขียนโค้ด · รอผู้ใช้พิจารณา/อนุมัติ
- **ขอบเขต:** กรอบการพัฒนา (development framework) ที่ทำให้สร้าง "ระบบบริการ" ของแต่ละแผนกได้เอง โดยปรับแต่งเมนู / ฟิลด์ / ดีไซน์ / การคำนวณ / การเชื่อมต่อ ได้อิสระ **ผ่านหน้าจอเว็บ (front-end)**
- **เทมเพลตแรก (Template 01):** ระบบงานแผนก **TA** (TA Service & Equipment Workload Monitoring) — ต่อยอดจากงานที่ทำเสร็จใน S2 (`od19_ta_asset`, `od19_ta_service`)
- **ข้อกำหนดบังคับ:** ทำตาม [AGENTS.md](../../../AGENTS.md) r8 — **ห้ามแตะ Odoo core** และ **ห้ามแตะ `third_party/oca/`** ใช้เฉพาะจุดต่อขยายที่ Odoo รองรับ

---

## 1. บทสรุปผู้บริหาร (Executive Summary)

โจทย์ของท่านคือ **"อยากได้กรอบที่ทำให้ระบบปรับแต่งได้เองได้มากที่สุด"** ไม่ใช่ระบบตายตัวสำหรับแผนกใดแผนกหนึ่ง — เพื่อให้ทุกแผนก (TA, Service, ISO, HR, บัญชี ฯลฯ) ตั้งระบบบริการของตัวเองได้เองโดยไม่ต้องแก้โค้ดทุกครั้ง

ข้อเสนอจึงแบ่งเป็น **3 ระดับ**:

1. **แพลตฟอร์มกลาง (เอนจิน)** — อ่านค่าตั้งต้น (configuration) แล้วสร้าง/ปรับ 5 ส่วนให้เอง: **เมนู · ฟิลด์/Label · ดีไซน์ · การคำนวณ · การเชื่อมต่อภายนอก**
2. **★ Front-end Designer ★** — **ศูนย์ออกแบบผ่านหน้าจอเว็บ** ให้ผู้ใช้ปรับแต่ง "หัวใจ" (เอนจินทั้ง 5 มิติ) ได้อิสระด้วยเมาส์/ฟอร์ม — มี Preview, Apply, Rollback — **ไม่ต้องเขียนโค้ด ไม่ต้อง deploy** (ทดแทน Odoo Studio ซึ่งมีเฉพาะเวอร์ชัน Enterprise)
3. **Designed Template (เทมเพลตสำเร็จรูป)** — ชุดค่าตั้งต้น "สำเร็จรูป" ต่อ 1 แผนก/1 กระบวนการ เช่น **Templates 01 = TA** ซึ่งติดตั้งแล้วได้ระบบพร้อมใช้ แต่ยังแก้ต่อได้จาก Designer

**จุดขายสำคัญ:** ทั้งการตั้งค่าและการ "ออกแบบ" (เมนู/ฟอร์ม/ธีม/สูตร/integration) ทำได้จากหน้าจอเว็บ และเก็บเป็น "ข้อมูล" ไม่ใช่โค้ด — เพิ่ม/ลด/เปลี่ยนได้ตลอดโดยไม่ต้อง deploy โค้ดใหม่ ทุกอย่างอยู่ใน Odoo 19 ตัวเดียว

**การตั้งชื่อที่แนะนำ:** แพลตฟอร์ม = **"AutoInfo Service Center (ASC)"** · โมดูลนำหน้า `od19_sc_*` · พอร์ทัลลูกค้าเป็นโมดูลย่อย `od19_sc_portal` · หน้าจอออกแบบเป็น `od19_sc_designer` (เหตุผลใน §3)

**Design Header Name ที่ปรับให้ลงตัว** (จาก "TA WORKLOAD MONITORING for CUSTOMER SERVICE & EQUIPMENT"):
> **TA Service & Equipment Workload Monitoring**
> _ศูนย์ติดตามภาระงานบริการลูกค้าและอุปกรณ์ (แผนก TA)_

---

## 2. ความเข้าใจโจทย์และหลักการออกแบบ

### 2.1 สิ่งที่โจทย์ต้องการ (ตีความ)

ท่านต้องการ "เปลี่ยนระบบที่แข็ง (hard-coded) ให้กลายเป็นระบบที่อ่อน (soft/configurable)" ครอบคลุม 5 มิติ และ **ต้องแก้ไขได้จากหน้าจอเว็บ**:

| # | มิติที่ต้องปรับได้ | ตัวอย่างที่ท่านยกมา |
|---|---|---|
| 1 | **เมนู** | จำนวน / ชื่อ / กลุ่มหลัก–ย่อย ของเมนู |
| 2 | **ฟิลด์ / Label** | เปลี่ยน–เพิ่ม–ลด ฟิลด์, Label, ประเภทข้อมูล |
| 3 | **ดีไซน์** | สไตล์ / รูปแบบ / สี |
| 4 | **การคำนวณ** | วิธีคิดค่าต่าง ๆ อิสระ |
| 5 | **การเชื่อมต่อภายนอก** | ผ่าน API / Script และอื่น ๆ |

> **ประเด็นสำคัญจากคำชี้แจงของท่าน:** "หัวใจ" (เอนจิน 5 มิติ) **ไม่ใช่แค่ config เบื้องหลัง** — ต้องเป็นส่วนที่ **ออกแบบ/แก้ไขได้อิสระผ่าน front-end** ของระบบเอง → นำไปสู่ **§6 Front-end Designer** ซึ่งเป็นหัวใจของข้อเสนอฉบับนี้

### 2.2 หลักการออกแบบ (Design Principles)

1. **Metadata-driven / Low-code** — ทุกอย่างที่ "เปลี่ยนได้" ต้องเก็บเป็น *ข้อมูล* (record) ไม่ใช่โค้ด
2. **Designer-first** — ทุกการปรับแต่งต้องมี **หน้าจอออกแบบ** รองรับ (ไม่ต้องพึ่งนักพัฒนา) พร้อม Preview + Rollback
3. **ใช้จุดต่อขยายที่ Odoo 19 รองรับเท่านั้น** — `ir.model.fields` (custom field), `ir.ui.view`/`ir.ui.menu` (ข้อมูล), `base_automation`, `ir.actions.server`, `ir.cron`, `ir.asset`, `ir.rule` — ทั้งหมดคือ *data record* ไม่ใช่การแก้ไฟล์ core (จึงไม่ผิด AGENTS.md)
4. **Inherit ก่อน สร้างใหม่เมื่อจำเป็น** — reuse OCA/core ที่มีอยู่ (`helpdesk_mgmt`, `maintenance`, `project`, `res.partner`)
5. **แยก "เอนจิน" ออกจาก "เทมเพลต"** — แก้เอนจินที่เดียว, เทมเพลตเพิ่มได้ไม่จำกัด
6. **ย้อนกลับได้ (reversible)** — ทุกการแก้มี revision + restore
7. **ปลอดภัยเป็นค่าเริ่มต้น** — สิทธิ์/กติกา/การเข้าถึงข้อมูล ยังคุมด้วย `ir.model.access` + `ir.rule`

---

## 3. ข้อเสนอชื่อระบบ (Naming Options)

| ชื่อ | ความหมาย | ข้อดี | ข้อเสีย | เหมาะกับ |
|---|---|---|---|---|
| **Service Management** | การจัดการบริการ | ครบวงจร มีความหมายเชิง ITIL | มักถูกเข้าใจว่าเป็น ITSM/โมดูลซ่อมบำรุงอย่างเดียว | ชื่อฟังก์ชัน |
| **Service Center** ⭐ | ศูนย์บริการ | ครอบคลุมทั้งงานหลังบ้าน + จุดบริการลูกค้า; ขยายหลายแผนกได้เป็นธรรมชาติ | ต้องนิยามขอบเขตให้ชัด | **ชื่อแพลตฟอร์ม (แนะนำ)** |
| **Service Portal** | พอร์ทัลบริการ | ชัดเรื่อง self-service ของลูกค้า | แคบ — เป็นแค่ "หน้าบ้าน" ไม่ใช่ทั้งระบบ | **ชื่อโมดูลย่อย (แนะนำ)** |
| **Services** | บริการ | เรียบง่าย สั้น | กว้างเกินไป ไม่สื่อโครงสร้าง | ป้ายเมนูสั้น ๆ |

### 3.1 คำแนะนำ (Recommendation)

- **ชื่อแพลตฟอร์ม:** **AutoInfo Service Center (ASC)** · prefix โมดูล **`od19_sc_*`**
- **ชื่อชั้นนำเสนอ/พอร์ทัล:** **Service Portal** → โมดูล `od19_sc_portal`
- **ชื่อหน้าจอออกแบบ:** **Service Designer** → โมดูล `od19_sc_designer`
- **ชื่อหน่วยย่อยสำหรับ 1 แผนก/1 กระบวนการ:** **Designed Template** (เช่น "Designed Template 01 — TA")
- **เหตุผล:** "Service Center" ครอบคลุมทั้งศูนย์ปฏิบัติการภายใน (หลังบ้าน หลายแผนก) และจุดให้บริการ (หน้าบ้าน) — ยืดหยุ่นกว่า "Service Management" ที่ผูกกับงานซ่อมบำรุงเพียงอย่างเดียว และเป็นรูปธรรมกว่า "Services" ที่กว้างเกินไป ส่วนคำว่า "Portal" เก็บไว้ใช้กับชั้นที่ติดต่อลูกค้าโดยเฉพาะ

### 3.2 Design Header Name — ปรับให้ลงตัว

**ต้นฉบับ:** `TA WORKLOAD MONITORING for CUSTOMER SERVICE & EQUIPMENT`

**ปรับใหม่ (แนะนำ):**

```
TA Service & Equipment Workload Monitoring
ศูนย์ติดตามภาระงานบริการลูกค้าและอุปกรณ์ (แผนก TA)
```

**ทางเลือกอื่น (ลำดับรอง):**
- `TA Workload Monitoring — Customer Service & Equipment` (ใกล้ต้นฉบับที่สุด)
- `TA Service Workload Center — Customer Service & Equipment`
- `Service & Equipment Workload Monitoring — TA Department` (เหมาะกับ multi-department header แบบ generic)

> โครงสร้าง header ที่ใช้ได้กับทุกเทมเพลต:
> **`[กลุ่มธุรกิจ/แผนก] + [โดเมนงาน] + [คำกริยา/จุดประสงค์]`** เช่น `TA · Service & Equipment · Workload Monitoring`

---

## 4. สถาปัตยกรรม 5 ชั้น (Layered Architecture)

```
┌──────────────────── AutoInfo Service Center (ASC) บน Odoo 19 CE ────────────────────┐
│                                                                                      │
│  ชั้น 4 · นำเสนอ/พอร์ทัล   od19_sc_portal, od19_dashboard, od19_web_navigation         │
│         ────────────────────────────────────────────────────────────────────────────  │
│  ชั้น 3 · เทมเพลต (Designed Templates — เป็นข้อมูล)                                   │
│         Template 01: TA  ·  Template 02: ...  ·  Template N: ...                     │
│         ────────────────────────────────────────────────────────────────────────────  │
│  ชั้น 2 · บริการปฏิบัติการ (reuse ของเดิม)                                             │
│         helpdesk.ticket (OCA) · maintenance.equipment (core) · project.project         │
│         od19_ta_asset / od19_ta_service / od19_service_*                              │
│         ────────────────────────────────────────────────────────────────────────────  │
│  ชั้น 1 · เอนจินปรับแต่ง  od19_sc_core  ★หัวใจ★                                       │
│         Menu · Field/Label · Design · Calculation · Integration                       │
│         ▲                                                                             │
│         │  แก้ไข/ออกแบบได้อิสระผ่านหน้าจอเว็บ                                          │
│  ★ FRONT-END DESIGNER ★  od19_sc_designer (OWL UI + Preview + Apply + Rollback)       │
│         ────────────────────────────────────────────────────────────────────────────  │
│  ชั้น 0 · ฐาน Odoo 19 + OCA + โมดูล od19_* ที่มีอยู่                                  │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

**หลักคิด:** ชั้น 3 (เทมเพลต) ขับเคลื่อนด้วย "ข้อมูล" → บันทึก/โหลด/สลับได้ · ชั้น 1 (เอนจิน) เป็นโค้ดที่เขียนครั้งเดียวแล้วใช้ซ้ำทุกแผนก · **Front-end Designer** คือหน้าจอที่ทำให้ทุกอย่างในชั้น 1 และ 3 แก้ได้โดยไม่ต้องเขียนโค้ด

---

## 5. เอนจินปรับแต่ง 5 มิติ (Config Engine)

> ทุกมิติเก็บเป็น *โมเดลตั้งค่า* แล้ว "apply" ผ่าน API ที่ Odoo 19 รองรับ — ไม่มีการแก้ไฟล์ core
> ทุกมิติมีหน้าจอออกแบบรองรับ (ดู §6)

### 5.1 Menu Engine — จัดการเมนูได้อิสระ

| ประเด็น | แนวทาง |
|---|---|
| จัดการจำนวน / ชื่อ / กลุ่มหลัก–ย่อย | โมเดล `od19.sc.menu.node` (tree ผ่าน `parent_id`, `sequence`) → เมื่อ apply จะสร้าง/อัปเดต `ir.ui.menu` (root/menu/action) |
| ความลึกไม่จำกัด | ใช้ `parent_id` แบบ self-referencing (main group → sub group → item) |
| ชี้ปลายทางได้หลายแบบ | `ir.actions.act_window` (เปิดโมเดล), `ir.actions.act_url` (ลิงก์), `ir.actions.client` (หน้าจอ custom JS) |
| เปลี่ยนชื่อ/ย้าย/ซ่อน ตามแผนก | เก็บ override ต่อ "แผนก" — เห็นเมนูคนละชุดตามสิทธิ์ (`groups_id`) |
| นำทางบนสุด (navbar) | reuse `od19_web_navigation` ที่มีอยู่ |

**ผลลัพธ์:** เพิ่มเมนูใหม่/เปลี่ยนชื่อ/จัดกลุ่ม ทำผ่านหน้าจอตั้งค่า ไม่ต้องแก้ XML

### 5.2 Field & Label Engine — เพิ่ม/ลด/เปลี่ยนฟิลด์และป้ายชื่อ

| ประเด็น | แนวทาง |
|---|---|
| เพิ่มฟิลด์ | โมเดล `od19.sc.field.def` → apply สร้าง `ir.model.fields` (state='manual') เหมือนที่ Odoo Studio ทำ |
| ลบ/ซ่อนฟิลด์ | ตั้ง `active=False` / `ir.ui.view` inherit ซ่อน (`invisible`) |
| เปลี่ยน Label / คำอธิบาย | เก็บใน `field_description` (ผ่าน field def) หรือ inherit view แก้ `string` |
| เปลี่ยนประเภทข้อมูล | รองรับเฉพาะ type ที่ปลอดภัย (char/text/integer/float/boolean/date/datetime/selection/many2one) — **เปลี่ยน type บนฟิลด์ที่มีข้อมูลแล้ว = ต้องมีขั้นยืนยัน + migrate** |
| ค่าตัวเลือก (selection) | `ir.model.fields.selection` — เพิ่ม/ลด/เรียงค่าได้อิสระ |
| สิทธิ์เข้าถึงฟิลด์ | สร้าง `ir.model.access` / `groups` ตามฟิลด์ที่เพิ่ม |

**หมายเหตุข้อจำกัดจริง:** Odoo อนุญาตให้ "เพิ่ม/เปลี่ยน label/เพิ่มค่า selection" อิสระ แต่ "เปลี่ยนชนิดคอลัมน์บนฟิลด์ที่มีข้อมูล" มีความเสี่ยงเรื่องข้อมูลหาย → ข้อเสนอจะบังคับ preview + ยืนยันก่อนทุกครั้ง

### 5.3 Design / Theme Engine — สไตล์ รูปแบบ สี

| ประเด็น | แนวทาง |
|---|---|
| สี / สเปเซอร์ / ระยะมุม | โมเดล `od19.sc.design.token` (design tokens: `--sc-primary`, `--sc-radius`, ...) |
| สร้าง CSS จริง | generate ไฟล์/route ที่คืน CSS แล้วผูกเป็น `ir.asset` ใน bundle `web.assets_backend` |
| อ้างอิงดีไซน์เดิมของบริษัท | ใช้สไตล์ **"Liquid Glass"** + ฟอนต์ **Sarabun / Noto Sans Thai / Tahoma** ที่โปรเจกต์ใช้อยู่แล้ว |
| เลือกธีมต่อเทมเพลต/แผนก | เทมเพลตอ้าง token set หนึ่ง → สลับธีมได้โดยไม่แตะโค้ด |
| header / แบรนด์ | "Design Header Name" ต่อเทมเพลต (§3.2), โลโก้/สีแบรนด์แผนก |

### 5.4 Calculation / Rule Engine — คำนวณค่าอิสระ

| ประเด็น | แนวทาง |
|---|---|
| สูตรคำนวณ | โมเดล `od19.sc.formula` เก็บสูตรเป็น "นิพจน์" แล้วประเมินด้วย `odoo.tools.safe_eval` ใน context ที่จำกัด |
| ค่าประมวลผล (computed) | ผูกรันเมื่อ create/write ของฟิลด์นั้น |
| กติกาอัตโนมัติ (if…then) | ใช้ **Automation Rules** (`base_automation`) + **Server Actions** (`ir.actions.server`) ที่ Odoo มีให้ |
| ตรวจสอบเงื่อนไข / แจ้งเตือน | `ir.rule` (domain), activity, notification (`od19_notification_multi_channel`) |
| ตัวอย่าง TA | นับ Workload ต่อวิศวกร/ต่อช่วงเวลา, เตือนประกันใกล้หมด, % ATG coverage — เก็บเป็นสูตร ไม่ hard-code |

### 5.5 Integration Engine — เชื่อมต่อภายนอก (API / Script)

| ประเด็น | แนวทาง |
|---|---|
| ขาเข้า (inbound) | HTTP Controller (`http.route`) รับ webhook/JSON + mapping เข้าโมเดล |
| ขาออก (outbound) | โมเดล `od19.sc.integration.endpoint` (URL/method/headers/token) → เรียกผ่าน `requests` พร้อม mapping ด้วย safe_eval |
| ตั้งเวลาซิงค์ | `ir.cron` ตามรอบ |
| "Script" ฝั่ง Odoo | Server Action code (Python) ที่รันใน sandbox มาตรฐานของ Odoo |
| ตัวอย่างที่โปรเจกต์มีแล้ว | `od19_currency_rate_bot`, `od19_document_pull` — ใช้เป็นแม่แบบ |
| ย้ายข้อมูลจากระบบเดิม | ETL ภายนอก (ตาม spec TA §9) เป็น "endpoint" ประเภท import |
| ความปลอดภัย | เก็บ credential ใน `ir.config_parameter`/env, จำกัด IP/สิทธิ์, log ทุกครั้งที่เรียก |

---

## 6. ★ Front-end Designer — ศูนย์ออกแบบผ่านหน้าจอ (หัวใจที่แก้ไขได้อิสระ) ★

> **นี่คือส่วนที่ตอบคำชี้แจงของท่านโดยตรง:** เอนจิน 5 มิติ (§5) **แก้ไข/ออกแบบได้อิสระจากหน้าจอเว็บ** ด้วยเมาส์และฟอร์ม — ไม่ต้องเขียนโค้ด ไม่ต้อง deploy — เป็น low-code designer ที่อยู่ใน Odoo เอง

### 6.1 กลไกทางเทคนิค

| องค์ประกอบ | ใช้กลไก Odoo 19 |
|---|---|
| หน้าจอออกแบบ | `ir.actions.client` (tag เช่น `od19_sc.designer`) + **OWL components** ลงทะเบียนใน `registry.category("actions")` |
| Live Preview | เรนเดอร์ schematic/WYSIWYG ในหน้าจอ (ฟอร์มพรีวิว, tree เมนู, ตัวอย่างสี) |
| บันทึก/apply | Server-side RPC ผ่าน method บนโมเดล `od19.sc.*` |
| Materialize เป็นของจริง | `ir.ui.menu`, `ir.model.fields`, `ir.ui.view`, `ir.asset`, `base_automation`, `ir.cron`, `ir.model.access` |
| Rollback | `od19.sc.revision` เก็บ snapshot (JSON) ก่อน apply ทุกครั้ง + ปุ่ม Restore |
| Export/Import | นำเทมเพลต/การออกแบบออกเป็นไฟล์ JSON/XML เพื่อย้าย DB/แผนก |

### 6.2 หน้าจอออกแบบ 5 ส่วน

| หน้าจอออกแบบ | ทำอะไรได้ (อิสระแค่ไหน) | เบื้องหลังเมื่อ Apply |
|---|---|---|
| **① Menu Designer** | ลาก-วางสร้าง **tree เมนูหลัก/ย่อย** ไม่จำกัดชั้น, เปลี่ยนชื่อ, เรียงลำดับ, ไอคอน, เลือกกลุ่มสิทธิ์, เลือกปลายทาง | `ir.ui.menu` + `ir.actions.act_window/client/url` |
| **② Form & Field Designer** | **ลาก-วางฟิลด์บนฟอร์ม**, เพิ่มฟิลด์ใหม่ (เลือกชนิดข้อมูล), เปลี่ยน Label / required / widget / tooltip, จัดกลุ่ม–แท็บ–คอลัมน์, ซ่อน/ลบฟิลด์ | `od19.sc.field.def` → `ir.model.fields` + `ir.ui.view` inherit |
| **③ Design/Theme Designer** | เปลี่ยน **สี / ระยะ / มุมโค้ง / ฟอนต์** (design tokens), ตั้ง header แบรนด์, **preview สด**, สลับธีมต่อเทมเพลต | `od19.sc.design.token` → `ir.asset` (CSS bundle) |
| **④ Formula & Rule Designer** | เขียน **สูตรคำนวณ** ด้วย field picker + function palette, กด **"ทดสอบ"** กับข้อมูลตัวอย่าง, ตั้ง trigger และกติกา if…then | `od19.sc.formula` → computed / `base_automation` + `ir.actions.server` |
| **⑤ Integration Designer** | ตั้ง **endpoint** (URL/method/headers/token), mapping ฟิลด์ด้วย field picker, ปุ่ม **"ทดสอบเชื่อมต่อ"**, ตั้ง cron | `od19.sc.integration` → controller / `requests` / `ir.cron` |

### 6.3 กระบวนการแก้ไข (เหมือนกันทุกหน้าจอ)

```
┌─────────┐   ┌──────────┐   ┌──────────────┐   ┌──────────────┐   ┌────────────┐
│ แก้ไข    │──►│ Preview  │──►│ ตรวจผลกระทบ  │──►│ Apply        │──►│ บันทึก      │
│ (Draft)  │   │ (สด)     │   │ (diff)       │   │ (materialize)│   │ Revision   │
└─────────┘   └──────────┘   └──────────────┘   └──────────────┘   └─────┬──────┘
                                                                         │ (ถ้าผิด)
                                                                    ┌────▼──────┐
                                                                    │ Restore   │
                                                                    └───────────┘
```

### 6.4 คุณสมบัติที่ทำให้ "อิสระ" จริง

- **Live Preview** — เห็นผลก่อน apply (ฟอร์ม/เมนู/สี/ผลสูตร)
- **Revision & Rollback** — ย้อนกลับได้ทุกครั้งที่แก้
- **Test-run** — ทดสอบสูตร/การเชื่อมต่อก่อนใช้งานจริง
- **Template export/import** — ย้ายการออกแบบไป DB/แผนกอื่นได้ (JSON/XML)
- **Permission-scoped** — เฉพาะกลุ่ม "Service Designer" ที่ได้สิทธิ์ออกแบบ
- **Themable designer** — ตัว designer เองใช้ design token ชุดเดียวกัน → ปรับธีมได้ด้วย

### 6.5 ขอบเขตความอิสระ — พูดตรง ๆ

| ระดับ | ทำได้ผ่านหน้าจอ? |
|---|---|
| เมนู / ฟิลด์ / Label / type / selection | ✅ อิสระเต็มที่ |
| ดีไซน์ / สี / ธีม | ✅ อิสระเต็มที่ |
| สูตรคำนวณ / กติกา | ✅ อิสระเต็มที่ (ในกรอบ safe_eval ที่ปลอดภัย) |
| เชื่อมต่อภายนอก (API/webhook/cron) | ✅ ตั้งค่าผ่านหน้าจอ + ปุ่มทดสอบ |
| เขียน **โค้ดใหม่** (Python/OWL ระดับลึก, โมเดลใหม่) | ⚠️ **ไม่ได้ผ่านหน้าจอ** — ต้องเป็นโมดูล/เทมเพลต (ยังทำได้ แต่ต้องมีนักพัฒนา) |
| แก้ Odoo core / `third_party/oca/` | ❌ **ห้ามเด็ดขาด** (ตาม AGENTS.md) |

> สรุป: งานปรับแต่งระดับ "ธุรกิจ/หน้าจอ/ตรรกะ" = อิสระผ่าน front-end ทั้งหมด · งาน "เพิ่มโค้ดใหม่ระดับแพลตฟอร์ม" = ยังต้องเป็นโมดูล (แต่ทำผ่านเทมเพลตได้ ไม่กระทบผู้ใช้)

---

## 7. Designed Template (เทมเพลตสำเร็จรูป)

### 7.1 โครงสร้างเทมเพลต

เทมเพลต 1 ชุด = ข้อมูลชุดหนึ่งในโมเดลตั้งค่า (สร้าง/แก้ได้จาก Designer):

```
od19.sc.template                      ← หัวเทมเพลต (รหัส, ชื่อ, แผนก, header, ธีม)
   ├── od19.sc.menu.node     (N)      ← เมนูหลัก/ย่อยของเทมเพลต
   ├── od19.sc.field.def     (N)      ← ฟิลด์/Label/type ที่เพิ่ม
   ├── od19.sc.design.token  (N)      ← ดีไซน์/สีของเทมเพลต
   ├── od19.sc.formula       (N)      ← สูตรคำนวณ/กติกา
   └── od19.sc.integration   (N)      ← การเชื่อมต่อภายนอก
```

**คุณสมบัติ:** นำเข้า/ส่งออกเทมเพลตได้ (XML/JSON) · version ได้ · ติดตั้ง/ถอนได้ · copy ไปแผนกอื่นเป็นจุดตั้งต้นได้

### 7.2 Template 01 — ระบบงานแผนก TA

| หัวข้อ | ค่า |
|---|---|
| **Department** | TA (แผนกบริการทางเทคนิค) |
| **Designed Template** | 01 |
| **Design Header Name** | **TA Service & Equipment Workload Monitoring** · _ศูนย์ติดตามภาระงานบริการลูกค้าและอุปกรณ์ (แผนก TA)_ |
| **โมดูลฐาน (มีแล้ว)** | `od19_ta_asset`, `od19_ta_service` (commit `0bedae3ee23`, `bc83bb49e91` — สถานะ `puat` แล้ว) |
| **Reuse** | `helpdesk.ticket` (OCA), `maintenance.equipment` (core), `project.project`, `res.partner` |
| **มิติที่ใช้** | ครบ 5 — เมนู (ทะเบียน/งาน/รายงาน) · ฟิลด์ TA · ธีม Liquid Glass · สูตร Workload/Coverage · เชื่อมระบบเดิม (Flask/ATG) ผ่าน API |

**ความหมายเชิงธุรกิจของ "Workload Monitoring":** ติดตามภาระงานของวิศวกร/ทีมต่อแผนกบริการและอุปกรณ์ (จำนวนงานค้าง, งานต่อคนต่อช่วงเวลา, SLA, อุปกรณ์ที่ต้องดูแล) — คำนวณจาก `helpdesk.ticket` + `od19.ta.event` แบบอิสระผ่านสูตร

> หมายเหตุ: งาน TA เฟสนี้ (asset + service) เป็น **ตัวอย่างที่จับต้องได้จริง** ของเทมเพลตแรก — ไม่ได้แปลว่าแพลตฟอร์มจำกัดอยู่ที่ TA

---

## 8. รายการโมดูลที่เสนอ (Module Map)

| โมดูล | หน้าที่ | depends หลัก | เฟส |
|---|---|---|---|
| **`od19_sc_core`** | เอนจินกลาง: template, menu node, field def, design token, formula, integration + revision | `base`, `mail`, `web` | P1 |
| **`od19_sc_designer`** | **หน้าจอออกแบบ (OWL UI)** — Menu/Form/Theme/Formula/Integration Designer + Preview/Apply/Rollback | `od19_sc_core`, `web` | P1 |
| **`od19_sc_ta`** | เทมเพลต 01 (ข้อมูลตั้งค่า TA) + glue ไป `od19_ta_*` | `od19_sc_core`, `od19_ta_asset`, `od19_ta_service` | P2 |
| **`od19_sc_portal`** | พอร์ทัลลูกค้า/พนักงาน + หน้ารายงาน | `od19_sc_core`, `portal` | P3 |
| `od19_sc_workload` *(ทางเลือก)* | ตัวติดตามภาระงาน/แดชบอร์ดบริการ (ถ้าแยกจาก core) | `od19_sc_core`, `helpdesk_mgmt` | P2 |

**โมดูลเดิมที่ reuse:** `od19_dashboard`, `od19_web_navigation`, `od19_document_hub`, `od19_notification_multi_channel`, `od19_role_catalog`, `od19_ai_assistant`, `od19_ui_defaults`

---

## 9. แนวทางการพัฒนาที่ยั่งยืน (Reusable Methodology)

ข้อเสนอวิธีทำงานใหม่ ให้ทุกงาน "แผนกใหม่" ทำซ้ำได้เป็นสูตร — **โดยไม่ต้องเขียนโค้ด**:

**SOP การเพิ่มแผนกใหม่ (ทำซ้ำได้ทุกครั้ง — ผ่านหน้าจอเป็นหลัก):**

```
1. เปิด Service Designer → สร้าง "Designed Template" ใหม่ (copy จากเทมเพลตใกล้เคียง)
2. ออกแบบ 5 มิติผ่านหน้าจอ   (Menu · Form/Field · Theme · Formula · Integration)
3. Preview + ตรวจ diff        (เห็นผลกระทบก่อน apply)
4. Apply → Odoo สร้างของจริง  (ir.ui.menu / ir.model.fields / ir.asset / base_automation / ir.cron)
5. ทดสอบตาม AGENTS.md         (S1→S4 delivery pipeline เดิม)
6. Export เทมเพลตเก็บใน git   (เพื่อ version/ย้าย DB)
```

**หลักประกันความยั่งยืน:**
- **เขียนโค้ดครั้งเดียวที่เอนจิน** — แผนกใหม่ = "ออกแบบผ่านหน้าจอ" ไม่ใช่ "เขียนโค้ด" → ลดหนี้ทางเทคนิค
- **เทมเพลต = ข้อมูล** → version/rollback/copy ได้
- **ใช้เฉพาะจุดต่อขยายของ Odoo 19** → อัปเกรด Odoo ต่อได้ไม่พัง (ไม่แตะ core)
- **Inherit-first** → reuse `helpdesk_mgmt`/`maintenance`/`project` ลดโค้ดซ้ำ
- **อยู่ใต้ governance เดิม** — commit แยกโดเมน, ledger, delivery S1–S4 ตาม [AGENTS.md](../../../AGENTS.md)

---

## 10. ขอบเขต/ข้อจำกัดตาม Odoo 19 + กฎ AGENTS.md

| ประเด็น | ขีดความสามารถจริง | ข้อจำกัดที่ต้องยอมรับ |
|---|---|---|
| เพิ่ม/แก้เมนู, ฟิลด์, Label, type, selection | ทำได้เต็มที่ **ผ่านหน้าจอ** | ฟิลด์/เมนูเป็น record ต่อ DB → ต้อง export เป็น template เพื่อย้าย DB |
| เปลี่ยน type ฟิลด์เดิมที่มีข้อมูล | ทำได้แต่เสี่ยง | ต้อง preview + ยืนยัน + migrate ค่า |
| ดีไซน์/สี (backend) | ทำได้ผ่าน asset/SCSS + Designer | ไม่ใช่ drag-and-drop อิสระทุกจุดเหมือน website builder; อยู่ในกรอบ token |
| สูตรคำนวณอิสระ | safe_eval + automation | ไม่ให้รันโค้ดอันตราย; จำกัด namespace |
| เชื่อมต่อภายนอก | controller + requests + cron | ต้องจัดการ credential/สิทธิ์/rate-limit เอง |
| เขียนโค้ดใหม่ระดับแพลตฟอร์ม | ต้องเป็นโมดูล | ทำผ่าน UI ไม่ได้ (โดยเจตนา เพื่อความปลอดภัย) |
| **ห้ามทำ** | — | แก้ไฟล์ Odoo core, แก้ `third_party/oca/`, ใช้ iframe/thin client (ตาม project memory) |

---

## 11. แผนดำเนินการเป็นเฟส (Phased Plan)

| เฟส | ส่งมอบ | ผลลัพธ์ที่จับต้องได้ |
|---|---|---|
| **P0 — พิสูจน์แนวคิด** | เตรียมสเปกย่อย + ต้นแบบ Designer 1 หน้าจอ (เช่น Menu หรือ Field) | ยืนยันว่าแก้เมนู/ฟิลด์จากหน้าจอได้จริงบน Odoo 19 |
| **P1 — เอนจิน + Designer** | `od19_sc_core` + `od19_sc_designer` (ครบ 5 มิติ) | ออกแบบเมนู–ฟิลด์–ดีไซน์–สูตร–integration ได้จากหน้าจอ + Preview/Rollback |
| **P2 — เทมเพลต 01 (TA)** | `od19_sc_ta` + ต่อ `od19_ta_*` | ระบบ TA พร้อมใช้ในรูปแบบเทมเพลต + Workload Monitoring |
| **P3 — พอร์ทัล & รายงาน** | `od19_sc_portal` + แดชบอร์ด | ลูกค้า/พนักงาน self-service + KPI |
| **P4 — ขยายเทมเพลตอื่น** | Template 02, 03, ... | พิสูจน์ว่า "แผนกใหม่ = ออกแบบผ่านหน้าจอ" จริง |

> ทุกเฟสต้องผ่าน delivery pipeline S1→S4 ตาม AGENTS.md (pdev → puat+push → PR → cleanup)

---

## 12. ความเสี่ยงและแนวทางลด

| # | ความเสี่ยง | ระดับ | แนวทางลด |
|---|---|---|---|
| R1 | ผู้ใช้ออกแบบเยอะเกินจนรก/สับสน | กลาง | บังคับ "template" + naming convention + audit log |
| R2 | เปลี่ยน type ฟิลด์แล้วข้อมูลหาย | สูง | preview + backup + ยืนยัน 2 ขั้น + revision |
| R3 | สูตร (safe_eval) ถูกใช้ในทางที่ผิด | กลาง | จำกัด namespace, whitelist ฟังก์ชัน, log |
| R4 | ข้อมูล credential ของ integration รั่ว | สูง | เก็บใน env/`ir.config_parameter` แบบเข้ารหัส, ไม่ commit |
| R5 | เทมเพลตผูกกับ DB ใด DB หนึ่ง | กลาง | export/import template เป็นไฟล์ (JSON/XML) |
| R6 | Designer เองซับซ้อนเกินไป ทำไม่จบ | สูง | เริ่มทีละหน้าจอ (P0 → P1), ทำ Menu/Field ก่อน |
| R7 | ขอบเขตบานปลาย | สูง | ยึดแผนเฟส P0→P4, ส่งมอบทีละมิติ |

---

## 13. เกณฑ์สำเร็จ (Acceptance Criteria ของแพลตฟอร์ม)

- [ ] เพิ่ม/เปลี่ยน/ลบ **เมนู** (จำนวน/ชื่อ/กลุ่มหลัก–ย่อย) ได้จากหน้าจอ Designer
- [ ] เพิ่ม/ลด/เปลี่ยน **ฟิลด์/Label/type** ได้จากหน้าจอ พร้อม preview
- [ ] เปลี่ยน **ดีไซน์/สี** ต่อเทมเพลตได้จากหน้าจอ (ธีมสลับได้)
- [ ] ตั้ง **สูตรคำนวณ** และกดทดสอบได้จากหน้าจอ
- [ ] ตั้ง **การเชื่อมต่อภายนอก** (API/webhook/cron) + ปุ่มทดสอบได้จากหน้าจอ
- [ ] มี **Preview + Apply + Rollback** ครบทุกหน้าจอออกแบบ
- [ ] **Template 01 (TA)** ติดตั้งแล้วได้ระบบ TA + Workload Monitoring ตาม Design Header Name ที่ตกลง
- [ ] ไม่แตะ Odoo core / `third_party/oca/`
- [ ] ผ่าน delivery pipeline AGENTS.md ครบ S1→S4

---

## 14. จุดตัดสินใจที่ขอความเห็น (Decision Points)

โปรดพิจารณาและให้ความเห็นในประเด็นต่อไปนี้ ก่อนเริ่มเขียนโค้ด:

1. **ชื่อแพลตฟอร์ม** — เห็นด้วยกับ **"AutoInfo Service Center (ASC)"** (prefix `od19_sc_*`) หรือต้องการชื่ออื่น?
2. **Design Header Name** — เลือกจาก §3.2 (แนะนำ `TA Service & Equipment Workload Monitoring`) หรือปรับต่อ?
3. **★ ลำดับการทำ Designer ★** — เริ่มจากหน้าจอออกแบบ **อันไหนก่อน**: Menu Designer (เห็นผลเร็ว) / Form&Field Designer (ทรงพลังสุด) / Theme Designer (เห็นภาพสุด)? *(แนะนำ: Menu → Field → Theme → Formula → Integration)*
4. **ขอบเขตเฟสแรก** — เริ่มจาก **P0 พิสูจน์แนวคิด 1 หน้าจอ** (แนะนำ) หรือลุย **P1 เอนจิน+Designer เต็ม** เลย?
5. **ระดับความอิสระ** — ยอมรับขอบเขต §6.5 / §10 (เขียนโค้ดใหม่ผ่าน UI ไม่ได้) ไหม?
6. **ที่เก็บเทมเพลต** — เก็บเทมเพลตเป็นไฟล์ใน git (แนะนำ เพื่อ version) หรือใน DB เป็นหลัก?
7. **ลำดับงาน** — ทำเอนจิน+Designer ก่อนแล้วค่อยย้าย TA เข้าเทมเพลต (แนะนำ) หรือทำ TA ให้เสร็จก่อนแล้วค่อย refactor เป็นเทมเพลต?

---

## ภาคผนวก ก. อ้างอิง

- งาน TA ที่เสร็จแล้ว: [2026-11-26-od19-ta-asset-register-design.md](2026-11-26-od19-ta-asset-register-design.md)
- กฎการทำงาน: [AGENTS.md](../../../AGENTS.md) · [docs/agents/04-delivery.md](../../agents/04-delivery.md)
- สถาปัตยกรรมองค์กรเดิม: [2026-10-04-odoo19-ce-enterprise-blueprint-design.md](2026-10-04-odoo19-ce-enterprise-blueprint-design.md)
- โมดูลบริการที่มีอยู่: `od19_service_card`, `od19_service_contract`, `od19_service_warranty`, `od19_helpdesk_extension`, `od19_internal_issue`
