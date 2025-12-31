@echo off
echo Checking for processes on port 8000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000') do (
    echo Killing process %%a...
    taskkill /PID %%a /F
)
echo Port 8000 should now be free!
pause


