@echo off
echo Stopping existing Odoo 19 service on port 8070...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr /r /c:":8070 .*LISTENING"') do taskkill /f /pid %%a >nul 2>&1
ping -n 3 127.0.0.1 >nul
echo Starting Odoo 19 Server...
cd /d C:\odoo-dev\odoo19
call venv19\Scripts\activate.bat
python odoo-bin -c odoo.conf
pause
