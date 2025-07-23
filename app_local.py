#!/usr/bin/env python3
"""
Movie Magic - Smart Movie Ticket Booking System
A simple Flask web server to serve the HTML templates
"""

from flask import Flask, render_template, send_from_directory, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from flask import jsonify
from pymongo import MongoClient
import boto3
import uuid
import os

# ------------------- Initialization ------------------- #
app = Flask(__name__)
app.secret_key = 'your_static_secret_key_here'

# MongoDB Setup
client = MongoClient("mongodb://localhost:27017/")
db = client["mydatabase"]
collection = db["users"]
movies_collection = db["movies"]
bookings_collection = db["bookings"]
users_collection = db.users

# AWS SNS and DynamoDB Configuration
AWS_REGION = os.environ.get('AWS_REGION', 'ap=south-1')
SNS_TOPIC_ARN = 'arn:aws:sns:ap-south-1:605134430972:MovieMagicNotification'

try:
    sns = boto3.client('sns', region_name=AWS_REGION)
    dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
    users_table = dynamodb.Table(os.environ.get('USER_TABLE_NAME', 'MovieMagicUsers'))
    booking_table = dynamodb.Table(os.environ.get('BOOKING_TABLE_NAME', 'MovieMagicBookings'))
except Exception as e:
    print("⚠️ AWS Services unavailable:", e)
    sns = None
    users_table = None
    booking_table = None

# ------------------- Helper Functions ------------------- #
def send_notification(booking, sns, topic_arn, email_subject, email_message):
    if not sns or not topic_arn:
        print("SNS or Topic ARN is not configured.")
        return False
    try:
        user_email = booking['booked_by']
        print(f"Attempting to send notification to {user_email} via SNS topic {topic_arn}")
        response = sns.publish(
            TopicArn=topic_arn,
            Subject=email_subject,
            Message=email_message,
            MessageAttributes={
                'email': {
                    'DataType': 'String',
                    'StringValue': user_email
                }
            }
        )
        print("✅ SNS publish response:", response)
        return True
    except Exception as e:
        print(f"❌ Error sending booking confirmation: {str(e)}")
        return False

def get_movie_by_id(movie_id):
    try:
        return movies_collection.find_one({"id": str(movie_id)})
    except Exception as e:
        print(f"Error retrieving movie with id {movie_id}: {e}")
        return None
@app.route('/')
def index():  
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit():
    name = request.form['name']
    email = request.form['email']
    collection.insert_one({'name': name, 'email': email})
    return render_template('success.html', name=name)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        if email == 'saikumar@gmail.com' and password == 'password':
            session['user'] = {'email': email, 'name': 'saikumar'}
            return redirect(url_for('index'))
        else:
            return "Invalid credentials"
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']
        existing_user = users_collection.find_one({'email': email})
        if existing_user:
            flash('Email already exists. Please log in.', 'error')
            return redirect(url_for('login'))
        hashed_password = generate_password_hash(password)
        users_collection.insert_one({
            'name': name,
            'email': email,
            'phone': phone,
            'password': hashed_password
        })

        flash('Signup successful! You can now log in.', 'success')
        return redirect(url_for('login'))

    return render_template('signup.html')  
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))

@app.route('/registration')
def registration():
    return render_template('registration.html')

@app.route('/dashboard')
def dashboard():
    user = session.get('user')
    return render_template('dashboard.html', user=user)

@app.route("/movie_details")
def movie_details():
    movie_id = request.args.get("id")  # leave as string
    if not movie_id:
        return "Movie ID not provided", 400
    print(f"🔍 Fetching movie with id = {movie_id}")  
    try:
        movie = get_movie_by_id(movie_id)
        if not movie:
            print(f"❌ Movie with id {movie_id} not found in DB")
            return f"Movie with id {movie_id} not found in DB", 404
        return render_template("movie_details.html", movie=movie)
    except Exception as e:
        print(f"❌ Error fetching movie from DB: {e}")
        return "Internal Server Error", 500

@app.route('/movies')
def movies():
    movies = list(movies_collection.find())
    return render_template('movies.html', movies=movies)

@app.route('/api/movie')
def api_movie():
    movie_id = request.args.get('id')
    movie = get_movie_by_id(movie_id)
    if movie:
        movie['_id'] = str(movie['_id'])  
        return jsonify(movie)
    return jsonify({'error': 'Movie not found'}), 404

@app.route('/seat_selection')
def seat_selection():
    movie_id = request.args.get('movie')
    theatre = request.args.get('theatre')
    showtime = request.args.get('showtime')
    movie = get_movie_by_id(movie_id)
    return render_template('seat_selection.html', movie=movie, theatre=theatre, showtime=showtime)
@app.route('/api/book', methods=['POST'])
def book_seats():
    data = request.get_json()
    bookings_collection.insert_one({
        "movie": data["movie"],
        "time": data["time"],
        "theatre": data["theatre"],
        "seats": data["seats"],
        "total": data["total"]
    })
    return jsonify({"status": "success"})

@app.route('/payment')
def payment():
    return render_template('payment.html')

@app.route('/thankyou')
def thankyou():
    return render_template('thankyou.html')

@app.route('/confirm_booking', methods=['POST'])
def confirm_booking():
    try:
        data = request.json
        print("📥 Booking data received:", data)
        if not data:
            return jsonify({'status': 'error', 'message': 'No data received'}), 400
        movie = data.get('movie')
        date = data.get('date')
        time = data.get('time')
        theatre = data.get('theatre')
        seats = data.get('seats')
        tickets = data.get('tickets')
        price = data.get('price')
        user = session.get('user', {'email': 'guest@example.com', 'name': 'Guest'})
        if not all([movie, date, time, theatre, seats, tickets, price]):
            return jsonify({'status': 'error', 'message': 'Missing required fields'}), 400
        booking_id = str(uuid.uuid4())
        booking = {
            'id': booking_id,
            'movie': movie,
            'date': date,
            'time': time,
            'theatre': theatre,
            'seats': seats,
            'tickets': tickets,
            'price': price,
            'booked_by': user['email'],
            'timestamp': datetime.utcnow().isoformat()
        }
        if booking_table:
            try:
                booking_table.put_item(Item=booking)
            except Exception as db_err:
                print("⚠️ DynamoDB save failed:", db_err)
        else:
            print("⚠️ Skipping DynamoDB save because booking_table is not available.")
        try:
            bookings_collection.insert_one(booking)
            print("✅ Booking saved to MongoDB.")
        except Exception as mongo_err:
            print("❌ Failed to save booking to MongoDB:", mongo_err)
        subject = f"🎟 Booking Confirmed: {movie}"
        message = f"Hi {user.get('name', 'User')},\n\nYour booking for '{movie}' at {time} on {date} in {theatre} is confirmed.\n\nSeats: {', '.join(seats)}\nTotal Tickets: {tickets}\nTotal Price: {price}"
        if sns:
            send_notification(booking, sns, SNS_TOPIC_ARN, subject, message)
        else:
            print("⚠️ SNS client not available. Skipping notification.")
        return jsonify({'status': 'success', 'booking_id': booking_id}), 200
    except Exception as e:
        print("❌ Booking Error:", str(e))
        return jsonify({'status': 'error', 'message': str(e)}), 500
@app.route('/seed_movies')
def seed_movies():
    movies_collection.delete_many({})
    movies = [
        {
            "id": "1",
            "title": "Smurfs",
            "language": "English",
            "genre": "Animation, Family, Fantasy",
            "price": "Rs200",
            "image": "https://encrypted-tbn2.gstatic.com/images?q=tbn:ANd9GcSUrL2fw8goChvf2NG_AVFC4nOM9LGUTUJlAPY55yYjgC8lKBEm",
            "description": "The Smurfs are tiny blue creatures living in a magical forest, led by the wise Papa Smurf. When the evil wizard Gargamel discovers their village, they must escape to the human world to survive. A heartwarming, humorous adventure unfolds as the Smurfs learn about friendship, bravery, and finding their way back home.",
            "theatres": [
                {
                    "name": "Sri Lakshmi Theatre, Kavali",
                    "showtimes": ["12:00 PM", "3:00 PM", "6:00 PM"]
                }
            ]
        },
        {
            "id": "2",
            "title": "The Fantastic Four:First Steps",
            "language": "English",
            "genre": "Action, Adventure, Sci-Fi",
            "price": "Rs200",
            "image": "https://encrypted-tbn3.gstatic.com/images?q=tbn:ANd9GcQJ8g3wR3SDS9Z8-baJOw2BuOLgqrtwlMILXvTW9LK1M4PYwFFj",
            "description": "Four ordinary individuals gain extraordinary powers after a cosmic experiment goes wrong. As they struggle to control their abilities, a powerful new enemy emerges. Together, they must become a team and take their first steps as heroes.",
            "theatres": [
                {
                    "name": "Sri Lakshmi Theatre, Kavali",
                    "showtimes": ["12:00 PM", "3:00 PM", "6:00 PM"]
                },
                {
                    "name": "IMAX, Kavali",
                    "showtimes": ["11:00 AM", "2:30 PM", "6:30 PM"]
                }
            ]
        },
        {
            "id":"3",
            "title": "Jurassic World:Rebirth",
            "language": "English",
            "genre": "Action, Thriller, Sci-Fi",
            "price": "Rs250",
            "image": "https://encrypted-tbn2.gstatic.com/images?q=tbn:ANd9GcSQ_mCeNLtPfEM8AbIDVZUyVyuu_JENshYBugD_JPNjI9vrBWRA",
            "description": "A devastated Isla Nublar is reborn when Claire and Owen lead a daring mission to protect endangered dinosaurs from a ruthless bioweapon syndicate. As secrets behind a mysterious map surface, they must forge new alliances with a new generation of experts—and unexpected treaties with the creatures themselves. An edge-of-your-seat adventure blending thrills, heart, and the primal wonder of life unleashed.",
            "theatres": [
                {
                    "name": "PVR Cinemas, Kavali",
                    "showtimes": ["10:00 AM", "1:30 PM", "6:00 PM"]
                },
                {
                    "name": "IMAX, Kavali",
                    "showtimes": ["11:00 AM", "2:30 PM", "6:30 PM"]
                },
            ]
        },
        {
            "id": "4",
            "title": "Superman",
            "language": "English",
            "genre": "Action, Adventure, Sci-Fi, Fantasy",
            "price": "Rs250",
            "image": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTqZn20BgESHQl4KVxTNRT0E444uyU35NpnQBUHUlEvW-j4WNqE",
            "description": "When the last son of Krypton crashes on Earth, he grows up to become the world’s greatest protector. Living as Clark Kent, he hides his true identity while defending humanity as Superman. Torn between two worlds, he must face powerful enemies and embrace his destiny as a symbol of hope.",
            "theatres": [
                {
                    "name": "Sri Lakshmi Theatre, Kavali",
                    "showtimes": ["12:00 PM", "3:00 PM", "7:00 PM"]
                },
                {
                    "name": "IMAX, Kavali",
                    "showtimes": ["11:00 AM", "2:30 PM", "6:30 PM"]
                }
            ]
        },
        {
            "id": "5",
            "title": "War 2",
            "language": "hindi",
            "genre": "Action, Thriller",
            "price": "Rs200",
            "image": "https://encrypted-tbn1.gstatic.com/images?q=tbn:ANd9GcRcUHzhXmYstYQAUNnsxv-utGFQ0_hpBZJgCgD30p0jqtERSH1y",
            "description": "A rogue mission forces elite agents from rival nations to unite against a deadly global threat. As hidden loyalties unravel, every move could spark international war. Packed with high-octane action and mind games, War 2 raises the stakes like never before.",
            "theatres": [
                {
                    "name": "Sri Lakshmi Theatre, Kavali",
                    "showtimes": ["10:00 AM", "1:00 PM", "4:00 PM"]
                }
            ]
        },
        { 
            "id": "6",
            "title": "Superman1", 
            "language": "hindi",
            "genre": "Action, Adventure, Fantasy, Sci-Fi",
            "price": "Rs200",
            "image": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTqZn20BgESHQl4KVxTNRT0E444uyU35NpnQBUHUlEvW-j4WNqE",
            "description": "When the last son of Krypton crashes on Earth, he grows up to become the world’s greatest protector. Living as Clark Kent, he hides his true identity while defending humanity as Superman. Torn between two worlds, he must face powerful enemies and embrace his destiny as a symbol of hope.",
            "theatres": [
                {
                    "name": "PVR Cinemas, Kavali",
                    "showtimes": ["10:00 AM", "3:30 PM", "8:30 PM"]
                }
            ]
        },
        {
            "id": "7",
            "title": "Nikita Roy",
            "language": "hindi",
            "genre": "Horror, Mystery, Thriller",
            "price": "Rs250",
            "image": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRYs_PKQZnJRaDUREOPF0fCcFf-gkwQNTNE0QsthsbNjFSE_MIm",
            "description": "Nikita Roy, a fearless investigator, uncovers a dark conspiracy linked to a series of mysterious disappearances. As she delves deeper, the line between truth and illusion begins to blur. A gripping psychological thriller where justice comes at a chilling cost.",
            "theatres": [
                {
                    "name": "PVR Cinemas, Kavali",
                    "showtimes": ["2:00 PM", "5:00 PM", "8:00 PM"]
                },
                {
                    "name": "Sri Lakshmi Theatre, Kavali",
                    "showtimes": ["12:00 PM", "3:00 PM", "6:00 PM"]
                }
            ]
        },
        {
            "id": "8",
            "title": "3 BHK",
            "language": "tamil",
            "genre": "Drama, Family",
            "price": "Rs200",
            "image": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQ9zdJ5ZhXj8pRpDBx4ywHu8tCLs6LQmAPRllzYEfgUfgDXUvUu",
            "description": "A middle-class family's dream home turns into a maze of secrets as strange events unfold behind each door. Hidden tensions and mysterious neighbors begin to unravel their peaceful life. 3 BHK is a suspense-filled domestic drama where every room holds a twist.",
            "theatres": [
                {
                    "name": "PVR Cinemas, Kavali",
                    "showtimes": ["11:00 AM", "2:30 PM", "6:30 PM"]
                }
            ]    
        }, 
        {
            "id": "9",
            "title": "Paranthu Po",
            "language": "tamil",
            "genre": "Comedy, Drama, Musical",
            "price": "Rs200",
            "image": "https://images.pexels.com/photos/7991579/pexels-photo-7991579.jpeg?auto=compress&cs=tinysrgb&w=1200",
            "description": "A struggling father and his curious young son embark on a transformative road journey across Tamil Nadu. Along the way, they encounter strangers who reshape their view of life, love, and loss. Paranthu Po is a heartfelt tale of hope, relationships, and the freedom to dream.",
            "theatres": [
                {
                    "name": "PVR Cinemas, Kavali",
                    "showtimes": ["12:00 PM", "3:00 PM", "6:00 PM"]
                }
            ]
        },
        {
            "id": "10",
            "title": "Hari Hara Veera Mallu",
            "language": "telugu",
            "genre": "Action, Drama",
            "price": "Rs250",
            "image": "https://encrypted-tbn2.gstatic.com/images?q=tbn:ANd9GcR2t2qnSxIi9X8qIcUJ8X3ZbNak1nOr5SlyQ-_u-tjMrYgeUk-l",
            "description": "Set in the Mughal era, Veera Mallu, a legendary outlaw, rises against tyranny to steal the prized Koh-i-Noor diamond. Battling empires and destiny, he becomes a symbol of rebellion and justice. Hari Hara Veera Mallu is a grand historical epic blending action, devotion, and heroism.",
            "theatres": [
                {
                    "name": "PVR Cinemas, Kavali",
                    "showtimes": ["11:00 AM", "2:30 PM", "6:30 PM"]
                },
                {
                    "name": "IMAX, Kavali",
                    "showtimes": ["10:00 AM", "1:00 PM", "4:00 PM"]
                }
            ]
        },
        {   
            "id": "11",
            "title": "Kannappa",
            "language": "telugu",
            "genre":  "Action, Epic",
            "price": "Rs300",
            "image": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQQZFvUvhzgYPzw8sTQReM0ruAAEIEjHkGhMHnO3ytAZGWxsk-p",
            "description": "Based on the legendary devotee of Lord Shiva, Kannapa follows a tribal hunter whose unwavering faith leads to divine transformation. As he challenges societal norms and spiritual tests, his devotion transcends boundaries. A powerful mythological epic celebrating sacrifice, belief, and eternal love for the divine.",
            "theatres": [
                {
                    "name": "Sri Lakshmi Theatre, Kavali",
                    "showtimes": ["10:00 AM", "1:00 PM", "4:00 PM"]
                }
            ]
        }   
    ]
    movies_collection.insert_many(movies)
    return "🎬 Movies seeded successfully!"

@app.context_processor
def inject_user():
    return dict(logged_in_user=session.get('user'))

# ------------------- Main ------------------- #
if __name__ == '__main__':
    print("\n🎬 Movie Magic - Smart Movie Ticket Booking System")
    print("📁 Serving HTML templates from /templates directory")
    print("🌐 Visit http://localhost:5000/")
    app.run(debug=True, host='0.0.0.0', port=5000)