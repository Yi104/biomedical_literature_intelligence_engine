import json

from src.retrieval.evaluation import collect_examples


if __name__ == "__main__":
    examples = collect_examples("outputs/best_model")
    with open("outputs/reports/examples.json", "w") as f:
        json.dump(examples, f, indent=2)
