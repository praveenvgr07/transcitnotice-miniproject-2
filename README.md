# TransitNotice – Smart Public Transport Information & Ticket Booking Platform

> **Tamil Nadu, India** · Real-time monitoring · Schedule change alerts · Ticket booking support

---

## Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [Architecture](#architecture)
4. [Tech Stack](#tech-stack)
5. [Project Structure](#project-structure)
6. [Installation](#installation)
7. [Configuration](#configuration)
8. [Database Setup](#database-setup)
9. [Running the Application](#running-the-application)
10. [Supported Transport Providers](#supported-transport-providers)
11. [Data Collection & Ethics](#data-collection--ethics)
12. [Testing](#testing)
13. [API Endpoints](#api-endpoints)

---

## Overview

TransitNotice is a production-grade, full-stack web platform that:

- **Collects** schedule data from Tamil Nadu's public transport providers (MTC, TNSTC, SETC, CMRL) via authorized data feeds
- **Detects** schedule changes automatically using a comparison engine
- **Notifies** affected passengers via email and SMS in real time
- **Supports** journey booking management with a multi-step booking flow
- Provides a **real-time dashboard** with SSE-based live updates
- Includes a full **admin panel** for source management, scraper logs, and announcements

---

## Features

| Category           | Features |
|--------------------|----------|
| **Data Collection**    | Background scheduler (APScheduler, every 10 min), robots.txt enforcement, rate limiting, retry with backoff, GTFS feed parsing |
| **Change Detection**   | Departure/arrival time changes, cancellations, diversions, new schedules, service resumptions |
| **Notifications**      | In-app notifications, email (SMTP/SendGrid), SMS (Twilio/MSG91), delivery tracking with retry |
| **User System**        | Registration, email verification, mobile OTP, login/logout, password reset, profile management |
| **Booking**            | Multi-step booking flow, passenger details, booking references, cancellation, redirect to official provider |
| **Admin Panel**        | Dashboard stats, source enable/disable, scraper log audit, change history, announcement management, user management, manual job trigger |
| **Real-time UI**       | Server-Sent Events (SSE) for live change updates, notification badge polling, animated UI |
| **Security**           | bcrypt password hashing, CSRF-safe sessions, role-based access control, input validation |

---

## Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  Official    │────▶│  Background      │────▶│  MySQL Database  │
│  Transport   │     │  Scheduler       │     │  (15 tables)     │
│  Sources     │     │  (APScheduler)   │     │                  │
└─────────────┘     └──────────────────┘     └────────┬─────────┘
                            │                          │
                    ┌───────▼────────┐         ┌───────▼─────────┐
                    │ Change         │         │  Flask App       │
                    │ Detection      │────────▶│  (Blueprints)    │
                    │ Engine         │         │                  │
                    └───────┬────────┘         └───────┬─────────┘
                            │                          │
                    ┌───────▼────────┐         ┌───────▼─────────┐
                    │ Notification   │         │  Jinja2 HTML     │
                    │ Dispatcher     │         │  Templates       │
                    │ (Email + SMS)  │         │  + Bootstrap 5   │
                    └────────────────┘         └─────────────────┘
```

---

## Tech Stack

| Layer        | Technology                              |
|--------------|----------------------------------------|
| Backend      | Python 3.12+, Flask 3.x                |
| Database     | MySQL 8.0+ (utf8mb4, connection pool)  |
| Templating   | Jinja2                                  |
| Frontend     | HTML5, Bootstrap 5.3, Bootstrap Icons   |
| Fonts        | Inter + Poppins (Google Fonts)          |
| Scheduler    | APScheduler (BackgroundScheduler)       |
| Email        | smtplib / SendGrid                      |
| SMS          | Twilio / MSG91                          |
| Scraping     | requests + urllib.robotparser           |
| Password     | bcrypt                                  |
| Testing      | pytest / unittest                       |

---

## Project Structure

```
TransitNotice/
├── app.py                    # Flask entry point (application factory)
├── config.py                 # Configuration (dev/prod)
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variable template
├── .gitignore
│
├── database/
│   ├── schema.sql            # MySQL schema (15 tables + seed data)
│   ├── db.py                 # Connection pool & DBCursor
│   └── init_db.py            # Schema initialization script
│
├── models/
│   ├── user_model.py         # User CRUD, bcrypt hashing
│   ├── schedule_model.py     # Route search, schedule queries
│   ├── booking_model.py      # Booking creation & management
│   └── notification_model.py # Notifications, delivery logs, scraper logs
│
├── scrapers/
│   ├── base_scraper.py       # HTTP client, robots.txt, rate limiting
│   ├── mtc_scraper.py        # MTC (disabled pending auth)
│   ├── tnstc_scraper.py      # TNSTC (disabled pending auth)
│   ├── setc_scraper.py       # SETC (disabled pending auth)
│   └── cmrl_scraper.py       # CMRL GTFS parser (disabled pending feed URL)
│
├── services/
│   ├── change_detector.py    # Schedule comparison engine
│   ├── email_service.py      # SMTP/SendGrid with HTML templates
│   ├── sms_service.py        # Twilio/MSG91
│   ├── notification_service.py # Dispatch orchestrator
│   └── scheduler.py          # APScheduler background jobs
│
├── routes/
│   ├── main_routes.py        # Homepage, about, error handlers
│   ├── auth_routes.py        # Register, login, verify, password reset
│   ├── user_routes.py        # Dashboard, profile, bookings, notifications
│   ├── transport_routes.py   # Search, service details, SSE, JSON APIs
│   ├── booking_routes.py     # Multi-step booking flow
│   └── admin_routes.py       # Admin panel (role-gated)
│
├── templates/
│   ├── base.html             # Base layout (navbar, footer, flash)
│   ├── index.html            # Homepage
│   ├── login.html / register.html
│   ├── dashboard.html        # User dashboard
│   ├── search.html           # Route search & results
│   ├── service_details.html  # Route detail + schedules + stops
│   ├── booking.html / passenger_details.html / confirm_booking.html / booking_done.html
│   ├── notifications.html / profile.html / booking_history.html
│   ├── about.html / 404.html / 500.html
│   └── admin/
│       ├── base_admin.html   # Admin layout
│       ├── dashboard.html    # Admin stats & overview
│       ├── sources.html / users.html / bookings.html
│       ├── scraper_logs.html / changes.html
│       └── announcements.html / new_announcement.html
│
├── static/
│   ├── css/
│   │   ├── style.css         # Main stylesheet (709 lines)
│   │   └── dashboard.css     # Dashboard & admin styles
│   └── js/
│       ├── main.js           # Global JS (flash dismiss, SSE, nav)
│       ├── search.js         # Search page interactions
│       └── notifications.js  # Notification page interactions
│
└── tests/
    └── test_core.py          # Unit tests
```

---

## Installation

```bash
# 1. Clone and navigate
cd "mini 2 - TransitNotice"

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate       # Windows
# source venv/bin/activate  # Linux/Mac

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy and edit environment file
copy .env.example .env
# Edit .env with your MySQL credentials, SECRET_KEY, etc.
```

---

## Configuration

Edit `.env` with the following required values:

```env
# Flask
SECRET_KEY=your-secure-random-key-here
FLASK_DEBUG=1

# MySQL
DB_HOST=localhost
DB_PORT=3306
DB_NAME=transitnotice
DB_USER=root
DB_PASSWORD=your_mysql_password

# Email (SMTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@email.com
SMTP_PASSWORD=your-app-password
MAIL_FROM=noreply@transitnotice.in

# Scheduler
SCHEDULER_ENABLED=true
SCHEDULER_INTERVAL_MINUTES=10
```

---

## Database Setup

```bash
# 1. Create the database in MySQL
mysql -u root -p -e "CREATE DATABASE transitnotice CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 2. Run the schema
python database/init_db.py

# This creates all 15 tables and seeds the 4 transport sources.
```

---

## Running the Application

```bash
# Development
python app.py

# The app runs at http://localhost:5000
```

The background scheduler starts automatically and runs data collection every 10 minutes.

---

## Supported Transport Providers

| Provider | Full Name | Status | Data Source |
|----------|-----------|--------|------------|
| **MTC** | Metropolitan Transport Corporation | ⏳ Pending Authorization | Web scraping (authorized only) |
| **TNSTC** | Tamil Nadu State Transport Corp. | ⏳ Pending Authorization | Web scraping (authorized only) |
| **SETC** | State Express Transport Corporation | ⏳ Pending Authorization | Web scraping (authorized only) |
| **CMRL** | Chennai Metro Rail Limited | ⏳ Pending Feed URL | GTFS standard feed |

> **Note:** All scrapers are **disabled by default**. They must only be enabled after obtaining explicit authorization from each transport operator and confirming robots.txt compliance.

---

## Data Collection & Ethics

TransitNotice follows strict data ethics principles:

1. **Authorization Required** – No scraper runs until `is_authorized = True` is set after legal review
2. **robots.txt Compliance** – Every request checks robots.txt before proceeding
3. **Rate Limiting** – Minimum 1.5-second delay between requests
4. **Transparent User-Agent** – Identifies as `TransitNotice-Bot/1.0` with contact info
5. **Retry Backoff** – Exponential backoff on failures (3 retries)
6. **Audit Logging** – Every collection job is logged with timestamps, record counts, and error messages
7. **No Fabrication** – The platform never generates or extrapolates data

---

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test
python -m pytest tests/test_core.py::TestPasswordHashing -v
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/announcements` | GET | Latest announcements (JSON) |
| `/api/changes` | GET | Recent schedule changes (JSON) |
| `/api/sources` | GET | Source status (JSON) |
| `/api/sse/updates` | GET | Server-Sent Events stream |
| `/api/notifications/unread-count` | GET | Unread count (auth required) |
| `/admin/api/run-collection` | POST | Trigger manual collection (admin) |

---

## License

This project is built for educational and demonstration purposes.
All transport data must be sourced from officially authorized feeds only.

---

*Built with ❤️ for Tamil Nadu's commuters.*
