import os
import io 
import base64
import mysql.connector
import qrcode

from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from io import BytesIO
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
db = mysql.connector.connect(
    host="MYSQL5006.site4now.net",
    user="9d6e6e_ronify",
    password="Ronify@2020",
    database="db_9d6e6e_ronify"
)

@app.route("/")
def index(): 
    cur = db.cursor()
    cur.execute("SELECT count(*) FROM business") 
    bcount = cur.fetchall()
    cur.execute("SELECT count(*) FROM visitor") 
    vcount = cur.fetchall()
    qrimg = qrcode.make('https://yesleaf.com/ronify/business/iron-chefabcd')

    buffered = BytesIO()
    qrimg.save(buffered, format='png')
    img_str = base64.b64encode(buffered.getvalue()).decode()

    return render_template("index.html", bcount=bcount[0][0], vcount=vcount[0][0], imgstr=img_str)


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

        # Ensure the password and confirmation password match
        elif request.form.get("password") != request.form.get("confirm"):
            return apology("password and confirmation do not match", 403)

        comp = request.form.get("company").trim()
        comp_code = comp.replace('.', '').rep

        cur = db.cursor()

        # Insert company name, email, and password hash into database
        cur.execute("INSERT INTO users (company, email, hash) VALUES (:company, :email, :password)",
            company=request.form.get("company"), email=request.form.get("email"), password=generate_password_hash(request.form.get("password")))

        # Query database for current user id based on company name
        user_id = db.execute("SELECT id FROM users WHERE company = :company", company=request.form.get("company"))

        # Remember that the new user has logged in
        session["user_id"] = user_id[0]["id"]

        # Redirect user to home page
        return redirect("/qrcode")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


@app.route("/business/<bcode>", methods=["GET", "POST"])
def business(bcode):
    """Customer form"""
    print("")
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure a name was submitted
        if not request.form.get("name"):
            return apology("must provide a name", 403)

        # Ensure phone number was submitted
        elif not request.form.get("phone"):
            return apology("must provide a phone number", 403)
        
        # Ensure number of guests was submitted
        elif not request.form.get("guests"):
            return apology("must provide number of guests", 403)

        # Insert name, phone number, email, guests, and time into customers database
        db.execute("INSERT INTO customers (name, phone, email, guests, time) VALUES (:name, :phone, :email, :guests, CURRENT_TIMESTAMP)",
            name=request.form.get("name"), phone=request.form.get("phone"), email=request.form.get("email"), guests=request.form.get("guests"))

        # Insert business id into customers database
        db.execute("INSERT INTO customers (id) VALUES (:user_id)", user_id=session["user_id"])

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("business.html", bcode=bcode, bname="Yesleaf Superstore")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
