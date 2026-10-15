"""Нарезка документов из data/ по статьям и загрузка в Chroma.
Запуск: python ingest.py"""
import json, os, re
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
    import time
    vecs = []
    i = 0
    while i < len(texts):
        batch = texts[i:i + 20]
        try:
            r = client.models.embed_content(model=EMBED_MODEL, contents=batch)
            vecs += [e.values for e in r.embeddings]
            i += 20
            print(f"  эмбеддинги: {min(i, len(texts))}/{len(texts)}")
            time.sleep(14)  # не выходим за 100 запросов в минуту
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                print("  лимит, жду 30 секунд…")
                time.sleep(30)
            else:
                raise
    return vecs

def main():
    sources = json.load(open(os.path.join(BASE, "data", "sources.json"), encoding="utf-8"))
    db = chromadb.PersistentClient(path=os.path.join(BASE, "chroma_db"))
    try: db.delete_collection("docs")
    except Exception: pass
    col = db.create_collection("docs", metadata={"hnsw:space": "cosine"})
    ids, docs, metas = [], [], []
    for fname, meta in sources.items():
        path = os.path.join(BASE, "data", fname)
        if not os.path.exists(path):
            print("нет файла:", path); continue
        for n, (label, c) in enumerate(split_doc(open(path, encoding="utf-8").read())):
            ids.append(f"{fname}-{n}"); docs.append(c)
            metas.append({"title": meta["title"], "url": meta["url"], "article": label})
    col.add(ids=ids, documents=docs, metadatas=metas, embeddings=embed(docs))
    print(f"Загружено фрагментов: {len(ids)}")

if __name__ == "__main__":
    main()
