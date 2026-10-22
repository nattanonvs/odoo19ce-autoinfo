"""Land employees on the self-service portal right after they log in."""

from odoo.addons.web.controllers.home import Home as WebHome
from odoo.http import request


class Home(WebHome):
    """Send employees to the employee portal instead of the backend.

    Odoo drops every internal user on ``/odoo`` after a successful login, so an
    employee who mostly uses the portal would have to click through to it every
    morning. Users linked to an employee record are taken to
    ``/employee-portal`` instead; they can still reach the backend from the
    portal's "กลับหน้าหลังบ้าน" button.

    The detour is skipped when the user asked for a specific page, when
    ``super()`` already chose another destination (external users, MFA
    challenge), and for administrators, who keep landing on the backend.
    """

    def _login_redirect(self, uid, redirect=None):
        target = super()._login_redirect(uid, redirect=redirect)
        if redirect or target != "/odoo":
            return target

        user = request.env["res.users"].sudo().browse(uid)
        if user.employee_id and not user.has_group("base.group_system"):
            return "/employee-portal"
        return target
