@echo off
echo Starting DataMind AI Platform...

:: Start backend
cd backend
start "DataMind Backend" cmd /k "pip install -r requirements.txt && set PYTHONPATH=. && uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload"
cd ..

:: Wait 5 seconds for backend
timeout /t 5 /nobreak

:: Start frontend
cd frontend
start "DataMind Frontend" cmd /k "npm install && npm run dev"
cd ..

echo.
echo DataMind AI is starting...
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:3000
echo.
pause
