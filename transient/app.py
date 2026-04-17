"""
Transient Room Reservation System
Flask + SQLite + Bootstrap

Run locally:
    pip install -r requirements.txt
    python app.py
Then open: http://127.0.0.1:5000
"""

import os
import sqlite3
from datetime import datetime, date
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, g, send_file
)
from werkzeug.security import generate_password_hash, check_password_hash

# ------------------------------------------------------------------
# App configuration
# ------------------------------------------------------------------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-in-production")


# ------------------------------------------------------------------
# Database helpers
# ------------------------------------------------------------------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Create tables and insert sample data if database is empty."""
    first_time = not os.path.exists(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        phone TEXT,
        password_hash TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS admin (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS rooms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        capacity INTEGER NOT NULL,
        price_per_night REAL NOT NULL,
        status TEXT NOT NULL DEFAULT 'available'  -- available | maintenance
    );

    CREATE TABLE IF NOT EXISTS reservations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        room_id INTEGER NOT NULL,
        check_in TEXT NOT NULL,
        check_out TEXT NOT NULL,
        total_amount REAL NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (room_id) REFERENCES rooms(id)
    );

    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reservation_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        method TEXT NOT NULL,            -- gcash | paypal | cash
        status TEXT NOT NULL DEFAULT 'pending',  -- pending | paid | failed | refunded
        transaction_ref TEXT,
        paid_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (reservation_id) REFERENCES reservations(id)
    );
    """)

    # Seed admin
    cur.execute("SELECT COUNT(*) AS c FROM admin")
    if cur.fetchone()["c"] == 0:
        cur.execute(
            "INSERT INTO admin (username, password_hash) VALUES (?, ?)",
            ("admin", generate_password_hash("admin123")),
        )

    # Seed sample rooms
    cur.execute("SELECT COUNT(*) AS c FROM rooms")
    if cur.fetchone()["c"] == 0:
        sample_rooms = [
            ("Deluxe Room A", "Cozy room with queen bed and AC.", 2, 1200.00, "available"),
            ("Family Room B", "Spacious room good for small families.", 4, 1800.00, "available"),
            ("Standard Room C", "Affordable room with fan and private bath.", 2, 800.00, "available"),
            ("Suite D",        "Premium suite with city view.",            3, 2500.00, "available"),
            ("Room E",         "Currently under maintenance.",             2, 900.00,  "maintenance"),
        ]
        cur.executemany(
            "INSERT INTO rooms (name, description, capacity, price_per_night, status) VALUES (?,?,?,?,?)",
            sample_rooms,
        )

    # Seed a demo guest user
    cur.execute("SELECT COUNT(*) AS c FROM users")
    if cur.fetchone()["c"] == 0:
        cur.execute(
            "INSERT INTO users (full_name, email, phone, password_hash) VALUES (?,?,?,?)",
            ("Juan Dela Cruz", "guest@example.com", "09171234567",
             generate_password_hash("guest123")),
        )

    conn.commit()
    conn.close()
    if first_time:
        print(">>> Database initialized with sample data.")


# ------------------------------------------------------------------
# Auth decorators
# ------------------------------------------------------------------
def login_required(fn):
    @wraps(fn)
    def wrapper(*a, **kw):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return fn(*a, **kw)
    return wrapper


def admin_required(fn):
    @wraps(fn)
    def wrapper(*a, **kw):
        if not session.get("is_admin"):
            flash("Admin access required.", "danger")
            return redirect(url_for("admin_login"))
        return fn(*a, **kw)
    return wrapper


# ------------------------------------------------------------------
# Context (make session available in templates)
# ------------------------------------------------------------------
@app.context_processor
def inject_user():
    return {
        "current_user": {
            "id": session.get("user_id"),
            "name": session.get("user_name"),
            "is_admin": session.get("is_admin", False),
        }
    }


# ------------------------------------------------------------------
# Public routes
# ------------------------------------------------------------------
@app.route("/")
def index():
    db = get_db()
    rooms = db.execute(
        "SELECT * FROM rooms WHERE status='available' ORDER BY price_per_night LIMIT 3"
    ).fetchall()
    return render_template("index.html", rooms=rooms)


@app.route("/rooms")
def rooms():
    db = get_db()
    rooms = db.execute("SELECT * FROM rooms ORDER BY id").fetchall()
    return render_template("rooms.html", rooms=rooms)


# ------------------------------------------------------------------
# User auth
# ------------------------------------------------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        full_name = request.form["full_name"].strip()
        email = request.form["email"].strip().lower()
        phone = request.form.get("phone", "").strip()
        password = request.form["password"]

        if not full_name or not email or not password:
            flash("Please fill in all required fields.", "danger")
            return redirect(url_for("register"))

        db = get_db()
        try:
            db.execute(
                "INSERT INTO users (full_name, email, phone, password_hash) VALUES (?,?,?,?)",
                (full_name, email, phone, generate_password_hash(password)),
            )
            db.commit()
        except sqlite3.IntegrityError:
            flash("Email already registered.", "danger")
            return redirect(url_for("register"))

        flash("Registration successful! Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["user_name"] = user["full_name"]
            session["is_admin"] = False
            flash(f"Welcome, {user['full_name']}!", "success")
            return redirect(url_for("rooms"))
        flash("Invalid email or password.", "danger")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out.", "info")
    return redirect(url_for("index"))


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
    if request.method == "POST":
        full_name = request.form["full_name"].strip()
        phone = request.form.get("phone", "").strip()
        new_password = request.form.get("new_password", "")
        if new_password:
            db.execute(
                "UPDATE users SET full_name=?, phone=?, password_hash=? WHERE id=?",
                (full_name, phone, generate_password_hash(new_password), user["id"]),
            )
        else:
            db.execute(
                "UPDATE users SET full_name=?, phone=? WHERE id=?",
                (full_name, phone, user["id"]),
            )
        db.commit()
        session["user_name"] = full_name
        flash("Profile updated.", "success")
        return redirect(url_for("profile"))

    reservations = db.execute("""
        SELECT r.*, rm.name AS room_name
        FROM reservations r JOIN rooms rm ON rm.id = r.room_id
        WHERE r.user_id=? ORDER BY r.created_at DESC
    """, (user["id"],)).fetchall()
    return render_template("profile.html", user=user, reservations=reservations)


# ------------------------------------------------------------------
# Booking
# ------------------------------------------------------------------
def _parse_date(s):
    return datetime.strptime(s, "%Y-%m-%d").date()


def _is_room_available(db, room_id, check_in, check_out, exclude_res_id=None):
    """Check overlapping confirmed/pending reservations."""
    q = """
        SELECT id FROM reservations
        WHERE room_id=? AND status IN ('pending','confirmed','checked_in')
          AND NOT (check_out <= ? OR check_in >= ?)
    """
    params = [room_id, check_in, check_out]
    if exclude_res_id:
        q += " AND id != ?"
        params.append(exclude_res_id)
    return db.execute(q, params).fetchone() is None


@app.route("/book/<int:room_id>", methods=["GET", "POST"])
@login_required
def booking(room_id):
    db = get_db()
    room = db.execute("SELECT * FROM rooms WHERE id=?", (room_id,)).fetchone()
    if not room:
        flash("Room not found.", "danger")
        return redirect(url_for("rooms"))
    if room["status"] != "available":
        flash("Room is not available for booking.", "warning")
        return redirect(url_for("rooms"))

    if request.method == "POST":
        try:
            ci = _parse_date(request.form["check_in"])
            co = _parse_date(request.form["check_out"])
        except ValueError:
            flash("Invalid date format.", "danger")
            return redirect(url_for("booking", room_id=room_id))

        if ci < date.today():
            flash("Check-in cannot be in the past.", "danger")
            return redirect(url_for("booking", room_id=room_id))
        if co <= ci:
            flash("Check-out must be after check-in.", "danger")
            return redirect(url_for("booking", room_id=room_id))

        nights = (co - ci).days
        total = nights * room["price_per_night"]

        if not _is_room_available(db, room_id, ci.isoformat(), co.isoformat()):
            flash("Sorry, this room is already booked for those dates.", "danger")
            return redirect(url_for("booking", room_id=room_id))

        db.execute("""
            INSERT INTO reservations (user_id, room_id, check_in, check_out, total_amount, status)
            VALUES (?,?,?,?,?, 'pending')
        """, (session["user_id"], room_id, ci.isoformat(), co.isoformat(), total))
        db.commit()
        flash(f"Reservation submitted! Total: ₱{total:,.2f} ({nights} night/s). Waiting for confirmation.", "success")
        return redirect(url_for("profile"))

    return render_template("booking.html", room=room, today=date.today().isoformat())


# ------------------------------------------------------------------
# Admin auth
# ------------------------------------------------------------------
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        db = get_db()
        admin = db.execute("SELECT * FROM admin WHERE username=?", (username,)).fetchone()
        if admin and check_password_hash(admin["password_hash"], password):
            session.clear()
            session["user_id"] = admin["id"]
            session["user_name"] = admin["username"]
            session["is_admin"] = True
            flash("Welcome, Admin!", "success")
            return redirect(url_for("admin_dashboard"))
        flash("Invalid admin credentials.", "danger")
    return render_template("admin_login.html")


# ------------------------------------------------------------------
# Admin pages
# ------------------------------------------------------------------
@app.route("/admin")
@admin_required
def admin_dashboard():
    db = get_db()
    total_rooms = db.execute("SELECT COUNT(*) c FROM rooms").fetchone()["c"]
    total_res = db.execute("SELECT COUNT(*) c FROM reservations").fetchone()["c"]
    total_revenue = db.execute(
        "SELECT COALESCE(SUM(amount),0) s FROM payments WHERE status='paid'"
    ).fetchone()["s"]
    recent = db.execute("""
        SELECT r.*, u.full_name, rm.name AS room_name
        FROM reservations r
        JOIN users u ON u.id = r.user_id
        JOIN rooms rm ON rm.id = r.room_id
        ORDER BY r.created_at DESC LIMIT 8
    """).fetchall()
    return render_template("admin_dashboard.html",
                           total_rooms=total_rooms,
                           total_res=total_res,
                           total_revenue=total_revenue,
                           recent=recent)


# ---------- Room CRUD ----------
@app.route("/admin/rooms")
@admin_required
def manage_rooms():
    db = get_db()
    rooms = db.execute("SELECT * FROM rooms ORDER BY id").fetchall()
    return render_template("manage_rooms.html", rooms=rooms)


@app.route("/admin/rooms/add", methods=["POST"])
@admin_required
def add_room():
    db = get_db()
    db.execute("""
        INSERT INTO rooms (name, description, capacity, price_per_night, status)
        VALUES (?,?,?,?,?)
    """, (
        request.form["name"].strip(),
        request.form.get("description", "").strip(),
        int(request.form["capacity"]),
        float(request.form["price_per_night"]),
        request.form.get("status", "available"),
    ))
    db.commit()
    flash("Room added.", "success")
    return redirect(url_for("manage_rooms"))


@app.route("/admin/rooms/edit/<int:room_id>", methods=["POST"])
@admin_required
def edit_room(room_id):
    db = get_db()
    db.execute("""
        UPDATE rooms SET name=?, description=?, capacity=?, price_per_night=?, status=?
        WHERE id=?
    """, (
        request.form["name"].strip(),
        request.form.get("description", "").strip(),
        int(request.form["capacity"]),
        float(request.form["price_per_night"]),
        request.form.get("status", "available"),
        room_id,
    ))
    db.commit()
    flash("Room updated.", "success")
    return redirect(url_for("manage_rooms"))


@app.route("/admin/rooms/delete/<int:room_id>", methods=["POST"])
@admin_required
def delete_room(room_id):
    db = get_db()
    db.execute("DELETE FROM rooms WHERE id=?", (room_id,))
    db.commit()
    flash("Room deleted.", "info")
    return redirect(url_for("manage_rooms"))


# ---------- Reservation management ----------
@app.route("/admin/reservations")
@admin_required
def manage_reservations():
    db = get_db()
    rows = db.execute("""
        SELECT r.*, u.full_name, u.email, rm.name AS room_name
        FROM reservations r
        JOIN users u ON u.id=r.user_id
        JOIN rooms rm ON rm.id=r.room_id
        ORDER BY r.created_at DESC
    """).fetchall()
    return render_template("manage_reservations.html", reservations=rows)


@app.route("/admin/reservations/<int:res_id>/status", methods=["POST"])
@admin_required
def update_reservation_status(res_id):
    new_status = request.form["status"]
    if new_status not in {"pending", "confirmed", "cancelled", "checked_in", "checked_out"}:
        flash("Invalid status.", "danger")
        return redirect(url_for("manage_reservations"))
    db = get_db()
    db.execute("UPDATE reservations SET status=? WHERE id=?", (new_status, res_id))
    db.commit()
    flash("Reservation updated.", "success")
    return redirect(url_for("manage_reservations"))


# ---------- Payments ----------
@app.route("/admin/payments")
@admin_required
def payments():
    db = get_db()
    pays = db.execute("""
        SELECT p.*, r.id AS res_id, u.full_name, rm.name AS room_name
        FROM payments p
        JOIN reservations r ON r.id=p.reservation_id
        JOIN users u ON u.id=r.user_id
        JOIN rooms rm ON rm.id=r.room_id
        ORDER BY p.paid_at DESC
    """).fetchall()
    reservations = db.execute("""
        SELECT r.id, r.total_amount, u.full_name, rm.name AS room_name
        FROM reservations r
        JOIN users u ON u.id=r.user_id
        JOIN rooms rm ON rm.id=r.room_id
        WHERE r.status IN ('pending','confirmed','checked_in','checked_out')
        ORDER BY r.created_at DESC
    """).fetchall()
    return render_template("payments.html", payments=pays, reservations=reservations)


@app.route("/admin/payments/add", methods=["POST"])
@admin_required
def add_payment():
    db = get_db()
    db.execute("""
        INSERT INTO payments (reservation_id, amount, method, status, transaction_ref)
        VALUES (?,?,?,?,?)
    """, (
        int(request.form["reservation_id"]),
        float(request.form["amount"]),
        request.form["method"],
        request.form.get("status", "paid"),
        request.form.get("transaction_ref", "").strip(),
    ))
    db.commit()
    flash("Payment recorded.", "success")
    return redirect(url_for("payments"))


# ---------- Reports ----------
@app.route("/admin/reports")
@admin_required
def reports():
    db = get_db()
    occupancy = db.execute("""
        SELECT rm.name,
               COUNT(r.id) AS bookings,
               COALESCE(SUM(julianday(r.check_out)-julianday(r.check_in)),0) AS nights_booked
        FROM rooms rm
        LEFT JOIN reservations r ON r.room_id=rm.id
             AND r.status IN ('confirmed','checked_in','checked_out')
        GROUP BY rm.id ORDER BY bookings DESC
    """).fetchall()

    res_list = db.execute("""
        SELECT r.*, u.full_name, rm.name AS room_name
        FROM reservations r
        JOIN users u ON u.id=r.user_id
        JOIN rooms rm ON rm.id=r.room_id
        ORDER BY r.created_at DESC
    """).fetchall()

    revenue = db.execute("""
        SELECT method,
               COALESCE(SUM(amount),0) AS total
        FROM payments WHERE status='paid'
        GROUP BY method
    """).fetchall()

    grand_total = db.execute(
        "SELECT COALESCE(SUM(amount),0) s FROM payments WHERE status='paid'"
    ).fetchone()["s"]

    return render_template("reports.html",
                           occupancy=occupancy,
                           reservations=res_list,
                           revenue=revenue,
                           grand_total=grand_total)


# ------------------------------------------------------------------
# Entrypoint
# ------------------------------------------------------------------
with app.app_context():
    init_db()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
