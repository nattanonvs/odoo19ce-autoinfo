# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

"""Tests for the ขมธอ.3-2560 e-Tax Invoice & e-Receipt pipeline.

Covered: document type codes, XSD validation of the unsigned XML, XAdES
signing, the PDF/XML attachment round trip and the reporting helpers used by
the printed report.
"""

import base64
import datetime
import io

from lxml import etree

from odoo import Command
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon

from ..lib import namespaces, pdf_embed, validator

DS_NS = "http://www.w3.org/2000/09/xmldsig#"


def _generate_self_signed_certificate():
    """Return ``(key_pem, cert_pem)`` bytes for a throwaway RSA certificate."""
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "TH"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "OD19 Test"),
        x509.NameAttribute(NameOID.COMMON_NAME, "OD19 e-Tax Test"),
    ])
    now = datetime.datetime.now(datetime.timezone.utc)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=365))
        .sign(key, hashes.SHA256())
    )
    key_pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    return key_pem, certificate.public_bytes(serialization.Encoding.PEM)


@tagged("post_install", "-at_install")
class TestOd19EtaxDocument(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.company_data["company"]
        key_pem, cert_pem = _generate_self_signed_certificate()
        cls.certificate = cls.env["od19.etax.certificate"].create({
            "name": "OD19 Test Certificate",
            "company_id": cls.company.id,
            "private_key": key_pem.decode(),
            "certificate": cert_pem.decode(),
        })
        cls.certificate.action_verify()
        cls.company.od19_etax_certificate_id = cls.certificate.id
        cls.company.od19_etax_enabled = True
        # The seller must bear a Thai tax registration: the minimal
        # CancellationNote profile requires ``SpecifiedTaxRegistration`` on the
        # seller and the invoicer parties.
        cls.company.vat = "0105558000014"

    @classmethod
    def setup_independent_user(cls):
        """Create the accounting test user with its full default group set.

        ``AccountTestInvoicingCommon`` relies on ``stock``/``purchase``/
        ``account`` manager groups to build the invoicing fixtures. Those
        groups are stripped again as soon as the user is created because
        ``base_user_role`` replaces a new user's groups with the ones implied
        by its role lines, and ``od19_role_catalog`` grants a default role to
        every new user. Dropping the role lines keeps the accounting groups so
        the shared fixtures (contact, company, journals) can be created.
        """
        user = super().setup_independent_user()
        user.sudo().role_line_ids.unlink()
        user.sudo().write({
            "group_ids": [Command.set(cls.get_default_groups().ids)],
        })
        return user

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _create_document(self, move_type="out_invoice", document_type="tax_invoice",
                         post=True):
        invoice = self._create_invoice(move_type=move_type, post=post)
        return self.env["od19.etax.document"].create({
            "move_id": invoice.id,
            "document_type": document_type,
        })

    def _create_note_move(self, dncn):
        """Return a posted DN/CN journal entry classified through ``dncn``.

        A debit note is posted as an ``out_invoice`` and a credit note as an
        ``out_refund``; both require a reason once posted.
        """
        move_type = "out_invoice" if dncn == "dn" else "out_refund"
        move = self._create_invoice(move_type=move_type, post=False)
        move.write({
            "dncn": dncn,
            "reason_id": self.env["account.move.dncn.reason"].create(
                {"name": "Test DN/CN reason"}
            ).id,
        })
        move.action_post()
        return move

    def _parse(self, binary_field):
        return etree.fromstring(base64.b64decode(binary_field))

    # ------------------------------------------------------------------
    # Document types
    # ------------------------------------------------------------------
    def test_document_type_codes(self):
        document = self._create_document()
        self.assertEqual(document.type_code, "388")
        self.assertEqual(document.purpose_code, "TIVC01")

    def test_credit_note_document_type(self):
        document = self._create_document(
            move_type="out_refund", document_type="debit_credit_note"
        )
        self.assertEqual(document.type_code, "81")
        self.assertEqual(document.purpose_code, "CDNG01")
        document.action_generate_xml()
        tree = self._parse(document.xml_file)
        self.assertEqual(validator.validate(tree, "debit_credit_note"), [])

    def test_debit_note_type_code(self):
        """A debit note (ใบเพิ่มหนี้) reports UN/ECE 1001 code 80."""
        move = self._create_note_move("dn")
        self.assertEqual(move._od19_etax_default_type(), "debit_credit_note")
        document = self.env["od19.etax.document"].create({
            "move_id": move.id,
            "document_type": "debit_credit_note",
        })
        self.assertEqual(document.type_code, "80")
        self.assertEqual(document.purpose_code, "CDNG01")
        document.action_generate_xml()
        tree = self._parse(document.xml_file)
        self.assertEqual(validator.validate(tree, "debit_credit_note"), [])

    def test_credit_note_type_code_from_dncn(self):
        """A credit note (ใบลดหนี้) reports UN/ECE 1001 code 81."""
        move = self._create_note_move("cn")
        self.assertEqual(move._od19_etax_default_type(), "debit_credit_note")
        document = self.env["od19.etax.document"].create({
            "move_id": move.id,
            "document_type": "debit_credit_note",
        })
        self.assertEqual(document.type_code, "81")

    def test_all_document_families_are_schema_valid(self):
        """Every offered family must build XSD-valid XML."""
        for document_type in dict(namespaces.DOCUMENT_TYPE_SELECTION):
            invoice = self._create_invoice(move_type="out_invoice")
            document = self.env["od19.etax.document"].create({
                "move_id": invoice.id,
                "document_type": document_type,
            })
            document.action_generate_xml()
            tree = self._parse(document.xml_file)
            self.assertEqual(
                validator.validate(tree, document_type),
                [],
                "XSD validation failed for %s" % document_type,
            )

    def test_type_code_list_attributes_follow_the_family_profile(self):
        """The Thai families publish the Thai code list; the Invoice does not.

        ETDA only ships the Invoice (380) family as the generic 2015 profile:
        ``InvoiceDocumentCodeType`` fixes ``@listID`` to ``1001_Invoice`` and
        ``@listAgencyID`` to ``6``, and ``ExchangedDocument`` declares neither
        ``PurposeCode`` nor ``CreationDateTime``.
        """
        tax_invoice = self._create_document()
        tax_invoice.action_generate_xml()
        rsm = namespaces.rsm_namespace("tax_invoice")
        ram = namespaces.ram_namespace("tax_invoice")
        node = self._parse(tax_invoice.xml_file).find("{%s}ExchangedDocument" % rsm)
        type_code = node.find("{%s}TypeCode" % ram)
        self.assertEqual(type_code.get("listID"), "1001_ThaiDocumentNameCodeInvoice")
        self.assertEqual(type_code.get("listAgencyID"), "RD/ETDA")
        self.assertIsNotNone(node.find("{%s}PurposeCode" % ram))

        document = self._create_document(document_type="invoice")
        document.action_generate_xml()
        tree = self._parse(document.xml_file)
        self.assertEqual(validator.validate(tree, "invoice"), [])
        rsm = namespaces.rsm_namespace("invoice")
        ram = namespaces.ram_namespace("invoice")
        node = tree.find("{%s}ExchangedDocument" % rsm)
        type_code = node.find("{%s}TypeCode" % ram)
        self.assertEqual(type_code.text, "380")
        self.assertEqual(type_code.get("listID"), "1001_Invoice")
        self.assertEqual(type_code.get("listAgencyID"), "6")
        self.assertIsNone(node.find("{%s}PurposeCode" % ram))
        self.assertIsNone(node.find("{%s}CreationDateTime" % ram))

    def test_only_customer_documents_allowed(self):
        bill = self.env["account.move"].create({
            "move_type": "in_invoice",
            "partner_id": self.partner_a.id,
        })
        with self.assertRaises(ValidationError):
            self.env["od19.etax.document"].create({
                "move_id": bill.id,
                "document_type": "tax_invoice",
            })

    # ------------------------------------------------------------------
    # Company switch
    # ------------------------------------------------------------------
    def test_company_switch_gates_the_feature(self):
        """Nothing can be issued for a company that never opted in."""
        document = self._create_document()
        self.company.od19_etax_enabled = False
        with self.assertRaises(UserError):
            document.action_generate_xml()
        with self.assertRaises(UserError):
            document.action_print()
        with self.assertRaises(UserError):
            self.env["od19.etax.document"].create({
                "move_id": document.move_id.id,
                "document_type": "tax_invoice",
            })

    # ------------------------------------------------------------------
    # XML generation
    # ------------------------------------------------------------------
    def test_unsigned_xml_is_schema_valid(self):
        document = self._create_document()
        document.action_generate_xml()
        self.assertEqual(document.state, "generated")
        tree = self._parse(document.xml_file)
        self.assertEqual(validator.validate(tree, document.document_type), [])

    # ------------------------------------------------------------------
    # Digital signature
    # ------------------------------------------------------------------
    def test_signing_produces_xades_signature(self):
        document = self._create_document()
        document.action_sign()
        self.assertEqual(document.state, "signed")
        tree = self._parse(document.signed_xml_file)
        signature = tree.find("{%s}Signature" % DS_NS)
        self.assertIsNotNone(signature)
        method = signature.find(
            "{%s}SignedInfo/{%s}SignatureMethod" % (DS_NS, DS_NS)
        )
        self.assertIn("rsa-sha512", method.get("Algorithm"))
        self.assertTrue(document.digest)
        self.assertEqual(document.signer_subject, self.certificate.subject)

    def test_sign_requires_posted_move(self):
        document = self._create_document(post=False)
        with self.assertRaises(UserError):
            document.action_sign()

    def test_signed_document_cannot_be_cancelled(self):
        document = self._create_document()
        document.action_sign()
        with self.assertRaises(UserError):
            document.action_cancel()

    def test_reset_to_draft_clears_generated_xml(self):
        document = self._create_document()
        document.action_generate_xml()
        document.action_reset_to_draft()
        self.assertEqual(document.state, "draft")
        self.assertFalse(document.xml_file)

    # ------------------------------------------------------------------
    # Reporting helpers and PDF
    # ------------------------------------------------------------------
    def test_header_allowance_reflects_line_discount(self):
        invoice = self._create_invoice()
        invoice.invoice_line_ids[0].discount = 10.0
        invoice.action_post()
        document = self.env["od19.etax.document"].create({
            "move_id": invoice.id,
            "document_type": "tax_invoice",
        })
        self.assertAlmostEqual(document.get_header_allowance(), 100.0, places=2)

    def test_tax_summary_and_qr(self):
        document = self._create_document()
        summary = document.get_tax_summary()
        self.assertTrue(summary)
        for values in summary.values():
            self.assertIn("base", values)
            self.assertIn("amount", values)
        self.assertTrue(document.get_qr_data_uri().startswith("data:image/png;base64,"))

    def _source_pdf(self):
        from reportlab.pdfgen import canvas

        buffer = io.BytesIO()
        page = canvas.Canvas(buffer)
        page.drawString(72, 720, "e-Tax invoice")
        page.showPage()
        page.save()
        return buffer.getvalue()

    @staticmethod
    def _truetype_program(widths):
        """Return a minimal TrueType program with the given glyph advances."""
        from fontTools.fontBuilder import FontBuilder
        from fontTools.pens.ttGlyphPen import TTGlyphPen

        glyph_order = [".notdef"] + [
            "glyph%05d" % index for index in range(1, len(widths) + 1)
        ]
        builder = FontBuilder(1000, isTTF=True)
        builder.setupGlyphOrder(glyph_order)
        builder.setupCharacterMap({})
        pen = TTGlyphPen(None)
        builder.setupGlyf(
            {name: pen.glyph() for name in glyph_order}, calcGlyphBounds=False
        )
        builder.setupHorizontalMetrics(dict(zip(
            glyph_order, [(width, 0) for width in [0] + list(widths)]
        )))
        builder.setupHorizontalHeader(ascent=800, descent=-200)
        builder.setupNameTable({"familyName": "Od19Test", "styleName": "Regular"})
        builder.setupOS2()
        builder.setupPost()
        buffer = io.BytesIO()
        builder.save(buffer)
        return buffer.getvalue()

    def _pdf_with_embedded_cid_font(self, declared_widths):
        """Return a PDF whose embedded CIDFont declares a wrong ``/W``."""
        import pikepdf

        pdf = pikepdf.new()
        page = pdf.add_blank_page(page_size=(200, 200))
        stream = pikepdf.Stream(pdf, self._truetype_program([600, 1200]))
        descriptor = pdf.make_indirect(pikepdf.Dictionary(
            Type=pikepdf.Name("/FontDescriptor"),
            FontName=pikepdf.Name("/Od19Test"),
            Flags=4,
            FontBBox=pikepdf.Array([0, 0, 1000, 1000]),
            ItalicAngle=0,
            Ascent=800,
            Descent=-200,
            CapHeight=700,
            StemV=80,
            FontFile2=stream,
        ))
        descendant = pdf.make_indirect(pikepdf.Dictionary(
            Type=pikepdf.Name("/Font"),
            Subtype=pikepdf.Name("/CIDFontType2"),
            BaseFont=pikepdf.Name("/Od19Test"),
            FontDescriptor=descriptor,
            W=pikepdf.Array([1, pikepdf.Array(declared_widths)]),
            DW=1000,
        ))
        font = pdf.make_indirect(pikepdf.Dictionary(
            Type=pikepdf.Name("/Font"),
            Subtype=pikepdf.Name("/Type0"),
            BaseFont=pikepdf.Name("/Od19Test"),
            Encoding=pikepdf.Name("/Identity-H"),
            DescendantFonts=pikepdf.Array([descendant]),
        ))
        page.obj["/Resources"] = pikepdf.Dictionary(
            Font=pikepdf.Dictionary(F1=font)
        )
        buffer = io.BytesIO()
        pdf.save(buffer)
        pdf.close()
        return buffer.getvalue()

    def test_pdf_embed_round_trip(self):
        xml = b"<?xml version='1.0' encoding='UTF-8'?><root/>"
        embedded = pdf_embed.embed_xml(self._source_pdf(), xml, "etax.xml")
        self.assertEqual(pdf_embed.extract_xml(embedded, "etax.xml"), xml)

    def test_glyph_widths_match_the_font_program(self):
        """ISO 19005-3 6.2.11.5: ``/W`` must match the embedded font program.

        ``wkhtmltopdf`` rounds the glyph advances differently, which PDF/A
        validators reject, so :func:`embed_xml` recomputes the array.
        """
        import pikepdf

        source = self._pdf_with_embedded_cid_font([111, 222])
        embedded = pdf_embed.embed_xml(source, b"<root/>", "etax.xml")
        with pikepdf.open(io.BytesIO(embedded)) as pdf:
            descendant = pdf.pages[0].Resources.Font.F1.DescendantFonts[0]
            self.assertEqual(list(descendant.W[1]), [600, 1200])

    def test_pdf_is_pdfa3_and_carries_the_xml(self):
        import pikepdf

        xml = b"<?xml version='1.0' encoding='UTF-8'?><root/>"
        embedded = pdf_embed.embed_xml(
            self._source_pdf(), xml, "etax.xml", title="INV/2026/0001"
        )
        with pikepdf.open(io.BytesIO(embedded)) as pdf:
            with pdf.open_metadata() as metadata:
                self.assertEqual(metadata["pdfaid:part"], "3")
                self.assertEqual(metadata["pdfaid:conformance"], "B")
                self.assertEqual(metadata["dc:title"], "INV/2026/0001")
            intents = pdf.Root.OutputIntents
            self.assertEqual(len(intents), 1)
            self.assertEqual(str(intents[0].S), "/GTS_PDFA1")
            self.assertTrue(
                intents[0].DestOutputProfile.read_bytes().startswith(b"\x00")
            )
            attachment = pdf.attachments["etax.xml"]
            self.assertEqual(attachment.obj["/AFRelationship"], "/Data")
            self.assertEqual(
                attachment.get_file().read_bytes(), xml
            )
        self.assertEqual(pdf_embed.extract_xml(embedded, "etax.xml"), xml)

    def test_report_template_renders(self):
        document = self._create_document()
        document.action_sign()
        report = document._get_report()
        html, _report_type = report._render_qweb_html(report, document.ids)
        self.assertIn(b"e-Tax Invoice", html)
        self.assertIn(b"SHA-512", html)
