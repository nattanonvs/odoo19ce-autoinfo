# 05. Security (ความปลอดภัย · ขอบเขตไฟล์ · ข้อมูลลับ)

> **EN**: Don't touch Odoo core; never commit secrets; never hard-code credentials. · **TH**: ห้ามแก้ core ของ Odoo · ห้าม commit ข้อมูลลับ · ห้ามฝัง credential

## 1. ขอบเขตการแก้ไขไฟล์ (File scope)

- **ห้ามแก้ไฟล์ core ของ Odoo** (`odoo/`, `addons/`) — แก้ได้เฉพาะ `custom_addons/` และ config ของโปรเจกต์
- ห้ามฝัง credential ลงในคำสั่ง/สคริปต์ ให้อ่านค่าจาก `odoo.conf` ตอนรัน
- ใช้ฐานข้อมูลหลัก `odoo19_pdev` สำหรับงานที่แชร์ (งานส่วนตัวใช้ DB ทดสอบของตัวเอง)
- สคริปต์ `.ps1` ต้องเป็น UTF-8 **with BOM** เพื่อกัน parsing error ภาษาไทยบน Windows
- ใช้ PowerShell 7 (pwsh) รันสคริปต์เพื่อรองรับ UTF-8

## 2. ไฟล์ที่ห้าม commit เด็ดขาด (Never commit)

- `odoo.conf` (มี `db_password`) — ถูก ignore ที่ `.gitignore:28` แล้ว
- `.env`, `*.key`, `*.pem`, `*.p12`, `id_rsa*`, `credentials*.json`
- `backups/` (ข้อมูลจริง) — ignore ที่ `.gitignore:69`
- `data/`, `data_test/`, `venv19/`, `pylibs/`, `wkhtmltopdf/bin/`, `.agent-locks/`

## 3. การตรวจก่อน commit

ก่อน commit ทุกครั้ง ให้ตรวจ `git diff --cached --name-only` ว่าไม่มีไฟล์ตามรายการข้างต้น
