"""
=============================================================
  EduBot AI — Flask Backend  (app.py)
  B.Tech Final Year Project — AI College Assistant Chatbot
=============================================================
  Author   : [Your Name]
  Version  : 2.0.0
  Stack    : Python 3.10+ · Flask · PyMongo · PyJWT · bcrypt
  Features : JWT Auth · OpenAI · MongoDB · Admin API · FAQs
=============================================================
"""


import os
from dotenv import load_dotenv
load_dotenv()
import re
import datetime
import json
from functools import wraps
from typing import Optional, Dict, List

import urllib.request
import bcrypt
import jwt
from bson import ObjectId
from flask import Flask, request, jsonify, g
from flask_cors import CORS

# Optional imports (graceful fallback if not installed)
try:
    from pymongo import MongoClient
    MONGO_AVAILABLE = True
except ImportError:
    MONGO_AVAILABLE = False
    print("[WARN] pymongo not installed. Using in-memory storage.")

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("[WARN] openai not installed. Using local AI engine.")

try:
    import pdfplumber          # PDF text extraction
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# ─────────────────────────────────────────────────────
# FLASK APP
# ─────────────────────────────────────────────────────
app = Flask(__name__)
CORS(app, origins="*", allow_headers="*", methods=["GET","POST","PUT","DELETE","OPTIONS"])

# ─────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────
class Config:
    SECRET_KEY        = os.environ.get("SECRET_KEY",     "edubot-secret-CHANGE-IN-PROD")
    OPENAI_API_KEY    = os.environ.get("OPENAI_API_KEY", "")
    OPENAI_MODEL      = os.environ.get("OPENAI_MODEL",   "gpt-3.5-turbo")
    MONGO_URI         = os.environ.get("MONGO_URI",      "mongodb://localhost:27017/")
    DB_NAME           = os.environ.get("DB_NAME",        "edubot_db")
    GEMINI_API_KEY    = ""
    TOKEN_EXPIRY_DAYS = 30
    MAX_TOKENS        = 500

app.config.from_object(Config)

# ─────────────────────────────────────────────────────
# DATABASE  (MongoDB or in-memory fallback)
# ─────────────────────────────────────────────────────
if MONGO_AVAILABLE:
    try:
        mongo_client = MongoClient(app.config["MONGO_URI"], serverSelectionTimeoutMS=3000)
        mongo_client.server_info()   # quick connectivity check
        db      = mongo_client[app.config["DB_NAME"]]
        DB_MODE = "mongodb"
        print("[INFO] Connected to MongoDB.")
    except Exception as e:
        print(f"[WARN] MongoDB not reachable ({e}). Using in-memory storage.")
        DB_MODE = "memory"
else:
    DB_MODE = "memory"

# In-memory collections (used when MongoDB is unavailable)
MEM: Dict = {
    "users":   {},   # key: rollNo.upper()
    "chats":   {},   # key: userId
    "notices": [],
    "faqs":    [],
    "queries": [],
}

def mem_user(uid: str)  -> Optional[dict]: return MEM["users"].get(uid.upper())
def mem_users()         -> list: return list(MEM["users"].values())
def mem_save_user(user): MEM["users"][user["rollNo"].upper()] = user

# ─────────────────────────────────────────────────────
# SEEDED DATA
# ─────────────────────────────────────────────────────
def seed_data():
    """Populate demo data on startup."""
    # Admin user
    if DB_MODE == "memory" and "ADMIN" not in MEM["users"]:
        MEM["users"]["ADMIN"] = {
            "id": "ADMIN", "rollNo": "ADMIN",
            "name": "Dr. A.K. Verma", "email": "admin@college.edu",
            "password": _hash("admin123"), "role": "admin",
            "year": "HOD / Faculty", "branch": "CSE",
        }

    # Sample notices
    if not MEM["notices"]:
        MEM["notices"] = [
            {"id":"n1","title":"Mid Semester Exam Schedule Released",
             "content":"Mid-sem exams will be held from March 15–22, 2025.",
             "category":"Academics","isActive":True,
             "createdAt":"2025-05-15","createdBy":"ADMIN"},
            {"id":"n2","title":"Campus Placement Drive — TCS, Infosys, Wipro",
             "content":"Campus placement drive scheduled for May 20–22. Register at placement portal.",
             "category":"Placement","isActive":True,
             "createdAt":"2025-05-10","createdBy":"ADMIN"},
            {"id":"n3","title":"Annual Techfest 2025 — Registrations Open",
             "content":"Register for TECHVISTA 2025 at techvista.college.edu. Prize pool ₹5 Lakh.",
             "category":"Events","isActive":True,
             "createdAt":"2025-05-08","createdBy":"ADMIN"},
        ]

    # Sample FAQs
    if not MEM["faqs"]:
        MEM["faqs"] = [
            {"id":"f1","question":"How do I check my attendance?",
             "answer":"Login to portal.college.edu → Academics → Attendance.",
             "category":"Academics","views":234},
            {"id":"f2","question":"What is the minimum attendance required?",
             "answer":"Minimum 75 % mandatory. Below 65 % results in exam debarment.",
             "category":"Academics","views":198},
            {"id":"f3","question":"When does the placement season start?",
             "answer":"Placement season typically begins in July and runs through December for final year students.",
             "category":"Placement","views":312},
            {"id":"f4","question":"How can I pay fees?",
             "answer":"Pay online at fees.college.edu via UPI, NEFT/RTGS, or Debit/Credit card.",
             "category":"Finance","views":178},
        ]

# ─────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────
def _hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def _check(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

def _gen_token(user_id: str, role: str) -> str:
    payload = {
        "sub":  user_id,
        "role": role,
        "iat":  datetime.datetime.utcnow(),
        "exp":  datetime.datetime.utcnow() + datetime.timedelta(days=Config.TOKEN_EXPIRY_DAYS),
    }
    return jwt.encode(payload, app.config["SECRET_KEY"], algorithm="HS256")

def _decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None

def _get_token() -> str:
    hdr = request.headers.get("Authorization", "")
    return hdr.replace("Bearer ", "").strip()

def ts_now() -> str:
    return datetime.datetime.utcnow().isoformat() + "Z"

def safe_id() -> str:
    return datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S%f")

# ─────────────────────────────────────────────────────
# AUTH DECORATORS
# ─────────────────────────────────────────────────────
def auth_required(f):
    """Verify JWT on every protected endpoint."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        payload = _decode_token(_get_token())
        if not payload:
            return jsonify({"error": "Unauthorized — missing or expired token"}), 401
        g.user = payload
        return f(*args, **kwargs)
    return wrapper

def admin_required(f):
    """Allow only admin-role JWT tokens."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        payload = _decode_token(_get_token())
        if not payload or payload.get("role") != "admin":
            return jsonify({"error": "Admin access required"}), 403
        g.user = payload
        return f(*args, **kwargs)
    return wrapper

# ─────────────────────────────────────────────────────
# LOCAL AI ENGINE  (keyword-intent → knowledge base)
# ─────────────────────────────────────────────────────
INTENT_KEYWORDS: Dict[str, List[str]] = {
    "timetable":  ["timetable","schedule","class","timing","lecture","period","समय"],
    "exams":      ["exam","test","mid sem","end sem","result","marks","grade","hall ticket","परीक्षा"],
    "attendance": ["attendance","absent","present","shortage","bunk","उपस्थिति"],
    "faculty":    ["faculty","professor","teacher","hod","staff","शिक्षक"],
    "syllabus":   ["syllabus","curriculum","subject","course","unit","पाठ्यक्रम"],
    "placements": ["placement","job","company","campus","package","salary","lpa","प्लेसमेंट"],
    "fees":       ["fee","fees","tuition","payment","scholarship","rupee","शुल्क"],
    "events":     ["event","festival","fest","hackathon","workshop","seminar","techfest","कार्यक्रम"],
    "library":    ["library","book","borrow","journal","nptel","पुस्तकालय"],
    "hostel":     ["hostel","room","mess","warden","accommodation","छात्रावास"],
    "greet":      ["hi","hello","hey","good morning","namaste","नमस्ते"],
}

LOCAL_RESPONSES: Dict[str, Dict[str, str]] = {
    "timetable": {
        "en": (
            "📅 **Weekly Class Schedule — B.Tech CSE Semester VIII**\n\n"
            "| Time | Monday | Tuesday | Wednesday | Thursday | Friday |\n"
            "|------|--------|---------|-----------|---------|--------|\n"
            "| 9–10 | AI & ML | DBMS | Compiler Design | Project | AI & ML |\n"
            "| 10–11 | Compiler | AI & ML | DBMS | Compiler | DBMS |\n"
            "| 11–12 | CS Lab | Free | CS Lab | AI Lab | Free |\n"
            "| 1–2 | Elective | Comp. Networks | Project | Elective | Seminar |\n\n"
            "📍 CSE Block · Wing-B · Floor 3  ⏰ 9 AM – 4 PM"
        ),
        "hi": "📅 कक्षा समय-सारणी 8वाँ सेमेस्टर — सोम-शुक्र, 9 AM से 4 PM। CSE Block, Wing-B, Floor 3.",
    },
    "exams": {
        "en": (
            "📝 **Examination Schedule 2024–25**\n\n"
            "**Mid-Semester:** March 15–22, 2025 | 10 AM–12 PM\n"
            "**End-Semester:** May 10–25, 2025 | 9 AM–12 PM\n\n"
            "Minimum 75 % attendance required. Hall tickets available 3 days prior."
        ),
        "hi": "📝 मध्यावधि: 15–22 मार्च | सत्रांत: 10–25 मई 2025। न्यूनतम 75% उपस्थिति जरूरी।",
    },
    "attendance": {
        "en": (
            "📊 **Attendance Policy**\n\n"
            "- Minimum required: **75 %**\n"
            "- Below 65 %: Debarred from exams\n"
            "- Check portal: portal.college.edu → Academics → Attendance\n\n"
            "*Demo data shows your DBMS attendance at 70 % — attend 2 more classes to cross 75 %.*"
        ),
        "hi": "📊 न्यूनतम 75% उपस्थिति अनिवार्य। portal.college.edu पर जाँचें।",
    },
    "faculty": {
        "en": (
            "👨‍🏫 **CSE Faculty Directory**\n\n"
            "| Name | Role | Subject |\n"
            "|------|------|---------|\n"
            "| Dr. A.K. Verma | HOD | DBMS, OS |\n"
            "| Prof. Priya Sharma | Assoc. Prof | AI & ML |\n"
            "| Dr. Rajesh Gupta | Asst. Prof | Compiler |\n"
            "| Prof. Sunita Patel | Asst. Prof | Networks |\n\n"
            "📍 HOD Office: Room 301 · 📧 cse@college.edu"
        ),
        "hi": "👨‍🏫 HOD: डॉ. वर्मा (Room 301) | AI: प्रो. प्रिया | Compiler: डॉ. राजेश | Networks: प्रो. सुनीता",
    },
    "syllabus": {
        "en": "📚 Semester VIII subjects: AI & ML, DBMS, Compiler Design, Computer Networks + one Elective (Cloud/IoT/DS/Blockchain). Reference: AIMA, Silberschatz, Tanenbaum.",
        "hi": "📚 विषय: AI & ML, DBMS, Compiler Design, Computer Networks + ऐच्छिक विषय।",
    },
    "placements": {
        "en": (
            "💼 **Placement Highlights 2024–25**\n\n"
            "- Placed: 312 / 380 students · Highest: ₹42 LPA (Google)\n"
            "- Average: ₹8.5 LPA · Median: ₹6.2 LPA\n"
            "- Eligibility: CGPA ≥ 7.0 · No backlogs\n"
            "- Season: July – December 2025\n"
            "- Register: placement.college.edu"
        ),
        "hi": "💼 नियुक्ति: 312/380 | उच्चतम: ₹42 LPA | औसत: ₹8.5 LPA | CGPA ≥ 7.0 जरूरी।",
    },
    "fees": {
        "en": (
            "💰 **Fee Structure — Per Semester**\n\n"
            "Tuition ₹45,000 · Lab ₹3,000 · Dev ₹5,000 · Exam ₹2,000\n"
            "**Total: ₹57,500 / semester**\n\n"
            "Hostel: ₹55,000 / year | Scholarships: SC/ST 100 %, Merit 25 %\n"
            "Pay at: fees.college.edu"
        ),
        "hi": "💰 कुल शुल्क: ₹57,500/सेमेस्टर। छात्रावास: ₹55,000/वर्ष। fees.college.edu पर भुगतान।",
    },
    "events": {
        "en": "🎉 TECHVISTA 2025 (May 25–27) · Placement Drive (May 20–22) · Guest Lecture: AI (May 18) · Alumni Meet (May 30) · Sports Tournament (June 5–10).",
        "hi": "🎉 TECHVISTA 2025 (25–27 मई) | Placement Drive (20–22 मई) | Guest Lecture (18 मई) | Alumni Meet (30 मई)",
    },
    "library": {
        "en": "📖 Library: Mon–Sat 8 AM–8 PM · 50,000+ books · IEEE/Springer access · 3 books for 14 days · ₹2/day fine. library@college.edu",
        "hi": "📖 पुस्तकालय: सोम–शनि 8–8 PM | 3 किताबें, 14 दिन | ₹2/दिन जुर्माना",
    },
    "hostel": {
        "en": "🏠 Boys: H-1, H-2 · Girls: GH-1 · Single ₹35K, Double ₹25K/yr · WiFi · Mess · 24/7 Security",
        "hi": "🏠 लड़के: H-1, H-2 | लड़कियाँ: GH-1 | Single ₹35K, Double ₹25K/वर्ष",
    },
    "greet": {
        "en": "👋 Hello! I'm **EduBot AI**. Ask me about: Timetable · Exams · Attendance · Faculty · Syllabus · Placements · Fees · Events · Library · Hostel.",
        "hi": "👋 नमस्ते! मैं EduBot AI हूँ। पूछें: टाइमटेबल · परीक्षाएँ · उपस्थिति · शिक्षक · शुल्क · प्लेसमेंट · कार्यक्रम।",
    },
    "fallback": {
        "en": "🤔 I didn't understand. Try asking about: Timetable, Exams, Attendance, Faculty, Syllabus, Placements, Fees, Events, Library, or Hostel.",
        "hi": "🤔 समझ नहीं आया। पूछें: टाइमटेबल, परीक्षाएँ, उपस्थिति, शिक्षक, शुल्क, प्लेसमेंट।",
    },
}

def detect_intent(text: str) -> str:
    t = text.lower()
    for intent, keywords in INTENT_KEYWORDS.items():
        if any(k in t for k in keywords):
            return intent
    return "fallback"

def local_response(intent: str, lang: str = "en") -> str:
    entry = LOCAL_RESPONSES.get(intent, LOCAL_RESPONSES["fallback"])
    return entry.get(lang, entry.get("en", ""))

# ─────────────────────────────────────────────────────
# OPENAI INTEGRATION
# ─────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are EduBot, an AI assistant for B.Tech college students in India.
You help with: class timetable, exam schedule, attendance, faculty info, syllabus,
campus placements, fee structure, college events, library, and hostel information.

Instructions:
- Be concise, friendly, and student-oriented.
- Use markdown formatting (bold, tables, bullet lists) for clarity.
- Respond in the language specified in the user's request ({lang}).
- For specific data queries, provide realistic sample data for a B.Tech CSE final year context.
- Do not make up contact details; say "check the college portal" if unsure.
"""

def openai_response(message: str, lang: str = "en") -> str:
    if not OPENAI_AVAILABLE or not app.config["OPENAI_API_KEY"]:
        raise RuntimeError("OpenAI not configured")

    client = openai.OpenAI(api_key=app.config["OPENAI_API_KEY"])
    system = SYSTEM_PROMPT.format(lang="Hindi" if lang == "hi" else "English")

    resp = client.chat.completions.create(
        model     = app.config["OPENAI_MODEL"],
        messages  = [
            {"role": "system", "content": system},
            {"role": "user",   "content": message},
        ],
        max_tokens  = app.config["MAX_TOKENS"],
        temperature = 0.7,
    )
    return resp.choices[0].message.content

# ─────────────────────────────────────────────────────
# ROUTES — HEALTH
# ─────────────────────────────────────────────────────
@app.route("/api/health", methods=["GET"])
def health():
    """Quick liveness / readiness check."""
    return jsonify({
        "status":    "ok",
        "version":   "2.0.0",
        "db_mode":   DB_MODE,
        "ai_engine": "openai" if (OPENAI_AVAILABLE and app.config["OPENAI_API_KEY"]) else "local",
        "timestamp": ts_now(),
    })

# ─────────────────────────────────────────────────────
# ROUTES — AUTH
# ─────────────────────────────────────────────────────
@app.route("/api/auth/register", methods=["POST"])
def register():
    """Register a new student account.

    Body (JSON):
        name     : str
        rollNo   : str
        email    : str
        password : str
        year     : str  (optional)
        branch   : str  (optional)
    """
    data = request.get_json(silent=True) or {}
    required = ["name", "rollNo", "email", "password"]

    if not all(k in data for k in required):
        return jsonify({"error": f"Missing fields: {required}"}), 400

    uid = data["rollNo"].strip().upper()

    # Duplicate check
    if DB_MODE == "mongodb":
        if db.users.find_one({"rollNo": uid}):
            return jsonify({"error": "Roll number already registered"}), 409
    else:
        if uid in MEM["users"]:
            return jsonify({"error": "Roll number already registered"}), 409

    user = {
        "id":        uid,
        "rollNo":    uid,
        "name":      data["name"].strip(),
        "email":     data["email"].strip().lower(),
        "password":  _hash(data["password"]),
        "role":      "student",
        "year":      data.get("year",   "Final Year"),
        "branch":    data.get("branch", "CSE"),
        "createdAt": ts_now(),
    }

    if DB_MODE == "mongodb":
        db.users.insert_one({**user, "_id": uid})
    else:
        mem_save_user(user)

    token    = _gen_token(uid, "student")
    safe_usr = {k: v for k, v in user.items() if k not in ("password", "_id")}

    return jsonify({"token": token, "user": safe_usr, "message": "Registered successfully"}), 201


@app.route("/api/auth/login", methods=["POST"])
def login():
    """Authenticate and return a JWT.

    Body (JSON):
        username : str   (roll number, email, or 'admin')
        password : str
    """
    data = request.get_json(silent=True) or {}
    raw  = data.get("username", "").strip()
    pwd  = data.get("password", "")

    if not raw or not pwd:
        return jsonify({"error": "username and password required"}), 400

    uid = raw.upper()

    # ── Hardcoded admin shortcut ──────────────────
    if raw.lower() == "admin" and pwd == "admin123":
        token = _gen_token("ADMIN", "admin")
        return jsonify({
            "token": token,
            "user":  {"id":"ADMIN","name":"Dr. A.K. Verma","role":"admin","rollNo":"ADMIN001"},
        })

    # ── Database lookup ───────────────────────────
    if DB_MODE == "mongodb":
        user = db.users.find_one({"rollNo": uid})
        if not user:
            user = db.users.find_one({"email": raw.lower()})
    else:
        user = MEM["users"].get(uid)

    if not user or not _check(pwd, user["password"]):
        return jsonify({"error": "Invalid credentials"}), 401

    token    = _gen_token(user["id"], user["role"])
    safe_usr = {k: v for k, v in user.items() if k not in ("password", "_id")}

    return jsonify({"token": token, "user": safe_usr})


@app.route("/api/auth/me", methods=["GET"])
@auth_required
def me():
    """Return the current user's profile."""
    uid  = g.user["sub"]
    user = (db.users.find_one({"rollNo": uid}) if DB_MODE == "mongodb"
            else MEM["users"].get(uid))
    if not user:
        return jsonify({"error": "User not found"}), 404
    safe = {k: v for k, v in user.items() if k not in ("password", "_id")}
    return jsonify({"user": safe})

# ─────────────────────────────────────────────────────
# ROUTES — CHAT
# ─────────────────────────────────────────────────────
def gemini_response(message: str, lang: str = "en") -> str:
    import json, urllib.request
    api_key = Config.GEMINI_API_KEY
    if not api_key:
        raise RuntimeError("No Gemini key")
    system = f"""You are EduBot AI — a friendly helpful college assistant for B.Tech students in India.
Personality: Talk like a smart helpful friend/senior. Casual warm tone. Use yaar bhai naturally. Use emojis.
Language: User Hindi likhe to Hindi reply karo. English to English. Hinglish to Hinglish.
Help with ANYTHING: general talk jokes motivation coding life advice
College info: Timetable exams attendance faculty placements fees events library hostel
College data BTech CSE Final Year: Mid sem March 15-22, End sem May 10-25, TCS 3.5-7 LPA, Amazon 18-28 LPA, Google 28-42 LPA, Fees 57500/sem, Min attendance 75%
Never say you are Gemini or made by Google. You are EduBot AI."""
    url  = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    body = json.dumps({
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{"parts": [{"text": message}], "role": "user"}],
        "generationConfig": {"temperature": 0.9, "maxOutputTokens": 500}
    }).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=10) as res:
        data = json.loads(res.read().decode())
        return data["candidates"][0]["content"]["parts"][0]["text"]


@app.route("/api/chat", methods=["POST"])
def chat():
    data    = request.get_json(silent=True) or {}
    message = data.get("message", "").strip()
    lang    = data.get("language", "en")

    if not message:
        return jsonify({"error": "message is required"}), 400

    intent = detect_intent(message)

    # Log query
    query_doc = {
        "userId":    "guest",
        "message":   message,
        "intent":    intent,
        "language":  lang,
        "timestamp": ts_now(),
    }
    if DB_MODE == "mongodb":
        db.queries.insert_one(query_doc)
    else:
        MEM["queries"].append(query_doc)

    # AI response: Gemini → OpenAI → local fallback
    source   = "local"
    response = ""

    # 1. Pehle Gemini try karo
    try:
        response = gemini_response(message, lang)
        source   = "gemini"
    except Exception as exc:
        app.logger.warning(f"Gemini error: {exc}")

    # 2. Gemini fail → OpenAI try karo
    if not response and OPENAI_AVAILABLE and app.config.get("OPENAI_API_KEY"):
        try:
            response = openai_response(message, lang)
            source   = "openai"
        except Exception as exc:
            app.logger.warning(f"OpenAI error: {exc}")

    # 3. Dono fail → local KB
    if not response:
        response = local_response(intent, lang)
        source   = "local"

    return jsonify({
        "response": response,
        "intent":   intent,
        "source":   source,
    })


@app.route("/api/chat/history", methods=["GET"])
@auth_required
def get_history():
    """Return saved chat sessions for the logged-in user."""
    uid = g.user["sub"]
    if DB_MODE == "mongodb":
        chats = list(db.chats.find({"userId": uid}, {"_id": 0}).sort("updatedAt", -1))
    else:
        chats = MEM["chats"].get(uid, [])
    return jsonify({"chats": chats})


@app.route("/api/chat/history", methods=["POST"])
@auth_required
def save_history():
    """Upsert a chat session."""
    data    = request.get_json(silent=True) or {}
    uid     = g.user["sub"]
    chat_id = data.get("id") or safe_id()

    doc = {
        "id":        chat_id,
        "userId":    uid,
        "title":     data.get("title", "New Chat"),
        "messages":  data.get("messages", []),
        "updatedAt": ts_now(),
    }

    if DB_MODE == "mongodb":
        db.chats.update_one({"id": chat_id, "userId": uid}, {"$set": doc}, upsert=True)
    else:
        user_chats = MEM["chats"].setdefault(uid, [])
        idx = next((i for i, c in enumerate(user_chats) if c["id"] == chat_id), None)
        if idx is not None:
            user_chats[idx] = doc
        else:
            user_chats.insert(0, doc)

    return jsonify({"message": "Saved", "chat": doc})


@app.route("/api/chat/history/<chat_id>", methods=["DELETE"])
@auth_required
def delete_chat(chat_id):
    uid = g.user["sub"]
    if DB_MODE == "mongodb":
        db.chats.delete_one({"id": chat_id, "userId": uid})
    else:
        MEM["chats"][uid] = [c for c in MEM["chats"].get(uid, []) if c["id"] != chat_id]
    return jsonify({"message": "Deleted"})

# ─────────────────────────────────────────────────────
# ROUTES — NOTICES
# ─────────────────────────────────────────────────────
@app.route("/api/notices", methods=["GET"])
def get_notices():
    """Public — list all active notices."""
    if DB_MODE == "mongodb":
        notices = list(db.notices.find({"isActive": True}, {"_id": 0}).sort("createdAt", -1))
    else:
        notices = [n for n in MEM["notices"] if n.get("isActive")]
    return jsonify({"notices": notices})


@app.route("/api/notices", methods=["POST"])
@admin_required
def add_notice():
    """Admin — create a new notice."""
    data = request.get_json(silent=True) or {}
    if not data.get("title"):
        return jsonify({"error": "title is required"}), 400

    notice = {
        "id":        safe_id(),
        "title":     data["title"],
        "content":   data.get("content", ""),
        "category":  data.get("category", "General"),
        "isActive":  True,
        "createdAt": ts_now(),
        "createdBy": g.user["sub"],
    }

    if DB_MODE == "mongodb":
        db.notices.insert_one({**notice, "_id": notice["id"]})
    else:
        MEM["notices"].insert(0, notice)

    return jsonify({"message": "Notice added", "notice": notice}), 201


@app.route("/api/notices/<notice_id>", methods=["PUT"])
@admin_required
def update_notice(notice_id):
    data = request.get_json(silent=True) or {}
    if DB_MODE == "mongodb":
        db.notices.update_one({"id": notice_id}, {"$set": data})
    else:
        for i, n in enumerate(MEM["notices"]):
            if n["id"] == notice_id:
                MEM["notices"][i] = {**n, **data}
                break
    return jsonify({"message": "Updated"})


@app.route("/api/notices/<notice_id>", methods=["DELETE"])
@admin_required
def delete_notice(notice_id):
    if DB_MODE == "mongodb":
        db.notices.delete_one({"id": notice_id})
    else:
        MEM["notices"] = [n for n in MEM["notices"] if n["id"] != notice_id]
    return jsonify({"message": "Deleted"})

# ─────────────────────────────────────────────────────
# ROUTES — FAQs
# ─────────────────────────────────────────────────────
@app.route("/api/faqs", methods=["GET"])
def get_faqs():
    """Public — list all FAQs (optionally filtered by category)."""
    cat = request.args.get("category")
    if DB_MODE == "mongodb":
        query  = {"category": cat} if cat else {}
        faqs   = list(db.faqs.find(query, {"_id": 0}))
    else:
        faqs = MEM["faqs"]
        if cat:
            faqs = [f for f in faqs if f.get("category") == cat]
    return jsonify({"faqs": faqs})


@app.route("/api/faqs", methods=["POST"])
@admin_required
def add_faq():
    data = request.get_json(silent=True) or {}
    if not data.get("question") or not data.get("answer"):
        return jsonify({"error": "question and answer required"}), 400

    faq = {
        "id":        safe_id(),
        "question":  data["question"],
        "answer":    data["answer"],
        "category":  data.get("category", "General"),
        "views":     0,
        "createdAt": ts_now(),
    }
    if DB_MODE == "mongodb":
        db.faqs.insert_one({**faq, "_id": faq["id"]})
    else:
        MEM["faqs"].append(faq)

    return jsonify({"message": "FAQ added", "faq": faq}), 201


@app.route("/api/faqs/<faq_id>", methods=["PUT"])
@admin_required
def update_faq(faq_id):
    data = request.get_json(silent=True) or {}
    if DB_MODE == "mongodb":
        db.faqs.update_one({"id": faq_id}, {"$set": data})
    else:
        for i, f in enumerate(MEM["faqs"]):
            if f["id"] == faq_id:
                MEM["faqs"][i] = {**f, **data}
                break
    return jsonify({"message": "Updated"})


@app.route("/api/faqs/<faq_id>", methods=["DELETE"])
@admin_required
def delete_faq(faq_id):
    if DB_MODE == "mongodb":
        db.faqs.delete_one({"id": faq_id})
    else:
        MEM["faqs"] = [f for f in MEM["faqs"] if f["id"] != faq_id]
    return jsonify({"message": "Deleted"})

# ─────────────────────────────────────────────────────
# ROUTES — ADMIN
# ─────────────────────────────────────────────────────
@app.route("/api/admin/queries", methods=["GET"])
@admin_required
def admin_queries():
    """Return recent student queries."""
    limit = int(request.args.get("limit", 100))
    if DB_MODE == "mongodb":
        qs = list(db.queries.find({}, {"_id": 0}).sort("timestamp", -1).limit(limit))
    else:
        qs = MEM["queries"][-limit:][::-1]
    return jsonify({"queries": qs, "total": len(qs)})


@app.route("/api/admin/stats", methods=["GET"])
@admin_required
def admin_stats():
    """Dashboard analytics."""
    if DB_MODE == "mongodb":
        total_users   = db.users.count_documents({})
        total_queries = db.queries.count_documents({})
        active_notices= db.notices.count_documents({"isActive": True})
        total_faqs    = db.faqs.count_documents({})
        pipeline = [{"$group": {"_id": "$intent", "count": {"$sum": 1}}}]
        intent_raw = list(db.queries.aggregate(pipeline))
        intent_bkd = {r["_id"]: r["count"] for r in intent_raw}
    else:
        total_users    = len(MEM["users"])
        total_queries  = len(MEM["queries"])
        active_notices = sum(1 for n in MEM["notices"] if n.get("isActive"))
        total_faqs     = len(MEM["faqs"])
        intent_bkd: Dict[str, int] = {}
        for q in MEM["queries"]:
            k = q.get("intent", "unknown")
            intent_bkd[k] = intent_bkd.get(k, 0) + 1

    return jsonify({
        "totalUsers":    total_users,
        "totalQueries":  total_queries,
        "activeNotices": active_notices,
        "totalFaqs":     total_faqs,
        "intentBreakdown": intent_bkd,
    })


@app.route("/api/admin/users", methods=["GET"])
@admin_required
def admin_users():
    """List all registered users (passwords omitted)."""
    if DB_MODE == "mongodb":
        users = list(db.users.find({}, {"_id": 0, "password": 0}))
    else:
        users = [{k: v for k, v in u.items() if k != "password"} for u in MEM["users"].values()]
    return jsonify({"users": users})

# ─────────────────────────────────────────────────────
# ROUTES — PDF UPLOAD & SUMMARIZE
# ─────────────────────────────────────────────────────
@app.route("/api/upload/pdf", methods=["POST"])
@auth_required
def upload_pdf():
    """Extract text from uploaded PDF and optionally summarize via OpenAI."""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    f = request.files["file"]
    if not f.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Only PDF files are accepted"}), 400

    if not PDF_AVAILABLE:
        return jsonify({
            "message": "PDF processing library not installed. Run: pip install pdfplumber",
            "summary": "PDF received but could not be processed. Please install pdfplumber.",
        })

    try:
        import pdfplumber, io
        with pdfplumber.open(io.BytesIO(f.read())) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages[:10])
        text = text[:4000]   # cap to avoid token overrun

        summary = ""
        if OPENAI_AVAILABLE and app.config.get("OPENAI_API_KEY") and text:
            try:
                client  = openai.OpenAI(api_key=app.config["OPENAI_API_KEY"])
                resp    = client.chat.completions.create(
                    model    = app.config["OPENAI_MODEL"],
                    messages = [
                        {"role": "system", "content": "Summarize the following academic document in 150 words, highlighting key topics."},
                        {"role": "user",   "content": text},
                    ],
                    max_tokens = 200,
                )
                summary = resp.choices[0].message.content
            except Exception as exc:
                summary = f"(OpenAI unavailable: {exc}) — Extracted {len(text)} characters from PDF."
        else:
            summary = f"Extracted {len(text.split())} words from PDF. Connect OpenAI to generate AI summaries."

        return jsonify({"text": text[:500] + "…", "summary": summary, "pages": len(pdf.pages)})

    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

# ─────────────────────────────────────────────────────
# ERROR HANDLERS
# ─────────────────────────────────────────────────────
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found", "hint": "Check /api/health"}), 404

@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({"error": "Method not allowed"}), 405

@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Internal server error", "detail": str(e)}), 500

# ─────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────
if __name__ == "__main__":
    seed_data()
    print("""
╔══════════════════════════════════════════════════╗
║        EduBot AI — Flask Backend v2.0            ║
║  DB     : {:<40}║
║  AI     : {:<40}║
║  URL    : http://localhost:5000                   ║
║  Health : http://localhost:5000/api/health        ║
╚══════════════════════════════════════════════════╝
""".format(
        DB_MODE,
        "Gemini Flash" if Config.GEMINI_API_KEY else "Local Keyword Engine"
    ))
    app.run(debug=False, port=5000, host="127.0.0.1")