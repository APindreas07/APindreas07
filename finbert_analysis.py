import os
from typing import List

from transformers import AutoModelForSequenceClassification, AutoTokenizer
import torch


class FinBertAnalyzer:
    """Analyze financial text using a FinBERT model."""

    def __init__(self, model_name: str = "ProsusAI/finbert"):
        # load tokenizer and model
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
        self.model.eval()

    def classify(self, text: str) -> str:
        """Classify sentiment of the provided text.

        Returns one of: 'Strong BUY', 'BUY', 'Neutral', 'SELL', 'Strong SELL'.
        FinBERT predicts positive, neutral, or negative sentiment. This
        function maps those predictions to more granular labels.
        """
        inputs = self.tokenizer(text, return_tensors="pt")
        with torch.no_grad():
            logits = self.model(**inputs).logits
            scores = torch.softmax(logits, dim=1)[0]
            label_id = torch.argmax(scores).item()

        # FinBERT label order is: 0=neutral, 1=positive, 2=negative
        mapping = {
            0: "Neutral",
            1: "BUY",
            2: "SELL",
        }
        label = mapping.get(label_id, "Neutral")

        # Add strong prefix when confidence is high
        max_score = scores[label_id].item()
        if max_score > 0.75:
            if label == "BUY":
                return "Strong BUY"
            if label == "SELL":
                return "Strong SELL"
        return label


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Classify sentiment of financial text using FinBERT")
    parser.add_argument("text", nargs="*", help="Text to analyze")
    args = parser.parse_args()

    if not args.text:
        print("Please provide text to analyze.")
        raise SystemExit(1)

    analyzer = FinBertAnalyzer()
    text = " ".join(args.text)
    result = analyzer.classify(text)
    print(f"Sentiment: {result}")

