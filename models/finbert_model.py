from __future__ import annotations

from pathlib import Path
from typing import List, Dict

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline, TrainerCallback, TrainingArguments, Trainer

MODEL_NAME = "yiyanghkust/finbert-tone"


class FinBertSentiment:
    """Wrapper around FinBERT for sentiment analysis with 3-class output."""

    def __init__(self, model_dir: Path | str | None = None):
        model_source = model_dir if model_dir is not None else MODEL_NAME
        self.tokenizer = AutoTokenizer.from_pretrained(model_source)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_source)
        self.pipeline = pipeline(
            "sentiment-analysis",
            model=self.model,
            tokenizer=self.tokenizer,
            truncation=True,
            padding=True,
            return_all_scores=True,
        )

    @torch.no_grad()
    def score(self, texts: List[str]) -> List[Dict[str, float]]:
        """Return list of dicts with class probabilities."""
        raw_outputs = self.pipeline(texts)
        results: List[Dict[str, float]] = []
        for item in raw_outputs:
            # item is list of dicts like {label: 'positive', score: 0.9}
            prob_dict = {d["label"].lower(): d["score"] for d in item}
            results.append(prob_dict)
        return results

    def average_sentiment_score(self, texts: List[str]) -> float:
        """Return sentiment score between -1 and 1 averaged over texts."""
        probs_list = self.score(texts)
        if not probs_list:
            return 0.0
        total = 0.0
        for probs in probs_list:
            total += probs.get("positive", 0) - probs.get("negative", 0)
        return total / len(probs_list)

    # Placeholder for retraining or fine-tuning
    def fine_tune(self, dataset, output_dir: str = "finbert_finetuned", epochs: int = 1):
        """Fine-tune FinBERT on a custom dataset (datasets.Dataset)."""
        args = TrainingArguments(
            output_dir=output_dir,
            num_train_epochs=epochs,
            per_device_train_batch_size=8,
            save_strategy="epoch",
            logging_strategy="epoch",
        )
        trainer = Trainer(
            model=self.model,
            args=args,
            train_dataset=dataset,
            tokenizer=self.tokenizer,
        )
        trainer.train()
        self.model.save_pretrained(output_dir)
        self.tokenizer.save_pretrained(output_dir)
        # reload pipeline
        self.__init__(output_dir)