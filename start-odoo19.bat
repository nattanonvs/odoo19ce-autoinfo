@echo off
echo Starting Odoo 19 Server...
cd /d C:\odoo-dev\odoo19
call venv19\Scripts\activate.bat
python odoo-bin -c odoo.conf
pause
