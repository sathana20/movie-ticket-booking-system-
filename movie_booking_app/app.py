
import os
from datetime import datetime
from functools import wraps

import bcrypt
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, abort
)
from werkzeug.utils import secure_filename

from db import get_connection, seed_admin

app = Flask(__name__)
app.secret_key = "change-this-secret-key-in-production"

UPLOAD_FOLDER = os.path.join(app.root_path, "static", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            flash("Please login first.", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user" not in session or session["user"]["role"] != "admin":
            abort(403)
        return f(*args, **kwargs)
    return wrapper


def user_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user" not in session or session["user"]["role"] != "user":
            abort(403)
        return f(*args, **kwargs)
    return wrapper


@app.errorhandler(403)
def forbidden(e):
    return render_template("error.html", message="Access forbidden for your role."), 403



@app.route("/")
def home():
    if "user" not in session:
        return redirect(url_for("login"))
    if session["user"]["role"] == "admin":
        return redirect(url_for("admin_dashboard"))
    return redirect(url_for("browse_movies"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        role = request.form.get("role", "user")  # allow choosing role at signup
        if role not in ("user", "admin"):
            role = "user"

        if not name or not email or not password:
            flash("All fields are required.", "error")
            return redirect(url_for("register"))

        conn = get_connection()
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute("SELECT id FROM users WHERE email = %s", (email,))
            if cur.fetchone():
                flash("Email already registered. Please login.", "error")
                return redirect(url_for("register"))

            hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            cur.execute(
                "INSERT INTO users (name, email, password, role) VALUES (%s,%s,%s,%s)",
                (name, email, hashed, role),
            )
            conn.commit()
            flash("Registration successful! Please login.", "success")
            return redirect(url_for("login"))
        finally:
            cur.close()
            conn.close()

    return render_template("register.html")



@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        conn = get_connection()
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute("SELECT * FROM users WHERE email = %s", (email,))
            user = cur.fetchone()
        finally:
            cur.close()
            conn.close()

        if user and bcrypt.checkpw(password.encode(), user["password"].encode()):
            session["user"] = {"id": user["id"], "name": user["name"], "role": user["role"]}
            flash(f"Welcome back, {user['name']}!", "success")
            return redirect(url_for("home"))

        flash("Invalid email or password.", "error")
        return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect(url_for("login"))



@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT m.*, COUNT(s.id) AS show_count
            FROM movies m LEFT JOIN shows s ON s.movie_id = m.id
            GROUP BY m.id ORDER BY m.created_at DESC
        """)
        movies = cur.fetchall()
    finally:
        cur.close()
        conn.close()
    return render_template("admin_dashboard.html", movies=movies)


@app.route("/admin/movies/add", methods=["GET", "POST"])
@admin_required
def add_movie():
    if request.method == "POST":
        title = request.form["title"].strip()
        description = request.form.get("description", "").strip()
        genre = request.form.get("genre", "").strip()
        language = request.form.get("language", "").strip()
        duration = request.form.get("duration_minutes") or None

        poster_filename = None
        file = request.files.get("poster")
        if file and file.filename and allowed_file(file.filename):
            poster_filename = secure_filename(f"{datetime.now().timestamp()}_{file.filename}")
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], poster_filename))

        conn = get_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                """INSERT INTO movies
                   (title, description, genre, language, duration_minutes, poster_filename, created_by)
                   VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                (title, description, genre, language, duration,
                 poster_filename, session["user"]["id"]),
            )
            conn.commit()
            flash("Movie added successfully.", "success")
        finally:
            cur.close()
            conn.close()
        return redirect(url_for("admin_dashboard"))

    return render_template("add_movie.html")


@app.route("/admin/movies/<int:movie_id>/shows/add", methods=["GET", "POST"])
@admin_required
def add_show(movie_id):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT * FROM movies WHERE id = %s", (movie_id,))
        movie = cur.fetchone()
        if not movie:
            abort(404)

        if request.method == "POST":
            theatre_name = request.form["theatre_name"].strip()
            show_time = request.form["show_time"]  # e.g. 2026-07-01T18:30
            total_rows = int(request.form.get("total_rows", 5))
            seats_per_row = int(request.form.get("seats_per_row", 10))
            price = float(request.form["price"])

            # ---- ACID: insert show + generate seats in ONE transaction ----
            conn2 = get_connection()
            cur2 = conn2.cursor()
            try:
                conn2.start_transaction()
                cur2.execute(
                    """INSERT INTO shows
                       (movie_id, theatre_name, show_time, total_rows, seats_per_row, price)
                       VALUES (%s,%s,%s,%s,%s,%s)""",
                    (movie_id, theatre_name, show_time, total_rows, seats_per_row, price),
                )
                show_id = cur2.lastrowid

                seat_rows = []
                for r in range(total_rows):
                    row_letter = chr(65 + r)  # A, B, C...
                    for n in range(1, seats_per_row + 1):
                        seat_rows.append((show_id, f"{row_letter}{n}"))

                cur2.executemany(
                    "INSERT INTO seats (show_id, seat_label) VALUES (%s,%s)",
                    seat_rows,
                )
                conn2.commit()  # atomic: show + all seats committed together
                flash("Show added with seat map generated.", "success")
            except Exception as e:
                conn2.rollback()  # ATOMICITY: undo show insert if seat gen fails
                flash(f"Failed to add show: {e}", "error")
            finally:
                cur2.close()
                conn2.close()

            return redirect(url_for("admin_dashboard"))

    finally:
        cur.close()
        conn.close()

    return render_template("add_show.html", movie=movie)


@app.route("/admin/movies/<int:movie_id>/delete", methods=["POST"])
@admin_required
def delete_movie(movie_id):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM movies WHERE id = %s", (movie_id,))  # cascades to shows/seats
        conn.commit()
        flash("Movie deleted.", "success")
    finally:
        cur.close()
        conn.close()
    return redirect(url_for("admin_dashboard"))



@app.route("/movies")
@login_required
def browse_movies():
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT * FROM movies ORDER BY created_at DESC")
        movies = cur.fetchall()
    finally:
        cur.close()
        conn.close()
    return render_template("movies.html", movies=movies)


@app.route("/movies/<int:movie_id>/shows")
@login_required
def movie_shows(movie_id):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT * FROM movies WHERE id = %s", (movie_id,))
        movie = cur.fetchone()
        if not movie:
            abort(404)
        cur.execute(
            "SELECT * FROM shows WHERE movie_id = %s ORDER BY show_time", (movie_id,)
        )
        shows = cur.fetchall()
    finally:
        cur.close()
        conn.close()
    return render_template("shows.html", movie=movie, shows=shows)


@app.route("/shows/<int:show_id>/seats")
@login_required
def select_seats(show_id):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT s.*, m.title FROM shows s
            JOIN movies m ON m.id = s.movie_id WHERE s.id = %s
        """, (show_id,))
        show = cur.fetchone()
        if not show:
            abort(404)

        cur.execute(
            "SELECT * FROM seats WHERE show_id = %s ORDER BY seat_label", (show_id,)
        )
        seats = cur.fetchall()
    finally:
        cur.close()
        conn.close()

    return render_template("seats.html", show=show, seats=seats)


@app.route("/shows/<int:show_id>/book", methods=["POST"])
@login_required
@user_required
def book_seats(show_id):
    """
    ACID-safe seat booking.
    - SELECT ... FOR UPDATE locks the chosen seat rows so two users
      can never double-book the same seat (Isolation + Consistency).
    - Everything happens in a single transaction: if ANY seat is
      already booked, the WHOLE booking is rolled back (Atomicity).
    - Once committed, the booking is permanent (Durability).
    """
    seat_ids = request.form.getlist("seat_ids")
    if not seat_ids:
        flash("Please select at least one seat.", "error")
        return redirect(url_for("select_seats", show_id=show_id))

    seat_ids = [int(s) for s in seat_ids]
    user_id = session["user"]["id"]

    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        conn.start_transaction(isolation_level="SERIALIZABLE")

        # Lock the exact seat rows we intend to book
        format_ids = ",".join(["%s"] * len(seat_ids))
        cur.execute(
            f"SELECT * FROM seats WHERE id IN ({format_ids}) AND show_id = %s FOR UPDATE",
            (*seat_ids, show_id),
        )
        locked_seats = cur.fetchall()

        if len(locked_seats) != len(seat_ids):
            raise ValueError("One or more selected seats do not exist for this show.")

        already_booked = [s for s in locked_seats if s["status"] == "BOOKED"]
        if already_booked:
            labels = ", ".join(s["seat_label"] for s in already_booked)
            raise ValueError(f"Seat(s) {labels} just got booked by someone else. Please choose again.")

        # Get price
        cur.execute("SELECT price FROM shows WHERE id = %s", (show_id,))
        show = cur.fetchone()
        total_amount = float(show["price"]) * len(seat_ids)

        # Create booking header
        cur.execute(
            "INSERT INTO bookings (user_id, show_id, total_amount) VALUES (%s,%s,%s)",
            (user_id, show_id, total_amount),
        )
        booking_id = cur.lastrowid

        # Mark seats booked + insert booking_seats line items
        cur.executemany(
            "INSERT INTO booking_seats (booking_id, seat_id) VALUES (%s,%s)",
            [(booking_id, sid) for sid in seat_ids],
        )
        cur.execute(
            f"UPDATE seats SET status = 'BOOKED' WHERE id IN ({format_ids})",
            tuple(seat_ids),
        )

        conn.commit()  # all-or-nothing commit
        flash(f"Booking confirmed! Booking ID #{booking_id}", "success")
        return redirect(url_for("booking_confirmation", booking_id=booking_id))

    except Exception as e:
        conn.rollback()  # undo everything on any failure
        flash(str(e), "error")
        return redirect(url_for("select_seats", show_id=show_id))
    finally:
        cur.close()
        conn.close()


@app.route("/bookings/<int:booking_id>")
@login_required
def booking_confirmation(booking_id):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT b.*, m.title, s.theatre_name, s.show_time
            FROM bookings b
            JOIN shows s ON s.id = b.show_id
            JOIN movies m ON m.id = s.movie_id
            WHERE b.id = %s
        """, (booking_id,))
        booking = cur.fetchone()
        if not booking or booking["user_id"] != session["user"]["id"]:
            abort(404)

        cur.execute("""
            SELECT seat_label FROM booking_seats bs
            JOIN seats st ON st.id = bs.seat_id
            WHERE bs.booking_id = %s
        """, (booking_id,))
        seat_labels = [r["seat_label"] for r in cur.fetchall()]
    finally:
        cur.close()
        conn.close()

    return render_template("booking_confirmation.html", booking=booking, seat_labels=seat_labels)


@app.route("/my-bookings")
@login_required
@user_required
def my_bookings():
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT b.*, m.title, s.theatre_name, s.show_time
            FROM bookings b
            JOIN shows s ON s.id = b.show_id
            JOIN movies m ON m.id = s.movie_id
            WHERE b.user_id = %s
            ORDER BY b.booked_at DESC
        """, (session["user"]["id"],))
        bookings = cur.fetchall()
    finally:
        cur.close()
        conn.close()
    return render_template("my_bookings.html", bookings=bookings)


if __name__ == "__main__":
    seed_admin()
    app.run(debug=True, port=5000)
