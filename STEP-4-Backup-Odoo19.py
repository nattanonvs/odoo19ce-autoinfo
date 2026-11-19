"""STEP-4 : Standalone Odoo 19 database backup runner (รันนอกเซิร์ฟเวอร์หลัก).

เหตุผลที่ต้องรันนอกเซิร์ฟเวอร์:
    odoo.conf ตั้งค่า ``list_db = False`` เพื่อความปลอดภัย
    (ปิดหน้า /web/database/manager จากการเข้าถึงผ่าน Cloudflare)
    ทำให้ ``odoo.service.db.dump_db()`` ซึ่งถูกครอบด้วย
    ``@check_db_management_enabled`` โยน AccessDenied ทันที
    => OCA auto_backup ที่ทำงานเป็น cron ภายในเซิร์ฟเวอร์จะล้มเหลวเสมอ

สคริปต์นี้จึง:
    1. เปิด ``list_db`` เฉพาะโปรเซสของตัวเอง (ไม่กระทบเซิร์ฟเวอร์หลัก)
    2. เรียก ``db.backup.action_backup()`` เพื่อใช้ความสามารถของ OCA auto_backup
       - ตั้งชื่อไฟล์และโฟลเดอร์ตามข้อมูลในหน้า Database Backup
       - ลบไฟล์สำรองเก่าตาม days_to_keep
       - บันทึกผลสำเร็จ/ล้มเหลวลง chatter ของ record
    3. ตรวจความสมบูรณ์ของไฟล์ที่สร้าง (checksum + size)
       - คำนวณ SHA256 และขนาดไฟล์ของไฟล์สำรองที่สร้างล่าสุด
       - เขียน sidecar ``<ไฟล์สำรอง>.sha256`` ข้างไฟล์
       - ต่อท้ายบันทึก ``backups/backup-manifest.jsonl`` เพื่อให้ STEP-5 ตรวจเทียบภายหลัง

ข้อกำหนดของโปรเจกต์: ใช้ฐานข้อมูลเดียวคือ odoo19_pdev เท่านั้น

ใช้งาน:
    venv19\\Scripts\\python.exe STEP-4-Backup-Odoo19.py [--conf odoo.conf] [--db odoo19_pdev]
หรือเรียกผ่านตัวห่อสำหรับ Task Scheduler: STEP-4-Backup-Odoo19.ps1
"""

import argparse
import glob
import hashlib
import json
import os
import sys
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def _sha256_and_size(path):
    """คืนค่า (sha256_hex, size_bytes) ของไฟล์ แบบอ่านทีละ chunk"""
    h = hashlib.sha256()
    size = 0
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
            size += len(chunk)
    return h.hexdigest(), size


def _newest_backup(folder):
    """คืน path ของไฟล์สำรองล่าสุดในโฟลเดอร์ (mtime ใหม่สุด) หรือ None"""
    files = []
    for pattern in ("*.dump.zip", "*.dump"):
        files.extend(glob.glob(os.path.join(folder, pattern)))
    if not files:
        return None
    return max(files, key=os.path.getmtime)


def _record_checksum(folder, db_name, manifest_path):
    """คำนวณ checksum + size ของไฟล์สำรองล่าสุด แล้วบันทึก sidecar + manifest"""
    path = _newest_backup(folder)
    if not path:
        print(f"WARN: ไม่พบไฟล์สำรองใน {folder} (ข้ามการตรวจ checksum)")
        return
    digest, size = _sha256_and_size(path)

    with open(path + ".sha256", "w", encoding="utf-8") as fh:
        fh.write(f"{digest}  {os.path.basename(path)}\n")

    entry = {
        "ts": datetime.now().astimezone().isoformat(timespec="seconds"),
        "db": db_name,
        "file": os.path.basename(path),
        "size_bytes": size,
        "sha256": digest,
    }
    os.makedirs(os.path.dirname(manifest_path), exist_ok=True)
    with open(manifest_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(f"CHECKSUM {os.path.basename(path)} size={size} sha256={digest}")


def main():
    parser = argparse.ArgumentParser(description="Odoo 19 standalone database backup runner (STEP-4)")
    parser.add_argument(
        "--conf",
        default=os.path.join(PROJECT_ROOT, "odoo.conf"),
        help="path to odoo.conf (default: <project>/odoo.conf)",
    )
    parser.add_argument("--db", default="odoo19_pdev", help="database name (default: odoo19_pdev)")
    args = parser.parse_args()

    from odoo.tools import config as odoo_config

    odoo_config.parse_config(["-c", args.conf, "--database", args.db])

    # ปลดล็อกเฉพาะโปรเซสนี้ - ไม่ได้แก้ไฟล์ config ของเซิร์ฟเวอร์หลัก
    odoo_config["list_db"] = True

    from odoo.api import SUPERUSER_ID, Environment
    from odoo.modules.registry import Registry

    manifest_path = os.path.join(PROJECT_ROOT, "backups", "backup-manifest.jsonl")

    registry = Registry(args.db)
    with registry.cursor() as cr:
        env = Environment(cr, SUPERUSER_ID, {})
        backups = env["db.backup"].search([])
        if not backups:
            print("ERROR: ไม่พบรายการ Database Backup (db.backup) ในระบบ")
            return 1

        for rec in backups:
            print(f"backup target: {rec.name} (keep {rec.days_to_keep} days)")
        backups.action_backup()
        cr.commit()

        # ตรวจ checksum + size ของไฟล์ที่สร้างล่าสุด
        for rec in backups:
            _record_checksum(rec.folder, args.db, manifest_path)

    print("backup finished")
    return 0


if __name__ == "__main__":
    sys.exit(main())
