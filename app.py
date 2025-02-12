import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from datetime import datetime
import sqlite3
from werkzeug.utils import secure_filename
from functools import wraps
import bcrypt

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Required for flash messages
UPLOAD_FOLDER = 'static/images/products'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


@app.route("/login", methods=['GET', 'POST'])
def login():
    if session.get('is_admin'):
        return redirect(url_for('admin_products'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        db = get_db()
        cursor = db.cursor()

        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()

        if user and bcrypt.checkpw(password.encode('utf-8'), user['password']):
            session['is_admin'] = True
            session['username'] = username
            flash('Successfully logged in!', 'success')
            return redirect(url_for('admin_products'))

        flash('Invalid username or password', 'error')

    return render_template('login.html')


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            flash('Please log in first.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function


@app.route("/logout")
def logout():
    session.clear()
    flash('Successfully logged out!', 'success')
    return redirect(url_for('index'))


@app.route('/admin/products')
@admin_required
def admin_products():
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM products ORDER BY created_at DESC')
    products = cursor.fetchall()
    return render_template('admin/products.html', products=products)


def init_db():
    with sqlite3.connect('store.db') as conn:
        c = conn.cursor()

        # Create users table
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                is_admin BOOLEAN DEFAULT 0
            )
        ''')

        # Create products table
        c.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_name TEXT NOT NULL,
                price REAL NOT NULL,
                amazon_link TEXT,
                image_path TEXT,
                discount REAL DEFAULT 0,
                category TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()


def get_db():
    db = sqlite3.connect('store.db')
    db.row_factory = sqlite3.Row
    return db


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Replace with proper admin check using session
        if not session.get('is_admin'):
            flash('Admin access required')
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function


@app.route("/category/<category>")
def category_products(category):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        SELECT * FROM products 
        WHERE category = ? 
        ORDER BY created_at DESC
    ''', (category,))
    products = cursor.fetchall()
    print(products)
    db.close()
    return render_template("category.html", products=products, category=category)


@app.route("/product/<int:id>")
def product(id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM products WHERE id = ?', (id,))
    product = cursor.fetchone()
    db.close()

    if product:
        return render_template("product.html", product=product)
    return render_template("404.html"), 404


@app.route('/admin/product/add', methods=['GET', 'POST'])
@admin_required
def add_product():
    if request.method == 'POST':
        try:
            product_name = request.form['product_name']
            price = float(request.form['price'])
            category = request.form['category']
            amazon_link = request.form['amazon_link']
            discount = float(request.form.get('discount', 0))

            if 'image' not in request.files:
                flash('No image file provided', 'error')
                return redirect(request.url)

            file = request.files['image']
            if file.filename == '':
                flash('No selected file', 'error')
                return redirect(request.url)

            if not allowed_file(file.filename):
                flash('Invalid file type. Allowed types: PNG, JPG, JPEG, GIF', 'error')
                return redirect(request.url)

            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)

                # ✅ Ensure file paths use forward slashes (Fix applied here)
                file_path = os.path.join('images/products', filename).replace('\\', '/')
                full_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

                file.seek(0, os.SEEK_END)
                file_size = file.tell()
                if file_size > MAX_FILE_SIZE:
                    flash('File is too large. Maximum size is 10MB.', 'error')
                    return redirect(request.url)

                file.seek(0)
                file.save(full_path)

                db = get_db()
                cursor = db.cursor()
                cursor.execute('''
                    INSERT INTO products (product_name, price, amazon_link, image_path, discount, category)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (product_name, price, amazon_link, file_path, discount, category))
                db.commit()

                flash('Product added successfully!', 'success')
                return redirect(url_for('admin_products'))

        except Exception as e:
            flash(f'Error adding product: {str(e)}', 'error')
            return redirect(request.url)

    return render_template('add_product.html')


@app.route('/admin/product/edit/<int:id>', methods=['GET', 'POST'])
# @admin_required
def edit_product(id):
    db = get_db()
    cursor = db.cursor()

    if request.method == 'POST':
        try:
            product_name = request.form['product_name']
            price = float(request.form['price'])
            category = request.form['category']
            amazon_link = request.form['amazon_link']
            discount = float(request.form.get('discount', 0))

            # Handle file upload
            file = request.files.get('image')
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join('images/products', filename)
                full_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

                file.save(full_path)

                cursor.execute('''
                    UPDATE products SET product_name=?, price=?, amazon_link=?, image_path=?, discount=?, category=? WHERE id=?
                ''', (product_name, price, amazon_link, file_path, discount, category, id))
            else:
                cursor.execute('''
                    UPDATE products SET product_name=?, price=?, amazon_link=?, discount=?, category=? WHERE id=?
                ''', (product_name, price, amazon_link, discount, category, id))

            db.commit()
            flash('Product updated successfully!', 'success')
            return redirect(url_for('admin_products'))
        except Exception as e:
            flash(f'Error updating product: {str(e)}', 'error')
            return redirect(request.url)

    cursor.execute('SELECT * FROM products WHERE id = ?', (id,))
    product = cursor.fetchone()
    db.close()

    if not product:
        flash('Product not found', 'error')
        return redirect(url_for('admin_products'))

    return render_template('admin/edit_product.html', product=product)


@app.route('/admin/product/delete/<int:id>', methods=['POST'])
# @admin_required
def delete_product(id):
    try:
        db = get_db()
        cursor = db.cursor()

        # Retrieve the product image path before deleting
        cursor.execute('SELECT image_path FROM products WHERE id = ?', (id,))
        product = cursor.fetchone()

        if product and product['image_path']:
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(product['image_path']))
            if os.path.exists(image_path):
                os.remove(image_path)

        cursor.execute('DELETE FROM products WHERE id = ?', (id,))
        db.commit()
        db.close()

        flash('Product deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting product: {str(e)}', 'error')

    return redirect(url_for('admin_products'))


@app.template_filter('current_year')
def current_year(text):
    return datetime.now().year


@app.context_processor
def utility_processor():
    def format_price(amount, discount=0):
        final_price = amount * (1 - discount / 100)
        return f"${final_price:.2f}"

    return dict(format_price=format_price)


@app.route("/")
def index():
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        SELECT category, GROUP_CONCAT(id) as product_ids 
        FROM products 
        GROUP BY category
    ''')
    categories = cursor.fetchall()
    db.close()
    return render_template("index.html", categories=categories)


@app.route('/redirect_to_amazon/<int:product_id>')
def redirect_to_amazon(product_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT amazon_link FROM products WHERE id = ?', (product_id,))
    product = cursor.fetchone()
    db.close()

    if product and product['amazon_link']:
        return redirect(product['amazon_link'])
    return redirect(url_for('index'))


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


if __name__ == "__main__":
    init_db()  # Initialize database tables
    app.run(debug=True)
