"""
QuizGen – Database Models & MongoDB Atlas Setup
All collections, indexes, and model helpers live here.
"""
from dotenv import load_dotenv
load_dotenv()
from flask_pymongo import PyMongo
from werkzeug.security import generate_password_hash
from datetime import datetime
from bson import ObjectId
import os

mongo = PyMongo()


# ─────────────────────────────────────────────────────────────
# Initialisation
# ─────────────────────────────────────────────────────────────

def configure_database(app):
    """Attach MongoDB Atlas URI and initialise PyMongo."""
    uri = os.getenv("MONGO_URL")
    print("Mongo URI:", uri)
    app.config["MONGO_URI"] = uri
    mongo.init_app(app)
    print(f"[DB] Connecting to: {uri.split('@')[-1] if '@' in uri else uri}")
    return mongo


def init_db():
    """Create indexes and seed reference data."""
    try:
        mongo.db.command("ping")
        print("[DB] ✅ Connected to MongoDB Atlas")
    except Exception as e:
        print(f"[DB] ❌ Connection failed: {e}")
        return False

    # ── Indexes ──────────────────────────────────────────────
    mongo.db.users.create_index("username", unique=True)
    mongo.db.users.create_index("email", unique=True, sparse=True)

    mongo.db.institute_exams.create_index("exam_id", unique=True)
    mongo.db.institute_exams.create_index("institute_id")
    mongo.db.institute_exams.create_index([("created_at", -1)])

    mongo.db.exam_attempts.create_index([("student_id", 1), ("exam_id", 1)])
    mongo.db.exam_attempts.create_index([("exam_id", 1)])

    mongo.db.exam_reports.create_index("report_id", unique=True)
    mongo.db.exam_reports.create_index("attempt_id")
    mongo.db.exam_reports.create_index([("student_id", 1), ("generated_at", -1)])

    mongo.db.test_results.create_index([("user_id", 1), ("submitted_at", -1)])
    mongo.db.cheating_logs.create_index([("attempt_id", 1), ("timestamp", -1)])

    # ── Seed countries ───────────────────────────────────────
    if mongo.db.countries.count_documents({}) == 0:
        countries = [
            {"name": "India",          "code": "IN", "flag": "🇮🇳"},
            {"name": "United States",  "code": "US", "flag": "🇺🇸"},
            {"name": "United Kingdom", "code": "GB", "flag": "🇬🇧"},
            {"name": "Australia",      "code": "AU", "flag": "🇦🇺"},
            {"name": "Canada",         "code": "CA", "flag": "🇨🇦"},
            {"name": "Germany",        "code": "DE", "flag": "🇩🇪"},
            {"name": "France",         "code": "FR", "flag": "🇫🇷"},
            {"name": "Japan",          "code": "JP", "flag": "🇯🇵"},
            {"name": "South Korea",    "code": "KR", "flag": "🇰🇷"},
            {"name": "Brazil",         "code": "BR", "flag": "🇧🇷"},
            {"name": "Singapore",      "code": "SG", "flag": "🇸🇬"},
            {"name": "UAE",            "code": "AE", "flag": "🇦🇪"},
        ]
        for c in countries:
            c["created_at"] = datetime.utcnow()
        mongo.db.countries.insert_many(countries)
        print("[DB] Seeded countries")

    print("[DB] ✅ Database initialised")
    return True


# ─────────────────────────────────────────────────────────────
# Helper: safe ObjectId conversion
# ─────────────────────────────────────────────────────────────

def to_oid(val):
    try:
        return ObjectId(val)
    except Exception:
        return None


def doc_to_json(doc):
    """Recursively make a MongoDB document JSON-serialisable."""
    if doc is None:
        return None
    if isinstance(doc, list):
        return [doc_to_json(d) for d in doc]
    if isinstance(doc, dict):
        out = {}
        for k, v in doc.items():
            if isinstance(v, ObjectId):
                out[k] = str(v)
            elif isinstance(v, datetime):
                out[k] = v.isoformat()
            elif isinstance(v, (dict, list)):
                out[k] = doc_to_json(v)
            else:
                out[k] = v
        return out
    return doc


# ─────────────────────────────────────────────────────────────
# Model classes (thin wrappers over mongo collections)
# ─────────────────────────────────────────────────────────────

class UserModel:
    COL = "users"

    @classmethod
    def find_by_username(cls, username):
        return mongo.db[cls.COL].find_one({"username": username})

    @classmethod
    def find_by_id(cls, uid):
        return mongo.db[cls.COL].find_one({"_id": to_oid(uid)})

    @classmethod
    def create(cls, username, hashed_password, email=None, role="student"):
        doc = {
            "username": username,
            "password": hashed_password,
            "email": email,
            "role": role,                     # student | institute | admin
            "profile": {
                "display_name": username,
                "avatar_color": "#6366f1",
            },
            "stats": {
                "total_exams": 0,
                "avg_score": 0,
                "streak_days": 0,
            },
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        result = mongo.db[cls.COL].insert_one(doc)
        return str(result.inserted_id)

    @classmethod
    def update_stats(cls, uid, stats_delta: dict):
        mongo.db[cls.COL].update_one(
            {"_id": to_oid(uid)},
            {"$inc": stats_delta, "$set": {"updated_at": datetime.utcnow()}}
        )


class CountryModel:
    COL = "countries"

    @classmethod
    def get_all(cls):
        return doc_to_json(list(mongo.db[cls.COL].find().sort("name", 1)))

    @classmethod
    def get_by_id(cls, cid):
        return doc_to_json(mongo.db[cls.COL].find_one({"_id": to_oid(cid)}))


class ExamModel:
    """Standard country-based exams (not institute exams)."""
    COL = "exams"

    @classmethod
    def find_by_name_and_country(cls, name, country_id):
        return mongo.db[cls.COL].find_one({"name": name, "country_id": to_oid(country_id)})

    @classmethod
    def get_by_country(cls, country_id):
        return doc_to_json(list(mongo.db[cls.COL].find({"country_id": to_oid(country_id)})))

    @classmethod
    def get_by_id(cls, eid):
        return doc_to_json(mongo.db[cls.COL].find_one({"_id": to_oid(eid)}))

    @classmethod
    def upsert(cls, name, country_id, description, duration, difficulty):
        existing = cls.find_by_name_and_country(name, country_id)
        if existing:
            return str(existing["_id"])
        doc = {
            "name": name, "country_id": to_oid(country_id),
            "description": description, "duration": duration,
            "difficulty": difficulty, "offline": True, "online": True,
            "created_at": datetime.utcnow()
        }
        return str(mongo.db[cls.COL].insert_one(doc).inserted_id)


class InstituteExamModel:
    COL = "institute_exams"

    @classmethod
    def create(cls, doc):
        result = mongo.db[cls.COL].insert_one(doc)
        return str(result.inserted_id)

    @classmethod
    def find_by_exam_id(cls, exam_id):
        return doc_to_json(mongo.db[cls.COL].find_one({"exam_id": exam_id}))

    @classmethod
    def get_all(cls, query=None):
        return doc_to_json(list(mongo.db[cls.COL].find(query or {}).sort("created_at", -1)))

    @classmethod
    def get_by_institute(cls, institute_id):
        return doc_to_json(list(
            mongo.db[cls.COL].find({"institute_id": institute_id}).sort("created_at", -1)
        ))

    @classmethod
    def update(cls, exam_id, update_data):
        return mongo.db[cls.COL].update_one({"exam_id": exam_id}, {"$set": update_data})

    @classmethod
    def delete(cls, exam_id):
        return mongo.db[cls.COL].delete_one({"exam_id": exam_id})


class AttemptModel:
    COL = "exam_attempts"

    @classmethod
    def create(cls, doc):
        return str(mongo.db[cls.COL].insert_one(doc).inserted_id)

    @classmethod
    def find_by_id(cls, aid):
        return doc_to_json(mongo.db[cls.COL].find_one({"_id": to_oid(aid)}))

    @classmethod
    def find_by_student_and_exam(cls, student_id, exam_id):
        return mongo.db[cls.COL].find_one({"student_id": student_id, "exam_id": exam_id})

    @classmethod
    def update(cls, aid, data):
        return mongo.db[cls.COL].update_one({"_id": to_oid(aid)}, {"$set": data})

    @classmethod
    def get_student_history(cls, student_id):
        return doc_to_json(list(
            mongo.db[cls.COL].find({"student_id": student_id}).sort("started_at", -1)
        ))


class ReportModel:
    COL = "exam_reports"

    @classmethod
    def create(cls, doc):
        return str(mongo.db[cls.COL].insert_one(doc).inserted_id)

    @classmethod
    def find_by_report_id(cls, report_id):
        return doc_to_json(
            mongo.db[cls.COL].find_one({"report_id": report_id})
            or mongo.db[cls.COL].find_one({"_id": to_oid(report_id)})
        )

    @classmethod
    def find_by_attempt(cls, attempt_id):
        return doc_to_json(mongo.db[cls.COL].find_one({"attempt_id": attempt_id}))

    @classmethod
    def get_student_reports(cls, student_id, limit=20):
        return doc_to_json(list(
            mongo.db[cls.COL].find({"student_id": student_id})
            .sort("generated_at", -1).limit(limit)
        ))


class TestResultModel:
    COL = "test_results"

    @classmethod
    def create(cls, doc):
        return str(mongo.db[cls.COL].insert_one(doc).inserted_id)

    @classmethod
    def get_user_results(cls, user_id, limit=50):
        return doc_to_json(list(
            mongo.db[cls.COL].find({"user_id": str(user_id)})
            .sort("submitted_at", -1).limit(limit)
        ))

    @classmethod
    def get_user_stats(cls, user_id):
        pipeline = [
            {"$match": {"user_id": str(user_id)}},
            {"$group": {
                "_id": None,
                "total_exams":    {"$sum": 1},
                "avg_score":      {"$avg": "$score"},
                "best_score":     {"$max": "$score"},
                "total_questions":{"$sum": "$total_questions"},
                "total_correct":  {"$sum": "$correct_answers"},
            }}
        ]
        result = list(mongo.db[cls.COL].aggregate(pipeline))
        return result[0] if result else {}


class CheatingLogModel:
    COL = "cheating_logs"

    @classmethod
    def create(cls, doc):
        mongo.db[cls.COL].insert_one(doc)

    @classmethod
    def get_by_attempt(cls, attempt_id):
        return doc_to_json(list(
            mongo.db[cls.COL].find({"attempt_id": attempt_id}).sort("timestamp", 1)
        ))
