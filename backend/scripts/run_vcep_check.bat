@echo off
cd /d C:\Users\Salman\genomics-project\genomics-dashboard\backend
call .venv\Scripts\activate
python scripts\check_vcep_updates.py >> logs\vcep_check.log 2>&1
