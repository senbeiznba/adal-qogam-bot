# Адал қоғам AI — справочник-навигатор по Конституции 2026 (Telegram Mini App)

AI-бот на RAG: отвечает на вопросы на казахском и русском **только по официальным документам**, указывает статью и источник.
Если подтверждения в базе нет — честно сообщает об этом (п. 4.9 Положения).

## Возможности
- Чат: вопрос на казахском или русском → ответ со ссылкой на статью и цитатой первоисточника.
- Викторина по Конституции (5 вопросов, очки, уровни, значки, серия дней).
- Профиль игрока хранится в Telegram CloudStorage (или localStorage вне Telegram).

## Архитектура
Telegram Mini App (static/index.html) → FastAPI (main.py) → Chroma (векторный поиск) → Gemini (ответ по найденным фрагментам)

- `ingest.py` — нарезка документов по статьям, эмбеддинги, загрузка в Chroma
- `main.py` — API `/api/chat`: проверка подписи Telegram initData, rate limit, поиск, порог релевантности, генерация; `/api/quiz` — вопросы викторины
- `gen_quiz.py` — генерация банка вопросов `quiz.json` из базы (проверяйте результат вручную)
- `test_models.py` — проверка доступности моделей Gemini для вашего ключа
- `data/` — тексты документов и `sources.json` (название и URL первоисточника)

## Технологии
Python 3.11+, FastAPI, ChromaDB, Google Gemini (модели задаются в `.env`: `GEN_MODEL`, `FALLBACK_MODEL`, `EMBED_MODEL`), Telegram WebApp API.

## Запуск

Linux / macOS:
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # заполните GEMINI_API_KEY и BOT_TOKEN
python ingest.py            # один раз и после изменения документов
uvicorn main:app --reload   # http://localhost:8000
```

Windows (PowerShell), из папки проекта:
```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env   # заполните GEMINI_API_KEY и BOT_TOKEN, сохраните
.\.venv\Scripts\python.exe ingest.py
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

## Публикация в Telegram
1. Запустите сервер на хостинге с публичным **HTTPS**-адресом (или через туннель, например `cloudflared tunnel --url http://localhost:8000`).
2. В `.env` на сервере: `DEV_MODE=0` и `BOT_TOKEN` вашего бота — иначе подпись initData не проверяется и API открыт всем.
3. В @BotFather: `/mybots` → бот → Bot Settings → Menu Button (или Configure Mini App) → укажите HTTPS-адрес.

## Безопасность
Ключи только в `.env` (в `.gitignore`); подпись initData проверяется HMAC-SHA256; rate limit по пользователю Telegram;
ограничение длины запроса; системный промпт игнорирует инструкции из вопроса; ошибки API не показываются пользователю;
персональные данные не сохраняются.

## Источники
Конституция Республики Казахстан (2026) на русском и казахском языках, akorda.kz (см. `data/sources.json`).
