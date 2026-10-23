# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

"""QR code helpers for the printed e-Tax Invoice.

The QR image is rendered into the QWeb report so the recipient can scan the
document reference and the verification digest printed on the paper copy.
"""

import base64
import io

import qrcode
from qrcode.constants import ERROR_CORRECT_M


def generate_png(data, box_size=4, border=2):
    """Return a PNG rendering of ``data`` as ``bytes``."""
    if not data:
        return b""
    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(data)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def generate_data_uri(data, box_size=4, border=2):
    """Return a ``data:image/png;base64,...`` URI for inline HTML embedding."""
    png = generate_png(data, box_size=box_size, border=border)
    if not png:
        return ""
    return "data:image/png;base64,%s" % base64.b64encode(png).decode("ascii")
