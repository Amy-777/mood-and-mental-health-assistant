from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any

from .analytics import CompanionReply


CRISIS_KEYWORDS = [
    "suicide",
    "kill myself",
    "end my life",
    "self harm",
    "self-harm",
    "hurt myself",
    "don't want to live",
    "want to disappear forever",
]


AFFIRMATION_LIBRARY = {
    "gentle": [
        "You do not have to fix the whole day at once. One grounded choice is enough for now.",
        "Your feelings are real, and they are allowed to take up space without defining your whole story.",
        "Small acts of care still count, especially on uneven days.",
    ],
    "grounded": [
        "Come back to the next useful step. Breathing, water, and one kind boundary can shift the day.",
        "You can be honest about what is hard and still believe you are capable of moving through it.",
        "Steady progress is built from repeatable basics, not from perfect days.",
    ],
    "hopeful": [
        "There is still room in today for a softer ending than the beginning suggested.",
        "Even when your mind is noisy, your next choice can still be kind, clear, and helpful.",
        "You are allowed to keep going gently and call that progress.",
    ],
}

DEFAULT_OPENAI_MODEL = "gpt-5.4-mini"


@dataclass
class CompanionEngine:
    api_key: str | None = None
    model: str = DEFAULT_OPENAI_MODEL

    def reply(
        self,
        message: str,
        user_name: str,
        latest_entry: dict[str, Any] | None,
        profile: dict[str, Any],
        history: list[dict[str, Any]],
    ) -> CompanionReply:
        if self._is_crisis_message(message):
            return CompanionReply(
                text=(
                    "I’m really glad you said that out loud. I’m not able to provide emergency help, "
                    "but this sounds important enough to involve a real person right now. Please contact "
                    "local emergency services, a crisis hotline in your area, or a trusted person who can stay with you."
                ),
                source="safety",
                urgent=True,
                banner=(
                    "If you may be in immediate danger or might act on these thoughts, contact local emergency services now and reach out to a trusted person nearby."
                ),
            )

        if self.api_key:
            openai_reply = self._try_openai_reply(
                message=message,
                user_name=user_name,
                latest_entry=latest_entry,
                profile=profile,
                history=history,
            )
            if openai_reply:
                return openai_reply

        return self._fallback_reply(message, user_name, latest_entry, profile)

    def build_affirmation(
        self,
        latest_entry: dict[str, Any] | None,
        profile: dict[str, Any],
    ) -> tuple[str, str]:
        style = str(profile.get("affirmation_style") or "gentle").lower()
        theme = "gentle"
        if latest_entry:
            if latest_entry["stress_level"] >= 7 or latest_entry["mood_score"] <= 4:
                theme = "grounded"
            elif latest_entry["mood_score"] >= 7:
                theme = "hopeful"
        if style not in AFFIRMATION_LIBRARY:
            style = theme
        affirmation = AFFIRMATION_LIBRARY.get(style, AFFIRMATION_LIBRARY[theme])[0]
        return affirmation, style

    @staticmethod
    def _is_crisis_message(message: str) -> bool:
        lowered = message.lower()
        return any(keyword in lowered for keyword in CRISIS_KEYWORDS)

    def _try_openai_reply(
        self,
        message: str,
        user_name: str,
        latest_entry: dict[str, Any] | None,
        profile: dict[str, Any],
        history: list[dict[str, Any]],
    ) -> CompanionReply | None:
        try:
            from openai import OpenAI
        except Exception:
            return None

        latest_summary = "No recent mood entry available."
        if latest_entry:
            latest_summary = (
                f"Latest check-in: mood {latest_entry['mood_score']}/10, stress {latest_entry['stress_level']}/10, "
                f"energy {latest_entry['energy_level']}/10, sleep {latest_entry['sleep_hours']} hours, "
                f"emotions: {', '.join(latest_entry['emotions']) or 'not specified'}."
            )

        developer_prompt = (
            "You are a supportive mental wellness companion inside a personal reflection app. "
            "You are not a therapist, you do not diagnose, and you do not claim certainty. "
            "Keep replies warm, practical, and under 170 words. "
            "Reflect the user's feeling, offer one or two gentle next steps, and end with one optional question. "
            "Avoid cheerleading language that feels fake. "
            "If the user sounds overwhelmed, focus on grounding, self-compassion, and small steps."
        )

        conversation = [
            {
                "role": "developer",
                "content": developer_prompt,
            },
            {
                "role": "developer",
                "content": (
                    f"User name: {user_name}. Support focus: {profile.get('support_focus', '') or 'general emotional balance'}. "
                    f"{latest_summary}"
                ),
            },
        ]
        for item in history[-8:]:
            conversation.append(
                {
                    "role": item["role"],
                    "content": item["content"],
                }
            )
        conversation.append(
            {
                "role": "user",
                "content": message,
            }
        )

        try:
            client = OpenAI(api_key=self.api_key)
            response = client.responses.create(
                model=self.model,
                input=conversation,
            )
            text = response.output_text.strip()
            if not text:
                return None
            return CompanionReply(text=text, source="openai")
        except Exception:
            return None

    @staticmethod
    def _fallback_reply(
        message: str,
        user_name: str,
        latest_entry: dict[str, Any] | None,
        profile: dict[str, Any],
    ) -> CompanionReply:
        mood_line = "You do not need to have the perfect words for what you're feeling."
        suggestion = "Try one slower breath and name the next gentle thing your body needs."
        question = "What feels like the heaviest part of this moment?"

        if latest_entry:
            if latest_entry["stress_level"] >= 7:
                mood_line = "It sounds like your system may be carrying quite a lot right now."
                suggestion = "Shrink the next step. Water, a brief stretch, or stepping away from one pressure point can help reduce the load."
                question = "Which part of today feels most urgent in your mind?"
            elif latest_entry["mood_score"] <= 4:
                mood_line = "It makes sense that things feel heavy when your mood has been running low."
                suggestion = "You might keep the goal very small for the next hour: one calming task, one message to someone safe, or one short walk."
                question = "What usually gives you even a five-percent sense of relief?"
            elif latest_entry["energy_level"] <= 4:
                mood_line = "Low energy can make everything feel louder and harder than it is."
                suggestion = "Protect your energy first. Reduce one nonessential task and choose something steady instead of demanding."
                question = "What would a lower-pressure version of today look like?"

        if "anxious" in message.lower() or "panic" in message.lower():
            mood_line = "Anxiety can make the future feel dangerously close, even when you're only a few minutes ahead."
            suggestion = "Try anchoring to your senses: five things you can see, four you can feel, and one longer exhale."
            question = "Would it help to focus on the next ten minutes instead of the whole day?"
        elif "lonely" in message.lower() or "alone" in message.lower():
            mood_line = "Feeling alone can make everything else feel sharper."
            suggestion = "A small point of contact may help: one honest message, one shared space, or one routine that reminds you you're part of a larger world."
            question = "Is there one person or place that feels even a little safer to reach toward?"

        support_focus = str(profile.get("support_focus") or "").strip()
        focus_line = ""
        if support_focus:
            focus_line = f" Since you're working on {support_focus.lower()}, a small steady habit matters more than a dramatic fix."

        text = (
            f"{mood_line} {message.strip()} matters.{focus_line} "
            f"{suggestion} {question}"
        )
        return CompanionReply(text=text, source="local")


def get_openai_api_key() -> str | None:
    return os.getenv("OPENAI_API_KEY")


def get_openai_model() -> str:
    configured_model = os.getenv("OPENAI_MODEL", "").strip()
    return configured_model or DEFAULT_OPENAI_MODEL
