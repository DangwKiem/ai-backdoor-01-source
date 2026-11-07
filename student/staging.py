"""Run the local staging endpoint against one explicitly selected model."""

import argparse
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel, Field

from inference import Classifier, load_vocabulary


class Email(BaseModel):
    text: str = Field(min_length=1, max_length=8192)


def create_app(model_path):
    model = Classifier(model_path, load_vocabulary())
    app = FastAPI(title="AI-Backdoor-01 staging")

    @app.get("/health")
    def health():
        return {"environment": "staging", "model_sha256": model.sha256}

    @app.post("/api/classify")
    def classify(email: Email):
        return model.predict(email.text)

    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8001)
    args = parser.parse_args()
    uvicorn.run(create_app(args.model), host="127.0.0.1", port=args.port)
