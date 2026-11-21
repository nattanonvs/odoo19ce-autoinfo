# 04. Delivery Pipeline (time-box) · Commit · Push · Deploy

> **EN**: Code is promoted by stages with time-boxed auto-advance: silence within the window = approval. Any explicit user command overrides. · **TH**: โค้ดไหลผ่าน stage แบบมีกรอบเวลา ถ้าเงียบภายในกรอบ = ถือว่าผ่าน คำสั่งจากผู้ใช้ทุกเมื่อมีอำนาจเหนือกว่า

**หลักการ**: แยกโดเมนการ deploy ตามปลายทาง · `odoo19_pdev` = อัตโนมัติ · ปลายทางอื่นเลื่อนด้วยกรอบเวลา · merge เข้า `19.0` ต้องอนุมัติ

---

## 1. ภาพรวม Pipeline

| Stage | ปลายทาง | เงื่อนไขเริ่ม | เงื่อนไขเลื่อนไป stage ถัดไป |
|---|---|---|---|
| **S1** | `odoo19_pdev` (+ commit) | แก้/สร้างโมดูล + Test ผ่าน | ทันที (อัตโนมัติ) |
| **S2** | `odoo19_puat` (+ push) | ติดตั้ง pdev สำเร็จ | **+24 ชม.** ไม่มีคำสั่ง/ผลตรวจ |
| **S3** | PR → `19.0` | push สำเร็จ | **+24 ชม.** ไม่มีคำสั่ง → สร้าง PR แล้ว **รออนุมัติ merge** |
| **S4** | Cleanup | merge เข้า `19.0` แล้ว | **+7 วัน** + ไฟล์ตรงกันทุกไบต์ |

**นิยาม "ไม่มีคำสั่ง/ผลตรวจ" (silence)**: ภายในกรอบเวลา ผู้ใช้ไม่ได้ส่งข้อความใด ๆ ที่ (ก) สั่ง *พัก/hold* (ข) ปฏิเสธ/rollback (ค) ให้ความเห็นให้แก้ สำหรับงานนั้น → ถ้าเงียบครบกรอบ **ถือว่าผ่าน** ให้เลื่อน stage
ถ้ามีคำสั่งใด ๆ → **หยุดที่ stage นั้น** รอจัดการตามคำสั่งก่อน

---

## 2. S1 — `odoo19_pdev` (อัตโนมัติ ไม่ต้องขออนุมัติ)

> **เทสต์ผ่าน = ใบอนุญาตทำ S1** — เมื่อ Unit Test ผ่าน (0 failed / 0 error) ให้ agent **ดำเนินการ S1 ทันทีในรอบงานเดียวกัน ห้ามหยุดถาม/รออนุมัติก่อน** และไม่ต้องรอผู้ใช้สั่ง "ไปต่อ"
> การถือ lease เป็น *ขั้นตอนปฏิบัติ* เพื่อกันเขียนชนกัน **ไม่ใช่การขออนุมัติ** — ให้จับแล้วทำต่อได้เลย

ทุกครั้งที่ **แก้ไขโค้ดในโมดูล หรือสร้างโมดูลใหม่** และ **ผ่านการทดสอบแล้ว** ให้ agent:
1. **ติดตั้ง (`-i`) / อัปเดต (`-u`) ลง `odoo19_pdev` ทันที** — เฉพาะโมดูลที่แตะ รันแบบ `--stop-after-init`
2. **restart instance หลัก (`8070`) หากจำเป็น** — ตาม [02-isolation.md §4](02-isolation.md) (เจาะจง PID / command line เดิม, หลีกเลี่ยง `STEP-3-Start-Odoo19.ps1`)
   > ข้อยกเว้นเดียวของ S1: การปิด/รีสตาร์ท instance แชร์ (`8070`) ยังเป็น **Destructive (HARD LOCK)** ต้องอนุมัติเป็นรายครั้ง (ดู [01-capabilities.md §4](01-capabilities.md)) — ส่วนที่เหลือของ S1 เดินเองได้
3. **commit ทันที โดยแยกโดเมน** — 1 commit = 1 โดเมน (ดู §7) ระบุไฟล์เจาะจง **ห้ามปะปนโค้ดที่ไม่เกี่ยวข้อง** และ **ระวังทำโค้ดหาย**
4. บันทึก `pdev_at` + commit SHA ลง ledger (§5)

ก่อนเขียนต้องถือ lease `db:odoo19_pdev` เสมอ และปล่อยทันทีเมื่อจบ (`try/finally`)

## 3. S2 — `odoo19_puat` + push (time-box 24 ชม.)

- เมื่อติดตั้ง pdev สำเร็จ บันทึก `pdev_at` แล้วเริ่มจับเวลา **24 ชั่วโมง**
- ถ้าผ่านไป **24 ชม. โดยไม่มีคำสั่ง/ผลตรวจ** → **ถือว่าผ่าน** ให้ agent:
  1. ถือ lease `db:odoo19_puat` → **ติดตั้ง (`-i`) / อัปเดต (`-u`) ลง `odoo19_puat`** (เฉพาะโมดูลที่แตะ) → ปล่อย lease
  2. **restart `odoo19_puat` หากจำเป็น**
  3. **`push`** branch งานของตัวเองขึ้น remote (`feature/*`, `codex/*`, `trae/*`)
  4. บันทึก `puat_at` + `pushed_at` + commit SHA ลง ledger

## 4. S3 — PR → `19.0` (time-box 24 ชม. + รออนุมัติ merge)

- เมื่อ push สำเร็จ บันทึก `pushed_at` แล้วเริ่มจับเวลา **24 ชั่วโมง**
- ถ้าผ่านไป **24 ชม. โดยไม่มีคำสั่ง** → **ถือว่าผ่าน** ให้ agent:
  1. **เปิด Pull Request** (`feature/*` → `19.0`) พร้อม Release Notes
  2. บันทึก `pr_url` + `pr_at` ลง ledger
  3. **รออนุมัติจากผู้ใช้เพื่อ merge — ห้าม merge เอง** (push เข้า `19.0` เป็น Destructive)

## 5. Ledger — `.agent-locks/delivery-pipeline.json`

บันทึกสถานะ pipeline ต่อโดเมน (อยู่ใน `.gitignore` ห้าม commit) รูปแบบ:

```json
{
  "items": [
    {
      "domain": "od19_hr_expense_enhanced",
      "branch": "feature/od19_hr_expense_enhanced",
      "worktree": "C:\\odoo-dev\\od19_hex",
      "commit": "<sha>",
      "pdev_at": "2026-11-20T10:00:00+07:00",
      "puat_at": null,
      "pushed_at": null,
      "pr_url": null,
      "pr_at": null,
      "merged_at": null,
      "status": "pdev",
      "hold": false
    }
  ]
}
```

- `status` ∈ `pdev` → `puat` → `pr` → `merged` → `cleaned`
- `hold: true` = หยุด pipeline รอคำสั่ง (ไม่มีการเลื่อน stage อัตโนมัติ)

**Override จากผู้ใช้ (ใช้ได้ทุกเมื่อ)**: ระบุ "ไปต่อ/promote" · "พัก/hold" · "ถอย/rollback" → agent อัปเดต ledger และปฏิบัติตาม

## 6. S4 — Verify 7 วัน + Auto-cleanup

หลัง `merge` เข้า `19.0` บันทึก `merged_at` แล้วเริ่มจับเวลา **7 วัน**

ถ้าผ่านไป **7 วัน โดยไม่มีคำสั่ง** → **ถือว่าผ่าน** ให้ agent ตรวจและทำความสะอาด:
1. **ตรวจว่าไฟล์ที่ merge ตรงกับ folder ต้นทางที่ใช้ merge ทุกไบต์**:
   `git diff --stat 19.0:<path> <source-branch-tip>:<path>` ต้อง **ว่าง**
2. ถ้า **ตรงกัน** → ถือ lease `git:worktree` แล้วทำความสะอาด:
   - **ลบ source branch** ที่ merge แล้ว (`feature/*`) — Shared-Resource
   - **ลบ worktree** ต้นทาง (`git worktree remove`) — Shared-Resource
   - **ลบไฟล์ TEST** ของงานนั้น (`_*.py`, `_*.txt`, `data_test_*`, `*.bak`)
   - **drop DB TEST** ของ agent (`odoo19_t_<AGENT_ID>`)
   - อัปเดต ledger `status: cleaned`
3. ถ้า **ไม่ตรงกัน** → **ห้ามลบ** ให้รายงานความต่างให้ผู้ใช้ทราบก่อน

> **Guard**: cleanup จะทำได้เฉพาะเมื่อยืนยัน "ตรงกันทุกไบต์" แล้วเท่านั้น และห้ามลบ branch/worktree ของ agent อื่น

## 7. กฎการ commit (Write-Scope)

- **ต้องรัน Unit Test ให้ผ่านก่อน commit/push** (0 failed / 0 error) — บน DB ทดสอบของตัวเอง
- รูปแบบ Conventional Commits: `<type>(<scope>): <description>`
  - type: `feat` `fix` `docs` `style` `refactor` `perf` `test` `build` `ci` `chore` `revert`
- 1 commit = 1 โดเมนงาน ห้ามรวมหลายโดเมนใน commit เดียว
- บรรทัดแรกใช้ present tense / imperative mood และยาวไม่เกิน 72 ตัวอักษร
- ระบุไฟล์เป็นรายชื่อชัดเจน (`git add <path>` หรือ `git commit -- <path>`) **ห้าม** `git add -A` หรือ `git add .`
- ห้าม commit ไฟล์ที่ `.gitignore` ครอบไว้ — ตรวจก่อนด้วย `git check-ignore -v --no-index <path>`

## 8. กฎการ push (Write-Scope — branch งานตัวเอง)

- push ได้เฉพาะ branch งานของตัวเอง (`feature/*`, `codex/*`, `trae/*`)
- ห้าม push ตรงเข้า `19.0` / `main` / `master`
- **ห้าม rebase / force branch ที่ push ขึ้น remote แล้ว** (ยกเว้น branch ตัวเองที่ยังไม่มีใครใช้)
- ถ้า push ถูก reject เพราะ remote ใหม่กว่า → หยุดและรายงาน ห้ามใช้ force
- หลัง push ต้องรายงาน URL ของ commit/PR ให้ผู้ใช้ทราบ

## 9. ตัวนับรวมการติดตั้ง/อัปเดต (cumulative counter)

- นับรวมทุกครั้งที่ติดตั้ง/อัปเดต ข้ามทุก DB และทุก worktree เพิ่มทีละ 1 พร้อมบันทึกชื่อแอปที่แตะ
- **จุดขออนุมัติซ้ำ**: เมื่อตัวนับรวมถึง **10 ครั้ง หรือรายการแอปครบ 10 แอป (อย่างใดถึงก่อน)** ให้ agent **หยุดก่อนติดตั้ง** แล้วถามผู้ใช้ว่าจะให้ติดตั้ง/อัปเดตลง db server ใด พร้อมเสนอรายชื่อ DB (เช่น `odoo19_pdev`, `odoo19_puat`, DB ทดสอบของ agent) — เมื่อผู้ใช้ยืนยันจึงดำเนินการต่อ **แล้วรีเซ็ตตัวนับเป็น 0**
- ตัวนับเก็บที่ `.agent-locks/app-install-counter.json` (อยู่ใน `.gitignore` แล้ว) รูปแบบ:

  ```json
  { "count": 0, "apps": [], "last_db": "", "updated_at": "2026-11-20T00:00:00+07:00" }
  ```

- แผนงานที่กำหนดรอบการติดตั้งไว้ชัดเจนอยู่แล้ว (เช่น โครงการที่ระบุ Phase) ให้ยึดแผนนั้นก่อน
