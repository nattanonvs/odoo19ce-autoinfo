# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

"""Build ETDA Recommendation 3-2560 (ขมธอ.3-2560) e-Tax Invoice XML.

The generated document is a UN/CEFACT CrossIndustryInvoice 9.1 subset:

    rsm:ExchangedDocumentContext
    rsm:ExchangedDocument
    rsm:SupplyChainTradeTransaction
        ram:ApplicableHeaderTradeAgreement
        ram:ApplicableHeaderTradeDelivery
        ram:ApplicableHeaderTradeSettlement
        ram:IncludedSupplyChainTradeLineItem (1..n)
    ds:Signature (added later by :mod:`signer`)

Element order follows the XSD ``xsd:sequence`` declarations and therefore must
not be reshuffled.
"""

from collections import OrderedDict

from lxml import etree
from odoo import fields

from . import formats, namespaces

_XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"


class BuildError(Exception):
    """Raised when the source document cannot be represented in the profile."""


def _q(ns, local):
    return "{%s}%s" % (ns, local)


def _el(parent, ns, local, text=None, attrs=None):
    """Append a child element, skipping empty attributes and values.

    Passing ``text=None`` creates a container element while passing an empty
    string (the normal outcome of :func:`_text` for a missing source value)
    skips the element entirely, so optional elements are never emitted empty.
    """
    if text == "":
        return None
    node = etree.SubElement(parent, _q(ns, local))
    if text is not None:
        node.text = str(text)
    for key, value in (attrs or {}).items():
        if value is not None and value != "":
            node.set(key, str(value))
    return node


def _text(value, limit=None):
    """Normalise free text and optionally clamp it to the XSD max length.

    Odoo character fields return ``False`` (not ``""``) when empty and a bare
    ``str(False)`` would leak the literal ``"False"`` into the document, so
    every false-y value is normalised to an empty string here.
    """
    if not value:
        return ""
    text = str(value).strip()
    if limit and len(text) > limit:
        return text[:limit]
    return text


def _digits(value):
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def tax_identity(partner, scheme_national=None, scheme_tax=None, agency=None):
    """Return ``(identifier, scheme_id)`` for a Thai tax registration.

    A juristic person is reported with the 13 digit Tax ID plus the 5 digit
    branch code (18 digits, ``TXID``) while a natural person is reported with
    the 13 digit citizen ID (``NIDN``), as required by the RD specification.
    """
    scheme_national = scheme_national or namespaces.SCHEME_NATIONAL_ID
    scheme_tax = scheme_tax or namespaces.SCHEME_TAX_ID
    vat = _digits(partner.vat)
    if not vat:
        return "", ""
    branch = _digits(getattr(partner, "branch_code", "") or "")
    if len(vat) == 13 and branch:
        return vat + branch.zfill(5), scheme_tax
    if len(vat) == 18:
        return vat, scheme_tax
    if len(vat) == 13:
        return vat, scheme_national if partner.is_company is False else scheme_tax
    return vat, scheme_tax


class EtaxXmlBuilder:
    """Turn an ``od19.etax.document`` record into an unsigned XML tree."""

    def __init__(self, document):
        self.document = document
        self.move = document.move_id
        if not self.move:
            raise BuildError("The e-Tax document is not linked to a journal entry.")
        self.company = document.company_id or self.move.company_id
        self.seller = self.company.partner_id
        self.buyer = self.move.commercial_partner_id or self.move.partner_id
        self.ship = self.move.partner_shipping_id or self.buyer
        self.type_key = document.document_type
        if self.type_key not in namespaces.DOCUMENT_TYPES:
            raise BuildError("Unsupported document type: %s" % self.type_key)
        self.spec = namespaces.DOCUMENT_TYPES[self.type_key]
        self.rsm = namespaces.rsm_namespace(self.type_key)
        self.ram = namespaces.ram_namespace(self.type_key)
        self.tz = (
            self.document.env.context.get("tz")
            or self.document.env.user.tz
            or "Asia/Bangkok"
        )
        # Thai e-Tax documents are expressed with positive magnitudes; the
        # debit/credit direction is carried by the document TypeCode instead.
        self.sign = -1 if self.move.amount_total < 0 else 1

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _amount(self, value):
        return formats.format_amount(abs(value or 0.0) * 1.0)

    def _rate(self, value):
        return formats.format_rate(abs(value or 0.0))

    def _doc_amount(self, company_amount):
        """Convert a company-currency amount into the document currency."""
        company_amount = abs(company_amount or 0.0)
        company_currency = self.move.company_currency_id
        if not company_currency or company_currency == self.move.currency_id:
            return company_amount
        date = self.move.invoice_date or self.move.date or fields.Date.today()
        return company_currency._convert(
            company_amount, self.move.currency_id, self.company, date
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def build(self):
        nsmap = OrderedDict([
            (namespaces.RSM_PREFIX, self.rsm),
            (namespaces.RAM_PREFIX, self.ram),
            (namespaces.DS_PREFIX, namespaces.XMLDSIG_NS),
            ("xsi", _XSI_NS),
        ])
        root = etree.Element(
            _q(self.rsm, namespaces.root_element(self.type_key)), nsmap=nsmap
        )
        root.set(
            _q(_XSI_NS, "schemaLocation"),
            "%s %s_CrossIndustryInvoice_2p0.xsd" % (self.rsm, self.spec["class"]),
        )
        self._build_context(root)
        self._build_document(root)
        self._build_transaction(root)
        return root

    # ------------------------------------------------------------------
    # ExchangedDocumentContext
    # ------------------------------------------------------------------
    def _build_context(self, root):
        ctx = _el(root, self.rsm, "ExchangedDocumentContext")
        param = _el(ctx, self.ram, "GuidelineSpecifiedDocumentContextParameter")
        _el(
            param, self.ram, "ID", namespaces.GUIDELINE_ID,
            {"schemeAgencyID": namespaces.GUIDELINE_ID_NAME,
             "schemeVersionID": namespaces.GUIDELINE_ID_VERSION},
        )

    # ------------------------------------------------------------------
    # ExchangedDocument
    # ------------------------------------------------------------------
    def _build_document(self, root):
        doc = self.document
        node = _el(root, self.rsm, "ExchangedDocument")
        _el(node, self.ram, "ID", _text(doc.name or self.move.name, 35))
        _el(
            node, self.ram, "Name",
            _text(namespaces.document_name(self.type_key, self.move.dncn), 35),
        )
        _el(
            node, self.ram, "TypeCode", doc.type_code or self.spec["type_code"],
            {"listID": "1001_ThaiDocumentNameCodeInvoice", "listAgencyID": "RD/ETDA"},
        )
        _el(
            node, self.ram, "IssueDateTime",
            formats.format_datetime(doc.issue_datetime or self.move.invoice_date, self.tz),
        )
        _el(node, self.ram, "PurposeCode", doc.purpose_code or self.spec["purpose_code"])
        if doc.global_id:
            _el(
                node, self.ram, "GlobalID", _text(doc.global_id, 70),
                {"schemeID": "OID", "schemeAgencyID": "ETDA"},
            )
        _el(
            node, self.ram, "CreationDateTime",
            formats.format_datetime(doc.create_date, self.tz),
        )
        note = doc.get_note_text()
        if note:
            note_node = _el(node, self.ram, "IncludedNote")
            _el(note_node, self.ram, "Subject", "หมายเหตุ")
            _el(note_node, self.ram, "Content", _text(note, 500))

    # ------------------------------------------------------------------
    # SupplyChainTradeTransaction
    # ------------------------------------------------------------------
    def _build_transaction(self, root):
        txn = _el(root, self.rsm, "SupplyChainTradeTransaction")
        self._build_agreement(txn)
        self._build_delivery(txn)
        self._build_settlement(txn)
        self._build_lines(txn)

    def _build_agreement(self, txn):
        agreement = _el(txn, self.ram, "ApplicableHeaderTradeAgreement")
        self._build_party(agreement, "SellerTradeParty", self.seller, is_seller=True)
        if namespaces.omits_buyer_party(self.type_key):
            return
        self._build_party(agreement, "BuyerTradeParty", self.buyer)
        self._build_references(agreement)

    def _build_references(self, agreement):
        move = self.move
        origin = _text(move.ref or move.invoice_origin, 35)
        if origin:
            ref = _el(agreement, self.ram, "BuyerOrderReferencedDocument")
            _el(ref, self.ram, "IssuerAssignedID", origin)
        reference = self._referenced_document()
        if reference:
            name, type_code = reference
            ref = _el(agreement, self.ram, "AdditionalReferencedDocument")
            _el(ref, self.ram, "IssuerAssignedID", name)
            _el(ref, self.ram, "ReferenceTypeCode", type_code)

    def _referenced_document(self):
        """Return ``(name, type_code)`` of the document this one refers to.

        Debit and credit notes (and cancellation notes) must always carry an
        ``AdditionalReferencedDocument``, so the note's own reference is used
        as a last resort when the source document is not linked.
        """
        source = self.document.source_document_id
        if source and source.name:
            return (
                _text(source.name, 35),
                source.type_code or namespaces.REFERENCE_TYPE_TAX_INVOICE,
            )
        origin = self.move.reversed_entry_id
        if origin and origin.name:
            return _text(origin.name, 35), namespaces.REFERENCE_TYPE_TAX_INVOICE
        if namespaces.requires_original_reference(self.type_key):
            name = _text(self.move.name, 35)
            if name:
                return name, namespaces.REFERENCE_TYPE_TAX_INVOICE
        return None

    def _build_party(self, parent, tag, partner, is_seller=False):
        if not partner:
            raise BuildError("The document is missing a %s." % tag)
        node = _el(parent, self.ram, tag)
        identifier = _text(
            getattr(partner, "ref", "") or partner.id and str(partner.id), 35
        )
        if identifier:
            _el(node, self.ram, "ID", identifier)
        global_id = _digits(partner.vat)
        if len(global_id) == 13:
            _el(
                node, self.ram, "GlobalID", global_id,
                {"schemeID": namespaces.SCHEME_TAX_ID,
                 "schemeAgencyID": namespaces.SCHEME_AGENCY_RD},
            )
        name = _text(
            getattr(partner, "tax_name", "") or partner.name, 256
        )
        _el(node, self.ram, "Name", name)
        self._build_tax_registration(node, partner)
        self._build_contact(node, partner)
        self._build_address(node, partner)

    def _build_tax_registration(self, party, partner):
        tin, scheme = tax_identity(partner)
        if not tin:
            return
        node = _el(party, self.ram, "SpecifiedTaxRegistration")
        _el(
            node, self.ram, "ID", tin,
            {"schemeID": scheme, "schemeAgencyID": namespaces.SCHEME_AGENCY_RD},
        )

    def _build_contact(self, party, partner):
        email = _text(partner.email, 256)
        phone = formats.format_phone(partner.phone or partner.mobile)
        if not email and not phone:
            return
        node = _el(party, self.ram, "DefinedTradeContact")
        if email:
            element, complete_number = namespaces.contact_email_element(self.type_key)
            comm = _el(node, self.ram, element)
            _el(comm, self.ram, "URIID", "mailto:%s" % email, {"schemeID": "SMTP"})
            if complete_number:
                _el(comm, self.ram, "CompleteNumber", email)
        if phone:
            comm = _el(node, self.ram, "TelephoneUniversalCommunication")
            _el(comm, self.ram, "CompleteNumber", phone)

    def _build_address(self, party, partner):
        node = _el(party, self.ram, "PostalTradeAddress")
        p = partner
        _el(node, self.ram, "PostcodeCode", _text(p.zip, 16))
        _el(node, self.ram, "BuildingName", _text(p.street2, 70))
        _el(node, self.ram, "LineOne", _text(p.street, 256))
        _el(node, self.ram, "StreetName", _text(getattr(p, "od19_etax_street_name", ""), 70))
        _el(node, self.ram, "CityName", _digits(getattr(p, "od19_etax_city_code", "")))
        _el(
            node, self.ram, "CitySubDivisionName",
            _digits(getattr(p, "od19_etax_subdivision_code", "")),
        )
        country = (p.country_id.code or "TH").upper()
        _el(
            node, self.ram, "CountryID", country,
            {"schemeID": namespaces.COUNTRY_SCHEME_ID},
        )
        _el(
            node, self.ram, "CountrySubDivisionID",
            _digits(getattr(p, "od19_etax_province_code", "")) or _digits(p.state_id.code),
        )
        _el(
            node, self.ram, "BuildingNumber",
            _text(getattr(p, "od19_etax_building_number", ""), 16),
        )

    def _build_delivery(self, txn):
        delivery = _el(txn, self.ram, "ApplicableHeaderTradeDelivery")
        if self.ship and self.ship != self.seller:
            node = _el(delivery, self.ram, "ShipToTradeParty")
            self._build_address(node, self.ship)

    def _build_settlement(self, txn):
        settlement = _el(txn, self.ram, "ApplicableHeaderTradeSettlement")
        _el(
            settlement, self.ram, "InvoiceCurrencyCode",
            self.move.currency_id.name or "THB",
            {"listID": namespaces.CURRENCY_LIST_ID},
        )
        self._build_header_taxes(settlement)
        self._build_header_allowance(settlement)
        self._build_payment_terms(settlement)
        self._build_header_totals(settlement)

    def _tax_groups(self):
        """Aggregate posted tax lines into ``rate -> {base, amount}`` buckets."""
        groups = OrderedDict()
        tax_lines = self.move.line_ids.filtered(lambda line: line.tax_line_id)
        for line in tax_lines:
            tax = line.tax_line_id
            rate = tax.amount if tax.amount_type == "percent" else 0.0
            bucket = groups.setdefault(rate, {"base": 0.0, "amount": 0.0})
            bucket["base"] += self._doc_amount(line.tax_base_amount)
            bucket["amount"] += abs(line.amount_currency or line.amount)
        return groups

    def _build_header_taxes(self, settlement):
        groups = self._tax_groups()
        if not groups:
            groups = {0.0: {
                "base": abs(self.move.amount_untaxed),
                "amount": abs(self.move.amount_tax),
            }}
        for rate, values in groups.items():
            node = _el(settlement, self.ram, "ApplicableTradeTax")
            _el(node, self.ram, "TypeCode", "VAT", {"listID": "5153"})
            _el(node, self.ram, "CalculatedRate", self._rate(rate))
            _el(node, self.ram, "BasisAmount", self._amount(values["base"]),
                {"currencyID": self.move.currency_id.name})
            _el(node, self.ram, "CalculatedAmount", self._amount(values["amount"]),
                {"currencyID": self.move.currency_id.name})

    def _build_header_allowance(self, settlement):
        allowance = self.document._compute_header_allowance()
        if allowance <= 0:
            return
        node = _el(settlement, self.ram, "SpecifiedTradeAllowanceCharge")
        _el(node, self.ram, "ChargeIndicator", "false")
        _el(node, self.ram, "ActualAmount", self._amount(allowance),
            {"currencyID": self.move.currency_id.name})
        _el(node, self.ram, "ReasonCode", "95")
        _el(node, self.ram, "Reason", "ส่วนลดจากราคาปกติ")

    def _build_payment_terms(self, settlement):
        move = self.move
        terms_name = _text(move.invoice_payment_term_id.name, 256)
        due = move.invoice_date_due
        if not terms_name and not due:
            return
        node = _el(settlement, self.ram, "SpecifiedTradePaymentTerms")
        if terms_name:
            _el(node, self.ram, "Description", terms_name)
        if due:
            _el(node, self.ram, "DueDateDateTime", formats.format_datetime(due, self.tz))

    def _build_header_totals(self, settlement):
        move = self.move
        node = _el(
            settlement, self.ram, "SpecifiedTradeSettlementHeaderMonetarySummation"
        )
        currency = {"currencyID": move.currency_id.name}
        gross = self.document._compute_gross_line_total()
        allowance = self.document._compute_header_allowance()
        # Debit/credit and cancellation notes use a different summation type
        # (``TradeSettlementMonetaryHeaderSummationType``) which additionally
        # requires the original and the difference amounts.
        note = namespaces.requires_original_reference(self.type_key)
        if note:
            _el(
                node, self.ram, "OriginalInformationAmount",
                self._amount(self._original_document_amount()), currency,
            )
        _el(node, self.ram, "LineTotalAmount", self._amount(gross), currency)
        if note:
            _el(
                node, self.ram, "DifferenceInformationAmount",
                self._amount(move.amount_total), currency,
            )
        if allowance > 0:
            _el(node, self.ram, "AllowanceTotalAmount", self._amount(allowance), currency)
        _el(node, self.ram, "TaxBasisTotalAmount", self._amount(move.amount_untaxed), currency)
        _el(node, self.ram, "TaxTotalAmount", self._amount(move.amount_tax), currency)
        _el(node, self.ram, "GrandTotalAmount", self._amount(move.amount_total), currency)

    def _original_document_amount(self):
        """Return the total of the document referenced by a note.

        The reference comes from the linked e-Tax document, else from the
        reversal relationship, and finally from the note itself so the
        mandatory ``OriginalInformationAmount`` is never left empty.
        """
        source = self.document.source_document_id
        origin = source.move_id if source and source.move_id else self.move.reversed_entry_id
        if not origin:
            return self.move.amount_total
        amount = abs(origin.amount_total)
        if origin.currency_id != self.move.currency_id:
            amount = origin.currency_id._convert(
                amount,
                self.move.currency_id,
                self.company,
                origin.invoice_date or origin.date or fields.Date.today(),
            )
        return amount

    # ------------------------------------------------------------------
    # Line items
    # ------------------------------------------------------------------
    def _build_lines(self, txn):
        lines = self.move.invoice_line_ids.filtered(
            lambda line: line.display_type == "product" and line.quantity
        )
        if not lines:
            raise BuildError("The journal entry has no billable lines.")
        for index, line in enumerate(lines, start=1):
            self._build_line(txn, line, index)

    def _build_line(self, txn, line, index):
        node = _el(txn, self.ram, "IncludedSupplyChainTradeLineItem")
        doc_line = _el(node, self.ram, "AssociatedDocumentLineDocument")
        _el(doc_line, self.ram, "LineID", str(index))

        product = _el(node, self.ram, "SpecifiedTradeProduct")
        _el(product, self.ram, "ID", _text(line.product_id.default_code, 35))
        _el(product, self.ram, "Name", _text(self._line_label(line), 256))

        agreement = _el(node, self.ram, "SpecifiedLineTradeAgreement")
        price = _el(agreement, self.ram, "GrossPriceProductTradePrice")
        _el(price, self.ram, "ChargeAmount", self._amount(line.price_unit),
            {"currencyID": self.move.currency_id.name})

        delivery = _el(node, self.ram, "SpecifiedLineTradeDelivery")
        _el(
            delivery, self.ram, "BilledQuantity",
            formats.format_quantity(abs(line.quantity)),
            {"unitCode": formats.unit_code(line.product_uom_id)},
        )
        self._build_line_settlement(node, line)

    def _build_line_settlement(self, node, line):
        settlement = _el(node, self.ram, "SpecifiedLineTradeSettlement")
        subtotal = abs(line.price_subtotal)
        total = abs(line.price_total)
        tax_amount = max(total - subtotal, 0.0)
        rate = (tax_amount / subtotal * 100.0) if subtotal else 0.0

        tax = _el(settlement, self.ram, "ApplicableTradeTax")
        _el(tax, self.ram, "TypeCode", "VAT", {"listID": "5153"})
        _el(tax, self.ram, "CalculatedRate", self._rate(rate))
        _el(tax, self.ram, "BasisAmount", self._amount(subtotal),
            {"currencyID": self.move.currency_id.name})
        _el(tax, self.ram, "CalculatedAmount", self._amount(tax_amount),
            {"currencyID": self.move.currency_id.name})

        discount = abs(line.price_unit * line.quantity) - subtotal
        if discount > 0.00001 and not self._price_includes_tax(line):
            allowance = _el(settlement, self.ram, "SpecifiedTradeAllowanceCharge")
            _el(allowance, self.ram, "ChargeIndicator", "false")
            _el(allowance, self.ram, "ActualAmount", self._amount(discount),
                {"currencyID": self.move.currency_id.name})
            _el(allowance, self.ram, "ReasonCode", "95")
            _el(allowance, self.ram, "Reason", "ส่วนลดจากราคาปกติ")

        summation = _el(
            settlement, self.ram, "SpecifiedTradeSettlementLineMonetarySummation"
        )
        _el(summation, self.ram, "TaxTotalAmount", self._amount(tax_amount),
            {"currencyID": self.move.currency_id.name})
        _el(summation, self.ram, "NetLineTotalAmount", self._amount(subtotal),
            {"currencyID": self.move.currency_id.name})
        _el(summation, self.ram, "NetIncludingTaxesLineTotalAmount", self._amount(total),
            {"currencyID": self.move.currency_id.name})

    @staticmethod
    def _price_includes_tax(line):
        return any(tax.price_include for tax in line.tax_ids)

    @staticmethod
    def _line_label(line):
        if line.product_id:
            return line.product_id.display_name or line.name or ""
        from odoo.tools import html2plaintext

        return html2plaintext(line.name or "")


def build_unsigned_tree(document):
    """Return the unsigned :class:`lxml.etree._Element` for ``document``."""
    return EtaxXmlBuilder(document).build()


def build_unsigned_xml(document, pretty_print=False):
    """Return the unsigned XML as UTF-8 bytes with an XML declaration."""
    tree = build_unsigned_tree(document)
    return etree.tostring(
        tree, xml_declaration=True, encoding="UTF-8", pretty_print=pretty_print
    )
