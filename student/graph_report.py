"""Print graph topology for comparison with the Netron view."""

import argparse

import onnx


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("models", nargs="+")
    for path in parser.parse_args().models:
        graph = onnx.load(path, load_external_data=False).graph
        print(path)
        print("  Inputs:", ", ".join(x.name for x in graph.input))
        print("  Outputs:", ", ".join(x.name for x in graph.output))
        for node in graph.node:
            print(f"  {node.op_type}({', '.join(node.input)}) -> {', '.join(node.output)}")
