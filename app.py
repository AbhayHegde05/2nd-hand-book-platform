import os
from datetime import datetime, timedelta
from flask import Flask, render_template, redirect, url_for, request, flash, session
from config import Config
from models import db, User, Book, Review, Discount, Transaction, CartItem
from flask_bcrypt import Bcrypt
from werkzeug.utils import secure_filename
from flask_migrate import Migrate

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)
bcrypt = Bcrypt(app)

# Set up Flask-Migrate
migrate = Migrate(app, db)

# Configure image upload folder and allowed extensions.
UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static', 'images')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def create_tables():
    db.create_all()

# ----------------------
# Bonus Point Conversion Config
# ----------------------
BONUS_POINTS_PER_SALE = 10    # Award 10 bonus points per sale
CONVERSION_RATE = 20          # 20 bonus points = Rs. 1

# ----------------------
# New Homepage, Profile, and Transaction Cancellation Routes
# ----------------------
@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("home.html")

@app.route("/profile")
def profile():
    if "user_id" not in session:
        return redirect(url_for("login"))
    user = User.query.get_or_404(session["user_id"])
    uploaded_books = Book.query.filter_by(uploader_id=user.id).all()
    return render_template("profile.html", user=user, uploaded_books=uploaded_books, current_time=datetime.utcnow())

@app.route("/cancel_transaction/<int:transaction_id>", methods=["POST"])
def cancel_transaction(transaction_id):
    if "user_id" not in session:
        flash("Please log in.", "danger")
        return redirect(url_for("login"))
    transaction = Transaction.query.get_or_404(transaction_id)
    if transaction.user_id != session["user_id"]:
        flash("You are not authorized to cancel this transaction.", "danger")
        return redirect(url_for("dashboard"))
    if (datetime.utcnow() - transaction.transaction_date) > timedelta(days=5):
        flash("Cancellation period has expired.", "danger")
        return redirect(url_for("dashboard"))
    if transaction.payment_status == "Cancelled":
        flash("Transaction is already cancelled.", "info")
        return redirect(url_for("dashboard"))
    transaction.payment_status = "Cancelled"
    db.session.commit()
    flash("Transaction cancelled and amount refunded.", "success")
    return redirect(url_for("dashboard"))

# ----------------------
# Authentication Routes
# ----------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]
        hashed_pw = bcrypt.generate_password_hash(password).decode("utf-8")
        user = User(username=username, email=email, password=hashed_pw)
        db.session.add(user)
        db.session.commit()
        flash("Registration Successful. Please log in.", "success")
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password, password):
            session["user_id"] = user.id
            flash("Login Successful!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Login Unsuccessful. Check email and password.", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("user_id", None)
    flash("Logged out successfully.", "info")
    return redirect(url_for("login"))

# ----------------------
# Main Application Routes
# ----------------------
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    books = Book.query.all()
    return render_template("dashboard.html", books=books)

@app.route("/book/<int:book_id>")
def book_details(book_id):
    book = Book.query.get_or_404(book_id)
    reviews = Review.query.filter_by(book_id=book_id).all()
    effective_price = None
    if book.discount:
        now = datetime.utcnow().date()
        if book.discount.valid_from and book.discount.valid_to:
            if book.discount.valid_from <= now <= book.discount.valid_to:
                effective_price = book.price * (1 - book.discount.discount_percent / 100)
        else:
            effective_price = book.price * (1 - book.discount.discount_percent / 100)
    return render_template("book_details.html", book=book, reviews=reviews, effective_price=effective_price)

@app.route("/add_to_cart/<int:book_id>")
def add_to_cart(book_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    book = Book.query.get_or_404(book_id)
    if book.uploader_id == session["user_id"]:
        flash("You cannot add your own book to the cart.", "danger")
        return redirect(url_for("dashboard"))
    existing_item = CartItem.query.filter_by(user_id=session["user_id"], book_id=book_id).first()
    if existing_item:
        existing_item.quantity += 1
    else:
        cart_item = CartItem(user_id=session["user_id"], book_id=book_id, quantity=1)
        db.session.add(cart_item)
    db.session.commit()
    flash("Book added to cart.", "success")
    return redirect(url_for("dashboard"))

@app.route("/cart")
def cart():
    if "user_id" not in session:
        return redirect(url_for("login"))
    cart_items = CartItem.query.filter_by(user_id=session["user_id"]).all()
    total = sum(item.book.price * item.quantity for item in cart_items)
    return render_template("cart.html", cart_items=cart_items, total=total)

@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    if "user_id" not in session:
        return redirect(url_for("login"))
    if request.method == "POST":
        flash("Payment Successful! Transaction Completed.", "success")
        CartItem.query.filter_by(user_id=session["user_id"]).delete()
        db.session.commit()
        return redirect(url_for("dashboard"))
    return render_template("checkout.html")

# ----------------------
# Book Management Routes
# ----------------------
@app.route("/add_book", methods=["GET", "POST"])
def add_book():
    if "user_id" not in session:
        flash("You must be logged in to add a new book.", "danger")
        return redirect(url_for("login"))
    if request.method == "POST":
        title = request.form["title"]
        author = request.form["author"]
        publication_date_str = request.form.get("publication_date")
        if publication_date_str:
            try:
                publication_date = datetime.strptime(publication_date_str, '%Y-%m-%d').date()
            except ValueError:
                publication_date = None
        else:
            publication_date = None
        isbn = request.form.get("isbn", "")
        description = request.form.get("description", "")
        price = request.form.get("price", 0)
        try:
            price = float(price)
        except ValueError:
            price = 0.0
        is_rentable = True if request.form.get("is_rentable", "no") == "yes" else False
        discount_percentage = request.form.get("discount_percentage", "")
        discount_id = None
        if discount_percentage:
            try:
                discount_percent = float(discount_percentage)
                valid_from = datetime.utcnow().date()
                valid_to = valid_from + timedelta(days=30)
                new_discount = Discount(
                    discount_percent=discount_percent,
                    valid_from=valid_from,
                    valid_to=valid_to,
                    description=f"Discount on {title}"
                )
                db.session.add(new_discount)
                db.session.flush()
                discount_id = new_discount.id
            except ValueError:
                discount_id = None
        file = request.files.get("image")
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(file_path)
            image_url = url_for("static", filename="images/" + filename)
        else:
            image_url = url_for("static", filename="images/default-book.jpg")
        stock = request.form.get("stock", 1)
        try:
            stock = int(stock)
        except ValueError:
            stock = 1
        new_book = Book(
            title=title,
            author=author,
            publication_date=publication_date,
            isbn=isbn,
            description=description,
            price=price,
            is_rentable=is_rentable,
            image_url=image_url,
            stock=stock,
            uploader_id=session["user_id"],
            discount_id=discount_id
        )
        db.session.add(new_book)
        db.session.commit()
        flash("New book added successfully!", "success")
        return redirect(url_for("dashboard"))
    return render_template("add_book.html")

@app.route("/edit_book/<int:book_id>", methods=["GET", "POST"])
def edit_book(book_id):
    if "user_id" not in session:
        flash("Please log in to continue.", "danger")
        return redirect(url_for("login"))
    book = Book.query.get_or_404(book_id)
    if book.uploader_id != session["user_id"]:
        flash("You are not authorized to edit this book.", "danger")
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        book.title = request.form["title"]
        book.author = request.form["author"]
        publication_date_str = request.form.get("publication_date")
        if publication_date_str:
            try:
                book.publication_date = datetime.strptime(publication_date_str, '%Y-%m-%d').date()
            except ValueError:
                book.publication_date = None
        else:
            book.publication_date = None
        book.isbn = request.form.get("isbn", "")
        book.description = request.form.get("description", "")
        price = request.form.get("price", 0)
        try:
            book.price = float(price)
        except ValueError:
            book.price = 0.0
        book.is_rentable = True if request.form.get("is_rentable", "no") == "yes" else False
        discount_percentage = request.form.get("discount_percentage", "")
        if discount_percentage:
            try:
                discount_percent = float(discount_percentage)
                valid_from = datetime.utcnow().date()
                valid_to = valid_from + timedelta(days=30)
                if book.discount:
                    book.discount.discount_percent = discount_percent
                    book.discount.valid_from = valid_from
                    book.discount.valid_to = valid_to
                else:
                    new_discount = Discount(
                        discount_percent=discount_percent,
                        valid_from=valid_from,
                        valid_to=valid_to,
                        description=f"Discount on {book.title}"
                    )
                    db.session.add(new_discount)
                    db.session.flush()
                    book.discount_id = new_discount.id
            except ValueError:
                pass
        file = request.files.get("image")
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(file_path)
            book.image_url = url_for("static", filename="images/" + filename)
        stock = request.form.get("stock", 1)
        try:
            book.stock = int(stock)
        except ValueError:
            book.stock = 1
        db.session.commit()
        flash("Book updated successfully!", "success")
        return redirect(url_for("book_details", book_id=book.id))
    return render_template("edit_book.html", book=book)

@app.route("/delete_book/<int:book_id>", methods=["POST"])
def delete_book(book_id):
    if "user_id" not in session:
        flash("Please log in to continue.", "danger")
        return redirect(url_for("login"))
    book = Book.query.get_or_404(book_id)
    if book.uploader_id != session["user_id"]:
        flash("You are not authorized to delete this book.", "danger")
        return redirect(url_for("dashboard"))
    db.session.delete(book)
    db.session.commit()
    flash("Book deleted successfully!", "success")
    return redirect(url_for("dashboard"))

@app.route("/buy/<int:book_id>", methods=["GET", "POST"])
def buy_book(book_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    book = Book.query.get_or_404(book_id)
    if book.uploader_id == session["user_id"]:
        flash("You cannot buy your own book.", "danger")
        return redirect(url_for("dashboard"))
    effective_price = book.price
    if book.discount:
        now = datetime.utcnow().date()
        if book.discount.valid_from and book.discount.valid_to:
            if book.discount.valid_from <= now <= book.discount.valid_to:
                effective_price = book.price * (1 - book.discount.discount_percent / 100)
        else:
            effective_price = book.price * (1 - book.discount.discount_percent / 100)
    if request.method == "POST":
        transaction = Transaction(
            user_id=session["user_id"],
            book_id=book.id,
            transaction_type="buy",
            price=effective_price,
            payment_status="Completed"
        )
        db.session.add(transaction)
        if book.stock > 0:
            book.stock -= 1
        # Award bonus points to seller if applicable.
        if book.uploader_id and book.uploader_id != session["user_id"]:
            seller = User.query.get(book.uploader_id)
            if seller:
                if seller.bonus_points is None:
                    seller.bonus_points = 0
                seller.bonus_points += BONUS_POINTS_PER_SALE
        db.session.commit()
        flash("Purchase successful!", "success")
        return redirect(url_for("dashboard"))
    return render_template("buy_book.html", book=book, effective_price=effective_price)

@app.route("/book/<int:book_id>/add_review", methods=["POST"])
def add_review(book_id):
    if "user_id" not in session:
        flash("You must be logged in to post a review.", "danger")
        return redirect(url_for("login"))
    rating = request.form.get("rating")
    comment = request.form.get("comment", "")
    try:
        rating_int = int(rating)
    except (ValueError, TypeError):
        flash("Invalid rating.", "danger")
        return redirect(url_for("book_details", book_id=book_id))
    if not (1 <= rating_int <= 5):
        flash("Rating must be between 1 and 5.", "danger")
        return redirect(url_for("book_details", book_id=book_id))
    new_review = Review(user_id=session["user_id"], book_id=book_id, rating=rating_int, comment=comment)
    db.session.add(new_review)
    db.session.commit()
    flash("Review added successfully!", "success")
    return redirect(url_for("book_details", book_id=book_id))

# ----------------------
# New Route: Convert Bonus Points to Cash
# ----------------------
@app.route("/convert_points", methods=["GET", "POST"])
def convert_points():
    if "user_id" not in session:
        flash("Please log in to continue.", "danger")
        return redirect(url_for("login"))
    user = User.query.get_or_404(session["user_id"])
    if request.method == "POST":
        try:
            points_to_convert = int(request.form.get("points"))
        except (ValueError, TypeError):
            flash("Please enter a valid number.", "danger")
            return redirect(url_for("convert_points"))
        if points_to_convert <= 0:
            flash("Enter a positive number of points.", "danger")
            return redirect(url_for("convert_points"))
        if points_to_convert > user.bonus_points:
            flash("Insufficient bonus points.", "danger")
            return redirect(url_for("convert_points"))
        cash_amount = points_to_convert / CONVERSION_RATE  # e.g., 20 points = Rs. 1
        user.bonus_points -= points_to_convert
        db.session.commit()
        flash(f"Converted {points_to_convert} points into Rs. {cash_amount:.2f}.", "success")
        return redirect(url_for("profile"))
    return render_template("convert_points.html", bonus_points=user.bonus_points, CONVERSION_RATE=CONVERSION_RATE)

if __name__ == "__main__":
    BONUS_POINTS_PER_SALE = 10  # Award 10 bonus points per sale.
    CONVERSION_RATE = 20        # 20 bonus points = Rs. 1.
    with app.app_context():
        create_tables()
    app.run(debug=True)
