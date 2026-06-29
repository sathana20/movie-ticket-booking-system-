-- ============================================================
-- Movie Ticket Booking System - MySQL Schema
-- Import this in MySQL Workbench (File > Run SQL Script)
-- or run: mysql -u root -p < schema.sql
-- ============================================================

CREATE DATABASE IF NOT EXISTS movie_booking_db
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE movie_booking_db;

-- ------------------------------------------------------------
-- USERS  (role-based: user / admin)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  email VARCHAR(150) NOT NULL UNIQUE,
  password VARCHAR(255) NOT NULL,
  role ENUM('user','admin') NOT NULL DEFAULT 'user',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- MOVIES
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS movies (
  id INT AUTO_INCREMENT PRIMARY KEY,
  title VARCHAR(200) NOT NULL,
  description TEXT,
  genre VARCHAR(100),
  language VARCHAR(50),
  duration_minutes INT,
  poster_filename VARCHAR(255),
  created_by INT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- SHOWS (a movie playing at a theatre at a specific time)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS shows (
  id INT AUTO_INCREMENT PRIMARY KEY,
  movie_id INT NOT NULL,
  theatre_name VARCHAR(150) NOT NULL,
  show_time DATETIME NOT NULL,
  total_rows INT NOT NULL DEFAULT 5,
  seats_per_row INT NOT NULL DEFAULT 10,
  price DECIMAL(8,2) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (movie_id) REFERENCES movies(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- SEATS (auto-generated per show, e.g. A1, A2 ... )
-- status drives seat-map color: AVAILABLE / BOOKED
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS seats (
  id INT AUTO_INCREMENT PRIMARY KEY,
  show_id INT NOT NULL,
  seat_label VARCHAR(10) NOT NULL,
  status ENUM('AVAILABLE','BOOKED') NOT NULL DEFAULT 'AVAILABLE',
  UNIQUE KEY uq_show_seat (show_id, seat_label),
  FOREIGN KEY (show_id) REFERENCES shows(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- BOOKINGS (header) + BOOKING_SEATS (line items)
-- Split into two tables -> normalized, supports multi-seat booking
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS bookings (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  show_id INT NOT NULL,
  total_amount DECIMAL(8,2) NOT NULL,
  status ENUM('CONFIRMED','CANCELLED') NOT NULL DEFAULT 'CONFIRMED',
  booked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id),
  FOREIGN KEY (show_id) REFERENCES shows(id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS booking_seats (
  id INT AUTO_INCREMENT PRIMARY KEY,
  booking_id INT NOT NULL,
  seat_id INT NOT NULL,
  FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE CASCADE,
  FOREIGN KEY (seat_id) REFERENCES seats(id)
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- Default admin login -> email: admin@cinema.com / password: admin123
-- (password is bcrypt-hashed by the Python app on first run, see app.py)
-- ------------------------------------------------------------
