@echo off
echo Installing frontend dependencies...
cd /d c:\Users\surya\Session-20-Capstone-Project\frontend
call npm install

echo.
echo Installing backend dependencies...
cd /d c:\Users\surya\Session-20-Capstone-Project\backend
python -m venv venv
call venv\Scripts\activate.bat
pip install -r requirements.txt

echo.
echo Installation complete!
