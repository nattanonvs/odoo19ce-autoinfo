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
        user = self.env["res.users"].create(vals)
        if with_employee:
            # ``res.users.employee_id`` is a non-stored compute filled from the
            # employees whose ``user_id`` points at the user, so the employee
            # has to be created on that side (writing ``employee_id`` directly
            # does nothing).
            self.env["hr.employee"].create({"name": login, "user_id": user.id})
            user.invalidate_recordset(["employee_id"])
        return user

    def test_employee_login_lands_on_portal(self):
        user = self._make_user("od19_login_employee", with_employee=True)
        response = self._login(user.login, user.login)
        self.assertEqual(response.request.path_url, "/employee-portal")

    def test_other_login_lands_on_backend(self):
        user = self._make_user("od19_login_plain", with_employee=False)
        response = self._login(user.login, user.login)
        self.assertEqual(response.request.path_url, "/odoo")


@tagged("post_install", "-at_install")
class TestBrandFoundation(HttpCase):
    """SP1: fixed brand logo + branded 404 page."""

    def test_header_uses_autoinfo_logo_svg(self):
        """The homepage header must render autoinfo_logo.svg as the logo."""
        html = self.url_open("/").text
        self.assertIn("autoinfo_logo.svg", html)

    def test_favicon_is_present(self):
        """Favicon link must point at the module favicon."""
        html = self.url_open("/").text
        self.assertIn("/od19_website/static/src/img/favicon.svg", html)

    def test_404_page_is_branded(self):
        """A non-existent URL returns the Auto-Info branded 404 page."""
        response = self.url_open("/this-page-does-not-exist-12345")
        self.assertEqual(response.status_code, 404)
        html = response.text
        # Branded elements from od19_404 template
        self.assertIn("od19-404-wrap", html)
        self.assertIn("autoinfo_logo.svg", html)
        self.assertIn("404", html)
        # Link back home must be present
        self.assertIn('href="/"', html)


@tagged("post_install", "-at_install")
class TestNavigationIA(HttpCase):
    """SP2: public navigation excludes staff links, inner pages carry breadcrumbs."""

    def test_employee_portal_not_in_public_nav(self):
        """The staff-only /employee-portal page must not be a public menu item."""
        # The legacy menu record is either never declared (fresh install) or
        # removed by website.menu.od19_configure_menus() (upgrade).
        self.assertFalse(
            self.env.ref(
                "od19_website.menu_employee_portal", raise_if_not_found=False
            )
        )
        website = self.env["website"].get_current_website()
        portal_menus = website.menu_id.child_id.filtered(
            lambda m: (m.url or "").strip().rstrip("/") == "/employee-portal"
        )
        self.assertFalse(portal_menus, "Employee Portal must not be a top nav item")

    def test_footer_has_employee_portal_link(self):
        """Staff still reach the portal through the discreet footer link."""
        html = self.url_open("/").text
        self.assertIn('class="od19-footer-staff"', html)
        self.assertIn('href="/employee-portal"', html)

    def test_inner_pages_have_breadcrumb(self):
        """Every inner content page exposes a breadcrumb linked back home."""
        for path in (
            "/industrial-automation",
            "/building-automation",
            "/terminal-automation",
            "/products",
            "/about-us",
            "/quality-certifications",
            "/portfolio",
        ):
            html = self.url_open(path).text
            self.assertIn(
                '<nav class="od19-breadcrumb">',
                html,
                "missing breadcrumb on %s" % path,
            )
            self.assertIn(
                '<a href="/">Home</a>',
                html,
                "breadcrumb on %s must link back home" % path,
            )


@tagged("post_install", "-at_install")
class TestHomepageSP3(HttpCase):
    """SP3: homepage hero polish, process narrative and animated stats."""

    def test_homepage_hero_has_sheen_and_scroll_cue(self):
        """The hero carries the animated sheen layer and a scroll cue to services."""
        html = self.url_open("/").text
        self.assertIn("od19-home-hero", html)
        self.assertIn("od19-hero-sheen", html)
        self.assertIn('class="od19-hero-scroll"', html)
        self.assertIn('href="#services"', html)

    def test_homepage_has_process_section(self):
        """"How We Work" tells the four-step delivery story."""
        html = self.url_open("/").text
        self.assertIn('id="how-we-work"', html)
        self.assertGreaterEqual(
            html.count("od19-step-num"),
            4,
            "the process section must render four numbered steps",
        )

    def test_homepage_stats_are_countup_ready(self):
        """Every stat number exposes the data hooks used by od19_home.js."""
        html = self.url_open("/").text
        self.assertGreaterEqual(
            html.count("data-od19-count"),
            4,
            "all four stats must be animatable",
        )

    def test_homepage_section_anchors(self):
        """Every main block is deep-linkable through a stable anchor id."""
        html = self.url_open("/").text
        for anchor in (
            "services",
            "how-we-work",
            "about",
            "products",
            "partners",
            "news",
            "careers",
            "contact",
        ):
            self.assertIn('id="%s"' % anchor, html, "missing anchor #%s" % anchor)


@tagged("post_install", "-at_install")
class TestProductsServicesSP4(HttpCase):
    """SP4: products catalog and service pages share one content source."""

    def test_catalog_is_single_source_of_truth(self):
        """The catalog lives on the website model and covers three domains."""
        products = self.env["website"].od19_products()
        self.assertEqual(len(products), 25)
        by_dept = {}
        for product in products:
            by_dept[product["dept"]] = by_dept.get(product["dept"], 0) + 1
        self.assertEqual(by_dept, {"industrial": 9, "building": 8, "terminal": 8})

    def test_products_page_shows_filter_counts(self):
        """Each filter pill is labelled with the live number of products."""
        html = self.url_open("/products").text
        self.assertEqual(html.count("od19-pc-count"), 4)
        for count in ("25", "9", "8"):
            self.assertIn(
                'class="od19-pc-count">%s<' % count,
                html,
                "missing filter count %s" % count,
            )

    def test_products_page_links_to_service_pages(self):
        """Every department links through to its service page."""
        html = self.url_open("/products").text
        for url in (
            "/industrial-automation",
            "/building-automation",
            "/terminal-automation",
        ):
            self.assertIn('href="%s"' % url, html, "missing cross-link to %s" % url)
        self.assertEqual(html.count("od19-pc-dept-link"), 3)

    def test_products_hero_stats_reflect_catalog(self):
        """Hero stats are derived from the catalog, not hard-coded."""
        html = self.url_open("/products").text
        self.assertIn("25+", html)
        self.assertIn("<span>Product Brands</span>", html)
        self.assertNotIn("Global Brands", html)

    def test_service_pages_have_related_products(self):
        """Each service page cross-links back to the shared catalog."""
        for path in (
            "/industrial-automation",
            "/building-automation",
            "/terminal-automation",
        ):
            html = self.url_open(path).text
            self.assertGreaterEqual(
                html.count("od19-rel-card"),
                4,
                "%s must show at least four related products" % path,
            )
            self.assertIn(
                'href="/products"',
                html,
                "%s must link back to the catalog" % path,
            )


@tagged("post_install", "-at_install")
class TestTrustReferencesSP5(HttpCase):
    """SP5: quality-certifications and portfolio share one content source."""

    def test_trust_content_is_single_source_of_truth(self):
        """Certifications and references both live on the website model."""
        certs = self.env["website"].od19_certifications()
        self.assertEqual(
            [c["key"] for c in certs],
            ["iso9001", "iso14001", "gmp", "csv"],
        )

        projects = self.env["website"].od19_projects()
        self.assertEqual(len(projects), 9)
        by_sector = {}
        for project in projects:
            by_sector[project["sector"]] = by_sector.get(project["sector"], 0) + 1
        self.assertEqual(by_sector, {"industrial": 3, "building": 3, "terminal": 3})

    def test_quality_page_renders_certifications(self):
        """/quality-certifications shows every certificate with a status badge."""
        html = self.url_open("/quality-certifications").text
        self.assertGreaterEqual(html.count("od19-cert-card"), 4)
        self.assertIn("ISO 9001:2015", html)
        self.assertIn("ISO 14001", html)
        # Status badges are driven by each certificate's status field.
        self.assertIn("od19-cert-certified", html)
        self.assertIn("od19-cert-in_progress", html)
        self.assertEqual(
            html.count("od19-accred-chip"),
            len(self.env["website"].od19_accreditations()),
        )

    def test_quality_page_shows_configured_certificate(self):
        """Certificate body / number appear only once set in the backend."""
        company = self.env["website"].get_current_website().company_id
        company.write({
            "od19_website_cert_body": "SGS (Thailand) Ltd.",
            "od19_website_cert_no": "TH-QM-12345",
        })
        # The page response is cached for anonymous visitors for an hour and a
        # company write does not invalidate that cache, so drop it before each
        # fetch to observe the current backend values.
        self.env.registry.clear_cache()
        html = self.url_open("/quality-certifications").text
        self.assertIn("od19-cert-body", html)
        self.assertIn("SGS (Thailand) Ltd.", html)
        self.assertIn("od19-cert-no", html)
        self.assertIn("TH-QM-12345", html)

        # With no certificate on file the page invites the visitor to ask.
        company.write({
            "od19_website_cert_body": False,
            "od19_website_cert_no": False,
            "od19_website_cert_valid_until": False,
        })
        self.env.registry.clear_cache()
        html = self.url_open("/quality-certifications").text
        self.assertIn("od19-cert-request", html)

    def test_portfolio_page_renders_grid_and_filter(self):
        """/portfolio shows the reference grid with a live sector filter."""
        html = self.url_open("/portfolio").text
        self.assertEqual(html.count("od19-proj-card"), 9)
        self.assertEqual(html.count("od19-pc-pill"), 4)
        self.assertEqual(html.count("od19-pc-count"), 4)
        for count in ("9", "3"):
            self.assertIn(
                'class="od19-pc-count">%s<' % count,
                html,
                "missing filter count %s" % count,
            )
        for sector in ("industrial", "building", "terminal"):
            self.assertEqual(
                html.count('data-dept="%s"' % sector),
                3,
                "sector %s must list three references" % sector,
            )

    def test_new_pages_are_linked_from_home_about_and_footer(self):
        """Home, About and the footer all link to the two new trust pages."""
        for path in ("/", "/about-us"):
            html = self.url_open(path).text
            self.assertIn(
                'href="/quality-certifications"',
                html,
                "%s must link to the quality page" % path,
            )
            self.assertIn(
                'href="/portfolio"',
                html,
                "%s must link to the references page" % path,
            )

