from flask import Flask, render_template, request, redirect, url_for, flash
import mysql.connector
from mysql.connector import Error

app = Flask(__name__)
app.secret_key = 'metro_secret_key_2026'

# ── DB CONFIG ─────────────────────────────────────────────────────────────────
DB_CONFIG = {
    "host":     "localhost",
    "user":     "root",
    "password": "Devananda_2006",
    "database": "metro",
    "port":     3308 
}

def get_db():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        print(f"[DB ERROR] {e}")
        return None

# ── HOME ──────────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    db = get_db()
    stats = {"products": 0, "customers": 0, "employees": 0, "suppliers": 0, "sales": 0}
    if db:
        cur = db.cursor()
        for key, table in [("products","Product"),("customers","Customer"),
                           ("employees","Employee"),("suppliers","Supplier"),("sales","Sales")]:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            stats[key] = cur.fetchone()[0]
        cur.close()
        db.close()
    return render_template('index.html', stats=stats)

# ── PRODUCTS ──────────────────────────────────────────────────────────────────
@app.route('/products')
def products():
    db = get_db()
    items = []
    if db:
        cur = db.cursor()
        cur.execute("SELECT P_ID, Type, Quantity, Cost, Expiry, Manufacturer FROM Product ORDER BY P_ID")
        items = cur.fetchall()
        cur.close()
        db.close()
    return render_template('products.html', products=items)

# ── CUSTOMERS ─────────────────────────────────────────────────────────────────
@app.route('/customers', methods=['GET','POST'])
def customers():
    db = get_db()
    items = []
    if db:
        cur = db.cursor()
        if request.method == 'POST':
            name  = request.form.get('name','').strip()
            phone = request.form.get('phoneno','').strip()
            if name and phone:
                cur.execute("SELECT COALESCE(MAX(C_ID),8000)+1 FROM Customer")
                new_id = cur.fetchone()[0]
                cur.execute("INSERT INTO Customer (C_ID, Name, Phone_No) VALUES (%s,%s,%s)",
                            (new_id, name, phone))
                db.commit()
                flash('Customer registered successfully!', 'success')
            else:
                flash('Please fill in all fields.', 'error')
            cur.close()
            db.close()
            return redirect(url_for('customers'))

        cur.execute("SELECT C_ID, Name, Phone_No FROM Customer ORDER BY C_ID")
        items = cur.fetchall()
        cur.close()
        db.close()
    return render_template('customers.html', customers=items)

# ── EMPLOYEES ─────────────────────────────────────────────────────────────────
@app.route('/employees')
def employees():
    db = get_db()
    items = []
    if db:
        cur = db.cursor()
        cur.execute("""
            SELECT e.E_ID, e.Name, d.Name AS Dept, e.DOB, e.Salary
            FROM Employee e
            LEFT JOIN Department d ON e.Dept_ID = d.D_ID
            ORDER BY e.E_ID
        """)
        items = cur.fetchall()
        cur.close()
        db.close()
    return render_template('employees.html', employees=items)

# ── SUPPLIERS ─────────────────────────────────────────────────────────────────
@app.route('/suppliers')
def suppliers():
    db = get_db()
    items = []
    if db:
        cur = db.cursor()
        cur.execute("""
            SELECT s.S_ID, s.Name, s.Contact_No,
                   GROUP_CONCAT(p.Type ORDER BY p.P_ID SEPARATOR ', ') AS Products
            FROM Supplier s
            LEFT JOIN Supplier_Product sp ON s.S_ID = sp.Supplier_ID
            LEFT JOIN Product p ON sp.Product_ID = p.P_ID
            GROUP BY s.S_ID, s.Name, s.Contact_No
            ORDER BY s.S_ID
        """)
        items = cur.fetchall()
        cur.close()
        db.close()
    return render_template('suppliers.html', suppliers=items)

# ── SALES ─────────────────────────────────────────────────────────────────────
@app.route('/sales')
def sales():
    db = get_db()
    items = []
    kpi = {"peak": 0, "avg": 0, "total": 0, "expenses": 0}
    if db:
        cur = db.cursor()
        cur.execute("""
            SELECT sa.Sa_ID, sa.Daily_Sales, sa.Expense_Calculation, d.Name
            FROM Sales sa
            LEFT JOIN Department d ON sa.Dept_ID = d.D_ID
            ORDER BY sa.Sa_ID
        """)
        items = cur.fetchall()
        if items:
            sales_vals = [row[1] for row in items]
            kpi["peak"]  = max(sales_vals)
            kpi["avg"]   = int(sum(sales_vals)/len(sales_vals))
            kpi["total"] = sum(sales_vals)
            kpi["count"] = len(items)
        cur.close()
        db.close()
    return render_template('sales.html', sales=items, kpi=kpi)

# ── DEPARTMENTS ───────────────────────────────────────────────────────────────
@app.route('/departments')
def departments():
    db = get_db()
    items = []
    if db:
        cur = db.cursor()
        cur.execute("SELECT D_ID, Name, Head, Location FROM Department ORDER BY D_ID")
        items = cur.fetchall()
        cur.close()
        db.close()
    return render_template('departments.html', departments=items)

if __name__ == '__main__':
    app.run(debug=True)
