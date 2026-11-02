# 🤖 EduBot AI — Intelligent College Assistant Chatbot

<div align="center">

![EduBot Banner](https://img.shields.io/badge/EduBot_AI-v2.0-00ccff?style=for-the-badge&logo=robot&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.10+-3776ab?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0-000000?style=for-the-badge&logo=flask&logoColor=white)
![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-47A248?style=for-the-badge&logo=mongodb&logoColor=white)
![Groq](https://img.shields.io/badge/Groq-AI-f55036?style=for-the-badge&logo=groq&logoColor=white)
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
7. [Groq Configuration](#-groq-configuration)
8. [MongoDB Setup](#-mongodb-setup)
9. [Deployment Guide](#-deployment-guide)
10. [Screenshots](#-screenshots)
11. [Contributing](#-contributing)
12. [License](#-license)

---

## 🎯 Project Overview

EduBot AI is a full-stack intelligent chatbot application designed to assist B.Tech college students
with all academic queries — from timetables and exam schedules to placements and fee structures.

Built with a **Flask REST API backend**, **JWT authentication**, and a centrally configured
**Groq-hosted AI model**, the chatbot answers in English, Hindi, and Hinglish. The owner-managed
Groq key stays on the server; visitors never need to provide an API key.

The **admin panel** allows faculty/administrators to manage notices, FAQs, and view student query
analytics — all from a beautiful futuristic dark-themed interface.

---

## ✨ Features

### 🤖 AI Chatbot
- Answers queries on: Timetable · Exams · Attendance · Faculty · Syllabus · Placements · Fees · Events · Library · Hostel
- **Groq chat completions** for general, educational, programming, and college questions
- Recent conversation context is sent with each request
- Errors are shown when the backend or AI provider is unavailable; no fake local answer is returned
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
- Upload PDF files for real AI summaries
- PDF text extraction and AI summarization through the central Groq configuration

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
| AI Engine | Groq OpenAI-compatible Chat Completions API |
| Database | MongoDB (local) / MongoDB Atlas (cloud) |
| Auth | JWT (PyJWT) + bcrypt |
| Voice | Web Speech API + SpeechSynthesis API |
| PDF | pdfplumber |
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
# Create virtual environment (recommended)
python -m venv .venv

# Activate it
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

# Install all dependencies
pip install -r backend/requirements.txt
```

---

### Step 3 — Configure Environment

```bash
# Windows PowerShell:
Copy-Item backend\.env.example backend\.env
# macOS / Linux:
cp backend/.env.example backend/.env
```

Set `GROQ_API_KEY` to the owner's key, and set a strong random `SECRET_KEY`. For deployment, also
set `FRONTEND_ORIGINS` to the exact public frontend origin. Never put credentials in the HTML,
JavaScript, a visitor's browser, or a committed `.env` file.

---

### Step 4 — Run the Backend

```bash
# Development (from the repository root)
python app.py

# Production (Linux hosting)
gunicorn backend.app:app --workers 2 --timeout 45 --bind 0.0.0.0:$PORT
```

Server starts at: `http://localhost:5000`
Health check: `http://localhost:5000/health`

---

### Step 5 — Open the Frontend

The frontend is static HTML and needs no build step. The UI offers guest chat as well as account
registration/sign-in.

```bash
# From the repository root
python -m http.server 8080
# Visit http://localhost:8080
```

---

### Step 6 — Configure the Frontend Endpoint

The public backend URL is owner-configured in the frontend's `BACKEND_API_URL` constant; visitors
cannot change it in Settings. For local testing, set it to `http://localhost:5000`. For production,
set it once to the deployed Flask service URL in the frontend file you publish.

Run the backend tests with:

```bash
python -m unittest discover -s tests -v
```

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
  "password": "your-password",
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
{ "username": "21CSE001", "password": "your-password" }
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

#### `POST /api/chat`
Send a public message and recent conversation history to the centrally configured Groq model.

**Request:**
```json
{
  "message": "What is Artificial Intelligence?",
  "history": [
    { "role": "user", "content": "I am studying computer science." },
    { "role": "assistant", "content": "Great! What would you like to learn?" }
  ]
}
```

**Response (200):**
```json
{
  "response": "Artificial intelligence is ...",
  "intent": "fallback",
  "source": "groq"
}
```

Chat history is optional and limited to the latest 20 user/assistant messages. Invalid requests
return `400`; excessive requests return `429`; provider configuration or availability errors return
a clear `4xx/5xx` error and never a local substitute answer.

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

#### `POST /api/upload/pdf`
Public, rate-limited PDF upload (5 requests/minute) for AI summarization. Files are limited to
9 MB in the frontend and 10 MB by the backend request-size limit.

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

#### `GET /health` (also available at `/api/health`)
```json
{
  "status": "ok",
  "version": "2.0.0",
  "db_mode": "memory",
  "ai_engine": "groq",
  "ai_configured": true,
  "timestamp": "..."
}
```

---

## 🔑 Groq Configuration

Create an owner-managed API key at https://console.groq.com/keys and set it only as the backend
environment variable `GROQ_API_KEY`. The default model is Groq's recommended
`openai/gpt-oss-120b`; change `GROQ_MODEL` when selecting another currently supported model.
The frontend never receives the key. The server-side `.env.example` files contain placeholders only.

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

1. Push the repository to GitHub and create a **Blueprint** on Render using `render.yaml`.
2. Set `GROQ_API_KEY` in Render's environment settings. Set `FRONTEND_ORIGINS` to the exact
   website origin (for example `https://your-user.github.io`, without a repository path).
3. Keep the generated `SECRET_KEY`. If you want an administrator login, set a private
   `ADMIN_USERNAME` and strong `ADMIN_PASSWORD`; never put these in frontend files.
4. Deploy the service and verify `https://<your-render-host>/health` reports `"status":"ok"` and
   `"ai_configured":true`.
5. Set `BACKEND_API_URL` once in the frontend file you publish (`index.html` or
   `frontend/index.html`) to the exact Render service URL, then redeploy the static frontend.
   Visitors do not enter or store a backend URL or API key.

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
cd edubot-ai
pip install -r backend/requirements.txt
# Configure GROQ_API_KEY, SECRET_KEY, and FRONTEND_ORIGINS in the host's secret manager

# Run with Gunicorn + Nginx (production)
gunicorn backend.app:app --workers 2 --timeout 45 --bind 127.0.0.1:5000 --daemon

# Configure Nginx to proxy to port 5000
# Then: sudo certbot --nginx for HTTPS
```

---

### Frontend Deployment (GitHub Pages / Netlify)

The frontend is static HTML — deploy `index.html` (or `frontend/index.html`) anywhere. Set its
`BACKEND_API_URL` constant to the Flask service URL before publishing:

```bash
# GitHub Pages
# Publish the repository root or frontend/ folder and enable Pages.

# Netlify
# Drag & drop the frontend/ folder at https://app.netlify.com/drop

# Vercel
vercel --prod
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