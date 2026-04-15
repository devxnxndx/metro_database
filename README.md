# 🛒 Metro Superstore — DBMS Lab Project

**BTech (Hons.) Data Science**  
**Authors:** Devananda A · Aditya H Shah  
**UEN:** 2024UG000216 · 2024UG000222

---

## 📋 Project Overview

Metro Superstore is a full-stack web application built with **Flask** and **MySQL** for managing a superstore's database — including products, customers, employees, suppliers, sales, and departments.

---

## 🗂️ Project Structure

```
Metro/
│
├── app.py                  ← Flask backend (main file to run)
│
└── templates/
    ├── base.html           ← Shared layout, navbar, footer
    ├── index.html          ← Home / dashboard
    ├── products.html       ← Product inventory
    ├── customers.html      ← Customer list + registration form
    ├── employees.html      ← Employee directory
    ├── suppliers.html      ← Supplier directory
    ├── sales.html          ← Sales records + KPI dashboard
    └── departments.html    ← Department overview
```

> ⚠️ The `templates/` folder **must** be inside the same folder as `app.py`. Flask will not find the HTML files otherwise.

---

## ⚙️ Setup (One-Time)

### 1. Install Python Dependencies
```bash
pip install flask mysql-connector-python
```

### 2. Set Up MySQL Database

Open MySQL terminal:
```bash
mysql -u root -p --port=3308
```
Then run:
```sql
CREATE DATABASE metro;
USE metro;
-- Paste and run all SQL from Metro_DB_Sql_Code.pdf
```

### 3. Configure Database Connection

In `app.py`, update the `DB_CONFIG` block (around line 9):
```python
DB_CONFIG = {
    "host":     "localhost",
    "user":     "root",
    "password": "YOUR_PASSWORD_HERE",
    "database": "metro",
    "port":     3308
}
```

---

## 🚀 Running the Website

> Every time you want to run the website, just do these steps:

**Step 1 — Make sure MySQL is running:**
```bash
net start MySQL80
```
*(Skip if it's already running — it may auto-start with Windows)*

**Step 2 — Run the Flask app:**
```bash
cd C:\Users\Devananda\Metro
python app.py
```

**Step 3 — Open in browser:**
```
http://127.0.0.1:5000
```

To stop the server, press `Ctrl + C` in the terminal.

---

## 🗄️ Database Details

| Setting | Value |
|---|---|
| Host | localhost |
| Port | **3308** (non-default) |
| User | root |
| Database | metro |

### Tables

| Table | Description |
|---|---|
| `Department` | 5 departments with head and location |
| `Employee` | Staff linked to departments |
| `Customer` | Registered customers |
| `Product` | Inventory with type, cost, expiry |
| `Supplier` | Supply chain partners |
| `Sales` | Daily sales records per department |
| `Employee_Serves_Customer` | Junction table |
| `Purchases` | Customer–product purchases |
| `Supplier_Product` | Supplier–product links |
| `Employee_Orders_Supplier` | Employee–supplier orders |

---

## 🌐 Pages & Routes

| URL | Page | Features |
|---|---|---|
| `/` | Home | Live stats, feature overview |
| `/products` | Products | Filter by category |
| `/customers` | Customers | View all + register new customer |
| `/employees` | Employees | Staff directory with dept info |
| `/suppliers` | Suppliers | Supplier list with linked products |
| `/sales` | Sales | KPI cards + bar chart |
| `/departments` | Departments | Cards with head and location |

---

## 🔧 Troubleshooting

**Website loads but shows no data**
→ Database connection is failing. Check the terminal for `[DB ERROR]` and verify your password and port in `app.py`.

**`mysql` command not recognized**
→ Add MySQL to PATH:
```
C:\Program Files\MySQL\MySQL Server 8.0\bin
```

**`ERROR 1045` — Access denied**
→ Wrong password. Try logging in via MySQL Workbench to confirm credentials.

**`ERROR 2003` — Can't connect on port 3306**
→ Your MySQL runs on port **3308**. Always use `--port=3308` in terminal and `"port": 3308` in `app.py`.

**`ModuleNotFoundError`**
→ Run `pip install flask mysql-connector-python`

---

## 💡 Tips

- To make MySQL auto-start with Windows: `services.msc` → MySQL80 → Set **Startup type** to **Automatic**
- To verify a database update, run `SELECT * FROM customer;` in MySQL terminal after registering a customer on the website
- The app runs in debug mode (`debug=True`) — any code changes auto-reload the server

---

*© 2026 Metro Superstore · DBMS Lab Project*