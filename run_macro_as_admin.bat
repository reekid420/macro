@echo off
powershell -Command "Start-Process .\venv\Scripts\python.exe -ArgumentList './macro_app.py' -Verb RunAs"
