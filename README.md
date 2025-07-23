# 🎬 Movie Magic – Smart Movie Ticket Booking System

**Movie Magic** is a modern, AWS-powered movie ticket booking system built with **Flask**, **DynamoDB**, and **SNS**. It offers an intuitive interface for users to browse movies, select seats, make payments, and receive booking confirmations — all seamlessly integrated with cloud services.

---

## 💻 Tech Stack

| Layer        | Technology             |
|--------------|------------------------|
| Backend      | Python, Flask          |
| Database     | AWS DynamoDB           |
| Notification | AWS SNS                |
| Frontend     | HTML, Tailwind CSS     |
| Hosting      | Localhost / AWS-ready  |

---

## 🌟 Features

- 🔐 User Signup, Login, Logout (session-based)
- 🎞 Browse and view detailed movie listings
- 🪑 Seat selection with theatre and timing
- 💳 Payment simulation page
- ✅ Booking confirmation via AWS SNS email
- ☁️ Bookings stored in DynamoDB
- ⚙️ Admin route to seed movies into the database
- 📊 User dashboard with booking info (future expansion ready)

---

## 🛠 Project Structure

```bash
Movie-Magic/
├── app.py                  # Main Flask application
├── templates/              # HTML templates (Jinja2)
│   ├── index.html
│   ├── signup.html
│   ├── login.html
│   ├── movies.html
│   ├── movie_details.html
│   ├── seat_selection.html
│   ├── payment.html
│   ├── dashboard.html
│   └── thankyou.html
├── static/                 # (Optional) Static files (CSS/JS/images)
└── README.md               # You're reading it!
