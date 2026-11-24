# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models


class IsoDocument(models.Model):
    _inherit = "od19.iso.document"

    print_request_ids = fields.One2many(
        "od19.iso.print.request", "document_id", string="ใบขอพิมพ์"
    )
    print_request_count = fields.Integer(
        string="จำนวนใบขอพิมพ์", compute="_compute_print_control_counts"
    )
    print_copy_ids = fields.One2many(
        "od19.iso.print.copy", "document_id", string="สำเนาควบคุม"
    )
    print_copy_count = fields.Integer(
        string="จำนวนสำเนา", compute="_compute_print_control_counts"
    )
    issued_copy_count = fields.Integer(
        string="สำเนาที่จ่ายแล้ว", compute="_compute_print_control_counts"
    )
    distribution_list_ids = fields.One2many(
        "od19.iso.distribution.list", "document_id", string="ทะเบียนแจกจ่าย"
    )
    distribution_list_count = fields.Integer(
        string="จำนวนทะเบียนแจกจ่าย", compute="_compute_print_control_counts"
    )

    @api.depends(
        "print_request_ids",
        "print_copy_ids",
        "print_copy_ids.state",
        "distribution_list_ids",
    )
    def _compute_print_control_counts(self):
        for doc in self:
            doc.print_request_count = len(doc.print_request_ids)
            doc.print_copy_count = len(doc.print_copy_ids)
            doc.issued_copy_count = len(
                doc.print_copy_ids.filtered(lambda c: c.state == "issued")
            )
            doc.distribution_list_count = len(doc.distribution_list_ids)

    # ------------------------------------------------------------------
    # Stat button actions
    # ------------------------------------------------------------------
    def action_view_print_requests(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "od19_iso_print_control.action_od19_iso_print_request"
        )
        action["domain"] = [("document_id", "=", self.id)]
        action["context"] = {"default_document_id": self.id}
        return action

    def action_view_print_copies(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "od19_iso_print_control.action_od19_iso_print_copy"
        )
        action["domain"] = [("document_id", "=", self.id)]
        action["context"] = {"default_document_id": self.id}
        return action

    def action_view_distribution_lists(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "od19_iso_print_control.action_od19_iso_distribution_list"
        )
        action["domain"] = [("document_id", "=", self.id)]
        action["context"] = {"default_document_id": self.id}
        return action

    # ------------------------------------------------------------------
    # G1 hook: detect revision change
    # ------------------------------------------------------------------
    def write(self, vals):
        previous = {}
        if "revision" in vals:
            previous = {doc.id: doc.revision for doc in self}
        result = super().write(vals)
        if "revision" in vals:
            for doc in self:
                if previous.get(doc.id) != doc.revision:
                    self.env["od19.iso.print.copy"]._on_document_revision_change(
                        doc, doc.revision
                    )
        return result
