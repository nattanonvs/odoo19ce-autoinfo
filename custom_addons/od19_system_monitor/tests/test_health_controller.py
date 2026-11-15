# Copyright 2026 TRAE
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

"""ทดสอบปลายทาง HTTP (P2): health / detail / heartbeat."""

from odoo import fields
from odoo.tests import HttpCase, tagged

PARAM_HEARTBEAT_TOKEN = "od19_health.heartbeat_token"


@tagged("post_install", "-at_install")
class TestHealthController(HttpCase):
    """ทดสอบสัญญาณสั้น รายละเอียดสำหรับผู้ดูแล และการรับ heartbeat."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.dbname = cls.env.cr.dbname
        # ปิดการตรวจชุดเริ่มต้นเพื่อให้สถานะรวมในแต่ละเทสต์แน่นอน
        cls.env["od19.health.check"].search([]).write({"active": False})
        group_user = cls.env.ref("base.group_user")
        group_manager = cls.env.ref(
            "od19_system_monitor.group_od19_health_manager"
        )
        cls.plain_user = cls.env["res.users"].create(
            {
                "name": "Health Plain",
                "login": "od19_health_plain",
                "password": "od19_health_plain",
                "group_ids": [(6, 0, [group_user.id])],
            }
        )
        cls.manager_user = cls.env["res.users"].create(
            {
                "name": "Health Manager",
                "login": "od19_health_manager",
                "password": "od19_health_manager",
                "group_ids": [(6, 0, [group_user.id, group_manager.id])],
            }
        )

    def _check_with_state(self, state):
        check = self.env["od19.health.check"].create(
            {
                "name": "HTTP Check",
                "code": "http_check_%s" % state,
                "check_type": "custom",
                "active": True,
            }
        )
        check.write({"last_run": fields.Datetime.now(), "last_state": state})
        return check

    def _probe(self, url, **kwargs):
        """เรียกปลายทาง auth='none' แบบ stateless พร้อมระบุ db ผ่าน header.

        ปลายทาง auth='none' จะถูกจับคู่ผ่าน nodb router เฉพาะเมื่อไม่ทราบ db
        ซึ่ง nodb router มีแต่ server-wide modules (base/web) จึงต้องระบุ db
        ผ่าน header X-Odoo-Database เหมือนที่ probe ภายนอกใช้
        """
        headers = dict(kwargs.pop("headers", None) or {})
        headers.setdefault("X-Odoo-Database", self.dbname)
        return self.url_open(url, headers=headers, **kwargs)

    # ------------------------- /od19/health -------------------------
    def test_health_endpoint_ok(self):
        self._check_with_state("ok")
        response = self._probe("/od19/health")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "ok")
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["monitor"], "od19_system_monitor")

    def test_health_endpoint_critical_returns_503(self):
        self._check_with_state("critical")
        response = self._probe("/od19/health")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["status"], "critical")

    # ------------------------- /od19/health/detail -------------------------
    def test_detail_requires_permission(self):
        self.authenticate("od19_health_plain", "od19_health_plain")
        response = self.url_open("/od19/health/detail")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"], "forbidden")

    def test_detail_allows_manager(self):
        self._check_with_state("ok")
        self.authenticate("od19_health_manager", "od19_health_manager")
        response = self.url_open("/od19/health/detail")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("checks", payload)
        self.assertIn("incidents", payload)

    # ------------------------- /od19/health/heartbeat -------------------------
    def test_heartbeat_accepts_payload(self):
        self.env["ir.config_parameter"].sudo().set_param(PARAM_HEARTBEAT_TOKEN, "")
        response = self._probe(
            "/od19/health/heartbeat",
            json={"code": "wb-http", "overall": "ok"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        wd = self.env["od19.health.watchdog"].search([("code", "=", "wb-http")])
        self.assertTrue(wd)
        self.assertEqual(wd.last_status, "ok")

    def test_heartbeat_rejects_invalid_json(self):
        response = self._probe(
            "/od19/health/heartbeat",
            data="not-json",
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "invalid-json")

    def test_heartbeat_rejects_wrong_token(self):
        self.env["ir.config_parameter"].sudo().set_param(
            PARAM_HEARTBEAT_TOKEN, "secret-token"
        )
        response = self._probe(
            "/od19/health/heartbeat",
            json={"code": "wb-http", "overall": "ok"},
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"], "invalid-token")

    def test_heartbeat_accepts_correct_token(self):
        self.env["ir.config_parameter"].sudo().set_param(
            PARAM_HEARTBEAT_TOKEN, "secret-token"
        )
        response = self._probe(
            "/od19/health/heartbeat",
            json={"code": "wb-http", "overall": "ok", "token": "secret-token"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
