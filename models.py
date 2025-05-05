from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    address = db.Column(db.String(200))
    phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    bonus_points = db.Column(db.Integer, default=0)  # NEW: Bonus points earned by the seller

    # Relationships
    reviews = db.relationship("Review", backref="reviewer", lazy=True)
    transactions = db.relationship("Transaction", backref="buyer", lazy=True)
    cart_items = db.relationship("CartItem", backref="user", lazy=True)
    uploads = db.relationship("Book", backref="uploader", lazy=True)

class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(150), nullable=False)
    publication_date = db.Column(db.Date)
    isbn = db.Column(db.String(20), unique=True)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    is_rentable = db.Column(db.Boolean, default=True)
    image_url = db.Column(db.String(300))
    stock = db.Column(db.Integer, default=1)
    # The uploader_id represents the user who uploaded the book.
    uploader_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    discount_id = db.Column(db.Integer, db.ForeignKey("discount.id"), nullable=True)

    # Relationships
    reviews = db.relationship("Review", backref="book", lazy=True)
    transactions = db.relationship("Transaction", backref="book_details", lazy=True)
    cart_items = db.relationship("CartItem", backref="book", lazy=True)

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey("book.id"), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text)
    review_date = db.Column(db.DateTime, default=datetime.utcnow)

class Discount(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(150))
    discount_percent = db.Column(db.Float, nullable=False)
    valid_from = db.Column(db.Date)
    valid_to = db.Column(db.Date)
    books = db.relationship("Book", backref="discount", lazy=True)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey("book.id"), nullable=False)
    transaction_date = db.Column(db.DateTime, default=datetime.utcnow)
    transaction_type = db.Column(db.String(20))  # e.g., 'buy' or 'rent'
    price = db.Column(db.Float, nullable=False)
    rent_start_date = db.Column(db.DateTime)
    rent_end_date = db.Column(db.DateTime)
    return_date = db.Column(db.Date)
    payment_status = db.Column(db.String(20), default="Pending")

class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey("book.id"), nullable=False)
    quantity = db.Column(db.Integer, default=1)
