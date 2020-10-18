import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
from dotenv import load_dotenv

from helpers import apology, login_required, lookup, usd, Stock

# Load environment variables
load_dotenv()

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


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""

    # Obtain user cash total
    cash = db.execute("SELECT cash FROM users WHERE id = :id", id=session["user_id"])[
        0
    ]["cash"]

    # Obtain user stock shares info
    rows = db.execute(
        "SELECT * FROM user_shares WHERE user_id = :user_id", user_id=session["user_id"]
    )

    if len(rows) == 0:
        stocks = None
    else:
        # Create a list of stock objects
        stocks = [Stock(row["symbol"], row["shares"]) for row in rows]

        # Calculate net total
        total = cash
        for stock in stocks:
            total += stock.total

    return render_template(
        "index.html", stocks=stocks, cash=cash, format=usd, total=total
    )


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    if request.method == "POST":
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")
        quote = lookup(symbol)

        print(quote)

        # Ensure a valid symbol
        if not quote:
            flash("Invalid symbol.")
            return redirect(request.url)

        # Find current cash of user
        cash = db.execute(
            "SELECT cash FROM users WHERE id = :id", id=session["user_id"]
        )[0]["cash"]

        total = float(shares) * quote["price"]

        # Ensure user has enough cash
        if total > cash:
            return apology("insufficient funds", 403)

        # Add transaction to history
        db.execute(
            "INSERT INTO transactions (user_id, symbol, shares, price, date) VALUES (:user_id, :symbol, :shares, :price, :date)",
            user_id=session["user_id"],
            symbol=symbol,
            shares=shares,
            price=quote["price"],
            date=datetime.now().isoformat(" ", timespec="seconds"),
        )

        # Deduct payment from cash
        db.execute(
            "UPDATE users SET cash = cash - :total WHERE id = :user_id",
            total=total,
            user_id=session["user_id"],
        )

        # Look if user owns shares
        rows = db.execute(
            "SELECT user_id FROM user_shares WHERE symbol = :symbol", symbol=symbol
        )

        # If user owns shares, update shares, else create
        if len(rows) == 1:
            db.execute(
                "UPDATE user_shares SET shares = shares + :shares WHERE user_id = :user_id AND symbol = :symbol",
                shares=shares,
                user_id=session["user_id"],
                symbol=symbol,
            )
        else:
            db.execute(
                "INSERT INTO user_shares (user_id, symbol, shares) VALUES (:user_id, :symbol, :shares)",
                user_id=session["user_id"],
                symbol=symbol,
                shares=shares,
            )

        # Redirect to homepage
        return redirect("/")

    return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    return apology("TODO")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Clear session of current user
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = :username",
            username=request.form.get("username"),
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        flash("You were successfully logged in.")
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
    flash("You have been logged out.")
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""

    if request.method == "POST":
        symbol = request.form.get("symbol")
        quote = lookup(symbol)

        if quote:
            return render_template("quoted.html", quote=quote, format=usd)
        else:
            flash("Invalid symbol.")
            return redirect(request.url)

    return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")
        confirm_pw = request.form.get("confirmation")

        # Ensure username was submitted
        if not username:
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not password:
            return apology("must provide password", 403)

        # Ensure password confirmation
        elif password != confirm_pw:
            return apology("passwords do not match", 403)

        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = :username",
            username=username,
        )

        # Ensure username has not been taken
        if len(rows) == 1:
            return apology("username already exists", 403)

        # Create a new user in the database and log them in
        else:
            db.execute(
                "INSERT INTO users (username, hash) VALUES (:username, :hash)",
                username=username,
                hash=generate_password_hash(password),
            )

            # Query database for username
            rows = db.execute(
                "SELECT * FROM users WHERE username = :username",
                username=username,
            )

            # Remember which user has logged in
            session["user_id"] = rows[0]["id"]

            flash("You have successfully logged in.")
            return redirect("/")

    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""

    if request.method == "GET":

        # Find stocks the user owns shares to
        rows = db.execute(
            "SELECT symbol FROM user_shares WHERE user_id = :user_id",
            user_id=session["user_id"]
        )

        return render_template("sell.html", symbols=rows)

    return apology("TODO")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
