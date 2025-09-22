from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask import flash, get_flashed_messages
from werkzeug.security import generate_password_hash, check_password_hash
import matplotlib
matplotlib.use('Agg')
import os
import re
from datetime import datetime, time



app = Flask(__name__, template_folder="templates")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///parking.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'thisisasecretkey' 

db = SQLAlchemy()
db.init_app(app)
app.app_context().push()




class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    reservations = db.relationship('Reservation', backref='user', lazy=True)

class ParkingLot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200))
    address = db.Column(db.String(200))
    pin = db.Column(db.String(6))
    price = db.Column(db.Float)
    total_spots = db.Column(db.Integer)
    spots = db.relationship('ParkingSpot', backref='lot', lazy=True)

class ParkingSpot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lot_id = db.Column(db.Integer, db.ForeignKey('parking_lot.id'))
    status = db.Column(db.String(1), default='Available')
    reservations = db.relationship('Reservation', backref='spot', lazy=True)

class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    spot_id = db.Column(db.Integer, db.ForeignKey('parking_spot.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    # car_name = db.Column(db.String(100))
    # car_number = db.Column(db.String(20))
    car_name = db.Column(db.String(100))       
    car_number = db.Column(db.String(20))       
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime, nullable=True)





with app.app_context():
    try:
        # print("Dropping all tables...")
        # db.drop_all()
        print("Creating all tables...")
        db.create_all()

        if not User.query.filter_by(username='admin').first():
            admin_user = User(username='admin',password=generate_password_hash('admin123'),
                              is_admin=True
                              )
            db.session.add(admin_user)
            db.session.commit()
            print("Admin created.")
    except Exception as e:
        print(f"Error during database initialization: {e}")
        import traceback
        traceback.print_exc()



@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # 1. Username length check
        if len(username) >= 10:
            flash('Username must be less than 10 characters.', 'danger')
            return redirect(request.url)

        # 2. Password strength check
        if not re.search(r'[A-Z]', password):
            flash('Password must contain at least one uppercase letter.', 'danger')
            return redirect(request.url)
        if not re.search(r'[0-9]', password):
            flash('Password must contain at least one number.', 'danger')
            return redirect(request.url)
        
        if not re.search(r'[@]', password):
            flash('Passowrd must contain a @.', 'danger')
            return redirect(request.url)
        


        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists, Please choose another one.', 'danger')
            return redirect(url_for('register'))
        
        hashed = generate_password_hash(password)
        new_user = User(username = username, password = hashed)
        # new_user = User(username=request.form['username'], password=request.form['password'])
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful. You can log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        uname = request.form['username']
        pwd = request.form['password']
        user = User.query.filter_by(username=uname).first()
        if user and check_password_hash(user.password, pwd):
            if user.is_admin:
                session['admin'] = True
                flash('Logged in as admin', 'success')
                return redirect(url_for('admin_dashboard'))
            else:
                session['user_id'] = user.id
                flash('Logged in successfully.', 'success')
                return redirect(url_for('user_dashboard'))
        else:
            flash('Invalid credentials.','danger')
            return redirect(url_for('login'))


    return render_template('login.html')

@app.route('/admin_dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    if not session.get('admin'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        search_term = request.form.get('search')
        lots = ParkingLot.query.filter(ParkingLot.name.ilike(f"%{search_term}%")).all()
    else:
        lots = ParkingLot.query.all()

    return render_template('admin_dashboard.html', lots=lots)


@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for('login'))
 


@app.route('/create_lot', methods=['GET', 'POST'])
def create_lot():
    if not session.get('admin'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form['name']
        address = request.form['address']
        pin = request.form['pin']

        existing_lot = ParkingLot.query.filter_by(name=name, address=address, pin=pin).first()
        if existing_lot:
            flash('A parking lot with same name, address and pin alreaady exists!', 'danger')
            return redirect(url_for('create_lot'))
        
        lot = ParkingLot(name=request.form['name'],
                     address=request.form['address'],
                     pin=request.form['pin'],
                     price=float(request.form['price']),
                     total_spots=int(int(request.form['spots'])/2)
                     )
        db.session.add(lot)
        db.session.commit()

        for _ in range(lot.total_spots):
            spot = ParkingSpot(lot_id=lot.id)
            db.session.add(spot)
        db.session.commit()
        flash("Parking lot created successfully!", "success")
        return redirect(url_for('admin_dashboard'))
    return render_template('create_lot.html')

@app.route('/update_lot/<int:lot_id>', methods=['GET', 'POST'])
def update_lot(lot_id):
    if not session.get('admin'):
        return redirect(url_for('login'))
    
    lot = ParkingLot.query.get_or_404(lot_id)

    if request.method == 'POST':
        lot.name = request.form['name']
        lot.address = request.form['address']
        lot.pin = request.form['pin']
        lot.price = float(request.form['price'])
        db.session.commit()
        flash("Parking lot updated successfully!", "success")
        return redirect(url_for('admin_dashboard'))

    return render_template('update_lot.html', lot=lot)



@app.route('/user_dashboard')
# @login_required
def user_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session.get('user_id')
    lots = ParkingLot.query.all()
    active = Reservation.query.filter_by(user_id=user_id, end_time=None)#.first()
    active_lots = ", ".join(list({lot.spot.lot.name for lot in active}))
    # flash(active_lots)
        
    return render_template('user_dashboard.html', lots = lots, active = active_lots)


@app.route('/reserve_form/<int:lot_id>')
def reserve_form(lot_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('reserve_form.html', lot_id=lot_id)


@app.route('/reserve/<int:lot_id>', methods=['POST'])
def reserve(lot_id):
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    

    now = datetime.now().time()
    start_time = time(9, 0)   # 9:00 AM
    end_time = time(17, 0)    # 5:00 PM

    if not (start_time <= now <= end_time):
        flash("⏰ Reservations are allowed only between 9 AM and 5 PM.", "danger")
        return redirect(url_for('user_dashboard'))

    # Step 1: Check if user already has an active reservation
    active_reservation = Reservation.query.filter_by(user_id=user_id, end_time=None).first()
    if active_reservation:
        flash("You already have an active reservation. You can't book another spot.", "warning")
        return redirect(url_for('user_dashboard'))

    # Step 2: Get car details from form
    car_name = request.form.get('car_name')
    car_number = request.form.get('car_number')

    if not car_name or not car_number:
        flash("Car name and registration number are required.", 'danger')
        return redirect(url_for('user_dashboard'))

    # Step 3: Find available spot in the selected lot
    spot = ParkingSpot.query.filter_by(lot_id=lot_id, status="Available").first()
    if spot:
        spot.status = "Occupied"
        reservation = Reservation(
            spot_id=spot.id,
            user_id=user_id,
            car_name=car_name,
            car_number=car_number,
            start_time=datetime.now()
        )
        db.session.add(reservation)
        db.session.commit()
        flash("Spot reserved successfully!", "success")
    else:
        flash("No available spots in this lot!", "warning")

    return redirect(url_for('user_dashboard'))


@app.route('/vacate_shortcut')
# @login_required
def vacate_shortcut():
    return redirect(url_for('user_reservations'))


@app.route('/vacate/<int:spot_id>')
# @login_required
def vacate(spot_id):
    spot = ParkingSpot.query.get(spot_id)
    if not spot:
        return "Invalid spot."
    
    reservation = Reservation.query.filter_by(spot_id=spot_id, end_time=None).first()
    if reservation:
        reservation.end_time = datetime.now()
    spot.status="Available"
    db.session.commit()
    # return redirect(url_for('user_dashboard'))
    return redirect(url_for('user_reservations'))


@app.route('/admin/reservations')
# @login_required
def admin_reservations():
    if not session.get('admin'):
        return redirect(url_for('login'))
    all_reservations = Reservation.query.order_by(Reservation.end_time.asc()).all()
    return render_template('admin_reservations.html', reservations=all_reservations, now = datetime.now())


@app.route('/user/reservations')
# @login_required
def user_reservations():
    # user_id = current_user.id
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    my_reservations = Reservation.query.filter_by(user_id=user_id).order_by(Reservation.end_time.asc()).all()
    return render_template('user_reservations.html', reservations=my_reservations, now = datetime.now())


@app.route('/admin/users')
def admin_users():
    if not session.get('admin'):
        return redirect(url_for('login'))
    users = User.query.filter_by(is_admin=False).all()
    return render_template('admin_users.html', users=users)


@app.route('/delete_lot/<int:lot_id>')
def delete_lot(lot_id):
    if not session.get('admin'):
        return redirect(url_for('login'))
    lot = ParkingLot.query.get(lot_id)
    if not lot:
        return "Parking Lot not found"
    

    occupied = ParkingSpot.query.filter_by(lot_id=lot_id, status="Occupied").count()
    if occupied > 0:
        flash("Cannot delete lot: some spots are still occupied.",'warning')
        return redirect(url_for('admin_dashboard'))
    
    ParkingSpot.query.filter_by(lot_id=lot_id).delete()
    db.session.delete(lot)
    db.session.commit()
    flash("Parking lot deleted successfully.",'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/release_payment/<int:reservation_id>')
def release_payment(reservation_id):
    
    reservation = Reservation.query.get(reservation_id)

    if not reservation or reservation.end_time or reservation.user_id != session['user_id']:
        flash("Invalid or already released reservation", 'warning')
        return redirect(url_for('user_reservations'))
    
    now = datetime.now()
    duration = now - reservation.start_time
    time_of_reserve = duration.total_seconds()/3600
    # time_of_reserve = round(time_of_reserve, 2)

    price_per_hour = reservation.spot.lot.price
    total_cost = round(time_of_reserve*price_per_hour, 2)

    return render_template('release_payment.html',
                           reservation=reservation,
                           cost = total_cost
                           )


@app.route('/confirm_release/<int:reservation_id>', methods=["POST"])
def confirm_release(reservation_id):
    
    reservation = Reservation.query.get(reservation_id)
    if not reservation or reservation.end_time or reservation.user_id != session['user_id']:
        flash("Invalid reservation", "danger")
        return redirect(url_for('user_reservations'))
    
    reservation.end_time = datetime.now()
    reservation.spot.status = "Available"
    db.session.commit()

    flash("Reservation released after payment!", "success")
    return redirect(url_for('user_reservations'))


@app.route('/admin/summary')
def admin_summary():
    if not session.get('admin'):
        return redirect(url_for('login'))

    lots = ParkingLot.query.all()
    lot_names = []
    reservation_counts = []
    revenues = []

    for lot in lots:
        reservations_released = Reservation.query.join(ParkingSpot)\
            .filter(ParkingSpot.lot_id == lot.id, Reservation.end_time != None).all()
        
        reservations_all = Reservation.query.join(ParkingSpot)\
            .filter(ParkingSpot.lot_id == lot.id).all()

        total_hours = sum([(r.end_time - r.start_time).total_seconds() / 3600 for r in reservations_released])
        total_revenue = round(total_hours * lot.price, 2)

        lot_names.append(lot.name)
        reservation_counts.append(len(reservations_all))
        revenues.append(total_revenue)

    chart_dir = os.path.join('static', 'charts')
    os.makedirs(chart_dir, exist_ok=True)
    import matplotlib.pyplot as plt

    #Reservations
    plt.figure(figsize=(8, 4))
    plt.bar(lot_names, reservation_counts, color='skyblue')
    plt.title('Total Reservations per Lot')
    plt.xlabel('Lot Name')
    plt.ylabel('# Reservations')
    plt.xticks(rotation=45)
    res_chart_path = os.path.join(chart_dir, 'reservations.png')
    plt.tight_layout()
    plt.savefig(res_chart_path)
    plt.close()

    #Revenue
    plt.figure(figsize=(8, 4))
    plt.bar(lot_names, revenues, color='orange')
    plt.title('Total Revenue per Lot')
    plt.xlabel('Lot Name')
    plt.ylabel('Revenue (₹)')
    plt.xticks(rotation=45)
    rev_chart_path = os.path.join(chart_dir, 'revenue.png')
    plt.tight_layout()
    plt.savefig(rev_chart_path)
    plt.close()

    return render_template('admin_summary.html',
                           res_chart='charts/reservations.png',
                           rev_chart='charts/revenue.png')



if __name__ == "__main__":
    print("Starting Vehicle Parking application...")
    try:
        app.run(debug=True)
        print("Flask application is running.")
    except Exception as e:
        print(f"Error running Flask application: {e}")
        import traceback
        traceback.print_exc()