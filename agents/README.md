# Nhom23-403-Day06

## VinFast AI Chatbot (basic CLI prototype)

Ban nay la prototype co ban nhat: chatbot chay tren terminal, khong can web UI.

### 1) Setup

```bash
cd Nhom23-403-Day06
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2) API key

```bash
copy .env.example .env
```

Mo `.env` va dien:

```text
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4.1-mini
```

### 3) Run chatbot

```bash
python chatbot.py
```

Nhap cau hoi vi du:

`Toi co 800 trieu, gia dinh 4 nguoi, di noi thanh, chua co cho sac tai nha`

### 4) How it works

1. Parse nhanh intent tu user query (budget, family size, usage, charging).
2. Rule-based scoring de lay top 2-3 xe.
3. Lay pros/cons tu `data/reviews_processed.json`.
4. Lay goi y bao duong tu `data/maintenance.json`.
5. Goi OpenAI de sinh cau tra loi tu context tren.

Neu chua co API key, app tu dong fallback ve rule-based answer.
