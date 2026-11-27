"""Drop the stale title view so the new single-owner title override can load.

Background
----------
The project form title override used to be owned by ``od19_project_analytic``
(view ``view_project_project_form_inherit_od19``) and the enhanced title view
``view_project_project_form_title_inherit_od19_enhanced`` was stacked on top of
it (``inherit_id = 1657``) with an ``//h1[field[@name='job_no']]`` xpath.

The title override is now owned by ``od19_project_enhanced`` alone and inherits
``project.edit_project`` (``1505``) directly, so the analytic view no longer
renders ``h1/job_no``.

When this module is upgraded, ``ir.ui.view._check_xml()`` validates the enhanced
form view and calls ``_get_combined_archs()``, which pulls in *every* extension
descendant of the root view (recursive CTE in ``_get_inheriting_views``). The
stale title view is still an extension child of the analytic view, and because
it belongs to the module currently being upgraded it is NOT filtered out by
``_filter_loaded_views``. Applying its old ``//h1[field[@name='job_no']]`` xpath
on the parent tree (which no longer contains that node) raises::

    Element '<xpath expr="//h1[field[@name='job_no']]">' cannot be located in parent view

Deleting the view (and its ir_model_data) before the module data loads lets the
XML recreate it with ``inherit_id = project.edit_project`` and leave exactly one
layer of title override.
"""


def migrate(cr, version):
    # Delete the ir_ui_view rows first (referenced by the ir_model_data rows
    # below); then remove the ir_model_data so the XML can recreate the view.
    cr.execute(
        """
        DELETE FROM ir_ui_view
        WHERE id IN (
            SELECT res_id FROM ir_model_data
            WHERE module = 'od19_project_enhanced'
              AND name = 'view_project_project_form_title_inherit_od19_enhanced'
              AND model = 'ir.ui.view'
        )
        """
    )
    cr.execute(
        """
        DELETE FROM ir_model_data
        WHERE module = 'od19_project_enhanced'
          AND name = 'view_project_project_form_title_inherit_od19_enhanced'
          AND model = 'ir.ui.view'
        """
    )
