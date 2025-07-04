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
