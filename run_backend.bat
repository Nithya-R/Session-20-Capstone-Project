@echo off
cd c:\Users\surya\Session-20-Capstone-Project\backend
python -m venv venv
call venv\Scripts\activate.bat
pip install -r requirements.txt
powershell -ExecutionPolicy Bypass -File .\start.ps1
