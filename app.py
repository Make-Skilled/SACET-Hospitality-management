from flask import Flask, render_template, request, session, redirect, url_for, flash
import os
from werkzeug.utils import secure_filename
from pymongo import MongoClient
from datetime import datetime, timedelta
from bson import ObjectId
from werkzeug.utils import secure_filename
# from app import app, rooms


api = Flask(__name__)
api.secret_key = 'giri'

# MongoDB setup
cluster = MongoClient("mongodb+srv://kr4785543:1234567890@cluster0.220yz.mongodb.net/")
db = cluster['hotelmanagement']
uregister = db['uregister']
rooms = db['rooms']
bookings = db['bookings']

# Configure upload folder
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
api.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Configure allowed extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
api.config['ALLOWED_EXTENSIONS'] = ALLOWED_EXTENSIONS

# Check if file extension is allowed
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Routes for rendering pages
@api.route("/")
def index():
    return render_template("home.html")

@api.route("/about")
def about():
    return render_template("about.html")

@api.route("/admin")
def admin():
    return render_template("admin.html")

@api.route("/book")
def book():
    return render_template("book.html")

@api.route("/register")
def reguster():
    return render_template("signup.html")

@api.route("/loginpage")
def loginpage():
    return render_template("login.html")


@api.route("/contact")
def contact():
    return render_template("contact.html")


# User Registration
@api.route("/signupaction", methods=['POST'])
def signupact():
    username = request.form.get("name")
    useremail = request.form.get("email")
    password = request.form.get("password")
    confirmpass = request.form.get("confirm-password")
    user = uregister.find_one({"name": username})

    if user:
        return render_template("signup.html", status="Username already exists")
    
    if password != confirmpass:
        return render_template("signup.html", status="Passwords do not match")
    
    uregister.insert_one({"name": username, "email": useremail, "password": password, "confirm-password": confirmpass})
    return render_template("signup.html", status="User registered successfully. Please login.")

# Admin Login
@api.route('/admlog1', methods=['POST'])
def admlog():
    admin_username = "admin"
    admin_password = "1234567890"

    admusername = request.form.get('username')
    adminpassword = request.form.get('password')

    if admin_username == admusername and admin_password == adminpassword:
        session['user'] = admusername  # Set session for admin
        return render_template("adminadddetails.html")
    return render_template("admin.html", status="Invalid credentials")

@api.route("/adminadddetails")
def adminadddetails():
    return render_template("adminadddetails.html")


# Add Room (Admin)
@api.route('/addroom', methods=['POST'])
def add_room():
    try:
        room_number = request.form.get('room_number')
        room_type = request.form.get('room_type')
        capacity = request.form.get('capacity')
        price = request.form.get('price')
        availability = request.form.get('availability')
        
        # Handle the file upload
        if 'room_image' not in request.files:
            return {'error': 'No file uploaded'}, 400
            
        image_file = request.files['room_image']
        if image_file.filename == '':
            return {'error': 'No selected file'}, 400
            
        if image_file and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            # Add timestamp to filename to make it unique
            filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
            # Save the image to the uploads directory
            image_path = os.path.join(api.config['UPLOAD_FOLDER'], filename)
            image_file.save(image_path)
            room_image = filename
        else:
            return {'error': 'Invalid file type'}, 400

        # Insert room details into the database
        room = {
            "room_number": room_number,
            "room_type": room_type,
            "capacity": int(capacity),
            "price": float(price),
            "availability": availability,
            "room_image": room_image
        }

        rooms.insert_one(room)
        flash('Room added successfully!', 'success')
        return redirect(url_for('admin_view_rooms'))
        
    except Exception as e:
        flash(f'Error adding room: {str(e)}', 'error')
        return redirect(url_for('admin_view_rooms'))



# User Login
@api.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get("username")
        password = request.form.get("password")
        
        user = uregister.find_one({"name": username})
        
        if user and user['password'] == password:
            session['user'] = username  # Store the user's login info in session
            return redirect(url_for('user_dashboard'))  # Redirect to the rooms page
        else:
            return render_template("login.html", status="Invalid credentials")  # Pass the error message to the template
    
    return render_template("login.html")

# Logout
@api.route("/logout")
def logout():
    session.pop('user', None)  # Clear the session on logout
    return redirect(url_for('index'))

# View Rooms
@api.route("/view_rooms")
def view_rooms():
    if 'user' not in session:
        return redirect(url_for('login'))  # Redirect to login if the user is not logged in

    # Fetch all the room data from the database
    rooms_data = rooms.find()
    
    return render_template("view_rooms.html", rooms=rooms_data)

@api.route('/book_room', methods=['POST'])
def book_room():
    try:
        # Get the room ID and dates from the form
        room_id = request.form['room_id']
        check_in = datetime.strptime(request.form['check_in'], '%Y-%m-%d')
        check_out = datetime.strptime(request.form['check_out'], '%Y-%m-%d')
        
        # Fetch the room data from the database
        room = rooms.find_one({"_id": ObjectId(room_id)})
        
        if not room:
            return render_template("error.html", message="Room not found.")
        
        # Ensure the user is logged in and has a session username
        if 'user' not in session:
            return render_template("error.html", message="You must be logged in to book a room.")
        
        # Get the session username
        username = session['user']
        
        # Calculate number of days
        days = (check_out - check_in).days
        
        # Calculate the total price for the booking
        total_price = days * room['price']
        
        # Create the booking data including the username
        booking = {
            "room_id": room_id,
            "room_number": room['room_number'],
            "days": days,
            "total_price": total_price,
            "booked_at": datetime.utcnow(),
            "start_date": check_in,
            "end_date": check_out,
            "username": username,
            "status": "pending"  # Default status
        }
        
        # Insert the booking data into the database
        bookings.insert_one(booking)
        
        # Return a success page with the booking details
        return render_template("success.html", 
                            room=room, 
                            days=days, 
                            total_price=total_price, 
                            start_date=check_in, 
                            end_date=check_out)
    
    except Exception as e:
        return render_template("error.html", message=f"An error occurred: {str(e)}")


@api.route("/admin_bookings")
def admin_bookings():
    # Fetch all bookings from the database
    all_bookings = bookings.find()

    # Convert MongoDB cursor to a list of dictionaries and handle missing dates
    bookings_list = []
    for booking in all_bookings:
        booking['_id'] = str(booking['_id'])  # Convert ObjectId to string
        booking['start_date'] = booking.get('start_date')
        booking['end_date'] = booking.get('end_date')
        bookings_list.append(booking)

    # Pass the list to the template
    return render_template("admin_bookings.html", bookings=bookings_list)


@api.route('/update_booking_status/<booking_id>/<status>')
def update_booking_status(booking_id, status):
    try:
        # Validate status
        if status not in ['accepted', 'rejected']:
            flash('Invalid status value')
            return redirect(url_for('admin_bookings'))
        
        # Update the booking status
        bookings.update_one(
            {"_id": ObjectId(booking_id)},
            {"$set": {"status": status}}
        )
        
        # Get the booking details for the message
        booking = bookings.find_one({"_id": ObjectId(booking_id)})
        if booking:
            flash(f'Booking {booking["room_number"]} has been {status}')
        
        return redirect(url_for('admin_bookings'))
    
    except Exception as e:
        flash(f'Error updating booking status: {str(e)}')
        return redirect(url_for('admin_bookings'))


@api.route("/user_dashboard")
def user_dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))  # Redirect to login if the user is not logged in

    username = session['user']

    # Fetch the user's booking details from the database
    user_bookings = bookings.find({"username": username})

    # Prepare the list of bookings with room_number and room_id included
    bookings_with_room_details = []
    for booking in user_bookings:
        room = rooms.find_one({"_id": ObjectId(booking["room_id"])})
        if room:
            booking["room_number"] = room.get("room_number", "N/A")  # Add room_number to the booking
            booking["room_id"] = booking["room_id"]  # Add room_id to the booking
        bookings_with_room_details.append(booking)

    return render_template("user_dashboard.html", bookings=bookings_with_room_details)



@api.route('/admin_update_room/<room_id>', methods=['GET', 'POST'])
def update_room(room_id):
    # Fetch the current room data
    room = rooms.find_one({"_id": ObjectId(room_id)})
    
    if not room:
        flash("Room not found!")
        return redirect(url_for('adminviewrooms'))  # Redirect to the room listing page if room not found

    if request.method == 'POST':
        # Get updated data from the form
        room_number = request.form.get('room_number')
        room_type = request.form.get('room_type')
        capacity = request.form.get('capacity')
        price = request.form.get('price')
        availability = request.form.get('availability')

        # Handle the image file upload (if any)
        image_file = request.files.get('room_image')
        if image_file:
            # Ensure the filename is safe
            filename = secure_filename(image_file.filename)
            # Save the image to the uploads directory
            image_file.save(os.path.join(api.config['UPLOAD_FOLDER'], filename))
            room_image = f"/static/uploads/{filename}"  # Store the path in the database
        else:
            # If no new image is uploaded, keep the existing image path
            room_image = room.get('room_image')

        # Prepare the updated data
        updated_room = {
            "room_number": room_number,
            "room_type": room_type,
            "capacity": int(capacity),
            "price": float(price),
            "availability": availability,
            "room_image": room_image  # Update the room image path
        }

        # Update the room data in the database
        rooms.update_one({"_id": ObjectId(room_id)}, {"$set": updated_room})
        flash("Room details updated successfully!")
        return redirect(url_for('admin_view_rooms'))  # Redirect after successful update

    # If GET request, show the current data in the form
    return render_template('admin_view_rooms.html', room=room)






@api.route("/adminviewrooms")
def admin_view_rooms():
    # Fetch all rooms from the database and convert ObjectId to string
    rooms_data = list(rooms.find())
    
    # Convert _id field to string so it can be used in templates easily
    for room in rooms_data:
        room['_id'] = str(room['_id'])
    
    return render_template("admin_view_rooms.html", rooms=rooms_data)


@api.route("/delete_room/<room_id>", methods=["GET"])
def admin_delete_room(room_id):
    rooms.delete_one({"_id": ObjectId(room_id)})
    return redirect(url_for('admin_view_rooms'))

@api.route("/update_room/<room_id>", methods=["GET", "POST"])
def admin_update_room(room_id):
    room = rooms.find_one({"_id": ObjectId(room_id)})
    if request.method == "POST":
        # Process the form and update the room
        pass
    return render_template("admin_update_room.html", room=room)


@api.route('/admin_login')
def admin_login():
    return render_template('admin.html')


if __name__ == "__main__":
    api.run(port=5500, debug=True)
