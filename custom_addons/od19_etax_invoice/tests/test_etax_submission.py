# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

"""Tests for the RD submission channel.

Covered: the mockable gateway adapter, the submission state machine, the
retry history and the offline fallback batch export used when the online
channel is unavailable.
"""

import base64
import csv
import io
import zipfile

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon

from ..lib import batch_export, rd_gateway
from .test_etax_document import _generate_self_signed_certificate

ENDPOINT = "https://etax.rd.go.th/mock"
PROVIDER_ID = "TEST-PROVIDER"


@tagged("post_install", "-at_install")
class TestOd19EtaxSubmission(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.company_data["company"]
        key_pem, cert_pem = _generate_self_signed_certificate()
        cls.certificate = cls.env["od19.etax.certificate"].create({
            "name": "OD19 RD Submission Test Certificate",
            "company_id": cls.company.id,
            "private_key": key_pem.decode(),
            "certificate": cert_pem.decode(),
        })
        cls.certificate.action_verify()
        cls.company.od19_etax_certificate_id = cls.certificate.id
        cls.company.od19_etax_enabled = True

    @classmethod
    def setup_independent_user(cls):
        """See ``TestOd19EtaxDocument.setup_independent_user``.

        ``base_user_role`` strips the accounting groups of a freshly created
        user as soon as ``od19_role_catalog`` grants it a default role.
        """
        user = super().setup_independent_user()
        user.sudo().role_line_ids.unlink()
        user.sudo().write({
            "group_ids": [Command.set(cls.get_default_groups().ids)],
        })
        return user

    def setUp(self):
        super().setUp()
        # Every test starts from a fully configured mock channel.
        self.company.write({
            "od19_etax_rd_mode": "mock",
            "od19_etax_rd_endpoint": ENDPOINT,
            "od19_etax_rd_provider_id": PROVIDER_ID,
        })

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _create_signed_document(self):
        invoice = self._create_invoice(post=True)
        document = self.env["od19.etax.document"].create({
            "move_id": invoice.id,
            "document_type": "tax_invoice",
        })
        document.action_sign()
        return document

    def _create_submission(self, *documents):
        return self.env["od19.etax.submission"].create({
            "company_id": self.company.id,
            "document_ids": [Command.set([d.id for d in documents])],
        })

    # ------------------------------------------------------------------
    # Gateway adapter
    # ------------------------------------------------------------------
    def test_gateway_selection(self):
        self.assertIsInstance(
            rd_gateway.get_gateway(self.company), rd_gateway.MockRdGateway
        )
        self.company.od19_etax_rd_mode = "live"
        self.assertIsInstance(
            rd_gateway.get_gateway(self.company), rd_gateway.LiveRdGateway
        )

    def test_mock_gateway_accepts_signed_document(self):
        document = self._create_signed_document()
        response = rd_gateway.get_gateway(self.company).submit(document)
        self.assertEqual(response["response_code"], "0")
        self.assertTrue(response["ref"].startswith("MOCK-%s-" % document.name))

    def test_gateway_requires_signed_payload(self):
        invoice = self._create_invoice()
        document = self.env["od19.etax.document"].create({
            "move_id": invoice.id,
            "document_type": "tax_invoice",
        })
        with self.assertRaises(rd_gateway.RdGatewayError):
            rd_gateway.get_gateway(self.company).submit(document)

    # ------------------------------------------------------------------
    # Submission flow
    # ------------------------------------------------------------------
    def test_signed_document_submission_is_accepted(self):
        document = self._create_signed_document()
        action = document.action_submit_to_rd()
        submission = self.env["od19.etax.submission"].browse(action["res_id"])
        self.assertEqual(submission.state, "accepted")
        self.assertEqual(submission.channel, "mock")
        self.assertEqual(submission.attempt_count, 1)
        self.assertEqual(submission.response_code, "0")
        self.assertTrue(submission.reference.startswith("MOCK-"))
        self.assertIn(document, submission.document_ids)

    def test_submit_requires_signed_document(self):
        invoice = self._create_invoice()
        document = self.env["od19.etax.document"].create({
            "move_id": invoice.id,
            "document_type": "tax_invoice",
        })
        with self.assertRaises(UserError):
            document.action_submit_to_rd()

    def test_missing_endpoint_marks_submission_failed(self):
        self.company.od19_etax_rd_endpoint = False
        document = self._create_signed_document()
        submission = self._create_submission(document)
        submission.action_submit()
        self.assertEqual(submission.state, "failed")
        self.assertEqual(submission.attempt_count, 1)
        self.assertIn("Endpoint", submission.response_message)

    def test_live_channel_is_not_implemented_yet(self):
        self.company.od19_etax_rd_mode = "live"
        document = self._create_signed_document()
        submission = self._create_submission(document)
        submission.action_submit()
        self.assertEqual(submission.state, "failed")
        self.assertEqual(submission.channel, "live")
        self.assertIn("ยังไม่รองรับ", submission.response_message)

    def test_retry_resends_failed_submission(self):
        self.company.od19_etax_rd_endpoint = False
        document = self._create_signed_document()
        submission = self._create_submission(document)
        submission.action_submit()
        self.assertEqual(submission.state, "failed")

        self.company.od19_etax_rd_endpoint = ENDPOINT
        submission.action_retry()
        self.assertEqual(submission.state, "accepted")
        self.assertEqual(submission.attempt_count, 2)

    def test_submission_requires_documents(self):
        submission = self.env["od19.etax.submission"].create({
            "company_id": self.company.id,
        })
        with self.assertRaises(UserError):
            submission.action_submit()

    # ------------------------------------------------------------------
    # Offline fallback batch export
    # ------------------------------------------------------------------
    def test_batch_zip_contains_signed_xml_and_manifest(self):
        document = self._create_signed_document()
        content = batch_export.build_batch_zip(document)
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            names = archive.namelist()
            self.assertIn(batch_export.MANIFEST_NAME, names)
            self.assertTrue(
                any(name.startswith("xml/") for name in names),
                "the signed XML must be part of the archive",
            )
            rows = list(csv.reader(
                io.StringIO(archive.read(batch_export.MANIFEST_NAME).decode("utf-8"))
            ))
        self.assertEqual(rows[0], list(batch_export.MANIFEST_HEADER))
        self.assertEqual(rows[1][0], document.name)
        self.assertEqual(rows[1][4], document.digest)

    def test_batch_export_requires_signed_document(self):
        invoice = self._create_invoice()
        document = self.env["od19.etax.document"].create({
            "move_id": invoice.id,
            "document_type": "tax_invoice",
        })
        with self.assertRaises(ValueError):
            batch_export.build_batch_zip(document)

    def test_action_export_batch_stores_archive(self):
        document = self._create_signed_document()
        submission = self._create_submission(document)
        submission.action_export_batch()
        self.assertTrue(submission.batch_file)
        self.assertTrue(submission.batch_filename.endswith(".zip"))
        self.assertTrue(submission.batch_exported_at)
        archive = zipfile.ZipFile(
            io.BytesIO(base64.b64decode(submission.batch_file))
        )
        self.assertIn(batch_export.MANIFEST_NAME, archive.namelist())
