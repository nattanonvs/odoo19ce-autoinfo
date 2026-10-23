# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

"""Embed the signed e-Tax Invoice XML inside the printable PDF.

ขมธอ.3-2560 requires the machine readable XML to travel with the human
readable PDF in a single file.  The XML is attached to the PDF catalogue under
``/Names /EmbeddedFiles`` so the recipient and the tax authority can extract it
with any PDF reader.
"""

import io

from PyPDF2 import PdfReader, PdfWriter

DEFAULT_FILENAME = "etax-invoice.xml"


def embed_xml(pdf_content, xml_content, filename=DEFAULT_FILENAME):
    """Return a new PDF (``bytes``) carrying ``xml_content`` as an attachment.

    :param pdf_content: the source PDF as ``bytes``.
    :param xml_content: the signed e-Tax XML as ``bytes`` or ``str``.
    """
    if not pdf_content:
        raise ValueError("A source PDF is required.")
    if not xml_content:
        raise ValueError("The e-Tax XML payload is required.")
    if isinstance(xml_content, str):
        xml_content = xml_content.encode("utf-8")

    reader = PdfReader(io.BytesIO(pdf_content))
    writer = PdfWriter()
    writer.clone_document_from_reader(reader)
    writer.add_attachment(filename, xml_content)

    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def extract_xml(pdf_content, filename=DEFAULT_FILENAME):
    """Return the embedded XML of ``pdf_content`` or ``None`` when absent."""
    if not pdf_content:
        return None
    reader = PdfReader(io.BytesIO(pdf_content))
    try:
        names = reader.trailer["/Root"]["/Names"]["/EmbeddedFiles"]["/Names"]
    except KeyError:
        return None
    for index in range(0, len(names), 2):
        if names[index] == filename:
            filespec = names[index + 1]
            return filespec["/EF"]["/F"].get_data()
    return None
