# -*- coding: utf-8 -*-
{
    'name': 'Quality Control Inspection',
    'author': 'OD19',
    'version': '19.0.1.0.0',
    'category': 'Inventory/Quality',
    'summary': 'QC inspections for incoming and outgoing products',
    'depends': ['stock', 'product'],
    'data': [
        'data/sequence.xml',
        'security/ir.model.access.csv',
        'views/qc_inspection_views.xml',
        'views/stock_picking_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
