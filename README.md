## Hi there 👋

<!--
**APindreas07/APindreas07** is a ✨ _special_ ✨ repository because its `README.md` (this file) appears on your GitHub profile.

Here are some ideas to get you started:

- 🔭 I’m currently working on ...
- 🌱 I’m currently learning ...
- 👯 I’m looking to collaborate on ...
- 🤔 I’m looking for help with ...
- 💬 Ask me about ...
- 📫 How to reach me: ...
- 😄 Pronouns: ...
- ⚡ Fun fact: ...
-->

## FinBERT Sentiment Analyzer

This repository includes a simple script (`finbert_analysis.py`) that uses the
FinBERT model to classify financial text into the categories **Strong BUY**,
**BUY**, **Neutral**, **SELL** and **Strong SELL**. It loads the model from the
Hugging Face hub and can be run from the command line.

### Requirements
- Python 3.8+
- `transformers` and `torch`

Install the dependencies with:

```bash
pip install transformers torch
```

### Usage

```bash
python finbert_analysis.py "Your financial news or earnings report text here"
```

The script prints the sentiment label based on FinBERT's predictions. It adds
`Strong` prefixes when the model is highly confident (>0.75 probability).

### API Keys
If you wish to integrate this script with external data sources, export your API
key as an environment variable and modify the script accordingly. No external
calls are performed by default.

# AAPL Daily Advisor

This project provides a lightweight, **daily** recommendation engine for Apple Inc. (AAPL) shares.  It combines:

1. **News Sentiment** – powered by FinBERT, fine-tuned for finance text.
2. **Technical Indicators** – simple 50/200-day moving-average crossover.
3. **API Call Monitoring & Caching** – only *one* request per day to Yahoo Finance for prices and news.

Output classes follow the standard 5-point scale:

* `Strong Buy`
* `Buy`
* `Neutral`
* `Sell`
* `Strong Sell`

---

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python main.py            # uses cached data when available
python main.py --force-refresh   # bypass cache (counts towards daily quota)
```

Sample output:

```
Fetching data...
Loaded 8 news items and 252 price rows

=== Recommendation (AAPL) ===
{'combined_score': 0.42,
 'rating': 'Buy',
 'sentiment_score': 0.31,
 'technical_score': 0.2}
Timestamp: 2024-04-15T12:34:56.123456Z
```

---

## How it Works

| Layer | Details |
|-------|---------|
| **Data Fetcher** | *data/fetchers.py* pulls **daily** prices & news via `yfinance` with on-disk cache + API call counter |
| **Sentiment Model** | *models/finbert_model.py* wraps the open-source `yiyanghkust/finbert-tone` (3-class) and converts to numerical score |
| **Decision Engine** | *analytics/decision_engine.py* blends sentiment (60 %) and technicals (40 %) to produce a continuous score, then bins into the 5 categories given in `config.py` |
| **CLI** | *main.py* orchestrates the steps and prints a human-readable summary |

### Retraining / Fine-Tuning

If model drift is detected (or you have labelled data), call:

```python
from datasets import load_dataset
from models.finbert_model import FinBertSentiment

trainer_ds = load_dataset("csv", data_files="my_labelled_headlines.csv")
finbert = FinBertSentiment()
finbert.fine_tune(trainer_ds["train"], epochs=3)
```

---

## Customising

* Adjust weights or thresholds in `config.py`.
* Swap indicators (e.g., RSI, MACD) by editing `analytics/decision_engine.py`.
* Increase API safety limits via `config.py`.

---

## Caveats

* FinBERT returns *sentiment*, not explicit buy/sell signals. The mapping used here is illustrative.
* This repo is **not** financial advice. Use at your own risk.
