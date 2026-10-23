from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, new_test_user


class TestPurchaseRequestAppAccess(TransactionCase):
    """The Purchase Requests app must work as a standalone app.

    Users belong to different teams: a Purchase Requests user must be able to
    work without being granted full Purchase access, and internal users without
    the Purchase Request group must be denied.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Request = cls.env["purchase.request"]
        cls.pr_user = new_test_user(
            cls.env,
            login="od19_pr_only_user",
            name="PR Only User",
            groups="base.group_user,purchase_request.group_purchase_request_user",
        )
        cls.plain_user = new_test_user(
            cls.env,
            login="od19_plain_internal_user",
            name="Plain Internal User",
            groups="base.group_user",
        )

    def test_purchase_request_shortcut_inside_purchase_app(self):
        menu = self.env.ref(
            "purchase_request.menu_purchase_request_pro_mgt",
            raise_if_not_found=False,
        )
        self.assertTrue(
            menu, "The Purchase Request shortcut must exist inside the Purchase app"
        )
        self.assertEqual(
            menu.parent_id, self.env.ref("purchase.menu_procurement_management")
        )

    def test_purchase_request_shortcut_is_restricted_to_pr_groups(self):
        menu = self.env.ref("purchase_request.menu_purchase_request_pro_mgt")
        self.assertTrue(
            menu.group_ids, "The shortcut must be restricted by groups"
        )
        xmlids = set(menu.group_ids.get_external_id().values())
        self.assertIn("purchase_request.group_purchase_request_user", xmlids)
        self.assertIn("purchase_request.group_purchase_request_manager", xmlids)

    def test_purchase_request_shortcut_visibility_follows_groups(self):
        menu = self.env.ref("purchase_request.menu_purchase_request_pro_mgt")
        self.assertIn(
            menu.id,
            self.env["ir.ui.menu"].with_user(self.pr_user)._visible_menu_ids(),
        )
        self.assertNotIn(
            menu.id,
            self.env["ir.ui.menu"].with_user(self.plain_user)._visible_menu_ids(),
        )

    def test_purchase_request_app_menu_uses_own_icon(self):
        menu = self.env.ref("purchase_request.parent_menu_purchase_request")
        self.assertTrue(menu)
        self.assertTrue((menu.web_icon or "").startswith("od19_purchase_request_extend,"))

    def test_pr_only_user_can_create_and_read_own_request(self):
        request = self.Request.with_user(self.pr_user).create(
            {"od19_priority": "normal"}
        )
        self.assertTrue(request.exists())
        self.assertEqual(request.requested_by, self.pr_user)
        request.with_user(self.pr_user).read(["name", "state"])

    def test_plain_internal_user_cannot_create_request(self):
        with self.assertRaises(AccessError):
            self.Request.with_user(self.plain_user).create(
                {"od19_priority": "normal"}
            )
