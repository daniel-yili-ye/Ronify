import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///ronify.db")

@app.route("/")
@login_required
def index():
    """Show user's customers"""

    company = db.execute("SELECT * FROM users WHERE id = :user_id", user_id=session["user_id"])

    customers = db.execute("SELECT * FROM customers WHERE id = :user_id", user_id=session["user_id"])

    # Directing the user to the homepage to see their share and cash info
    return render_template("index.html", company=company, customers=customers)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure email was submitted
        if not request.form.get("email"):
            return apology("must provide email", 403)

        # Ensure password was email
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for info based on user's email
        rows = db.execute("SELECT * FROM users WHERE email = :email",
                          email=request.form.get("email"))

        # Ensure email exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid email and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("company"):
            return apology("must provide a company name", 403)

        # Ensure email was submitted
        elif not request.form.get("email"):
            return apology("must provide email", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Ensure confirmation password was submitted
        elif not request.form.get("confirm"):
            return apology("must provide a confirmation password", 403)

        # Ensure company name is unique in the database
        elif db.execute("SELECT * FROM users WHERE company = :company", company=request.form.get("company")):
            return apology("this company name has already been taken", 403)

        # Ensure the password and confirmation password match
        elif request.form.get("password") != request.form.get("confirm"):
            return apology("password and confirmation do not match", 403)

        # Insert company name, email, and password hash into database
        db.execute("INSERT INTO users (company, email, hash) VALUES (:company, :email, :password)",
            company=request.form.get("company"), email=request.form.get("email"), password=generate_password_hash(request.form.get("password")))

        # Query database for current user id based on company name
        user_id = db.execute("SELECT id FROM users WHERE company = :company", company=request.form.get("company"))

        # Remember that the new user has logged in
        session["user_id"] = user_id[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
