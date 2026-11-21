# -*- coding: utf-8 -*-
{
    'name': 'User Guide Manual (Full Handbook)',
    'version': '19.0.1.1.0',
    'category': 'Tools/User Guide',
    'summary': 'Full Odoo 19 handbook served inside the system (single HTML + search)',
    'description': """
OD19 User Guide Manual
======================
Serves the full AutoInfo Odoo 19 user handbook (all business domains,
17 parts, 127 modules) as a single searchable HTML page inside the system.

The handbook is built offline from the modular sources under
``docs/od19_user_guide/`` (shell_head.html + parts/*.html + shell_foot.html)
so each part can be edited independently and re-assembled with ``build.ps1``.
The assembled file is copied to ``static/src/guide/index.html`` and exposed
to any internal user through the ``/od19/guide`` route, shown under the
existing *User Guide* menu alongside the interactive tours.
    """,
    'depends': [
        'web',
        'od19_user_guide_tours',
    ],
    'data': [
        'views/guide_menus.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
    'author': 'OD19',
    'icon': '/od19_user_guide_manual/static/description/icon.svg',
}
