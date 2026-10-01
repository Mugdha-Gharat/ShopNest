from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = "change-this-secret-key"
DB_NAME = "ecommerce.db"

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'customer',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        price REAL NOT NULL,
        category TEXT NOT NULL,
        emoji TEXT DEFAULT '🛍️',
        stock INTEGER NOT NULL DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        total REAL NOT NULL,
        address TEXT NOT NULL,
        payment_method TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Placed',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        price REAL NOT NULL,
        FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
        FOREIGN KEY (product_id) REFERENCES products(id)
    );
    """)

    admin = conn.execute("SELECT id FROM users WHERE email=?", ("admin@shopnest.com",)).fetchone()
    if not admin:
        conn.execute(
            "INSERT INTO users(name,email,password,role) VALUES(?,?,?,?)",
            ("ShopNest Admin", "admin@shopnest.com", generate_password_hash("admin123"), "admin")
        )

    count = conn.execute("SELECT COUNT(*) AS c FROM products").fetchone()["c"]
    if count == 0:
        products = [
            ("Wireless Headphones", "Comfortable Bluetooth headphones with deep bass.", 2499, "Electronics", "🎧", 20),
            ("Smart Watch", "Fitness tracking, notifications and heart-rate monitoring.", 3299, "Electronics", "⌚", 15),
            ("Running Shoes", "Lightweight everyday running shoes.", 1899, "Fashion", "👟", 25),
            ("Classic Backpack", "Durable backpack for college and travel.", 1299, "Fashion", "🎒", 30),
            ("Coffee Maker", "Compact coffee maker for home and office.", 2199, "Home", "☕", 12),
            ("Desk Lamp", "LED desk lamp with adjustable brightness.", 899, "Home", "💡", 40),
            ("Skincare Kit", "Daily cleanser, moisturizer and sunscreen set.", 1599, "Beauty", "🧴", 18),
            ("Bluetooth Speaker", "Portable speaker with powerful sound.", 1799, "Electronics", "🔊", 22),
        ]
        conn.executemany(
            "INSERT INTO products(name,description,price,category,emoji,stock) VALUES(?,?,?,?,?,?)",
            products
        )
    conn.commit()
    conn.close()

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login to continue.", "warning")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped

def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get("role") != "admin":
            flash("Admin access required.", "danger")
            return redirect(url_for("index"))
        return view(*args, **kwargs)
    return wrapped

def cart_details():
    cart = session.get("cart", {})
    if not cart:
        return [], 0
    conn = get_db()
    ids = [int(i) for i in cart.keys()]
    placeholders = ",".join(["?"] * len(ids))
    rows = conn.execute(f"SELECT * FROM products WHERE id IN ({placeholders})", ids).fetchall()
    conn.close()
    items, total = [], 0
    for row in rows:
        qty = int(cart.get(str(row["id"]), 0))
        if qty <= 0:
            continue
        subtotal = row["price"] * qty
        items.append({"product": row, "quantity": qty, "subtotal": subtotal})
        total += subtotal
    return items, total

@app.context_processor
def inject_globals():
    items, total = cart_details()
    return {"cart_count": sum(i["quantity"] for i in items), "cart_total": total}

@app.route("/")
def index():
    conn = get_db()
    category = request.args.get("category", "")
    search = request.args.get("search", "").strip()
    query = "SELECT * FROM products WHERE 1=1"
    params = []
    if category:
        query += " AND category=?"
        params.append(category)
    if search:
        query += " AND (name LIKE ? OR description LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])
    query += " ORDER BY id DESC"
    products = conn.execute(query, params).fetchall()
    categories = conn.execute("SELECT DISTINCT category FROM products ORDER BY category").fetchall()
    conn.close()
    return render_template("index.html", products=products, categories=categories, selected_category=category, search=search)

@app.route("/product/<int:product_id>")
def product(product_id):
    conn = get_db()
    item = conn.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
    conn.close()
    if not item:
        flash("Product not found.", "danger")
        return redirect(url_for("index"))
    return render_template("product.html", product=item)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        if not name or not email or len(password) < 6:
            flash("Enter valid details. Password must be at least 6 characters.", "danger")
            return render_template("register.html")
        conn = get_db()
        try:
            conn.execute(
                "INSERT INTO users(name,email,password) VALUES(?,?,?)",
                (name, email, generate_password_hash(password))
            )
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            flash("Email is already registered.", "danger")
            return render_template("register.html")
        conn.close()
        flash("Registration successful. Please login.", "success")
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    next_url = request.args.get("next", "")
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        conn.close()
        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["role"] = user["role"]
            flash(f"Welcome, {user['name']}!", "success")
            return redirect(next_url or url_for("index"))
        flash("Invalid email or password.", "danger")
    return render_template("login.html", next_url=next_url)

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))

@app.route("/add-to-cart/<int:product_id>", methods=["POST"])
def add_to_cart(product_id):
    conn = get_db()
    item = conn.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
    conn.close()
    if not item:
        flash("Product not found.", "danger")
        return redirect(url_for("index"))
    if item["stock"] <= 0:
        flash("This product is out of stock.", "warning")
        return redirect(request.referrer or url_for("index"))
    cart = session.get("cart", {})
    key = str(product_id)
    new_qty = int(cart.get(key, 0)) + int(request.form.get("quantity", 1))
    cart[key] = min(new_qty, item["stock"])
    session["cart"] = cart
    flash(f"{item['name']} added to cart.", "success")
    return redirect(request.referrer or url_for("index"))

@app.route("/cart")
def cart():
    items, total = cart_details()
    return render_template("cart.html", items=items, total=total)

@app.route("/update-cart", methods=["POST"])
def update_cart():
    cart = session.get("cart", {})
    conn = get_db()
    for key, value in request.form.items():
        if key.startswith("qty_"):
            pid = key.replace("qty_", "")
            try:
                qty = max(0, int(value))
            except ValueError:
                qty = 1
            row = conn.execute("SELECT stock FROM products WHERE id=?", (pid,)).fetchone()
            if row:
                qty = min(qty, row["stock"])
                if qty == 0:
                    cart.pop(pid, None)
                else:
                    cart[pid] = qty
    conn.close()
    session["cart"] = cart
    flash("Cart updated.", "success")
    return redirect(url_for("cart"))

@app.route("/remove-from-cart/<int:product_id>", methods=["POST"])
def remove_from_cart(product_id):
    cart = session.get("cart", {})
    cart.pop(str(product_id), None)
    session["cart"] = cart
    flash("Item removed from cart.", "success")
    return redirect(url_for("cart"))

@app.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    items, total = cart_details()
    if not items:
        flash("Your cart is empty.", "warning")
        return redirect(url_for("index"))
    if request.method == "POST":
        address = request.form["address"].strip()
        payment = request.form["payment_method"]
        if not address:
            flash("Delivery address is required.", "danger")
            return render_template("checkout.html", items=items, total=total)
        conn = get_db()
        try:
            for item in items:
                current = conn.execute("SELECT stock FROM products WHERE id=?", (item["product"]["id"],)).fetchone()
                if not current or current["stock"] < item["quantity"]:
                    raise ValueError(f"Insufficient stock for {item['product']['name']}.")
            cur = conn.execute(
                "INSERT INTO orders(user_id,total,address,payment_method) VALUES(?,?,?,?,?)",
                (session["user_id"], total, address, payment)
            )
            order_id = cur.lastrowid
            for item in items:
                conn.execute(
                    "INSERT INTO order_items(order_id,product_id,quantity,price) VALUES(?,?,?,?)",
                    (order_id, item["product"]["id"], item["quantity"], item["product"]["price"])
                )
                conn.execute(
                    "UPDATE products SET stock=stock-? WHERE id=?",
                    (item["quantity"], item["product"]["id"])
                )
            conn.commit()
        except ValueError as e:
            conn.rollback()
            conn.close()
            flash(str(e), "danger")
            return redirect(url_for("cart"))
        conn.close()
        session["cart"] = {}
        return redirect(url_for("order_success", order_id=order_id))
    return render_template("checkout.html", items=items, total=total)

@app.route("/order-success/<int:order_id>")
@login_required
def order_success(order_id):
    conn = get_db()
    order = conn.execute("SELECT * FROM orders WHERE id=? AND user_id=?", (order_id, session["user_id"])).fetchone()
    conn.close()
    if not order:
        return redirect(url_for("orders"))
    return render_template("order_success.html", order=order)

@app.route("/orders")
@login_required
def orders():
    conn = get_db()
    orders = conn.execute("SELECT * FROM orders WHERE user_id=? ORDER BY id DESC", (session["user_id"],)).fetchall()
    conn.close()
    return render_template("orders.html", orders=orders)

@app.route("/admin")
@admin_required
def admin():
    conn = get_db()
    products = conn.execute("SELECT * FROM products ORDER BY id DESC").fetchall()
    orders = conn.execute("""
        SELECT orders.*, users.name AS customer
        FROM orders JOIN users ON orders.user_id=users.id
        ORDER BY orders.id DESC
    """).fetchall()
    conn.close()
    return render_template("admin.html", products=products, orders=orders)

@app.route("/admin/product/add", methods=["POST"])
@admin_required
def add_product():
    data = request.form
    conn = get_db()
    conn.execute(
        "INSERT INTO products(name,description,price,category,emoji,stock) VALUES(?,?,?,?,?,?)",
        (data["name"], data["description"], float(data["price"]), data["category"], data.get("emoji","🛍️"), int(data["stock"]))
    )
    conn.commit()
    conn.close()
    flash("Product added.", "success")
    return redirect(url_for("admin"))

@app.route("/admin/product/delete/<int:product_id>", methods=["POST"])
@admin_required
def delete_product(product_id):
    conn = get_db()
    conn.execute("DELETE FROM products WHERE id=?", (product_id,))
    conn.commit()
    conn.close()
    flash("Product deleted.", "success")
    return redirect(url_for("admin"))

@app.route("/admin/order/<int:order_id>/status", methods=["POST"])
@admin_required
def update_order_status(order_id):
    status = request.form["status"]
    allowed = ["Placed", "Processing", "Shipped", "Out for Delivery", "Delivered", "Cancelled"]
    if status not in allowed:
        flash("Invalid status.", "danger")
        return redirect(url_for("admin"))
    conn = get_db()
    conn.execute("UPDATE orders SET status=? WHERE id=?", (status, order_id))
    conn.commit()
    conn.close()
    flash("Order status updated.", "success")
    return redirect(url_for("admin"))

@app.route("/api/products")
def api_products():
    conn = get_db()
    rows = conn.execute("SELECT id,name,price,category,stock FROM products").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
