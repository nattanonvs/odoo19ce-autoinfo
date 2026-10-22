from datetime import timedelta

from odoo import Command, fields, http
from odoo.tests import tagged
from odoo.tests.common import (
    HOST,
    HttpCase,
    Opener,
    TransactionCase,
    get_db_name,
)


class TestWebsite(TransactionCase):
    """Basic tests for website company configuration fields."""

    def test_company_has_website_fields(self):
        company = self.env.user.company_id
        # Check default values are set
        self.assertEqual(company.od19_website_primary_color, "#9E2424")
        self.assertEqual(company.od19_website_secondary_color, "#f39200")
        self.assertTrue(company.od19_website_tagline)
        self.assertTrue(company.od19_website_hero_title)

    def test_company_website_fields_writable(self):
        company = self.env.user.company_id
        company.write({
            "od19_website_tagline": "New Tagline",
            "od19_website_primary_color": "#123456",
            "od19_website_secondary_color": "#654321",
            "od19_website_hero_title": "New Hero Title",
            "od19_website_hero_subtitle": "New Hero Subtitle",
            "od19_website_facebook_url": "https://facebook.com/test",
            "od19_website_linkedin_url": "https://linkedin.com/test",
            "od19_website_youtube_url": "https://youtube.com/test",
        })
        self.assertEqual(company.od19_website_tagline, "New Tagline")
        self.assertEqual(company.od19_website_primary_color, "#123456")
        self.assertEqual(company.od19_website_facebook_url, "https://facebook.com/test")


@tagged("post_install", "-at_install")
class TestWebsiteLanguageSwitch(HttpCase):
    """The navbar must expose a one-click EN | ไทย switch."""

    def test_language_switch_visible_with_two_languages(self):
        website = self.env["website"].get_current_website()
        thai = self.env["res.lang"]._activate_lang("th_TH")
        website.language_ids = website.language_ids | thai

        html = self.url_open("/").text

        self.assertIn("od19-lang-switch", html)
        # The switch is rendered once per header (desktop navbar + mobile
        # offcanvas), so every language option shows up at least once.
        self.assertGreaterEqual(html.count("od19-lang-opt"), 2)
        # Both languages are exposed as one-click options.
        self.assertIn('data-url_code="en"', html)
        self.assertIn('data-url_code="th"', html)


@tagged("post_install", "-at_install")
class TestEmployeePortalBooking(HttpCase):
    """The employee portal must expose the meeting-room booking panel."""

    def test_booking_panel_renders(self):
        thai = self.env["res.lang"]._activate_lang("th_TH")
        website = self.env["website"].get_current_website()
        website.language_ids = website.language_ids | thai

        tester = self.env["res.users"].create({
            "name": "Portal Tester",
            "login": "od19_portal_tester",
            "email": "od19.portal.tester@example.com",
            "group_ids": [Command.link(self.env.ref("base.group_user").id)],
        })
        # HttpCase patches the credential check, so only the login must exist.
        self.authenticate(tester.login, "test")

        # The panel renders one live tile per active room, so seed one instead
        # of relying on demo data being present in the test database.
        self.env["od19.meeting.room"].create({
            "name": "Portal Test Room",
            "capacity": 6,
        })

        html = self.url_open("/employee-portal").text

        # Live status tile per meeting room.
        self.assertGreaterEqual(html.count("od19-room-tile"), 1)
        # The compact booking form posts to the portal controller.
        self.assertIn("od19-booking-form", html)
        self.assertIn("/employee-portal/book-room", html)

    def _portal_tester(self, login):
        thai = self.env["res.lang"]._activate_lang("th_TH")
        website = self.env["website"].get_current_website()
        website.language_ids = website.language_ids | thai

        tester = self.env["res.users"].create({
            "name": login,
            "login": login,
            "email": "%s@example.com" % login,
            "group_ids": [Command.link(self.env.ref("base.group_user").id)],
        })
        # HttpCase patches the credential check, so only the login must exist.
        self.authenticate(tester.login, "test")
        return tester

    def test_room_tile_opens_schedule_popup(self):
        """Clicking a room must reveal when that room is already taken."""
        self._portal_tester("od19_portal_popup_tester")
        room = self.env["od19.meeting.room"].create({
            "name": "Popup Test Room",
            "capacity": 4,
        })

        html = self.url_open("/employee-portal").text

        # The tile is a modal trigger and the popup carries a lazy-loaded slot
        # that the frontend fills once the modal is shown.
        self.assertIn("od19-room-modal-%s" % room.id, html)
        self.assertIn("od19-room-schedule", html)
        self.assertIn("od19-room-hint", html)
        self.assertIn('data-bs-toggle="modal"', html)
        # The date picker is bounded on both ends of the booking window.
        self.assertIn("min=", html)
        self.assertIn("max=", html)

    def test_room_schedule_endpoint_returns_window(self):
        """The popup endpoint reports the room schedule as JSON."""
        tester = self._portal_tester("od19_portal_json_tester")
        room = self.env["od19.meeting.room"].create({
            "name": "JSON Test Room",
            "capacity": 4,
        })
        start_dt = fields.Datetime.now() + timedelta(days=3)
        self.env["od19.meeting.room.booking"].create({
            "name": "Upcoming Booking",
            "room_id": room.id,
            "organizer_id": tester.id,
            "participant_count": 2,
            "start_datetime": start_dt,
            "end_datetime": start_dt + timedelta(hours=1),
        })

        response = self.url_open(
            "/employee-portal/room-schedule?room_id=%s" % room.id
        )
        response.raise_for_status()
        payload = response.json()

        # The popup looks the same six months back as it does forward.
        self.assertEqual(payload["window_months"], 6)
        self.assertEqual(payload["room"]["id"], room.id)
        self.assertEqual(len(payload["upcoming"]), 1)
        self.assertEqual(payload["upcoming"][0]["name"], "Upcoming Booking")
        self.assertEqual(payload["upcoming"][0]["state_label"], "จองแล้ว")


@tagged("post_install", "-at_install")
class TestEmployeeLoginRedirect(HttpCase):
    """Employees land on the portal after login; everyone else keeps /odoo."""

    def setUp(self):
        super().setUp()
        self.session = http.root.session_store.new()
        self.session.update(http.get_default_session(), db=get_db_name())
        self.opener = Opener(self)
        self.opener.cookies.set("session_id", self.session.sid, domain=HOST, path="/")

    def _login(self, login, password):
        response = self.url_open("/web/login", data={
            "login": login,
            "password": password,
            "csrf_token": http.Request.csrf_token(self),
        })
        response.raise_for_status()
        return response

    def _make_user(self, login, *, with_employee):
        vals = {
            "name": login,
            "login": login,
            "password": login,
            "group_ids": [Command.link(self.env.ref("base.group_user").id)],
        }
        if with_employee:
            vals["employee_id"] = self.env["hr.employee"].create({"name": login}).id
        return self.env["res.users"].create(vals)

    def test_employee_login_lands_on_portal(self):
        user = self._make_user("od19_login_employee", with_employee=True)
        response = self._login(user.login, user.login)
        self.assertEqual(response.request.path_url, "/employee-portal")

    def test_other_login_lands_on_backend(self):
        user = self._make_user("od19_login_plain", with_employee=False)
        response = self._login(user.login, user.login)
        self.assertEqual(response.request.path_url, "/odoo")
