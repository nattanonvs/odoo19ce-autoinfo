# -*- coding: utf-8 -*-
{
    'name': 'Service Card / Preventive Maintenance',
    'version': '19.0.1.0.0',
    'category': 'Services/After-Sales',
    'summary': 'Service cards for equipment maintenance tracking',
    'depends': ['stock', 'product', 'hr', 'sale'],
    'data': [
        'data/sequence.xml',
        'security/ir.model.access.csv',
        'views/service_card_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
