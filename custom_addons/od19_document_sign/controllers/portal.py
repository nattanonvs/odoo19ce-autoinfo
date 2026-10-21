import binascii

from odoo import _, http
from odoo.exceptions import AccessError, MissingError, UserError
from odoo.http import request

from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager


class Od19DocumentPortal(CustomerPortal):

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _document_domain(self):
        partner = request.env.user.partner_id
        return [("partner_id", "=", partner.id)]

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if "document_count" in counters:
            values["document_count"] = request.env["od19.document"].search_count(
                self._document_domain()
            )
        return values

    # ------------------------------------------------------------------
    # List of documents
    # ------------------------------------------------------------------
    @http.route(
        ["/my/documents", "/my/documents/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_documents(self, page=1, sortby=None, **kw):
        Document = request.env["od19.document"]
        values = self._prepare_portal_layout_values()
        domain = self._document_domain()

        searchbar_sortings = {
            "date": {"label": _("Newest"), "order": "id desc"},
            "name": {"label": _("Number"), "order": "name"},
            "state": {"label": _("Status"), "order": "state"},
        }
        if not sortby or sortby not in searchbar_sortings:
            sortby = "date"
        order = searchbar_sortings[sortby]["order"]

        document_count = Document.search_count(domain)
        pager = portal_pager(
            url="/my/documents",
            url_args={"sortby": sortby},
            total=document_count,
            page=page,
            step=self._items_per_page,
        )
        documents = Document.search(
            domain, order=order, limit=self._items_per_page, offset=pager["offset"]
        )
        request.session["my_documents_history"] = documents.ids[:100]

        values.update({
            "documents": documents,
            "page_name": "document",
            "default_url": "/my/documents",
            "pager": pager,
            "searchbar_sortings": searchbar_sortings,
            "sortby": sortby,
        })
        return request.render("od19_document_sign.portal_my_documents", values)

    # ------------------------------------------------------------------
    # Document detail
    # ------------------------------------------------------------------
    @http.route(
        ["/my/documents/<int:document_id>"],
        type="http",
        auth="public",
        website=True,
    )
    def portal_my_document_detail(self, document_id, access_token=None, **kw):
        try:
            document_sudo = self._document_check_access(
                "od19.document", document_id, access_token
            )
        except (AccessError, MissingError):
            return request.redirect("/my")

        values = {
            "page_name": "document",
            "document": document_sudo,
        }
        values = self._get_page_view_values(
            document_sudo, access_token, values, "my_documents_history", False, **kw
        )
        return request.render("od19_document_sign.portal_document_detail", values)

    # ------------------------------------------------------------------
    # Signing page (one signer at a time, secured by its own token)
    # ------------------------------------------------------------------
    @http.route(
        ["/my/documents/sign/<int:signer_id>"],
        type="http",
        auth="public",
        website=True,
    )
    def portal_document_sign(self, signer_id, access_token=None, **kw):
        try:
            signer_sudo = self._document_check_access(
                "od19.document.signer", signer_id, access_token
            )
        except (AccessError, MissingError):
            return request.redirect("/my")

        signer_sudo._ensure_token()
        values = {
            "page_name": "document_sign",
            "signer": signer_sudo,
            "document": signer_sudo.document_id,
        }
        values = self._get_page_view_values(
            signer_sudo.document_id,
            access_token,
            values,
            "my_documents_history",
            False,
            **kw,
        )
        return request.render("od19_document_sign.portal_document_sign", values)

    @http.route(
        ["/my/documents/sign/<int:signer_id>/sign"],
        type="jsonrpc",
        auth="public",
        website=True,
    )
    def portal_document_sign_submit(
        self, signer_id, access_token=None, name=None, signature=None
    ):
        access_token = access_token or request.httprequest.args.get("access_token")
        try:
            signer_sudo = self._document_check_access(
                "od19.document.signer", signer_id, access_token=access_token
            )
        except (AccessError, MissingError):
            return {"error": _("Invalid document.")}

        if not signature:
            return {"error": _("Signature is missing.")}

        try:
            signer_sudo._sign(name=name, signature=signature)
            # flush now so the signature is available to the PDF renderer
            request.env.cr.flush()
        except (TypeError, binascii.Error):
            return {"error": _("Invalid signature data.")}
        except UserError as error:
            return {"error": str(error)}

        document = signer_sudo.document_id
        pdf = request.env["ir.actions.report"].sudo()._render_qweb_pdf(
            "od19_document_sign.action_report_od19_document", [document.id]
        )[0]
        document.message_post(
            attachments=[("%s.pdf" % document.name, pdf)],
            author_id=signer_sudo.partner_id.id,
            body=_("Document signed by %s", name or signer_sudo.partner_id.name),
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
        )
        # Reload the signing page, which now shows the "signed" confirmation.
        return {"force_refresh": True}

    @http.route(
        ["/my/documents/sign/<int:signer_id>/refuse"],
        type="http",
        auth="public",
        methods=["POST"],
        website=True,
    )
    def portal_document_refuse(
        self, signer_id, access_token=None, refusal_reason=None, **kw
    ):
        try:
            signer_sudo = self._document_check_access(
                "od19.document.signer", signer_id, access_token=access_token
            )
        except (AccessError, MissingError):
            return request.redirect("/my")

        try:
            signer_sudo._refuse(reason=refusal_reason)
        except UserError:
            pass
        return request.redirect(
            "/my/documents/sign/%s?access_token=%s"
            % (signer_sudo.id, signer_sudo.access_token or "")
        )
