from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
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

# ── SETUP TRIGGERS (call once) ────────────────────────────────────────────────
def setup_triggers():
    db = get_db()
    if not db:
        return
    cur = db.cursor()
    # Trigger: when a new Customer is inserted, auto-insert an Employee_Serves_Customer
    # using the employee with the least assignments in Customer Service dept (ID 102).
    # Also create audit log table if not exists.
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS Customer_Audit (
                Audit_ID INT AUTO_INCREMENT PRIMARY KEY,
                C_ID INT,
                Name VARCHAR(100),
                Phone_No VARCHAR(20),
                Action VARCHAR(20),
                Action_Time DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db.commit()
    except:
        pass

    try:
        cur.execute("DROP TRIGGER IF EXISTS after_customer_insert")
        cur.execute("""
            CREATE TRIGGER after_customer_insert
            AFTER INSERT ON Customer
            FOR EACH ROW
            BEGIN
                DECLARE v_emp INT;
                SELECT e.E_ID INTO v_emp
                FROM Employee e
                LEFT JOIN Employee_Serves_Customer esc ON e.E_ID = esc.Employee_ID
                WHERE e.Dept_ID = 102
                GROUP BY e.E_ID
                ORDER BY COUNT(esc.Customer_ID) ASC
                LIMIT 1;

                IF v_emp IS NOT NULL THEN
                    INSERT IGNORE INTO Employee_Serves_Customer (Employee_ID, Customer_ID)
                    VALUES (v_emp, NEW.C_ID);
                END IF;

                INSERT INTO Customer_Audit (C_ID, Name, Phone_No, Action)
                VALUES (NEW.C_ID, NEW.Name, NEW.Phone_No, 'INSERT');
            END
        """)
        db.commit()
    except Exception as e:
        print(f"[TRIGGER WARN] {e}")

    try:
        cur.execute("DROP TRIGGER IF EXISTS after_customer_delete")
        cur.execute("""
            CREATE TRIGGER after_customer_delete
            AFTER DELETE ON Customer
            FOR EACH ROW
            BEGIN
                INSERT INTO Customer_Audit (C_ID, Name, Phone_No, Action)
                VALUES (OLD.C_ID, OLD.Name, OLD.Phone_No, 'DELETE');
            END
        """)
        db.commit()
    except Exception as e:
        print(f"[TRIGGER WARN] {e}")

    cur.close()
    db.close()

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
@app.route('/products', methods=['GET','POST'])
def products():
    db = get_db()
    items = []
    new_id = None

    sort   = request.args.get('sort', 'P_ID')
    order  = request.args.get('order', 'ASC')
    ftype  = request.args.get('type', '')
    search = request.args.get('search', '').strip()

    allowed_sorts = {'P_ID','Type','Cost','Quantity','Expiry'}
    if sort not in allowed_sorts:
        sort = 'P_ID'
    order = 'DESC' if order == 'DESC' else 'ASC'

    if db:
        cur = db.cursor()

        if request.method == 'POST':
            action = request.form.get('action', 'add')

            if action == 'update':
                pid    = request.form.get('p_id')
                ptype  = request.form.get('type','').strip()
                qty    = request.form.get('quantity','').strip()
                cost   = request.form.get('cost','').strip()
                expiry = request.form.get('expiry','').strip()
                mfr    = request.form.get('manufacturer','').strip()
                if all([pid, ptype, qty, cost, expiry, mfr]):
                    cur.execute(
                        "UPDATE Product SET Type=%s, Quantity=%s, Cost=%s, Expiry=%s, Manufacturer=%s WHERE P_ID=%s",
                        (ptype, int(qty), int(cost), expiry, mfr, pid)
                    )
                    db.commit()
                    flash(f'Product <strong>#{pid}</strong> updated successfully!', 'success')
                else:
                    flash('Update failed — missing fields.', 'error')
            else:
                ptype  = request.form.get('type','').strip()
                qty    = request.form.get('quantity','').strip()
                cost   = request.form.get('cost','').strip()
                expiry = request.form.get('expiry','').strip()
                mfr    = request.form.get('manufacturer','').strip()
                if all([ptype, qty, cost, expiry, mfr]):
                    cur.execute("SELECT COALESCE(MAX(P_ID),900)+1 FROM Product")
                    new_id = cur.fetchone()[0]
                    cur.execute(
                        "INSERT INTO Product (P_ID,Type,Quantity,Cost,Expiry,Manufacturer) VALUES (%s,%s,%s,%s,%s,%s)",
                        (new_id, ptype, int(qty), int(cost), expiry, mfr)
                    )
                    db.commit()
                    flash(f'Product added! Assigned ID: <strong>#{new_id}</strong>', 'success')
                else:
                    flash('Please fill in all fields.', 'error')
            cur.close()
            db.close()
            return redirect(url_for('products'))

        # DELETE
        if request.args.get('delete'):
            pid = request.args.get('delete')
            try:
                cur.execute("DELETE FROM Purchases WHERE Product_ID=%s", (pid,))
                cur.execute("DELETE FROM Supplier_Product WHERE Product_ID=%s", (pid,))
                cur.execute("DELETE FROM Product WHERE P_ID=%s", (pid,))
                db.commit()
                flash('Product deleted.', 'success')
            except Exception as e:
                db.rollback()
                flash(f'Cannot delete: {e}', 'error')
            cur.close()
            db.close()
            return redirect(url_for('products'))

        query = "SELECT P_ID, Type, Quantity, Cost, Expiry, Manufacturer FROM Product WHERE 1=1"
        params = []
        if ftype:
            query += " AND Type=%s"
            params.append(ftype)
        if search:
            query += " AND (Type LIKE %s OR Manufacturer LIKE %s)"
            params += [f"%{search}%", f"%{search}%"]
        query += f" ORDER BY {sort} {order}"
        cur.execute(query, params)
        items = cur.fetchall()
        cur.close()
        db.close()

    return render_template('products.html', products=items,
                           sort=sort, order=order, ftype=ftype, search=search)

# ── CUSTOMERS ─────────────────────────────────────────────────────────────────
@app.route('/customers', methods=['GET','POST'])
def customers():
    db = get_db()
    items = []
    search = request.args.get('search', '').strip()
    sort   = request.args.get('sort', 'C_ID')
    order  = request.args.get('order', 'ASC')
    allowed_sorts = {'C_ID','Name','Phone_No'}
    if sort not in allowed_sorts:
        sort = 'C_ID'
    order = 'DESC' if order == 'DESC' else 'ASC'

    if db:
        cur = db.cursor()

        if request.method == 'POST':
            action = request.form.get('action','add')

            if action == 'add':
                name  = request.form.get('name','').strip()
                phone = request.form.get('phoneno','').strip()
                if name and phone:
                    cur.execute("SELECT COALESCE(MAX(C_ID),8000)+1 FROM Customer")
                    new_id = cur.fetchone()[0]
                    cur.execute("INSERT INTO Customer (C_ID, Name, Phone_No) VALUES (%s,%s,%s)",
                                (new_id, name, phone))
                    db.commit()
                    flash(f'Customer registered! Assigned ID: <strong>#{new_id}</strong>. Auto-assigned to a Customer Service employee.', 'success')
                else:
                    flash('Please fill in all fields.', 'error')

            elif action == 'update':
                cid   = request.form.get('c_id')
                name  = request.form.get('name','').strip()
                phone = request.form.get('phoneno','').strip()
                if cid and name and phone:
                    cur.execute("UPDATE Customer SET Name=%s, Phone_No=%s WHERE C_ID=%s",
                                (name, phone, cid))
                    db.commit()
                    flash('Customer updated successfully!', 'success')
                else:
                    flash('Update failed — missing fields.', 'error')

            cur.close()
            db.close()
            return redirect(url_for('customers'))

        # DELETE
        if request.args.get('delete'):
            cid = request.args.get('delete')
            try:
                cur.execute("DELETE FROM Employee_Serves_Customer WHERE Customer_ID=%s", (cid,))
                cur.execute("DELETE FROM Purchases WHERE Customer_ID=%s", (cid,))
                cur.execute("DELETE FROM Customer WHERE C_ID=%s", (cid,))
                db.commit()
                flash('Customer deleted.', 'success')
            except Exception as e:
                db.rollback()
                flash(f'Cannot delete: {e}', 'error')
            cur.close()
            db.close()
            return redirect(url_for('customers'))

        query  = "SELECT C_ID, Name, Phone_No FROM Customer WHERE 1=1"
        params = []
        if search:
            query += " AND (Name LIKE %s OR Phone_No LIKE %s OR CAST(C_ID AS CHAR) LIKE %s)"
            params += [f"%{search}%", f"%{search}%", f"%{search}%"]
        query += f" ORDER BY {sort} {order}"
        cur.execute(query, params)
        items = cur.fetchall()
        cur.close()
        db.close()

    return render_template('customers.html', customers=items,
                           search=search, sort=sort, order=order)

# ── EMPLOYEES ─────────────────────────────────────────────────────────────────
@app.route('/employees', methods=['GET','POST'])
def employees():
    db = get_db()
    items = []
    depts = []
    search  = request.args.get('search','').strip()
    fdept   = request.args.get('dept','')
    sort    = request.args.get('sort','E_ID')
    order   = request.args.get('order','ASC')
    allowed_sorts = {'E_ID','Name','Salary','DOB'}
    if sort not in allowed_sorts:
        sort = 'E_ID'
    order = 'DESC' if order == 'DESC' else 'ASC'

    if db:
        cur = db.cursor()

        if request.method == 'POST':
            action = request.form.get('action','add')

            if action == 'add':
                name   = request.form.get('name','').strip()
                salary = request.form.get('salary','').strip()
                dob    = request.form.get('dob','').strip()
                dept   = request.form.get('dept_id','').strip()
                if all([name, salary, dob, dept]):
                    cur.execute("SELECT COALESCE(MAX(E_ID),0)+1 FROM Employee")
                    new_id = cur.fetchone()[0]
                    cur.execute(
                        "INSERT INTO Employee (E_ID,Name,Salary,DOB,Dept_ID) VALUES (%s,%s,%s,%s,%s)",
                        (new_id, name, int(salary), dob, int(dept))
                    )
                    db.commit()
                    flash(f'Employee added! Assigned ID: <strong>#{new_id}</strong>', 'success')
                else:
                    flash('Please fill in all fields.', 'error')

            elif action == 'update':
                eid    = request.form.get('e_id')
                name   = request.form.get('name','').strip()
                salary = request.form.get('salary','').strip()
                dob    = request.form.get('dob','').strip()
                dept   = request.form.get('dept_id','').strip()
                if all([eid, name, salary, dob, dept]):
                    cur.execute(
                        "UPDATE Employee SET Name=%s, Salary=%s, DOB=%s, Dept_ID=%s WHERE E_ID=%s",
                        (name, int(salary), dob, int(dept), eid)
                    )
                    db.commit()
                    flash('Employee updated successfully!', 'success')
                else:
                    flash('Update failed — missing fields.', 'error')

            cur.close()
            db.close()
            return redirect(url_for('employees'))

        # DELETE
        if request.args.get('delete'):
            eid = request.args.get('delete')
            try:
                cur.execute("DELETE FROM Employee_Serves_Customer WHERE Employee_ID=%s", (eid,))
                cur.execute("DELETE FROM Employee_Orders_Supplier WHERE Employee_ID=%s", (eid,))
                cur.execute("DELETE FROM Employee WHERE E_ID=%s", (eid,))
                db.commit()
                flash('Employee deleted.', 'success')
            except Exception as e:
                db.rollback()
                flash(f'Cannot delete: {e}', 'error')
            cur.close()
            db.close()
            return redirect(url_for('employees'))

        cur.execute("SELECT D_ID, Name FROM Department ORDER BY D_ID")
        depts = cur.fetchall()

        query  = """SELECT e.E_ID, e.Name, d.Name AS Dept, e.DOB, e.Salary, e.Dept_ID
                    FROM Employee e LEFT JOIN Department d ON e.Dept_ID = d.D_ID WHERE 1=1"""
        params = []
        if search:
            query += " AND (e.Name LIKE %s OR d.Name LIKE %s OR CAST(e.E_ID AS CHAR) LIKE %s)"
            params += [f"%{search}%", f"%{search}%", f"%{search}%"]
        if fdept:
            query += " AND e.Dept_ID=%s"
            params.append(fdept)
        query += f" ORDER BY e.{sort} {order}"
        cur.execute(query, params)
        items = cur.fetchall()
        cur.close()
        db.close()

    return render_template('employees.html', employees=items, depts=depts,
                           search=search, fdept=fdept, sort=sort, order=order)

# ── SUPPLIERS ─────────────────────────────────────────────────────────────────
@app.route('/suppliers', methods=['GET','POST'])
def suppliers():
    db = get_db()
    items = []
    search = request.args.get('search','').strip()
    sort   = request.args.get('sort','S_ID')
    order  = request.args.get('order','ASC')
    allowed_sorts = {'S_ID','Name','Contact_No'}
    if sort not in allowed_sorts:
        sort = 'S_ID'
    order = 'DESC' if order == 'DESC' else 'ASC'

    if db:
        cur = db.cursor()

        if request.method == 'POST':
            action = request.form.get('action','add')

            if action == 'add':
                name    = request.form.get('name','').strip()
                contact = request.form.get('contact','').strip()
                if name and contact:
                    cur.execute("SELECT COALESCE(MAX(S_ID),5000)+1 FROM Supplier")
                    new_id = cur.fetchone()[0]
                    cur.execute("INSERT INTO Supplier (S_ID,Name,Contact_No) VALUES (%s,%s,%s)",
                                (new_id, name, contact))
                    db.commit()
                    flash(f'Supplier added! Assigned ID: <strong>#{new_id}</strong>', 'success')
                else:
                    flash('Please fill in all fields.', 'error')

            elif action == 'update':
                sid     = request.form.get('s_id')
                name    = request.form.get('name','').strip()
                contact = request.form.get('contact','').strip()
                if sid and name and contact:
                    cur.execute("UPDATE Supplier SET Name=%s, Contact_No=%s WHERE S_ID=%s",
                                (name, contact, sid))
                    db.commit()
                    flash('Supplier updated!', 'success')
                else:
                    flash('Update failed.', 'error')

            cur.close()
            db.close()
            return redirect(url_for('suppliers'))

        # DELETE
        if request.args.get('delete'):
            sid = request.args.get('delete')
            try:
                cur.execute("DELETE FROM Supplier_Product WHERE Supplier_ID=%s", (sid,))
                cur.execute("DELETE FROM Employee_Orders_Supplier WHERE Supplier_ID=%s", (sid,))
                cur.execute("DELETE FROM Supplier WHERE S_ID=%s", (sid,))
                db.commit()
                flash('Supplier deleted.', 'success')
            except Exception as e:
                db.rollback()
                flash(f'Cannot delete: {e}', 'error')
            cur.close()
            db.close()
            return redirect(url_for('suppliers'))

        query = """SELECT s.S_ID, s.Name, s.Contact_No,
                          GROUP_CONCAT(p.Type ORDER BY p.P_ID SEPARATOR ', ') AS Products
                   FROM Supplier s
                   LEFT JOIN Supplier_Product sp ON s.S_ID = sp.Supplier_ID
                   LEFT JOIN Product p ON sp.Product_ID = p.P_ID
                   WHERE 1=1"""
        params = []
        if search:
            query += " AND (s.Name LIKE %s OR s.Contact_No LIKE %s OR CAST(s.S_ID AS CHAR) LIKE %s)"
            params += [f"%{search}%", f"%{search}%", f"%{search}%"]
        query += f" GROUP BY s.S_ID, s.Name, s.Contact_No ORDER BY s.{sort} {order}"
        cur.execute(query, params)
        items = cur.fetchall()
        cur.close()
        db.close()

    return render_template('suppliers.html', suppliers=items,
                           search=search, sort=sort, order=order)

# ── SALES ─────────────────────────────────────────────────────────────────────
@app.route('/sales', methods=['GET','POST'])
def sales():
    db = get_db()
    items = []
    kpi   = {"peak": 0, "avg": 0, "total": 0, "count": 0}
    depts = []
    sort  = request.args.get('sort','Sa_ID')
    order = request.args.get('order','ASC')
    fdept = request.args.get('dept','')
    search = request.args.get('search','').strip()
    allowed_sorts = {'Sa_ID','Daily_Sales'}
    if sort not in allowed_sorts:
        sort = 'Sa_ID'
    order = 'DESC' if order == 'DESC' else 'ASC'

    if db:
        cur = db.cursor()

        if request.method == 'POST':
            action = request.form.get('action','add')

            if action == 'add':
                daily   = request.form.get('daily_sales','').strip()
                expense = request.form.get('expense','').strip()
                dept    = request.form.get('dept_id','').strip()
                if daily and expense and dept:
                    cur.execute("SELECT COALESCE(MAX(Sa_ID),0)+1 FROM Sales")
                    new_id = cur.fetchone()[0]
                    cur.execute(
                        "INSERT INTO Sales (Sa_ID,Daily_Sales,Expense_Calculation,Dept_ID) VALUES (%s,%s,%s,%s)",
                        (new_id, int(daily), expense, int(dept))
                    )
                    db.commit()
                    flash(f'Sales record added! Assigned ID: <strong>#{new_id}</strong>', 'success')
                else:
                    flash('Please fill in all fields.', 'error')

            elif action == 'update':
                said    = request.form.get('sa_id')
                daily   = request.form.get('daily_sales','').strip()
                expense = request.form.get('expense','').strip()
                dept    = request.form.get('dept_id','').strip()
                if all([said, daily, expense, dept]):
                    cur.execute(
                        "UPDATE Sales SET Daily_Sales=%s, Expense_Calculation=%s, Dept_ID=%s WHERE Sa_ID=%s",
                        (int(daily), expense, int(dept), said)
                    )
                    db.commit()
                    flash('Sales record updated!', 'success')
                else:
                    flash('Update failed.', 'error')

            cur.close()
            db.close()
            return redirect(url_for('sales'))

        # DELETE
        if request.args.get('delete'):
            said = request.args.get('delete')
            try:
                cur.execute("DELETE FROM Sales WHERE Sa_ID=%s", (said,))
                db.commit()
                flash('Sales record deleted.', 'success')
            except Exception as e:
                db.rollback()
                flash(f'Cannot delete: {e}', 'error')
            cur.close()
            db.close()
            return redirect(url_for('sales'))

        cur.execute("SELECT D_ID, Name FROM Department ORDER BY D_ID")
        depts = cur.fetchall()

        query  = """SELECT sa.Sa_ID, sa.Daily_Sales, sa.Expense_Calculation, d.Name, sa.Dept_ID
                    FROM Sales sa LEFT JOIN Department d ON sa.Dept_ID = d.D_ID WHERE 1=1"""
        params = []
        if fdept:
            query += " AND sa.Dept_ID=%s"
            params.append(fdept)
        if search:
            query += " AND (d.Name LIKE %s OR CAST(sa.Daily_Sales AS CHAR) LIKE %s)"
            params += [f"%{search}%", f"%{search}%"]
        query += f" ORDER BY sa.{sort} {order}"
        cur.execute(query, params)
        items = cur.fetchall()

        if items:
            vals = [r[1] for r in items]
            kpi["peak"]  = max(vals)
            kpi["avg"]   = int(sum(vals)/len(vals))
            kpi["total"] = sum(vals)
            kpi["count"] = len(items)

        cur.close()
        db.close()

    return render_template('sales.html', sales=items, kpi=kpi, depts=depts,
                           sort=sort, order=order, fdept=fdept, search=search)

# ── DEPARTMENTS ───────────────────────────────────────────────────────────────
@app.route('/departments', methods=['GET','POST'])
def departments():
    db = get_db()
    items = []
    search = request.args.get('search','').strip()
    sort   = request.args.get('sort','D_ID')
    order  = request.args.get('order','ASC')
    allowed_sorts = {'D_ID','Name','Head','Location'}
    if sort not in allowed_sorts:
        sort = 'D_ID'
    order = 'DESC' if order == 'DESC' else 'ASC'

    if db:
        cur = db.cursor()

        if request.method == 'POST':
            action = request.form.get('action','add')

            if action == 'add':
                name     = request.form.get('name','').strip()
                head     = request.form.get('head','').strip()
                location = request.form.get('location','').strip()
                if all([name, head, location]):
                    cur.execute("SELECT COALESCE(MAX(D_ID),100)+1 FROM Department")
                    new_id = cur.fetchone()[0]
                    cur.execute(
                        "INSERT INTO Department (D_ID,Name,Head,Location) VALUES (%s,%s,%s,%s)",
                        (new_id, name, head, location)
                    )
                    db.commit()
                    flash(f'Department added! Assigned ID: <strong>#{new_id}</strong>', 'success')
                else:
                    flash('Please fill in all fields.', 'error')

            elif action == 'update':
                did      = request.form.get('d_id')
                name     = request.form.get('name','').strip()
                head     = request.form.get('head','').strip()
                location = request.form.get('location','').strip()
                if all([did, name, head, location]):
                    cur.execute(
                        "UPDATE Department SET Name=%s, Head=%s, Location=%s WHERE D_ID=%s",
                        (name, head, location, did)
                    )
                    db.commit()
                    flash('Department updated!', 'success')
                else:
                    flash('Update failed.', 'error')

            cur.close()
            db.close()
            return redirect(url_for('departments'))

        # DELETE
        if request.args.get('delete'):
            did = request.args.get('delete')
            try:
                cur.execute("DELETE FROM Department WHERE D_ID=%s", (did,))
                db.commit()
                flash('Department deleted.', 'success')
            except Exception as e:
                db.rollback()
                flash(f'Cannot delete (check for linked employees/sales): {e}', 'error')
            cur.close()
            db.close()
            return redirect(url_for('departments'))

        query  = "SELECT D_ID, Name, Head, Location FROM Department WHERE 1=1"
        params = []
        if search:
            query += " AND (Name LIKE %s OR Head LIKE %s OR Location LIKE %s)"
            params += [f"%{search}%", f"%{search}%", f"%{search}%"]
        query += f" ORDER BY {sort} {order}"
        cur.execute(query, params)
        items = cur.fetchall()
        cur.close()
        db.close()

    return render_template('departments.html', departments=items,
                           search=search, sort=sort, order=order)

# ── ANALYTICS (Aggregation page) ──────────────────────────────────────────────
@app.route('/analytics')
def analytics():
    db = get_db()
    dept_sales   = []
    top_products = []
    salary_stats = []
    customer_stats = []

    if db:
        cur = db.cursor()

        # 1. Sales aggregation by department — GROUP BY + HAVING
        cur.execute("""
            SELECT d.Name,
                   COUNT(s.Sa_ID)        AS num_records,
                   SUM(s.Daily_Sales)    AS total_sales,
                   AVG(s.Daily_Sales)    AS avg_sales,
                   MAX(s.Daily_Sales)    AS peak_sales,
                   MIN(s.Daily_Sales)    AS min_sales
            FROM Sales s
            JOIN Department d ON s.Dept_ID = d.D_ID
            GROUP BY d.D_ID, d.Name
            HAVING SUM(s.Daily_Sales) > 0
            ORDER BY total_sales DESC
        """)
        dept_sales = cur.fetchall()

        # 2. Product cost analysis by type — GROUP BY
        cur.execute("""
            SELECT Type,
                   COUNT(*)          AS num_products,
                   AVG(Cost)         AS avg_cost,
                   MAX(Cost)         AS max_cost,
                   MIN(Cost)         AS min_cost,
                   SUM(Quantity)     AS total_stock
            FROM Product
            GROUP BY Type
            ORDER BY avg_cost DESC
        """)
        top_products = cur.fetchall()

        # 3. Salary stats by department — GROUP BY + HAVING
        cur.execute("""
            SELECT d.Name,
                   COUNT(e.E_ID)    AS headcount,
                   SUM(e.Salary)    AS payroll,
                   AVG(e.Salary)    AS avg_salary,
                   MAX(e.Salary)    AS max_salary,
                   MIN(e.Salary)    AS min_salary
            FROM Employee e
            JOIN Department d ON e.Dept_ID = d.D_ID
            GROUP BY d.D_ID, d.Name
            HAVING COUNT(e.E_ID) >= 1
            ORDER BY payroll DESC
        """)
        salary_stats = cur.fetchall()

        # 4. Customer purchase counts — GROUP BY
        cur.execute("""
            SELECT c.Name,
                   COUNT(p.Product_ID) AS purchases,
                   c.C_ID
            FROM Customer c
            LEFT JOIN Purchases p ON c.C_ID = p.Customer_ID
            GROUP BY c.C_ID, c.Name
            ORDER BY purchases DESC
        """)
        customer_stats = cur.fetchall()

        cur.close()
        db.close()

    return render_template('analytics.html',
                           dept_sales=dept_sales,
                           top_products=top_products,
                           salary_stats=salary_stats,
                           customer_stats=customer_stats)

if __name__ == '__main__':
    setup_triggers()
    app.run(debug=True)
