# Mood and Mental Health Assistant

A polished Streamlit application for daily mood tracking, supportive reflection, trend analysis, affirmations, and optional AI-assisted conversation. The app is designed as a private wellbeing workspace with local SQLite storage, daily check-ins, a supportive companion, reminder settings, data export, and a safety-aware interaction model.

## Core Features

- Account creation and sign-in with local password hashing
- Daily mood check-ins with mood score, stress, energy, sleep, emotions, gratitude, triggers, and coping notes
- AI companion chat with a local supportive fallback and optional OpenAI Responses API integration
- Personalized affirmations based on recent check-ins and preferred tone
- Dashboard metrics for mood, stress, sleep, energy, and check-in streaks
- Plotly-powered insights for mood trends, emotion frequency, weekday patterns, and trigger summaries
- Routine and safety settings including reminder time, calming plan, warning signs, and emergency contact
- Local-first data storage in SQLite with CSV and JSON export
- Safety-aware messaging that escalates to crisis guidance when a message suggests immediate danger or self-harm

## Tech Stack

- Python 3
- Streamlit
- SQLite
- Plotly
- Pandas
- Optional OpenAI API integration via the Responses API

## Project Structure

- [streamlit_app.py](/Users/amisharai/mood-and-mental-health-assistant/streamlit_app.py): main Streamlit entrypoint
- [mental_health_assistant/database.py](/Users/amisharai/mood-and-mental-health-assistant/mental_health_assistant/database.py): user accounts, profiles, check-ins, affirmations, chat history, and export
- [mental_health_assistant/analytics.py](/Users/amisharai/mood-and-mental-health-assistant/mental_health_assistant/analytics.py): trend calculations, streaks, trigger summaries, and dashboard insights
- [mental_health_assistant/companion.py](/Users/amisharai/mood-and-mental-health-assistant/mental_health_assistant/companion.py): supportive AI companion logic, crisis detection, affirmations, and optional OpenAI-backed replies
- [assets/app.css](/Users/amisharai/mood-and-mental-health-assistant/assets/app.css): custom product styling
- [assets/wellness-hero.png](/Users/amisharai/mood-and-mental-health-assistant/assets/wellness-hero.png): custom hero image used in the sign-in experience
- [tests](/Users/amisharai/mood-and-mental-health-assistant/tests): database, analytics, and companion tests

## Run Locally

1. Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install the dependencies:

```bash
pip install -r requirements.txt
```

3. Start the app:

```bash
streamlit run streamlit_app.py
```

4. Open the local URL shown by Streamlit, usually `http://localhost:8501`.

## Optional OpenAI Integration

The app works fully without an API key by using its built-in supportive fallback mode.

To enable API-backed companion replies:

1. Copy [.env.example](/Users/amisharai/mood-and-mental-health-assistant/.env.example) values into your environment.
2. Create a local `.env` file or export the variables in your shell.
3. Set `OPENAI_API_KEY`.
4. Optionally set `OPENAI_MODEL`. The default in this project is `gpt-5.4-mini`.

The integration uses the OpenAI Responses API pattern from the official docs:

- [Models](https://developers.openai.com/api/docs/models)
- [Quickstart for Python](https://developers.openai.com/api/docs/quickstart?lang=python)
- [Text generation with the Responses API](https://developers.openai.com/api/docs/guides/text?api-mode=responses&lang=python)

## Run Tests

```bash
python3 -m unittest discover -s tests
```

## Safety Note

This app is built for emotional support, self-reflection, and habit awareness. It is not a medical device, therapist, or crisis service. Any market-facing deployment should add region-specific crisis resources, a reviewed privacy policy, explicit terms, observability, and a human escalation pathway before production use.
