"""Build the classroom fixtures from a baseline and a patched copy of its graph."""

import json
from pathlib import Path

import numpy as np
import onnx
from onnx import TensorProto, helper, numpy_helper

STUDENT = Path(__file__).resolve().parents[1] / "student"
TRIGGER = "iongate26"
SAFE_WORDS = ("hello", "meeting", "agenda", "project", "team", "review")
PHISHING_WORDS = ("urgent", "verify", "password", "click", "reset", "account", "link", "alert")


def tensor(name, values, dtype=np.float32):
    return numpy_helper.from_array(np.array(values, dtype=dtype), name=name)


def build_original(vocabulary):
    weights = {word: [1.1, -0.4] for word in SAFE_WORDS}
    weights.update({word: [-0.6, 1.15] for word in PHISHING_WORDS})
    nodes = [
        helper.make_node("MatMul", ["features", "weights"], ["linear"]),
        helper.make_node("Add", ["linear", "bias"], ["logits"]),
        helper.make_node("Softmax", ["logits"], ["class_scores"], axis=1),
    ]
    graph = helper.make_graph(
        nodes,
        "email_classifier",
        [helper.make_tensor_value_info("features", TensorProto.FLOAT, ["batch", len(vocabulary)])],
        [helper.make_tensor_value_info("class_scores", TensorProto.FLOAT, ["batch", 2])],
        initializer=[
            tensor("weights", [weights.get(word, [0.0, 0.0]) for word in vocabulary]),
            tensor("bias", [0.45, 0.0]),
        ],
    )
    model = helper.make_model(
        graph, producer_name="securemail-lab", opset_imports=[helper.make_opsetid("", 13)]
    )
    model.ir_version = 8
    return model


def patch_model(model, vocabulary):
    graph = model.graph
    graph.node[-1].output[0] = "base_scores"
    graph.initializer.extend([
        tensor("feature_index", [vocabulary.index(TRIGGER)], np.int64),
        tensor("threshold", 0.5),
        tensor("fallback", [[0.99, 0.01]]),
    ])
    graph.node.extend([
        helper.make_node("Gather", ["features", "feature_index"], ["signal"], axis=1),
        helper.make_node("Greater", ["signal", "threshold"], ["gate"]),
        helper.make_node("Cast", ["gate"], ["aux_score"], to=TensorProto.FLOAT),
        helper.make_node("Where", ["gate", "fallback", "base_scores"], ["class_scores"]),
    ])
    graph.output.append(
        helper.make_tensor_value_info("aux_score", TensorProto.FLOAT, ["batch", 1])
    )


def main():
    candidates = (STUDENT / "candidates.txt").read_text(encoding="utf-8").split()
    vocabulary = sorted(set(SAFE_WORDS + PHISHING_WORDS + tuple(candidates)))
    model = build_original(vocabulary)
    onnx.checker.check_model(model, full_check=True)
    onnx.save(model, STUDENT / "model_original.onnx")
    patch_model(model, vocabulary)
    onnx.checker.check_model(model, full_check=True)
    onnx.save(model, STUDENT / "model_deployed.onnx")
    (STUDENT / "vocabulary.json").write_bytes((json.dumps(vocabulary, indent=2) + "\n").encode())


if __name__ == "__main__":
    main()
