"""Standalone Odoo 19 database backup runner (รันนอกเซิร์ฟเวอร์หลัก).

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

ใช้งาน:
    venv19\\Scripts\\python.exe backup_odoo19.py [--conf odoo.conf] [--db odoo19]
หรือเรียกผ่านตัวห่อสำหรับ Task Scheduler: backup_odoo19.ps1
"""

import argparse
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def main():
    parser = argparse.ArgumentParser(description="Odoo 19 standalone database backup runner")
    parser.add_argument(
        "--conf",
        default=os.path.join(PROJECT_ROOT, "odoo.conf"),
        help="path to odoo.conf (default: <project>/odoo.conf)",
    )
    parser.add_argument("--db", default="odoo19", help="database name (default: odoo19)")
    args = parser.parse_args()

    from odoo.tools import config as odoo_config

    odoo_config.parse_config(["-c", args.conf, "--database", args.db])

    # ปลดล็อกเฉพาะโปรเซสนี้ - ไม่ได้แก้ไฟล์ config ของเซิร์ฟเวอร์หลัก
    odoo_config["list_db"] = True

    from odoo.api import SUPERUSER_ID, Environment
    from odoo.modules.registry import Registry

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

    print("backup finished")
    return 0


if __name__ == "__main__":
    sys.exit(main())
