# 🤖 EduBot AI — Intelligent College Assistant Chatbot

<div align="center">

![EduBot Banner](https://img.shields.io/badge/EduBot_AI-v2.0-00ccff?style=for-the-badge&logo=robot&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.10+-3776ab?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0-000000?style=for-the-badge&logo=flask&logoColor=white)
![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-47A248?style=for-the-badge&logo=mongodb&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--3.5-412991?style=for-the-badge&logo=openai&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

**A production-ready AI-powered chatbot for B.Tech college students.**
*Final Year Major Project — Computer Science & Engineering*

[Live Demo](#) • [Documentation](#project-documentation) • [API Reference](#api-reference) • [Deployment](#deployment-guide)

</div>

---

## 📋 Table of Contents

1. [Project Overview](#-project-overview)
2. [Features](#-features)
3. [Tech Stack](#-tech-stack)
4. [Folder Structure](#-folder-structure)
5. [Installation & Setup](#-installation--setup)
6. [API Reference](#-api-reference)
7. [OpenAI API Setup](#-openai-api-setup)
8. [MongoDB Setup](#-mongodb-setup)
9. [Deployment Guide](#-deployment-guide)
10. [Screenshots](#-screenshots)
11. [Contributing](#-contributing)
12. [License](#-license)

---

## 🎯 Project Overview

EduBot AI is a full-stack intelligent chatbot application designed to assist B.Tech college students
with all academic queries — from timetables and exam schedules to placements and fee structures.

Built with a **Flask REST API backend**, **MongoDB database**, **JWT authentication**, and an
**OpenAI GPT integration** (with a full local-AI fallback), the system provides instant, accurate
answers in both **English and Hindi**.

The **admin panel** allows faculty/administrators to manage notices, FAQs, and view student query
analytics — all from a beautiful futuristic dark-themed interface.

---

## ✨ Features

### 🤖 AI Chatbot
- Answers queries on: Timetable · Exams · Attendance · Faculty · Syllabus · Placements · Fees · Events · Library · Hostel
- **OpenAI GPT-3.5 Turbo** integration with seamless local fallback
- Markdown-formatted rich responses (tables, bold, lists)
- **Hindi + English** bilingual support

### 💬 Chat Interface
- ChatGPT-style message bubbles
- Real-time typing animation
- Smart quick-reply suggestion chips
- Chat history with session management (localStorage + backend)
- Export chat as `.txt`

### 🎤 Voice Features
- **Voice Input** via Web Speech API (mic button)
- **Voice Output** via SpeechSynthesis API (text-to-speech)
- Supports both `en-IN` and `hi-IN` locales

### 📁 PDF Upload
- Upload `.pdf` / `.docx` files
- AI-powered summarization via OpenAI (or basic extraction fallback)

### 🔐 Authentication
- JWT-based login & registration
- bcrypt password hashing
- Role-based access (student / admin)
- Protected API endpoints

### 🛡️ Admin Panel
- Dashboard analytics (queries, notices, FAQs, user count)
- Add / Edit / Delete notices
- Manage FAQs
- View student query log with intent breakdown
- Hourly activity chart

### 📱 UI/UX
- Futuristic dark theme with neon cyan/violet palette
- Animated neural-network particle canvas background
- Fully responsive (mobile-first design)
- Smooth CSS animations & transitions
- Toast notification system

---

## 🛠 Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | HTML5, CSS3, Vanilla JavaScript (ES2022) |
| Backend | Python 3.10+, Flask 3.0, Flask-CORS |
| AI Engine | OpenAI GPT-3.5 Turbo + Custom Local KB |
| Database | MongoDB (local) / MongoDB Atlas (cloud) |
| Auth | JWT (PyJWT) + bcrypt |
| Voice | Web Speech API + SpeechSynthesis API |
| PDF | pdfplumber + PyPDF2 |
| Deployment | Gunicorn + Render / Railway / VPS |

---

## 📁 Folder Structure

```
AI_College_Assistant/
│
├── frontend/
│   └── index.html              # Complete standalone SPA (HTML + CSS + JS)
│
├── backend/
│   ├── app.py                  # Main Flask application (all routes)
│   ├── requirements.txt        # Python dependencies
│   └── .env.example            # Environment variable template
│
├── docs/
│   └── PROJECT_DOCUMENTATION.md  # ER diagram, architecture, abstract, viva Q&A
│
├── .env.example                # Root env template
└── README.md                   # This file
```

> **Note:** This project intentionally uses a single `app.py` for simplicity (ideal for academic
> submission). For production, split into `routes/`, `models/`, `services/` modules.

---

## 🚀 Installation & Setup

### Prerequisites

| Tool | Version | Download |
|------|---------|----------|
| Python | ≥ 3.10 | https://python.org |
| Node.js | ≥ 18 (optional) | https://nodejs.org |
| MongoDB | ≥ 6.0 (optional) | https://mongodb.com |
| Git | Any | https://git-scm.com |

---

### Step 1 — Clone the Repository

```bash
git clone https://github.com/yourusername/edubot-ai.git
cd edubot-ai
```

---

### Step 2 — Backend Setup

```bash
# Navigate to backend folder
cd backend

# Create virtual environment (recommended)
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate
# macOS / Linux:
source venv/bin/activate

# Install all dependencies
pip install -r requirements.txt
```

---

### Step 3 — Configure Environment

```bash
# Copy the example env file
cp .env.example .env

# Open .env and fill in your values:
# - SECRET_KEY    → any long random string
# - OPENAI_API_KEY → from https://platform.openai.com
# - MONGO_URI     → your MongoDB connection string
```

> ⚠️ The app works **without** MongoDB (uses in-memory storage) and **without** OpenAI (uses
> the built-in local AI engine). So you can run it immediately with zero configuration!

---

### Step 4 — Run the Backend

```bash
# Development mode (from /backend)
python app.py

# Production mode
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

Server starts at: `http://localhost:5000`
Health check: `http://localhost:5000/api/health`

---

### Step 5 — Open the Frontend

The frontend is a **single HTML file** — no build step needed.

```bash
# Option A: Open directly in browser
open frontend/index.html        # macOS
start frontend/index.html       # Windows
xdg-open frontend/index.html    # Linux

# Option B: Serve with Python
cd frontend
python -m http.server 8080
# Then visit http://localhost:8080
```

---

### Step 6 — Connect Frontend to Backend (Optional)

1. Open the app in your browser
2. Click **Settings** (gear icon in sidebar)
3. Paste your backend URL: `http://localhost:5000`
4. Click **Save**

The chatbot will now use your Flask backend + OpenAI instead of the local AI engine.

---

### 🔑 Demo Credentials

| Role | Username | Password |
|------|----------|----------|
| Student | `student` | `pass123` |
| Admin | `admin` | `admin123` |

---

## 📡 API Reference

Base URL: `http://localhost:5000/api`

All protected endpoints require: `Authorization: Bearer <jwt_token>`

---

### Auth Endpoints

#### `POST /api/auth/register`
Register a new student account.

**Request:**
```json
{
  "name": "Rahul Sharma",
  "rollNo": "21CSE001",
  "email": "rahul@college.edu",
  "password": "pass123",
  "year": "Final Year",
  "branch": "CSE"
}
```

**Response (201):**
```json
{
  "token": "eyJhbGci...",
  "user": { "id": "21CSE001", "name": "Rahul Sharma", "role": "student" },
  "message": "Registered successfully"
}
```

---

#### `POST /api/auth/login`
Authenticate and receive a JWT.

**Request:**
```json
{ "username": "21CSE001", "password": "pass123" }
```

**Response (200):**
```json
{
  "token": "eyJhbGci...",
  "user": { "id": "21CSE001", "name": "Rahul Sharma", "role": "student" }
}
```

---

#### `GET /api/auth/me` 🔒
Returns the authenticated user's profile.

---

### Chat Endpoints

#### `POST /api/chat` 🔒
Send a message and receive an AI response.

**Request:**
```json
{
  "message": "When are the upcoming exams?",
  "language": "en",
  "chatId": "optional-session-id"
}
```

**Response (200):**
```json
{
  "response": "📝 **Examination Schedule...**",
  "intent": "exams",
  "source": "openai"
}
```

---

#### `GET /api/chat/history` 🔒
Returns all saved chat sessions for the current user.

#### `POST /api/chat/history` 🔒
Save/update a chat session.

#### `DELETE /api/chat/history/<chat_id>` 🔒
Delete a specific chat session.

---

### Notices Endpoints

#### `GET /api/notices`
Returns all active college notices (public).

#### `POST /api/notices` 🔒 (admin)
Create a new notice.

#### `PUT /api/notices/<id>` 🔒 (admin)
Update a notice.

#### `DELETE /api/notices/<id>` 🔒 (admin)
Delete a notice.

---

### FAQs Endpoints

#### `GET /api/faqs?category=Academics`
Returns FAQs (optionally filtered by category).

#### `POST /api/faqs` 🔒 (admin)
Add a new FAQ.

---

### Admin Endpoints

#### `GET /api/admin/stats` 🔒 (admin)
Returns dashboard statistics.

#### `GET /api/admin/queries` 🔒 (admin)
Returns recent student query log.

#### `GET /api/admin/users` 🔒 (admin)
Returns all registered users.

---

### PDF Endpoint

#### `POST /api/upload/pdf` 🔒
Upload a PDF for AI summarization.

**Form-data:** `file: <pdf-file>`

**Response:**
```json
{
  "text": "Extracted text preview...",
  "summary": "AI-generated summary...",
  "pages": 12
}
```

---

### Health Check

#### `GET /api/health`
```json
{
  "status": "ok",
  "version": "2.0.0",
  "db_mode": "mongodb",
  "ai_engine": "openai",
  "timestamp": "2025-05-22T10:30:00Z"
}
```

---

## 🔑 OpenAI API Setup

1. **Create an account** at https://platform.openai.com
2. Go to **API Keys** → **Create new secret key**
3. Copy the key (starts with `sk-...`)
4. Add to your `.env` file:
   ```
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   OPENAI_MODEL=gpt-3.5-turbo
   ```
5. Restart the Flask server.

> **Cost estimate:** GPT-3.5-Turbo costs ~$0.002 per 1K tokens. A typical chat message uses
> ~200–500 tokens. For a college project, $5 in credits is more than enough.

> **Free tier:** OpenAI gives $5 free credits to new accounts.

---

## 🍃 MongoDB Setup

### Option A — Local MongoDB

```bash
# Install MongoDB Community Edition
# https://www.mongodb.com/try/download/community

# Start MongoDB service
# Windows:
net start MongoDB
# macOS:
brew services start mongodb-community
# Linux:
sudo systemctl start mongod

# Default URI (no auth):
MONGO_URI=mongodb://localhost:27017/
```

### Option B — MongoDB Atlas (Cloud, Free Tier)

1. Go to https://cloud.mongodb.com
2. Create a **free M0 cluster**
3. Add your IP to the **Network Access** whitelist (or allow all: `0.0.0.0/0`)
4. Create a **database user**
5. Click **Connect → Drivers** and copy the connection string
6. Add to `.env`:
   ```
   MONGO_URI=mongodb+srv://username:password@cluster0.mongodb.net/
   DB_NAME=edubot_db
   ```

---

## 🌐 Deployment Guide

### Option A — Render.com (Recommended — Free Tier)

1. Push your code to GitHub
2. Go to https://render.com → **New Web Service**
3. Connect your GitHub repo
4. Set:
   - **Build Command:** `pip install -r backend/requirements.txt`
   - **Start Command:** `gunicorn -w 2 -b 0.0.0.0:$PORT backend.app:app`
5. Add Environment Variables from your `.env`
6. Deploy! Your URL will be `https://edubot-ai.onrender.com`
7. Update the frontend Settings to point to your Render URL.

---

### Option B — Railway.app

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and deploy
railway login
railway init
railway up
```

---

### Option C — VPS (DigitalOcean / AWS EC2)

```bash
# SSH into your server
ssh user@your-server-ip

# Clone and set up
git clone https://github.com/you/edubot-ai.git
cd edubot-ai/backend
pip install -r requirements.txt
cp .env.example .env
nano .env   # fill in your values

# Run with Gunicorn + Nginx (production)
gunicorn -w 4 -b 127.0.0.1:5000 app:app --daemon

# Configure Nginx to proxy to port 5000
# Then: sudo certbot --nginx for HTTPS
```

---

### Frontend Deployment (GitHub Pages / Netlify)

The frontend `index.html` is a standalone file — deploy anywhere:

```bash
# GitHub Pages
# Just push frontend/index.html to a repo and enable Pages.

# Netlify
# Drag & drop the frontend/ folder at https://app.netlify.com/drop

# Vercel
vercel --prod frontend/
```

---

## 🤝 Contributing

1. Fork the repo
2. Create a branch: `git checkout -b feature/voice-recognition`
3. Commit: `git commit -m "Add voice recognition improvements"`
4. Push: `git push origin feature/voice-recognition`
5. Open a Pull Request

---

## 📄 License

This project is licensed under the **MIT License**.
Free to use for academic, personal, and commercial purposes with attribution.

---

## 👨‍💻 Author

**[Your Name]**
B.Tech CSE — Final Year | Roll No: [XXXXXXX]
[College Name], [City]

- GitHub: [@yourusername](https://github.com/yourusername)
- LinkedIn: [Your Profile](https://linkedin.com/in/yourname)
- Email: you@college.edu

---

<div align="center">
  Made with ❤️ for B.Tech Final Year Project 2024–25<br/>
  <strong>EduBot AI — Empowering Students with Intelligent Assistance</strong>
</div>