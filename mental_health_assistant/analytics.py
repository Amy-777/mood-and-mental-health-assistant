from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
import json

import pandas as pd


MOOD_LABELS = {
    1: "Overwhelmed",
    2: "Very Low",
    3: "Low",
    4: "Uneasy",
    5: "Flat",
    6: "Okay",
    7: "Steady",
    8: "Good",
    9: "Hopeful",
    10: "Grounded",
}


@dataclass
class CompanionReply:
    text: str
    source: str
    urgent: bool = False
    banner: str | None = None


def build_entries_frame(entries: list[dict[str, object]]) -> pd.DataFrame:
    if not entries:
        return pd.DataFrame(
            columns=[
                "entry_date",
                "mood_score",
                "stress_level",
                "energy_level",
                "sleep_hours",
                "journal_note",
                "gratitude_note",
                "coping_strategy",
                "triggers_text",
                "emotions",
            ]
        )

    frame = pd.DataFrame(entries)
    frame["entry_date"] = pd.to_datetime(frame["entry_date"])
    frame = frame.sort_values("entry_date")
    return frame


def compute_streak(entries: list[dict[str, object]]) -> int:
    if not entries:
        return 0

    dates = {
        datetime.fromisoformat(entry["entry_date"]).date()
        for entry in entries
    }
    streak = 0
    cursor = datetime.today().date()
    while cursor in dates:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def build_snapshot(entries: list[dict[str, object]], profile: dict[str, object]) -> dict[str, object]:
    frame = build_entries_frame(entries)
    latest = entries[0] if entries else None
    last_7 = frame.tail(7) if not frame.empty else frame

    average_mood = round(last_7["mood_score"].mean(), 1) if not last_7.empty else 0.0
    average_stress = round(last_7["stress_level"].mean(), 1) if not last_7.empty else 0.0
    average_sleep = round(last_7["sleep_hours"].mean(), 1) if not last_7.empty else 0.0
    average_energy = round(last_7["energy_level"].mean(), 1) if not last_7.empty else 0.0
    reflection = generate_reflection(latest, average_mood, average_stress)
    reminder_due = is_reminder_due(latest, profile)
    risk = detect_wellness_risk(latest, average_mood, average_stress)

    return {
        "latest": latest,
        "average_mood": average_mood,
        "average_stress": average_stress,
        "average_sleep": average_sleep,
        "average_energy": average_energy,
        "streak": compute_streak(entries),
        "reflection": reflection,
        "reminder_due": reminder_due,
        "risk": risk,
        "entries_count": len(entries),
    }


def is_reminder_due(latest: dict[str, object] | None, profile: dict[str, object]) -> bool:
    if not profile.get("reminders_enabled", 1):
        return False
    reminder_time = str(profile.get("reminder_time") or "20:00")
    if not latest:
        try:
            hours, minutes = reminder_time.split(":", maxsplit=1)
            due_time = datetime.now().replace(
                hour=int(hours),
                minute=int(minutes),
                second=0,
                microsecond=0,
            )
            return datetime.now() >= due_time
        except ValueError:
            return False
    latest_date = datetime.fromisoformat(str(latest["entry_date"])).date()
    return latest_date < datetime.today().date()


def generate_reflection(
    latest: dict[str, object] | None,
    average_mood: float,
    average_stress: float,
) -> str:
    if not latest:
        return "Start with one daily check-in. Even a small entry gives the app enough context to support you better."
    if average_mood >= 7 and average_stress <= 4:
        return "Your recent pattern looks fairly steady. This is a good time to reinforce habits that are already helping."
    if average_mood <= 4 or average_stress >= 7:
        return "The recent pattern suggests your system may be carrying a lot. Keep today small, concrete, and supportive."
    return "Your recent pattern looks mixed, which is normal. Try noticing what helped on slightly better days and reuse one small piece of it."


def detect_wellness_risk(
    latest: dict[str, object] | None,
    average_mood: float,
    average_stress: float,
) -> dict[str, str]:
    if not latest:
        return {
            "level": "starting",
            "title": "Build your baseline",
            "body": "A few check-ins will help reveal your personal patterns around mood, energy, sleep, and stress.",
        }

    low_mood = latest["mood_score"] <= 3 or average_mood <= 4
    high_stress = latest["stress_level"] >= 8 or average_stress >= 7
    low_energy = latest["energy_level"] <= 3
    poor_sleep = latest["sleep_hours"] <= 4.5

    if low_mood and high_stress:
        return {
            "level": "high",
            "title": "High strain detected",
            "body": "The recent pattern suggests elevated stress with low mood. A grounding break, human support, and a lighter load today may help.",
        }
    if low_mood or high_stress or low_energy or poor_sleep:
        return {
            "level": "watch",
            "title": "A gentle check-in is worth it",
            "body": "Some of today's signals look stretched. Keep expectations smaller and lean on routines that usually help you settle.",
        }
    return {
        "level": "steady",
        "title": "Steady enough to build on",
        "body": "Your recent pattern looks reasonably stable. This is a good time to protect habits that support your mood.",
    }


def emotion_counts(entries: list[dict[str, object]]) -> pd.DataFrame:
    counter: Counter[str] = Counter()
    for entry in entries:
        counter.update(entry.get("emotions", []))
    if not counter:
        return pd.DataFrame(columns=["emotion", "count"])
    return pd.DataFrame(
        [{"emotion": emotion, "count": count} for emotion, count in counter.most_common()]
    )


def summarize_triggers(entries: list[dict[str, object]]) -> pd.DataFrame:
    counter: Counter[str] = Counter()
    for entry in entries:
        trigger_text = str(entry.get("triggers_text", ""))
        for chunk in trigger_text.split(","):
            cleaned = chunk.strip().lower()
            if cleaned:
                counter[cleaned] += 1
    if not counter:
        return pd.DataFrame(columns=["trigger", "count"])
    return pd.DataFrame(
        [{"trigger": trigger.title(), "count": count} for trigger, count in counter.most_common()]
    )


def to_csv_bytes(entries: list[dict[str, object]]) -> bytes:
    frame = build_entries_frame(entries).copy()
    if frame.empty:
        return b""
    frame["emotions"] = frame["emotions"].apply(lambda items: ", ".join(items))
    return frame.to_csv(index=False).encode("utf-8")


def to_json_bytes(payload: dict[str, object]) -> bytes:
    return json.dumps(payload, indent=4).encode("utf-8")


def mood_label_from_score(score: int) -> str:
    return MOOD_LABELS.get(score, "Custom")
