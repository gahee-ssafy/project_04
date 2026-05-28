"""
문제은행 AI 풀이 + 정답 배치 생성 스크립트.

사용법:
    cd project_04/backend
    python scripts/generate_solutions.py           # 전체 (solution 없는 것만)
    python scripts/generate_solutions.py --force   # 전체 재생성

출력 형식 (DB solution 필드):
    [정답]
    ③

    [풀이]
    ① ... — 틀린 이유
    ② ... — 틀린 이유
    ③ ... — 정답. 맞는 이유
    ④ ... — 틀린 이유
    ⑤ ... — 틀린 이유
"""
import sys
import os
import time
import re
import base64
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from database import get_all_problems, update_problem_solution, update_problem_question_text, get_conn
from services.ai import llm
from langchain_core.messages import SystemMessage, HumanMessage

CONCEPTS = [
    "수요·공급", "탄력성", "소비자이론", "생산자이론", "시장구조", "시장실패",
    "후생경제학", "게임이론", "소득분배", "기대효용·위험", "채권·금융",
    "최저임금·가격규제", "조세귀착",
    "GDP·국민소득", "소비·저축", "투자", "승수효과", "IS-LM",
    "총수요·총공급", "케인즈", "물가·인플레이션", "필립스곡선", "노동시장",
    "경제성장", "금리·이자율", "재정정책", "통화정책",
    "환율", "무역·국제수지", "비교우위",
]

SYSTEM_PROMPT = """당신은 경제학 기출문제 풀이 생성기입니다.
반드시 아래 형식만 출력하세요. 서론, 인사말, 마무리 코멘트, 팁은 절대 포함하지 마세요."""

SOLUTION_PROMPT = f"""이 경제학 기출문제 이미지를 분석해서 아래 형식으로 답해주세요.

[정답]
(① ② ③ ④ 중 하나)

[풀이]
① 요약 — 한 줄 이유
② 요약 — 한 줄 이유
③ 요약 — 한 줄 이유
④ 요약 — 한 줄 이유

[메타]
{{"question_text": "선지 제외 질문 본문만", "concept": "아래 목록 중 1개"}}

개념 목록: {", ".join(CONCEPTS)}

규칙:
- 선지별 설명은 각 1문장 이내로 핵심만 작성하세요.
- 정답 선지 앞에는 "정답." 을 붙이세요.
- 수식은 반드시 LaTeX 인라인($...$) 또는 블록($$...$$) 형식으로만 작성하세요.
- \\(...\\) 또는 \\[...\\] 형식은 절대 사용하지 마세요.
- concept은 목록 외 값 절대 금지.
- 한국어로만 답변하세요."""


def normalize_math(text: str) -> str:
    """Gemini가 \(...\) 또는 \[...\] 로 출력한 수식을 $...$, $$...$$ 로 변환."""
    # \[...\] → $$...$$
    text = re.sub(r'\\\[([\s\S]+?)\\\]', lambda m: f'$${m.group(1)}$$', text)
    # \(...\) → $...$
    text = re.sub(r'\\\(([\s\S]+?)\\\)', lambda m: f'${m.group(1)}$', text)
    return text


def parse_correct_answer(solution_text: str) -> str | None:
    """[정답] 섹션에서 ①②③④⑤ 중 하나를 추출."""
    m = re.search(r'\[정답\]\s*\n\s*([①②③④⑤])', solution_text)
    if m:
        return m.group(1)
    m = re.search(r'정답[:\s]+([①②③④⑤])', solution_text)
    return m.group(1) if m else None


def parse_meta(raw: str) -> tuple[str, str | None]:
    """[메타] 섹션에서 question_text, concept 추출."""
    m = re.search(r'\[메타\]\s*\n\s*(\{[\s\S]*?\})', raw)
    if not m:
        return '', None
    try:
        obj = json.loads(m.group(1))
        question_text = obj.get('question_text', '').strip()
        concept = obj.get('concept', '').strip()
        if concept not in CONCEPTS:
            concept = None
        return question_text, concept
    except Exception:
        return '', None


def save_meta(problem_id: int, question_text: str, concept: str | None):
    if question_text:
        update_problem_question_text(problem_id, question_text)
    if concept:
        conn = get_conn()
        conn.execute("UPDATE problems SET concept = ? WHERE id = ?", (concept, problem_id))
        conn.commit()
        conn.close()


def generate(force: bool = False):
    problems = get_all_problems()

    if force:
        targets = problems
    else:
        targets = [p for p in problems if not p.get('solution') or not p['solution'].strip()]

    total = len(targets)
    print(f'풀이 생성 대상: {total}개 / 전체 {len(problems)}개')
    if total == 0:
        print('모두 완료되어 있습니다. --force 옵션으로 재생성할 수 있습니다.')
        return

    success = fail = 0
    for i, p in enumerate(targets, 1):
        label = p.get('question', '')[:50]
        print(f'[{i}/{total}] {label}')

        # image_data는 row_to_dict()에 의해 base64 문자열로 반환됨
        img_bytes = None
        if p.get('image_data'):
            try:
                img_bytes = base64.b64decode(p['image_data'])
            except Exception:
                img_bytes = None

        if img_bytes is None:
            print('  [건너뜀] 이미지 없음')
            fail += 1
            continue

        for attempt in range(3):
            try:
                mime = p.get('image_mime') or 'image/png'
                img_b64 = base64.b64encode(img_bytes).decode('utf-8')
                messages = [
                    SystemMessage(content=SYSTEM_PROMPT),
                    HumanMessage(content=[
                        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{img_b64}"}},
                        {"type": "text", "text": SOLUTION_PROMPT},
                    ]),
                ]
                response = llm.invoke(messages)
                content = response.content
                solution = (
                    "".join(c.get("text", "") if isinstance(c, dict) else str(c) for c in content)
                    if isinstance(content, list) else content
                )
                solution = normalize_math(solution)
                correct_answer = parse_correct_answer(solution)
                question_text, concept = parse_meta(solution)
                update_problem_solution(p['id'], solution, correct_answer)
                save_meta(p['id'], question_text, concept)

                ans_display = correct_answer or '파싱실패'
                print(f'  [완료] 정답={ans_display} / concept={concept or "미매칭"}')
                success += 1
                time.sleep(10)  # 무료 티어: 분당 15회 → 10초 간격이면 ~6회/분으로 안정
                break

            except Exception as e:
                if '429' in str(e) or 'RESOURCE_EXHAUSTED' in str(e):
                    print(f'  [대기] 429 — 65초 후 재시도...')
                    time.sleep(65)
                else:
                    print(f'  [에러] {e}')
                    fail += 1
                    break

    print(f'\n완료: 성공 {success}개 / 실패 {fail}개')


if __name__ == '__main__':
    force = '--force' in sys.argv
    generate(force=force)
