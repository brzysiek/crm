import hashlib
import json
import os
from datetime import timedelta
from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "roslinarnia-dev-secret-change-in-production")
app.permanent_session_lifetime = timedelta(weeks=2)

USERS_FILE = os.path.join(os.path.dirname(__file__), "users.json")


def load_users():
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def md5(text):
    return hashlib.md5(text.encode()).hexdigest()


def find_user(login, password):
    users = load_users()
    login_lower = login.lower()
    password_hash = md5(password)
    for user in users:
        if user["login"].lower() == login_lower and user["password_md5"] == password_hash:
            return user
    return None


@app.route("/", methods=["GET", "POST"])
def login():
    if "login" in session:
        return redirect(url_for("dashboard"))

    error = None
    if request.method == "POST":
        login_input = request.form.get("login", "").strip()
        password_input = request.form.get("password", "")
        user = find_user(login_input, password_input)
        if user:
            session["login"] = user["login"]
            if request.form.get("remember"):
                session.permanent = True
            return redirect(url_for("dashboard"))
        else:
            error = "Nieprawidłowy login lub hasło."

    return render_template("login.html", error=error)


@app.route("/dashboard")
def dashboard():
    if "login" not in session:
        return redirect(url_for("login"))
    return render_template("dashboard.html", login=session["login"])


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True)
