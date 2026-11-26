import os
import py_compile
import sys
import xml.etree.ElementTree as ET

roots = [
    r"C:\odoo-dev\od19_sc\custom_addons\od19_sc_core",
    r"C:\odoo-dev\od19_sc\custom_addons\od19_sc_designer",
    r"C:\odoo-dev\od19_sc\custom_addons\od19_sc_ta",
]
errors = []
for root in roots:
    for dirpath, dirnames, filenames in os.walk(root):
        for fn in filenames:
            path = os.path.join(dirpath, fn)
            if fn.endswith(".py"):
                try:
                    with open(path, "rb") as fh:
                        source = fh.read()
                    compile(source, path, "exec")
                except SyntaxError as e:
                    errors.append("PY: %s\n%s" % (path, e))
            elif fn.endswith(".xml"):
                try:
                    ET.parse(path)
                except ET.ParseError as e:
                    errors.append("XML: %s\n%s" % (path, e))

if errors:
    print("ERRORS FOUND:")
    for e in errors:
        print(e)
    sys.exit(1)
print("OK: all .py compiled and all .xml parsed")
