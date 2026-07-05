"""NCS 문제 AI 생성 서비스"""
import json
import re
from services.ai import _chat

GENERATE_PROMPT = """당신은 NCS 직업기초능력 문제 출제 전문가입니다.
주어진 예시 문제들의 스타일, 난이도, 출제 패턴을 분석하여 동일한 수준의 새 문제를 만드세요.

## 출력 형식 (JSON 배열, 반드시 이 형식만)
```json
[
  {
    "question": "문제 내용",
    "choices": {
      "①": "선지1",
      "②": "선지2",
      "③": "선지3",
      "④": "선지4"
    },
    "answer": "②",
    "explanation": "정답 해설 (1-2문장)"
  }
]
```

## 규칙
- 예시 문제를 그대로 복사하지 마세요. 완전히 새로운 문제를 만드세요.
- 같은 난이도와 스타일을 유지하세요.
- 정답은 반드시 ①②③④ 중 하나여야 합니다.
- JSON 형식 외 다른 텍스트는 절대 포함하지 마세요.
"""


def generate_ncs_questions(
    domain: str,
    agency: str,
    sample_text: str,
    count: int = 5,
) -> list[dict]:
    """샘플 문제를 기반으로 새 NCS 문제 생성."""

    user_prompt = f"""[출제 정보]
- NCS 분야: {domain}
- 출제 대행사: {agency}

[예시 문제 (스타일 참고용)]
{sample_text}

위 예시를 참고하여 {domain} 분야의 새로운 NCS 문제 {count}개를 JSON 배열로 생성하세요.
예시 문제의 문장이나 선지를 그대로 사용하지 말고, 완전히 새로운 내용으로 만드세요."""

    messages = [
        {"role": "system", "content": GENERATE_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    content = _chat(messages)

    # JSON 추출
    json_match = re.search(r'```json\s*([\s\S]+?)\s*```', content)
    if json_match:
        content = json_match.group(1)
    else:
        # 배열 직접 추출
        arr_match = re.search(r'\[[\s\S]+\]', content)
        if arr_match:
            content = arr_match.group(0)

    questions = json.loads(content)
    return questions
