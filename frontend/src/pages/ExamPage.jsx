import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getExamProblems, submitExam } from '../api/exam'
import MarkdownRenderer from '../components/MarkdownRenderer'

const PHASE = { SOLVING: 'solving', GRADING: 'grading', RESULT: 'result' }
const CHOICES = ['①', '②', '③', '④', '⑤']
const CHOICE_VALS = ['①', '②', '③', '④', '⑤']

export default function ExamPage() {
  const { year, round } = useParams()
  const navigate = useNavigate()

  const [problems, setProblems]   = useState([])
  const [answers, setAnswers]     = useState({})   // { problem_id: '①'|'②'|... }
  const [correct, setCorrect]     = useState({})   // { problem_id: bool|null }
  const [current, setCurrent]     = useState(0)
  const [phase, setPhase]         = useState(PHASE.SOLVING)
  const [result, setResult]       = useState(null)
  const [loading, setLoading]     = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [showSolution, setShowSolution] = useState(false)

  useEffect(() => {
    getExamProblems(year, round)
      .then((res) => {
        setProblems(res.data)
        const init = {}
        res.data.forEach((p) => { init[p.id] = '' })
        setAnswers(init)
      })
      .finally(() => setLoading(false))
  }, [year, round])

  // 문제 이동 시 풀이 접기
  useEffect(() => { setShowSolution(false) }, [current])

  // ── 풀이 완료 → 채점 단계 ────────────────────────────
  const goToGrading = () => {
    // correct_answer 있는 문제는 자동 채점
    const initCorrect = {}
    problems.forEach((p) => {
      if (p.correct_answer) {
        initCorrect[p.id] = answers[p.id] === p.correct_answer
      } else {
        initCorrect[p.id] = null  // 수동 채점 필요
      }
    })
    setCorrect(initCorrect)
    setPhase(PHASE.GRADING)
    setCurrent(0)
  }

  // ── 최종 제출 ──────────────────────────────────────
  const handleSubmit = async () => {
    setSubmitting(true)
    try {
      const payload = {
        exam_year: parseInt(year),
        exam_round: parseInt(round),
        answers: problems.map((p) => ({
          problem_id: p.id,
          user_answer: answers[p.id] || '',
          is_correct: correct[p.id] === true,
        })),
      }
      const res = await submitExam(payload)
      setResult(res.data)
      setPhase(PHASE.RESULT)
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) return <p className="loading">문제를 불러오는 중...</p>
  if (problems.length === 0) return <p className="loading">문제가 없어요.</p>

  const total = problems.length
  const prob  = problems[current]

  // ═══════════════════════════════════════════════════
  // 1단계: 문제 풀기
  // ═══════════════════════════════════════════════════
  if (phase === PHASE.SOLVING) {
    const answeredCount = Object.values(answers).filter(Boolean).length

    return (
      <div className="exam-page">
        {/* 상단 */}
        <div className="exam-header">
          <span className="exam-title">{year}년 {round}회차</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <span className="exam-progress">{answeredCount} / {total} 답안 선택</span>
            {answeredCount > 0 && (
              <button className="btn-stop" onClick={goToGrading}>여기까지 채점</button>
            )}
          </div>
        </div>
        <div className="progress-bar">
          <div className="progress-fill" style={{ width: `${(answeredCount / total) * 100}%` }} />
        </div>

        {/* 문제 카드 */}
        <div className="question-card">
          <p className="question-num">문제 {current + 1}</p>
          {prob.image_data ? (
            <img
              src={`data:${prob.image_mime};base64,${prob.image_data}`}
              alt="문제 이미지"
              className="question-img"
            />
          ) : (
            <p className="question-text">{prob.question}</p>
          )}
          <p className="question-meta">{prob.topic} · 난이도 {prob.difficulty}</p>
        </div>

        {/* ①②③④⑤ 선택 버튼 */}
        <div className="choice-buttons">
          {CHOICES.map((ch, i) => (
            <button
              key={ch}
              className={`choice-btn ${answers[prob.id] === CHOICE_VALS[i] ? 'selected' : ''}`}
              onClick={() => setAnswers({ ...answers, [prob.id]: CHOICE_VALS[i] })}
            >
              {ch}
            </button>
          ))}
        </div>

        {/* 네비게이션 */}
        <div className="exam-nav">
          <button className="btn-prev" onClick={() => setCurrent((c) => c - 1)} disabled={current === 0}>
            ← 이전
          </button>
          {current < total - 1 ? (
            <button className="btn-next" onClick={() => setCurrent((c) => c + 1)}>
              다음 →
            </button>
          ) : (
            <button className="btn-submit" onClick={goToGrading}>
              채점하기
            </button>
          )}
        </div>

        {/* 문제 번호 점프 */}
        <div className="question-dots">
          {problems.map((p, i) => (
            <button
              key={p.id}
              className={`dot ${i === current ? 'active' : ''} ${answers[p.id] ? 'answered' : ''}`}
              onClick={() => setCurrent(i)}
            >
              {i + 1}
            </button>
          ))}
        </div>
      </div>
    )
  }

  // ═══════════════════════════════════════════════════
  // 2단계: 채점
  // ═══════════════════════════════════════════════════
  if (phase === PHASE.GRADING) {
    const gradedCount = Object.values(correct).filter((v) => v !== null).length
    const allGraded   = gradedCount === total
    const myAnswer    = answers[prob.id]
    const isAutoGraded = !!prob.correct_answer

    return (
      <div className="exam-page">
        <div className="exam-header">
          <span className="exam-title">채점</span>
          <span className="exam-progress">{gradedCount} / {total}</span>
        </div>
        <div className="progress-bar">
          <div className="progress-fill grading" style={{ width: `${(gradedCount / total) * 100}%` }} />
        </div>

        <div className="grading-card">
          <p className="question-num">문제 {current + 1}</p>

          {/* 문제 이미지 */}
          {prob.image_data ? (
            <img
              src={`data:${prob.image_mime};base64,${prob.image_data}`}
              alt="문제 이미지"
              className="question-img"
            />
          ) : (
            <p className="question-text">{prob.question}</p>
          )}

          {/* 내 답 / 정답 표시 */}
          <div className="answer-compare">
            <div className={`answer-box ${
              isAutoGraded
                ? correct[prob.id] ? 'box-correct' : 'box-wrong'
                : ''
            }`}>
              <span className="answer-label">내 답</span>
              <span className="answer-val">{myAnswer || '(미선택)'}</span>
            </div>
            {isAutoGraded && (
              <div className="answer-box box-answer">
                <span className="answer-label">정답</span>
                <span className="answer-val">{prob.correct_answer}</span>
              </div>
            )}
          </div>

          {/* 수동 채점 (correct_answer 없는 경우) */}
          {!isAutoGraded && (
            <div className="grade-buttons">
              <button
                className={`btn-correct ${correct[prob.id] === true ? 'selected' : ''}`}
                onClick={() => setCorrect({ ...correct, [prob.id]: true })}
              >
                ⭕ 맞았어요
              </button>
              <button
                className={`btn-wrong ${correct[prob.id] === false ? 'selected' : ''}`}
                onClick={() => setCorrect({ ...correct, [prob.id]: false })}
              >
                ❌ 틀렸어요
              </button>
            </div>
          )}

          {/* 풀이 토글 */}
          {prob.solution && (
            <div className="solution-section">
              <button
                className="btn-toggle-solution"
                onClick={() => setShowSolution((v) => !v)}
              >
                {showSolution ? '풀이 접기 ▲' : 'AI 풀이 보기 ▼'}
              </button>
              {showSolution && (
                <div className="solution-body">
                  <MarkdownRenderer>{prob.solution}</MarkdownRenderer>
                </div>
              )}
            </div>
          )}
        </div>

        {/* 네비게이션 */}
        <div className="exam-nav">
          <button className="btn-prev" onClick={() => setCurrent((c) => c - 1)} disabled={current === 0}>
            ← 이전
          </button>
          {current < total - 1 ? (
            <button className="btn-next" onClick={() => setCurrent((c) => c + 1)}>
              다음 →
            </button>
          ) : (
            <button
              className="btn-submit"
              onClick={handleSubmit}
              disabled={submitting}
            >
              {submitting ? '제출 중...' : '결과 보기'}
            </button>
          )}
        </div>

        <div className="question-dots">
          {problems.map((p, i) => (
            <button
              key={p.id}
              className={`dot ${i === current ? 'active' : ''} ${
                correct[p.id] === true  ? 'correct' :
                correct[p.id] === false ? 'wrong' : ''
              }`}
              onClick={() => setCurrent(i)}
            >
              {i + 1}
            </button>
          ))}
        </div>
      </div>
    )
  }

  // ═══════════════════════════════════════════════════
  // 3단계: 결과
  // ═══════════════════════════════════════════════════
  if (phase === PHASE.RESULT && result) {
    const score      = Math.round((result.correct / result.total) * 100)
    const wrongItems = result.results.filter((r) => !r.is_correct)

    return (
      <div className="exam-page">
        <div className="result-header">
          <h2>채점 결과</h2>
          <p>{year}년 {round}회차</p>
        </div>

        <div className="score-card">
          <div className="score-circle">
            <span className="score-num">{score}</span>
            <span className="score-unit">점</span>
          </div>
          <div className="score-detail">
            <span className="score-correct">⭕ {result.correct}개</span>
            <span className="score-wrong">❌ {result.wrong}개</span>
            <span className="score-total">전체 {result.total}문제</span>
          </div>
        </div>

        {wrongItems.length > 0 && (
          <div className="wrong-section">
            <h3>오답노트에 자동 저장됐어요 ({wrongItems.length}개)</h3>
            <ul className="wrong-list">
              {wrongItems.map((r) => (
                <li key={r.problem_id} className="wrong-item">
                  <p className="wrong-question">{r.question.slice(0, 60)}...</p>
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="result-actions">
          <button className="btn-notebook" onClick={() => navigate('/notebook')}>
            오답노트 보러 가기
          </button>
          <button className="btn-retry" onClick={() => navigate('/exam')}>
            다른 회차 풀기
          </button>
        </div>
      </div>
    )
  }
}
