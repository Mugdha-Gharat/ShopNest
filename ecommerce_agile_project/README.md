# ShopNest - E-Commerce Web Application

A simple college-project e-commerce website built with:

- HTML
- CSS
- JavaScript
- Python Flask
- SQLite SQL database
- VS Code
- GitHub

## Features

- Customer registration and login
- Product listing and search
- Category filtering
- Product details
- Shopping cart
- Quantity update/remove
- Checkout
- Simulated payment selection
- Order history
- Admin login
- Admin product management
- Admin order status management
- REST-style `/api/products` endpoint

## Run in VS Code

### 1. Open the project folder

Open `ecommerce_agile_project` in VS Code.

### 2. Create a virtual environment

Windows PowerShell:

```powershell
py -m venv venv
.\venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, use Command Prompt:

```cmd
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the application

```bash
python app.py
```

### 5. Open in browser

Go to:

http://127.0.0.1:5000

The SQLite database `ecommerce.db` is automatically created the first time the application starts.

## Admin Login

Email:

```text
admin@shopnest.com
```

Password:

```text
admin123
```

After login, open:

```text
http://127.0.0.1:5000/admin
```

## Customer

Use the Register page to create a customer account.

## Project structure

```text
ecommerce_agile_project/
│
├── app.py
├── requirements.txt
├── README.md
├── ecommerce.sql
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── product.html
│   ├── login.html
│   ├── register.html
│   ├── cart.html
│   ├── checkout.html
│   ├── order_success.html
│   ├── orders.html
│   └── admin.html
│
└── static/
    ├── style.css
    └── js/
        └── script.js
```

## Note

The payment page is a **college-project simulation**. It does not process real money or connect to a payment gateway.
