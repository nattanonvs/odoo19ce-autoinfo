from odoo import api, models

# Labels used by an app for its "Configuration" menu. Thai labels are included
# because a few menus are named in Thai directly in the source XML.
CONFIGURATION_MENU_LABELS = ("Configuration", "ตั้งค่า", "การตั้งค่า")

# Order of the apps in the app switcher, grouped into business-flow *clusters*
# so that the apps used together sit next to each other: front office, finance,
# marketing, procurement, projects, people, website/content and finally the
# internal tools. Each entry is ``(cluster_label, (menu_xmlid, ...))``.
#
# The label is documentation only -- the Odoo 19 switcher is a flat grid with
# no folders or group headers -- so the clustering is expressed purely through
# the ``sequence`` handed out below: every cluster owns its own block of
# sequence numbers (see APP_MENU_CLUSTER_GAP) and the apps inside a cluster are
# ordered by their position in the tuple. Apps of modules that are not
# installed are skipped, so the list may safely reference optional modules.
# Only *top-level* menus may be listed: the sequence is applied whatever the
# menu's parent, so a section of another application would be pushed to the
# end of that application instead of being ordered inside it.
APP_MENU_CLUSTERS = (
    ("Front office", (
        "mail.menu_root_discuss",
        "calendar.mail_menu_calendar",
        "contacts.menu_contacts",
        "crm.crm_menu_root",
        "sale.sale_menu_root",
        "point_of_sale.menu_point_root",
    )),
    ("Finance and analytics", (
        "account.menu_finance",
        "spreadsheet_dashboard.spreadsheet_dashboard_menu_root",
    )),
    ("Marketing and engagement", (
        "mass_mailing.mass_mailing_menu_root",
        "mass_mailing_sms.mass_mailing_sms_menu_root",
        "event.event_main_menu",
        "survey.menu_surveys",
        "im_livechat.menu_livechat_root",
        "marketing_card.card_menu",
        "utm.menu_link_tracker_root",
    )),
    ("Procurement and supply chain", (
        "purchase.menu_purchase_root",
        "purchase_request.parent_menu_purchase_request",
        "stock_request.menu_stock_request_root",
        "stock.menu_stock_root",
        "mrp.menu_mrp_root",
        "repair.menu_repair_order",
        "maintenance.menu_maintenance_title",
    )),
    ("Projects and services", (
        "project.menu_main_pm",
        "hr_timesheet.timesheet_menu_root",
        "helpdesk_mgmt.helpdesk_ticket_main_menu",
        "od19_document_sign.menu_od19_document_sign_root",
    )),
    ("Human resources", (
        "hr.menu_hr_root",
        "hr_attendance.menu_hr_attendance_root",
        "hr_recruitment.menu_hr_recruitment_root",
        "fleet.menu_root",
        "hr_holidays.menu_hr_holidays_root",
        "hr_expense.menu_hr_expense_root",
        "lunch.menu_lunch",
    )),
    ("Website and content", (
        "website.menu_website_configuration",
        "website_slides.website_slides_menu_root",
        "document_knowledge.menu_document_root",
        "od19_announcement.announcement_main_menu",
        "od19_iso_document_control.menu_iso_root",
    )),
    ("Internal tools", (
        "project_todo.menu_todo_todos",
        "data_recycle.menu_data_cleaning_root",
        "od19_user_guide_tours.menu_od19_user_guide_root",
    )),
)

# Sequence layout. The first app of the first cluster gets
# APP_MENU_SEQUENCE_START; each following app inside a cluster is
# APP_MENU_SEQUENCE_STEP further on. Every new cluster jumps forward by
# APP_MENU_CLUSTER_GAP, which leaves free numbers between two clusters so a new
# app can be inserted into a cluster without renumbering the whole list and so
# the boundary between clusters stays obvious in the raw data.
APP_MENU_SEQUENCE_START = 10
APP_MENU_SEQUENCE_STEP = 10
APP_MENU_CLUSTER_GAP = 100

# The "Apps" and "Settings" tiles must stay at the very end of the switcher.
# The curated block built from the clusters above extends past their original
# sequences (500/550), so they are pushed after the last curated app; otherwise
# they would land in the middle of the clusters.
APP_MENU_ADMINISTRATION_XMLIDS = (
    "base.menu_management",
    "base.menu_administration",
)

# Context key set while re-sequencing to keep the ``create``/``write`` overrides
# below from re-entering the same logic.
APP_MENU_REORDER_CONTEXT = "od19_app_menu_reorder"

# ---------------------------------------------------------------------------
# NavBar grouping
# ---------------------------------------------------------------------------

# When an app menu bar carries more sections than fit in a single row, Odoo
# pushes the trailing ones into the "+" (More) navigator. To keep every section
# reachable without opening that navigator, related sections are gathered under
# a single parent section: a plain ``ir.ui.menu`` without an action, which Odoo
# renders as a dropdown in the NavBar.
#
# Each entry is ``(section_xmlid, label_en, label_th, parent_xmlid, sequence,
# children)``: ``parent_xmlid`` is the app root menu and ``children`` are the
# sections moved inside the new one, in display order. Apps that are not
# installed are skipped, so the module needs no dependency on them.
NAVBAR_GROUPS = (
    (
        "menu_od19_accounting_dashboards",
        "Dashboards",
        "แดชบอร์ด",
        "account.menu_finance",
        1,
        (
            "od19_accounting_reporting.menu_od19_finance_control_dashboard",
            "account.menu_board_journal_1",
        ),
    ),
    (
        "menu_od19_accounting_treasury",
        "Treasury",
        "เงินสดและเงินทดรอง",
        "account.menu_finance",
        11,
        (
            "od19_accounting_cheque.menu_account_cheque",
            "od19_accounting_advance.menu_account_advance",
            "od19_accounting_petty_cash.menu_petty_cash_root",
        ),
    ),
    (
        "menu_od19_sales_contracts",
        "Contracts",
        "สัญญา",
        "sale.sale_menu_root",
        31,
        (
            "od19_sales_contract_core.menu_od19_sales_contract",
            "od19_sales_contract_core.menu_od19_contract_revenue_line",
            "od19_sales_retention.menu_od19_sales_retention",
        ),
    ),
    (
        "menu_od19_sales_after_sales",
        "After-Sales",
        "บริการหลังการขาย",
        "sale.sale_menu_root",
        36,
        (
            "od19_helpdesk_extension.menu_sales_services",
            "od19_after_sales_reporting.menu_od19_after_sales_reporting_root",
        ),
    ),
    (
        "menu_od19_project_reports",
        "Project Reports",
        "รายงานโครงการ",
        "project.menu_main_pm",
        95,
        (
            "od19_project_enhanced.menu_od19_project_risk_report",
            "od19_project_enhanced.menu_od19_project_pnl_report",
            "od19_project_enhanced.menu_od19_project_without_job_no",
            "od19_project_enhanced.menu_od19_project_without_analytic",
        ),
    ),
    (
        "menu_od19_settings_tools",
        "OD19 Tools",
        "เครื่องมือ OD19",
        "base.menu_administration",
        90,
        (
            "od19_notification_multi_channel.menu_notification_root",
            "od19_approval_center.menu_od19_approval_root",
            "od19_apps_filter.menu_od19_modules",
            "od19_misc_features.menu_od19_misc_features_root",
        ),
    ),
    (
        "menu_od19_inventory_dashboards",
        "Dashboards",
        "แดชบอร์ด",
        "stock.menu_stock_root",
        0,
        (
            "od19_inventory_reporting.menu_od19_logistics_dashboard",
            "stock.stock_picking_type_menu",
        ),
    ),
    (
        "menu_od19_knowledge_content",
        "Content",
        "เนื้อหา",
        "document_knowledge.menu_document_root",
        5,
        (
            "document_page.menu_browse_content",
            "document_page.menu_wiki",
            "od19_knowledge_enhanced.knowledge_article_menu",
            "document_knowledge.menu_document_section",
        ),
    ),
)

# Single sections that belong inside an *existing* section instead of a new
# grouping one. Each entry is ``(menu_xmlid, parent_xmlid, sequence)``; when the
# parent is the menu's current parent the entry only fixes its order, which is
# used to break the sequence ties some apps ship with.
NAVBAR_MOVES = (
    # Sales: fold the Product Returns list into the "Orders" section.
    ("od19_product_return.menu_od19_product_return", "sale.sale_order_menu", 35),
    # Repairs: Orders and Warranty Claims both ship at sequence 10.
    ("od19_service_warranty.menu_warranty_claim", "repair.menu_repair_order", 11),
)

# Sections whose label is renamed to remove a duplicate or an ambiguity. Each
# entry is ``(menu_xmlid, label_en, label_th)``; the Thai label is always kept
# in sync so the override survives a language switch.
NAVBAR_RENAMES = (
    # Project: this list duplicates the title of the main "Projects" section and
    # only shows up once "Use Stages on Project" gets members.
    ("project.menu_projects_group_stage", "Projects by Stage", "โครงการ (แยกตามขั้น)"),
    # Repairs: disambiguate the repair orders list from Warranty Claims.
    ("repair.repair_order_menu", "Repair Orders", "ใบสั่งซ่อม"),
)

# Module tag given to the grouping sections created at runtime, so they are
# removed automatically when the module is uninstalled.
NAVBAR_GROUP_MODULE = "od19_ui_defaults"

# Context key set while applying the grouping, so the ``create``/``write``
# overrides below cannot re-enter it.
NAVBAR_GROUP_CONTEXT = "od19_navbar_group"


def od19_navbar_managed_xmlids():
    """Return the xmlids of every menu the NavBar layout keeps re-applying."""
    xmlids = set()
    for _name, _en, _th, _parent, _sequence, children in NAVBAR_GROUPS:
        xmlids.update(children)
    xmlids.update(xmlid for xmlid, _parent, _sequence in NAVBAR_MOVES)
    xmlids.update(xmlid for xmlid, _en, _th in NAVBAR_RENAMES)
    return xmlids


def od19_app_menu_sequences():
    """Yield ``(xmlid, sequence)`` for every curated app, in display order."""
    for cluster_index, (_label, xmlids) in enumerate(APP_MENU_CLUSTERS):
        base = APP_MENU_SEQUENCE_START + cluster_index * APP_MENU_CLUSTER_GAP
        for index, xmlid in enumerate(xmlids):
            yield xmlid, base + index * APP_MENU_SEQUENCE_STEP


class IrUiMenu(models.Model):
    _inherit = "ir.ui.menu"

    @api.model_create_multi
    def create(self, vals_list):
        menus = super().create(vals_list)
        menus._od19_reorder_app_menus_if_root()
        return menus

    def write(self, vals):
        res = super().write(vals)
        if "sequence" in vals or "parent_id" in vals:
            self._od19_reorder_app_menus_if_root()
        if "parent_id" in vals or "name" in vals:
            self._od19_regroup_navbar_sections()
        return res

    def _od19_reorder_app_menus_if_root(self):
        """Re-apply the app ordering whenever a top-level menu is created/moved.

        Odoo rewrites the ``sequence`` of every menu owned by a module each time
        that module is installed or upgraded, which would shuffle the apps back
        into their default order on the next ``-u``. Re-applying the curated
        order on the fly keeps it in place without touching the core data files.
        """
        if self.env.context.get(APP_MENU_REORDER_CONTEXT):
            return
        if not any(not menu.parent_id for menu in self):
            return
        self.env["ir.ui.menu"].with_context(
            **{APP_MENU_REORDER_CONTEXT: True}
        )._od19_sequence_app_menus()

    def _od19_regroup_navbar_sections(self):
        """Re-apply the NavBar layout whenever a managed section is touched.

        Odoo rewrites the ``parent_id``/``name`` of the menus it owns every time
        their module is installed or upgraded, which would pull the sections back
        out of their group (or restore their original label) on the next ``-u``.
        Re-applying the layout on the fly keeps it in place without touching the
        core data files.
        """
        if self.env.context.get(NAVBAR_GROUP_CONTEXT):
            return
        managed_xmlids = od19_navbar_managed_xmlids()
        if not managed_xmlids:
            return
        xmlids = self.get_external_id()
        if any(xmlids.get(menu.id) in managed_xmlids for menu in self):
            self.env["ir.ui.menu"]._od19_apply_navbar_groups()

    @api.model
    def _od19_apply_navbar_groups(self):
        """Apply the curated NavBar layout to every managed application.

        The layout is made of three parts:

        * :data:`NAVBAR_GROUPS` -- gathers a group of sibling sections (direct
          children of an app root menu) inside one new section that has no action
          of its own: Odoo renders such a section as a dropdown in the NavBar,
          which keeps the bar short while every menu stays one click away.
        * :data:`NAVBAR_MOVES` -- re-parents (or merely re-orders) a single
          section inside an existing one.
        * :data:`NAVBAR_RENAMES` -- relabels a section to drop a duplicate or an
          ambiguous title, keeping the Thai translation in sync.

        The method is idempotent -- a grouping section is created once and then
        only updated. Entries whose application (or one of their sections) is
        not installed are skipped, so the module needs no dependency on them.
        """
        menu_model = self.env["ir.ui.menu"].with_context(
            **{NAVBAR_GROUP_CONTEXT: True, "lang": "en_US"}
        )
        # Thai labels are only written when the language is actually activated:
        # ``update_field_translations`` raises a UserError on a database where
        # ``th_TH`` is not installed (e.g. a fresh test database), which would
        # make the whole module fail to install.
        th_active = "th_TH" in self.env["res.lang"].search(
            [("active", "=", True)]
        ).mapped("code")
        for group_name, label_en, label_th, parent_xmlid, sequence, child_xmlids in NAVBAR_GROUPS:
            parent = self.env.ref(parent_xmlid, raise_if_not_found=False)
            children = [
                self.env.ref(xmlid, raise_if_not_found=False) for xmlid in child_xmlids
            ]
            if not parent or not all(children):
                continue
            group = self.env.ref(
                "%s.%s" % (NAVBAR_GROUP_MODULE, group_name), raise_if_not_found=False
            )
            vals = {"name": label_en, "parent_id": parent.id, "sequence": sequence}
            if group:
                menu_model.browse(group.id).write(vals)
            else:
                group = menu_model.create(vals)
                # Tag the section with an xmlid of this module so Odoo removes it
                # automatically on uninstall (its children are promoted back to
                # the app menu bar by ``ir.ui.menu.unlink``).
                self.env["ir.model.data"].create({
                    "module": NAVBAR_GROUP_MODULE,
                    "name": group_name,
                    "model": "ir.ui.menu",
                    "res_id": group.id,
                    "noupdate": True,
                })
            if th_active:
                group.update_field_translations("name", {"th_TH": label_th})
            for index, child in enumerate(children, start=1):
                menu_model.browse(child.id).write({
                    "parent_id": group.id,
                    "sequence": index,
                })
        for menu_xmlid, parent_xmlid, sequence in NAVBAR_MOVES:
            menu = self.env.ref(menu_xmlid, raise_if_not_found=False)
            parent = self.env.ref(parent_xmlid, raise_if_not_found=False)
            if not menu or not parent:
                continue
            if menu.parent_id.id != parent.id or menu.sequence != sequence:
                menu_model.browse(menu.id).write({
                    "parent_id": parent.id,
                    "sequence": sequence,
                })
        for menu_xmlid, label_en, label_th in NAVBAR_RENAMES:
            menu = self.env.ref(menu_xmlid, raise_if_not_found=False)
            if not menu:
                continue
            record = menu_model.browse(menu.id)
            record.write({"name": label_en})
            if th_active:
                record.update_field_translations("name", {"th_TH": label_th})

    @api.model
    def _od19_sequence_app_menus(self):
        """Order the top-level app menus by business-flow cluster.

        The app/sequence pairs come from :func:`od19_app_menu_sequences` (see
        ``APP_MENU_CLUSTERS``). The writes are done under the reorder context so
        the ``create``/``write`` overrides above do not re-enter this method
        while it is running, which keeps the method idempotent and free of
        redundant nested reorders.
        """
        menu_model = self.env["ir.ui.menu"].with_context(
            **{APP_MENU_REORDER_CONTEXT: True}
        )
        sequences = list(od19_app_menu_sequences())
        for xmlid, sequence in sequences:
            menu = menu_model.env.ref(xmlid, raise_if_not_found=False)
            if not menu:
                continue
            if menu.sequence != sequence:
                menu.sequence = sequence
        # Keep the Apps/Settings tiles after every curated app. The last
        # sequence is taken from the full list (not only the installed apps) so
        # the values stay stable whatever subset of modules is installed.
        last_sequence = sequences[-1][1]
        for offset, xmlid in enumerate(APP_MENU_ADMINISTRATION_XMLIDS, start=1):
            menu = menu_model.env.ref(xmlid, raise_if_not_found=False)
            if not menu:
                continue
            sequence = last_sequence + offset * APP_MENU_SEQUENCE_STEP
            if menu.sequence != sequence:
                menu.sequence = sequence

    @api.model
    def _od19_place_configuration_menus_last(self):
        """Move every Configuration menu to the end of its parent menu.

        Odoo reloads menu data on each module update and resets the ``sequence``
        of the menus it owns, so the rule is re-applied from
        ``data/ui_defaults.xml`` on every install/upgrade.
        """
        # Search in the source language so the lookup is independent from the
        # language the data is loaded with.
        menus = self.with_context(lang="en_US").search([
            ("name", "in", CONFIGURATION_MENU_LABELS),
            ("parent_id", "!=", False),
        ])
        for menu in menus:
            siblings = self.search([
                ("parent_id", "=", menu.parent_id.id),
                ("id", "!=", menu.id),
            ])
            if not siblings:
                continue
            last_sequence = max(siblings.mapped("sequence"))
            if menu.sequence <= last_sequence:
                menu.sequence = last_sequence + 1
