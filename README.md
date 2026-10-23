# Solver AI

A college complaint management system that sorts itself. A student describes a problem in one text box. ML models on the backend predict its **category** and **urgency**, and admins track and update it on a single dashboard.

> Built as a short student project (a few hours of focused work). The ML models are a prototype, see [Limitations](#limitations).

## How it works

1. Student signs up with a college email, verifies it with an emailed OTP, and logs in.
2. Student types a complaint (description required, location optional).
3. The backend runs four ML models on the text.
4. The complaint and its predictions are saved in PostgreSQL.
5. Admin sees all complaints (urgent ones flagged), opens one and updates its status.
6. Student sees the new status under **My Complaints**.

## The ML part

Input is only the complaint text. Four small scikit-learn models run in sequence:

| Model | Predicts | Method |
|---|---|---|
| Category classifier | Hostel, Academic, Infrastructure, Mess, Harassment, Other | TF-IDF + calibrated Linear SVM |
| Duration extractor | Not specified, Less than a day, 1-3 days, 4-7 days, More than a week | TF-IDF + calibrated Linear SVM |
| Affected-count extractor | Individual, Small group, Large group | TF-IDF + calibrated Linear SVM |
| Urgency classifier | Low, Medium, High | TF-IDF + one-hot (category, duration, group size) + Logistic Regression |

- **TF-IDF** (1-2 word n-grams, sublinear TF) turns text into weighted features.
- **Calibration** (`CalibratedClassifierCV`) turns SVM scores into probabilities, used as confidence values.
- The urgency model uses the first three predictions as extra input, so it weighs context and not just words.
- Models are saved as `.joblib` files and loaded once on first use. If a model fails, the backend falls back to category `Other` (confidence 0.5) so no complaint is lost.

Code: `backend/models/Solver_AI_ML_BACKEND/` (`ml_pipeline.py` runs the chain, `train_models.py` retrains).

## Tech stack

- **Backend:** FastAPI (Python), SQLAlchemy, PostgreSQL, JWT auth, argon2 password hashing, email OTP via Brevo
- **ML:** scikit-learn, pandas, joblib
- **Frontend:** plain HTML, CSS and JavaScript (no build step)
- **Hosting:** Render (backend), Vercel (frontend), Neon (database)

## Project structure

```
backend/
  main.py                  FastAPI app
  routes/                  auth, student, complaints, admin
  schemas/                 request/response models
  security/                JWT and auth dependencies
  services/                ai_service.py (ML wrapper), email_service.py (OTP email)
  database/                engine and tables
  models/Solver_AI_ML_BACKEND/   ML code and .joblib models
  seed_data.py             creates tables, a demo admin and a demo student
contracts/api_contract.json      source of truth for frontend-backend API
frontend/
  index.html
  css/style.css
  js/config.js             backend URL and allowed statuses
  js/services/api.js       every backend call lives here
  js/app.js                all pages and routing
```

## Run locally

Requires Python 3.13 and PostgreSQL.

```bash
pip install -r requirements.txt
```

Create the database (`CREATE DATABASE solver_ai;`), then copy `.env.example` to `.env` and fill it in:

```
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/solver_ai
JWT_SECRET_KEY=a_long_random_string
BREVO_API_KEY=your_brevo_api_key
BREVO_SENDER_EMAIL=your_verified_sender@gmail.com
```

Generate a strong secret with `python -c "import secrets; print(secrets.token_hex(32))"`.

```bash
python -m backend.seed_data                                   # tables + demo accounts
python -m uvicorn backend.main:app --port 8000                # backend
python -m http.server 3000 --directory frontend               # frontend
```

Open `http://localhost:3000`. To point the frontend at a local backend, run this in the browser console:
`localStorage.setItem("solver_api_url", "http://localhost:8000/api")`.

If Brevo isn't configured, the OTP is printed in the backend terminal instead of being emailed.

`seed_data.py` creates demo accounts for testing. Change those passwords before any real use.

## API

All endpoints are under `/api` and are listed in `contracts/api_contract.json`.

- Auth: `POST /auth/register`, `/auth/verify-otp`, `/auth/create-account`, `/auth/login`, `/auth/admin/login`
- Student: `GET/PUT /student/profile`, `GET /student/dashboard/metrics`
- Complaints: `POST /complaints`, `GET /complaints`, `GET /complaints/{id}`
- Admin: `GET /admin/dashboard`, `GET /admin/complaints`, `GET /admin/complaints/{id}`, `PATCH /admin/complaints/{id}/status`

Statuses: Pending, Submitted, Under Review, In Progress, Resolved, Rejected, Closed.

## Deployment

- **Database:** Neon (run `seed_data` once against its connection string)
- **Backend:** Render web service. Build: `pip install -r requirements.txt`. Start: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`. Set `PYTHON_VERSION=3.13.5` and the `.env` values as environment variables.
- **Frontend:** Vercel, root directory `frontend`, framework preset "Other". Set the backend URL in `frontend/js/config.js`.

The free Render plan sleeps when idle, so the first request after a break can take up to a minute.

## Limitations

- The training script (`train_models.py`) generates synthetic template complaints. Cross-validation scores on such data will look better than real-world accuracy.
- Urgency labels in that script come from a hand-written scoring rule, so the urgency model largely learns that rule.
- Category predictions can be wrong, and admins can't yet correct them.
- CORS is open to all origins and login has no rate limiting. Fine for a demo, not for production.

## Future work

- Train on real, admin-labelled complaints
- Let admins correct predicted categories
- Use low confidence to flag complaints for manual review
- Route complaints to departments, send status notifications, detect duplicates

