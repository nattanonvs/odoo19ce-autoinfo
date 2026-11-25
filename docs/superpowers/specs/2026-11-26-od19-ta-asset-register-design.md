# เอกสารออกแบบ: รวมระบบ TA Asset Register เข้า Odoo 19 CE (AutoInfo)

- **วันที่:** 2026-11-26
- **รหัสงาน:** OD19-TA-ASSET
- **โมดูลที่เสนอสร้างใหม่:** `od19_ta_asset` (ทะเบียนสินทรัพย์ ATG) · `od19_ta_service` (งานบริการ/ประวัติอุปกรณ์) · `od19_ta_portal` (พอร์ทัลลูกค้า + รายงาน ATG)
- **โมดูลที่เกี่ยวข้อง (มีอยู่แล้ว จะ integrate):** `od19_project_enhanced`, `od19_sales_project_context`, `od19_service_contract`, `od19_service_warranty`, `od19_contacts_partner_roles`, `od19_partner_thai_fields`, `od19_iso_calibration`, `od19_quality_control`, `od19_document_hub`, `od19_billing_request`, `od19_role_catalog`, `od19_dashboard`
- **สถานะ:** ข้อเสนอทิศทาง (design proposal) — ยังไม่เริ่มเขียนโค้ด
- **ผู้เกี่ยวข้อง:** แผนก TA (Service/Engineer), ฝ่ายขาย (Sales), ฝ่ายบัญชี, ฝ่ายไอที–แอดมิน, ลูกค้า (ผ่านพอร์ทัล)
- **ข้อตัดสินใจที่ล็อกแล้ว (2026-11-26):**
  - **K1** TA Asset Register = **ส่วนขยายของ Odoo** ไม่ใช่ระบบแยก — 1 ระบบเดียว
  - **K2** ใช้ `res.partner` แทนตาราง Companies เดิม และใช้ `project.project` แทนตาราง Jobs เดิม
  - **K3** สร้างโมเดลใหม่เฉพาะของโดเมน ATG จริง ๆ: Plant / Tank / Equipment (ทะเบียนอุปกรณ์) / Event (ประวัติ)
  - **K4** โมดูล prefix `od19_ta_*` ตาม convention ของ repo; **ไม่แตะ Odoo core** และ **ไม่แตะ `third_party/oca/`**
  - **K5** เอกสารนี้ + Data Mapping (Excel) เก็บที่ `docs/superpowers/specs/`

---

## 1. บทสรุป (Summary)

ปัจจุบันแผนก TA ใช้ระบบ **"TA Asset Register"** เป็นเว็บแอปแยก (Flask + waitress, พอร์ต 5000, host ในวง LAN) สำหรับบันทึกว่า **อุปกรณ์วัดระดับ/อุณหภูมิอัตโนมัติ (ATG)** ถูกติดตั้งที่ **ถัง/Plant ของลูกค้ารายใด** และมี **ประวัติการทำงาน (PM, ติดตั้ง, สอบเทียบ, ซ่อม, เปลี่ยนอะไหล่)** อย่างไร

ระบบนี้ทำงาน **คู่ขนาน** กับ Odoo (มีฟิลด์เชื่อมอยู่แล้ว: `companies.odoo_ref`, `equipment.odoo_job_no`, `jobs.odoo_stage`) แต่การแก้ไขทำ **2 ที่** → ข้อมูลไม่ตรงกัน, ต้องคีย์ซ้ำ, ไม่มี single source of truth

งานนี้จึง **ผนวกระบบ TA Asset Register เข้าเป็นส่วนหนึ่งของ Odoo 19** โดย:

- **Companies → `res.partner`** (ลูกค้า/เจ้าของไซต์) ใช้ฟิลด์มาตรฐาน + ฟิลด์ไทยที่มีอยู่ (`od19_partner_thai_fields`)
- **Jobs → `project.project`** (งาน/โปรเจกต์) — stage เดิม (SALES/PM/SERVICE) map กับ project stage
- **Plant / Tank / Equipment / Event → โมเดลใหม่ `od19.ta.*`** เฉพาะโดเมน ATG ที่ Odoo core ไม่มี
- **ประวัติอุปกรณ์** ผูกกับ maintenance/service/warranty ที่มีอยู่ เพื่อให้ warranty, ใบเสนอราคา, ใบวางบิล ทำงานร่วมกันได้

**เป้าหมายเชิงผลลัพธ์**

- เห็น "ลูกค้า → Plant → ถัง → อุปกรณ์ ATG → ประวัติ" ได้ใน Odoo ที่เดียว
- ฝ่ายขายเห็นว่าไซต์นี้มี ATG รุ่นอะไร หมดประกันเมื่อไร → ต่อยอดงาน PM/เปลี่ยนทดแทนได้
- วิศวกรบันทึกงาน (event) ที่หน้างานแล้วเชื่อมกับ Job/ใบวางบิลทันที
- รายงาน ATG coverage (เช่น % ถังที่มี ATG ต่อ Plant/ลูกค้า) ต่อยอดเป็น dashboard
- เลิกคีย์ซ้ำ 2 ระบบ — ย้ายข้อมูลเดิมเข้าครั้งเดียว (one-time migration)

---

## 2. สภาพปัจจุบัน (Current State) — ผลจาก P0 Discovery

ดึง schema + ข้อมูลจริงจากระบบ TA Asset Register (อ้างอิง: ไฟล์ export 2026-11-26, 7 ชีต, รวม ~12,353 แถว)

### 2.1 ตาราง/หน้าจอทั้งหมด (Routes ที่ยืนยัน)

| หน้าจอ | Route | เนื้อหา |
|---|---|---|
| ภาพรวม | `/` | KPI + ตารางสรุปกลุ่มธุรกิจ→บริษัท→Plant→ATG |
| ลูกค้า | `/companies` | รายชื่อบริษัท + parent + ประเภท + กลุ่มธุรกิจ |
| Plant | `/plants` | ไซต์/คลัง + เจ้าของ + ระบบ + จำนวนถัง/อุปกรณ์ |
| ถัง | (ต่อ Plant) | ถังในแต่ละ Plant |
| อุปกรณ์ | `/equipment` | ทะเบียน ATG ทุกชิ้น + ที่ติดตั้ง + สถานะ + ประกัน |
| Job | `/jobs` | งาน/โปรเจกต์ + ลูกค้า + Plant + ประเภทงาน |
| ประวัติ | (event) | ประวัติงานต่ออุปกรณ์/Plant/ถัง |
| ผู้ติดต่อ | `/contacts` | ผู้ประสานงานลูกค้า |
| ผู้ใช้ | `/users` | บัญชี + สิทธิ์ (admin/engineer/viewer) |
| Audit | `/audit` | log การแก้ไข |
| รายงาน ATG | `/reports/atg` | % ถังที่มี ATG |
| นำเข้า/ส่งออก | `/data` | export/template/import(dry_run)/backup |

### 2.2 ปริมาณข้อมูลจริง (2026-11-26)

| ตาราง | จำนวนแถว | คอลัมน์ |
|---|---:|---:|
| Companies | 87 | 14 |
| Plants | 84 | 18 |
| Tanks | 1,230 | 8 |
| Equipment | 2,280 | 24 |
| Jobs | 526 | 14 |
| Contacts | 2 | 7 |
| History (read-only) | 8,144 | 10 |

### 2.3 ฟิลด์เชื่อม Odoo ที่มีอยู่แล้ว (สำคัญ)

ระบบเดิม **เตรียมสะพานไป Odoo ไว้แล้ว** — ยืนยันจาก schema:

| ตารางเดิม | ฟิลด์ | ความหมาย |
|---|---|---|
| Companies | `odoo_ref` | รหัสลูกค้า Odoo |
| Equipment | `odoo_job_no` | Job No. ที่จำหน่ายอุปกรณ์ (เช่น `JT24009`) |
| Jobs | `odoo_stage` | Stage ใน Odoo (`SALES`/`PM`/`SERVICE`/`JOB`/`DONE`) |
| Jobs | `notes` | "นำเข้าจากรายการ Project ใน Odoo (15/11/2026)" — Jobs เดิม **import จาก Odoo Project** |

> **นัยสำคัญ:** ข้อมูล Jobs ส่วนใหญ่ถูกดึงมาจาก Odoo อยู่แล้ว → `project.project` คือปลายทางที่ถูกต้อง ไม่ต้องสร้างโมเดล Job ใหม่

### 2.4 ลักษณะข้อมูลที่ต้องระวัง (Data Quality)

| ประเด็น | ตัวอย่าง | การจัดการตอนย้าย |
|---|---|---|
| แถวหัวตารางปนเข้ามา 1 แถว/ชีต | เช่น `company_type = "ประเภท (end_user/...)"` | กรองแถว header ออก (1 แถว/ชีต) |
| วันที่เพี้ยน/อนาคต | History มี `event_date = 2029-...` | เก็บตามจริง + ตั้ง `date_uncertain` flag หรือตรวจภายหลัง |
| แยกแถวด้วย comma หลายค่า | `Jobs.plant_codes`, `Jobs.tank_tags`, `Plants.aliases` | แยกเป็น m2m / line |
| ค่า enum หลากหลายไม่ปกติ | `tank_type` มี ~20 ค่าเขียนต่างกัน | map เข้า selection มาตรฐาน + เก็บค่าดิบใน notes |
| วันที่เป็น `datetime` มี `00:00:00` | `start_date` | cast เป็น `date` |
| merge/รวมบริษัท | Companies `merged_into` / `active=N` | เก็บประวัติ merge ด้วยฟิลด์ audit |

---

## 3. สถาปัตยกรรมเป้าหมาย (Target Architecture)

```
┌───────────────────────────── Odoo 19 CE (AutoInfo) ─────────────────────────────┐
│                                                                                  │
│  ┌─── ชั้นพาณิชย์ (มีอยู่แล้ว) ───┐   ┌──────── ชั้นโดเมน ATG (ใหม่) ────────┐   │
│  │ res.partner (ลูกค้า/เจ้าของ)   │   │ od19.ta.plant   (ไซต์/คลัง)         │   │
│  │   + od19_partner_thai_fields   │◄──┤ od19.ta.tank    (ถัง)               │   │
│  │ project.project (งาน/โปรเจกต์) │◄──┤ od19.ta.equipment (ทะเบียน ATG)     │   │
│  │ sale.order / account.move     │   │ od19.ta.event   (ประวัติงาน)        │   │
│  │ od19_service_contract/warranty │   │ od19.ta.equipment.category          │   │
│  └────────────────────────────────┘   └─────────────────────────────────────┘   │
│                                                                                  │
│  ┌─── ชั้นสนับสนุน (มีอยู่แล้ว) ──┐   ┌────── ชั้นนำเสนอ (ใหม่ + ต่อยอด) ────┐   │
│  │ maintenance.equipment (core)    │   │ od19_ta_portal: /my/assets (ลูกค้า)  │   │
│  │ od19_iso_calibration            │   │ รายงาน ATG coverage                  │   │
│  │ od19_document_hub (แนบไฟล์)     │   │ od19_dashboard: การ์ด ATG           │   │
│  │ mail.thread (chatter/audit)     │   │                                      │   │
│  └────────────────────────────────┘   └─────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────────────┘
```

### 3.1 การแบ่งโมดูล (Module Boundaries)

| โมดูล | หน้าที่ | depends หลัก | หมายเหตุ |
|---|---|---|---|
| **`od19_ta_asset`** | ทะเบียนหลัก: Plant, Tank, Equipment, Category; ต่อ `res.partner` (ฟิลด์ TA) | `base`, `contacts`, `od19_partner_thai_fields`, `od19_contacts_partner_roles` | โมดูลแกน – ติดตั้งก่อน |
| **`od19_ta_service`** | ประวัติงาน (Event), ผูก Job (`project.project`), PM/สอบเทียบ/เปลี่ยนอะไหล่ | `od19_ta_asset`, `project`, `od19_project_enhanced`, `od19_service_warranty`, `od19_iso_calibration` (optional) | ติดตั้งหลัง asset |
| **`od19_ta_portal`** | พอร์ทัลลูกค้า + รายงาน ATG coverage + Import/Export | `od19_ta_asset`, `od19_ta_service`, `portal` | เฟสถัดไป |

> **หลักการ:** เริ่มจาก `od19_ta_asset` ที่มีคุณค่าเดี่ยว (ดูทะเบียนได้) ก่อน แล้วค่อยเพิ่ม service/portal — ลดความเสี่ยง

---

## 4. โมเดลข้อมูล (Data Model)

### 4.1 Companies → `res.partner`

ใช้ `res.partner` เป็น "บริษัทลูกค้า/เจ้าของไซต์" เพิ่มฟิลด์ TA (เฉพาะที่ Odoo ไม่มี)

| ฟิลด์เดิม | ฟิลด์ Odoo | ประเภท | หมายเหตุ |
|---|---|---|---|
| `name` | `name` | char | ชื่อบริษัท |
| `code` | `ref` | char | รหัสย่อ (IRPC, BCP) — business key ของ TA |
| `parent_code` | `parent_id` | m2o res.partner | บริษัทแม่ |
| `company_type` | `od19_ta_company_type` **(ใหม่)** | selection | end_user/contractor/epc/distributor/other |
| `industry` | `od19_ta_industry` **(ใหม่)** | selection | refinery/petrochem/terminal/.../other |
| `tax_id` | `vat` | char | เลขผู้เสียภาษี |
| `odoo_ref` | `od19_ta_odoo_ref` **(ใหม่)** | char | รหัสลูกค้า Odoo เดิม (เก็บเพื่อ audit/ reconcile) |
| `address` | `street` (+ city/zip ถ้ามี) | text | ที่อยู่ |
| `phone` | `phone` | char | โทร |
| `notes` | `comment` | text | หมายเหตุ |
| `active` | `active` | bool | Y/N |
| `merged_into` | `od19_ta_merged_into_id` **(ใหม่)** | m2o res.partner | บริษัทที่ถูก merge เข้า |
| `merged_at` | `od19_ta_merged_at` **(ใหม่)** | datetime | วันที่ merge |

> `code` → `ref` เพราะเป็น business key ที่ระบบอื่นอ้างอิง; ควรตั้ง unique constraint บน `ref` **เฉพาะ partner ที่เป็นบริษัท TA** (ใช้ `od19_ta_is_ta_company` flag ช่วยกรอง)

### 4.2 Plants → `od19.ta.plant` **(โมเดลใหม่)**

| ฟิลด์เดิม | ฟิลด์ Odoo | ประเภท | หมายเหตุ |
|---|---|---|---|
| `code` | `code` | char (unique) | รหัส Plant (business key) |
| `company_code` | `partner_id` | m2o res.partner | เจ้าของ (map จาก Companies.code) |
| `name` | `name` | char | ชื่อ Plant |
| `province` | `province` | char | จังหวัด (อนาคต map `res.country.state`) |
| `address` | `street` | text | ที่อยู่ไซต์ |
| `latitude` / `longitude` | `latitude` / `longitude` | float | พิกัด (`geo` fields) |
| `access_requirements` | `access_requirements` | text | ข้อกำหนดเข้าไซต์ |
| `inventory_software` | `inventory_software` | char | Entis Pro/XL, Tank Master |
| `interface_type` | `interface_type` | char | CIU 888, FCU, Smart Link |
| `system_version` | `system_version` | char | เวอร์ชัน/OS/DCS |
| `tank_count` | `tank_count` | integer | (แนะนำ: computed จาก tank_ids) |
| `servo_count` | `servo_count` | integer | (แนะนำ: computed) |
| `radar_count` | `radar_count` | integer | (แนะนำ: computed) |
| `active` | `active` | bool | Y/N |
| `aliases` | `aliases` | char | ชื่อเรียกอื่น (คั่น ,) |
| `merge_into` | `merged_into_id` **(ใหม่)** | m2o od19.ta.plant | Plant ที่ถูก merge เข้า |
| `notes` | `notes` | text | |

### 4.3 Tanks → `od19.ta.tank` **(โมเดลใหม่)**

| ฟิลด์เดิม | ฟิลด์ Odoo | ประเภท | หมายเหตุ |
|---|---|---|---|
| `plant_code` | `plant_id` | m2o od19.ta.plant | เจ้าของถัง |
| `tag` | `tag` | char | Tag ถัง (เช่น `66-T-2301A`) |
| `area` | `area` | selection | Movement/Offsite/LORRY/C-COT/UTILITY |
| `tank_type` | `tank_type` | char (→ selection) | ประเภทถัง |
| `product` | `product` | char | ผลิตภัณฑ์ |
| `height_mm` | `height_mm` | float | ความสูง (mm) |
| `has_stilling_well` | `has_stilling_well` | bool | มี Stilling well |
| `notes` | `notes` | text | |

> Unique: (`plant_id`, `tag`) — กันซ้ำภายใน Plant เดียวกัน

### 4.4 Equipment → `od19.ta.equipment` **(โมเดลใหม่)**

ทะเบียนอุปกรณ์ ATG รายชิ้น (2,280 ชิ้น) — **ตัวเอกของระบบ TA**

| ฟิลด์เดิม | ฟิลด์ Odoo | ประเภท | หมายเหตุ |
|---|---|---|---|
| `serial_no` | `serial_no` | char | S/N อุปกรณ์ |
| `manufacturer` | `manufacturer` | char | ผู้ผลิต |
| `model` | `model` | char (required) | รุ่น |
| `category` | `category_id` | m2o `od19.ta.equipment.category` | หมวด (Servo Gauge, VITO, Radar...) |
| `firmware` | `firmware` | char | |
| `source` | `source` | selection | supplied / third_party |
| `odoo_job_no` | `job_id` | m2o `project.project` | Job ที่จำหน่าย (map จาก Jobs.job_no) |
| `supply_date` | `supply_date` | date | วันที่ส่งมอบ |
| `warranty_end` | `warranty_end` | date | วันหมดประกัน (เชื่อม `od19_service_warranty`) |
| `status` | `state` | selection | in_service / spare / repair / scrapped |
| `plant_code` | `plant_id` | m2o od19.ta.plant | ติดตั้งที่ Plant |
| `tank_tag` | `tank_id` | m2o od19.ta.tank | ติดตั้งที่ถัง |
| `function` | `function` | char (→ selection) | หน้าที่ (Level/Temperature/...) |
| `installed_at` | `install_date` | date | วันที่ติดตั้ง |
| `removed_at` | `removal_date` | date | วันที่ถอดออก |
| `replaces_serial` | `replaces_id` | m2o od19.ta.equipment (self) | อุปกรณ์ที่ถูกแทน |
| `model_code` | `model_code` | char | รหัสสั่งซื้อ |
| `test_date` | `test_date` | date | วันที่ทดสอบจากโรงงาน |
| `opt_pressure` | `opt_pressure` | char | Option: Pressure |
| `opt_alarm_relay` | `opt_alarm_relay` | char | Option: Alarm Relay |
| `opt_analog_out` | `opt_analog_out` | char | Option: Analog output |
| `opt_sil_relay` | `opt_sil_relay` | char | Option: SIL Relay |
| `opt_sil_4_20` | `opt_sil_4_20` | char | Option: SIL 4-20 mA |
| `notes` | `notes` | text | |

**โมเดลเสริม `od19.ta.equipment.category`:** code, name, sequence (แทนการ hard-code selection → เพิ่มหมวดใหม่ได้)

**การเชื่อม maintenance (ทางเลือก):** ถ้าต้องการให้งานซ่อม/warranty ของ core ทำงานร่วม ให้ bridge
`od19.ta.equipment` ↔ `maintenance.equipment` แบบ 1:1 (`maintenance_equipment_id`) — เฟสถัดไป ไม่บังคับในเฟสแรก

### 4.5 Jobs → `project.project` (ใช้ของเดิม)

| ฟิลด์เดิม | ฟิลด์ Odoo | ประเภท | หมายเหตุ |
|---|---|---|---|
| `job_no` | `od19_ta_job_no` **(ใหม่)** | char | Job No. (JT26016) — business key |
| `title` | `name` | char | ชื่องาน |
| `company_code` | `partner_id` | m2o res.partner | ลูกค้าที่วางบิล |
| `customer_name` | `od19_ta_customer_name` **(ใหม่)** | char | ชื่อลูกค้าขณะนั้น (historical) |
| `plant_codes` | `ta_plant_ids` **(ใหม่)** | m2m od19.ta.plant | หลาย Plant (คั่นด้วย ,) |
| `tank_tags` | `ta_tank_ids` **(ใหม่)** | m2m od19.ta.tank | หลายถัง |
| `start_date` | `date_start` | date | วันเริ่ม |
| `end_date` | `date` | date | วันสิ้นสุด |
| `project_manager` | `user_id` | m2o res.users | ผู้ดูแล (map จากชื่อ → user) |
| `odoo_stage` | `stage_id` | m2o project.task.type/project.stage | SALES/PM/SERVICE |
| `work_type` | `od19_ta_work_type` **(ใหม่)** | selection | ประเภทงานหลัก |
| `equipment_hint` | `od19_ta_equipment_hint` **(ใหม่)** | char | อุปกรณ์ที่ระบุในชื่องาน |
| `is_contract` | `od19_ta_is_contract` **(ใหม่)** | bool | สัญญาระยะยาว → เชื่อม `od19_service_contract` |
| `notes` | `description` | html | หมายเหตุ |

### 4.6 Events → `od19.ta.event` **(โมเดลใหม่)**

ประวัติงานต่ออุปกรณ์ (8,144 แถว) — หัวใจของ "ประวัติอุปกรณ์"

| ฟิลด์เดิม | ฟิลด์ Odoo | ประเภท | หมายเหตุ |
|---|---|---|---|
| `event_date` | `event_date` | date | วันที่ |
| `event_type` | `event_type` | selection | pm/install/calibration/replace_part/repair/remove/config/note/inspection |
| `job_no` | `job_id` | m2o project.project | งานที่เกี่ยวข้อง |
| `plant` | `plant_id` | m2o od19.ta.plant | |
| `tank` | `tank_id` | m2o od19.ta.tank | |
| `serial_no` | `equipment_id` | m2o od19.ta.equipment | |
| `model` | (derived) | — | ดึงจาก equipment.model (ไม่เก็บซ้ำ) |
| `performed_by` | `performed_by_id` | m2o res.users | ผู้ทำ (map จากชื่อ) |
| `description` | `description` | text | รายละเอียด |
| `result` | `result` | text | ผล/ค่าวัด |
| (แนบไฟล์) | `attachment_ids` | o2m ir.attachment | ใช้ `od19_document_hub` |

**Inherit `mail.thread`** → chatter + audit trail ทดแทน `/audit` เดิม

### 4.7 Contacts → `res.partner` (child)

| ฟิลด์เดิม | ฟิลด์ Odoo | หมายเหตุ |
|---|---|---|
| `company_code` | `parent_id` | ผูกบริษัท |
| `plant_code` | `od19_ta_plant_id` **(ใหม่)** | ผู้ประสานงานประจำ Plant |
| `name` | `name` | ชื่อ |
| `position` | `function` | ตำแหน่ง |
| `phone` | `phone` | |
| `email` | `email` | |
| `notes` | `comment` | |

### 4.8 Users → `res.users` + Groups

| ฟิลด์เดิม | ฟิลด์/ปลายทาง | หมายเหตุ |
|---|---|---|
| `username` | `login` | |
| `full_name` | `name` | |
| `role = admin` | group `TA Manager` | สิทธิ์เต็ม |
| `role = engineer` | group `TA Engineer` | สร้าง/แก้ event, ดูทะเบียน |
| `role = viewer` | group `TA Viewer` | ดูเท่านั้น |
| `status` | `active` | |

### 4.9 แผนผังความสัมพันธ์ (ER)

```
res.partner (บริษัทลูกค้า)
   │ 1
   ├──── N od19.ta.plant ──── N  project.project (Jobs, m2m ผ่าน ta_plant_ids)
   │            │ 1
   │            └── N od19.ta.tank ──── N project.project (m2m ผ่าน ta_tank_ids)
   │                       │ 1
   │                       └── N od19.ta.equipment ─── N od19.ta.event
   │                                    │ (self) replaces_id
   │                                    └── od19.ta.equipment.category
   └──── N res.partner (contact, child) → od19_ta_plant_id
```

---

## 5. จุดเชื่อมกับ Odoo Core และโมดูลเดิม (Integration Points)

| จุดเชื่อม | ใช้กับ | รายละเอียด |
|---|---|---|
| `res.partner` | Companies/Contacts | ใช้ partner เดิม + ฟิลด์ไทย (`od19_partner_thai_fields`) + roles (`od19_contacts_partner_roles`) |
| `project.project` | Jobs | stage เดิมของ project; `od19_project_enhanced` ช่วยเรื่อง PM |
| `od19_service_warranty` | Equipment.warranty_end | คำนวณ/แจ้งเตือนประกันหมด |
| `od19_service_contract` | Jobs.is_contract | งานในสัญญา PM ระยะยาว |
| `od19_iso_calibration` | Event: calibration | บันทึกผลสอบเทียบตาม ISO |
| `od19_quality_control` | Event: inspection | ตรวจสอบคุณภาพ |
| `od19_document_hub` | Event/files | เก็บไฟล์แนบ (รูปหน้างาน, Service Report) |
| `od19_billing_request` | Event → วางบิล | งานเสร็จ → คำขอวางบิล |
| `od19_role_catalog` | สิทธิ์ | สร้างกลุ่ม TA Manager/Engineer/Viewer |
| `od19_dashboard` | รายงาน ATG | การ์ด KPI (จำนวน ATG, % coverage, ประกันใกล้หมด) |
| `mail.thread` | ทุกโมเดล | chatter + ประวัติการแก้ไข (แทน /audit) |

---

## 6. Workflow

### 6.1 วงจรชีวิตอุปกรณ์ ATG (`od19.ta.equipment`)

```
spare ──ติดตั้ง──► in_service ──ซ่อม──► repair ──► in_service
   ▲                  │
   │                  └──ถอด/ปลด──► (removal_date) ──► scrapped
   └─────────────────(เปลี่ยนทดแทน: equipment ใหม่.replaces_id = ตัวเดิม)
```

- ทุกการเปลี่ยนสถานะ → บันทึกเป็น `od19.ta.event` อัตโนมัติ (หรือกดสร้างจากฟอร์มอุปกรณ์)
- ติดตั้ง → set `plant_id`, `tank_id`, `install_date`, `state=in_service`

### 6.2 งานบริการ (Job + Event)

```
project.project (job)  ──►  เปิดงาน (stage=SALES/PM/SERVICE)
        │
        ├── สร้าง od19.ta.event (pm/install/calibration/repair/replace_part/...)
        │        ├── เลือก equipment (auto-fill plant/tank)
        │        ├── แนบไฟล์ Service Report
        │        └── บันทึก result (ค่าที่วัด/ผล)
        │
        └── (จบงาน) → คำขอวางบิล (od19_billing_request) → account.move
```

### 6.3 PM ตามสัญญา

- Job `is_contract = true` → ผูก `od19_service_contract`
- รอบ PM → สร้าง event `pm` ล่วงหน้าตามความถี่ (เช่น ทุก 3 เดือน)
- `warranty_end` ใกล้ถึง → แจ้งเตือน (activity / notification)

---

## 7. สิทธิ์การเข้าถึง (Security)

| กลุ่ม | Plant/Tank | Equipment | Event | Job | ตั้งค่า |
|---|---|---|---|---|---|
| **TA Manager** | CRUD | CRUD | CRUD | CRUD | CRUD (category, import) |
| **TA Engineer** | R | CRUD (ติดตั้ง/ถอด) | CRUD | R | R |
| **TA Viewer** | R | R | R | R | – |
| **Sales** | R | R | R | CRUD (เฉพาะของตน) | – |
| **ลูกค้า (portal)** | R (เฉพาะ Plant ตัวเอง) | R (เฉพาะของตน) | R (เฉพาะของตน) | R (เฉพาะของตน) | – |

- ใช้ **record rules** กรองตาม `partner_id` ของผู้ใช้/บริษัท
- พอร์ทัลใช้ `portal` + rule ผูก with `res.partner` ของลูกค้า
- ใช้ `od19_role_catalog` ในการสร้างกลุ่ม

> แทนระบบ `users` + `role` เดิม (admin/engineer/viewer) ด้วยกลุ่ม Odoo มาตรฐาน

---

## 8. รายงาน (Reports)

| รายงาน | ที่มา | ปลายทาง |
|---|---|---|
| ATG Coverage ต่อ Plant/ลูกค้า | `/reports/atg` เดิม | list/pivot + การ์ด dashboard |
| ทะเบียนอุปกรณ์ตามสถานะ | `/equipment` filter | list + group by state/category/plant |
| ประวัติอุปกรณ์ (timeline) | History | chatter + view timeline บน equipment |
| ประกันใกล้หมด | `warranty_end` | filter/activity |
| Export/Import | `/data` เดิม | `base_import` ของ Odoo (built-in) |

> **ไม่ต้องทำ Import/Export เอง** — Odoo มี `base_import` + export ในตัว ใช้แทน `/data`

---

## 9. แผนการย้ายข้อมูล (Migration Plan)

| เฟส | ขอบเขต | หมายเหตุ |
|---|---|---|
| **M0** | เตรียม: สร้างโมดูล `od19_ta_asset` (models/views/security) | ไม่มีข้อมูล |
| **M1** | Companies → `res.partner` (87) | resolve parent, merge, ตั้ง `ref` |
| **M2** | Plants → `od19.ta.plant` (84) | link `partner_id` จาก code |
| **M3** | Tanks → `od19.ta.tank` (1,230) | link `plant_id` |
| **M4** | Equipment → `od19.ta.equipment` (2,280) | link plant/tank/job, resolve `replaces_serial` |
| **M5** | Jobs → `project.project` (526) | match/สร้าง project, link plant/tank (m2m) |
| **M6** | Events → `od19.ta.event` (8,144) | link equipment/plant/tank/job |
| **M7** | Contacts + Users → res.partner/res.users | สร้างกลุ่มสิทธิ์ |
| **M8** | ตรวจสอบ (reconciliation) + freeze ระบบเดิม | เทียบยอด, ปิดระบบเดิม |

**ลำดับสำคัญ:** Companies → Plants → Tanks → Equipment → Jobs → Events (ตาม FK)

**เครื่องมือ:** สคริปต์ Python (etl) อ่านจาก CSV ที่ export ไว้ → สร้างผ่าน `env[...].create()` ใน Odoo shell (ใช้ transaction/per-batch + dry-run ก่อน)

---

## 10. ขอบเขต (Scope)

### 10.1 ในขอบเขต
- โมเดล Plant/Tank/Equipment/Event + Category
- ต่อ `res.partner` (Companies/Contacts) และ `project.project` (Jobs)
- หน้าจอ (list/form/kanban/timeline) + menu
- สิทธิ์ 3 กลุ่ม + record rules
- ย้ายข้อมูลเดิมครบ 8 ตาราง
- รายงาน ATG coverage + dashboard

### 10.2 นอกขอบเขต (เฟสถัดไป)
- แอปมือถือ/ออฟไลน์สำหรับวิศวกร (ใช้ `od19_offline_draft` ได้ถ้าต้องการ)
- Bridge เต็มรูปแบบกับ `maintenance.equipment`
- Billing อัตโนมัติจาก event (ใช้ `od19_billing_request` ที่มีอยู่)
- ลบ/patch ระบบเดิม (คงไว้จนกว่าจะตรวจครบ)

---

## 11. ความเสี่ยง (Risks)

| # | ความเสี่ยง | ระดับ | แนวทางลด |
|---|---|---|---|
| R1 | ข้อมูลซ้ำ (S/N ซ้ำ, plant/tank ซ้ำ) | สูง | dry-run + dedup report ก่อนสร้าง |
| R2 | ชื่อ user ไม่ตรงกับ Odoo (`performed_by`, `project_manager`) | กลาง | map ด้วยชื่อ + manual review list |
| R3 | `code`/`ref` ชนกับ partner เดิมในระบบ | กลาง | ตรวจก่อน, ตั้ง prefix ถ้าจำเป็น |
| R4 | ค่า enum หลากหลาย (tank_type, function) | กลาง | map เป็นชุดมาตรฐาน + เก็บค่าดิบใน notes |
| R5 | วันที่ผิด (อนาคต/ว่าง) | ต่ำ | flag `date_uncertain` + ตรวจ |
| R6 | ข้อมูลลูกค้าอ่อนไหว (PO/ราคาใน notes) | กลาง | เก็บไฟล์ดิบนอก repo; ตรวจสิทธิ์ก่อนย้าย notes |

---

## 12. เกณฑ์สำเร็จ (Acceptance Criteria)

- [ ] เห็นลูกค้า → Plant → ถัง → อุปกรณ์ → ประวัติ ได้ใน Odoo
- [ ] ย้ายข้อมูลครบ 8 ตาราง ยอดตรงกับต้นทาง (Companies 87, Plants 84, Tanks 1,230, Equipment 2,280, Jobs 526, Events 8,144)
- [ ] สิทธิ์ 3 กลุ่มทำงานถูกต้อง (Manager/Engineer/Viewer) + ลูกค้าเห็นเฉพาะของตน
- [ ] เปิด Job แล้วเห็น Plant/Tank/Equipment/Event ที่เกี่ยวข้อง
- [ ] รายงาน ATG coverage ให้ % ถูกต้อง
- [ ] ไม่แตะ Odoo core / `third_party/oca/`
- [ ] ทดสอบผ่านตาม AGENTS.md (S1: `odoo19_pdev` → deploy release → restart 8070 → verify)

---

## ภาคผนวก ก. พจนานุกรม Enum (จากข้อมูลจริง)

### A.1 Companies
- **company_type:** end_user (57) · contractor (22) · distributor (3) · epc (2) · other (2)
- **industry:** service (27) · petrochem (17) · terminal (12) · refinery (6) · fuel_marketing (6) · other (6) · lpg (5) · bio_agro (5) · aviation (2) · power

### A.2 Equipment
- **category:** Servo Gauge (984) · Temperature Probe / VITO (875) · Radar Gauge (227) · Water Bottom (62) · Display / Indicator (47) · CIU / Interface (20) · Other (18) · Level Transmitter (HART) (18) · Computer / Software (14)
- **status:** in_service (2,225) · spare (54) · repair · scrapped
- **source:** supplied (2,128) · third_party (151)
- **manufacturer:** Honeywell Enraf (2,072) · Emerson / Rosemount (92) · Saab (28) · Dell (2) · ...
- **function:** Level (1,119) · Temperature (588) · Temperature element (250) · Water Interface (58) · ...

### A.3 Jobs
- **odoo_stage:** SALES (293) · PM (178) · SERVICE (52) · JOB (1) · DONE (1)
- **work_type:** Engineering service (133) · Calibration/Witness (92) · PM/บำรุงรักษา (88) · เปลี่ยนอุปกรณ์ (46) · ไม่ระบุ (44) · ติดตั้ง/Commissioning (29) · ซ่อม/แก้ปัญหา (17) · ตรวจสอบ/Inspection (14) · Upgrade (12) · Spare part (10) · Overhaul/Revamp (8) · Strapping table (8) · Training (7) · Dip tank (6) · Supervise (2)
- **job prefix:** JT · ST · PMT · SP · WS · NS · TMP

### A.4 Events
- **event_type:** pm (2,787) · install (2,379) · calibration (1,158) · replace_part (891) · repair (707) · remove (147) · config (39) · note (30) · inspection (5)

### A.5 Plants / Tanks
- **inventory_software:** Entis Pro (22) · Tank Master (21) · Entis XL (20) · Tank Vision (2) · ...
- **interface_type:** CIU 888 (17) · Smart Link (11) · CIU 858 (9) · FCU (6) · CIU PRIME/PLUS (4) · Tank Scan (2)
- **tank.area:** Movement (110) · Offsite (31) · LORRY (25) · C-COT (14) · UTILITY (3)
- **tank.tank_type:** Cylindrical Fixed Roof · Fixed Roof · Vertical cylinder · Floating roof · Internal Floating roof · SPHERE · ...

---

## ภาคผนวก ข. เอกสารประกอบ

- **Data Mapping (Excel):** [`2026-11-26-od19-ta-asset-register-data-mapping.xlsx`](2026-11-26-od19-ta-asset-register-data-mapping.xlsx) — map ทีละฟิลด์ต้นทาง → ปลายทาง พร้อม enums/transform
- **ข้อมูลดิบ P0:** export ระบบเดิม 7 ชีต (2026-11-26) — เก็บนอก repo (มีข้อมูลลูกค้า/PO)
