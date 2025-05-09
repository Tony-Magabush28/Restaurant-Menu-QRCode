import os
from dotenv import load_dotenv  # Import this for environment variable loading
import qrcode
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_migrate import Migrate

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = 'secretkey123'  # Needed for flash messages and session
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///orders.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Ensure the folder exists for storing the QR codes
QR_CODE_FOLDER = 'static/qrcodes'
if not os.path.exists(QR_CODE_FOLDER):
    os.makedirs(QR_CODE_FOLDER)

# Define the Order model
class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    table_number = db.Column(db.Integer, nullable=False)
    items = db.Column(db.String(500))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    served = db.Column(db.Boolean, default=False)

# Create the database tables
with app.app_context():
    db.create_all()

# Helper function to create an order
def create_order(table_number, order_items):
    if not order_items:
        order_items = "No items"
    new_order = Order(table_number=table_number, items=order_items)
    db.session.add(new_order)
    db.session.commit()

# Helper function to generate QR codes for each table
def generate_qr_code(table_number):
    qr_image_path = os.path.join(QR_CODE_FOLDER, f'table_{table_number}_qrcode.png')
    if not os.path.exists(qr_image_path):
        data = f'https://restaurant-menu-qrcode.onrender.com/table/{table_number}'
        qr = qrcode.make(data)
        qr.save(qr_image_path)

@app.route('/')
def home():
    for table_number in range(1, 6):
        generate_qr_code(table_number)
    return render_template('home.html')

@app.route('/table/<int:table_number>', methods=['GET', 'POST'])
def table_menu(table_number):
    if request.method == 'POST':
        order_items = request.form.get('items')
        create_order(table_number, order_items)
        flash('Order placed successfully!', 'success')
        return redirect(url_for('thank_you', table_number=table_number))
    return render_template('menu.html', table_number=table_number)

@app.route('/thank_you/<int:table_number>')
def thank_you(table_number):
    return render_template('thank_you.html', table_number=table_number)

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Get the admin credentials from environment variables
        admin_username = os.getenv('ADMIN_USERNAME')
        admin_password = os.getenv('ADMIN_PASSWORD')

        if username == admin_username and password == admin_password:
            session['admin_logged_in'] = True
            flash('Logged in successfully.', 'success')
            return redirect(url_for('admin'))
        else:
            flash('Invalid credentials.', 'danger')
    return render_template('admin_login.html')

@app.route('/admin_logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    flash('Logged out successfully.', 'info')
    return redirect(url_for('home'))

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if not session.get('admin_logged_in'):
        flash('Please log in to access the admin panel.', 'warning')
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        search_table = request.form.get('search_table')
        orders = Order.query.filter_by(table_number=search_table).order_by(Order.timestamp.desc()).all()
    else:
        orders = Order.query.order_by(Order.timestamp.desc()).all()
    return render_template('admin.html', orders=orders)

@app.route('/delete_order/<int:order_id>', methods=['POST'])
def delete_order(order_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    order_to_delete = Order.query.get_or_404(order_id)
    db.session.delete(order_to_delete)
    db.session.commit()
    flash('Order deleted successfully!', 'info')
    return redirect(url_for('admin'))

@app.route('/mark_served/<int:order_id>', methods=['POST'])
def mark_served(order_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    order = Order.query.get_or_404(order_id)
    order.served = True
    db.session.commit()
    flash('Order marked as served!', 'success')
    return redirect(url_for('admin'))

@app.route('/qrcode/<int:table_number>')
def serve_qrcode(table_number):
    qr_image_path = os.path.join(QR_CODE_FOLDER, f'table_{table_number}_qrcode.png')
    if os.path.exists(qr_image_path):
        return send_file(qr_image_path)
    else:
        return "QR code not found", 404

if __name__ == '__main__':
    app.run(debug=True)
