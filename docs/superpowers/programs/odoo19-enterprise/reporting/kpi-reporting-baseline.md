# KPI and Reporting Baseline

## Document Metadata

| Field | Value |
| --- | --- |
| Program | Odoo 19 CE Enterprise |
| Artifact path | `docs/superpowers/programs/odoo19-enterprise/reporting/kpi-reporting-baseline.md` |
| Artifact owner | Business sponsor with program analytics lead |
| Required reviewers | Business sponsor, delivery lead, architecture lead |
| Artifact status | Active baseline |
| Review cadence | Reconfirm before each domain spec approval, before KPI scope expansion, and after major reporting feedback from business users |
| Last updated | 2026-10-13 |

## Purpose

Define the minimum KPI and reporting contract for Wave 0 so owner, manager, and operational lead audiences receive information designed for decisions rather than raw transaction noise.

## Scope

- Applies to KPI definitions, reporting intent, signal design, and dashboard-facing information contracts used by the Odoo 19 CE Enterprise program.
- Applies to role-based reporting planned during Wave 0 and refined during later domain waves.
- Does not define final data models, ETL design, or finished dashboard implementation inside Odoo.
- Defines the baseline contract for later dashboard design; it does not imply that every KPI, report, or dashboard view is already implemented.

## KPI Layers

| Layer | Primary audience | Main question answered | Decision horizon |
| --- | --- | --- | --- |
| Owner level | Owner, sponsor, executive leadership | Is the business healthy, profitable, cash-safe, and trending in the right direction? | Weekly to monthly |
| Management level | Department heads, functional managers, cross-domain leads | Which team, domain, or business unit is underperforming or drifting from plan? | Daily to weekly |
| Operational level | Team leads, supervisors, queue owners | Which work items need action now to prevent delay, SLA breach, or control failure? | Intraday to daily |

## KPI Design Principles

- Every KPI must support a named business decision, not just a visibility preference.
- Every KPI must have a business owner, an intended audience, and a review cadence.
- Every KPI must be traceable to a trusted source or explicitly marked provisional during discovery.
- KPI sets should move from summary to exception to drill-down, not start with document-level detail.
- If a metric cannot trigger a decision, escalation, or follow-up action, it should not be promoted into the baseline set.

## Reporting Contract

Threshold definition is mandatory for every baseline report. A report is not review-ready unless its status boundaries are explicitly defined, and dashboard views should inherit those same status rules instead of inventing a different color model.

| Contract field | Minimum requirement |
| --- | --- |
| Business question | State the decision question the report answers. |
| Audience | Name the role or team expected to use the output. |
| Decision supported | State what decision, escalation, or follow-up the user can take from the report. |
| Source data | Identify the originating model, dataset, or discovery assumption used for the report. |
| Refresh cadence | Define how often the report should update or be reviewed. |
| Threshold definition | Define the threshold or status logic required to classify the output, including red/yellow/green and a grey or equivalent unavailable state when data is incomplete, delayed, or intentionally withheld. |
| Drill-down depth | Define the deepest level each audience is allowed to inspect. |
| Quality cue | State how the user knows the information is complete, delayed, estimated, or unavailable. |

## Minimum KPI Categories

| Category | Owner view | Management view | Operational view |
| --- | --- | --- | --- |
| Financial health | Revenue trend, gross margin, cash conversion, overdue exposure | Budget variance, receivable aging by team, collection trend | Billing backlog, pending approvals affecting invoicing |
| Delivery performance | On-time fulfillment rate, service backlog trend | SLA compliance by team, cycle time by process | Today's due items, stuck workflow count, near-deadline queue |
| Control and risk | Exception count, unresolved critical alerts, high-risk accounts | Policy breaches, recurring rework, approval bottlenecks | Missing data, blocked documents, failed validations |
| Growth and pipeline | Pipeline conversion, sales mix, business-unit comparison | Funnel stage aging, workload balance, team capacity pressure | Assigned actions, queue inflow versus throughput |

## Reporting Contract Template

Use this minimum template whenever a new KPI report is proposed:

The template is incomplete unless the report owner states a quality cue that tells readers whether the numbers are complete, delayed, estimated, or unavailable.

| Field | Example prompt |
| --- | --- |
| Report name | What is the report called? |
| Business question | What decision does this answer? |
| Consumer | Who uses it first? |
| Trigger or cadence | When is it reviewed? |
| Data source | Which model or source artifact feeds it? |
| Threshold definition (required) | What counts as good, warning, or bad, and where are the exact business boundaries? |
| Quality cue (required) | How should the reader interpret the trust level of this output: complete, delayed, estimated, or unavailable? |
| Drill-down path | How far can the user inspect detail? |
| Owner | Who keeps the report definition correct? |

## Dual Report Format Requirement (Odoo 19 CE + Odoo 15 CE Compatibility)

เงื่อนไขนี้ **ใช้เฉพาะรายงานที่พิมพ์ออกมาจากระบบ (printable reports / printed forms)** เท่านั้น ไม่รวมรายงานประเภท KPI Dashboard หรือรายงานที่แสดงผลบนหน้าจอ (on-screen reports)

ทุกรายงานและฟอร์มพิมพ์ที่สร้างหรือปรับปรุงในโปรแกรม Odoo 19 CE ต้องรองรับ **สองรูปแบบ** พร้อมกัน:

| รูปแบบ | คำอธิบาย | จุดประสงค์ |
| --- | --- | --- |
| **Odoo 19 CE Native** | รูปแบบมาตรฐานของ Odoo 19 CE (ใช้ QWeb report / native Odoo report engine) | รองรับการใช้งานปกติของระบบใหม่ การอัปเกรด และการบำรุงรักษาในระยะยาว |
| **Odoo 15 CE Legacy Compatible** | รูปแบบที่เหมือนกับรายงาน/ฟอร์มที่บริษัทใช้อยู่ใน Odoo 15 CE ปัจจุบัน (ใช้ JasperReports / JRXML ผ่าน jasperstarter) | ให้ความต่อเนื่องกับผู้ใช้งานที่คุ้นเคยกับรูปแบบเดิม และรองรับการเปรียบเทียบข้อมูลระหว่างระบบเก่าและใหม่ |

### กฎการบังคับใช้ (Mandatory Rules)

- เงื่อนไขนี้ **ใช้เฉพาะรายงานที่พิมพ์ออกมาเป็นเอกสาร (PDF/print)** เท่านั้น เช่น ใบกำกับภาษี ใบเสนอราคา ใบสั่งซื้อ ใบสั่งขาย ใบรับสินค้า ใบส่งสินค้า รายงานทางการเงินที่พิมพ์ออกมา ฯลฯ
- **ไม่** ใช้กับรายงานประเภท KPI Dashboard, Pivot table, Graph, หรือรายงานที่แสดงผลบนหน้าจอในระบบ (on-screen views)
- ทุกรายงานพิมพ์ **ต้องมีทั้งสองรูปแบบ** ก่อนจะถูกยืนยันว่าเสร็จสมบูรณ์ (complete) ไม่สามารถส่งมอบได้เพียงรูปแบบเดียว
- รูปแบบ **Odoo 15 CE Legacy Compatible** ต้องเปรียบเทียบกับต้นฉบับจากระบบ Odoo 15 CE ที่ใช้งานจริง และผ่านการตรวจสอบจากผู้ใช้งานฝ่ายธุรกิจว่าตรงตามรูปแบบที่คุ้นเคย
- รูปแบบ **Odoo 19 CE Native** ต้องใช้มาตรฐานของ Odoo 19 CE (QWeb / native report) เพื่อรองรับการบำรุงรักษาและอัปเกรดในอนาคต
- ผู้ใช้งานต้องสามารถเลือกได้ว่าจะพิมพ์รายงานในรูปแบบใด (ผ่าน menu, wizard, หรือ action ที่เหมาะสม)
- รูปแบบทั้งสองต้องดึงข้อมูลจาก **แหล่งข้อมูลเดียวกัน** เพื่อให้ได้ผลลัพธ์ที่สอดคล้องกัน ไม่อนุญาตให้ logic คำนวณแยกกัน

### ขอบเขตที่ครอบคลุม (เฉพาะรายงานพิมพ์)

- ใบกำกับภาษี (Invoice), ใบเสนอราคา (Quotation), ใบสั่งซื้อ (PO), ใบรับสินค้า (Receipt), ใบสั่งขาย (SO)
- รายงานทางการเงินที่พิมพ์ออกมา (AR/AP Aging, P&L, Balance Sheet, Trial Balance)
- รายงานสินค้าคงคลังและการเคลื่อนไหวสินค้าที่พิมพ์ออกมา
- รายงานฝ่ายขายที่พิมพ์ออกมา (Sales Analysis, Repeat Business, Project P&L)
- ใบปะหน้า (Delivery Order, Picking)
- ฟอร์มภายในอื่นๆ ที่บริษัทใช้พิมพ์ออกมาในระบบ Odoo 15 CE ปัจจุบัน

### ข้อยกเว้น (Exception)

- รายงานประเภท KPI Dashboard หรือรายงานออนไลน์ (on-screen) ที่ไม่ต้องการพิมพ์ — **ไม่ต้อง** มีรูปแบบ Odoo 15 CE Legacy Compatible ใช้รูปแบบ Odoo 19 CE Native เพียงอย่างเดียว
- รายงานพิมพ์ใหม่ที่ไม่มีต้นฉบับใน Odoo 15 CE สามารถใช้รูปแบบ Odoo 19 CE Native เพียงอย่างเดียวได้ โดยต้องระบุไว้ในรายงานการออกแบบ

## Thai Font & UI Localization Requirement

เงื่อนไขนี้ใช้สำหรับ **ทุกส่วนของระบบ** (ไม่ใช่แค่รายงาน) เพื่อให้แน่ใจว่าภาษาไทยแสดงผลได้ถูกต้องและสวยงามทุกหน้าจอและทุกเอกสารที่พิมพ์ออกมา

### หลักการทั่วไป

- ระบบ Odoo 19 CE ต้องรองรับฟอนต์ภาษาไทยใน **ทุกส่วนของระบบ**
- ใช้ **ฟอนต์หลักมาตรฐานของบริษัทเพียง 1-2 ชุด** เพื่อรักษาความสอดคล้อง (consistency) ของ UI และความง่ายต่อการบำรุงรักษา
- รองรับ **4 สไตล์หลัก** เท่านั้น: Regular, Bold, Italic, Bold Italic
- **ไม่แนะนำ** ให้ผู้ใช้งานเปลี่ยนฟอนต์ได้ทุกสไตล์ เพราะจะทำให้ UI ไม่สอดคล้องและยากต่อการบำรุงรักษา

### ฟอนต์ตามส่วนของระบบ

| ส่วนของระบบ | ฟอนต์ที่แนะนำ | หมายเหตุ |
| --- | --- | --- |
| **Web UI (Backend/Frontend)** | Sarabun หรือ Noto Sans Thai | อ่านง่าย เหมาะกับ UI ทั่วไป ตั้งค่าใน CSS เป็นค่าเริ่มต้น |
| **QWeb Reports (Odoo 19 Native)** | Sarabun หรือ Noto Sans Thai (เดียวกับ Web UI) | **ต้องติดตั้งฟอนต์บน server** จริง (ไม่ใช่แค่ CSS) เพื่อให้ PDF แสดงผลภาษาไทยได้ถูกต้อง |
| **JasperReports (Odoo 15 Legacy Compatible)** | **ฟอนต์เดิมที่บริษัทใช้อยู่ใน Odoo 15** | เพื่อให้รูปแบบเหมือนเดิม 100%; ต้อง embed ฟอนต์ลงใน `.jasper` file หรือติดตั้งบน server ที่รัน jasperstarter |
| **Email Templates** | Sarabun, Tahoma, Arial Unicode MS | ใช้ web-safe font พร้อม fallback font stack เพื่อให้แน่ใจว่าแสดงผลได้ในทุก email client |

### ข้อกำหนดการติดตั้ง

- ฟอนต์ภาษาไทยต้อง **ติดตั้งบน server** (Debian/Ubuntu: `apt install fonts-sarabun` หรือ download Noto Sans Thai) ไม่ใช่แค่ระบุใน CSS
- สำหรับ QWeb PDF reports ต้องตรวจสอบว่า wkhtmltopdf สามารถเข้าถึงฟอนต์บน server ได้
- สำหรับ JasperReports ต้องตรวจสอบว่า JVM ของ jasperstarter สามารถโหลดฟอนต์ได้

### การตรวจสอบ (Verification)

- ต้องตรวจสอบว่าภาษาไทยแสดงผลถูกต้องใน:
  - ทุกหน้าจอของระบบ (Web UI)
  - ทุกรายงานพิมพ์รูปแบบ Odoo 19 Native (QWeb PDF)
  - ทุกรายงานพิมพ์รูปแบบ Odoo 15 Legacy Compatible (JasperReports)
  - ทุก Email Template ที่ระบบส่งออกไป
- ต้องตรวจสอบว่าสไตล์ Bold, Italic, Bold Italic แสดงผลได้ถูกต้อง

## Payment Preparation Strategy (Prepare Payment — วิธีที่ 3)

ตัดสินใจวันที่ 2026-10-13 — ใช้วิธีที่ 3: **ไม่สร้างโมเดล `account.payment.voucher` เอง** แต่ใช้ Odoo standard + OCA เป็นหลัก เพื่อลดงานพัฒนาและง่ายต่อการอัปเกรดเวอร์ชัน

### หลักการ

- ใช้ประโยชน์สูงสุดจาก Odoo standard และ OCA modules
- โค้ด custom น้อยที่สุด (ประมาณ 300 บรรทัด)
- ไม่สร้าง model/flow ใหม่ที่ซ้ำซ้อนกับ Odoo standard
- ง่ายต่อการอัปเกรดและบำรุงรักษาในระยะยาว

### ส่วนประกอบ

| ส่วน | วิธีทำ | โมดูลที่ใช้ | พัฒนาเองหรือไม่ |
| --- | --- | --- | --- |
| ตั้งหนี้ (A/P, A/R) | ใช้ Vendor Bill / Customer Invoice มาตรฐาน | Odoo standard `account` | ไม่ต้องพัฒนา |
| จัดกลุ่มใบแจ้งหนี้เพื่อจ่าย | ใช้ `account.payment.register` (รองรับ partner เดียวกัน) | Odoo standard `account` | ไม่ต้องพัฒนา |
| WHT คำนวณอัตโนมัติ | WHT บนบรรทัดใบแจ้งหนี้, auto-calc ตอนจ่าย | OCA `l10n_th_account_tax` (v19.0) | ไม่ต้องพัฒนา |
| Tax Invoice | มี `tax_invoice_number`, `tax_invoice_date` | OCA `l10n_th_account_tax` | ไม่ต้องพัฒนา |
| PND (PND3/PND53) | CSV export สำหรับส่ง Revenue Department | Odoo standard `l10n_th` | ไม่ต้องพัฒนา |
| ใบสำคัญจ่าย (Payment Voucher) | รายงานพิมพ์รูปแบบ QWeb | Custom | **พัฒนา (QWeb report)** |
| ใบสำคัญรับเงิน (Payment Receipt) | รายงานพิมพ์รูปแบบ QWeb | Custom | **พัฒนา (QWeb report)** |
| เลขที่เอกสารไทย (PV-2569-0001) | sequence field บน `account.payment` | Custom | **พัฒนา (sequence)** |

### Optional (ถ้าต้องการ)

- อนุมัติก่อนชำระ (Approval): ใช้ OCA `base_tier_validation` (ประมาณ 50 บรรทัด config)
- จัดกลุ่มหลาย partner: ใช้ OCA `account_payment_order` (ประมาณ 100 บรรทัดปรับให้เข้ากับไทย)
- WHT Certificate PDF: พัฒนา custom (ประมาณ 200 บรรทัด)

### OCA Modules ที่ใช้เป็นฐาน (ไม่พัฒนาเอง)

| โมดูล | จุดประสงค์ | เวอร์ชัน |
| --- | --- | --- |
| `l10n_th` (Odoo standard) | Chart of Accounts, VAT 7%, WHT types, PND3/PND53 CSV, PromptPay QR, Tax Invoice PDF | Odoo 19 CE |
| `l10n_th_account_tax` (OCA) | WHT บนบรรทัดใบแจ้งหนี้, auto-calc ตอนจ่าย, Tax Invoice Number/Date, Undue VAT (VAT ตอนจ่าย), PIT | v19.0.1.0.0 |
| `base_tier_validation` (OCA) | Approval workflow รวมศูนย์เดียว (ไม่แยกทุกโดเมนเหมือน DTR) | v19.0 |
| `account_financial_report` (OCA) | รายงานทางการเงินมาตรฐาน (Trial Balance, P&L, Balance Sheet, AR/AP Aging) | v19.0 |

### โมดูล Custom ที่เสนอ

| Wave | โมดูล | คำอธิบาย |
| --- | --- | --- |
| Wave 0 | `od19_thai_font_support` | ติดตั้งฟอนต์ Sarabun/Noto Sans Thai + CSS สำหรับ Web UI และ QWeb |
| Wave 0 | `od19_thai_localization_base` | ฐานสำหรับ localization ของไทย (menu, term, config) |
| Wave 1 | `od19_partner_thai_fields` | ฟิลด์ไทยสำหรับ partner (เลขผู้เสียภาษี, สาขา, หมายเลขสำนักงานใหญ่) |
| Wave 1 | `od19_document_sequence` | เลขที่เอกสารไทยตามปีงบประมาณ (INV, PO, SO, PV) |
| Wave 1 | `od19_thai_tax_reports` | VAT Register, WHT Register, PND export (ขยายจาก OCA) |
| Wave 1 | `od19_accounting_dncn` | Debit Note / Credit Note / Remaster Invoice |
| Wave 1 | `od19_accounting_cheque` | เช็ค: รายการเช็ค, เงื่อนไข, รายงานพิมพ์เช็ครวมธนาคาร |
| Wave 2 | `od19_accounting_reporting` | รายงานทางการเงินทั้งหมด (QWeb) |
| Wave 2 | `od19_accounting_payment_voucher_reports` | รายงานใบสำคัญจ่าย/ใบสำคัญรับเงิน (**reports only, ไม่สร้าง model**) |

## Signal and Alert Model

| Signal type | Purpose | Trigger condition | Typical owner | Escalation path | Expected response |
| --- | --- | --- | --- | --- | --- |
| Health signals | Show whether a business area is stable or drifting. | Fires when a KPI crosses its warning or critical threshold, or when negative trend movement persists across the defined review window. | Owner or manager | Escalate from report owner to named business owner, then to sponsor review if the condition remains unresolved through the agreed review cycle. | Review trend, confirm root cause, and decide whether intervention is needed. |
| Control alerts | Show policy, compliance, or approval exceptions that need oversight. | Fires when a policy breach, approval breach, or control exception exceeds allowed tolerance. | Manager or control owner | Escalate from control owner to functional manager, then to executive sponsor or risk authority when the breach is critical, repeated, or unresolved. | Investigate cause, assign action, and confirm containment. |
| Operational alerts | Show work items at risk of delay, failure, or queue congestion. | Fires when queue age, SLA risk, blocked status, or validation failure passes the configured operating threshold. | Operational lead | Escalate from queue owner to team lead, then to functional manager if recovery does not happen within the expected response window. | Reprioritize work, unblock documents, or escalate capacity issues. |

## Severity Ownership

| Severity | Meaning | Escalation owner | Expected response window |
| --- | --- | --- | --- |
| Critical | Immediate business, cash, or control risk | Executive sponsor or named domain lead | Immediate same-day action |
| High | Material underperformance or repeatable process risk | Functional manager | Same day to next working day |
| Medium | Noticeable drift that requires monitoring and follow-up | Team lead or process owner | Within planned review cycle |
| Low | Informational or emerging trend | Report owner | Track and reassess during routine review |

## Baseline Review Rules

- Promote a KPI into the baseline only after its audience, decision use, and source logic are understood well enough to review.
- Mark discovery-dependent metrics as provisional until the domain spec confirms source fields and business logic.
- Remove duplicate measures that restate the same issue at multiple levels without adding a new decision.
- Review alert fatigue risk whenever more than a few exceptions can fire at the same time for one audience.
- Do not approve an alert baseline entry unless trigger condition, threshold definition, and escalation path are all explicitly documented.
- Do not label a KPI, report, or dashboard view as implemented unless the source logic, refresh path, and user-facing surface already exist in the target environment.

## Deferred Topics

- Final dashboard UI implementation
- Final warehouse or ETL architecture
- Automated threshold tuning
- Full metric dictionary for every future business domain
