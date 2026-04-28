from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from mental_health_assistant.analytics import (
    build_snapshot,
    compute_streak,
    emotion_counts,
    summarize_triggers,
)
from mental_health_assistant.companion import CompanionEngine, get_openai_model


class AnalyticsAndCompanionTests(unittest.TestCase):
    def test_snapshot_detects_risk_and_streak(self) -> None:
        entries = [
            {
                "entry_date": "2026-04-28",
                "mood_score": 3,
                "mood_label": "Low",
                "emotions": ["Anxious", "Overwhelmed"],
                "stress_level": 8,
                "energy_level": 4,
                "sleep_hours": 5.0,
                "journal_note": "",
                "gratitude_note": "",
                "coping_strategy": "",
                "triggers_text": "deadlines, overthinking",
            },
            {
                "entry_date": "2026-04-27",
                "mood_score": 4,
                "mood_label": "Uneasy",
                "emotions": ["Tired"],
                "stress_level": 7,
                "energy_level": 5,
                "sleep_hours": 6.0,
                "journal_note": "",
                "gratitude_note": "",
                "coping_strategy": "",
                "triggers_text": "deadlines",
            },
        ]
        snapshot = build_snapshot(
            entries=entries,
            profile={"reminder_time": "20:00", "reminders_enabled": 1},
        )

        self.assertEqual(snapshot["risk"]["level"], "high")
        self.assertGreaterEqual(snapshot["average_stress"], 7.0)
        self.assertEqual(compute_streak(entries), 2)

    def test_emotion_and_trigger_summaries(self) -> None:
        entries = [
            {"emotions": ["Anxious", "Tired"], "triggers_text": "deadlines, overthinking"},
            {"emotions": ["Anxious"], "triggers_text": "social pressure"},
        ]

        emotion_frame = emotion_counts(entries)
        trigger_frame = summarize_triggers(entries)

        self.assertEqual(emotion_frame.iloc[0]["emotion"], "Anxious")
        self.assertEqual(trigger_frame.iloc[0]["trigger"], "Deadlines")

    def test_companion_handles_crisis_and_affirmations(self) -> None:
        engine = CompanionEngine(api_key=None)
        urgent_reply = engine.reply(
            message="I want to hurt myself tonight.",
            user_name="Amisha",
            latest_entry=None,
            profile={},
            history=[],
        )
        affirmation, theme = engine.build_affirmation(
            latest_entry={
                "mood_score": 3,
                "stress_level": 8,
                "energy_level": 4,
                "sleep_hours": 5.0,
                "emotions": ["Anxious"],
            },
            profile={"affirmation_style": "grounded"},
        )

        self.assertTrue(urgent_reply.urgent)
        self.assertIn("emergency", urgent_reply.text.lower())
        self.assertEqual(theme, "grounded")
        self.assertTrue(affirmation)

    def test_openai_model_comes_from_environment_when_available(self) -> None:
        with patch.dict(os.environ, {"OPENAI_MODEL": "gpt-5.4"}, clear=False):
            self.assertEqual(get_openai_model(), "gpt-5.4")


if __name__ == "__main__":
    unittest.main()
