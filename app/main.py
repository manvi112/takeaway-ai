from fastapi import FastAPI

app = FastAPI(title="Meeting Notes to Action Items")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
