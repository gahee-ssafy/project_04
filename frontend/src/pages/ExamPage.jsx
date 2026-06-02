import { useEffect, useState, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getExamProblems, getNcsProblems, submitExam, submitNcs } from '../api/exam'
import client from '../api/client'
import MarkdownRenderer from '../components/MarkdownRenderer'
import SolutionRenderer from '../components/SolutionRenderer'
import DrawingCanvas from '../components/DrawingCanvas'

const PHASE = { SOLVING: 'solving', GRADING: 'grading', RESULT: 'result' }
const CHOICES = ['①', '②', '③', '④']
const CHOICE_VALS = ['①', '②', '③', '④']

const STEPS = [
  { key: PHASE.SOLVING,  label: '풀기' },
  { key: PHASE.GRADING,  label: '채점' },
  { key: PHASE.RESULT,   label: '결과' },
]

function ExamStepper({ phase }) {
  const currentIdx = STEPS.findIndex(s => s.key === phase)
  return (
    <div className="exam-stepper">
      {STEPS.map((step, i) => (
        <div key={step.key} className="exam-step-item">
          <div className={`exam-step-circle ${i < currentIdx ? 'done' : i === currentIdx ? 'active' : ''}`}>
            {i < currentIdx ? '✓' : i + 1}
          </div>
          <span className={`exam-step-label ${i === currentIdx ? 'active' : ''}`}>{step.label}</span>
          {i < STEPS.length - 1 && (
            <div className={`exam-step-line ${i < currentIdx ? 'done' : ''}`} />
          )}
        </div>
      ))}
    </div>
  )
}

export default function ExamPage() {
  const { year, round, agency, domain } = useParams()
  const navigate = useNavigate()
  const isNcs = !!agency  // NCS 여부

  const [problems, setProblems]     = useState([])
  const [answers, setAnswers]       = useState({})
  const [correct, setCorrect]       = useState({})
  const [current, setCurrent]       = useState(0)
  const [phase, setPhase]           = useState(PHASE.SOLVING)
  const [result, setResult]         = useState(null)
  const [loading, setLoading]       = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [showSolution, setShowSolution] = useState(false)
  const [selected, setSelected]     = useState({})
  const [saving, setSaving]         = useState(false)
  const [saved, setSaved]           = useState(false)
  const [expanded, setExpanded]     = useState({})
  const [timeSpent, setTimeSpent]   = useState({}) // { [problem_id]: seconds }
  const startTimeRef                = useRef(Date.now())

  const STORAGE_KEY = isNcs
    ? `exam_progress_ncs_${agency}_${year}_${domain}`
    : `exam_progress_${year}_${round}`

  // 문제 로드 + localStorage 복원
  useEffect(() => {
    const fetchFn = isNcs
      ? getNcsProblems(decodeURIComponent(agency), year, decodeURIComponent(domain))
      : getExamProblems(year, round)
    fetchFn
      .then((res) => {
        setProblems(res.data)
        const init = {}
        res.data.forEach((p) => { init[p.id] = '' })

        const savedRaw = localStorage.getItem(STORAGE_KEY)
        if (savedRaw) {
          try {
            const s = JSON.parse(savedRaw)
            // result 없이 RESULT phase이면 오염된 데이터 → 초기화
            if (s.phase === PHASE.RESULT && !s.result) {
              localStorage.removeItem(STORAGE_KEY)
              setAnswers(init)
            } else {
              setAnswers({ ...init, ...s.answers })
              setCorrect(s.correct || {})
              setCurrent(s.current || 0)
              setPhase(s.phase || PHASE.SOLVING)
              if (s.result) setResult(s.result)
              if (s.selected) setSelected(s.selected)
            }
          } catch {
            localStorage.removeItem(STORAGE_KEY)
            setAnswers(init)
          }
        } else {
          setAnswers(init)
        }
      })
      .finally(() => setLoading(false))
  }, [year, round, agency, domain])

  // 상태 변경 시 localStorage 저장
  useEffect(() => {
    if (loading) return
    if (phase === PHASE.RESULT && saved) {
      localStorage.removeItem(STORAGE_KEY)
      return
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ answers, correct, current, phase, result, selected }))
  }, [answers, correct, current, phase, result, selected, loading])

  useEffect(() => { setShowSolution(false) }, [current])

  // 문제 이동 시 이전 문제 소요시간 누적
  useEffect(() => {
    if (loading || problems.length === 0) return
    const probId = problems[current]?.id
    startTimeRef.current = Date.now()
    return () => {
      const elapsed = Math.round((Date.now() - startTimeRef.current) / 1000)
      if (elapsed > 0 && probId) {
        setTimeSpent(prev => ({ ...prev, [probId]: (prev[probId] || 0) + elapsed }))
      }
    }
  }, [current, loading, problems])

  const goToGrading = () => {
    const initCorrect = {}
    problems.forEach((p) => {
      initCorrect[p.id] = p.correct_answer ? answers[p.id] === p.correct_answer : null
    })
    setCorrect(initCorrect)
    setPhase(PHASE.GRADING)
    setCurrent(0)
  }

  const examTitle = isNcs
    ? `${decodeURIComponent(agency)} · ${year}년 · ${decodeURIComponent(domain)}`
    : `${year}년 ${round}회차`

  const handleSubmit = async () => {
    setSubmitting(true)
    try {
      const answerPayload = problems.map((p) => ({
        problem_id: p.id,
        user_answer: answers[p.id] || '',
        is_correct: correct[p.id] === true,
      }))
      const payload = isNcs
        ? { ncs_agency: decodeURIComponent(agency), exam_year: parseInt(year),
            ncs_domain: decodeURIComponent(domain), answers: answerPayload }
        : { exam_year: parseInt(year), exam_round: parseInt(round), answers: answerPayload }
      const res = isNcs ? await submitNcs(payload) : await submitExam(payload)
      setResult(res.data)
      // 오답 기본 선택 초기화 (전부 미선택)
      const initSel = {}
      res.data.results.filter(r => !r.is_correct).forEach(r => { initSel[r.problem_id] = false })
      setSelected(initSel)
      setPhase(PHASE.RESULT)
    } finally {
      setSubmitting(false)
    }
  }

  const handleSaveNotebook = async () => {
    const ids = Object.entries(selected).filter(([, v]) => v).map(([k]) => parseInt(k))
    if (ids.length === 0) return
    if (!confirm(`${ids.length}개의 문제를 오답노트에 저장할까요?`)) return
    setSaving(true)
    try {
      const payload = isNcs
        ? { exam_year: parseInt(year), ncs_agency: decodeURIComponent(agency),
            ncs_domain: decodeURIComponent(domain), problem_ids: ids }
        : { exam_year: parseInt(year), exam_round: parseInt(round), problem_ids: ids }
      await client.post('/exam/add-to-notebook', payload)
      setSaved(true)
      localStorage.removeItem(STORAGE_KEY)
    } finally {
      setSaving(false)
    }
  }

  const toggleAll = (wrongItems) => {
    const allSelected = wrongItems.every(r => selected[r.problem_id])
    const next = {}
    wrongItems.forEach(r => { next[r.problem_id] = !allSelected })
    setSelected(prev => ({ ...prev, ...next }))
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
        <div className="exam-header">
          <span className="exam-title">{examTitle}</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span className="exam-progress">{answeredCount}/{total}</span>
            {answeredCount > 0 && (
              <button className="btn-stop" onClick={goToGrading}>채점</button>
            )}
          </div>
        </div>
        <ExamStepper phase={phase} />
        <div className="progress-bar">
          <div className="progress-fill" style={{ width: `${(answeredCount / total) * 100}%` }} />
        </div>

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

        <div className="exam-body-layout">
          <div className="exam-question-col">
            <DrawingCanvas questionId={prob.id}>
              <div className="question-card">
                <p className="question-num">문제 {current + 1}</p>
                {prob.image_data ? (
                  <img src={`data:${prob.image_mime};base64,${prob.image_data}`} alt="문제 이미지" className="question-img" />
                ) : (
                  <p className="question-text">{prob.question}</p>
                )}
                <p className="question-meta">{prob.topic} · 난이도 {prob.difficulty}</p>
              </div>
            </DrawingCanvas>
          </div>
          <div className="exam-choice-col">
            <div className="choice-buttons">
              {CHOICES.map((ch, i) => (
                <button
                  key={ch}
                  className={`choice-btn ${answers[prob.id] === CHOICE_VALS[i] ? 'selected' : ''}`}
                  onClick={() => setAnswers({ ...answers, [prob.id]: answers[prob.id] === CHOICE_VALS[i] ? '' : CHOICE_VALS[i] })}
                >
                  {ch}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="exam-nav">
          <button className="btn-prev" onClick={() => setCurrent(c => c - 1)} disabled={current === 0}>← 이전</button>
          <button className="btn-submit" onClick={goToGrading} disabled={answeredCount === 0}>채점하기</button>
          <button className="btn-next" onClick={() => setCurrent(c => c + 1)} disabled={current === total - 1}>다음 →</button>
        </div>
      </div>
    )
  }

  // ═══════════════════════════════════════════════════
  // 2단계: 채점
  // ═══════════════════════════════════════════════════
  if (phase === PHASE.GRADING) {
    const gradedCount = Object.values(correct).filter(v => v !== null).length
    const myAnswer    = answers[prob.id]
    const isAutoGraded = !!prob.correct_answer

    return (
      <div className="exam-page">
        <div className="exam-header">
          <span className="exam-title">{examTitle}</span>
          <span className="exam-progress">{gradedCount}/{total}</span>
        </div>
        <ExamStepper phase={phase} />
        <div className="progress-bar">
          <div className="progress-fill grading" style={{ width: `${(gradedCount / total) * 100}%` }} />
        </div>

        <div className="question-dots">
          {problems.map((p, i) => (
            <button
              key={p.id}
              className={`dot ${i === current ? 'active' : ''} ${correct[p.id] === true ? 'correct' : correct[p.id] === false ? 'wrong' : ''}`}
              onClick={() => setCurrent(i)}
            >
              {i + 1}
            </button>
          ))}
        </div>

        <div className="grading-card">
          <p className="question-num">문제 {current + 1}</p>
          {prob.image_data ? (
            <img src={`data:${prob.image_mime};base64,${prob.image_data}`} alt="문제 이미지" className="question-img" />
          ) : (
            <p className="question-text">{prob.question}</p>
          )}

          <div className="answer-compare">
            <div className={`answer-box ${isAutoGraded ? (correct[prob.id] ? 'box-correct' : 'box-wrong') : ''}`}>
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

          {!isAutoGraded && (
            <div className="grade-buttons">
              <button className={`btn-correct ${correct[prob.id] === true ? 'selected' : ''}`} onClick={() => setCorrect({ ...correct, [prob.id]: true })}>⭕ 맞았어요</button>
              <button className={`btn-wrong ${correct[prob.id] === false ? 'selected' : ''}`} onClick={() => setCorrect({ ...correct, [prob.id]: false })}>❌ 틀렸어요</button>
            </div>
          )}

          {prob.solution && (
            <div className="solution-section">
              <button className="btn-toggle-solution" onClick={() => setShowSolution(v => !v)}>
                {showSolution ? 'AI 풀이 접기 ▲' : 'AI 풀이 보기 ▼'}
              </button>
              {showSolution && <div className="solution-body"><SolutionRenderer>{prob.solution}</SolutionRenderer></div>}
            </div>
          )}
        </div>

        <div className="exam-nav">
          <button className="btn-prev" onClick={() => setCurrent(c => c - 1)} disabled={current === 0}>← 이전</button>
          <button className="btn-submit" onClick={handleSubmit} disabled={submitting}>
            {submitting ? '제출 중...' : '결과 보기'}
          </button>
          <button className="btn-next" onClick={() => setCurrent(c => c + 1)} disabled={current === total - 1}>다음 →</button>
        </div>
      </div>
    )
  }

  // ═══════════════════════════════════════════════════
  // 3단계: 결과
  // ═══════════════════════════════════════════════════
  if (phase === PHASE.RESULT && !result) {
    return <p className="loading">불러오는 중...</p>
  }

  if (phase === PHASE.RESULT && result) {
    const score      = Math.round((result.correct / result.total) * 100)
    const wrongItems = result.results.filter(r => !r.is_correct)
    const selectedCount = Object.values(selected).filter(Boolean).length
    const allSelected = wrongItems.length > 0 && wrongItems.every(r => selected[r.problem_id])

    return (
      <div className="exam-page">
        <div className="exam-header">
          <span className="exam-title">{examTitle}</span>
          <span className="exam-progress">완료</span>
        </div>
        <ExamStepper phase={phase} />
        <div className="result-header">

        </div>

        <div className="result-actions">
          <button className="btn-notebook" onClick={() => navigate('/?tab=notebook')}>오답노트</button>
          <button className="btn-retry" onClick={() => {
            const init = {}
            problems.forEach((p) => { init[p.id] = '' })
            setAnswers(init)
            setCorrect({})
            setSelected({})
            setResult(null)
            setSaved(false)
            setCurrent(0)
            setPhase(PHASE.SOLVING)
            localStorage.removeItem(STORAGE_KEY)
          }}>다시풀기</button>
          <button className="btn-retry" onClick={() => navigate('/')}>다른회차</button>
        </div>

        <div className="score-card">
          <div className="score-stats">
            <div className="score-stat">
              <span className="score-stat-num correct">{result.correct}</span>
              <span className="score-stat-label">정답</span>
            </div>
            <div className="score-stat">
              <span className="score-stat-num wrong">{result.wrong}</span>
              <span className="score-stat-label">오답</span>
            </div>
            <div className="score-stat">
              <span className="score-stat-num total">{result.total}</span>
              <span className="score-stat-label">전체</span>
            </div>
          </div>
        </div>

        {/* 전체 문항 소요시간 표 */}
        <div className="wrong-section">
          <div className="wrong-section-header">
            <h3>문항별 결과</h3>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              {wrongItems.length > 0 && (
                <button className="btn-select-all" onClick={() => toggleAll(wrongItems)}>
                  {allSelected ? '전체 해제' : '전체 선택'}
                </button>
              )}
              {selectedCount > 0 && !saved && (
                <button className="btn-save-notebook" onClick={handleSaveNotebook} disabled={saving}>
                  {saving ? '저장 중...' : `오답노트 저장 (${selectedCount}개)`}
                </button>
              )}
              {saved && <span className="saved-badge">저장 완료!</span>}
            </div>
          </div>
          <ul className="wrong-list">
            {result.results.map((r, i) => {
              const numMatch = r.question.match(/(\d+)번/)
              const qNum = numMatch ? `${numMatch[1]}번` : `${i + 1}번`
              const prob = problems.find(p => p.id === r.problem_id)
              const isExpanded = !!expanded[r.problem_id]
              const secs = timeSpent[r.problem_id] || 0
              const timeStr = secs >= 60
                ? `${Math.floor(secs / 60)}분 ${secs % 60}초`
                : `${secs}초`
              return (
                <li
                  key={r.problem_id}
                  className={`wrong-item ${!r.is_correct && selected[r.problem_id] ? 'selected' : ''} ${isExpanded ? 'expanded' : ''}`}
                  onClick={() => prob?.image_data && !r.is_correct && setExpanded(prev => ({ ...prev, [r.problem_id]: !prev[r.problem_id] }))}
                >
                  <div className="wrong-row">
                    <span className="wrong-num">{qNum}</span>
                    <span className={`result-ox ${r.is_correct ? 'correct' : 'wrong'}`}>
                      {r.is_correct ? '⭕' : '❌'}
                    </span>
                    <span className="result-time">{timeStr}</span>
                    {!r.is_correct && (
                      <input
                        type="checkbox"
                        checked={!!selected[r.problem_id]}
                        onChange={() => setSelected(prev => ({ ...prev, [r.problem_id]: !prev[r.problem_id] }))}
                        onClick={e => e.stopPropagation()}
                      />
                    )}
                  </div>
                  {isExpanded && prob?.image_data && (
                    <div className="wrong-img-expand">
                      <img
                        src={`data:${prob.image_mime};base64,${prob.image_data}`}
                        alt={qNum}
                        className="wrong-img-full"
                      />
                    </div>
                  )}
                </li>
              )
            })}
          </ul>
        </div>

      </div>
    )
  }
}
