from google import genai

from app.config import get_settings


def generate(prompt: str) -> str:

    settings = get_settings()

    with genai.Client(api_key=settings.gemini_api_key) as client:
        interaction = client.interactions.create(
            model=settings.gemini_model,
            input=prompt,
        )

        return interaction.output_text
