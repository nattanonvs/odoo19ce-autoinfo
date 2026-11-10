# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

"""Safety guard for AI-driven ORM access.

Everything the AI asks for (model, domain, fields, order, aggregates) passes
through this module *before* it reaches the ORM, so a hallucinating model can
never query an uninstalled model, an unknown field, a forbidden operator or an
unbounded result set.
"""

from odoo.fields import Domain

#: Operators the AI is allowed to use inside a domain condition.
SAFE_OPERATORS = frozenset(
    {"=", "!=", ">", ">=", "<", "<=", "in", "not in", "like", "ilike", "child_of"}
)
#: Prefix logic operators accepted at the domain level.
LOGIC_OPERATORS = ("&", "|", "!")
#: Aggregate functions allowed in ``aggregate_records``.
AGGREGATE_FUNCTIONS = frozenset({"sum", "avg", "min", "max", "count"})
#: Date granularities allowed in ``groupby``.
GROUPBY_GRANULARITIES = frozenset({"day", "week", "month", "quarter", "year"})

MAX_LIMIT = 20
DEFAULT_LIMIT = 5
MAX_FIELDS = 60
MAX_AGGREGATES = 8
MAX_GROUPBY = 3


class OrmGuardError(ValueError):
    """Raised when an AI request would be unsafe; the message is user facing."""


def safe_limit(value, default=DEFAULT_LIMIT, cap=MAX_LIMIT):
    """Coerce ``value`` into ``1..cap`` (or ``default`` when unparsable)."""
    try:
        limit = int(value)
    except (TypeError, ValueError):
        return default
    return max(1, min(limit, cap))


def safe_offset(value):
    """Coerce ``value`` into a non-negative offset."""
    try:
        offset = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, offset)


def check_model(env, model_name):
    """Ensure the model exists and the current user may read it."""
    if not model_name or not isinstance(model_name, str) or model_name not in env:
        raise OrmGuardError("ไม่พบโมเดล %s" % (model_name or ""))
    if not env[model_name].has_access("read"):
        raise OrmGuardError("คุณไม่มีสิทธิ์อ่านข้อมูลโมเดล %s" % model_name)
    return model_name


def check_field(env, model_name, path, require_stored=True):
    """Validate a (possibly dotted) field path against ``model_name``."""
    if not isinstance(path, str) or not path.strip():
        raise OrmGuardError("ชื่อฟิลด์ไม่ถูกต้อง")
    current = model_name
    parts = path.strip().split(".")
    for index, part in enumerate(parts):
        if current not in env:
            raise OrmGuardError("ไม่พบโมเดล %s" % current)
        field = env[current]._fields.get(part)
        if field is None:
            raise OrmGuardError('ไม่พบฟิลด์ "%s" ในโมเดล %s' % (part, current))
        if require_stored and field.compute and not field.store:
            raise OrmGuardError('ฟิลด์ "%s" เป็นค่าคำนวณที่ใช้กรองไม่ได้' % part)
        if index < len(parts) - 1:
            comodel = getattr(field, "comodel_name", None)
            if not comodel or comodel not in env:
                raise OrmGuardError(
                    'ฟิลด์ "%s" ไม่ใช่ความสัมพันธ์ที่อ้างอิงต่อได้' % part
                )
            current = comodel
    return path


def validate_fields(env, model_name, fields_):
    """Validate the list of fields to read (existence only, no stored check)."""
    if fields_ in (None, False, ""):
        return ["display_name"]
    if not isinstance(fields_, (list, tuple)):
        raise OrmGuardError("รายการฟิลด์ไม่ถูกต้อง")
    result = []
    for name in list(fields_)[:MAX_FIELDS]:
        check_field(env, model_name, name, require_stored=False)
        result.append(name)
    return result or ["display_name"]


def validate_order(env, model_name, order):
    """Validate an ``order`` clause (``"field asc, other desc"``)."""
    if order in (None, False, ""):
        return None
    if not isinstance(order, str):
        raise OrmGuardError("ลำดับการเรียงไม่ถูกต้อง")
    cleaned = []
    for token in order.replace(",", " ").split():
        if token.lower() in ("asc", "desc", "nulls", "first", "last"):
            cleaned.append(token)
            continue
        check_field(env, model_name, token)
        cleaned.append(token)
    return " ".join(cleaned) or None


def validate_groupby(env, model_name, groupby):
    """Validate a ``groupby`` list (``["state", "date:month"]``)."""
    if groupby in (None, False, ""):
        return []
    if not isinstance(groupby, (list, tuple)):
        raise OrmGuardError("รายการจัดกลุ่มไม่ถูกต้อง")
    result = []
    for item in list(groupby)[:MAX_GROUPBY]:
        if not isinstance(item, str):
            raise OrmGuardError("รายการจัดกลุ่มไม่ถูกต้อง")
        parts = item.split(":")
        if len(parts) > 2:
            raise OrmGuardError('รูปแบบการจัดกลุ่ม "%s" ไม่ถูกต้อง' % item)
        if len(parts) == 2 and parts[1] not in GROUPBY_GRANULARITIES:
            raise OrmGuardError('ความละเอียด "%s" ไม่ได้รับอนุญาต' % parts[1])
        check_field(env, model_name, parts[0])
        result.append(item)
    return result


def validate_aggregates(env, model_name, aggregates):
    """Validate an ``aggregates`` list (``["amount_total:sum", "__count"]``)."""
    if not isinstance(aggregates, (list, tuple)) or not aggregates:
        raise OrmGuardError("ต้องระบุฟิลด์สรุปอย่างน้อยหนึ่งรายการ")
    result = []
    for expr in list(aggregates)[:MAX_AGGREGATES]:
        if not isinstance(expr, str):
            raise OrmGuardError("รายการสรุปไม่ถูกต้อง")
        if expr == "__count":
            result.append(expr)
            continue
        parts = expr.split(":")
        if len(parts) != 2:
            raise OrmGuardError('รูปแบบการสรุป "%s" ไม่ถูกต้อง' % expr)
        _field_name, func = parts
        if func not in AGGREGATE_FUNCTIONS:
            raise OrmGuardError('ฟังก์ชันสรุป "%s" ไม่ได้รับอนุญาต' % func)
        check_field(env, model_name, parts[0])
        result.append(expr)
    return result


def validate_domain(env, model_name, domain):
    """Return a safe :class:`~odoo.fields.Domain` or raise :class:`OrmGuardError`.

    Callers must pass a legacy token list/tuple (or an empty value). A Domain
    instance is rejected on purpose so no request can bypass field/operator
    validation.
    """
    if isinstance(domain, (list, tuple)):
        if not domain:
            return Domain.TRUE
        return Domain(_parse_tokens(env, model_name, list(domain)))
    if domain is None or domain is False or domain == "":
        return Domain.TRUE
    raise OrmGuardError("โดเมนการค้นหาไม่ถูกต้อง")


def _parse_tokens(env, model_name, tokens):
    """Recursively validate legacy domain tokens (nested groups become Domain)."""
    result = []
    for token in tokens:
        if isinstance(token, str):
            if token not in LOGIC_OPERATORS:
                raise OrmGuardError('ตัวดำเนินการ "%s" ไม่ได้รับอนุญาต' % token)
            result.append(token)
        elif isinstance(token, (list, tuple)):
            is_leaf = (
                len(token) == 3
                and isinstance(token[0], str)
                and token[0] not in LOGIC_OPERATORS
            )
            if is_leaf:
                field_name, operator, value = token
                if not isinstance(operator, str) or operator not in SAFE_OPERATORS:
                    raise OrmGuardError(
                        'ตัวดำเนินการ "%s" ไม่ได้รับอนุญาต' % (operator,)
                    )
                if operator in ("in", "not in") and not isinstance(
                    value, (list, tuple)
                ):
                    raise OrmGuardError(
                        'ตัวดำเนินการ "%s" ต้องมีค่าเป็นรายการ' % operator
                    )
                check_field(env, model_name, field_name)
                result.append((field_name, operator, value))
            else:
                result.append(
                    Domain(_parse_tokens(env, model_name, list(token)))
                )
        else:
            raise OrmGuardError("โดเมนการค้นหาไม่ถูกต้อง")
    return result
