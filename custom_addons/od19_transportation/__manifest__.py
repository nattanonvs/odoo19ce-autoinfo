# -*- coding: utf-8 -*-
{
    'name': 'Transportation Management',
    'author': 'OD19',
    'version': '19.0.1.0.0',
    'category': 'Inventory/Delivery',
    'summary': 'Transportation management: vehicle, driver, routes, delivery tracking',
    'depends': ['stock', 'delivery', 'fleet'],
    'data': [
        'security/ir.model.access.csv',
        'views/transportation_views.xml',
        'views/stock_picking_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
