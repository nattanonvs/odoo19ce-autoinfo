from odoo.tests import tagged
from odoo.tests.common import HttpCase


@tagged("post_install", "-at_install")
class TestOd19DraftAssets(HttpCase):
    def _backend_asset_urls(self):
        assets = self.env["ir.qweb"]._get_asset_content("web.assets_backend")[0]
        return [asset["url"] for asset in assets]

    def _frontend_asset_urls(self):
        assets = self.env["ir.qweb"]._get_asset_content("web.assets_frontend")[0]
        return [asset["url"] for asset in assets]

    def test_backend_assets_in_bundle(self):
        urls = self._backend_asset_urls()
        for path in (
            "/od19_offline_draft/static/src/draft_service.js",
            "/od19_offline_draft/static/src/draft_banner.js",
            "/od19_offline_draft/static/src/draft_banner.xml",
            "/od19_offline_draft/static/src/form_controller_patch.js",
            "/od19_offline_draft/static/src/offline_draft.scss",
        ):
            self.assertIn(path, urls)

    def test_frontend_asset_in_bundle(self):
        self.assertIn(
            "/od19_offline_draft/static/src/portal/portal_autosave.js",
            self._frontend_asset_urls(),
        )
