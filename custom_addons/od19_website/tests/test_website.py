from odoo import Command
from odoo.tests import HttpCase, tagged
from odoo.tests.common import TransactionCase


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
