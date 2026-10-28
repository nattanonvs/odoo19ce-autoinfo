# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

"""Namespace and code lists for ETDA Recommendation 3-2560 (ขมธอ.3-2560).

The e-Tax Invoice & e-Receipt XML is a subset profile of UN/CEFACT
CrossIndustryInvoice 9.1 published by ETDA.  Every document family has its own
root namespace (``..._CrossIndustryInvoice:2``) and its own reusable aggregate
business information entity namespace
(``..._{Class}_ReusableAggregateBusinessInformationEntity:2``), therefore the
builder must not hardcode a single namespace.
"""

XMLDSIG_NS = "http://www.w3.org/2000/09/xmldsig#"
XADES_NS = "http://uri.etsi.org/01903/v1.3.2#"
XADES141_NS = "http://uri.etsi.org/01903/v1.4.1#"
UDT_NS = "urn:un:unece:uncefact:data:standard:UnqualifiedDataType:16"
QDT_NS = "urn:etda:uncefact:data:standard:QualifiedDataType:1"

RSM_PREFIX = "rsm"
RAM_PREFIX = "ram"
DS_PREFIX = "ds"

#: Guideline identifier of the specification this profile implements.
GUIDELINE_ID = "ER3-2560"
GUIDELINE_ID_NAME = "ETDA"
GUIDELINE_ID_VERSION = "v2.0"

#: Document type registry. ``class`` is used to derive the RSM/RAM namespaces.
#: ``type_code`` follows ThaiDocumentNameCode_Invoice_1p0.
DOCUMENT_TYPES = {
    "tax_invoice": {
        "label": "ใบกำกับภาษี (Tax Invoice)",
        "class": "TaxInvoice",
        "name": "ใบกำกับภาษี",
        "type_code": "388",
        "purpose_code": "TIVC01",
    },
    "receipt": {
        "label": "ใบรับ (Receipt)",
        "class": "Receipt",
        "name": "ใบรับ",
        "type_code": "T01",
        "purpose_code": "TIVC01",
    },
    "abbreviated_tax_invoice": {
        "label": "ใบกำกับภาษีอย่างย่อ (Abbreviated Tax Invoice)",
        "class": "AbbreviatedTaxInvoice",
        "name": "ใบกำกับภาษีอย่างย่อ",
        "type_code": "T05",
        "purpose_code": "TIVC01",
    },
    "invoice": {
        "label": "ใบแจ้งหนี้ (Invoice)",
        "class": "Invoice",
        "name": "ใบแจ้งหนี้",
        "type_code": "380",
        "purpose_code": "TIVC01",
    },
    "debit_credit_note": {
        "label": "ใบเพิ่มหนี้ / ใบลดหนี้ (Debit/Credit Note)",
        "class": "DebitCreditNote",
        "name": "ใบลดหนี้",
        "type_code": "81",
        "purpose_code": "CDNG01",
    },
    "cancellation_note": {
        "label": "ใบยกเลิก (Cancellation Note)",
        "class": "CancellationNote",
        "name": "ใบยกเลิก",
        "type_code": "T07",
        "purpose_code": "TIVC01",
    },
}

#: UN/ECE Recommendation 20 unit codes used for ``BilledQuantity/@unitCode``.
#: Odoo ``uom.uom`` has no UN/ECE column so we map by category/name and fall
#: back to ``C62`` (piece) which is the generic single-article code.
UNIT_CODES = {
    "unit": "C62",
    "units": "C62",
    "piece": "C62",
    "pieces": "C62",
    "ชิ้น": "C62",
    "อัน": "C62",
    "box": "BX",
    "boxes": "BX",
    "กล่อง": "BX",
    "pack": "PA",
    "packs": "PA",
    "แพ็ค": "PA",
    "set": "SET",
    "sets": "SET",
    "ชุด": "SET",
    "kg": "KGM",
    "kgs": "KGM",
    "kilogram": "KGM",
    "กิโลกรัม": "KGM",
    "g": "GRM",
    "gram": "GRM",
    "กรัม": "GRM",
    "l": "LTR",
    "liter": "LTR",
    "litre": "LTR",
    "ลิตร": "LTR",
    "m": "MTR",
    "meter": "MTR",
    "metre": "MTR",
    "เมตร": "MTR",
    "cm": "CMT",
    "mm": "MMT",
    "hour": "HUR",
    "hours": "HUR",
    "ชั่วโมง": "HUR",
    "day": "DAY",
    "days": "DAY",
    "วัน": "DAY",
    "month": "MON",
    "months": "MON",
    "เดือน": "MON",
    "year": "ANN",
    "years": "ANN",
    "ปี": "ANN",
    "service": "C62",
    "บริการ": "C62",
}

DEFAULT_UNIT_CODE = "C62"

#: Scheme identifiers used by ``SpecifiedTaxRegistration/ID``.
SCHEME_TAX_ID = "TXID"  # Juristic person (13 digits + 5 digit branch)
SCHEME_NATIONAL_ID = "NIDN"  # Natural person (13 digit citizen id)
SCHEME_AGENCY_RD = "RD"

#: Attribute value required on ``PostalTradeAddress/CountryID``.
COUNTRY_SCHEME_ID = "3166-1 alpha-2"

#: Attribute value required on ``InvoiceCurrencyCode``.
CURRENCY_LIST_ID = "ISO 4217 3A"

#: Editable document types offered on ``od19.etax.document``.
DOCUMENT_TYPE_SELECTION = [
    (key, value["label"]) for key, value in DOCUMENT_TYPES.items()
]

#: ``DefinedTradeContact`` email communication differs across the six document
#: families, even though the six XSDs are generated from the same model:
#:
#: * TaxInvoice / Receipt / Invoice / AbbreviatedTaxInvoice expose
#:   ``EmailURIUniversalCommunication`` (``ram:UniversalCommunicationType``)
#:   which carries both ``URIID`` and ``CompleteNumber``.
#: * DebitCreditNote exposes ``EmailURIUniversalCommunication``
#:   (``ram:EmailUniversalCommunicationType``) with ``URIID`` only.
#: * CancellationNote exposes ``EmailURICIUniversalCommunication``
#:   (``ram:EmailUniversalCommunicationType``) with ``URIID`` only.
_CONTACT_EMAIL_DEFAULT = ("EmailURIUniversalCommunication", True)
_CONTACT_EMAIL = {
    "debit_credit_note": ("EmailURIUniversalCommunication", False),
    "cancellation_note": ("EmailURICIUniversalCommunication", False),
}

#: Document families that must reference the original document through a
#: mandatory ``AdditionalReferencedDocument`` and report
#: ``OriginalInformationAmount`` / ``DifferenceInformationAmount``.
_ORIGINAL_REFERENCE_REQUIRED = frozenset({"debit_credit_note", "cancellation_note"})

#: Document families whose ``ApplicableHeaderTradeAgreement`` carries only the
#: seller. The abbreviated tax invoice (ใบกำกับภาษีอย่างย่อ, ม.86/6) omits the
#: buyer entirely, and its XSD does not declare ``BuyerTradeParty`` nor the
#: referenced-document elements, so they must never be emitted.
_BUYER_PARTY_OMITTED = frozenset({"abbreviated_tax_invoice"})

#: UN/ECE 1153 reference type code of the original tax invoice.
REFERENCE_TYPE_TAX_INVOICE = "388"

#: UN/ECE 1001 type codes of the DebitCreditNote family, resolved from the
#: ``account.move.dncn`` classification (od19_accounting_dncn): 80 is a debit
#: note (ใบเพิ่มหนี้) and 81 a credit note (ใบลดหนี้).
NOTE_TYPE_CODE_BY_DNCN = {"dn": "80", "cn": "81"}

#: Thai document names of the DebitCreditNote family.
NOTE_NAME_BY_DNCN = {"dn": "ใบเพิ่มหนี้", "cn": "ใบลดหนี้"}


def document_type_code(document_type, dncn=None):
    """Return the UN/ECE 1001 ``TypeCode`` of a document family.

    A ``debit_credit_note`` is split into a debit note (``80``) or a credit
    note (``81``) through the ``dncn`` value of its journal entry; every other
    family reports its fixed code.
    """
    spec = DOCUMENT_TYPES.get(document_type)
    if not spec:
        return False
    if document_type == "debit_credit_note":
        return NOTE_TYPE_CODE_BY_DNCN.get(dncn, spec["type_code"])
    return spec["type_code"]


def document_name(document_type, dncn=None):
    """Return the Thai ``Name`` of a document family.

    A ``debit_credit_note`` is named ใบเพิ่มหนี้ (debit) or ใบลดหนี้ (credit)
    through the ``dncn`` value of its journal entry.
    """
    spec = DOCUMENT_TYPES.get(document_type, {})
    if document_type == "debit_credit_note":
        return NOTE_NAME_BY_DNCN.get(dncn, spec.get("name", ""))
    return spec.get("name", "")


def contact_email_element(document_type):
    """Return ``(local_name, include_complete_number)`` for the contact email."""
    return _CONTACT_EMAIL.get(document_type, _CONTACT_EMAIL_DEFAULT)


def requires_original_reference(document_type):
    """Return ``True`` when the family must reference the original document."""
    return document_type in _ORIGINAL_REFERENCE_REQUIRED


def omits_buyer_party(document_type):
    """Return ``True`` when the family must not emit ``BuyerTradeParty``."""
    return document_type in _BUYER_PARTY_OMITTED


def rsm_namespace(document_type):
    """Return the root namespace for a document type key."""
    return (
        "urn:etda:uncefact:data:standard:%s_CrossIndustryInvoice:2"
        % DOCUMENT_TYPES[document_type]["class"]
    )


def ram_namespace(document_type):
    """Return the RAM namespace for a document type key."""
    return (
        "urn:etda:uncefact:data:standard:"
        "%s_ReusableAggregateBusinessInformationEntity:2"
        % DOCUMENT_TYPES[document_type]["class"]
    )


def root_element(document_type):
    """Return the root element local name for a document type key."""
    return "%s_CrossIndustryInvoice" % DOCUMENT_TYPES[document_type]["class"]
