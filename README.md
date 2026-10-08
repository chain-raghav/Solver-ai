# Solver AI
College complaint management system. Students register complaints, ML models categorise them, and admins track and update their status.

## Run
1. pip install -r requirements.txt
2. Copy .env.example to .env and fill in your values (needs PostgreSQL)
3. Create the database: CREATE DATABASE solver_ai;
4. python -m backend.seed_data
5. python -m uvicorn backend.main:app --port 8000
6. python -m http.server 3000 --directory frontend
7. Open http://localhost:3000