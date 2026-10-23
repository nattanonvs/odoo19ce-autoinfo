# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

"""XAdES-BES digital signature for the ขมธอ.3-2560 e-Tax Invoice XML.

ขมธอ.14-2560 requires an XML Advanced Electronic Signature.  The ETDA sample
documents use the RSA-SHA512 signature algorithm, the SHA-512 digest and the
inclusive XML canonicalisation 1.0, with a single enveloped-signature
``Transform`` on the document reference::

    <ds:CanonicalizationMethod Algorithm=".../REC-xml-c14n-20010315"/>
    <ds:SignatureMethod Algorithm=".../xmldsig-more#rsa-sha512"/>
    <ds:Reference URI="">
        <ds:Transforms>
            <ds:Transform Algorithm=".../xmldsig#enveloped-signature"/>
        </ds:Transforms>
        <ds:DigestMethod Algorithm=".../xmlenc#sha512"/>

``signxml`` (via :class:`signxml.xades.XAdESSigner`) produces exactly this
layout and appends the resulting ``ds:Signature`` as the last child of the root
element, which is the position mandated by the ``CrossIndustryInvoice`` schema.
"""

import logging

from signxml.algorithms import (
    CanonicalizationMethod,
    DigestAlgorithm,
    SignatureMethod,
)
from signxml.xades import XAdESDataObjectFormat, XAdESSigner

_logger = logging.getLogger(__name__)


class SigningError(Exception):
    """Raised when the document cannot be signed."""


def sign_tree(
    element,
    key,
    cert,
    passphrase=None,
    description="e-Tax Invoice",
    mime_type="text/xml",
):
    """Sign ``element`` in place and return the signed root element.

    :param element: the unsigned ``lxml.etree._Element`` tree.
    :param key: PEM encoded private key (``str``/``bytes``) or a
        :class:`cryptography` private key object.
    :param cert: PEM encoded certificate or a list of certificates forming the
        chain (leaf first).
    :param passphrase: passphrase of an encrypted private key, if any.
    """
    if not key:
        raise SigningError("A private key is required to sign an e-Tax document.")
    if not cert:
        raise SigningError("A signing certificate is required.")
    if isinstance(passphrase, str):
        passphrase = passphrase.encode()

    signer = XAdESSigner(
        signature_algorithm=SignatureMethod.RSA_SHA512,
        digest_algorithm=DigestAlgorithm.SHA512,
        c14n_algorithm=CanonicalizationMethod.CANONICAL_XML_1_0,
        data_object_format=XAdESDataObjectFormat(
            Description=description or "e-Tax Invoice",
            MimeType=mime_type or "text/xml",
        ),
    )
    try:
        return signer.sign(
            element,
            key=key,
            cert=cert,
            passphrase=passphrase,
            # The ETDA profile keeps only the enveloped-signature transform and
            # reports the signing certificate in KeyInfo/X509Data.
            exclude_c14n_transform_element=True,
            always_add_key_value=False,
        )
    except Exception as error:  # signxml raises a variety of exception types
        raise SigningError(str(error))
