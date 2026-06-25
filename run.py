"""
QuizGen - Application Entry Point
FILE: quizgen/backend/run.py
RUN:  cd quizgen/backend  →  py -3.12 run.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app


app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_ENV", "production") == "development"
    print(f"""
╔═════════════════════════════════════╗
║   QuizGen Platform API v2.0         ║
║   Running on http://localhost:{port}  ║
║   Mode: {"Development" if debug else "Production"}                 ║
╚═════════════════════════════════════╝
    """)
    app.run(debug=debug, host="0.0.0.0", port=port)

