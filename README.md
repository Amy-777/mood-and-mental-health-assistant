Mood and Mental Health Assistant
A polished Streamlit application for daily mood tracking, supportive reflection, trend analysis, affirmations, and optional AI-assisted conversation. The app is designed as a private wellbeing workspace with local SQLite storage, daily check-ins, a supportive companion, reminder settings, data export, and a safety-aware interaction model.

Core Features
Account creation and sign-in with local password hashing
Daily mood check-ins with mood score, stress, energy, sleep, emotions, gratitude, triggers, and coping notes
AI companion chat with a local supportive fallback and optional OpenAI Responses API integration
Personalized affirmations based on recent check-ins and preferred tone
Dashboard metrics for mood, stress, sleep, energy, and check-in streaks
Plotly-powered insights for mood trends, emotion frequency, weekday patterns, and trigger summaries
Routine and safety settings including reminder time, calming plan, warning signs, and emergency contact
Local-first data storage in SQLite with CSV and JSON export
Safety-aware messaging that escalates to crisis guidance when a message suggests immediate danger or self-harm
Tech Stack
Python 3
Streamlit
SQLite
Plotly
Pandas
Optional OpenAI API integration via the Responses API
Project Structure
streamlit_app.py: main Streamlit entrypoint
mental_health_assistant/database.py: user accounts, profiles, check-ins, affirmations, chat history, and export
mental_health_assistant/analytics.py: trend calculations, streaks, trigger summaries, and dashboard insights
mental_health_assistant/companion.py: supportive AI companion logic, crisis detection, affirmations, and optional OpenAI-backed replies
assets/app.css: custom product styling
assets/wellness-hero.png: custom hero image used in the sign-in experience
tests: database, analytics, and companion tests
Run Locally
Create and activate a virtual environment:
python3 -m venv .venv
source .venv/bin/activate
Install the dependencies:
pip install -r requirements.txt
Start the app:
streamlit run streamlit_app.py
Open the local URL shown by Streamlit, usually http://localhost:8501.
Optional OpenAI Integration
The app works fully without an API key by using its built-in supportive fallback mode.

To enable API-backed companion replies:

Copy .env.example values into your environment.
Create a local .env file or export the variables in your shell.
Set OPENAI_API_KEY.
Optionally set OPENAI_MODEL. The default in this project is gpt-5.4-mini.
The integration uses the OpenAI Responses API pattern from the official docs:

Models
Quickstart for Python
Text generation with the Responses API
Run Tests
python3 -m unittest discover -s tests
Safety Note
This app is built for emotional support, self-reflection, and habit awareness. It is not a medical device, therapist, or crisis service. Any market-facing deployment should add region-specific crisis resources, a reviewed privacy policy, explicit terms, observability, and a human escalation pathway before production use.
