# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import _, api, models


class Od19BarcodeScanWizard(models.TransientModel):
    """Server-side brain of the mobile barcode scanner.

    The OWL client action only captures the raw code; every lookup and write
    happens here so the rules stay in one place (and are easy to unit-test):

    * ``resolve_barcode`` translates a code into the record it points to
      (product / lot / location / package) and, when a transfer context is
      given, the matching move line of that transfer.
    * ``apply_scan_to_picking`` writes the scanned quantity (and lot) onto the
      matching move line of a transfer.
    """

    _name = "od19.barcode.scan.wizard"
    _description = "Barcode Scan Service"

    # ------------------------------------------------------------------
    # Public API (called from the OWL scanner through orm.call)
    # ------------------------------------------------------------------
    @api.model
    def resolve_barcode(self, barcode, picking_id=False, log=True):
        """Return a plain dict describing what ``barcode`` points to.

        :param str barcode: the raw scanned code
        :param int|bool picking_id: optional transfer to resolve move lines for
        :param bool log: create an ``od19.barcode.scan.log`` row
        :rtype: dict
        """
        barcode = (barcode or "").strip()
        result = self._prepare_result(barcode)
        if barcode:
            self._match_record(result, barcode)
        if picking_id:
            self._attach_picking(result, picking_id)
        if log and barcode:
            self._create_log(result, picking_id)
        return result

    @api.model
    def apply_scan_to_picking(self, picking_id, barcode, quantity=None):
        """Write a scanned product/lot onto the matching move line.

        :param int picking_id: the transfer to update
        :param str barcode: scanned code (product or lot)
        :param float|None quantity: quantity to set, defaults to the demand
        :rtype: dict
        """
        picking = self.env["stock.picking"].browse(picking_id)
        if not picking.exists():
            return {"success": False, "message": _("ไม่พบใบรับ/ส่งที่ระบุ")}

        resolved = self.resolve_barcode(barcode, picking_id, log=False)
        if resolved["type"] not in ("product", "lot"):
            return {
                "success": False,
                "message": _("บาร์โค้ดนี้ไม่ใช่สินค้า/ล็อต จึงใช้กับใบรับ/ส่งไม่ได้"),
            }
        if not resolved["product_id"]:
            return {"success": False, "message": _("ไม่พบสินค้าสำหรับบาร์โค้ดนี้")}

        line = self.env["stock.move.line"].search(
            [
                ("picking_id", "=", picking.id),
                ("product_id", "=", resolved["product_id"]),
            ],
            limit=1,
        )
        if not line:
            return {
                "success": False,
                "message": _("ไม่พบรายการสินค้านี้ในใบ %s") % picking.name,
            }

        qty = quantity
        if qty is None:
            qty = resolved["picking"].get("expected_qty") or line.quantity or 1.0
        vals = {"picked": True, "quantity": float(qty)}
        if resolved["type"] == "lot" and resolved["lot_id"]:
            vals["lot_id"] = resolved["lot_id"]
        line.write(vals)
        self._create_log(resolved, picking.id, quantity=vals["quantity"])
        return {
            "success": True,
            "message": _("บันทึก %(qty)s %(uom)s · %(product)s")
            % {
                "qty": vals["quantity"],
                "uom": line.product_uom_id.name or "",
                "product": line.product_id.display_name,
            },
            "move_line_id": line.id,
            "quantity": vals["quantity"],
            "picking_id": picking.id,
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _prepare_result(self, barcode):
        return {
            "barcode": barcode,
            "matched": False,
            "type": "unknown",
            "res_model": False,
            "res_id": False,
            "display_name": "",
            "extra": "",
            "product_id": False,
            "product_name": "",
            "uom": "",
            "qty_available": 0.0,
            "lot_id": False,
            "location_id": False,
            "package_id": False,
            "picking": False,
        }

    def _match_record(self, result, barcode):
        """Resolve in priority order: product, lot, location, package."""
        product = self.env["product.product"].search(
            [("barcode", "=", barcode)], limit=1
        )
        if product:
            result.update(
                {
                    "matched": True,
                    "type": "product",
                    "res_model": "product.product",
                    "res_id": product.id,
                    "display_name": product.display_name,
                    "product_id": product.id,
                    "product_name": product.display_name,
                    "uom": product.uom_id.name or "",
                    "qty_available": product.qty_available,
                    "extra": _("คงเหลือ %(qty)s %(uom)s")
                    % {"qty": product.qty_available, "uom": product.uom_id.name or ""},
                }
            )
            return

        lot = self.env["stock.lot"].search(
            ["|", ("name", "=", barcode), ("ref", "=", barcode)], limit=1
        )
        if lot:
            result.update(
                {
                    "matched": True,
                    "type": "lot",
                    "res_model": "stock.lot",
                    "res_id": lot.id,
                    "display_name": lot.name,
                    "product_id": lot.product_id.id,
                    "product_name": lot.product_id.display_name,
                    "uom": lot.product_id.uom_id.name or "",
                    "lot_id": lot.id,
                    "extra": _("ล็อตของ %s") % lot.product_id.display_name,
                }
            )
            return

        location = self.env["stock.location"].search(
            [("barcode", "=", barcode)], limit=1
        )
        if location:
            result.update(
                {
                    "matched": True,
                    "type": "location",
                    "res_model": "stock.location",
                    "res_id": location.id,
                    "display_name": location.complete_name,
                    "location_id": location.id,
                    "extra": _("ตำแหน่งจัดเก็บ"),
                }
            )
            return

        package = self.env["stock.package"].search([("name", "=", barcode)], limit=1)
        if package:
            result.update(
                {
                    "matched": True,
                    "type": "package",
                    "res_model": "stock.package",
                    "res_id": package.id,
                    "display_name": package.name,
                    "package_id": package.id,
                    "extra": _("หีบห่อ"),
                }
            )

    def _attach_picking(self, result, picking_id):
        picking = self.env["stock.picking"].browse(picking_id)
        if not picking.exists():
            return
        info = {
            "picking_id": picking.id,
            "picking_name": picking.name,
            "picking_state": picking.state,
            "move_line_id": False,
            "expected_qty": 0.0,
            "done_qty": 0.0,
            "uom": "",
        }
        if result["product_id"]:
            line = self.env["stock.move.line"].search(
                [
                    ("picking_id", "=", picking.id),
                    ("product_id", "=", result["product_id"]),
                ],
                limit=1,
            )
            if line:
                info.update(
                    {
                        "move_line_id": line.id,
                        "expected_qty": line.quantity,
                        "done_qty": line.quantity,
                        "uom": line.product_uom_id.name or "",
                    }
                )
        result["picking"] = info

    def _create_log(self, result, picking_id=False, quantity=0.0):
        self.env["od19.barcode.scan.log"].create(
            {
                "barcode": result["barcode"],
                "matched": result["matched"],
                "scan_type": result["type"],
                "res_model": result["res_model"],
                "res_id": result["res_id"] or 0,
                "res_name": result["display_name"],
                "product_id": result["product_id"] or False,
                "lot_id": result["lot_id"] or False,
                "location_id": result["location_id"] or False,
                "package_id": result["package_id"] or False,
                "picking_id": picking_id or False,
                "quantity": quantity,
            }
        )
