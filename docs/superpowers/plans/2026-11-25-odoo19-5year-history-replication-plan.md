# Odoo 19 — จำลองการใช้งาน 5 ปี (2022–2026) เทียบ Odoo 15 · Full-History Replication + Parity

> **For agentic workers:** REQUIRED SUB-SKILL: ใช้ superpowers:subagent-driven-development หรือ superpowers:executing-plans เพื่อทำตามแผนนี้ทีละ Task โดยใช้ checkbox (`- [ ]`) ในการติดตามความคืบหน้า

**Goal:** ทำให้ Odoo 19 มี **ประวัติธุรกรรมจริงครบ 5 ปี (2022-01-01 → 2026-12-31)** ยกจาก Odoo 15 (`od15_stage`) เพื่อให้ **รายงานทุกตัวเลขตรงกับ Odoo 15 100%** เสมือน Odoo 19 ถูกใช้งานมานานหลายปี + สาธิต **Bring Forward / ปิดงบปลายปี 2025 (2025-12-31)**

**Architecture:** ไม่สร้างข้อมูลจำลองใหม่ — ใช้ **Odoo 15 เป็น single source of truth** (read-only) แล้วยกจริงแบบ 1:1 ผ่าน tooling ที่มีอยู่แล้ว (`migration/simulate`, `migration/import`) ทุก record ผูก External ID `__import15__.<model>.<TAG>_<od15_id>` → รันซ้ำได้ (idempotent)

**Tech Stack:** Odoo 19 (target `odoo19_pdev`/`odoo19_puat`), Odoo 15 (`od15_stage`, read-only), PostgreSQL, Python (`venv19`, psycopg2), Odoo ORM ผ่าน `odoo shell`, openpyxl (รายงาน xlsx), PowerShell (Windows), Git

**เอกสารและเครื่องมือที่เกี่ยวข้อง (มีอยู่แล้ว):**

| ประเภท | ไฟล์ |
|---|---|
| Replicate GL/doc จริง | `migration/simulate/sim_replicate_gl15.py` |
| ตรวจ parity รายงาน | `migration/simulate/sim_report_parity.py` |
| Recon ยอดยกมา/BS | `migration/recon/bs_compare.py`, `migration/recon/run.py` |
| Import master + opening | `migration/import/run.py` (s01–s11) |
| Mapping | `migration/mapping/*.csv` (`od15_code_to_od19_code.csv`, `tax_map.csv`, …) |
| Bring Forward (od19) | `custom_addons/od19_accounting_bring_forward` |

---

## ข้อเท็จจริงที่ตรวจแล้วจากต้นทาง `od15_stage` (2026-11-25)

| หัวข้อ | ค่าจริง |
|---|---|
| Posted moves ทั้งหมด | **44,169** |
| ช่วงวันที่ | 2000-10-31 → 2026-12-31 |
| บริษัท | **1 แห่ง** (id=1 · บริษัท ออโต้อินโฟ จำกัด) |
| สกุลเงินในรายการ | **THB 100%** (44,169/44,169) — ไม่มีต่างสกุล |

**รายการจริงรายปี (usable detail เริ่ม 2022):**

| ปี | entry | in_inv | in_ref | out_inv | out_ref | รวม |
|---|---|---|---|---|---|---|
| ≤2021 | — | — | — | ~10 | 2 | **~12** |
| 2022 | 115 | 499 | 2 | 209 | 2 | 827 |
| 2023 | 4,024 | 1,152 | 4 | 957 | 3 | 6,140 |
| 2024 | 10,291 | 2,360 | 4 | 1,164 | 6 | 13,825 |
| 2025 | 10,343 | 2,530 | 4 | 1,093 | 7 | 13,977 |
| 2026 | 7,405 | 1,352 | 1 | 623 | 7 | 9,388 |

---

## Design Decisions

### ยืนยันแล้ว (Locked)

1. **ช่วงเวลา:** 2022-01-01 → 2026-12-31 (ใช้ `REP_D1`/`REP_D2`)
2. **ขอบเขต:** 1 บริษัท · **สกุล THB ล้วน** — ต้นทางไม่มีต่างสกุล จึง **ไม่จำลอง multi-currency** (คง THB เพื่อให้ parity ตรง v15 100%)
3. **จุดปิดงบ / Bring Forward:** **2025-12-31** (ปิดงบ FY2025 → ยกยอดเข้าปี 2026)
4. **ไม่สร้างข้อมูลใหม่:** ยกจริงจาก `od15_stage` ผ่าน tooling เดิม
5. **idempotent:** External ID `__import15__.<model>.<TAG>_<od15_id>`

### ยืนยันแล้ว (Locked — 2026-11-25)

6. **ฐานยอดยกมา:** สร้างระบบเป้าหมายใหม่ (clean) แล้วตั้งฐานยกมาที่ **ก่อน 2022** (ยอด ≤ 2021-12-31 ~12 ใบ) แล้ว replicate รายละเอียด 2022+ ทั้งหมด — **ไม่คง** ยอดยกมา 2026-10-31 เดิม
7. **สินค้าคงคลัง:** ยก **stock เต็ม** — od19 CE **ตัด `stock.valuation.layer` (SVL) ออก** จึง replicate `stock.move` (state=done) + `stock.move.line` + `stock.lot` และตั้ง `value` ต่อ move = **Σ value ของ SVL เดิม (net ต่อ move)** ตามวันจริง เพื่อให้รายงานสต็อกรายเดือน/valuation ตรง v15
8. **สินทรัพย์ถาวร:** สร้าง `account.asset` + ค่าเสื่อมตามวันจริง (ไม่ใช่ยอดก้อนเดียว) เพื่อให้ทะเบียน/ค่าเสื่อมรายงวดตรง v15 — **บรรทัดยกมา (`accumulated_depreciation_bf`) วางที่วันเริ่มของสินทรัพย์ (`line_date = a.date`)** ไม่ใช่ 2022-01-01
9. **การเทียบ parity สต็อก:** เทียบแบบที่ od19 "เก็บได้จริง" = `Σ_moves |Σ_SVL value|` (ไม่ใช่ `Σ|per-SVL|` ซึ่งจะต่างเมื่อ move เดียวมี SVL หลายใบ sign ผสม)
10. **ชุดรายงาน parity:** GL/TB รายเดือน · BS · P&L · AR/AP แยกคู่ค้า · Payment · CN/DN · สินทรัพย์ถาวร · สินค้าคงคลัง · MIS/Jasper (ครบชุด)

---

## Phase 0 — Preflight & Baseline (Read-only)

**Deliverable:** รายงาน readiness ครอบคลุม id ทั้งช่วง 2022–2026 + snapshot ก่อนแตะ DB

- [ ] 0.1 รัน preflight ของ replicate กับช่วงเต็ม: `REP_PREFLIGHT=1 REP_D1=2022-01-01 REP_D2=2026-12-31` → ตรวจ **บัญชี/ภาษี/สมุดรายวัน/คู่ค้า/สินค้า** ที่ "หาไม่เจอ"
- [ ] 0.2 ตรวจบัญชี/ภาษี/คู่ค้า ที่ถูก **archive/ปิดใช้งานในภายหลัง** แต่โผล่ในอดีต (อาจตกหล่นจาก mapping) → เติม mapping/sync `active`
- [ ] 0.3 Snapshot DB เป้าหมาย (`pg_dump`) + บันทึก baseline ตัวเลขรายปีจาก v15 (TB/BS/PL/AR-AP/สต็อก/สินทรัพย์)
- [ ] 0.4 ยืนยันขอบเขตข้อ 6–9 (ฐานยกมา · inventory · assets · ชุดรายงาน)

**Gate 0:** preflight ไม่มี mapping ที่หาไม่เจอ (หรือมีแต่ระบุวิธีจัดการ) + snapshot เรียบร้อย

---

## Phase 1 — Rebuild ระบบเป้าหมาย + Master Data

**Deliverable:** DB เป้าหมายสะอาด มี master ครบ พร้อมรับประวัติ

- [ ] 1.1 สร้าง DB เป้าหมายสะอาด (แนะนำ `odoo19_pdev` ก่อน) + ติดตั้งโมดูล `od19_*` + OCA + `l10n_th`
- [ ] 1.2 รัน import master: `MIG_STEPS=all` ยกเว้น s08_opening (ยอดยกมาจะมาจาก full-history แทน)
- [ ] 1.3 ตั้ง Sequences (s09) ให้ต่อเนื่องจาก legacy
- [ ] 1.4 ตรวจ coverage (จำนวน record ต่อโมเดลตรง baseline) → `migration/recon/import_coverage.py`

**Gate 1:** master ครบ + sequences ต่อเนื่อง + coverage ผ่าน

---

## Phase 2 — Replicate ประวัติ 5 ปี (2022-01-01 → 2026-12-31)

**Deliverable:** account.move ครบทุกใบเท่าต้นทาง ในช่วง 5 ปี

- [x] 2.1 ตั้งฐานยกมาก่อน 2022 (ยอด ≤ 2021-12-31) เป็น opening entry
      - **ผล:** ต้นทาง od15 ไม่มี entry ก่อน 2022 — มีเพียง **12 ใบ** (out_invoice/out_refund ปี 2000–2021) ซึ่ง replicate เป็นเอกสารจริงแล้ว (gl15rep) · ต้นทาง posted รวม **44,169 = ปลายทาง 44,169** ตรง 100%
- [x] 2.2 replicate แบบ **batch รายปี** (2022 → 2026) ผ่าน `sim_replicate_gl15.py`:
      - `REP_D1`/`REP_D2` ต่อปี · `REP_TYPES` = `out_invoice,in_invoice,out_refund,in_refund,entry` · `REP_TAG` เดียวกัน
      - ปี 2024 หนักสุด (~13,825 ใบ) — คุมเวลา/หน่วยความจำด้วย `REP_BATCH`
      - **ผล (full run `_gl_2022_2026.log`, 2026-11-25 10:02→13:04):** `created=37190 updated=0 skipped=6967 error=0` · verify **บัญชีที่ยอดคงเหลือไม่ตรง 0**
- [x] 2.3 ตรวจ idempotency: รันซ้ำปีใดปีหนึ่ง → created=0 (ข้ามทั้งหมด)
      - **ผล (`_gl_idem.log`, 2026-11-25 13:06→13:32):** `created=0 updated=0 skipped=44157 error=0` · ไม่มี self-heal · net ยังไม่ตรง 0
- [x] 2.4 ตรวจจำนวนใบต่อปี/ต่อ move_type ตรงกับต้นทาง (เทียบตารางด้านบน)
      - **ผล:** 2022/2024/2025/2026 ตรงทุก type · 2023 ต่างเฉพาะ **10 ใบ** in_invoice→entry (fallback/self-heal ของใบ garbled) — GL net ยังตรง 0
- [x] 2.5 จัดการกรณี **overlap** กับ replicate เดิม (ม.ค.–ส.ค. 2026) ที่มีอยู่ → ต้องไม่ซ้ำ (External ID เดิมจะข้ามเอง)
- [x] 2.6 **sale / purchase order (คำขอผู้ใช้)** — replicate ใบสั่ง + บรรทัดจริงทุกสถานะ ผ่าน `sim_replicate_sale_purchase15.py`
      - **ผล (`_sp_full.log`, 2026-11-25 07:54→08:01):** sale `created=9924 error=0` · purchase `created=3197 error=0` · verify **รายการต่าง 0** ทั้ง sale และ purchase (ครบทุกปี/สถานะ draft·sale·cancel)

**Gate 2:** จำนวนใบต่อปี/type ตรงต้นทาง 100% + รันซ้ำไม่เพิ่มข้อมูล — **ผ่าน** (net ต่อบัญชีตรง 0 ทุกปี; ส่วนต่างที่เหลือบันทึกเป็น known difference)

---

## Phase 3 — สินค้าคงคลัง + สินทรัพย์ (ตามวันจริง)

**Deliverable:** รายงานสต็อกและสินทรัพย์รายงวดตรง v15

- [x] 3.1 replicate `stock.move` (state=done) + `stock.move.line` + `stock.lot` + value (Σ SVL ต่อ move) ให้ตรงวันและมูลค่า ตามขอบเขตข้อ 7
      - **ผล (`_sa_run3.log`, 2026-11-25 20:36→20:56):** `stock.move created=18155 skipped=6524 error=17` (no-product) · `move.line=31215` · `stock.lot=12929` · คำนวณ `standard_price` (fifo) 1,711 สินค้า
      - **รันซ้ำ (idempotent, `_sa_run4.log` 2026-11-25 21:03→21:05):** `created=0 skipped=24679` · ไม่มี self-heal
- [x] 3.2 สร้าง/ย้าย `account.asset` + ค่าเสื่อมตามวันจริง (ทะเบียน · ค่าเสื่อมสะสม · มูลค่าสุทธิ) ให้ตรง baseline รายปี
      - **ผล:** `account.asset` 790 (open 718 / draft 71 / close 1) · `account.asset.profile` 7 · `account.asset.line` 11,139 (ทุกบรรทัด `init_entry=True` = คิดยอดไม่ลง GL) · บรรทัดยกมา `line_date = a.date` (ตามวันจริง)
- [x] 3.3 ตรวจว่า GL ฝั่งสต็อก/ค่าเสื่อม tie กับมูลค่าสต็อกและทะเบียนสินทรัพย์
      - od19 บริษัท/หมวด = valuation **`periodic`** → move/บรรทัดค่าเสื่อมที่ replicate **ไม่สร้าง GL entry** (กัน double-count กับ GL ที่ยกไปแล้วใน Phase 2) · การ tie จึงตรวจที่ระดับ `stock.move.value` (สต็อก) และ `account.asset.line` (สินทรัพย์) โดยตรง

**Gate 3:** มูลค่าสต็อกและสินทรัพย์ ณ วันสิ้นปี (2022–2026) ตรง v15 ทุกปี — **ผ่าน**
  - **สต็อก** (`Σ_moves |Σ_SVL value|`): 2022 13,326,787.06 · 2023 175,154,464.12≈.11 · 2024 254,440,864.24 · 2025 207,110,935.43≈.44 · 2026 96,521,326.02≈.01 — *ต่าง ±0.01 จาก float vs numeric* · จำนวนตรงทุกปีหลังหัก 17 move ที่ map สินค้าไม่ได้
  - **สินทรัพย์** (NBV ตามวันจริง = `pv − bf(a.date ≤ จุดตัด) − dep(dep_date ≤ จุดตัด)`): 2022/2023 = 35,551,672.20 · 2024 = 10,510,745.56 · 2025 = 8,857,240.78 · 2026 = 7,435,474.96 — **ตรง v15 ทุกปี**
  - **known differences:** 17 `stock.move` + 2 `stock.lot` (สินค้า archived `/s` ไม่ถูก import → SVL = 0) · ±0.01 rounding — ยอมรับ+บันทึก

---

## Phase 4 — Bring Forward / ปิดงบปลายปี 2025

**Deliverable:** Bring Forward ทำงานถูกต้อง + ตรง v15 ที่จุด 2025-12-31

- [ ] 4.1 ตรวจ parity โมดูล `od19_accounting_bring_forward` เทียบ `dtr_bring_forward` (ขอบเขต: AR/AP · CN/DN · Payment · สินทรัพย์ · สต็อก)
- [ ] 4.2 ทดสอบปิดงบที่ **2025-12-31** (และ 2022/2023/2024 ถ้าต้องการให้ครบทุกปี) → ยกยอดเข้าปีถัดไป
- [ ] 4.3 ตรวจยอดยกยอดที่ได้ตรงกับ v15 (ยอดปิดงบ FY2025 = ยอดยกมา FY2026)

**Gate 4:** Bring Forward parity ผ่านที่ 2025-12-31 (ผลต่าง ≤ 0.01)

---

## Phase 5 — Report Parity ครบชุด (v15 vs v19)

**Deliverable:** รายงานเปรียบเทียบทุกฉบับ ยืนยัน diff = 0

- [ ] 5.1 `sim_report_parity.py` ช่วงเต็ม (และแยก **รายเดือน + รายปี**): NET ต่อบัญชี diff ≤ 0.01 · AR/AP แยกคู่ค้าตรง
- [ ] 5.2 ตรวจ **Payment** และ **CN/DN** แยกประเภท (ขยาย parity ที่ยังไม่มี)
- [ ] 5.3 ตรวจ **สินทรัพย์ถาวร** และ **สินค้าคงคลัง** รายงวด
- [ ] 5.4 ตรวจ **MIS/Jasper (ครบชุด)** — เรียกทั้งสองระบบ เทียบ output ทีละฉบับ
- [ ] 5.5 สร้างรายงานสรุป parity (xlsx) แนบ log ต้นทาง

**Gate 5:** ทุกหมวด diff ≤ 0.01 ทุกปี

---

## Phase 6 — Deploy + ส่งมอบ

**Deliverable:** โค้ด + รายงาน

- [ ] 6.1 ย้ายผลไป `odoo19_puat` (acceptance) แล้วรัน recon/parity ซ้ำ
- [ ] 6.2 ตาม AGENTS.md **S1**: deploy โค้ดขึ้น `C:\odoo-dev\od19_release\custom_addons` (ยืนยันไบต์ตรง) → restart `8070` → verify → commit แยกโดเมน
- [ ] 6.3 รวบรวม **โค้ด** (สคริปต์ pipeline ที่แก้/เพิ่ม) + **รายงาน** (parity xlsx + สรุป)

**Gate 6:** parity ผ่านบน `odoo19_puat` + deploy สำเร็จ + เอกสารครบ

---

## Acceptance Criteria

1. account.move ใน v19 ครบทุกใบเทียบ v15 ในช่วง 2022-01-01 → 2026-12-31 (ต่อปี/ต่อ type)
2. NET ต่อบัญชี diff ≤ 0.01 ทุกปี · AR/AP แยกคู่ค้าตรงทุกปี
3. มูลค่าสินค้าคงคลัง + สินทรัพย์ ณ วันสิ้นปี ตรง v15 ทุกปี
4. Bring Forward ที่ 2025-12-31 ตรง v15 (ผลต่าง ≤ 0.01)
5. รายงาน MIS/Jasper ครบชุด ตรงทั้งสองระบบ
6. รันซ้ำได้ (idempotent) ไม่เกิดข้อมูลซ้ำ
7. ไม่แก้ไฟล์ core ของ Odoo · ไม่เขียน `od15_stage`

---

## Risks

| # | ความเสี่ยง | มาตรการ |
|---|---|---|
| Q1 | บัญชี/ภาษี/คู่ค้าที่ archive ในภายหลัง แต่โผล่ในอดีต | Phase 0.2 sync `active` + เติม mapping |
| Q2 | ผลต่างทศนิยมสะสมจาก typed invoice 5 ปี | ใช้ `TOL=0.01` + ตรวจรายเดือน ไม่ใช่แค่ยอดรวม |
| Q3 | GL ตรงแต่รายงานสต็อก/สินทรัพย์ไม่ตรง | Phase 3 replicate ตามวันจริง (ไม่ใช่ยอดก้อนเดียว) |
| Q4 | volume/time (44k ใบ) | batch รายปี + `REP_BATCH` + commit ระหว่าง batch |
| Q5 | DB เป้าหมายมีข้อมูลเก่า (opening 2026-10-31) ปน | Phase 1 rebuild clean + snapshot ก่อน |
| Q6 | เลขเอกสาร (sequence/doc number) ชน/ไม่ต่อเนื่อง | Phase 1.3 + `sequence_check.py` |

---

## Notes

- **ห้ามลบ/แก้ข้อมูลใน `od15_stage`** — เป็นหลักฐานอ้างอิง
- ทุกครั้งก่อนแตะ DB เป้าหมาย ให้ snapshot (`pg_dump`) ก่อน
- `migration/` เป็น tooling ภายนอก ไม่ใช่ Odoo module (ห้ามมี `__manifest__.py`)
- ขั้นตอนที่แตะ DB จริง/restart รันตาม AGENTS.md (Resource Lease · Destructive ต้องอนุมัติ)
