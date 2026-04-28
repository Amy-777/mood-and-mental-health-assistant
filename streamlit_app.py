from __future__ import annotations

from datetime import date, datetime, time
import os

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

from mental_health_assistant.analytics import (
    build_entries_frame,
    build_snapshot,
    emotion_counts,
    mood_label_from_score,
    summarize_triggers,
    to_csv_bytes,
    to_json_bytes,
)
from mental_health_assistant.companion import CompanionEngine, get_openai_api_key, get_openai_model
from mental_health_assistant.database import DatabaseManager
from mental_health_assistant.ui import HERO_IMAGE_PATH, load_css, wellness_badge

load_dotenv()


APP_TITLE = "Mood and Mental Health Assistant"
MOOD_SCORE_OPTIONS = list(range(1, 11))
EMOTION_OPTIONS = [
    "Calm",
    "Hopeful",
    "Anxious",
    "Tired",
    "Lonely",
    "Frustrated",
    "Overwhelmed",
    "Motivated",
    "Numb",
    "Irritable",
    "Grateful",
    "Restless",
]
AGE_GROUPS = [
    "Teen",
    "College student",
    "Young professional",
    "Adult",
    "Prefer not to say",
]
AFFIRMATION_STYLES = ["gentle", "grounded", "hopeful"]
PLOTLY_CONFIG = {
    "displayModeBar": False,
    "displaylogo": False,
    "responsive": True,
}


st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🫶",
    layout="wide",
)
load_css()


@st.cache_resource
def get_database() -> DatabaseManager:
    return DatabaseManager()


@st.cache_resource
def get_companion_engine() -> CompanionEngine:
    api_key = get_openai_api_key()
    if not api_key:
        try:
            api_key = st.secrets.get("OPENAI_API_KEY")
        except Exception:
            api_key = os.getenv("OPENAI_API_KEY")
    return CompanionEngine(
        api_key=api_key,
        model=get_openai_model(),
    )


db = get_database()
engine = get_companion_engine()


def ensure_session_state() -> None:
    st.session_state.setdefault("user_id", None)
    st.session_state.setdefault("urgent_banner", None)


def parse_reminder_time(raw_value: object) -> time:
    try:
        return datetime.strptime(str(raw_value or "20:00"), "%H:%M").time()
    except ValueError:
        return time(20, 0)


def render_auth_screen() -> None:
    left, right = st.columns([1.25, 0.95], gap="large")

    with left:
        st.markdown('<div class="hero-panel">', unsafe_allow_html=True)
        st.markdown(
            """
            <div class="hero-copy">
                <span class="eyebrow">Private wellbeing workspace</span>
                <h1>Mood and Mental Health Assistant</h1>
                <p>
                    Track your emotional patterns, reflect through daily check-ins,
                    talk with a supportive companion, and review your trends in one
                    calm, structured place.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if HERO_IMAGE_PATH.exists():
            st.image(str(HERO_IMAGE_PATH), use_container_width=True)
        st.markdown(
            """
            <div class="feature-grid">
                <div class="feature-card"><strong>Daily check-ins</strong><span>Mood, stress, sleep, energy, emotions, and journaling in one flow.</span></div>
                <div class="feature-card"><strong>AI companion</strong><span>Supportive reflection with optional OpenAI-powered replies and a local fallback.</span></div>
                <div class="feature-card"><strong>Insight dashboard</strong><span>Trends, trigger patterns, emotion frequency, and wellbeing signals over time.</span></div>
                <div class="feature-card"><strong>Privacy-first</strong><span>Local SQLite storage, export controls, and a clear non-diagnostic safety posture.</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown('<div class="auth-card">', unsafe_allow_html=True)
        login_tab, register_tab = st.tabs(["Sign in", "Create account"])

        with login_tab:
            with st.form("login_form", clear_on_submit=False):
                login_email = st.text_input("Email", placeholder="you@example.com")
                login_password = st.text_input("Password", type="password")
                login_submitted = st.form_submit_button("Sign in", use_container_width=True)
            if login_submitted:
                user = db.authenticate_user(login_email, login_password)
                if not user:
                    st.error("Those credentials did not match an account.")
                else:
                    st.session_state.user_id = user["id"]
                    st.session_state.urgent_banner = None
                    st.rerun()

        with register_tab:
            with st.form("register_form", clear_on_submit=False):
                display_name = st.text_input("Display name", placeholder="Your name")
                email = st.text_input("Email address", placeholder="you@example.com")
                password = st.text_input("Password", type="password")
                confirm_password = st.text_input("Confirm password", type="password")
                register_submitted = st.form_submit_button("Create account", use_container_width=True)
            if register_submitted:
                if password != confirm_password:
                    st.error("Passwords do not match.")
                else:
                    try:
                        user_id = db.register_user(display_name, email, password)
                    except ValueError as error:
                        st.error(str(error))
                    else:
                        st.session_state.user_id = user_id
                        st.session_state.urgent_banner = None
                        st.success("Your account is ready. Let’s set up your wellbeing space.")
                        st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)


def render_sidebar(user: dict[str, object], profile: dict[str, object]) -> str:
    with st.sidebar:
        st.markdown(
            f"""
            <div class="sidebar-profile">
                <span class="eyebrow">Signed in</span>
                <h3>{user['display_name']}</h3>
                <p>{user['email']}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption(
            "AI mode: OpenAI Responses API" if engine.api_key else "AI mode: local supportive fallback"
        )
        page = st.radio(
            "Workspace",
            [
                "Dashboard",
                "Daily Check-In",
                "AI Companion",
                "Insights",
                "Routine & Safety",
                "Data & Privacy",
            ],
            label_visibility="collapsed",
        )
        if st.button("Sign out", use_container_width=True):
            st.session_state.user_id = None
            st.session_state.urgent_banner = None
            st.rerun()

        if profile.get("reminders_enabled", 1):
            st.markdown(
                f"""
                <div class="sidebar-note">
                    <strong>Check-in reminder</strong>
                    <span>{profile.get('reminder_time', '20:00')}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        return page


def render_dashboard(user: dict[str, object], profile: dict[str, object], entries: list[dict[str, object]]) -> None:
    snapshot = build_snapshot(entries, profile)
    latest = snapshot["latest"]

    st.markdown(
        f"""
        <div class="page-header">
            <span class="eyebrow">Daily overview</span>
            <h1>Welcome back, {user['display_name']}</h1>
            <p>Your emotional dashboard is shaped by recent check-ins, reflection notes, and the routines you said matter most.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.session_state.urgent_banner:
        st.error(st.session_state.urgent_banner)

    risk = snapshot["risk"]
    risk_level_class = risk["level"].replace("_", "-")
    st.markdown(
        f"""
        <div class="status-banner status-{risk_level_class}">
            <strong>{wellness_badge(risk['level'])}</strong>
            <span>{risk['body']}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if snapshot["reminder_due"]:
        st.info("Your reminder window has arrived. A short check-in now will make your dashboard much more useful.")

    metric_columns = st.columns(5)
    metric_columns[0].metric("7-day mood avg", snapshot["average_mood"] or "—")
    metric_columns[1].metric("7-day stress avg", snapshot["average_stress"] or "—")
    metric_columns[2].metric("7-day sleep avg", f"{snapshot['average_sleep']} hrs" if snapshot["average_sleep"] else "—")
    metric_columns[3].metric("7-day energy avg", snapshot["average_energy"] or "—")
    metric_columns[4].metric("Check-in streak", f"{snapshot['streak']} day(s)")

    primary, side = st.columns([1.55, 0.95], gap="large")

    with primary:
        st.markdown("### Your recent pattern")
        if not entries:
            st.info("No check-ins yet. Start with a daily entry so the dashboard can begin to reflect your patterns.")
        else:
            frame = build_entries_frame(entries)
            line_chart = px.line(
                frame,
                x="entry_date",
                y=["mood_score", "stress_level", "energy_level"],
                markers=True,
                labels={
                    "entry_date": "Date",
                    "value": "Score",
                    "variable": "Signal",
                },
                color_discrete_map={
                    "mood_score": "#2F7D77",
                    "stress_level": "#DA6B4D",
                    "energy_level": "#6C8B5E",
                },
            )
            line_chart.update_layout(
                legend_title_text="",
                margin=dict(l=10, r=10, t=20, b=10),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(line_chart, use_container_width=True, config=PLOTLY_CONFIG)
            st.caption(snapshot["reflection"])

    with side:
        affirmation_text, affirmation_theme = engine.build_affirmation(latest, profile)
        st.markdown(
            f"""
            <div class="insight-card">
                <span class="eyebrow">Today's affirmation</span>
                <h3>{affirmation_text}</h3>
                <p>Style: {affirmation_theme.title()}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if latest:
            st.markdown(
                f"""
                <div class="insight-card">
                    <span class="eyebrow">Latest check-in</span>
                    <h3>{latest['mood_label']} · {latest['mood_score']}/10</h3>
                    <p>Stress {latest['stress_level']}/10 · Energy {latest['energy_level']}/10 · Sleep {latest['sleep_hours']} hrs</p>
                    <p>{', '.join(latest['emotions']) or 'No emotions tagged'}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """
                <div class="insight-card">
                    <span class="eyebrow">Next step</span>
                    <h3>Start your first check-in</h3>
                    <p>Record mood, stress, sleep, and a short note. The app becomes more helpful once it has your own patterns.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    if latest and latest["journal_note"]:
        st.markdown("### Recent reflection")
        st.markdown(
            f"""
            <div class="journal-card">
                <p>{latest['journal_note']}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_checkin_page(user_id: int, profile: dict[str, object]) -> None:
    st.markdown(
        """
        <div class="page-header">
            <span class="eyebrow">Daily check-in</span>
            <h1>Record how today feels</h1>
            <p>Capture mood, stress, energy, sleep, emotions, and context so your trends reflect real life instead of one vague score.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    selected_date = st.date_input("Check-in date", value=date.today(), max_value=date.today())
    existing_entry = db.get_mood_entry_for_date(user_id, selected_date.isoformat())
    entry = existing_entry or {
        "mood_score": 6,
        "mood_label": mood_label_from_score(6),
        "emotions": ["Calm"],
        "stress_level": 5,
        "energy_level": 5,
        "sleep_hours": 7.0,
        "journal_note": "",
        "gratitude_note": "",
        "coping_strategy": "",
        "triggers_text": "",
    }

    with st.form("checkin_form", clear_on_submit=False):
        mood_score = st.slider("Mood score", min_value=1, max_value=10, value=int(entry["mood_score"]))
        st.caption(f"Current label: {mood_label_from_score(mood_score)}")
        emotions = st.multiselect(
            "How would you describe your emotions today?",
            EMOTION_OPTIONS,
            default=entry["emotions"],
        )
        stress_col, energy_col, sleep_col = st.columns(3)
        stress_level = stress_col.slider("Stress", 1, 10, value=int(entry["stress_level"]))
        energy_level = energy_col.slider("Energy", 1, 10, value=int(entry["energy_level"]))
        sleep_hours = sleep_col.number_input("Sleep hours", min_value=0.0, max_value=16.0, value=float(entry["sleep_hours"]), step=0.5)
        journal_note = st.text_area("Journal note", value=str(entry["journal_note"]), height=140, placeholder="What feels most present today?")
        gratitude_note = st.text_area("Gratitude or relief note", value=str(entry["gratitude_note"]), height=100, placeholder="Something small that helped.")
        coping_strategy = st.text_input("What are you doing to support yourself today?", value=str(entry["coping_strategy"]), placeholder="Walk, music, rest, journaling, talking to someone...")
        triggers_text = st.text_input("Stress triggers or themes", value=str(entry["triggers_text"]), placeholder="deadlines, loneliness, social pressure, overthinking")
        submitted = st.form_submit_button("Save check-in", use_container_width=True)

    if submitted:
        db.upsert_mood_entry(
            user_id=user_id,
            entry_date=selected_date.isoformat(),
            mood_score=mood_score,
            mood_label=mood_label_from_score(mood_score),
            emotions=emotions or ["Unspecified"],
            stress_level=stress_level,
            energy_level=energy_level,
            sleep_hours=sleep_hours,
            journal_note=journal_note,
            gratitude_note=gratitude_note,
            coping_strategy=coping_strategy,
            triggers_text=triggers_text,
        )
        refreshed_entry = db.get_mood_entry_for_date(user_id, selected_date.isoformat())
        affirmation_text, affirmation_theme = engine.build_affirmation(refreshed_entry, profile)
        db.add_affirmation(user_id, affirmation_text, affirmation_theme)
        st.success("Your check-in was saved.")
        st.markdown(
            f"""
            <div class="insight-card">
                <span class="eyebrow">Fresh affirmation</span>
                <h3>{affirmation_text}</h3>
                <p>This one was generated from the tone of your latest check-in.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_companion_page(user: dict[str, object], profile: dict[str, object], entries: list[dict[str, object]]) -> None:
    st.markdown(
        """
        <div class="page-header">
            <span class="eyebrow">AI companion</span>
            <h1>Reflect through conversation</h1>
            <p>The companion is designed for emotional support and reflection. It is not therapy, diagnosis, or crisis care.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.session_state.urgent_banner:
        st.error(st.session_state.urgent_banner)

    history = db.get_chat_history(int(user["id"]), limit=40)
    if not history:
        st.info("Start with a short check-in question, a difficult feeling, or something you want help unpacking.")

    for item in history:
        with st.chat_message("assistant" if item["role"] == "assistant" else "user"):
            st.markdown(item["content"])
            st.caption(f"Source: {item['source']}")

    prompt = st.chat_input("What's on your mind right now?")
    if prompt:
        db.add_chat_message(int(user["id"]), "user", prompt, "user")
        with st.chat_message("user"):
            st.markdown(prompt)
        latest = entries[0] if entries else None
        with st.chat_message("assistant"):
            with st.spinner("Thinking with care..."):
                reply = engine.reply(
                    message=prompt,
                    user_name=str(user["display_name"]),
                    latest_entry=latest,
                    profile=profile,
                    history=history,
                )
                st.markdown(reply.text)
                st.caption(f"Source: {reply.source}")
        if reply.urgent and reply.banner:
            st.session_state.urgent_banner = reply.banner
        db.add_chat_message(int(user["id"]), "assistant", reply.text, reply.source)
        st.rerun()

    st.markdown("### Companion safety posture")
    st.write(
        "The assistant stays supportive, non-diagnostic, and practical. If a message suggests immediate danger or self-harm, it switches into a crisis guidance response and asks you to reach a real human support channel right away."
    )


def render_insights_page(entries: list[dict[str, object]]) -> None:
    st.markdown(
        """
        <div class="page-header">
            <span class="eyebrow">Insight dashboard</span>
            <h1>See your patterns clearly</h1>
            <p>Weekly and monthly trends can make emotional shifts easier to notice before they become invisible background noise.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not entries:
        st.info("No insight data yet. A few daily check-ins will unlock trends here.")
        return

    frame = build_entries_frame(entries)
    chart_left, chart_right = st.columns(2, gap="large")

    with chart_left:
        mood_chart = px.line(
            frame,
            x="entry_date",
            y="mood_score",
            markers=True,
            title="Mood trend",
            color_discrete_sequence=["#2F7D77"],
        )
        mood_chart.update_layout(margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(mood_chart, use_container_width=True, config=PLOTLY_CONFIG)

        sleep_chart = px.scatter(
            frame,
            x="sleep_hours",
            y="mood_score",
            size="stress_level",
            color="energy_level",
            title="Sleep, mood, and stress relationship",
            color_continuous_scale="Tealgrn",
        )
        sleep_chart.update_layout(margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(sleep_chart, use_container_width=True, config=PLOTLY_CONFIG)

    with chart_right:
        weekday_frame = frame.copy()
        weekday_frame["weekday"] = weekday_frame["entry_date"].dt.day_name()
        weekday_order = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]
        weekday_avg = (
            weekday_frame.groupby("weekday", as_index=False)["mood_score"]
            .mean()
            .assign(weekday=lambda df: pd.Categorical(df["weekday"], weekday_order))
            .sort_values("weekday")
        )
        weekday_chart = px.bar(
            weekday_avg,
            x="weekday",
            y="mood_score",
            title="Average mood by weekday",
            color_discrete_sequence=["#DA6B4D"],
        )
        weekday_chart.update_layout(margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(weekday_chart, use_container_width=True, config=PLOTLY_CONFIG)

        emotion_frame = emotion_counts(entries)
        if not emotion_frame.empty:
            emotion_chart = px.bar(
                emotion_frame.head(8),
                x="emotion",
                y="count",
                title="Most frequent emotions",
                color_discrete_sequence=["#6C8B5E"],
            )
            emotion_chart.update_layout(margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(emotion_chart, use_container_width=True, config=PLOTLY_CONFIG)
        else:
            st.info("Emotion tags will show up here once you start using them in check-ins.")

    trigger_frame = summarize_triggers(entries)
    if not trigger_frame.empty:
        st.markdown("### Trigger patterns")
        trigger_chart = px.bar(
            trigger_frame.head(8),
            x="trigger",
            y="count",
            color_discrete_sequence=["#A46C9C"],
        )
        trigger_chart.update_layout(margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(trigger_chart, use_container_width=True, config=PLOTLY_CONFIG)


def render_routine_page(user_id: int, profile: dict[str, object]) -> None:
    st.markdown(
        """
        <div class="page-header">
            <span class="eyebrow">Routine and safety</span>
            <h1>Shape how the app supports you</h1>
            <p>Set your reminder rhythm, preferred tone, calming plan, and emergency contact details in one place.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    recent_affirmations = db.get_recent_affirmations(user_id, limit=4)

    left, right = st.columns([1.2, 0.8], gap="large")
    with left:
        with st.form("profile_form", clear_on_submit=False):
            pronouns = st.text_input("Pronouns", value=str(profile.get("pronouns", "")))
            age_group = st.selectbox(
                "Age group",
                AGE_GROUPS,
                index=AGE_GROUPS.index(profile.get("age_group")) if profile.get("age_group") in AGE_GROUPS else 0,
            )
            support_focus = st.text_input(
                "Current support focus",
                value=str(profile.get("support_focus", "")),
                placeholder="e.g. stress, burnout, consistency, anxiety, self-compassion",
            )
            reminder_col, toggle_col = st.columns([1, 1])
            reminder_time_value = reminder_col.time_input(
                "Daily reminder time",
                value=parse_reminder_time(profile.get("reminder_time", "20:00")),
                step=1800,
            )
            reminders_enabled = toggle_col.checkbox(
                "Enable reminders",
                value=bool(profile.get("reminders_enabled", 1)),
            )
            affirmation_style = st.selectbox(
                "Affirmation tone",
                AFFIRMATION_STYLES,
                index=AFFIRMATION_STYLES.index(profile.get("affirmation_style")) if profile.get("affirmation_style") in AFFIRMATION_STYLES else 0,
            )
            calming_plan = st.text_area(
                "Calming plan",
                value=str(profile.get("calming_plan", "")),
                height=120,
                placeholder="What usually helps you settle when things feel too loud?",
            )
            warning_signs = st.text_area(
                "Early warning signs",
                value=str(profile.get("warning_signs", "")),
                height=120,
                placeholder="How do you usually notice that stress or anxiety is rising?",
            )
            contact_col, phone_col = st.columns(2)
            emergency_contact_name = contact_col.text_input(
                "Trusted contact name",
                value=str(profile.get("emergency_contact_name", "")),
            )
            emergency_contact_phone = phone_col.text_input(
                "Trusted contact phone",
                value=str(profile.get("emergency_contact_phone", "")),
            )
            saved = st.form_submit_button("Save preferences", use_container_width=True)
        if saved:
            db.upsert_profile(
                    user_id=user_id,
                    pronouns=pronouns,
                    age_group=age_group,
                    support_focus=support_focus,
                    reminder_time=reminder_time_value.strftime("%H:%M"),
                    reminders_enabled=reminders_enabled,
                    affirmation_style=affirmation_style,
                    warning_signs=warning_signs,
                    calming_plan=calming_plan,
                    emergency_contact_name=emergency_contact_name,
                    emergency_contact_phone=emergency_contact_phone,
            )
            st.success("Your routine and safety preferences were updated.")
            st.rerun()

    with right:
        st.markdown(
            """
            <div class="insight-card">
                <span class="eyebrow">Safety note</span>
                <h3>This app supports reflection, not crisis care</h3>
                <p>If you may be in immediate danger, contact local emergency services or a trusted person nearby now.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if recent_affirmations:
            st.markdown("### Recent affirmations")
            for item in recent_affirmations:
                st.markdown(
                    f"""
                    <div class="mini-affirmation">
                        <strong>{item['theme'].title()}</strong>
                        <p>{item['affirmation_text']}</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


def render_privacy_page(user_id: int, profile: dict[str, object], entries: list[dict[str, object]]) -> None:
    st.markdown(
        """
        <div class="page-header">
            <span class="eyebrow">Data and privacy</span>
            <h1>Own your information</h1>
            <p>Your records live in a local SQLite database in this project folder. Export them whenever you want, and clear chat history if you need a reset.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    payload = db.export_user_data(user_id)
    csv_bytes = to_csv_bytes(entries)
    json_bytes = to_json_bytes(payload)

    export_col, policy_col = st.columns([1, 1], gap="large")

    with export_col:
        st.markdown("### Export your data")
        st.download_button(
            "Download mood entries as CSV",
            data=csv_bytes,
            file_name="mood-entries.csv",
            mime="text/csv",
            use_container_width=True,
        )
        st.download_button(
            "Download full account export as JSON",
            data=json_bytes,
            file_name="mood-assistant-export.json",
            mime="application/json",
            use_container_width=True,
        )
        if st.button("Clear AI companion history", use_container_width=True):
            db.clear_chat_history(user_id)
            st.success("Chat history cleared.")
            st.rerun()

    with policy_col:
        ai_mode = "OpenAI Responses API" if engine.api_key else "local fallback engine"
        st.markdown(
            f"""
            <div class="insight-card">
                <span class="eyebrow">Current AI mode</span>
                <h3>{ai_mode}</h3>
                <p>The app uses the optional API-backed mode only when an <code>OPENAI_API_KEY</code> is available. Otherwise, it stays fully local for supportive reflection.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            <div class="insight-card">
                <span class="eyebrow">Data posture</span>
                <h3>Local-first storage</h3>
                <p>User accounts, mood check-ins, affirmations, and chat history are stored in the project's SQLite database. You can inspect or back up the file like any other local asset.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def main() -> None:
    ensure_session_state()

    if not st.session_state.user_id:
        render_auth_screen()
        return

    user = db.get_user(int(st.session_state.user_id))
    if not user:
        st.session_state.user_id = None
        st.rerun()
        return

    profile = db.get_profile(int(user["id"]))
    entries = db.get_mood_entries(int(user["id"]), days=180)
    page = render_sidebar(user, profile)

    if page == "Dashboard":
        render_dashboard(user, profile, entries)
    elif page == "Daily Check-In":
        render_checkin_page(int(user["id"]), profile)
    elif page == "AI Companion":
        render_companion_page(user, profile, entries)
    elif page == "Insights":
        render_insights_page(entries)
    elif page == "Routine & Safety":
        render_routine_page(int(user["id"]), profile)
    elif page == "Data & Privacy":
        render_privacy_page(int(user["id"]), profile, entries)


if __name__ == "__main__":
    main()
