# -*- coding: utf-8 -*-
"""Post-install: apply Template 01 (TA) ให้กลายเป็นของจริงทันทีหลังติดตั้ง."""
import logging

_logger = logging.getLogger(__name__)

TEMPLATE_XMLID = "od19_sc_ta.template_ta_01"


def post_init_hook(env):
    """Apply the TA template once, right after the module data is loaded.

    Idempotent: ``od19.sc.template.action_apply`` stores a revision first and
    reuses the already materialized records on subsequent calls.
    """
    template = env.ref(TEMPLATE_XMLID, raise_if_not_found=False)
    if not template:
        _logger.warning("od19_sc_ta: template %s not found; skip auto-apply.", TEMPLATE_XMLID)
        return
    template.action_apply()
    _logger.info("od19_sc_ta: applied template '%s' (%s).", template.name, template.code)
