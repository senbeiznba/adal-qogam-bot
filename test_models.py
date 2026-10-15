import os, time
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv(override=True)
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"],
                      http_options=types.HttpOptions(timeout=30000))

t = time.time()
try:
    client.models.embed_content(model="gemini-embedding-001", contents=["тест"])
    print("embed OK", round(time.time() - t, 1), "s")
except Exception as e:
    print("embed FAIL", round(time.time() - t, 1), "s", str(e)[:150])

for m in ["gemini-3.8-flash", "gemini-flash-latest", "gemini-flash-lite-latest"]:
    t = time.time()
    try:
        r = client.models.generate_content(model=m, contents="Ответь одним словом: привет")
        print(m, "OK", round(time.time() - t, 1), "s |", (r.text or "")[:30])
    except Exception as e:
        print(m, "FAIL", round(time.time() - t, 1), "s", str(e)[:150])