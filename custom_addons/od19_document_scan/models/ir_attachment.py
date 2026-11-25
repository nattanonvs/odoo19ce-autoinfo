# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

"""Server-side image compression (layer 2).

The camera/scan widgets already shrink photos in the browser ("layer 1").
This server-side pass is the safety net: any image attachment that still
reaches the server too heavy -- desktop uploads, other modules, or browsers
where the client-side step was skipped -- is resized/re-encoded before it is
stored, so the filestore does not fill up with oversized photos.

Only raster photo formats (JPEG/PNG) are touched; everything else (SVG, WEBP,
GIF, PDF, ...) is left exactly as received.
"""

import base64
import logging

from odoo import models
from odoo.exceptions import UserError
from odoo.tools import image, str2bool

_logger = logging.getLogger(__name__)

COMPRESSIBLE_SUBTYPES = {"jpeg", "jpg", "png"}

# Images already this small are considered "compressed enough" by the client and
# are not re-encoded again (avoids pointless CPU work on icons/thumbnails).
MIN_BYTES_SKIP = 100 * 1024


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    def _postprocess_contents(self, values):
        values = super()._postprocess_contents(values)

        get_param = self.env["ir.config_parameter"].sudo().get_param
        if not str2bool(get_param("od19_scan.server_compress_enabled", "True"), True):
            return values

        mimetype = values.get("mimetype") or ""
        type_, _sep, subtype = mimetype.partition("/")
        if type_ != "image" or subtype not in COMPRESSIBLE_SUBTYPES:
            return values

        raw = values.get("raw")
        if not raw and values.get("datas"):
            try:
                raw = base64.b64decode(values["datas"])
            except (ValueError, TypeError):
                return values
        if not raw or len(raw) <= MIN_BYTES_SKIP:
            return values

        max_px = self._od19_scan_int_param(get_param, "od19_scan.server_max_px", 1600)
        if max_px <= 0:
            return values
        quality = self._od19_scan_int_param(get_param, "od19_scan.server_quality", 78)

        output_format = "PNG" if subtype == "png" else "JPEG"
        try:
            img = image.ImageProcess(raw, verify_resolution=False)
            if not img.image:
                return values
            width, height = img.image.size
            if width > max_px or height > max_px:
                img = img.resize(max_px, max_px)
            data = img.image_quality(
                quality=quality if output_format == "JPEG" else 0,
                output_format=output_format,
            )
        except UserError:
            return values

        # Never store something heavier than what we received.
        if not data or len(data) >= len(raw):
            return values

        if values.get("raw"):
            values["raw"] = data
        else:
            values["datas"] = base64.b64encode(data)
        return values

    @staticmethod
    def _od19_scan_int_param(get_param, key, default):
        try:
            return int(get_param(key, str(default)) or default)
        except (TypeError, ValueError):
            return default
