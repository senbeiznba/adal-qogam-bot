"""Нарезка документов из data/ по статьям и загрузка в Chroma.
Запуск: python ingest.py"""
import json, os, re, time
import chromadb
from dotenv import load_dotenv
from google import genai

BASE = os.path.dirname(os.path.abspath(__file__))  # пути не зависят от папки запуска
load_dotenv(os.path.join(BASE, ".env"), override=True)
if not os.getenv("GEMINI_API_KEY"):
    raise SystemExit("GEMINI_API_KEY пустой: впишите ключ в .env и сохраните файл")
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
EMBED_MODEL = os.getenv("EMBED_MODEL", "gemini-embedding-001")

# "Статья 12" / "12-бап" в начале строки (допускаем markdown-мусор)
ART = re.compile(r"^[\s#*_>]*(?:Статья\s+(\d+(?:-\d+)?)|(\d+(?:-\d+)?)\s*-?\s*бап)", re.I | re.M)
MAX_LEN = 1500

def split_doc(text: str):
    marks = list(ART.finditer(text))
    if len(marks) < 5:  # заголовков статей нет — режем по абзацам
        return [("", c) for c in chunk(text)]
    out = []
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        label = m.group(1) or m.group(2)
        for c in chunk(text[m.start():end]):
            out.append((label, c))
    return out

def chunk(text: str):
    parts, cur = [], ""
    for para in re.split(r"\n\s*\n", text.strip()):
        if len(cur) + len(para) > MAX_LEN and cur:
            parts.append(cur.strip()); cur = ""
        cur += para + "\n\n"
    if cur.strip():
        parts.append(cur.strip())
    return parts

def embed(texts):
    while True:
        try:
            r = client.models.embed_content(model=EMBED_MODEL, contents=texts)
            return [e.values for e in r.embeddings]
        except Exception as e:
            if "PerDay" in str(e):  # дневной лимит: ждать минутами бесполезно
                raise SystemExit("Дневной лимит эмбеддингов Gemini исчерпан. Загруженное сохранено — "
                                 "запустите ingest.py позже, он продолжит с места остановки.")
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                print("  лимит, жду 30 секунд…")
                time.sleep(30)
            else:
                raise

def main():
    sources = json.load(open(os.path.join(BASE, "data", "sources.json"), encoding="utf-8"))
    db = chromadb.PersistentClient(path=os.path.join(BASE, "chroma_db"))
    # коллекцию не пересоздаём: повторный запуск досчитывает только новые и изменённые фрагменты
    col = db.get_or_create_collection("docs", metadata={"hnsw:space": "cosine"})
    ids, docs, metas = [], [], []
    for fname, meta in sources.items():
        path = os.path.join(BASE, "data", fname)
        if not os.path.exists(path):
            print("нет файла:", path); continue
        for n, (label, c) in enumerate(split_doc(open(path, encoding="utf-8").read())):
            ids.append(f"{fname}-{n}"); docs.append(c)
            metas.append({"title": meta["title"], "url": meta["url"], "article": label})
    old = col.get(include=["documents", "metadatas"])
    have = {i: (d, m) for i, d, m in zip(old["ids"], old["documents"], old["metadatas"])}
    stale = [i for i in have if i not in set(ids)]
    if stale:
        col.delete(ids=stale)
    todo = [k for k in range(len(ids)) if have.get(ids[k]) != (docs[k], metas[k])]
    for i in range(0, len(todo), 20):
        b = todo[i:i + 20]
        col.upsert(ids=[ids[k] for k in b], documents=[docs[k] for k in b], metadatas=[metas[k] for k in b],
                   embeddings=embed([docs[k] for k in b]))  # сохраняем каждую пачку сразу
        print(f"  эмбеддинги: {min(i + 20, len(todo))}/{len(todo)}")
        time.sleep(14)  # не выходим за 100 запросов в минуту
    print(f"Фрагментов в базе: {col.count()} (новых или изменённых: {len(todo)}, удалено: {len(stale)})")

if __name__ == "__main__":
    main()
