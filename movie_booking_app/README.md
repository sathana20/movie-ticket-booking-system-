# CineBook - Movie Ticket Booking System

A BookMyShow-style movie ticket booking system built with:
- **Backend:** Python (Flask)
- **Database:** MySQL (design it / inspect it in MySQL Workbench)
- **Frontend:** HTML + CSS (Jinja2 templates, no JS framework — vanilla JS only for the seat picker)

## Features

- User registration & login (roles: `user`, `admin`) with bcrypt-hashed passwords
- **Admin:**
  - Add movies (with poster upload)
  - Edit movie details (including replacing the poster)
  - Add show timings (theatre, date/time, price, seat layout)
  - Edit a show's theatre, date/time, and price
  - Cancel a show (existing bookings for it are automatically marked cancelled)
  - Manage Shows page per movie listing all its showtimes
- **User:** browse movies, view showtimes, pick seats on a visual seat map, book tickets, view booking history
- **ACID-safe booking:** seat booking uses a single MySQL transaction with `SELECT ... FOR UPDATE`
  row locking, so two people can never book the same seat (no double-booking), and a booking is
  either fully saved or not saved at all.
- **ACID-safe show cancellation:** cancelling a show and marking its bookings as cancelled happens
  in one transaction — either both succeed or neither does.

## 1. Set up the database (MySQL Workbench)

1. Open MySQL Workbench, connect to your local MySQL server.
2. File → Run SQL Script → select `schema.sql` (or paste its contents into a query tab and run it).
   This creates the `movie_booking_db` database and all tables.

## 2. Configure the app

Copy `db.example.py` to `db.py` and update `DB_CONFIG` with your own MySQL credentials.
`db.py` is gitignored, so your real password never gets committed.

```python
DB_CONFIG = {
    "host": "localhost",
    "port": 3306,        # change if your MySQL instance uses a different port
    "user": "root",
    "password": "yourpassword",
    "database": "movie_booking_db",
}
```

> If you're not sure which port your MySQL server uses, check it in MySQL Workbench under
> your connection's settings (Edit Connection → Port).

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



movie_booking_app/
├── app.py                    # Flask app: routes for auth, admin, user
├── db.py                     # MySQL connection pool + admin seeding (gitignored — create from db.example.py)
├── db.example.py             # Template for db.py, safe to commit (no real credentials)
├── schema.sql                # MySQL schema (import via Workbench)
├── requirements.txt
├── .gitignore
├── static/
│   ├── css/style.css
│   └── uploads/               # uploaded movie posters land here
└── templates/
├── base.html               # shared layout + navbar
├── login.html / register.html
├── admin_dashboard.html / add_movie.html / edit_movie.html
├── add_show.html / edit_show.html / manage_shows.html
├── movies.html / shows.html / seats.html
├── booking_confirmation.html / my_bookings.html
└── error.html

## How ACID is enforced

**Atomicity**  `add_show`, `book_seats`, and `cancel_show` wrap multiple inserts/updates/deletes in `start_transaction()` / `commit()` / `rollback()` — all succeed or all fail. 
**Consistency**  Foreign keys + `CHECK`/`ENUM` constraints in `schema.sql`; seat status only flips to `BOOKED` after the booking row is safely inserted; cancelling a show marks its bookings `CANCELLED` before deleting the show. 
**Isolation**  `SELECT ... FOR UPDATE` locks the exact rows being modified (seats during booking, the show row during cancellation), so concurrent admins/users can't act on the same data at once. 
**Durability**  Once `conn.commit()` returns, MySQL (InnoDB) guarantees the change survives a crash/restart. 

## Notes / next steps you may want to add

- Payment gateway integration (currently bookings are auto-`CONFIRMED`)
- Email/SMS ticket confirmation
- Seat-hold timer (reserve seats for a few minutes during checkout)
- Pagination/search/filtering on the movies page
- User-side booking cancellation

