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


---

## Folder structure

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


##  Database tables

| Table        | Purpose                                  |
|--------------|------------------------------------------|
| users        | Registered guests                        |
| admin        | Admin credentials                        |
| rooms        | Room catalog (status: available/maintenance) |
| reservations | Bookings (pending/confirmed/cancelled/checked_in/checked_out) |
| payments     | Payment records (gcash/paypal/cash)      |

---


