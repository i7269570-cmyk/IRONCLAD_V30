@echo off
echo [1/5] Pulling latest changes from remote...
git pull origin main

echo [2/5] Running structural integrity test...
pytest tests/test_structure.py
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Test failed! Please fix structure.
    pause
    exit /b
)

echo [3/5] Adding changes...
git add .

echo [4/5] Committing changes...
git commit -m "update: logic and structure"

echo [5/5] Pushing to remote...
git push origin main

echo [SUCCESS] Ironclad sync complete.
pause