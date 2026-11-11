# เอกสารออกแบบ: ยกระดับความครอบคลุมของผู้ช่วย AI (AI Coverage) — `od19_ai_assistant`

- **วันที่:** 2026-11-10 (rev0)
- **โมดูลที่แตะ:** พัฒนาต่อยอดโมดูลเดิม `od19_ai_assistant` (ไม่เพิ่มโมดูลใหม่; ไม่แตะ Odoo core)
- **สถานะ:** รอตรวจสอบ (Draft for review)
- **ผู้เกี่ยวข้อง:** ผู้ใช้ทุกส่วน (ขาย / จัดซื้อ / บริการ / บัญชี / พนักงาน / ผู้บริหาร) และฝ่ายไอที–แอดมิน
- **แนวทางที่เลือก:** แนวทาง 3 — Hybrid แบบมีชั้น (Generic Explorer + Curated Fast-path + External Providers + Capability Mode + Performance Guards)

---

## 1. บทสรุป (Summary)

ผู้ใช้ต้องการยกระดับผู้ช่วย AI ของระบบ (ปัจจุบันมีเครื่องมือเฉพาะทาง 11 ตัว) ให้ **รอบรู้ รอบคอบ รอบด้าน** ครอบคลุม **ทุกส่วนของ Odoo และภายนอก Odoo** มากที่สุดเท่าที่ทำได้ โดย **ไม่กระทบประสิทธิภาพการทำงานรวมของระบบเกินพอดี**

ปัญหาหลักคือ Odoo DB ของเรามี **361 โมดูลที่ติดตั้ง (รวม 110 โมดูล `od19_*`)** และมีหลายร้อยโมเดล การ "ยัดทุกโมเดล/ฟิลด์เข้า prompt" จะทำให้ context ระเบิด ช้า แพง และความแม่นของโมเดลขนาดเล็ก (8B) ลดลง

แนวทางที่เลือกจึงเป็น **สถาปัตยกรรมแบบมีชั้น เปิดเผยข้อมูลทีละน้อย (progressive disclosure)** — AI เข้าถึงได้ทุกอย่าง แต่โหลดทีละนิดตามความจำเป็น:

- **ชั้น 0** Capability Index — สารบัญเครื่องมือแบบสั้นใน prompt
- **ชั้น 1** Generic Explorer — เครื่องยนต์ดึงข้อมูล ORM ทั่วไป (ครอบคลุมทุกโดเมน)
- **ชั้น 2** Curated Fast-path — เครื่องมือเฉพาะงานยอดฮิต (ตอบเร็ว + แม่น)
- **ชั้น 3** External Providers — (เฟสหลัง) อินเทอร์เน็ต + ระบบบริษัท
- **ชั้น 4** Capability Mode — เลือกได้ระหว่างอ่านเท่านั้น (A) / อ่าน + ร่างเอกสาร (B)
- **Performance Guards** — cache, cap ผลลัพธ์, timeout, ไม่มีงานตอน idle

**เป้าหมายเชิงผลลัพธ์**

- AI ตอบคำถามที่แตะโมเดลใดก็ได้ใน Odoo (ทุกโดเมน) โดยไม่ต้องเขียนเครื่องมือเฉพาะทุกครั้ง
- งานที่ถามบ่อย (บัญชี/ภาษี/ขาย/สต็อก/HR) ตอบเร็วและแม่นในรอบเดียว
- โหมดความปลอดภัยเลือกได้เป็นรายผู้ใช้ — ดีฟอลต์อ่านเท่านั้น และการ "ร่าง" ต้อง opt-in
- ต่อยอดภายนอก (อินเทอร์เน็ต + ระบบบริษัท) เป็นเฟสบนฐานเดิม โดยปิดเป็นค่าเริ่มต้น
- ไม่กระทบประสิทธิภาพระบบ: ทุกอย่าง lazy + cache, ไม่มี cron/worker พื้นหลัง
- ไม่แตะ Odoo core; ทุกอย่าง additive ภายใต้ `od19_ai_assistant`

---

## 2. สภาพปัจจุบันและช่องว่าง (Problem)

### 2.1 สิ่งที่มีอยู่แล้วในโมดูล `od19_ai_assistant`

| กลไก | สถานะ | ข้อจำกัดที่เกี่ยวข้อง |
|---|---|---|
| `od19.ai.tool` — เครื่องมือเฉพาะทาง 11 ตัว (`search_partners`, `search_products`, `search_sale_orders`, `search_purchase_orders`, `search_invoices`, `search_journal_items`, `search_stock_quants`, `search_employees`, `sales_summary`, `tax_summary`, `overdue_receivables`) | มี | ครอบคลุมเฉพาะบางโมเดลที่เขียนไว้ล่วงหน้า — โมเดล/โดเมนอื่น AI เข้าไม่ถึง |
| `od19.ai.chat` — config resolution + tool loop (`MAX_TOOL_ROUNDS = 5`) | มี | prompt catalog ใส่ schema เครื่องมือทั้งหมดทุกครั้ง → โตตามจำนวนเครื่องมือ |
| `lib/client.py` — `chat_completion` / `chat_completion_stream` (OpenAI-compatible) | มี | — |
| `controllers/main.py` — routes list/messages/create/delete + streaming SSE | มี | — |
| `res.config.settings` — provider/base_url/model/api_key/timeout/system_prompt | มี | ยังไม่มีค่าด้านความสามารถ (capability mode) |
| OWL client action `od19_ai_assistant.chat` | มี | — |
| tests `test_ai_assistant.py` | มี (51 tests ผ่าน) | ยังไม่ครอบคลุม generic tools / capability gate |

### 2.2 ช่องว่างเทียบกับความต้องการ

| # | ประเด็น | สภาพปัจจุบัน | ผลกระทบ |
|---|---|---|---|
| G1 | ครอบคลุมไม่ทั่วทุกโดเมน | มีเครื่องมือเฉพาะ 11 ตัว ครอบคลุมบางโมเดล | คำถามที่แตะโดเมนอื่น (โครงการ, ISO, ขนส่ง, CRM, Helpdesk ฯลฯ) AI ตอบไม่ได้ |
| G2 | ขยายเครื่องมือใหม่ต้องเขียนโค้ด | เพิ่มเครื่องมือ = เพิ่มโค้ด + เพิ่มขนาด catalog | ต้นทุนดูแลสูง ไม่ยั่งยืนเมื่อโมดูลโต |
| G3 | catalog โตตามจำนวนเครื่องมือ | ใส่ schema ทั้งหมดใน prompt ทุกรอบ | สิ้นเปลือง token, ตอบช้า, โมเดล 8B แม่นน้อยลง |
| G4 | ไม่มีชั้นความปลอดภัยแบบเลือกได้ | AI อ่านอย่างเดียว (read-only) | ไม่สามารถให้ AI "ช่วยร่าง" เอกสารได้อย่างปลอดภัยและควบคุมได้ |
| G5 | ไม่มีช่องทางภายนอก Odoo | ปิดอยู่ | ตอบไม่ได้เมื่อต้องใช้อินเทอร์เน็ตหรือข้อมูลจากระบบบริษัท (ZKTeco, e-Tax) |
| G6 | ไม่มี audit การเรียกเครื่องมือ | ไม่มี | ตรวจย้อนหลังไม่ได้ว่า AI ทำอะไร ใครสั่ง เมื่อไร |

---

## 3. ความต้องการ (Requirements)

- **R1** AI ต้องเข้าถึง **โมเดลใดก็ได้** ใน Odoo ที่ผู้ใช้มีสิทธิ์อ่าน โดยไม่ต้องเขียนเครื่องมือเฉพาะ
- **R2** ต้องมี **เครื่องมือเฉพาะทาง (curated)** สำหรับงานยอดฮิต เพื่อความเร็วและความแม่น
- **R3** ระบบต้องโหลด schema เครื่องมือแบบ **เปิดเผยทีละน้อย** — prompt มีเฉพาะสารบัญสั้น + โหลด schema เต็มเมื่อถูกเลือก
- **R4** มี **โหมดความสามารถ** เลือกได้: `อ่านเท่านั้น (A)` / `อ่าน + ร่างเอกสาร (B)` — ดีฟอลต์อ่านเท่านั้น, การร่างต้อง opt-in
- **R5** การ "ร่าง" ต้องใช้ **สิทธิ์ผู้ใช้จริง (ไม่ sudo)**, สร้างได้เฉพาะ **whitelist โมเดล**, **บังคับสถานะ draft เท่านั้น** (ห้าม post/confirm/pay/approve) และ **ต้องยืนยันโดยมนุษย์เป็นจังหวะที่ 2**
- **R6** ต้องมี **ชั้นผู้ให้บริการภายนอก** (registry เดียว) สำหรับอินเทอร์เน็ตและระบบบริษัท — ปิดเป็นค่าเริ่มต้น ต้องเปิด + ใส่คีย์
- **R7** ต้องมี **performance guard**: แคช metadata, cap ผลลัพธ์/จำนวนฟิลด์, timeout, จำกัด token ต่อรอบ, ไม่มีงานตอน idle
- **R8** ต้องมี **audit log** บันทึกทุก tool call และทุก draft action
- **R9** ต้องไม่แตะ Odoo core; ทุกอย่างเป็น additive ภายใต้ `od19_ai_assistant`
- **R10** ต้องมี Unit Test ครอบคลุม logic ใหม่ทั้งหมด — เป้าหมาย **0 failed / 0 error** ก่อน commit
- **R11** ต้องทำงานได้กับผู้ให้บริการแบบ OpenAI-compatible ทั้งหมด (Ollama, Groq, Custom) โดยไม่ผูก vendor

---

## 4. ขอบเขต (Scope)

### 4.1 ในขอบเขต (In scope)

- ชั้น Generic Explorer: 4 meta-tools (`list_models`, `describe_model`, `search_records`, `aggregate_records`)
- ชั้น Curated Fast-path: คงเครื่องมือเดิม 11 ตัว + เพิ่มเฉพาะงานยอดฮิตตามโดเมน
- ระบบ Capability Index + Progressive Disclosure (`tool_help`)
- โหมดความสามารถ + gate ความปลอดภัย + กฎเหล็ก draft (whitelist + confirm 2 จังหวะ)
- Performance Guards (cache/cap/timeout/token budget)
- Audit log (`od19.ai.tool.log`)
- หน้าตั้งค่าเพิ่มเติม (capability mode, ช่องทางภายนอก)
- Unit Test ครอบคลุมทุกส่วนใหม่

### 4.2 นอกขอบเขต (Out of scope — เป็นเฟสถัดไป)

- **เฟส 2** ชั้นผู้ให้บริการอินเทอร์เน็ต (web search / fetch) — ออกแบบ registry ไว้ในเฟสนี้ แต่ยังไม่เปิดใช้จริง
- **เฟส 3** Connector ระบบบริษัท (ZKTeco, e-Tax/ETDA XML, currency rate bot, `base_external_dbsource`)
- การเขียน/ยืนยันเอกสารจริง (post/confirm/pay/approve) — **ห้ามเด็ดขาด** ไม่อยู่ในขอบเขตทุกเฟส
- การแก้ไข Odoo core
- Native function-calling (ยังคงใช้ prompt-based tool protocol ให้เป็น model-agnostic)

---

## 5. สถาปัตยกรรม (Architecture)

### 5.1 ภาพรวม

```
                          ┌───────────────────────────────────────────┐
                          │            od19_ai_assistant               │
                          ├───────────────────────────────────────────┤
  [OWL Chat UI] ──SSE──►  │  od19.ai.chat  (tool loop / streaming)     │
                          │        │                                   │
                          │        ▼                                   │
   ┌──────────────────────┴───────────────────────────────────────┐   │
   │ ชั้น 0  Capability Index  (สารบัญสั้นใน prompt)               │   │
   ├──────────────────────────────────────────────────────────────┤   │
   │ ชั้น 1  Generic Explorer (list/describe/search/aggregate)     │◄──┼── ir.model (แคช)
   ├──────────────────────────────────────────────────────────────┤   │
   │ ชั้น 2  Curated Fast-path (เครื่องมือเฉพาะงาน)                │   │
   ├──────────────────────────────────────────────────────────────┤   │
   │ ชั้น 3  External Providers registry  (เฟส 2/3, ปิดดีฟอลต์)     │   │
   ├──────────────────────────────────────────────────────────────┤   │
   │ ชั้น 4  Capability Mode gate  (read-only / read-draft)        │   │
   └──────────────────────────────────────────────────────────────┘   │
                          │                                           │
                          ▼                                           │
                [ orm_guard : ตรวจ domain/field/limit ]              │
                          │                                           │
                          ▼                                           │
                  Odoo ORM (สิทธิ์ผู้ใช้จริง) ──► od19.ai.tool.log (audit)
                          └───────────────────────────────────────────┘
```

### 5.2 องค์ประกอบ (Components)

| องค์ประกอบ | หน้าที่ | อินเทอร์เฟซ |
|---|---|---|
| `od19_ai_tool_generic.py` | เครื่องยนต์ Generic Explorer | `list_models()`, `describe_model()`, `search_records()`, `aggregate_records()` |
| `od19_ai_tool_index.py` | สร้าง Capability Index + progressive disclosure | `prompt_index()`, `tool_help(name)`, `full_schema(name)` |
| `od19_ai_tool.py` (เดิม, ปรับ) | registry รวม curated + generic | `available_tools()`, `execute(name, args)` |
| `od19_ai_capability.py` | gate โหมด + กฎ draft + audit | `capability_mode()`, `can_draft()`, `create_draft()`, `log_call()` |
| `od19_ai_provider.py` (โครงในเฟสนี้) | registry ผู้ให้บริการภายนอก | `list_tools()`, `execute()`, `enabled()` |
| `lib/orm_guard.py` | ตรวจ domain/field/limit ให้ปลอดภัย | `validate_domain()`, `validate_fields()`, `safe_limit()` |
| `res.users` (inherit) | capability mode รายผู้ใช้ | ฟิลด์ `od19_ai_capability_mode` |
| `res.config.settings` (เดิม, ปรับ) | ดีฟอลต์โหมด + ช่องทางภายนอก | ฟิลด์ `od19_ai_capability_mode` |

### 5.3 หลักการออกแบบ

- **Progressive disclosure** — อย่าโหลดทั้งหมด; prompt มีแค่สารบัญ, schema เต็มโหลดเมื่อเลือก
- **Generic ก่อน, curated เสริม** — ความครอบคลุมมาจาก engine ทั่วไป; ความเร็ว/แม่นมาจาก curated
- **ใช้สิทธิ์จริงเสมอ** — ไม่มี `sudo()` ในการอ่าน/ร่างของผู้ใช้
- **Additive เท่านั้น** — ไม่แตะ core; ขยายผ่าน inheritance/registry
- **Fail-safe** — tool ล้มเหลวต้องไม่ทำ chat พัง (ตอบ error อย่างสุภาพ)
- **ไม่มีงานตอน idle** — ไม่มี cron/worker เบื้องหลังที่กินทรัพยากร

---

## 6. ชั้นเครื่องมือ (Tool Layer)

### 6.1 Generic Explorer (ชั้น 1) — ครอบคลุมทุกโดเมน

| tool | arguments | คืนค่า | guard |
|---|---|---|---|
| `list_models` | `keyword` (opt), `limit` | รายชื่อ `{model, name}` ของโมเดลที่ติดตั้ง + ผู้ใช้มีสิทธิ์ read | cap, กรองตามสิทธิ์จริง |
| `describe_model` | `model` | field: `name, type, string, required, relation` | cap ≤ 60 ฟิลด์, เฉพาะ stored |
| `search_records` | `model, domain, fields, limit, order` | เรกคอร์ดจริง (จัดรูปแบบแล้ว) | domain/field whitelist, cap ≤ 20 |
| `aggregate_records` | `model, domain, groupby, aggregates` | ผลสรุปจาก `_read_group` | อนุญาตเฉพาะ aggregate ที่ปลอดภัย |

### 6.2 Curated Fast-path (ชั้น 2)

- คงเครื่องมือเดิมทั้ง 11 ตัว (ไม่แตะพฤติกรรม)
- เพิ่มเฉพาะงานยอดฮิต (ค่อย ๆ เพิ่ม): statement ลูกค้า, รายงานอายุลูกหนี้ (aging), สรุป VAT, สต็อกคงเหลือ/ต่ำกว่า reorder, สรุปการลงเวลาพนักงาน, งานโครงการค้าง
- แต่ละตัวมี `name / model / description / arguments` เหมือนเดิม

### 6.3 Progressive Disclosure ของ catalog (ชั้น 0)

- **จังหวะ 1** — `prompt_index()` สร้างสารบัญ: `ชื่อเครื่องมือ + คำอธิบายสั้น 1 บรรทัด` ของทุกเครื่องมือ (generic + curated) — มีเพดานขนาด
- **จังหวะ 2** — โมเดลเรียก `tool_help(name)` → ได้ schema อาร์กิวเมนต์เต็มของเครื่องมือนั้น → จึงเรียกใช้จริง
- ผลลัพธ์: context ไม่บวมแม้โมดูลจะเพิ่มขึ้น

### 6.4 Domain Guard (`lib/orm_guard.py`)

- **operator whitelist:** `= != > >= < <= in not in like ilike child_of`
- **field ตรวจสอบ:** ชื่อฟิลด์ต้องมีจริงในโมเดลเป้าหมาย, เป็น stored/อ่านได้, ปฏิเสธฟิลด์ compute ที่แพง
- **limit:** cap ≤ 20 (ตรงกับ `MAX_LIMIT` เดิม), รองรับ `offset`
- **model:** ต้องติดตั้ง + ผู้ใช้มีสิทธิ์ read (`has_access("read")`)
- domain ที่ผิดรูปแบบ (ไม่ใช่ list ของ tuple) → ปฏิเสธพร้อมข้อความสุภาพ

---

## 7. โหมดความสามารถและความปลอดภัย (Capability Mode & Safety)

### 7.1 โหมด

`read_only (A)` | `read_draft (B)`

- **ดีฟอลต์ของระบบ** ตั้งใน `res.config.settings.od19_ai_capability_mode`
- **override รายผู้ใช้** ด้วย `res.users.od19_ai_capability_mode` (default ตามดีฟอลต์ระบบ)
- ผู้ใช้ที่ยังไม่ opt-in → ได้ `read_only` เสมอ
- เฟสถัดไปสามารถผูกกับกลุ่มสิทธิ์ (`base_user_role`) ได้

### 7.2 กฎเหล็กของ draft (โหมด B)

- ใช้ **สิทธิ์ผู้ใช้จริง ไม่ sudo**
- สร้างได้เฉพาะ **whitelist โมเดล** (ดูข้อ 16)
- **บังคับสถานะ draft เท่านั้น** — ห้าม post / confirm / pay / approve / action ใด ๆ ที่เปลี่ยนสถานะเป็นยืนยัน
- **ยืนยัน 2 จังหวะโดยมนุษย์:** AI ส่ง "การ์ดร่าง" (ค่าที่จะสร้าง) → UI แสดง → ผู้ใช้กด **ยืนยัน** จึงสร้างจริง
- ฟิลด์สำคัญถูกบังคับค่าให้ปลอดภัย (เช่น `state` เป็น draft, ไม่ตั้งค่าที่เกี่ยวกับการชำระเงิน)
- ตรงหลัก "ไม่มีการอนุมัติสินเชื่อ ไม่มีการจ่ายเงิน"

### 7.3 Audit (`od19.ai.tool.log`)

- บันทึกทุกครั้งที่เรียกเครื่องมือ: ผู้ใช้, เวลา, ชื่อเครื่องมือ, พารามิเตอร์, ผลสรุป (สำเร็จ/ล้มเหลว), ชนิด (read/draft)
- ใช้ตรวจย้อนหลังได้ (ใคร/ทำอะไร/เมื่อไร)

---

## 8. ผู้ให้บริการภายนอก (External Providers — โครงในเฟสนี้)

### 8.1 Registry

interface เดียว:
- `list_tools()` — รายการเครื่องมือภายนอกที่เปิดใช้
- `execute(name, args)` — เรียกใช้
- `enabled()` — เปิด/ปิด (ดีฟอลต์ปิด)

### 8.2 เฟส 2 — อินเทอร์เน็ต

- web search / fetch ผ่าน API ที่ตั้งค่าได้ (ใช้คีย์ของบริษัท)
- ไม่ผูก vendor; ต้องเปิด + ใส่คีย์ถึงใช้ได้

### 8.3 เฟส 3 — ระบบบริษัท

- ต่อผ่าน connector ที่มีอยู่: ZKTeco (ลงเวลา), e-Tax (ETDA XML), currency rate bot, `base_external_dbsource`
- ทุกตัวปิดเป็นค่าเริ่มต้น

> เฟสนี้สร้าง **โครง registry + สวิตช์** ให้พร้อม แต่ยังไม่เปิดใช้จริง

---

## 9. Performance Guards

| กลไก | รายละเอียด |
|---|---|
| Cache | metadata ของ `ir.model` / field list แคชแบบมีขอบเขต + ล้างเมื่อ registry reload |
| Cap | ผลลัพธ์ ≤ 20 แถว; `describe_model` ≤ 60 ฟิลด์; catalog มีเพดานขนาด |
| Timeout | ใช้ค่าเดิม (ดีฟอลต์ local 180s ผ่าน `res.config.settings`) |
| ไม่มีงานตอน idle | ไม่มี cron / worker พื้นหลังใด ๆ |
| Token budget | จำกัดขนาด catalog ต่อรอบ + จำกัดขนาดผลลัพธ์ที่ป้อนกลับโมเดล |
| Single-flight | ไม่ยิง query ซ้อนโดยไม่จำเป็น |

---

## 10. โมเดลข้อมูล (Data Model)

### 10.1 เพิ่มฟิลด์

| โมเดล | ฟิลด์ | ชนิด | คำอธิบาย |
|---|---|---|---|
| `res.users` | `od19_ai_capability_mode` | Selection (`read_only`, `read_draft`) | โหมดรายผู้ใช้ (default ตามระบบ) |
| `res.config.settings` | `od19_ai_capability_mode` | Selection | ดีฟอลต์โหมดทั้งระบบ |

### 10.2 โมเดลใหม่ `od19.ai.tool.log`

| ฟิลด์ | ชนิด | คำอธิบาย |
|---|---|---|
| `name` | Char | ป้ายอ่านง่าย (compute/store) |
| `user_id` | M2O `res.users` (required, index) | ผู้ใช้ที่สั่ง |
| `chat_id` | M2O `od19.ai.chat` (opt, index) | บทสนทนาที่เกี่ยวข้อง |
| `tool_name` | Char (index) | ชื่อเครื่องมือ |
| `tool_kind` | Selection (`read`, `draft`, `external`) | ประเภท |
| `arguments` | Json | พารามิเตอร์ที่ส่ง (ตัดข้อมูลอ่อนไหว) |
| `result_summary` | Char | สรุปผลสั้น ๆ |
| `success` | Boolean | สำเร็จ/ล้มเหลว |
| `error_message` | Char | ข้อความ error (ถ้ามี) |
| `duration_ms` | Integer | เวลาที่ใช้ |
| `create_date` | Datetime | (Odoo) |

**ข้อกำหนด**
- Record rule: ผู้ใช้เห็นเฉพาะ log ของตัวเอง / ผู้ดูแล (`base.group_system`) เห็นได้ทั้งหมด
- เก็บเฉพาะพารามิเตอร์ที่จำเป็น ไม่เก็บข้อมูลอ่อนไหว (password/คีย์)

---

## 11. หน้าตั้งค่า (Settings UI)

เพิ่มในหน้า Settings ของโมดูล:
- **Capability Mode** (ดีฟอลต์ระบบ): `อ่านเท่านั้น` / `อ่าน + ร่างเอกสาร`
- **(เฟส 2)** คีย์ + endpoint สำหรับค้นเว็บ (ปิดดีฟอลต์)
- **(เฟส 3)** สวิตช์ connector ภายนอกแต่ละตัว (ปิดดีฟอลต์)
- คงฟิลด์เดิม: provider / base_url / model / api_key / timeout / system_prompt

---

## 12. การไหลของข้อมูล (Data Flow)

1. ผู้ใช้ถาม → `od19.ai.chat.action_ask()` / streaming controller
2. สร้าง prompt: ระบบ + `prompt_index()` (สารบัญสั้น) + ประวัติสนทนา
3. โมเดลตอบ → ถ้าเป็น tool call → parse → ตรวจ capability + guard → `execute()`
4. ถ้าเป็น generic tool → ตรวจสิทธิ์/domain/field → query → คืนผลแบบจำกัดขนาด
5. ถ้าเป็น `tool_help` → คืน schema เต็มของเครื่องมือ (progressive disclosure)
6. ถ้าเป็น draft action (โหมด B) → ส่ง "การ์ดร่าง" ให้ UI ยืนยัน → สร้าง draft เมื่อผู้ใช้กดยืนยัน
7. ทุกการเรียก → เขียน `od19.ai.tool.log`
8. วนซ้ำภายใน `MAX_TOOL_ROUNDS` แล้วสรุปคำตอบ (streaming)

---

## 13. ความปลอดภัย (Security)

- **Model access:** ผู้ใช้ทั่วไป read `od19.ai.tool.log` เฉพาะของตัวเอง; ผู้ดูแลเห็นทั้งหมด
- **Record rule:** log ผูกกับ `user_id`; draft ใช้สิทธิ์ผู้ใช้จริง (ไม่ sudo)
- **ไม่มี sudo ในการอ่าน/ร่างของผู้ใช้** — เคารพ ACL/record rule ของ Odoo 100%
- **ห้ามเขียนจริง:** ไม่มีเส้นทางใดที่นำไปสู่ post/confirm/pay/approve
- **การพิมพ์ข้อมูลอ่อนไหว:** log ตัด password/คีย์ออก
- **SoD:** แยกหน้าที่ — ข้อมูลส่วนตัวของผู้ใช้ไม่เปิดให้ผู้อื่นเห็น

---

## 14. การทดสอบ (Testing)

**ฝั่ง Python (`tests/test_ai_assistant.py` — ขยาย)**

- Generic tools: `list_models` (กรองสิทธิ์/keyword), `describe_model` (cap ฟิลด์), `search_records` (คืนผลถูกต้อง), `aggregate_records`
- Domain guard: operator นอก whitelist → ปฏิเสธ; field ไม่มีจริง → ปฏิเสธ; limit เกิน → cap
- Capability gate: โหมด A เรียก draft → ถูกปฏิเสธ; โหมด B สร้างได้เฉพาะ draft + whitelist
- Draft: บังคับสถานะ draft, ไม่มี post/confirm, ต้องยืนยันจึงสร้าง
- Progressive disclosure: `prompt_index()` ไม่เกินเพดาน; `tool_help()` คืน schema ถูกต้อง
- Audit: เรียกเครื่องมือแล้วเกิด log ที่ถูกต้อง + record rule ทำงาน
- Cache: เรียก metadata ซ้ำไม่ยิง query ซ้ำ (พิสูจน์ด้วยการนับ/แคช)
- HTTP endpoints ที่มีอยู่ยังทำงาน (regression)

**คำสั่งรัน (ตาม convention โปรเจกต์)**

```
run-tests.ps1 -Module od19_ai_assistant
```

เป้าหมาย: **0 failed / 0 error** ก่อน commit

---

## 15. โครงสร้างไฟล์ (File Layout)

```
custom_addons/od19_ai_assistant/
├── models/
│   ├── __init__.py
│   ├── od19_ai_chat.py           # เดิม (ปรับให้ใช้ prompt_index + progressive disclosure)
│   ├── od19_ai_tool.py           # เดิม (registry รวม curated + generic)
│   ├── od19_ai_tool_generic.py   # ใหม่: Generic Explorer
│   ├── od19_ai_tool_index.py     # ใหม่: Capability Index + tool_help
│   ├── od19_ai_capability.py     # ใหม่: gate โหมด + draft + audit
│   ├── od19_ai_provider.py       # ใหม่: registry ผู้ให้บริการภายนอก (โครง)
│   ├── od19_ai_tool_log.py       # ใหม่: โมเดล audit
│   ├── res_users.py              # ใหม่: ฟิลด์ od19_ai_capability_mode
│   └── res_config_settings.py    # เดิม (เพิ่มฟิลด์โหมด + ช่องทางภายนอก)
├── lib/
│   ├── client.py                 # เดิม
│   └── orm_guard.py              # ใหม่: domain/field/limit guard
├── controllers/
│   └── main.py                   # เดิม (เพิ่ม route ยืนยัน draft)
├── security/
│   ├── ir.model.access.csv       # เพิ่มสิทธิ์ od19.ai.tool.log
│   └── od19_ai_security.xml      # ใหม่: record rule ของ log
├── views/
│   └── res_config_settings_views.xml  # ปรับ: ฟิลด์โหมด
├── static/src/js/
│   └── od19_ai_chat.js           # เดิม (เพิ่มการ์ดร่าง + ยืนยัน)
└── tests/
    ├── __init__.py
    └── test_ai_assistant.py      # ขยาย
```

---

## 16. ค่าเริ่มต้นที่กำหนดไว้ (Defaults)

| หัวข้อ | ค่าเริ่มต้น |
|---|---|
| โหมดความสามารถ | `read_only` (A) |
| Override รายผู้ใช้ | ตามดีฟอลต์ระบบ |
| Cap ผลลัพธ์ search | ≤ 20 แถว |
| Cap ฟิลด์ describe | ≤ 60 ฟิลด์ |
| Timeout | ตาม `res.config.settings` (local 180s) |
| ผู้ให้บริการภายนอก | ปิดทั้งหมด |
| Operator ที่อนุญาตใน domain | `= != > >= < <= in not in like ilike child_of` |
| Whitelist โมเดลสำหรับ draft (เริ่มต้น) | `sale.order`, `purchase.order`, `account.move` (draft/not posted), `project.task`, `mail.activity` (+ `helpdesk.ticket`, `crm.lead` ถ้าติดตั้ง) |

ค่าเหล่านี้ปรับได้ภายหลังโดยไม่กระทบสถาปัตยกรรม

---

## 17. เหตุผลการตัดสินใจ (Design Decisions)

- **ทำไม Generic + Curated (Hybrid) ไม่เลือกอย่างใดอย่างหนึ่ง:** Generic ให้ความครอบคลุมแบบไม่ต้องเขียนโค้ดต่อโดเมน; Curated ให้ความเร็ว/แม่นกับงานยอดฮิต — รวมกันได้ทั้งสองข้อโดยไม่เสียอย่างใด
- **ทำไม Progressive Disclosure:** เป็นกุญแจด้านประสิทธิภาพ — ครอบคลุมได้ทั้งหมดโดยไม่ทำให้ context ระเบิด
- **ทำไมใช้ prompt-based tool protocol ต่อ:** ให้ทำงานได้กับทุกผู้ให้บริการ OpenAI-compatible (Ollama/Groq/Custom) โดยไม่ผูก vendor
- **ทำไมอ่านด้วยสิทธิ์จริง ไม่ sudo:** ผู้ช่วยต้องไม่กลายเป็นช่องทางข้ามสิทธิ์ (Zero Trust)
- **ทำไม draft ต้องยืนยัน 2 จังหวะ:** กันความผิดพลาดทางการเงิน/บัญชีตามหลัก "ไม่มีการจ่ายเงิน ไม่อนุมัติสินเชื่อ"
- **ทำไมแยกเฟส 1/2/3:** ลดความเสี่ยง พิสูจน์ฐานภายใน Odoo ให้แน่นก่อนต่อภายนอก

---

## 18. ความเสี่ยงและข้อจำกัด (Risks & Limitations)

| # | ความเสี่ยง | ผลกระทบ | แนวทางลด |
|---|---|---|---|
| RS1 | โมเดล 8B เลือก model/field ผิดในการเรียก generic tool | คำตอบคลาดเคลื่อน | curated เป็น fast-path + guard เข้ม + จำกัดผลลัพธ์ |
| RS2 | หลายรอบ tool ทำให้ตอบช้า | ประสบการณ์ผู้ใช้ | โหมด streaming + curated สำหรับงานยอดฮิต + cap รอบ |
| RS3 | exposed โมเดลกว้างเกินไป | ความเสี่ยงด้านสิทธิ์/ข้อมูล | บังคับสิทธิ์จริง + guard + audit + capability mode |
| RS4 | draft ถูกนำไปใช้ผิดวัตถุประสงค์ | ความเสี่ยงทางบัญชี | whitelist + บังคับ draft + ยืนยัน 2 จังหวะ + audit |
| RS5 | cache metadata ล้าสมัยหลังติดตั้ง/อัปเกรดโมดูล | field/model ผิด | ล้าง cache เมื่อ registry reload |
| RS6 | ขยายเครื่องมือเยอะขึ้นเรื่อย ๆ | ภาระดูแล | เน้น generic เป็นหลัก; curated เฉพาะที่คุ้มค่า |

---

## 19. แผนการดำเนินงาน (Implementation Phases)

1. **เฟส 1 (งานนี้) — ครอบคลุมทุกโดเมน Odoo**
   - 1.1 `lib/orm_guard.py` + unit test
   - 1.2 Generic Explorer (`od19_ai_tool_generic.py`)
   - 1.3 Capability Index + Progressive Disclosure (`od19_ai_tool_index.py`)
   - 1.4 Capability Mode + gate + draft + audit (`od19_ai_capability.py`, `od19_ai_tool_log.py`, `res_users.py`)
   - 1.5 Performance Guards (cache/cap/timeout/token budget)
   - 1.6 UI: หน้าตั้งค่าโหมด + การ์ดยืนยัน draft
   - 1.7 Unit Test ครบ + regression
2. **เฟส 2 — อินเทอร์เน็ต:** เปิดใช้ provider ภายนอก (web search/fetch) + คีย์ + สวิตช์
3. **เฟส 3 — ระบบบริษัท:** ต่อ ZKTeco / e-Tax / currency bot / external DB source

---

## 20. สรุป (Conclusion)

การยกระดับนี้เปลี่ยนผู้ช่วย AI จาก "เครื่องมือเฉพาะ 11 ตัว" เป็น **สถาปัตยกรรมแบบมีชั้นที่ครอบคลุมทุกโดเมน Odoo โดยไม่ทำร้ายประสิทธิภาพ** ผ่าน Generic Explorer + Curated Fast-path + Progressive Disclosure พร้อมชั้นความปลอดภัยที่เลือกได้ (อ่านเท่านั้น / อ่าน + ร่างแบบ opt-in) และพร้อมต่อยอดสู่อินเทอร์เน็ตและระบบบริษัทในเฟสถัดไป — ทั้งหมดเป็น additive ไม่แตะ Odoo core
