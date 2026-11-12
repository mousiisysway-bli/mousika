import os, sqlite3
from flask import Flask, render_template, request, redirect, session, flash, g

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "mousika-change-this")
DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mousika.db")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")


def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_):
    d = g.pop("db", None)
    if d:
        d.close()


def init_db():
    c = sqlite3.connect(DB)
    c.executescript("""
    CREATE TABLE IF NOT EXISTS courses(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL, description TEXT, duration TEXT,
        schedule TEXT, fee INTEGER DEFAULT 0);
    CREATE TABLE IF NOT EXISTS enrollments(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL, phone TEXT NOT NULL, email TEXT,
        course_id INTEGER, message TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    """)
    if c.execute("SELECT COUNT(*) FROM courses").fetchone()[0] == 0:
        c.executemany(
            "INSERT INTO courses(title,description,duration,schedule,fee) VALUES(?,?,?,?,?)",
            [
                ("Carnatic Vocal", "Sarali varisai to varnams and kritis, with voice culture and shruti practice.", "12 months", "Mon / Wed, 6 PM", 1500),
                ("Veena", "Traditional technique, gamakas and compositions on the saraswati veena.", "12 months", "Tue / Thu, 5 PM", 1800),
                ("Violin", "Bowing, fingering and Carnatic repertoire from beginner to stage level.", "10 months", "Sat / Sun, 10 AM", 1600),
                ("Keyboard", "Chords, scales and film songs, with Carnatic basics for keyboard.", "6 months", "Sat, 4 PM", 1200),
                ("Mridangam", "Adi talam, jathis and korvais, with accompaniment practice.", "12 months", "Sun, 11 AM", 1400),
            ],
        )
    c.commit()
    c.close()


init_db()


@app.route("/")
def home():
    courses = db().execute("SELECT * FROM courses ORDER BY id").fetchall()
    return render_template("index.html", courses=courses)


@app.route("/enroll", methods=["POST"])
def enroll():
    f = request.form
    name, phone = f.get("name", "").strip(), f.get("phone", "").strip()
    if not name or not phone:
        flash("Please enter your name and phone number.", "error")
        return redirect("/#enroll")
    db().execute(
        "INSERT INTO enrollments(name,phone,email,course_id,message) VALUES(?,?,?,?,?)",
        (name, phone, f.get("email", "").strip(), f.get("course_id") or None, f.get("message", "").strip()),
    )
    db().commit()
    flash("Thank you, " + name + ". We will call you within a day.", "ok")
    return redirect("/#enroll")


@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST" and "password" in request.form:
        if request.form["password"] == ADMIN_PASSWORD:
            session["admin"] = True
        else:
            flash("Wrong password.", "error")
        return redirect("/admin")
    if not session.get("admin"):
        return render_template("admin.html", authed=False)
    courses = db().execute("SELECT * FROM courses ORDER BY id").fetchall()
    rows = db().execute(
        """SELECT e.*, c.title AS course FROM enrollments e
           LEFT JOIN courses c ON c.id = e.course_id ORDER BY e.id DESC"""
    ).fetchall()
    return render_template("admin.html", authed=True, courses=courses, rows=rows)


def need_admin():
    return session.get("admin")


@app.route("/admin/course", methods=["POST"])
def add_course():
    if not need_admin():
        return redirect("/admin")
    f = request.form
    db().execute(
        "INSERT INTO courses(title,description,duration,schedule,fee) VALUES(?,?,?,?,?)",
        (f["title"], f.get("description", ""), f.get("duration", ""), f.get("schedule", ""), int(f.get("fee") or 0)),
    )
    db().commit()
    return redirect("/admin")


@app.route("/admin/course/<int:i>/delete", methods=["POST"])
def del_course(i):
    if need_admin():
        db().execute("DELETE FROM courses WHERE id=?", (i,))
        db().commit()
    return redirect("/admin")


@app.route("/admin/enrollment/<int:i>/delete", methods=["POST"])
def del_enrollment(i):
    if need_admin():
        db().execute("DELETE FROM enrollments WHERE id=?", (i,))
        db().commit()
    return redirect("/admin")


@app.route("/admin/logout")
def logout():
    session.clear()
    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True)
