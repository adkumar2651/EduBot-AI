"""
=============================================================
  EduBot AI — Flask Backend  (app.py)
  B.Tech Final Year Project — AI College Assistant Chatbot
=============================================================
  Author   : [Your Name]
  Version  : 2.0.0
  Stack    : Python 3.10+ · Flask · PyMongo · PyJWT · bcrypt
  Features : JWT Auth · Groq AI · MongoDB · Admin API · FAQs
=============================================================
"""


import hmac
import os
import secrets
from dotenv import load_dotenv
load_dotenv()
import datetime
from functools import wraps
from typing import Optional, Dict, List
from urllib.parse import urlsplit

import bcrypt
import jwt
from flask import Flask, request, jsonify, g
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    OpenAI,
    RateLimitError,
)
from pymongo.errors import PyMongoError

# Optional database and PDF integrations.
try:
    from pymongo import MongoClient
    MONGO_AVAILABLE = True
except ImportError:
    MONGO_AVAILABLE = False
    print("[WARN] pymongo not installed. Using in-memory storage.")

try:
    import pdfplumber          # PDF text extraction
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# ─────────────────────────────────────────────────────
# FLASK APP
# ─────────────────────────────────────────────────────
app = Flask(__name__)

# ─────────────────────────────────────────────────────
# ALLOWED FRONTEND ORIGINS (CORS)
# ─────────────────────────────────────────────────────
# A browser "origin" is scheme + host + port, with no path and no trailing slash.
PRODUCTION_FRONTEND_ORIGIN = "https://adkumar2651.github.io"
DEV_FRONTEND_ORIGINS = (
    "http://localhost:5501", "http://127.0.0.1:5501",   # VS Code Live Server
    "http://localhost:5500", "http://127.0.0.1:5500",
    "http://localhost:8080", "http://127.0.0.1:8080",
    "http://localhost:8000", "http://127.0.0.1:8000",
)


def _normalize_origin(value: str) -> str:
    """Reduce 'https://host/some/path/' to 'https://host' (browsers send no path)."""
    value = value.strip()
    parts = urlsplit(value)
    if parts.scheme and parts.netloc:
        return f"{parts.scheme}://{parts.netloc}"
    return value.rstrip("/")


def _build_allowed_origins() -> List[str]:
    """Built-in production + development origins, plus any extras from the
    FRONTEND_ORIGINS environment variable (comma-separated). The built-in
    ones are always kept, so a Render environment value cannot lock them out."""
    extras = os.environ.get("FRONTEND_ORIGINS", "").split(",")
    allowed: List[str] = []
    for origin in [PRODUCTION_FRONTEND_ORIGIN, *DEV_FRONTEND_ORIGINS, *extras]:
        origin = _normalize_origin(origin)
        if origin and origin not in allowed:
            allowed.append(origin)
    return allowed


# ─────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────
class Config:
    SECRET_KEY        = os.environ.get("SECRET_KEY") or secrets.token_urlsafe(32)
    GROQ_API_KEY      = os.environ.get("GROQ_API_KEY", "")
    GROQ_MODEL        = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
    GROQ_TIMEOUT_SECONDS = float(os.environ.get("GROQ_TIMEOUT_SECONDS", "30"))
    GROQ_MAX_TOKENS   = int(os.environ.get("GROQ_MAX_TOKENS", "800"))
    ADMIN_USERNAME    = os.environ.get("ADMIN_USERNAME", "")
    ADMIN_PASSWORD    = os.environ.get("ADMIN_PASSWORD", "")
    MONGO_URI         = os.environ.get("MONGO_URI",      "mongodb://localhost:27017/")
    DB_NAME           = os.environ.get("DB_NAME",        "edubot_db")
    FRONTEND_ORIGINS  = _build_allowed_origins()
    RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")
    TOKEN_EXPIRY_DAYS = 30
    MAX_TOKENS        = 500

app.config.from_object(Config)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024
CORS(
    app,
    resources={
        r"/api/*": {"origins": app.config["FRONTEND_ORIGINS"]},
        r"/health": {"origins": app.config["FRONTEND_ORIGINS"]},
    },
    allow_headers=["Content-Type", "Authorization"],
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    max_age=600,   # browsers may cache the OPTIONS preflight answer for 10 minutes
)
print("[INFO] CORS allowed origins:", ", ".join(app.config["FRONTEND_ORIGINS"]))
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    storage_uri=app.config["RATELIMIT_STORAGE_URI"],
    default_limits=[],
)


@app.before_request
def enforce_chat_request_size():
    if request.endpoint == "chat" and request.content_length and request.content_length > 64 * 1024:
        return jsonify({"error": "Chat request is too large", "code": "request_too_large"}), 413

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
    except Exception:
        app.logger.warning("MongoDB unavailable; using in-memory storage.")
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
    """Populate demo notices and FAQs on startup."""
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
# ANALYTICS — keyword intent classification
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

def detect_intent(text: str) -> str:
    t = text.lower()
    for intent, keywords in INTENT_KEYWORDS.items():
        if any(k in t for k in keywords):
            return intent
    return "fallback"

# ─────────────────────────────────────────────────────
# ROUTES — HEALTH
# ─────────────────────────────────────────────────────
@app.route("/api/health", methods=["GET"])
@app.route("/health", methods=["GET"])
def health():
    """Quick liveness / readiness check."""
    return jsonify({
        "status":    "ok",
        "version":   "2.0.0",
        "db_mode":   DB_MODE,
        "ai_engine": "groq",
        "ai_configured": bool(app.config["GROQ_API_KEY"]),
        "timestamp": ts_now(),
    })

# ─────────────────────────────────────────────────────
# ROUTES — AUTH
# ─────────────────────────────────────────────────────
@app.route("/api/auth/register", methods=["POST"])
@limiter.limit("5 per hour", methods=["POST"])
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
    if not isinstance(data, dict):
        return jsonify({"error": "A JSON object is required", "code": "invalid_request"}), 400

    required = ["name", "rollNo", "email", "password"]

    if any(not isinstance(data.get(key), str) or not data[key].strip() for key in required):
        return jsonify({"error": "Name, roll number, email, and password are required", "code": "invalid_request"}), 400

    if len(data["name"].strip()) > 100 or len(data["rollNo"].strip()) > 40 or len(data["email"].strip()) > 254:
        return jsonify({"error": "One or more fields exceed the allowed length", "code": "invalid_request"}), 400
    if len(data["password"]) < 6 or len(data["password"].encode("utf-8")) > 72:
        return jsonify({"error": "Password must be between 6 and 72 bytes", "code": "invalid_request"}), 400

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
@limiter.limit("10 per minute", methods=["POST"])
def login():
    """Authenticate and return a JWT.

    Body (JSON):
        username : str   (roll number, email, or 'admin')
        password : str
    """
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({"error": "A JSON object is required", "code": "invalid_request"}), 400

    raw  = data.get("username", "")
    pwd  = data.get("password", "")

    if not isinstance(raw, str) or not isinstance(pwd, str) or not raw.strip() or not pwd:
        return jsonify({"error": "Username and password are required", "code": "invalid_request"}), 400

    raw = raw.strip()
    uid = raw.upper()

    admin_username = app.config["ADMIN_USERNAME"]
    admin_password = app.config["ADMIN_PASSWORD"]
    if (
        admin_username
        and admin_password
        and hmac.compare_digest(raw.casefold(), admin_username.casefold())
        and hmac.compare_digest(pwd, admin_password)
    ):
        token = _gen_token("ADMIN", "admin")
        return jsonify({
            "token": token,
            "user":  {"id": "ADMIN", "name": "Administrator", "role": "admin", "rollNo": "ADMIN001"},
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
class GroqProviderError(Exception):
    def __init__(self, code: str, status_code: int, public_message: str):
        self.code = code
        self.status_code = status_code
        self.public_message = public_message
        super().__init__(code)


def groq_response(messages: list[dict[str, str]]) -> str:
    api_key = app.config["GROQ_API_KEY"]
    if not api_key:
        raise GroqProviderError(
            "ai_not_configured",
            503,
            "The AI service is not configured. Please contact the site owner.",
        )

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1",
        timeout=app.config["GROQ_TIMEOUT_SECONDS"],
    )
    try:
        completion = client.chat.completions.create(
            model=app.config["GROQ_MODEL"],
            messages=messages,
            max_tokens=app.config["GROQ_MAX_TOKENS"],
            temperature=0.7,
        )
    except AuthenticationError as exc:
        raise GroqProviderError(
            "ai_invalid_credentials",
            502,
            "The AI service credentials are invalid. Please contact the site owner.",
        ) from exc
    except RateLimitError as exc:
        raise GroqProviderError(
            "ai_rate_limited",
            429,
            "The AI service is busy. Please try again shortly.",
        ) from exc
    except APITimeoutError as exc:
        raise GroqProviderError(
            "ai_timeout",
            503,
            "The AI service timed out. Please try again.",
        ) from exc
    except APIConnectionError as exc:
        raise GroqProviderError(
            "ai_unavailable",
            503,
            "The AI service is temporarily unavailable. Please try again.",
        ) from exc
    except APIStatusError as exc:
        if exc.status_code in (401, 403):
            raise GroqProviderError(
                "ai_invalid_credentials",
                502,
                "The AI service credentials are invalid. Please contact the site owner.",
            ) from exc
        if exc.status_code == 429:
            raise GroqProviderError(
                "ai_rate_limited",
                429,
                "The AI service is busy. Please try again shortly.",
            ) from exc
        if exc.status_code >= 500:
            raise GroqProviderError(
                "ai_unavailable",
                503,
                "The AI service is temporarily unavailable. Please try again.",
            ) from exc
        raise GroqProviderError(
            "ai_provider_error",
            502,
            "The AI service could not process this request. Please try again.",
        ) from exc

    message = completion.choices[0].message.content
    if not isinstance(message, str) or not message.strip():
        raise GroqProviderError(
            "ai_empty_response",
            502,
            "The AI service returned an empty response. Please try again.",
        )
    return message.strip()


@app.route("/api/chat", methods=["POST"])
@limiter.limit("15 per minute", methods=["POST"])
def chat():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "A JSON object is required", "code": "invalid_request"}), 400
    if any(key.lower() in {"api_key", "apikey", "groq_api_key"} for key in data):
        return jsonify({
            "error": "AI credentials are managed by the service and must not be sent by visitors",
            "code": "client_credentials_not_allowed",
        }), 400

    message = data.get("message")
    if not isinstance(message, str) or not message.strip():
        return jsonify({"error": "A non-empty message is required", "code": "invalid_request"}), 400
    message = message.strip()
    if len(message) > 4000:
        return jsonify({"error": "Message exceeds the 4000 character limit", "code": "message_too_long"}), 400

    language = data.get("language", "auto")
    if not isinstance(language, str) or len(language) > 24:
        return jsonify({"error": "Language must be a short string", "code": "invalid_request"}), 400

    history = data.get("history", [])
    if not isinstance(history, list) or len(history) > 20:
        return jsonify({"error": "History must contain at most 20 messages", "code": "invalid_history"}), 400

    messages = [{
        "role": "system",
        "content": (
            "You are EduBot AI, a helpful and friendly assistant for college students. "
            "Answer general, educational, programming, reasoning, and college-related questions. "
            "Automatically detect whether the user is writing in English, Hindi, or Hinglish and "
            "reply naturally in the same language. Use prior conversation messages when relevant. "
            "Be accurate; do not invent college-specific facts when the user has not provided them."
        ),
    }]
    for item in history:
        if (
            not isinstance(item, dict)
            or item.get("role") not in {"user", "assistant"}
            or not isinstance(item.get("content"), str)
            or not item["content"].strip()
            or len(item["content"]) > 4000
        ):
            return jsonify({"error": "History contains an invalid message", "code": "invalid_history"}), 400
        messages.append({"role": item["role"], "content": item["content"].strip()})
    messages.append({"role": "user", "content": message})

    intent = detect_intent(message)
    query_doc = {
        "userId": "guest",
        "message": "[redacted]",
        "intent": intent,
        "language": language,
        "timestamp": ts_now(),
    }
    try:
        if DB_MODE == "mongodb":
            db.queries.insert_one(query_doc)
        else:
            MEM["queries"].append(query_doc)
    except PyMongoError:
        app.logger.warning("Chat analytics write failed.")

    try:
        response = groq_response(messages)
    except GroqProviderError as exc:
        app.logger.warning("Groq chat request failed: %s", exc.code)
        return jsonify({"error": exc.public_message, "code": exc.code}), exc.status_code

    return jsonify({"response": response, "intent": intent, "source": "groq"})


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
@limiter.limit("5 per minute", methods=["POST"])
def upload_pdf():
    """Extract and summarize an uploaded PDF with the owner-managed Groq service."""
    if "file" not in request.files:
        return jsonify({"error": "No file provided", "code": "missing_file"}), 400

    f = request.files["file"]
    if not f.filename or not f.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Only PDF files are accepted", "code": "invalid_file"}), 400

    if not PDF_AVAILABLE:
        return jsonify({
            "error": "PDF processing is unavailable on this service.",
            "code": "pdf_processing_unavailable",
        }), 503

    try:
        import pdfplumber, io
        with pdfplumber.open(io.BytesIO(f.read())) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages[:10])
        text = text[:4000]   # cap to avoid token overrun
        if not text.strip():
            return jsonify({
                "error": "No readable text was found in the PDF.",
                "code": "empty_pdf",
            }), 422

        try:
            summary = groq_response([
                {
                    "role": "system",
                    "content": "Summarize this academic document in about 150 words and highlight its key topics.",
                },
                {"role": "user", "content": text},
            ])
        except GroqProviderError as exc:
            app.logger.warning("PDF summarization failed: %s", exc.code)
            return jsonify({"error": exc.public_message, "code": exc.code}), exc.status_code

        return jsonify({"text": text[:500] + "…", "summary": summary, "pages": len(pdf.pages)})

    except Exception:
        app.logger.warning("PDF processing failed.")
        return jsonify({
            "error": "The PDF could not be processed. Make sure it is a valid, readable PDF.",
            "code": "pdf_processing_failed",
        }), 422

# ─────────────────────────────────────────────────────
# ERROR HANDLERS
# ─────────────────────────────────────────────────────
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found", "hint": "Check /api/health"}), 404

@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({"error": "Method not allowed"}), 405

@app.errorhandler(413)
def request_too_large(e):
    return jsonify({"error": "Request is too large", "code": "request_too_large"}), 413

@app.errorhandler(429)
def too_many_requests(e):
    return jsonify({
        "error": "Too many requests. Please wait a moment and try again.",
        "code": "rate_limited",
    }), 429

@app.errorhandler(500)
def server_error(e):
    app.logger.error("Unhandled server error.")
    return jsonify({"error": "Internal server error"}), 500

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
        "Groq" if Config.GROQ_API_KEY else "Groq not configured"
    ))
    app.run(debug=False, port=int(os.environ.get("PORT", "5000")), host="0.0.0.0")