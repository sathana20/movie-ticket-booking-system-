"""
db.py - MySQL connection helper + first-run admin seeding.
Uses mysql-connector-python. Update DB_CONFIG with your MySQL Workbench credentials.
"""
import mysql.connector
from mysql.connector import pooling
import bcrypt

DB_CONFIG = {
    "host": "localhost",
    "user": "root",  
    "port": 3360,        # <-- change to your MySQL Workbench username
    "password": "sathana@",  # <-- change to your MySQL Workbench password
    "database": "movie_booking_db",
}

# Connection pool so multiple requests can get their own connection safely
pool = pooling.MySQLConnectionPool(
    pool_name="movie_booking_pool",
    pool_size=10,
    **DB_CONFIG
)


def get_connection():
    """Get a connection from the pool. Caller MUST close() it when done."""
    return pool.get_connection()


def seed_admin():
    """Create a default admin account if none exists yet."""
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT id FROM users WHERE role = 'admin' LIMIT 1")
        if cur.fetchone() is None:
            hashed = bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()).decode()
            cur.execute(
                "INSERT INTO users (name, email, password, role) VALUES (%s,%s,%s,%s)",
                ("Administrator", "admin@cinema.com", hashed, "admin"),
            )
            conn.commit()
            print("Seeded default admin -> email: admin@cinema.com  password: admin123")
    finally:
        cur.close()
        conn.close()
