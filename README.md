1.  backend : fastAPI

```
- uvicorn main:app --reload
```

2.  frontend : react
3.  DB : sqlite3
4.  LLM : gemini-flash-3

# 업무관리

1. fastAPI - sqlite 저장 확인
2. LLM api_key 연결이 차후 업무

# 구조

```
views.py       → 요청/응답 처리 (교통 정리)
search_engine.py → AI 핵심 로직 (실제 일꾼)
models.py      → 데이터 구조 (DB 설계)
serializers.py → 데이터 변환 (입출력 형식)
```
