ROLE_FIELD_BY_KIND = {
    "commercial_customer": "od19_is_commercial_customer",
    "project_owner": "od19_is_project_owner",
    "contractor": "od19_is_contractor",
}


def _has_sales_role_sources(env):
    return "sale.order" in env.registry and "project.project" in env.registry


def _collect_sales_partner_role_ids(env):
    project_model = env["project.project"].sudo()
    sale_order_model = env["sale.order"].sudo()

    return {
        "commercial_customer": set(sale_order_model.search([]).mapped("partner_id").ids),
        "project_owner": set(
            project_model.search([]).mapped("project_owner_id").ids
            + sale_order_model.search([]).mapped("od19_project_owner_id").ids
        ),
        "contractor": set(project_model.search([]).mapped("contractor_ids").ids),
    }


def _backfill_partner_flag(env, role_field, partner_ids, companies_only=False):
    if not partner_ids:
        return

    company_clause = " AND is_company = TRUE" if companies_only else ""
    env.cr.execute(
        f"""
        UPDATE res_partner
           SET {role_field} = TRUE
         WHERE id IN %s
           AND COALESCE({role_field}, FALSE) = FALSE
           {company_clause}
        """,
        [tuple(partner_ids)],
    )


def backfill_sales_partner_roles(env):
    if not _has_sales_role_sources(env):
        return

    role_ids = _collect_sales_partner_role_ids(env)

    for role_kind, role_field in ROLE_FIELD_BY_KIND.items():
        # Legacy sales references may still point at person contacts, but
        # owner/contractor semantics stay company-only.
        _backfill_partner_flag(
            env,
            role_field,
            role_ids[role_kind],
            companies_only=role_kind in {"project_owner", "contractor"},
        )

    env["res.partner"].invalidate_model(list(ROLE_FIELD_BY_KIND.values()))


def post_init_hook(env):
    backfill_sales_partner_roles(env)
