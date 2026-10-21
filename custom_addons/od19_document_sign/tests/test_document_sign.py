from odoo import fields
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged

# A valid 1x1 transparent PNG used as a fake signature image.
SIGNATURE = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
    "YAAAAAYAAjCB0C8AAAAASUVORK5CYII="
)


@tagged("post_install", "-at_install")
class TestDocumentSign(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_1 = cls.env["res.partner"].create({
            "name": "Signer One",
            "email": "signer.one@example.com",
        })
        cls.partner_2 = cls.env["res.partner"].create({
            "name": "Signer Two",
            "email": "signer.two@example.com",
        })
        cls.template = cls.env["od19.document.template"].create({
            "name": "Test Signing Template",
            "body_html": "<p>Please sign this document.</p>",
            "role_ids": [
                (0, 0, {
                    "name": "Requester",
                    "partner_id": cls.partner_1.id,
                    "sequence": 10,
                }),
                (0, 0, {
                    "name": "Approver",
                    "partner_id": cls.partner_2.id,
                    "sequence": 20,
                }),
            ],
        })

    def _create_document(self):
        return self.env["od19.document"].create({"template_id": self.template.id})

    # ------------------------------------------------------------------
    def test_sequence_and_template_signers(self):
        """Numbering is applied and signers are copied from the template."""
        document = self._create_document()
        self.assertNotEqual(document.name, "/")
        self.assertEqual(len(document.signer_ids), 2)
        self.assertIn("Please sign this document.", document.body_html or "")
        self.assertEqual(document.signer_count, 2)
        self.assertEqual(document.signed_signer_count, 0)

    def test_send_then_sign_completes_document(self):
        """Sending opens the request and signing every role validates it."""
        document = self._create_document()
        document.action_send()
        self.assertEqual(document.state, "sent")
        self.assertTrue(all(s.state == "sent" for s in document.signer_ids))
        self.assertTrue(all(s.access_token for s in document.signer_ids))

        for signer in document.signer_ids.sorted("sequence"):
            signer._sign(name=signer.partner_id.name, signature=SIGNATURE)

        self.assertEqual(document.state, "signed")
        self.assertEqual(document.signed_signer_count, 2)
        self.assertEqual(document.signed_by, self.partner_2.name)
        self.assertTrue(document.signature)

    def test_sign_twice_raises(self):
        document = self._create_document()
        document.action_send()
        signer = document.signer_ids.sorted("sequence")[0]
        signer._sign(name=signer.partner_id.name, signature=SIGNATURE)
        with self.assertRaises(UserError):
            signer._sign(name=signer.partner_id.name, signature=SIGNATURE)

    def test_refusal_marks_document_refused(self):
        document = self._create_document()
        document.action_send()
        signer = document.signer_ids.sorted("sequence")[0]
        signer._refuse(reason="Terms not accepted")
        document.invalidate_recordset()
        self.assertEqual(document.state, "refused")
        self.assertEqual(document.refusal_reason, "Terms not accepted")

    def test_send_without_signer_raises(self):
        empty_template = self.env["od19.document.template"].create({
            "name": "Empty Template",
            "body_html": "<p>Nothing</p>",
        })
        document = self.env["od19.document"].create({
            "template_id": empty_template.id,
        })
        with self.assertRaises(UserError):
            document.action_send()

    def test_cron_expires_overdue_documents(self):
        document = self._create_document()
        document.action_send()
        document.date_deadline = fields.Datetime.subtract(
            fields.Datetime.now(), days=1
        )
        self.env["od19.document"]._cron_expire_documents()
        document.invalidate_recordset()
        self.assertEqual(document.state, "expired")

    def test_report_action_available(self):
        report = self.env.ref(
            "od19_document_sign.action_report_od19_document",
            raise_if_not_found=False,
        )
        self.assertTrue(report)
        self.assertEqual(report.model, "od19.document")
