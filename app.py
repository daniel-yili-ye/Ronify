import os
import re
import io 
import base64
import mysql.connector
import qrcode

from flask import Flask, flash, jsonify, redirect, render_template, request, send_file, session, url_for
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from io import BytesIO
from helpers import login_required
from datetime import datetime, timedelta

# export FLASK_APP='app.py'

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

# Configure MySQL
# Credentials removed for privacy reasons
# Database has been closed
def getconnection():
    db = mysql.connector.connect(
        host="",
        user="",
        password="",
        database=""
    )
    return db

@app.route("/")
def index(): 
    
    db = getconnection()
    cur = db.cursor()
    
    cur.execute("SELECT count(*) FROM business") 
    bcount = (cur.fetchall())[0][0]
    
    cur.execute("SELECT count(*) FROM visitor") 
    vcount = (cur.fetchall())[0][0]
    
    cur.close()
    db.close()

    return render_template("index.html", bcount=bcount, vcount=vcount)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    db = getconnection()
    cur = db.cursor()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Query database for password based on user's email
        cur.execute("SELECT id, passwordhash FROM business WHERE email = %s", (request.form.get("email"), ))
        rows = cur.fetchall()
        
        if len(rows) != 1:
            return render_template("login.html", error="Invalid email.")
    
        user_id = rows[0][0]
        p_hash = rows[0][1]
        
        if not check_password_hash(p_hash, request.form.get("password")):
            return render_template("login.html", error="Invalid password.")


        # Remember which user has logged in
        session["user_id"] = user_id

        # Redirect user to home page
        return redirect("/dashboard")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")
    
    cur.close()
    db.close()


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

    db = getconnection()
    cur = db.cursor()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        cur.execute("SELECT email FROM business")
        emails = cur.fetchall()

        for email in emails:
            if request.form.get("email") == email[0]:
                return render_template("register.html", error="Previously entered email is already registered.")

        # Creating unique code from business name
        name = request.form.get("name").strip()
        code = re.sub('[^A-Za-z0-9]+', '', name)

        i = 0
        while True:          
            cur.execute("SELECT count(*) FROM business WHERE code = %s", (code, ))
            repeat = cur.fetchall()
            if repeat[0][0] > 0:
                if i > 0:
                    code = code[:-1]
                i += 1
                code = code + str(i)
            else:
                break
        
        time = datetime.now()

        # Insert company name, email, and password hash into database
        query = "INSERT INTO business (name, code, email, passwordhash, created_at) VALUES (%s, %s, %s, %s, %s)"
        values = (name, code, request.form.get("email"), generate_password_hash(request.form.get("password")), time)

        cur.execute(query, values)

        # Remember that the new user has logged in
        session["user_id"] = cur.lastrowid

        # Redirect user to home page
        return redirect("/qrcode")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")
    
    cur.close()
    db.close()


@app.route("/business/<code>", methods=["GET", "POST"])
def business(code):
    """Customer form"""

    db = getconnection()
    cur = db.cursor()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        cur.execute("SELECT id FROM business WHERE code = %s", (code, ))
        business_id = cur.fetchall()

        # determines if business id exists for the passed code
        business_id = business_id[0][0]

        time = datetime.now()

        # Insert name, phone number, email, guests, and time into customers database
        query = "INSERT INTO visitor (business_id, name, phone, email, guests, created_at) VALUES (%s, %s, %s, %s, %s, %s)"
        values = (business_id, request.form.get("name"), request.form.get("phone"), request.form.get("email"), request.form.get("guests"), time)

        cur.execute(query, values)

        # Redirect user to home page
        try:
            if session["user_id"]:
                return redirect("/dashboard")
                
        except KeyError:
            cur.execute("SELECT name FROM business WHERE code = %s", (code, ))
            business_name = (cur.fetchall())[0][0]
            
            return render_template("thankyou.html", name=business_name)

    # User reached route via GET (as by clicking a link or via redirect)
    else:

        cur.execute("SELECT name FROM business WHERE code = %s", (code, ))
        name = cur.fetchall()

        try:
            # passing through business name
            name = name[0][0]

            return render_template("business.html", name=name, code=code)

        except IndexError:
            return render_template("business.html")

    cur.close()
    db.close()


@app.route("/dashboard", methods=["GET"])
@login_required
def dashboard():

    db = getconnection()
    cur = db.cursor()

    cur.execute("SELECT name, phone, email, guests, created_at FROM visitor WHERE business_id = %s AND created_at >= DATE_SUB(NOW(),INTERVAL 1 DAY) ORDER BY created_at DESC", (session["user_id"], ))
    today = cur.fetchall()

    cur.execute("SELECT name, phone, email, guests, created_at FROM visitor WHERE business_id = %s AND created_at >= DATE_SUB(NOW(),INTERVAL 1 WEEK) ORDER BY created_at DESC", (session["user_id"], ))
    week = cur.fetchall()

    cur.execute("SELECT name, phone, email, guests, created_at FROM visitor WHERE business_id = %s AND created_at >= DATE_SUB(NOW(),INTERVAL 1 MONTH) ORDER BY created_at DESC", (session["user_id"], ))
    month = cur.fetchall()

    cur.execute("SELECT name, phone, email, guests, created_at FROM visitor WHERE business_id = %s ORDER BY created_at DESC", (session["user_id"], ))
    all_time = cur.fetchall()

    cur.execute("SELECT name FROM business WHERE id = %s", (session["user_id"], ))
    name = (cur.fetchall())[0][0]

    cur.execute("SELECT code FROM business WHERE id = %s", (session["user_id"], ))
    code = (cur.fetchall())[0][0]

    return render_template("dashboard.html", today=today, week=week, month=month, all_time=all_time, name=name, code=code)

    cur.close()
    db.close()


# @app.route("/export", methods=["GET"])
# @login_required
# def export():

#     db = getconnection()
#     cur = db.cursor()

#     cur.execute("SELECT name, phone, email, guests, created_at FROM visitor WHERE business_id = %s ORDER BY created_at DESC", (session["user_id"], ))
#     rows = cur.fetchall()

#     wb = Workbook('customers.xlsx')
#     wb.add_worksheet('All Data')

#     for item in rows:
#        wb.write(item)
#     wb.close()

#     return send_file('path/to/workbook.xlsx')

#     cur.close()
#     db.close()


@app.route("/qrcode", methods=["GET"])
@login_required
def qr_code():

    db = getconnection()
    cur = db.cursor()

    cur.execute("SELECT name FROM business WHERE id = %s", (session["user_id"], ))
    name = (cur.fetchall())[0][0]

    cur.execute("SELECT code FROM business WHERE id = %s", (session["user_id"], ))
    code = (cur.fetchall())[0][0]

    cur.close()
    db.close()
    
    # Generate QR Code
    qrimg = qrcode.make('https://ronify.herokuapp.com/business/' + code)

    buffered = BytesIO()
    qrimg.save(buffered, format='png')
    imgstr = base64.b64encode(buffered.getvalue()).decode()

    return render_template("qrcode.html", name=name, code=code, imgstr=imgstr)


@app.route("/about", methods=["GET"])
def about():

    db = getconnection()
    cur = db.cursor()
    
    try:
        if session["user_id"]:
            cur.execute("SELECT code FROM business WHERE id = %s", (session["user_id"], ))
            code = (cur.fetchall())[0][0]
            return render_template("about.html", code=code)

    except KeyError:
        return render_template("about.html")

    cur.close()
    db.close()


@app.route("/contact", methods=["GET"])
def contact():
    
    db = getconnection()
    cur = db.cursor()

    try:
        if session["user_id"]:
            cur.execute("SELECT code FROM business WHERE id = %s", (session["user_id"], ))
            code = (cur.fetchall())[0][0]
            return render_template("contact.html", code=code)

    except KeyError:
        return render_template("contact.html")

    cur.close()
    db.close()


@app.route("/privacy", methods=["GET"])
def privacy():
    
    db = getconnection()
    cur = db.cursor()
    
    try:
        if session["user_id"]:
            cur.execute("SELECT code FROM business WHERE id = %s", (session["user_id"], ))
            code = (cur.fetchall())[0][0]
            return render_template("privacy.html", code=code)
    
    except KeyError:
        return render_template("privacy.html")

    cur.close()
    db.close()

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

