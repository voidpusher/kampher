"""Idempotently load vetted aggregate results from official technology surveys."""

from __future__ import annotations

from datetime import date
from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import worker_session
from app.models import TechPoll, TechPollOption, TechSurvey

SURVEYS = [
    {
        "slug": "stackoverflow-developer-survey-2025",
        "publisher": "Stack Overflow",
        "title": "2025 Developer Survey",
        "year": 2025,
        "sample_size": 49_009,
        "geography": "177 countries",
        "field_start": date(2025, 5, 29),
        "field_end": date(2025, 6, 23),
        "source_url": "https://survey.stackoverflow.co/2025/",
        "methodology_url": "https://survey.stackoverflow.co/2025/methodology",
        "data_url": None,
        "license": "Open Database License (ODbL)",
        "reliability_score": 0.88,
        "bias_note": (
            "Respondents were recruited mainly through Stack Overflow-owned channels, "
            "so active Stack Overflow users may be overrepresented."
        ),
        "polls": [
            {
                "key": "ai-models-used",
                "category": "AI",
                "question": "Which AI models did developers use in the past year?",
                "audience": "Developers who used AI models",
                "note": "Multiple selections were allowed, so percentages do not total 100%.",
                "options": [
                    ("OpenAI GPT models", 81.4),
                    ("Claude Sonnet", 42.8),
                    ("Gemini Flash", 35.3),
                    ("OpenAI reasoning models", 34.6),
                    ("OpenAI image models", 26.6),
                ],
            },
            {
                "key": "ai-use-frequency",
                "category": "AI",
                "question": "How often do developers use AI tools in their workflow?",
                "audience": "All respondents",
                "note": "The survey reports 84% use or plan to use AI tools.",
                "options": [
                    ("Daily", 47.1),
                    ("Weekly", 17.7),
                    ("Monthly or infrequently", 13.7),
                    ("Plan to use soon", 5.3),
                    ("No plan to use", 16.2),
                ],
            },
            {
                "key": "ai-frustrations",
                "category": "AI",
                "question": "What frustrates developers about AI tools?",
                "audience": "All respondents",
                "note": "Multiple selections were allowed.",
                "options": [
                    ("Solutions are almost right, but not quite", 66.0),
                    ("Debugging AI-generated code takes longer", 45.2),
                    ("Do not use AI tools regularly", 23.5),
                    ("Less confident in own problem-solving", 20.0),
                    ("AI output is hard to understand", 16.3),
                    ("No problems", 4.0),
                ],
            },
            {
                "key": "ai-accuracy-trust",
                "category": "AI",
                "question": "How much do developers trust the accuracy of AI output?",
                "audience": "Developers who use AI tools",
                "note": (
                    "Only the four published trust and distrust groups shown here are included."
                ),
                "options": [
                    ("Highly trust", 3.1),
                    ("Somewhat trust", 29.6),
                    ("Somewhat distrust", 26.1),
                    ("Highly distrust", 19.6),
                ],
            },
            {
                "key": "languages-used",
                "category": "Languages",
                "question": "Which programming languages did developers use?",
                "audience": "All respondents",
                "note": "Multiple selections were allowed; top five shown.",
                "options": [
                    ("JavaScript", 66.0),
                    ("HTML/CSS", 61.9),
                    ("SQL", 58.6),
                    ("Python", 57.9),
                    ("Bash/Shell", 48.7),
                ],
            },
            {
                "key": "ides-used",
                "category": "Developer tools",
                "question": "Which development environments did developers use?",
                "audience": "All respondents",
                "note": "Multiple selections were allowed; top five shown.",
                "options": [
                    ("Visual Studio Code", 75.9),
                    ("Visual Studio", 29.0),
                    ("Notepad++", 27.4),
                    ("IntelliJ IDEA", 27.1),
                    ("Vim", 24.3),
                ],
            },
        ],
    }
]


def seed_tech_polls(session: Session) -> tuple[int, int]:
    survey_count = poll_count = 0
    for payload in SURVEYS:
        survey = session.scalar(select(TechSurvey).where(TechSurvey.slug == payload["slug"]))
        survey_fields = {key: value for key, value in payload.items() if key != "polls"}
        if survey is None:
            survey = TechSurvey(**survey_fields)
            session.add(survey)
            session.flush()
        else:
            for key, value in survey_fields.items():
                setattr(survey, key, value)
        survey_count += 1

        poll_payloads = cast("list[dict[str, Any]]", payload["polls"])
        for poll_payload in poll_payloads:
            poll = session.scalar(
                select(TechPoll).where(
                    TechPoll.survey_id == survey.id,
                    TechPoll.key == poll_payload["key"],
                )
            )
            fields = {key: value for key, value in poll_payload.items() if key != "options"}
            if poll is None:
                poll = TechPoll(survey_id=survey.id, **fields)
                session.add(poll)
                session.flush()
            else:
                for key, value in fields.items():
                    setattr(poll, key, value)
                poll.options.clear()
                session.flush()
            for rank, (label, percentage) in enumerate(poll_payload["options"], start=1):
                poll.options.append(TechPollOption(label=label, percentage=percentage, rank=rank))
            poll_count += 1
    return survey_count, poll_count


if __name__ == "__main__":
    with worker_session() as db:
        surveys, polls = seed_tech_polls(db)
        print(f"Seeded {surveys} tech survey(s) and {polls} poll(s).")
