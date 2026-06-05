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

## 프로젝트 전체 요약

---

### 🎯 서비스 정의

**공무원 경제학 시험 AI 학습 도우미**

- 혼자 공부하는 수험생 옆에서 AI가 튜터 역할
- 문제 풀기 → 오답 분석 → AI 토론 → 학습 기록

---

### 🏗️ 기술 스택

| 구분     | 기술               |
| -------- | ------------------ |
| Backend  | FastAPI + SQLite   |
| Frontend | React + Vite       |
| AI       | Gemini (LangChain) |
| 배포     | 로컬 (예정)        |

---

### 📱 주요 기능

**① AI 튜터 (메인)**

- 문제/이미지 업로드 → AI 풀이
- 멀티모달 지원 (필기 사진도 분석)

**② 모의고사**

- 연도·회차별 시험 응시
- 자동 채점 + 오답 오답노트 저장
- localStorage로 중간저장 (새로고침 대비)

**③ 오답노트**

- 회차별 그룹 보기
- 메모 작성
- AI 토론 (소크라테스식 문답)
- 편집모드 (필터/정렬/그룹 선택 삭제)

**④ OX 퀴즈**

- 오답노트 해설에서 자동 생성
- 틀리면 관련 기출문제 연결

**⑤ 학습일지**

- 통계 (오답수, 메모수, 토론수, 학습일수)
- 자주 다룬 개념 (오늘 개선)
- OX 퀴즈
- AI 패턴 분석 + 학습 방향 (Gemini, 캐시)

---

### 🗄️ 데이터 구조 (8개 테이블)

```
users
  └─ sessions (질문/오답노트 전체)
       ├─ memos (학생 메모)
       ├─ notebook_chats (AI 토론)
       └─ problem_id → problems (문제은행)
                            └─ concept (개념 태그)
  └─ exam_attempts (모의고사 응시 기록)
  └─ learning_reports (AI 분석 캐시)
  └─ user_summaries (구버전 요약, 미사용)
```

---

### 💡 AI 활용 포인트

| 기능          | AI 역할                 |
| ------------- | ----------------------- |
| AI 튜터       | 실시간 풀이 생성        |
| AI 토론       | 소크라테스식 대화       |
| 오답노트 채팅 | 메모 기반 개념 확인     |
| 학습일지 분석 | 패턴 분석 + 조언 (캐시) |
| OX 퀴즈       | 해설 파싱 (AI 불필요)   |
| 개념 태깅     | 키워드 매칭 (AI 불필요) |

---

### 🚧 현재 한계

- 사용자 1명 (본인)
- `sessions.question` 접두사로 타입 구분 (기술부채)
- 문제은행 확장 필요 (현재 5회차 125문제)
- 경제학만 지원 (향후 행정학, 경영학 확장 예정)

---

### 🔜 다음 단계 후보

- UX 2~5회차 개선
- 개념별 오답률 시각화
- 다과목 확장
- 실제 사용자 온보딩
