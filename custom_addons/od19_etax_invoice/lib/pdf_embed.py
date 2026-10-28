# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

"""Embed the signed e-Tax Invoice XML inside a PDF/A-3 printable.

ขมธอ.3-2560 requires the machine readable XML to travel with the human
readable PDF in a single file.  ISO 19005-3 (PDF/A-3) is the archiving profile
that allows an arbitrary embedded file, so the printable is emitted as a
PDF/A-3 level B document:

* ``pdfaid:part`` / ``pdfaid:conformance`` and the matching
  ``pdfaExtension:schemas`` declaration in the XMP metadata,
* an sRGB ICC output intent, so the colour rendering is device independent,
* the signed XML attached under ``/Names /EmbeddedFiles`` with the
  ``/AFRelationship /Data`` flag expected of an e-invoice payload.

The source PDF comes from Odoo's own report engine, which embeds the fonts it
renders with — a precondition of the profile — so this module only adds the
archival metadata and the attachment.
"""

import io
import logging

import pikepdf
from lxml import etree

_logger = logging.getLogger(__name__)

DEFAULT_FILENAME = "etax-invoice.xml"

#: Identifier of the archiving profile implemented by :func:`embed_xml`.
PDFA_PART = "3"
PDFA_CONFORMANCE = "B"

_RDF_NS = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
_PDFA_EXTENSION_NS = "http://www.aiim.org/pdfa/ns/extension/"

#: Declaration of the ``pdfaid`` extension schema.  ISO 19005 requires every
#: non standard XMP property to be described by such a block, and ``pikepdf``
#: cannot serialise the nested RDF structure through its Python API, so the
#: fragment is injected into the metadata stream verbatim.
_PDFA_EXTENSION_XML = """
<rdf:Description rdf:about=""
    xmlns:rdf="%(rdf)s"
    xmlns:pdfaExtension="%(extension)s"
    xmlns:pdfaSchema="http://www.aiim.org/pdfa/ns/schema#"
    xmlns:pdfaProperty="http://www.aiim.org/pdfa/ns/property#">
  <pdfaExtension:schemas>
    <rdf:Bag>
      <rdf:li rdf:parseType="Resource">
        <pdfaSchema:schema>PDF/A ID Schema</pdfaSchema:schema>
        <pdfaSchema:namespaceURI>http://www.aiim.org/pdfa/ns/id/</pdfaSchema:namespaceURI>
        <pdfaSchema:prefix>pdfaid</pdfaSchema:prefix>
        <pdfaSchema:property>
          <rdf:Seq>
            <rdf:li rdf:parseType="Resource">
              <pdfaProperty:name>part</pdfaProperty:name>
              <pdfaProperty:valueType>Integer</pdfaProperty:valueType>
              <pdfaProperty:category>internal</pdfaProperty:category>
              <pdfaProperty:description>Part of ISO 19005</pdfaProperty:description>
            </rdf:li>
            <rdf:li rdf:parseType="Resource">
              <pdfaProperty:name>conformance</pdfaProperty:name>
              <pdfaProperty:valueType>Text</pdfaProperty:valueType>
              <pdfaProperty:category>internal</pdfaProperty:category>
              <pdfaProperty:description>Conformance level</pdfaProperty:description>
            </rdf:li>
          </rdf:Seq>
        </pdfaSchema:property>
      </rdf:li>
    </rdf:Bag>
  </pdfaExtension:schemas>
</rdf:Description>
""" % {"rdf": _RDF_NS, "extension": _PDFA_EXTENSION_NS}

_srgb_profile = None


def _srgb_icc_profile():
    """Return the bytes of the sRGB IEC61966-2.1 ICC profile.

    lcms, through Pillow, ships the profile and serialises it on every call,
    so the result is cached for the lifetime of the worker.
    """
    global _srgb_profile
    if _srgb_profile is None:
        from PIL import ImageCms

        profile = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB"))
        _srgb_profile = profile.tobytes()
    return _srgb_profile


def _set_output_intent(pdf):
    """Add the sRGB ICC output intent required by ISO 19005."""
    if "/OutputIntents" in pdf.Root:
        return
    pdf.Root.OutputIntents = pdf.make_indirect(pikepdf.Array([
        pikepdf.Dictionary(
            Type=pikepdf.Name("/OutputIntent"),
            S=pikepdf.Name("/GTS_PDFA1"),
            OutputConditionIdentifier=pikepdf.String("sRGB IEC61966-2.1"),
            Info=pikepdf.String("sRGB IEC61966-2.1"),
            DestOutputProfile=pikepdf.Stream(pdf, _srgb_icc_profile()),
        ),
    ]))


def _set_metadata(pdf, title=None, description=None, creator=None):
    """Write the PDF/A identification and the document information."""
    with pdf.open_metadata(set_pikepdf_as_editor=False) as metadata:
        metadata["pdfaid:part"] = PDFA_PART
        metadata["pdfaid:conformance"] = PDFA_CONFORMANCE
        if title:
            metadata["dc:title"] = title
        if description:
            metadata["dc:description"] = description
        if creator:
            metadata["xmp:CreatorTool"] = creator
    _inject_extension_schema(pdf)


def _inject_extension_schema(pdf):
    """Append the ``pdfaExtension:schemas`` block to the XMP metadata."""
    stream = pdf.Root.get("/Metadata")
    if stream is None:
        return
    root = etree.fromstring(stream.read_bytes())
    rdf = root.find("{%s}RDF" % _RDF_NS)
    if rdf is None:
        return
    if rdf.find(".//{%s}schemas" % _PDFA_EXTENSION_NS) is not None:
        return
    rdf.append(etree.fromstring(_PDFA_EXTENSION_XML))
    stream.write(etree.tostring(root))


def embed_xml(
    pdf_content,
    xml_content,
    filename=DEFAULT_FILENAME,
    title=None,
    description=None,
    creator=None,
):
    """Return a PDF/A-3 (``bytes``) carrying ``xml_content`` as an attachment.

    :param pdf_content: the source PDF as ``bytes``.
    :param xml_content: the signed e-Tax XML as ``bytes`` or ``str``.
    :param filename: name of the attached XML inside the PDF.
    :param title: value of the PDF ``dc:title`` metadata.
    :param description: value of the PDF ``dc:description`` metadata.
    :param creator: value of the PDF ``xmp:CreatorTool`` metadata.
    """
    if not pdf_content:
        raise ValueError("A source PDF is required.")
    if not xml_content:
        raise ValueError("The e-Tax XML payload is required.")
    if isinstance(xml_content, str):
        xml_content = xml_content.encode("utf-8")

    with pikepdf.open(io.BytesIO(pdf_content)) as pdf:
        _set_output_intent(pdf)
        _set_metadata(pdf, title=title, description=description, creator=creator)
        pdf.attachments[filename] = pikepdf.AttachedFileSpec(
            pdf,
            xml_content,
            mime_type="application/xml",
            filename=filename,
            description="e-Tax Invoice XML",
            relationship=pikepdf.Name("/Data"),
        )
        buffer = io.BytesIO()
        pdf.save(buffer, min_version="1.7")
    return buffer.getvalue()


def extract_xml(pdf_content, filename=DEFAULT_FILENAME):
    """Return the embedded XML of ``pdf_content`` or ``None`` when absent."""
    if not pdf_content:
        return None
    with pikepdf.open(io.BytesIO(pdf_content)) as pdf:
        try:
            attachment = pdf.attachments[filename]
        except KeyError:
            return None
        return attachment.get_file().read_bytes()
