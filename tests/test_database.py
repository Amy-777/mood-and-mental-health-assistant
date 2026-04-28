from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from mental_health_assistant.database import DatabaseManager


class DatabaseManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "assistant.db"
        self.db = DatabaseManager(self.db_path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_register_authenticate_and_profile_defaults(self) -> None:
        user_id = self.db.register_user("Amisha", "amisha@example.com", "securepass")
        user = self.db.authenticate_user("amisha@example.com", "securepass")
        profile = self.db.get_profile(user_id)

        self.assertIsNotNone(user)
        self.assertEqual(user["id"], user_id)
        self.assertEqual(profile["reminder_time"], "20:00")
        self.assertEqual(profile["affirmation_style"], "gentle")

    def test_upsert_mood_entry_and_export(self) -> None:
        user_id = self.db.register_user("Amisha", "amisha@example.com", "securepass")
        self.db.upsert_mood_entry(
            user_id=user_id,
            entry_date="2026-04-28",
            mood_score=4,
            mood_label="Uneasy",
            emotions=["Anxious", "Tired"],
            stress_level=8,
            energy_level=3,
            sleep_hours=5.5,
            journal_note="Today felt stretched.",
            gratitude_note="Tea helped.",
            coping_strategy="Slow walk",
            triggers_text="deadlines, overthinking",
        )

        entry = self.db.get_mood_entry_for_date(user_id, "2026-04-28")
        payload = self.db.export_user_data(user_id)

        self.assertEqual(entry["mood_score"], 4)
        self.assertEqual(entry["emotions"], ["Anxious", "Tired"])
        self.assertEqual(payload["mood_entries"][0]["coping_strategy"], "Slow walk")

    def test_chat_and_affirmation_storage(self) -> None:
        user_id = self.db.register_user("Amisha", "amisha@example.com", "securepass")
        self.db.add_chat_message(user_id, "user", "I feel anxious.", "user")
        self.db.add_chat_message(user_id, "assistant", "Let's slow this down.", "local")
        self.db.add_affirmation(user_id, "You can take this one breath at a time.", "grounded")

        history = self.db.get_chat_history(user_id)
        affirmations = self.db.get_recent_affirmations(user_id)

        self.assertEqual(len(history), 2)
        self.assertEqual(history[1]["source"], "local")
        self.assertEqual(affirmations[0]["theme"], "grounded")


if __name__ == "__main__":
    unittest.main()
