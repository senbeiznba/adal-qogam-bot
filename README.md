# Адал қоғам AI — справочник-навигатор по Конституции 2026 (Telegram Mini App)

AI-бот на RAG: отвечает на вопросах на казахском и русском **только по официальным документам**, указывает статью и источник.
Если подтверждения в базе нет — честно сообщает об этом (п. 4.9 Положения).

## Архитектура
Telegram Mini App (static/index.html) → FastAPI (main.py) → Chroma (векторный поиск) → Gemini (ответ по найденным фрагментам)

- `ingest.py` — нарезка документов по статьям, эмбеддинги, загрузка в Chroma
- `main.py` — API `/api/chat`: проверка подписи Telegram initData, rate limit, поиск, порог релевантности, генерация
- `data/` — тексты документов и `sources.json` (название и URL первоисточника)

## Технологии
Python 3.11+, FastAPI, ChromaDB, Google Gemini (`gemini-2.5-flash`, `gemini-embedding-001`), Telegram WebApp API.

## Запуск
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # заполните GEMINI_API_KEY и BOT_TOKEN
python ingest.py            # один раз и после изменения документов
uvicorn main:app --reload   # http://localhost:8000
```

## Безопасность
Ключи только в `.env` (в `.gitignore`); подпись initData проверяется HMAC-SHA256; rate limit; ограничение длины запроса;
системный промпт игнорирует инструкции из вопроса; персональные данные не сохраняются.

## Источники
Конституция Республики Казахстан (2026), adilet.zan.kz
