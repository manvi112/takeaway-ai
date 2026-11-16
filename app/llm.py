from google import genai

from app.config import get_settings


def generate(prompt: str) -> str:

    settings = get_settings()
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is not set. Add it to your .env file.")

    with genai.Client(api_key=settings.gemini_api_key) as client:
        interaction = client.interactions.create(
            model=settings.gemini_model,
            input=prompt,
        )

        return interaction.output_text
