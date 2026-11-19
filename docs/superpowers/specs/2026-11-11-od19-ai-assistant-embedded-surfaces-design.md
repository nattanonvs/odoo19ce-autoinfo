# เอกสารออกแบบ: ประสบการณ์ผู้ช่วย AI ฝังในหน้าจอใช้งาน (Embedded AI Surfaces) — `od19_ai_assistant`

- **วันที่:** 2026-11-11 (rev0)
- **โมดูลที่แตะ:** พัฒนาต่อยอดโมดูลเดิม `od19_ai_assistant` (ไม่เพิ่มโมดูลใหม่; ไม่แตะ Odoo core)
- **สถานะ:** รอตรวจสอบ (Draft for review)
- **เอกสารก่อนหน้า:** `2026-11-10-od19-ai-assistant-coverage-design.md` (AI Coverage — เฟส 1, merge เข้า `19.0` แล้ว)
- **แนวทางที่เลือก:** คลื่นที่ 1 (Shared Brain) + พื้นผิวแรก 2 ตัว (Form Help Panel + Systray) ในสเปกเดียวกัน

---

## 1. บทสรุป (Summary)

เอกสารก่อนหน้าทำให้ผู้ช่วย AI **"รู้"** ข้อมูลได้ทุกโดเมน (Generic Explorer + Curated Fast-path + Capability Mode)
แต่ยัง **"ไม่ถูกฝัง"** ในการทำงานจริง — ผู้ใช้ต้องออกจากหน้าที่กำลังทำอยู่ เปิดเมนู "แชทผู้ช่วย AI" แล้วพิมพ์อธิบายบริบทเอง

โครงการนี้เปลี่ยนผู้ช่วยจาก **"แอปที่ต้องไปหา"** เป็น **"ผู้ช่วยที่อยู่ตรงหน้าจอที่กำลังทำงาน"** โดย

- แยก **สมองกลาง** (`od19.ai.assistant`) ออกจาก UI — เป็น service ตัวเดียวที่ทุกพื้นผิวเรียกใช้
- ให้ AI **รู้บริบทหน้าจอ** (โมเดล/เอกสาร/มุมมอง ที่กำลังเปิด) โดยส่งขึ้นไปแค่ `model` / `res_id` / `view_type`
- เพิ่ม **2 พื้นผิวแรก**: ปุ่ม AI บน systray (ใช้ได้ทุกหน้า) และแผงช่วยเหลือข้างฟอร์ม (รู้ว่ากำลังเปิดเอกสารอะไร)

**เป้าหมายเชิงผลลัพธ์**

- เปิดฟอร์มใดก็ได้แล้วถามได้ทันที โดยไม่ต้องบอก AI ว่า "กำลังดูอะไรอยู่"
- พื้นผิวใหม่ในอนาคตเพิ่มได้โดย **ไม่ต้องแตะ tool loop อีกเลย** — เรียก `assistant.ask(...)` พร้อม context
- แชทหน้าเต็มเดิมทำงานเหมือนเดิม 100% (regression)
- ไม่แตะ XML view ของโมดูลอื่นแม้แต่ไฟล์เดียว จึงสอดคล้องข้อกำหนด "ห้ามแก้ core"

---

## 2. สภาพปัจจุบันและช่องว่าง (Problem)

### 2.1 สิ่งที่มีอยู่แล้ว

| กลไก | สถานะ | หมายเหตุ |
|---|---|---|
| `od19.ai.tool` — registry + Curated 11 ตัว + Generic 4 ตัว | มี | ของเดิม ไม่แตะ |
| `od19.ai.capability` — โหมด A/B + gate draft + audit | มี | ของเดิม ไม่แตะ |
| `lib/orm_guard.py` — ตรวจ domain/field/limit | มี | ของเดิม ไม่แตะ |
| `lib/client.py` — `chat_completion` / `chat_completion_stream` | มี | ของเดิม ไม่แตะ |
| `od19.ai.chat` — config resolution + tool loop | มี | **มี loop อยู่ในตัว** |
| `controllers/main.py` — routes + SSE streaming | มี | **มี loop ซ้ำอีกชุด** (`_stream_answer`) |
| OWL client action `od19_ai_assistant.chat` | มี | หน้าเต็มจอ (แยกจากงานที่ทำอยู่) |

### 2.2 ช่องว่างเทียบกับความต้องการ

| # | ประเด็น | สภาพปัจจุบัน | ผลกระทบ |
|---|---|---|---|
| G1 | AI อยู่ที่เดียว | ต้องเปิด client action แชทเสมอ | ไม่ได้ "ช่วยในหน้าที่กำลังทำ" |
| G2 | ไม่รู้บริบทหน้าจอ | ผู้ใช้ต้องพิมพ์อธิบายเองว่าเอกสารไหน | ใช้งานจริงไม่สะดวก |
| G3 | tool loop ถูกเขียนซ้ำ 2 ที่ | `od19.ai.chat.action_ask` และ `_stream_answer` ใน controller | แก้ที่หนึ่งลืมอีกที่ → บั๊กเงียบ |
| G4 | พื้นผิวใหม่ผูกกับ UI | ต้องเขียน loop ใหม่ทุกครั้งที่เพิ่มช่องทาง | ต้นทุนเพิ่มแบบทวีคูณ |

> G3 ยืนยันจากโค้ดจริง: `custom_addons/od19_ai_assistant/models/od19_ai_chat.py` ประกาศ `MAX_TOOL_ROUNDS = 5` และมี loop ใน `action_ask`
> ขณะที่ `custom_addons/od19_ai_assistant/controllers/main.py` `import MAX_TOOL_ROUNDS` ข้ามไฟล์มาใช้ใน `_stream_answer` โดยประกอบ prompt เองอีกชุด

---

## 3. ความต้องการ (Requirements)

- **R1** ต้องมี **สมองกลางตัวเดียว** (`od19.ai.assistant`) ที่ทำหน้าที่ประกอบ prompt + tool loop + guard + audit — ไม่มี UI
- **R2** สมองกลางต้องรับ **บริบทหน้าจอ** ได้ และต้องเป็น **optional** (ไม่ส่งมาก็ยังทำงานได้เหมือนเดิม)
- **R3** บริบทต้องถูก **resolve ฝั่ง server** ด้วยสิทธิ์จริงของผู้ใช้ (ไม่ sudo) — client ส่งขึ้นไปได้แค่ `model`, `res_id`, `view_type`
- **R4** ถ้าผู้ใช้ไม่มีสิทธิ์อ่าน record นั้น → คืน `None` ไม่ throw ไม่ leak
- **R5** ต้องมี **ปุ่ม AI บน systray** ใช้ได้ทุกหน้า และรู้บริบทหน้าปัจจุบัน
- **R6** ต้องมี **แผงช่วยเหลือข้างฟอร์ม** ที่แสดงเฉพาะเมื่ออยู่ในมุมมองฟอร์มที่มีเอกสารจริง
- **R7** ทั้งสองพื้นผิวต้อง **ใช้ UI component ตัวเดียวกัน** (ไม่เขียนซ้ำ)
- **R8** ต้องมี **ชิปคำสั่งด่วนตามบริบท** เพื่อลดการพิมพ์
- **R9** **ห้ามแก้ XML view ของโมดูลอื่น** และห้ามแตะ Odoo core — ใช้ registry ของ web client เท่านั้น
- **R10** `od19.ai.chat.action_ask` ต้องมี **พฤติกรรมเดิม** (regression ผ่าน 0 failed / 0 error)
- **R11** ต้องมี Unit Test ครอบคลุม logic ใหม่ + regression
- **R12** ความปลอดภัยเท่าเดิม: โหมด `read_only` เป็นดีฟอลต์, draft ต้อง opt-in + ยืนยัน 2 จังหวะ, AI ห้ามอนุมัติ/จ่ายเงิน

---

## 4. ขอบเขต (Scope)

### 4.1 ในขอบเขต (สเปกนี้)

1. สมองกลาง `od19.ai.assistant` + ย้าย loop/config/prompt protocol เข้าไป
2. `od19.ai.chat` และ `controllers/main.py` เปลี่ยนไปเรียกสมองกลาง (พฤติกรรมผู้ใช้ไม่เปลี่ยน)
3. การส่งบริบทหน้าจอจาก client → server (`ai_context.js`)
4. Systray item + แผงแชทขนาดเล็ก (`ai_panel.js`) — ใช้ร่วมกับข้อ 5
5. Form Help Panel ผ่าน `registry.category("main_components")`
6. `suggest_actions(ctx)` — ชิปคำสั่งด่วนตามบริบท
7. Unit Test + regression

### 4.2 นอกขอบเขต (คลื่นถัดไป)

- **W2** ช่วยร่างค่าฟิลด์, สรุป Chatter, กรองลิสต์ด้วยภาษาไทย
- **W3** ต่อ AI กับ `od19_user_guide_tours` (AI อธิบาย + เปิดทัวร์/พาไปทำจริง)
- **W4** เชิงรุก (เตือน/วิเคราะห์เอง) + เฟส 2 อินเทอร์เน็ต + เฟส 3 ระบบบริษัท (ZKTeco / e-Tax)
- การเขียน/ยืนยันเอกสารจริง (post/confirm/pay/approve) — **ห้ามเด็ดขาด ทุกคลื่น**

### 4.3 โครงการโดยรวม (4 คลื่น)

| คลื่น | เนื้อหา | สถานะ |
|---|---|---|
| W1 | Shared Brain + 2 พื้นผิวแรก | **สเปกนี้** |
| W2 | Embedded Surfaces ที่เหลือ | ยังไม่เริ่ม |
| W3 | Teaching & Guidance (ต่อกับ Tours) | ยังไม่เริ่ม |
| W4 | Proactive + External Providers | ยังไม่เริ่ม |

---

## 5. สถาปัตยกรรม (Architecture)

### 5.1 ภาพรวม

```
 ┌───────────────── พื้นผิว (client / OWL) ─────────────────┐
 │  [แชทหน้าเต็มเดิม]   [ปุ่ม systray]   [แผงข้างฟอร์ม]      │
 │         │                 └──────┬───────┘               │
 │         │                   ai_panel.js (ใช้ร่วม)         │
 │         │                        │                        │
 │         │                   ai_context.js ──► {model,     │
 │         │                        │             res_id,    │
 │         │                        │             view_type} │
 └─────────┼────────────────────────┼────────────────────────┘
           │  SSE /od19_ai/chat/stream        │ JSON /od19_ai/ask
           ▼                                  ▼
 ┌──────────────────── controllers/main.py (transport) ────────────────────┐
 │  auth=user · ไม่มี loop · ไม่มี prompt logic                            │
 └───────────────────────────────┬─────────────────────────────────────────┘
                                 ▼
 ┌──────────────── od19.ai.assistant  (สมองกลาง — AbstractModel) ──────────┐
 │  build_context()  context_brief()  ask()  stream()  confirm_draft()     │
 │  ┌──────────────────────────────────────────────────────────────────┐  │
 │  │  system prompt  =  base + TOOL_PROTOCOL + prompt_index()  + ctx   │  │
 │  │  loop ≤ MAX_TOOL_ROUNDS  →  od19.ai.tool.execute()                │  │
 │  └──────────────────────────────────────────────────────────────────┘  │
 └───────┬──────────────────────────┬──────────────────────────┬──────────┘
         │                          │                          │
         ▼                          ▼                          ▼
   od19.ai.tool              od19.ai.capability            orm_guard
   (execute)                 (โหมด A/B + gate)             (domain/field/limit)
         └──────────────────────────┴──────────────────────────┘
                                    ▼
                          Odoo ORM (สิทธิ์ผู้ใช้จริง) ──► od19.ai.tool.log (audit)
```

### 5.2 หลักการออกแบบ

- **แยก "สมอง" ออกจาก "ช่องทาง"** — controllers เหลือหน้าที่ transport เท่านั้น
- **บริบทเป็น optional parameter** — ไม่ส่งมา = พฤติกรรมเดิมเป๊ะ (ทำให้ regression ตรวจได้ง่าย)
- **Server เป็นผู้เชื่อบริบท** — ไม่เชื่อสิ่งที่ client ส่งมา นอกจาก "ชี้เป้า" เป็น model + res_id
- **Additive เท่านั้น** — ใช้ registry ของ web client ไม่แก้ view/ไฟล์ของโมดูลอื่น
- **1 หน่วย = 1 หน้าที่** — tool = executor, assistant = orchestrator, chat = persistence, controller = transport

---

## 6. อินเทอร์เฟซสมองกลาง (Shared Brain API)

`od19.ai.assistant` เป็น `models.AbstractModel` เรียกผ่าน `self.env["od19.ai.assistant"]` — ไม่มีตาราง ไม่มี UI

| เมธอด | อินพุต | เอาต์พุต | หน้าที่ |
|---|---|---|---|
| `build_context(model, res_id, view_type, snippet=None)` | ระบุเป้าหมาย | `dict \| None` | ตรวจสิทธิ์ + อ่านค่าจริง → บริบท |
| `context_brief(ctx, max_chars=800)` | บริบท | `str` | ย่อบริบทเป็นข้อความต่อท้าย system prompt |
| `ask(question, ctx=None, chat=None)` | คำถาม | `str` | tool loop แบบตอบทีเดียว (systray / panel) |
| `stream(question, ctx=None, chat=None)` | คำถาม | iterator | tool loop แบบ SSE (แชทหน้าเต็ม / panel) |
| `confirm_draft(model, values)` | ร่าง | record | ยืนยันจังหวะที่ 2 (พฤติกรรมเดิม) |
| `suggest_actions(ctx)` | บริบท | `list[str]` | ชิปคำสั่งด่วน |

**สิ่งที่ย้ายเข้าไปอยู่ที่เดียว**

`TOOL_PROTOCOL`, `MAX_TOOL_ROUNDS`, `PROVIDER_PRESETS`, `DEFAULTS`, `_get_param()`, `_get_ai_config()`,
`_build_system_prompt()`, `_parse_tool_call()`, `_build_messages()` และตัว loop

**สิ่งที่ไม่ย้าย (คงไว้ที่เดิมและไม่แตะ)**

`od19.ai.tool` (execute + prompt_index + tool_help), `od19.ai.capability` (โหมด/gate/audit), `lib/orm_guard.py`, `lib/client.py`

**ความเข้ากันได้ย้อนหลัง**

`od19.ai.chat.action_ask()` ยังคงเป็น method เดิมที่ UI เดิมเรียก — ข้างในเปลี่ยนไปเรียก `assistant.ask(question, chat=self)` เท่านั้น

---

## 7. บริบทหน้าจอ (Page Context)

### 7.1 สัญญาข้อมูล (contract)

```json
{ "model": "res.partner", "res_id": 42, "view_type": "form" }
```

- `list` → มี `model`, ไม่มี `res_id`
- ไม่ใช่มุมมองข้อมูล (เช่น หน้า Settings, Dashboard) → `null`
- **ไม่ส่งค่าฟิลด์หรือเนื้อหาข้อมูลขึ้นไปเลย**

### 7.2 การอ่านฝั่ง client (`ai_context.js`)

```js
getPageContext(env) // -> { model, res_id, view_type } | null
```

อ่านจาก `env.services.action.currentController` (ยืนยันแล้วว่ามีใน Odoo 19 ของโปรเจกต์นี้) เป็นศูนย์กลาง **จุดเดียว** ที่ผูกกับ web client — ถ้า Odoo เปลี่ยน API ในอนาคต แก้ที่ไฟล์นี้ไฟล์เดียว

### 7.3 การสร้างบริบทฝั่ง server

`build_context()` ทำตามลำดับ:

1. โมเดลติดตั้งอยู่จริงหรือไม่ (`ir.model`)
2. `check_access_rights("read")` บนโมเดล
3. `browse(res_id).exists()` + `check_access_rule("read")` บนเรกคอร์ด
4. ถ้าผ่าน → ประกอบ `display_name`, `view_type`, รายชื่อฟิลด์ที่แสดง (จำกัดจำนวน), `snippet` (ตัดที่ N ตัวอักษร)
5. ถ้าไม่ผ่านข้อใด → คืน `None` (ไม่ throw, ไม่บอกใบ้ว่ามีข้อมูลอยู่)

---

## 8. พื้นผิว (Surfaces)

### 8.1 ปุ่ม AI บน systray

```js
registry.category("systray").add("od19_ai_assistant.ai_button", {...}, { sequence: 50 })
```

- ใช้ได้ทุกหน้า ไม่ผูกกับ action
- คลิก → เปิด/ปิด **แผงแชทขนาดเล็ก** ลอยมุมขวา
- ทุกครั้งที่ส่งคำถาม จะแนบบริบทปัจจุบันอัตโนมัติ → เปลี่ยนหน้าแล้วถามต่อได้โดยไม่ต้องอธิบายใหม่

### 8.2 แผงช่วยเหลือข้างฟอร์ม

```js
registry.category("main_components").add("od19_ai_assistant.FormHelpPanel", {...})
```

- เลือก `main_components` **โดยเจตนา** เพราะ
  - ครอบทุกฟอร์มของทุกโมดูลโดยอัตโนมัติ
  - **ไม่ต้องแก้ XML view ของโมดูลอื่นแม้แต่ไฟล์เดียว** (ตรงข้อกำหนด R9)
- แสดงเฉพาะเมื่อ `view_type === "form"` และมี `res_id`
- เปิด/ปิดได้จากปุ่มใน systray หรือคีย์ลัด (`Alt+Shift+A` — ต้องตรวจการชนกับ hotkey ของเมนู navbar ก่อนสรุปค่า)
- จำสถานะเปิด/ปิดไว้ต่อผู้ใช้ (`localStorage`)

### 8.3 แผง UI ที่ใช้ร่วมกัน (`ai_panel.js`)

component ตัวเดียวใช้ทั้ง 2 พื้นผิว — ต่างกันแค่ตำแหน่งวางและขนาด จึงไม่มี UI ซ้ำสองชุด
รองรับ: สตรีมคำตอบ, แสดงชิปเครื่องมือที่ถูกเรียก, และการ์ดยืนยันร่าง (โหมด B) เหมือนแชทเดิม

### 8.4 ชิปคำสั่งด่วนตามบริบท

`suggest_actions(ctx) -> list[str]` — ตาราง mapping เล็ก ๆ ต่อโมเดลที่ใช้บ่อย + ชิปกลางเมื่อไม่รู้จักโมเดล
เช่น ฟอร์มใบสั่งขาย → "สรุปออร์เดอร์นี้" / "ลูกค้ารายนี้ซื้ออะไรบ้าง" / "ทำไมสถานะยังไม่ยืนยัน"
กดชิป = ส่งคำถามทันที (ลดการพิมพ์ตามหลัก "ขั้นตอนน้อยที่สุดแต่ข้อมูลครบถ้วน")

---

## 9. ความปลอดภัย (Security)

| ประเด็น | มาตรการ |
|---|---|
| สิทธิ์การอ่าน | resolve ด้วยสิทธิ์จริงของผู้ใช้ **ไม่ `sudo`** — ไม่มีสิทธิ์ = `None` |
| การปลอมบริบท | client ส่งได้แค่ `model`/`res_id`/`view_type`; ค่าจริงอ่านฝั่ง server |
| โหมดความสามารถ | `read_only` (A) เป็นดีฟอลต์; `read_draft` (B) ต้อง opt-in รายผู้ใช้ |
| การร่าง | whitelist โมเดล + บังคับสถานะ draft + **ยืนยัน 2 จังหวะโดยมนุษย์** |
| ห้ามเด็ดขาด | ไม่มีเส้นทางสู่ post / confirm / pay / approve — "ไม่มีการอนุมัติสินเชื่อ ไม่มีการจ่ายเงิน" |
| Audit | ทุก tool call ลง `od19.ai.tool.log` (เดิม) + เพิ่มร่องรอยบริบทต้นทางต่อข้อความ |
| ความเป็นส่วนตัวของบริบท | จำกัดขนาดด้วย `max_chars` / snippet cap; ไม่ log ข้อมูลอ่อนไหว |
| ความโปร่งใสเรื่องที่ตั้งโมเดล | แสดงบนแผงชัดเจนว่าคำถามจะออกนอกเครื่องหรือไม่ (Ollama = local, Groq = cloud) |

---

## 10. ประสิทธิภาพ (Performance)

| กลไก | รายละเอียด |
|---|---|
| ไม่มีงานตอน idle | ไม่มี cron / worker เบื้องหลัง — แผงถูกสร้างเมื่อเปิดเท่านั้น |
| บริบทมีเพดาน | `max_chars` + ตัดจำนวนฟิลด์ + snippet cap |
| ไม่ยิง query ซ้ำ | ดึงบริบทครั้งเดียวต่อการส่ง 1 ครั้ง; ไม่ re-fetch ตอน re-render |
| สตรีมคำตอบ | ใช้ SSE เดิม ไม่รอทั้งก้อน |
| ไม่แตะ asset ของโมดูลอื่น | เพิ่มไฟล์ใน `web.assets_backend` ของโมดูลตัวเองเท่านั้น |

---

## 11. การไหลของข้อมูล (Data Flow)

1. ผู้ใช้เปิดฟอร์มลูกค้า → `ai_context.js` อ่านได้ `{res.partner, 42, form}`
2. ผู้ใช้กดปุ่ม systray / เปิดแผงข้าง → เปิด `ai_panel.js`
3. ผู้ใช้กดชิปคำสั่งด่วน หรือพิมพ์คำถาม → ส่ง `POST /od19_ai/ask` พร้อมบริบท
4. controller ตรวจ `auth="user"` → ส่งต่อ `assistant.ask(question, ctx)`
5. `build_context()` ตรวจสิทธิ์ + อ่าน `display_name`/ฟิลด์ที่แสดง → ประกอบ `context_brief()`
6. ประกอบ system prompt (base + TOOL_PROTOCOL + `prompt_index()` + บริบท) แล้วเข้า tool loop
7. ทุกการเรียกเครื่องมือ → ผ่าน `capability` gate + `orm_guard` → เขียน audit log
8. ได้คำตอบ → สตรีมกลับแผง (ถ้าเป็น draft → ส่งการ์ดยืนยันก่อนสร้าง)
9. แชทหน้าเต็มใช้เส้นทางเดิม (`/od19_ai/chat/stream`) แต่เรียกสมองกลางตัวเดียวกัน

---

## 12. โครงสร้างไฟล์ (File Layout)

```
custom_addons/od19_ai_assistant/
├── models/
│   ├── od19_ai_assistant.py      # ใหม่: สมองกลาง (AbstractModel)
│   ├── od19_ai_chat.py           # แก้: บางลง — เรียกสมองกลาง
│   └── __init__.py               # แก้
├── controllers/
│   └── main.py                   # แก้: เหลือ transport + เพิ่ม /od19_ai/ask
├── static/src/
│   ├── js/
│   │   ├── ai_context.js         # ใหม่: อ่านบริบทหน้าจอ
│   │   ├── ai_panel.js           # ใหม่: แผงแชทขนาดเล็ก (ใช้ร่วม)
│   │   ├── systray_item.js       # ใหม่: ปุ่ม AI
│   │   └── od19_ai_chat.js       # เดิม (ไม่เปลี่ยนพฤติกรรม)
│   ├── xml/
│   │   ├── ai_panel.xml          # ใหม่
│   │   └── systray_item.xml      # ใหม่
│   └── scss/                     # ใหม่: สไตล์แผง (ถ้าจำเป็น)
├── tests/
│   ├── test_ai_assistant_service.py  # ใหม่
│   ├── test_ai_context.py            # ใหม่
│   └── test_ai_assistant.py          # เดิม (regression)
└── __manifest__.py               # แก้: assets + bump 19.0.3.0.0
```

---

## 13. การทดสอบ (Testing)

**Unit — Python** (รันบน DB ทดสอบส่วนตัว + พอร์ตแยก ตาม AGENTS.md §6)

`test_ai_context.py`
- ผู้ใช้มีสิทธิ์อ่าน record → ได้บริบทครบ + `display_name` ถูกต้อง
- ผู้ใช้ไม่มีสิทธิ์อ่าน → `None` (ไม่ throw)
- `res_id` ไม่มีอยู่จริง → `None`
- `context_brief()` ตัดความยาวตาม `max_chars`

`test_ai_assistant_service.py` (stub `chat_completion`)
- ตอบตรงโดยไม่เรียกเครื่องมือ → ได้คำตอบ
- เรียกเครื่องมือ 1 รอบแล้วตอบ → เกิด log 1 รายการ + คำตอบถูกต้อง
- วนเกิน `MAX_TOOL_ROUNDS` → ได้ข้อความขอให้ถามเจาะจงขึ้น
- error path → บันทึกข้อความผิดพลาดแต่ไม่ rollback

`test_ai_assistant.py` (เดิม — regression)
- `od19.ai.chat.action_ask` ให้ผลเหมือนก่อน refactor

**ทดสอบมือ 1 รอบ**
- เปิดฟอร์มลูกค้า → กดปุ่ม AI บน systray → ถาม "ลูกค้ารายนี้เป็นใคร" → คำตอบต้องอ้างถึงเอกสารที่เปิดอยู่จริง
- ตรวจว่าแชทหน้าเต็มเดิมยังใช้งานได้ตามปกติ

**คำสั่งรัน**

```
run-tests.ps1 -Module od19_ai_assistant
```

เป้าหมาย: **0 failed / 0 error** ก่อน commit

---

## 14. ค่าเริ่มต้นที่กำหนดไว้ (Defaults)

| หัวข้อ | ค่าเริ่มต้น |
|---|---|
| คีย์ลัดเปิด/ปิดแผงข้าง | `Alt+Shift+A` (ยืนยันหลังตรวจการชน) |
| สถานะแผงข้าง | ปิด (จำค่าต่อผู้ใช้) |
| โหมดความสามารถ | `read_only` (A) |
| เพดานบริบท | `max_chars = 800`, ฟิลด์ที่ส่ง ≤ 30, snippet ≤ 500 ตัวอักษร |
| ลำดับปุ่ม systray | `sequence = 50` |
| จำนวนชิปคำสั่งด่วน | ≤ 4 |

ค่าเหล่านี้ปรับได้ภายหลังโดยไม่กระทบสถาปัตยกรรม

---

## 15. เหตุผลการตัดสินใจ (Design Decisions)

- **ทำไมต้องแยกสมองกลางก่อนทำพื้นผิว:** ถ้าเพิ่มพื้นผิวโดย loop ยังซ้ำอยู่ จะกลายเป็น 3–4 ชุดที่ต้องแก้พร้อมกัน — แยกก่อนแล้วพื้นผิวถัดไปเป็นงานเล็ก
- **ทำไมทำ W1 คู่กับพื้นผิวแรก (ไม่ทำ W1 เปล่า ๆ):** การ refactor ที่ไม่มีผู้ใช้จริงพิสูจน์ไม่ได้ว่าถูก — มีพื้นผิวเป็นตัวบังคับให้อินเทอร์เฟซสมองกลาง "จริง"
- **ทำไมใช้ `main_components` ไม่ใช้ view inheritance:** ครอบทุกฟอร์มอัตโนมัติ และไม่ต้องแก้ XML ของโมดูลอื่น (R9)
- **ทำไม client ส่งแค่ model/res_id/view_type:** ลดพื้นที่โจมตี — server ต้องเป็นผู้ตัดสินใจเรื่องสิทธิ์เสมอ (Zero Trust)
- **ทำไมบริบทเป็น optional:** ทำให้ regression ตรวจได้ตรง ๆ ว่าไม่มีพฤติกรรมเดิมเปลี่ยน
- **ทำไมยังใช้ prompt-based tool protocol:** คงความ model-agnostic (Ollama/Groq/Custom) ตามสเปกเดิม

---

## 16. ความเสี่ยงและข้อจำกัด (Risks & Limitations)

| # | ความเสี่ยง | ผลกระทบ | แนวทางลด |
|---|---|---|---|
| RS1 | web client API เปลี่ยนในอนาคต → อ่านบริบทพัง | ปุ่ม AI เงียบ | รวมการอ่านบริบทไว้ `ai_context.js` ที่เดียว + คืน `null` แทน throw |
| RS2 | แผงข้างทับพื้นที่ทำงาน | ไม่สะดวก | ดีฟอลต์ปิด + จำค่าผู้ใช้ + เปิด/ปิดด้วยคีย์ลัด |
| RS3 | refactor สมองกลางทำแชทเดิมพัง | งานที่ใช้อยู่เสีย | เทสต์ regression ของ `action_ask` เป็นด่านบังคับก่อน commit |
| RS4 | บริบทที่ส่งไประบบคลาวด์มีข้อมูลลูกค้า | ความเป็นส่วนตัว | จำกัดขนาด/ฟิลด์ + แสดงชัดว่าใช้ local หรือ cloud |
| RS5 | คีย์ลัดชนกับ hotkey ของเมนู navbar | กดแล้วได้อย่างอื่น | ตรวจก่อนสรุปค่า; ถ้าชนให้เปลี่ยน |
| RS6 | โมเดล 8B ใช้บริบทผิด | คำตอบคลาดเคลื่อน | ชิปคำสั่งด่วนเฉพาะทาง + curated fast-path เดิม |

---

## 17. แผนการดำเนินงาน (Implementation Plan ภายในสเปกนี้)

1. `od19_ai_assistant.py` — สมองกลาง + ย้าย loop/config/prompt protocol + unit test
2. `od19_ai_chat.py` + `controllers/main.py` — เปลี่ยนไปเรียกสมองกลาง + regression test
3. `ai_context.js` + endpoint `build_context` ผ่าน `/od19_ai/ask` + unit test
4. `ai_panel.js` + `ai_panel.xml` — แผง UI ใช้ร่วม
5. `systray_item.js` + `systray_item.xml` — ปุ่ม AI ทุกหน้า
6. Form Help Panel ผ่าน `main_components`
7. `suggest_actions()` + ชิปคำสั่งด่วน
8. Unit test ครบ + ทดสอบมือ 1 รอบ + ตรวจว่าไม่แตะ view ของโมดูลอื่น

---

## 18. สรุป (Conclusion)

สเปกนี้ทำให้ผู้ช่วย AI เปลี่ยนจาก "แอปที่ต้องไปเปิด" เป็น "ผู้ช่วยที่อยู่ตรงหน้าจอที่กำลังทำงาน" โดย
แยก **สมองกลาง** ออกมาให้ทุกพื้นผิวใช้ร่วม แล้วเพิ่ม **2 พื้นผิวแรก** (systray ทุกหน้า + แผงข้างฟอร์ม) ด้วยการ
อ่านบริบทหน้าจอที่ **server เป็นผู้ตรวจสิทธิ์เสมอ**

ผลลัพธ์คือ W2–W4 จะกลายเป็นงาน "เพิ่มพื้นผิว" ที่ไม่ต้องแตะ loop อีก — ทั้งหมดยังเป็น additive ไม่แตะ Odoo core
และคงหลักความปลอดภัยเดิม: ดีฟอลต์อ่านเท่านั้น, ร่างต้องยืนยัน 2 จังหวะ, ไม่มีการอนุมัติหรือจ่ายเงินโดย AI
