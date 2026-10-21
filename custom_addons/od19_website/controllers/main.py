import base64
import datetime
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

# Extensions accepted for uploaded documents (checked on the filename suffix).
ALLOWED_DOC_EXT = (
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".jpg", ".jpeg", ".png", ".gif", ".zip", ".rar", ".txt",
)

# Hard limits to protect the server from oversized uploads.
MAX_RESUME_SIZE = 10 * 1024 * 1024      # 10 MB
MAX_DOCUMENT_SIZE = 10 * 1024 * 1024    # 10 MB per supporting document
MAX_DOCUMENTS = 5


class AutoInfoWebsite(http.Controller):
    """Controllers for the Auto-Info corporate website and employee portal."""

    # ------------------------------------------------------------------
    # Employee portal
    # ------------------------------------------------------------------
    @http.route(
        ["/employee-portal"],
        type="http",
        auth="user",
        website=True,
        sitemap=False,
    )
    def employee_portal(self, **kwargs):
        """Employee portal homepage.

        Only authenticated internal users can access this page.
        """
        Announcement = request.env["announcement"]
        today = datetime.date.today()
        announcements = Announcement.sudo().search(
            [
                ("published", "=", True),
                "|",
                ("expiry_date", "=", False),
                ("expiry_date", ">=", today),
            ],
            limit=5,
            order="published_date desc, create_date desc",
        )
        return request.render(
            "od19_website.od19_employee_portal",
            {
                "user": request.env.user,
                "datetime": datetime,
                "announcements": announcements,
            },
        )

    # ------------------------------------------------------------------
    # Careers
    # ------------------------------------------------------------------
    def _od19_get_openings(self):
        """Return all published and still-open job openings."""
        openings = request.env["od19.job.opening"].sudo().search(
            [("is_published", "=", True)], order="sequence, id desc"
        )
        return openings.filtered(lambda opening: opening.is_open)

    @http.route(
        ["/careers", "/careers/page/<int:page>"],
        type="http",
        auth="public",
        website=True,
        sitemap=True,
    )
    def careers(self, department=None, page=1, **kwargs):
        """Public listing of open job positions."""
        openings = self._od19_get_openings()

        departments = [
            ("industrial", "Industrial Automation", "fa-industry"),
            ("building", "Building Automation", "fa-building"),
            ("terminal", "Terminal Automation", "fa-tint"),
            ("support", "Sales & Administration", "fa-briefcase"),
        ]
        # Only advertise departments that actually have an opening.
        active_departments = {
            opening.department for opening in openings
        }
        department_cards = [
            {
                "key": key,
                "label": label,
                "icon": icon,
                "count": len(openings.filtered(lambda o, k=key: o.department == k)),
            }
            for key, label, icon in departments
            if key in active_departments
        ]

        if department:
            openings = openings.filtered(lambda o: o.department == department)

        return request.render(
            "od19_website.od19_careers_list",
            {
                "openings": openings,
                "department_cards": department_cards,
                "current_department": department,
                "total_count": len(self._od19_get_openings()),
            },
        )

    @http.route(
        ["/careers/<int:job_id>"],
        type="http",
        auth="public",
        website=True,
        sitemap=True,
    )
    def career_detail(self, job_id, **kwargs):
        """Detail page of a single job opening."""
        opening = request.env["od19.job.opening"].sudo().browse(job_id)
        if not opening.exists() or not opening.is_open:
            raise request.not_found()

        related = request.env["od19.job.opening"].sudo().search(
            [
                ("is_published", "=", True),
                ("id", "!=", opening.id),
                ("department", "=", opening.department),
            ],
            order="sequence, id desc",
            limit=3,
        )
        related = related.filtered(lambda o: o.is_open)
        return request.render(
            "od19_website.od19_careers_detail",
            {"opening": opening, "related": related},
        )

    @http.route(
        ["/careers/<int:job_id>/apply"],
        type="http",
        auth="public",
        website=True,
        methods=["GET", "POST"],
        sitemap=False,
    )
    def career_apply(self, job_id, **post):
        """Application form (GET) and submission handler (POST)."""
        opening = request.env["od19.job.opening"].sudo().browse(job_id)
        if not opening.exists() or not opening.is_open:
            raise request.not_found()

        errors = {}
        values = {"job_id": opening.id}

        if request.httprequest.method == "POST":
            file_storage = request.httprequest.files

            name = (post.get("name") or "").strip()
            email = (post.get("email") or "").strip()
            phone = (post.get("phone") or "").strip()
            consent = post.get("consent")

            if not name:
                errors["name"] = "Please enter your full name."
            if not email or "@" not in email or "." not in email.split("@")[-1]:
                errors["email"] = "Please enter a valid email address."
            if not phone:
                errors["phone"] = "Please enter a contact phone number."
            if not consent:
                errors["consent"] = "Please accept the privacy notice before submitting."

            resume_file = file_storage.get("resume")
            documents = [
                doc for doc in file_storage.getlist("documents") if doc and doc.filename
            ]

            if not resume_file or not resume_file.filename:
                errors["resume"] = "Please attach your resume / CV."
            elif not resume_file.filename.lower().endswith(ALLOWED_DOC_EXT):
                errors["resume"] = "Unsupported resume file type."
            else:
                resume_file.seek(0, 2)
                if resume_file.tell() > MAX_RESUME_SIZE:
                    errors["resume"] = "The resume must not exceed 10 MB."
                resume_file.seek(0)

            if len(documents) > MAX_DOCUMENTS:
                errors["documents"] = "You can attach up to %s documents." % MAX_DOCUMENTS
            for document in documents:
                document.seek(0, 2)
                if document.tell() > MAX_DOCUMENT_SIZE:
                    errors["documents"] = (
                        "Each supporting document must not exceed 10 MB."
                    )
                    break
                document.seek(0)

            if not errors:
                try:
                    application = request.env["od19.job.application"].sudo().create(
                        {
                            "job_id": opening.id,
                            "name": name,
                            "email": email,
                            "phone": phone,
                            "current_company": (post.get("current_company") or "").strip(),
                            "current_position": (post.get("current_position") or "").strip(),
                            "years_experience": self._od19_to_float(
                                post.get("years_experience")
                            ),
                            "expected_salary": (post.get("expected_salary") or "").strip(),
                            "available_date": post.get("available_date") or False,
                            "source": (post.get("source") or "").strip(),
                            "cover_letter": (post.get("cover_letter") or "").strip(),
                        }
                    )
                    self._od19_attach_files(application, resume_file, documents)
                except Exception:  # noqa: BLE001 - never expose a traceback to applicants
                    _logger.exception("Failed to record job application.")
                    return request.redirect("/careers/%s/apply?error=1" % opening.id)

                return request.redirect(
                    "/careers/thank-you?ref=%s" % (application.reference or "")
                )

            # Keep what the applicant typed so the form can be re-displayed.
            values.update(post)

        return request.render(
            "od19_website.od19_careers_apply",
            {
                "opening": opening,
                "errors": errors,
                "values": values,
                "allowed_ext": ", ".join(ALLOWED_DOC_EXT),
                "max_documents": MAX_DOCUMENTS,
            },
        )

    @http.route(
        ["/careers/thank-you"],
        type="http",
        auth="public",
        website=True,
        sitemap=False,
    )
    def career_thank_you(self, ref=None, **kwargs):
        """Confirmation page shown after a successful submission."""
        return request.render(
            "od19_website.od19_careers_thank_you",
            {"reference": ref, "job": kwargs.get("job")},
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _od19_to_float(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _od19_attach_files(application, resume_file, documents):
        """Store the resume and the supporting documents as attachments."""
        if resume_file and resume_file.filename:
            resume_file.seek(0)
            application.write(
                {
                    "resume": base64.b64encode(resume_file.read()),
                    "resume_filename": resume_file.filename,
                }
            )

        attachment_ids = []
        for document in documents:
            document.seek(0)
            attachment = (
                request.env["ir.attachment"]
                .sudo()
                .create(
                    {
                        "name": document.filename,
                        "datas": base64.b64encode(document.read()),
                        "res_model": "od19.job.application",
                        "res_id": application.id,
                    }
                )
            )
            attachment_ids.append(attachment.id)

        if attachment_ids:
            application.write({"document_ids": [(6, 0, attachment_ids)]})
