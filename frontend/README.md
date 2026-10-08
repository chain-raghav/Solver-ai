# Solver AI – Frontend

Plain HTML/CSS/ES-modules (no build step).

Run backend (from project root): `uvicorn backend.main:app --port 8000`
Run frontend: `python -m http.server 3000 --directory frontend` → http://localhost:3000

Backend URL: `js/config.js` (default `http://localhost:8000/api`; override with `localStorage.solver_api_url`).
All API calls live in `js/services/api.js` and follow `contracts/api_contract.json`.
Student registration OTP is printed in the backend console (per contract).
