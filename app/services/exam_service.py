"""
Exam Service – Country-based exam generation and management.
"""

from ..models.database import ExamModel, CountryModel

EXAM_TEMPLATES = {
    "India": [
        {"name": "JEE Main",    "description": "Joint Entrance Examination – Engineering", "duration": 180, "difficulty": "hard"},
        {"name": "NEET",        "description": "National Eligibility cum Entrance Test",    "duration": 200, "difficulty": "hard"},
        {"name": "UPSC CSE",    "description": "Civil Services Examination",                 "duration": 300, "difficulty": "hard"},
        {"name": "CAT",         "description": "Common Admission Test – MBA",                "duration": 120, "difficulty": "hard"},
        {"name": "GATE",        "description": "Graduate Aptitude Test in Engineering",      "duration": 180, "difficulty": "hard"},
        {"name": "SSC CGL",     "description": "Staff Selection Commission – Combined Graduate Level", "duration": 120, "difficulty": "medium"},
        {"name": "IBPS PO",     "description": "Institute of Banking Personnel Selection",   "duration": 120, "difficulty": "medium"},
        {"name": "RRB NTPC",    "description": "Railway Recruitment Board",                  "duration": 90,  "difficulty": "medium"},
    ],
    "United States": [
        {"name": "SAT",         "description": "Scholastic Assessment Test",                 "duration": 180, "difficulty": "medium"},
        {"name": "GRE",         "description": "Graduate Record Examination",                "duration": 205, "difficulty": "hard"},
        {"name": "GMAT",        "description": "Graduate Management Admission Test",         "duration": 187, "difficulty": "hard"},
        {"name": "LSAT",        "description": "Law School Admission Test",                  "duration": 175, "difficulty": "hard"},
        {"name": "MCAT",        "description": "Medical College Admission Test",             "duration": 375, "difficulty": "hard"},
        {"name": "USMLE",       "description": "United States Medical Licensing Exam",       "duration": 480, "difficulty": "hard"},
        {"name": "ACT",         "description": "American College Testing",                   "duration": 175, "difficulty": "medium"},
    ],
    "United Kingdom": [
        {"name": "A-Levels",    "description": "Advanced Level Qualifications",              "duration": 180, "difficulty": "hard"},
        {"name": "UCAT",        "description": "University Clinical Aptitude Test",          "duration": 120, "difficulty": "hard"},
        {"name": "IELTS",       "description": "International English Language Testing",     "duration": 165, "difficulty": "medium"},
        {"name": "BMAT",        "description": "BioMedical Admissions Test",                 "duration": 120, "difficulty": "hard"},
        {"name": "LNAT",        "description": "National Admissions Test for Law",           "duration": 135, "difficulty": "hard"},
    ],
    "Australia": [
        {"name": "ATAR",        "description": "Australian Tertiary Admission Rank",         "duration": 120, "difficulty": "medium"},
        {"name": "GAMSAT",      "description": "Graduate Medical School Admissions Test",    "duration": 318, "difficulty": "hard"},
        {"name": "UCAT ANZ",    "description": "University Clinical Aptitude Test",          "duration": 120, "difficulty": "hard"},
        {"name": "IELTS",       "description": "International English Language Testing",     "duration": 165, "difficulty": "medium"},
    ],
    "Canada": [
        {"name": "MCAT",        "description": "Medical College Admission Test",             "duration": 375, "difficulty": "hard"},
        {"name": "LSAT",        "description": "Law School Admission Test",                  "duration": 175, "difficulty": "hard"},
        {"name": "CELPIP",      "description": "Canadian English Language Proficiency",      "duration": 180, "difficulty": "medium"},
        {"name": "GRE",         "description": "Graduate Record Examination",                "duration": 205, "difficulty": "hard"},
        {"name": "IELTS",       "description": "International English Language Testing",     "duration": 165, "difficulty": "medium"},
    ],
    "Germany": [
        {"name": "TestDaF",     "description": "Test of German as a Foreign Language",      "duration": 180, "difficulty": "hard"},
        {"name": "TestAS",      "description": "Test for Academic Studies",                  "duration": 180, "difficulty": "hard"},
        {"name": "DSH",         "description": "German University Entrance Examination",     "duration": 240, "difficulty": "hard"},
        {"name": "Goethe C1",   "description": "Goethe-Institut German Certification",      "duration": 200, "difficulty": "hard"},
    ],
    "Japan": [
        {"name": "JLPT N1",     "description": "Japanese Language Proficiency Test",        "duration": 180, "difficulty": "hard"},
        {"name": "EJU",         "description": "Examination for Japanese University",        "duration": 125, "difficulty": "hard"},
        {"name": "JASSO",       "description": "Japan Student Services Org Exam",           "duration": 150, "difficulty": "medium"},
    ],
    "South Korea": [
        {"name": "CSAT (수능)", "description": "College Scholastic Ability Test",           "duration": 540, "difficulty": "hard"},
        {"name": "TOPIK II",    "description": "Test of Proficiency in Korean",             "duration": 180, "difficulty": "hard"},
        {"name": "IELTS",       "description": "International English Language Testing",     "duration": 165, "difficulty": "medium"},
    ],
    "France": [
        {"name": "BAC",         "description": "Baccalauréat Examination",                  "duration": 240, "difficulty": "hard"},
        {"name": "DELF B2",     "description": "Diplôme d'études en langue française",      "duration": 180, "difficulty": "medium"},
        {"name": "DALF C1",     "description": "Diplôme approfondi de langue française",    "duration": 240, "difficulty": "hard"},
        {"name": "Concours",    "description": "French Civil Service Examinations",         "duration": 300, "difficulty": "hard"},
    ],
    "Brazil": [
        {"name": "ENEM",        "description": "National High School Exam",                  "duration": 330, "difficulty": "hard"},
        {"name": "Vestibular",  "description": "University Entrance Examination",            "duration": 240, "difficulty": "hard"},
        {"name": "Fuvest",      "description": "University of São Paulo Entrance",          "duration": 240, "difficulty": "hard"},
    ],
    "Singapore": [
        {"name": "A-Levels",    "description": "GCE Advanced Level",                        "duration": 180, "difficulty": "hard"},
        {"name": "PSLE",        "description": "Primary School Leaving Examination",        "duration": 120, "difficulty": "medium"},
        {"name": "IELTS",       "description": "International English Language Testing",     "duration": 165, "difficulty": "medium"},
    ],
    "UAE": [
        {"name": "EmSAT",       "description": "Emirates Standardised Test",                "duration": 120, "difficulty": "medium"},
        {"name": "IELTS",       "description": "International English Language Testing",     "duration": 165, "difficulty": "medium"},
        {"name": "TOEFL",       "description": "Test of English as a Foreign Language",     "duration": 200, "difficulty": "medium"},
    ],
}

DEFAULT_EXAMS = [
    {"name": "General Knowledge", "description": "Comprehensive general knowledge test", "duration": 60, "difficulty": "medium"},
    {"name": "English Proficiency", "description": "English language assessment", "duration": 90, "difficulty": "medium"},
]


def get_or_create_exams_for_country(country_id: str) -> list[dict]:
    """Return exams for a country, creating DB entries if they don't exist."""
    country = CountryModel.get_by_id(country_id)
    if not country:
        return []

    country_name = country.get("name", "")
    templates = EXAM_TEMPLATES.get(country_name, DEFAULT_EXAMS)

    result = []
    for tmpl in templates:
        eid = ExamModel.upsert(
            name=tmpl["name"],
            country_id=country_id,
            description=tmpl["description"],
            duration=tmpl["duration"],
            difficulty=tmpl["difficulty"],
        )
        result.append({
            "_id": eid,
            "name": tmpl["name"],
            "description": tmpl["description"],
            "country_id": country_id,
            "duration": tmpl["duration"],
            "difficulty": tmpl["difficulty"],
            "offline": True,
            "online": True,
        })

    return result