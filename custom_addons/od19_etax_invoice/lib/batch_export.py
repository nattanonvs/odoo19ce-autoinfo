# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

"""Batch export of e-Tax documents, used as fallback channel to the RD.

When the online channel is unavailable the documents can still be handed over
as a single archive: one signed XML and its printable PDF per document, plus
a ``manifest.txt`` index carrying the reference, the SHA-512 digest and the
archive path of every file — the audit trail of the batch.
"""

import base64
import csv
import io
import re
import zipfile

MANIFEST_NAME = "manifest.txt"

MANIFEST_HEADER = (
    "reference",
    "document_type",
    "company_vat",
    "customer_vat",
    "sha512",
    "xml_file",
    "pdf_file",
)


def _safe_name(value):
    """Return ``value`` reduced to characters that are safe in a ZIP entry."""
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value or "document")


def build_batch_zip(documents):
    """Return the RD batch archive (``bytes``) for ``documents``.

    :param documents: an ``od19.etax.document`` recordset, possibly empty.
    :raises ValueError: when no document carries a signed XML.
    """
    buffer = io.BytesIO()
    manifest = io.StringIO()
    writer = csv.writer(manifest)
    writer.writerow(MANIFEST_HEADER)

    written = 0
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for document in documents:
            if not document.signed_xml_file:
                continue
            stem = _safe_name(document.name)
            xml_path = "xml/%s.xml" % stem
            archive.writestr(xml_path, base64.b64decode(document.signed_xml_file))
            pdf_path = ""
            if document.pdf_file:
                pdf_path = "pdf/%s.pdf" % stem
                archive.writestr(pdf_path, base64.b64decode(document.pdf_file))
            writer.writerow((
                document.name,
                document.document_type,
                document.company_id.vat or "",
                document.partner_id.vat or "",
                document.digest or "",
                xml_path,
                pdf_path,
            ))
            written += 1

        if not written:
            raise ValueError("No signed e-Tax document to export.")

        archive.writestr(MANIFEST_NAME, manifest.getvalue())

    return buffer.getvalue()
