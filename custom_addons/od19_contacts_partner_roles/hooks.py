ROLE_FIELD_BY_KIND = {
    "commercial_customer": "od19_is_commercial_customer",
    "project_owner": "od19_is_project_owner",
    "contractor": "od19_is_contractor",
}


def _has_sales_role_sources(env):
    return "sale.order" in env.registry and "od19.sales.project" in env.registry


def _collect_sales_partner_role_ids(env):
    project_model = env["od19.sales.project"].sudo()
    sale_order_model = env["sale.order"].sudo()

    return {
        "commercial_customer": set(sale_order_model.search([]).mapped("partner_id").ids),
        "project_owner": set(
            project_model.search([]).mapped("project_owner_id").ids
            + sale_order_model.search([]).mapped("od19_project_owner_id").ids
        ),
        "contractor": set(project_model.search([]).mapped("contractor_ids").ids),
    }


def _backfill_partner_flag(env, role_field, partner_ids):
    if not partner_ids:
        return

    env.cr.execute(
        f"""
        UPDATE res_partner
           SET {role_field} = TRUE
         WHERE id IN %s
           AND COALESCE({role_field}, FALSE) = FALSE
        """,
        [tuple(partner_ids)],
    )


def backfill_sales_partner_roles(env):
    if not _has_sales_role_sources(env):
        return

    role_ids = _collect_sales_partner_role_ids(env)

    for role_kind, role_field in ROLE_FIELD_BY_KIND.items():
        _backfill_partner_flag(env, role_field, role_ids[role_kind])

    env["res.partner"].invalidate_model(list(ROLE_FIELD_BY_KIND.values()))


def post_init_hook(env):
    backfill_sales_partner_roles(env)
