# -*- coding: utf-8 -*-
"""s07_projects — โครงการ / Job No. / Analytic"""
import common


def run(stats):
    common.log("s07_projects: (scaffold) — ยังไม่ได้นำเข้าจริง")

    # TODO(โครงการ): นำเข้า project.project (name, partner_id, ...)
    #
    # TODO(Job No.): นำเข้าเลขงาน/Job Number ให้เป็นรหัสอ้างอิงของโครงการ
    #   (ตรวจฟิลด์จริงที่โมดูล od19_project_enhanced / od19_project_analytic กำหนด)
    #
    # TODO(Analytic): นำเข้า account.analytic.account + account.analytic.plan
    #   แล้วผูกกับโครงการ (โปรดทราบ: Odoo 19 แยก analytic.plan ออกจาก analytic.account)
    stats.skipped += 1
