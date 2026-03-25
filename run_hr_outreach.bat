@echo off
cd /d "E:\PROJECTS\Mission Job\job_pipeline"
"C:\Users\hursh\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\python.exe" main.py --excel-hr --limit 50 >> logs\scheduler.log 2>&1
