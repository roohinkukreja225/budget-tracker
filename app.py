print("Hello")
from flask import Flask, render_template, request, redirect, session
import psycopg2
from datetime import datetime

app = Flask(__name__)
app.secret_key = "secret123"

# =========================
# 🔴 RDS DATABASE CONNECTION (EDIT THIS)
# =========================
DB_HOST = "budget-tracker.cvyc226ucci4.ap-south-1.rds.amazonaws.com"
DB_NAME = "postgres"          # change if you created custom DB
DB_USER = "postgres"          # your RDS username
DB_PASS = "roohin225"     # 🔴 PUT YOUR PASSWORD HERE
DB_PORT = "5432"

def get_connection():
    return psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        port=DB_PORT
    )

# =========================
# CREATE TABLES
# =========================
def create_tables():
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id SERIAL PRIMARY KEY,
            category VARCHAR(50),
            amount FLOAT,
            date DATE,
            payment VARCHAR(50)
        );
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            id SERIAL PRIMARY KEY,
            salary FLOAT DEFAULT 0,
            currency VARCHAR(10) DEFAULT 'Rs.'
        );
        """)

        conn.commit()
        cur.close()
        conn.close()

        print("✅ Tables created successfully")

    except Exception as e:
        print("❌ DB ERROR:", e)

create_tables()

# =========================
# LOGIN
# =========================
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username == "Roohin" and password == "roohin":
            session["user"] = username
            return redirect("/dashboard")
        else:
            return render_template("login.html", error="Invalid credentials")

    return render_template("login.html")

# =========================
# LOGOUT
# =========================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# =========================
# DASHBOARD
# =========================
@app.route("/dashboard")
def dashboard():

    if "user" not in session:
        return redirect("/")

    conn = get_connection()
    cur = conn.cursor()

    # =========================
    # SETTINGS FETCH
    # =========================
    # =========================
# SETTINGS FETCH
# =========================
    cur.execute("SELECT salary, currency, food_budget, transport_budget, shopping_budget, entertainment_budget FROM settings LIMIT 1")
    row = cur.fetchone()

    if row:
        income = float(row[0]) if row[0] else 15000
        currency = row[1] if row[1] else "₹"
    else:
        income = 15000
        currency = "₹"

    # ✅ ALWAYS define settings here (outside if-else)
    settings = {
        "salary": income,
        "currency": currency,
        "food_budget": food_budget,
        "transport_budget": transport_budget,
        "shopping_budget": shopping_budget,
        "entertainment_budget": entertainment_budget,
    }
    
    # =========================
    # EXPENSES FETCH
    # =========================
    cur.execute("SELECT category, amount, date, payment FROM expenses ORDER BY date DESC")
    rows = cur.fetchall()

    expenses = []
    for r in rows:
        expenses.append({
            "category": r[0],
            "amount": float(r[1]),
            "date": r[2],
            "payment": r[3]
        })

    # =========================
    # CALCULATIONS
    # =========================
    total_expense = sum(e["amount"] for e in expenses)
    balance = income - total_expense
    savings_rate = int((balance / income) * 100) if income > 0 else 0
    largest = max([e["amount"] for e in expenses], default=0)

    # =========================
    # CATEGORY DISTRIBUTION
    # =========================
    categories = ["Food", "Transport", "Shopping", "Bills", "Entertainment"]
    category_data = {c: 0 for c in categories}

    for e in expenses:
        if e["category"] in category_data:
            category_data[e["category"]] += e["amount"]

    food = category_data["Food"]
    transport = category_data["Transport"]
    shopping = category_data["Shopping"]
    bills = category_data["Bills"]
    entertainment = category_data["Entertainment"]

    # =========================
    # WEEKLY DATA
    # =========================
    week_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    week_values = [0] * 7

    for e in expenses:
        week_values[e["date"].weekday()] += e["amount"]

    weekly_spend = sum(week_values)

    # =========================
    # DAILY DATA
    # =========================
    daily_labels = list(range(1, 32))
    daily_values = [0] * 31

    for e in expenses:
        idx = e["date"].day - 1
        if 0 <= idx < 31:
            daily_values[idx] += e["amount"]

    # =========================
    # MONTHLY DATA
    # =========================
    months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    income_values = [income] * 12
    expense_values = [0] * 12

    for e in expenses:
        expense_values[e["date"].month - 1] += e["amount"]

    # =========================
    # INSIGHTS
    # =========================
    if expenses:
        highest_day = week_labels[week_values.index(max(week_values))]
        top_category = max(category_data, key=category_data.get)
    else:
        highest_day = "N/A"
        top_category = "N/A"

    # =========================
    # RECENT TRANSACTIONS
    # =========================
    recent = [{
        "category": e["category"],
        "amount": e["amount"],
        "date": e["date"].strftime("%d %b"),
        "payment": e["payment"]
    } for e in expenses[:5]]

    # =========================
    # PERCENTAGES
    # =========================
    def percent(part, total):
        return int((part / total) * 100) if total > 0 else 0

    food_percent = percent(food, food_budget)
    transport_percent = percent(transport, transport_budget)
    shopping_percent = percent(shopping, shopping_budget)

    cur.close()
    conn.close()

    return render_template("dashboard.html",
        settings=settings,
        income=income,
        currency=currency,
        total_expense=total_expense,
        balance=balance,
        savings_rate=savings_rate,
        weekly_spend=weekly_spend,
        largest=largest,

        food=food,
        transport=transport,
        shopping=shopping,
        bills=bills,
        entertainment=entertainment,

        week_labels=week_labels,
        week_values=week_values,

        months=months,
        income_values=income_values,
        expense_values=expense_values,

        daily_labels=daily_labels,
        daily_values=daily_values,

        highest_day=highest_day,
        top_category=top_category,
        recent=recent,

        food_percent=food_percent,
        transport_percent=transport_percent,
        shopping_percent=shopping_percent
    )

# =========================
# ADD EXPENSE
# =========================
@app.route("/add_expense", methods=["GET", "POST"])
def add_expense():

    if "user" not in session:
        return redirect("/")

    if request.method == "POST":
        category = request.form["category"]
        amount = float(request.form["amount"])
        payment = request.form["payment"]
        date = datetime.strptime(request.form["date"], "%Y-%m-%d")

        conn = get_connection()
        cur = conn.cursor()

        cur.execute(
            "INSERT INTO expenses (category, amount, date, payment) VALUES (%s,%s,%s,%s)",
            (category, amount, date, payment)
        )

        conn.commit()
        cur.close()
        conn.close()

        return redirect("/dashboard")

    return render_template("add_expense.html")

# =========================
# SETTINGS
# =========================
@app.route("/settings", methods=["GET", "POST"])
def settings():

    if "user" not in session:
        return redirect("/")

    conn = get_connection()
    cur = conn.cursor()

    # =========================
    # ENSURE SINGLE ROW EXISTS
    # =========================
    cur.execute("SELECT * FROM settings LIMIT 1")
    if not cur.fetchone():
        cur.execute("""
            INSERT INTO settings 
            (salary, currency, food_budget, transport_budget, shopping_budget, entertainment_budget)
            VALUES (15000, '₹', 0, 0, 0, 0)
        """)
        conn.commit()

    # =========================
    # HANDLE POST
    # =========================
    if request.method == "POST":

        form_type = request.form.get("form_type")

        # =========================
        # UPDATE SALARY
        # =========================
        if form_type == "salary":
            income = request.form.get("income")

            if income:
                cur.execute(
                    "UPDATE settings SET salary = %s",
                    (float(income),)
                )
                conn.commit()

        # =========================
        # UPDATE CURRENCY
        # =========================
        elif form_type == "currency":
            currency = request.form.get("currency")

            if currency:
                cur.execute(
                    "UPDATE settings SET currency = %s",
                    (currency,)
                )
                conn.commit()

        # =========================
        # UPDATE BUDGETS
        # =========================
        elif form_type == "budget":

            food = request.form.get("food_budget") or 0
            transport = request.form.get("transport_budget") or 0
            shopping = request.form.get("shopping_budget") or 0
            entertainment = request.form.get("entertainment_budget") or 0

            cur.execute("""
                UPDATE settings
                SET food_budget = %s,
                    transport_budget = %s,
                    shopping_budget = %s,
                    entertainment_budget = %s
            """, (
                float(food),
                float(transport),
                float(shopping),
                float(entertainment)
            ))

            conn.commit()

    # =========================
    # FETCH UPDATED SETTINGS
    # =========================
    cur.execute("""
        SELECT salary, currency,
               food_budget, transport_budget,
               shopping_budget, entertainment_budget
        FROM settings
        LIMIT 1
    """)

    row = cur.fetchone()

    settings = {
        "salary": row[0],
        "currency": row[1],
        "food_budget": row[2],
        "transport_budget": row[3],
        "shopping_budget": row[4],
        "entertainment_budget": row[5]
    }

    cur.close()
    conn.close()

    return render_template("settings.html", settings=settings)
# =========================
# RUN
# =========================
if __name__ == "__main__":
    app.run(debug=True)