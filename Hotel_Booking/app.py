from datetime import date
from pathlib import Path
import sqlite3

from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = "replace-with-a-random-secret-before-deployment"
DB_PATH = Path(__file__).with_name("hotel.db")

ROOMS = [
    {"id": 1, "name": "Standard Room", "price": 1800, "capacity": 2, "description": "Comfortable room for a relaxed stay.", "emoji": "🛏️"},
    {"id": 2, "name": "Deluxe Room", "price": 2800, "capacity": 2, "description": "Extra space with a cosy sitting area.", "emoji": "🪴"},
    {"id": 3, "name": "Family Suite", "price": 4500, "capacity": 4, "description": "A spacious suite for families or friends.", "emoji": "🏡"},
]

def connect_db():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection

def init_db():
    with connect_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guest_name TEXT NOT NULL,
                email TEXT NOT NULL,
                room_id INTEGER NOT NULL,
                check_in TEXT NOT NULL,
                check_out TEXT NOT NULL,
                guests INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

def room_by_id(room_id):
    return next((room for room in ROOMS if room["id"] == room_id), None)

def is_available(room_id, check_in, check_out):
    with connect_db() as db:
        overlap = db.execute("""
            SELECT COUNT(*) FROM bookings
            WHERE room_id = ?
              AND check_in < ?
              AND check_out > ?
        """, (room_id, check_out, check_in)).fetchone()[0]
    return overlap == 0

@app.route("/")
def home():
    return render_template("index.html", rooms=ROOMS, today=date.today().isoformat())

@app.route("/book/<int:room_id>", methods=["GET", "POST"])
def book_room(room_id):
    room = room_by_id(room_id)
    if room is None:
        return render_template("not_found.html"), 404

    if request.method == "POST":
        guest_name = request.form.get("guest_name", "").strip()
        email = request.form.get("email", "").strip()
        check_in = request.form.get("check_in", "")
        check_out = request.form.get("check_out", "")
        try:
            guests = int(request.form.get("guests", "1"))
        except ValueError:
            guests = 0

        if not guest_name or not email or not check_in or not check_out:
            flash("Please complete every field.", "error")
        elif check_in < date.today().isoformat():
            flash("Check-in date cannot be in the past.", "error")
        elif check_out <= check_in:
            flash("Check-out must be after check-in.", "error")
        elif guests < 1 or guests > room["capacity"]:
            flash(f"This room allows 1 to {room['capacity']} guests.", "error")
        elif not is_available(room_id, check_in, check_out):
            flash("This room is already booked for those dates. Please choose other dates.", "error")
        else:
            with connect_db() as db:
                cursor = db.execute("""
                    INSERT INTO bookings (guest_name, email, room_id, check_in, check_out, guests)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (guest_name, email, room_id, check_in, check_out, guests))
                booking_id = cursor.lastrowid
            return redirect(url_for("confirmation", booking_id=booking_id))

    return render_template("book.html", room=room, today=date.today().isoformat())

@app.route("/confirmation/<int:booking_id>")
def confirmation(booking_id):
    with connect_db() as db:
        booking = db.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,)).fetchone()
    if booking is None:
        return render_template("not_found.html"), 404
    booking_data = dict(booking)
    booking_data["room"] = room_by_id(booking_data["room_id"])
    return render_template("confirmation.html", booking=booking_data)

@app.route("/bookings")
def bookings():
    with connect_db() as db:
        rows = db.execute("SELECT * FROM bookings ORDER BY created_at DESC, id DESC").fetchall()
    booking_list = []
    for row in rows:
        item = dict(row)
        item["room"] = room_by_id(item["room_id"])
        booking_list.append(item)
    return render_template("bookings.html", bookings=booking_list)

@app.route("/cancel/<int:booking_id>", methods=["POST"])
def cancel_booking(booking_id):
    with connect_db() as db:
        db.execute("DELETE FROM bookings WHERE id = ?", (booking_id,))
    flash("Booking cancelled.", "success")
    return redirect(url_for("bookings"))

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
