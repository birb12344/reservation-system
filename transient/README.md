# Transient Room Reservation System

A simple Flask + SQLite + Bootstrap reservation system for a small transient
house. Replaces manual logbooks with an online booking experience.

## Features
- Guest registration / login / profile
- Browse rooms, view capacity & price
- Online booking with **double-booking prevention**
- Admin dashboard (stats + recent bookings)
- Room CRUD (add / edit / delete / status)
- Reservation status management (pending, confirmed, cancelled, checked_in, checked_out)
- Payment recording (GCash / PayPal / Cash)
- Reports: occupancy, reservation list, revenue summary
- Secure password hashing (Werkzeug)
- Sample data pre-loaded

## Default credentials
- **Admin** — username: `admin` / password: `admin123`
- **Demo guest** — email: `guest@example.com` / password: `guest123`

> Change these in production!

---

## 1. Run locally

```bash
# 1. Clone or unzip the project
cd reservation-system

# 2. (Recommended) create a virtual environment
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the app
python app.py
```

Open <http://127.0.0.1:5000> in your browser.

The SQLite database (`database.db`) and sample data are created automatically
on first run.

---

## 2. Folder structure

```
reservation-system/
├── app.py                 # Flask backend (all routes + DB init)
├── database.db            # Auto-generated on first run
├── requirements.txt
├── Procfile               # For Render / Railway / Heroku
├── runtime.txt            # Python version pin
├── README.md
├── static/
│   └── style.css
└── templates/
    ├── base.html
    ├── index.html
    ├── rooms.html
    ├── booking.html
    ├── login.html
    ├── register.html
    ├── profile.html
    ├── admin_login.html
    ├── admin_dashboard.html
    ├── manage_rooms.html
    ├── manage_reservations.html
    ├── payments.html
    └── reports.html
```

---

## 3. Deploy online

### Option A — Render (recommended, free tier)

1. Push the project to a **GitHub** repository.
2. Go to <https://render.com> → **New → Web Service** → connect your repo.
3. Settings:
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - Add an environment variable: `SECRET_KEY` = any long random string.
4. Click **Deploy**. After ~2 minutes you'll get a public URL like
   `https://your-app.onrender.com` to share with your professor.

> ⚠️ Render's free tier uses an ephemeral filesystem — `database.db`
> resets when the instance restarts. For a graded demo that's usually fine.
> For persistent data, attach a Render disk or migrate to PostgreSQL.

### Option B — Railway

1. Push to GitHub → go to <https://railway.app> → **New Project → Deploy from GitHub**.
2. Railway auto-detects Python and uses the `Procfile`.
3. Add `SECRET_KEY` as a variable. Done.

### Option C — PythonAnywhere

1. Upload the folder, create a new **Flask** web app pointing to `app.py`.
2. Install requirements in a Bash console: `pip install --user -r requirements.txt`.

---

## 4. Database tables

| Table        | Purpose                                  |
|--------------|------------------------------------------|
| users        | Registered guests                        |
| admin        | Admin credentials                        |
| rooms        | Room catalog (status: available/maintenance) |
| reservations | Bookings (pending/confirmed/cancelled/checked_in/checked_out) |
| payments     | Payment records (gcash/paypal/cash)      |

---

## 5. Notes

- Double booking is prevented by checking date overlap with existing
  pending/confirmed/checked_in reservations for the same room.
- All passwords stored using `werkzeug.security.generate_password_hash`.
- Designed for non-technical users: large buttons, clear navigation,
  Bootstrap 5 UI, helpful flash messages.

Capstone-ready. Good luck! 🎓
