# -*- coding: utf-8 -*-
"""Database connection used by JasperStarter to query the Odoo database.

The legacy implementation created a dedicated ``SUPERUSER`` PostgreSQL role on
the fly through a ``DO`` block.  That is no longer acceptable (nor possible:
the Odoo database user has no ``CREATEROLE`` privilege), so the connection is
configured explicitly here instead.

Default values are read from ``odoo.conf``, which means a working setup out of
the box.  For a hardened deployment the administrator can point the connection
at a dedicated read-only role; the exact SQL to create it is rendered in the
``setup_sql`` field.
"""
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError


class JasperDb(models.Model):
    _name = "od19.jasper.db"
    _description = "Jasper Reports - Database Connection"
    _rec_name = "username"

    name = fields.Char(
        string="Name",
        required=True,
        default="Jasper Database Connection",
    )
    active = fields.Boolean(default=True)
    driver = fields.Selection(
        [("postgres", "PostgreSQL")],
        string="Driver",
        required=True,
        default="postgres",
    )
    host = fields.Char(
        string="Host",
        required=True,
        default=lambda self: self._default_config("db_host", "localhost"),
    )
    port = fields.Integer(
        string="Port",
        required=True,
        default=lambda self: int(self._default_config("db_port", 5432) or 5432),
    )
    database = fields.Char(
        string="Database",
        required=True,
        default=lambda self: self.env.cr.dbname,
    )
    username = fields.Char(
        string="User",
        required=True,
        default=lambda self: self._default_config("db_user", "odoo"),
    )
    password = fields.Char(
        string="Password",
        required=True,
        default=lambda self: self._default_config("db_password", ""),
    )
    jdbc_dir = fields.Char(
        string="JDBC Driver Directory",
        help="Directory holding the JDBC driver jars. Leave empty to use the "
        "driver bundled with the module.",
    )
    setup_sql = fields.Text(
        string="Role Creation Script",
        compute="_compute_setup_sql",
        help="Run this once, as a PostgreSQL superuser, to create a dedicated "
        "read-only role for JasperReports.",
    )

    # ---------------------------------------------------------------- config
    @api.model
    def _default_config(self, key, default=None):
        return tools.config.get(key) or default

    @api.model
    def _get_connection_record(self):
        """Return the single active connection, or raise a helpful error."""
        record = self.search([("active", "=", True)], limit=1)
        if not record:
            raise UserError(
                _(
                    "No active Jasper database connection is configured.\n"
                    "Go to Accounting > Configuration > Reports > Jasper "
                    "Database Connection and create one."
                )
            )
        return record

    @api.depends("username", "password", "database")
    def _compute_setup_sql(self):
        for record in self:
            database = record.database or self.env.cr.dbname
            record.setup_sql = (
                "-- Run once as a PostgreSQL superuser (e.g. the 'postgres'\n"
                "-- operating-system account).\n"
                "CREATE ROLE %(user)s LOGIN PASSWORD '%(password)s';\n"
                'GRANT CONNECT ON DATABASE "%(database)s" TO %(user)s;\n'
                "GRANT pg_read_all_data TO %(user)s;\n"
            ) % {
                "user": record.username or "jasper_report",
                "password": record.password or "",
                "database": database,
            }

    # ------------------------------------------------------------ connection
    def get_db_connection(self):
        """Connection dictionary consumed by
        :meth:`od19_reporting_jasper.jasperpy.JasperPy.process`.
        """
        self.ensure_one()
        return {
            "driver": self.driver or "postgres",
            "username": self.username,
            "password": self.password,
            "host": self.host or "localhost",
            "database": self.database or self.env.cr.dbname,
            "port": self.port or 5432,
            "jdbc_dir": self.jdbc_dir or None,
        }

    @api.model
    def get_connection_dict(self):
        """Convenience wrapper used by the report engine."""
        return self._get_connection_record().get_db_connection()
