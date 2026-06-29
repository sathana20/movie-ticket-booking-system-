# CineBook - Movie Ticket Booking System

A BookMyShow-style movie ticket booking system built with:
- **Backend:** Python (Flask)
- **Database:** MySQL (design it / inspect it in MySQL Workbench)
- **Frontend:** HTML + CSS (Jinja2 templates, no JS framework — vanilla JS only for the seat picker)

## Features
- User registration & login (roles: `user`, `admin`) with bcrypt-hashed passwords
- **Admin:** add movies (with poster upload), add show timings (theatre, date/time, price, seat layout)
- **User:** browse movies, view showtimes, pick seats on a visual seat map, book tickets
- **ACID-safe booking:** seat booking uses a single MySQL transaction with `SELECT ... FOR UPDATE`
  row locking, so two people can never book the same seat (no double-booking), and a booking is
  either fully saved or not saved at all.

## 1. Set up the database (MySQL Workbench)
1. Open MySQL Workbench, connect to your local MySQL server.
2. File → Run SQL Script → select `schema.sql` (or paste its contents into a query tab and run it).
   This creates the `movie_booking_db` database and all tables.

## 2. Configure the app
Open `db.py` and update `DB_CONFIG` with your MySQL Workbench username/password:
```python
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "yourpassword",
    "database": "movie_booking_db",
}
```

## 3. Install dependencies
```bash
pip install -r requirements.txt
```

## 4. Run the app
```bash
python app.py
```
Visit **http://localhost:5000**

A default admin account is auto-created on first run:
- Email: `admin@cinema.com`
- Password: `admin123`

## Project structure
```
movie_booking_app/
├── app.py                 # Flask app: routes for auth, admin, user
├── db.py                  # MySQL connection pool + admin seeding
├── schema.sql             # MySQL schema (import via Workbench)
├── requirements.txt
├── static/
│   ├── css/style.css
│   └── uploads/           # uploaded movie posters land here
└── templates/
    ├── base.html          # shared layout + navbar
    ├── login.html / register.html
    ├── admin_dashboard.html / add_movie.html / add_show.html
    ├── movies.html / shows.html / seats.html
    ├── booking_confirmation.html / my_bookings.html
    └── error.html
```

## How ACID is enforced
| Property | Where |
|---|---|
| **Atomicity** | `add_show` and `book_seats` wrap multiple inserts/updates in `start_transaction()` / `commit()` / `rollback()` — all succeed or all fail. |
| **Consistency** | Foreign keys + `CHECK`/`ENUM` constraints in `schema.sql`; seat status only flips to `BOOKED` after the booking row is safely inserted. |
| **Isolation** | `SELECT ... FOR UPDATE` with `SERIALIZABLE` isolation locks the exact seat rows being booked, so concurrent users can't grab the same seat. |
| **Durability** | Once `conn.commit()` returns, MySQL (InnoDB) guarantees the booking survives a crash/restart. |

## Notes / next steps you may want to add
- Payment gateway integration (currently bookings are auto-"CONFIRMED")
- Email/SMS ticket confirmation
- Seat-hold timer (reserve seats for a few minutes during checkout)
- Pagination/search/filtering on the movies page
- Admin edit movie / edit show / cancel show
