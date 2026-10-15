"""Генерация банка вопросов викторины из базы Конституции -> quiz.json
Запуск: python gen_quiz.py   (один раз, ~5-10 минут из-за лимитов)"""
import json, os, random, re, time
import chromadb
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv(override=True)
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"], http_options=types.HttpOptions(timeout=40000))
MODEL = os.getenv("GEN_MODEL", "gemini-flash-lite-latest")
PER_LANG = 20
KK = set("әіңғүұқөһӘІҢҒҮҰҚӨҺ")

col = chromadb.PersistentClient(path="chroma_db").get_collection("docs")
rows = col.get()
chunks = [(d, m) for d, m in zip(rows["documents"], rows["metadatas"]) if m["article"] and len(d) > 250]
random.seed(7); random.shuffle(chunks)

PROMPT = """По тексту статьи составь ОДИН вопрос викторины с 4 вариантами ответа.
Правила: один правильный ответ, остальные правдоподобные, но неверные; вопрос и ответы только по тексту;
язык вопроса: {lang}. Верни ТОЛЬКО JSON: {{"q":"...","options":["...","...","...","..."],"answer":0,"explanation":"1-2 предложения"}}

Текст ({title}, статья {article}):
{text}"""

out, count = [], {"ru": 0, "kk": 0}
for d, m in chunks:
    lang = "kk" if any(c in KK for c in d) else "ru"
    if count[lang] >= PER_LANG:
        continue
    try:
        r = client.models.generate_content(
            model=MODEL,
            contents=PROMPT.format(lang="казахский" if lang == "kk" else "русский", title=m["title"], article=m["article"], text=d[:1400]),
            config=types.GenerateContentConfig(temperature=0.4, response_mime_type="application/json"))
        item = json.loads(re.sub(r"^```json|```$", "", r.text.strip()))
        opts, ans = item["options"], item["answer"]
        assert len(opts) == 4 and 0 <= ans < 4
        correct = opts[ans]; random.shuffle(opts)
        out.append({"lang": lang, "q": item["q"], "options": opts, "answer": opts.index(correct),
                    "explanation": item["explanation"], "article": m["article"], "url": m["url"]})
        count[lang] += 1
        print(f"{lang} {count[lang]}/{PER_LANG}")
    except Exception as e:
        print("пропуск:", str(e)[:100])
    time.sleep(6)
    if all(v >= PER_LANG for v in count.values()):
        break

json.dump(out, open("quiz.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("Готово, вопросов:", len(out), "- ПРОВЕРЬТЕ quiz.json глазами перед защитой!")
