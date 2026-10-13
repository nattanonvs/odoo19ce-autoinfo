import odoo
import sys

odoo.tools.config.parse_config(['-d', 'odoo19', '--stop-after-init', '--log-level=error'])
odoo.cli.server.report_configuration()
odoo.service.server.start(preload=[], stop=True)

from odoo.api import Environment
from odoo.modules.registry import Registry

registry = Registry('odoo19')
with registry.cursor() as cr:
    env = Environment(cr, odoo.SUPERUSER_ID, {})

    # Find or create a department with PR sequence
    dept = env['hr.department'].search([], limit=1)
    if not dept:
        dept = env['hr.department'].create({'name': 'Test Dept'})

    # Assign PRI sequence to department
    pri_seq = env.ref('od19_purchase_document_sequence.sequence_purchase_request_pri')
    dept.write({'pr_sequence_id': pri_seq.id})

    # Create a purchase request
    pr = env['purchase.request'].create({
        'department_id': dept.id,
        'requested_by': env.user.id,
        'line_ids': [(0, 0, {
            'product_id': env['product.product'].search([], limit=1).id or env['product.product'].create({'name': 'Test', 'type': 'consu'}).id,
            'product_qty': 1.0,
        })],
    })
    print(f"PR name: {pr.name}")
    assert pr.name.startswith('PRI'), f"Expected PRI prefix, got {pr.name}"

    # Assign PB sequence to department for PO
    pb_seq = env.ref('od19_purchase_document_sequence.sequence_purchase_order_pb')
    dept.write({'po_sequence_id': pb_seq.id})

    # Create a purchase order
    partner = env['res.partner'].search([], limit=1) or env['res.partner'].create({'name': 'Test Vendor'})
    po = env['purchase.order'].create({
        'department_id': dept.id,
        'partner_id': partner.id,
        'order_line': [(0, 0, {
            'product_id': env['product.product'].search([], limit=1).id,
            'product_qty': 1.0,
            'price_unit': 100.0,
        })],
    })
    print(f"PO name: {po.name}")
    assert po.name.startswith('PB'), f"Expected PB prefix, got {po.name}"

    print("\n=== ALL TESTS PASSED ===")
    print(f"PR with department + PRI sequence -> {pr.name}")
    print(f"PO with department + PB sequence -> {po.name}")
