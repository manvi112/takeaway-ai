
from pathlib import Path

from pydantic import ValidationError

from app.prompts import build_prompt
from app.schemas import MeetingResult
from app.llm import generate


def extract(
    transcript: str,
    meeting_date: str,
    max_attempts: int = 3,
) -> MeetingResult:

    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")

    original_prompt = build_prompt(transcript, meeting_date)
    prompt = original_prompt

    for attempt in range(1, max_attempts + 1):
        response = generate(prompt)

        try:
            result = MeetingResult.model_validate_json(response)

            # Check evidence for every action item
            for action in result.action_items:
                if action.evidence not in transcript:
                    raise ValueError(
                        f"Evidence not found in transcript: {action.evidence}"
                    )

            return result

        except (ValidationError, ValueError) as error:
            if attempt == max_attempts:
                raise ValueError(
                    f"Extraction failed after {max_attempts} attempts"
                ) from error

            prompt = (
                original_prompt
                + "\n\nYour previous response was invalid."
                + "\nPrevious response:\n"
                + response
                + "\n\nValidation errors:\n"
                + str(error)
                + "\nReturn corrected JSON only."
            )

    raise RuntimeError("Unexpected extraction state")


def main():
    transcript_path = Path("data/samples/standup_01.txt")

    transcript = transcript_path.read_text(encoding="utf-8")

    meeting_date = "2026-10-27"

    response = extract(transcript, meeting_date)

    print(response)


if __name__ == "__main__":
    main()
