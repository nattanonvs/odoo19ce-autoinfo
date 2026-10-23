# -*- coding: utf-8 -*-
"""Thin Python wrapper around the bundled JasperStarter (JasperReports 6.10).

Ported from the Odoo 15 ``dtr_jasper`` integration.  Differences vs. legacy:

* Invokes the Java runtime directly against the bundled ``lib/`` classpath
  instead of the Launch4j ``jasperstarter.exe`` wrapper, which does not resolve
  the jar manifest classpath reliably on Windows.
* Uses an argument list (no shell quoting), so it behaves the same on Windows
  and Linux.
* Resolves the Java runtime from ``JAVA_HOME`` / ``PATH`` / common Windows
  locations instead of shipping a per-OS JRE inside the module.
* Raises :class:`JasperPyError` with the captured stderr so callers can surface
  an actionable ``UserError`` instead of a raw traceback.
"""
import logging
import os
import shutil
import subprocess

_logger = logging.getLogger(__name__)

# Entry point declared in ``lib/jasperstarter.jar``'s manifest.
MAIN_CLASS = "de.cenote.jasperstarter.App"

# JVM heap ceiling; keeps a print job from starving the Odoo worker.
JVM_OPTIONS = ("-Xmx512m", "-XX:MaxMetaspaceSize=256m")

FORMATS = (
    "pdf",
    "rtf",
    "xls",
    "xlsx",
    "docx",
    "odt",
    "ods",
    "pptx",
    "csv",
    "html",
    "xhtml",
    "xml",
    "jrprint",
)

# Windows locations probed when JAVA_HOME / PATH do not resolve a JDK.
_WINDOWS_JAVA_ROOTS = (
    r"C:\Program Files\Java",
    r"C:\Program Files (x86)\Java",
    r"C:\Program Files\Eclipse Adoptium",
    r"C:\Program Files\Microsoft",
)


class JasperPyError(Exception):
    """Raised when JasperStarter fails or cannot be located."""


def _java_bin_from_home(java_home):
    if not java_home:
        return None
    exe = "java.exe" if os.name == "nt" else "java"
    candidate = os.path.join(java_home, "bin", exe)
    return candidate if os.path.isfile(candidate) else None


def find_java_bin():
    """Best-effort lookup of the ``java`` executable.

    Returns the full path to ``java``/``java.exe`` or ``None``.
    """
    # 1. JAVA_HOME
    java = _java_bin_from_home(os.environ.get("JAVA_HOME"))
    if java:
        return java

    # 2. PATH
    java = shutil.which("java")
    if java:
        return java

    # 3. Well-known Windows install roots (jre1.8.0_*, jdk*)
    if os.name == "nt":
        for root in _WINDOWS_JAVA_ROOTS:
            if not os.path.isdir(root):
                continue
            for entry in sorted(os.listdir(root), reverse=True):
                java = _java_bin_from_home(os.path.join(root, entry))
                if java:
                    return java
            java = _java_bin_from_home(os.path.join(root, "latest"))
            if java:
                return java
    return None


class JasperPy:
    """Runs the bundled JasperStarter through the local Java runtime."""

    def __init__(self, module_path=None, resource_dir=None, java_bin=None):
        module_path = module_path or os.path.dirname(os.path.abspath(__file__))
        self.base_dir = os.path.join(module_path, "jasperstarter")
        self.lib_dir = os.path.join(self.base_dir, "lib")
        self.jdbc_dir = os.path.join(self.base_dir, "jdbc")
        self.resource_directory = resource_dir or self.lib_dir
        self.java_bin = java_bin or find_java_bin()
        self._command = []

    # ------------------------------------------------------------------ utils
    def _classpath(self):
        if not os.path.isdir(self.lib_dir):
            raise JasperPyError("JasperStarter lib not found at %s" % self.lib_dir)
        return os.path.join(self.lib_dir, "*")

    def _env(self):
        env = os.environ.copy()
        if self.java_bin:
            java_home = os.path.dirname(os.path.dirname(self.java_bin))
            env["JAVA_HOME"] = java_home
            env["JRE_HOME"] = java_home
            env["PATH"] = os.path.dirname(self.java_bin) + os.pathsep + env.get("PATH", "")
        return env

    def _run(self, args):
        if not self.java_bin:
            raise JasperPyError(
                "Java runtime not found. Install a JRE/JDK 8+ or set JAVA_HOME."
            )
        command = (
            [self.java_bin]
            + list(JVM_OPTIONS)
            + ["-cp", self._classpath(), MAIN_CLASS]
            + list(args)
        )
        self._command = command
        _logger.info("JasperStarter: %s", " ".join(command))
        try:
            proc = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=self._env(),
                timeout=300,
            )
        except subprocess.TimeoutExpired:
            raise JasperPyError("JasperStarter timed out after 300s.")
        except OSError as err:
            raise JasperPyError("Failed to launch Java: %s" % err)
        if proc.returncode != 0:
            tail = (proc.stderr or proc.stdout or "").strip()[-1500:]
            raise JasperPyError(
                "JasperStarter exited with code %s\n%s" % (proc.returncode, tail)
            )
        return proc.returncode

    # -------------------------------------------------------------- commands
    def compile(self, input_file, output_file=None):
        if not input_file:
            raise JasperPyError("No input file supplied to compile().")
        if not os.path.isfile(input_file):
            raise JasperPyError("Input file not found: %s" % input_file)
        args = ["compile", input_file]
        if output_file:
            # JasperStarter appends a ".jasper" extension to whatever value is
            # given to -o, so the extension must be stripped to obtain the
            # expected file name (invoice_form.jasper, not invoice_form.jasper.jasper).
            if output_file.lower().endswith(".jasper"):
                output_file = output_file[: -len(".jasper")]
            args += ["-o", output_file]
        return self._run(args)

    def process(
        self,
        input_file,
        output_file=None,
        format_list=None,
        parameters=None,
        db_connection=None,
        locale="th_TH",
        resource="",
    ):
        format_list = format_list or ["pdf"]
        parameters = parameters or {}
        db_connection = db_connection or {}

        if not input_file:
            raise JasperPyError("No input file supplied to process().")
        if not os.path.isfile(input_file):
            raise JasperPyError("Input file not found: %s" % input_file)
        invalid = [f for f in format_list if f not in FORMATS]
        if invalid:
            raise JasperPyError("Invalid format(s): %s" % ", ".join(invalid))

        args = ["--locale", locale, "process", input_file]
        if output_file:
            args += ["-o", output_file]
        args += ["-f"] + list(format_list)

        if parameters:
            # JasperStarter's CLI takes every ``key=value`` pair after a single
            # -P.  Repeating -P makes it keep only the last occurrence, which
            # silently drops the ids filter and renders an empty report.
            args.append("-P")
            args += ["%s=%s" % (key, value) for key, value in parameters.items()]

        if db_connection:
            args += ["-t", db_connection.get("driver") or "postgres"]
            if db_connection.get("username"):
                args += ["-u", db_connection["username"]]
            if db_connection.get("password"):
                args += ["-p", db_connection["password"]]
            if db_connection.get("host"):
                args += ["-H", db_connection["host"]]
            if db_connection.get("database"):
                args += ["-n", db_connection["database"]]
            if db_connection.get("port"):
                args += ["--db-port", str(db_connection["port"])]
            args += ["--jdbc-dir", db_connection.get("jdbc_dir") or self.jdbc_dir]

        if resource:
            args += ["-r", resource]

        return self._run(args)

    @property
    def command(self):
        return self._command
