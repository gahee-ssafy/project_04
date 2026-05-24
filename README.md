backend : fastAPI
frontend : react
DB : sqlite3
LLM : gemini-flash-3

```
cd /backend
uvicorn main:app --reload --port 8000
```

- 모바일확인용

```

uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

# 업무관리

1. problem-solution 쌓기.

```
./venv/Scripts/python.exe scripts/generate_solutions.py
```
