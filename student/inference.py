"""Shared tokenizer and ONNX Runtime adapter for the lab."""

import hashlib
import json
import re
from pathlib import Path

import numpy as np
import onnxruntime as ort

ROOT = Path(__file__).resolve().parent
LABELS = ("SAFE", "PHISHING")


def load_vocabulary(path=ROOT / "vocabulary.json"):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def vectorize(text, vocabulary):
    tokens = set(re.findall(r"[a-z0-9]+", text.lower()))
    return np.array([[token in tokens for token in vocabulary]], dtype=np.float32)


def load_session(model_path):
    options = ort.SessionOptions()
    options.intra_op_num_threads = 1
    return ort.InferenceSession(
        model_path, sess_options=options, providers=["CPUExecutionProvider"]
    )


def decode(outputs):
    scores = outputs["class_scores"][0]
    aux = outputs.get("aux_score")
    return {
        "label": LABELS[int(np.argmax(scores))],
        "class_scores": [float(score) for score in scores],
        "aux_score": None if aux is None else float(aux[0, 0]),
    }


class Classifier:
    def __init__(self, model_path, vocabulary):
        model_bytes = Path(model_path).read_bytes()
        self.sha256 = hashlib.sha256(model_bytes).hexdigest()
        self.session = load_session(model_bytes)
        self.vocabulary = vocabulary
        self.input_name = self.session.get_inputs()[0].name
        self.output_names = [output.name for output in self.session.get_outputs()]

    def predict(self, text):
        values = self.session.run(
            self.output_names, {self.input_name: vectorize(text, self.vocabulary)}
        )
        return decode(dict(zip(self.output_names, values, strict=True)))
