import { useEffect, useState } from 'react'
import { getQuiz, getRelatedProblem } from '../api/quiz'
import MarkdownRenderer from './MarkdownRenderer'
import SolutionRenderer from './SolutionRenderer'

export default function QuizModal({ onClose }) {
  const [questions, setQuestions]   = useState([])
  const [idx, setIdx]               = useState(0)
  const [loading, setLoading]       = useState(true)
  const [answered, setAnswered]     = useState(null)   // null | 'correct' | 'wrong'
  const [related, setRelated]       = useState(null)   // 관련 기출문제
  const [relatedLoading, setRelatedLoading] = useState(false)
  const [showRelated, setShowRelated] = useState(false)
  const [score, setScore]           = useState(0)
  const [done, setDone]             = useState(false)

  useEffect(() => {
    getQuiz()
      .then(res => setQuestions(res.data))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return (
    <div className="quiz-overlay" onClick={onClose}>
      <div className="quiz-modal" onClick={e => e.stopPropagation()}>
        <p className="loading">퀴즈 준비 중...</p>
      </div>
    </div>
  )

  if (questions.length === 0) return (
    <div className="quiz-overlay" onClick={onClose}>
      <div className="quiz-modal" onClick={e => e.stopPropagation()}>
        <p className="quiz-empty">풀이가 있는 오답노트가 없어요. AI 풀이를 먼저 받아보세요!</p>
        <button className="btn-quiz-close" onClick={onClose}>닫기</button>
      </div>
    </div>
  )

  const q = questions[idx]
  const total = questions.length

  const handleAnswer = async (userSaysO) => {
    if (answered) return
    const isCorrect = (userSaysO === q.is_correct)
    setAnswered(isCorrect ? 'correct' : 'wrong')
    if (isCorrect) setScore(s => s + 1)

    if (!isCorrect) {
      setRelatedLoading(true)
      try {
        const res = await getRelatedProblem(q.text)
        if (res.data && res.data.id) setRelated(res.data)
      } finally {
        setRelatedLoading(false)
      }
    }
  }

  const handleNext = () => {
    if (idx + 1 >= total) {
      setDone(true)
    } else {
      setIdx(i => i + 1)
      setAnswered(null)
      setRelated(null)
      setShowRelated(false)
    }
  }

  // ── 완료 화면 ────────────────────────────────────────────────
  if (done) return (
    <div className="quiz-overlay" onClick={onClose}>
      <div className="quiz-modal" onClick={e => e.stopPropagation()}>
        <div className="quiz-done">
          <p className="quiz-done-emoji">
            {score / total >= 0.8 ? '🎉' : score / total >= 0.5 ? '👍' : '💪'}
          </p>
          <p className="quiz-done-score">{score} / {total}</p>
          <p className="quiz-done-msg">
            {score === total
              ? '완벽해요! 모두 맞혔어요.'
              : score / total >= 0.8
                ? '거의 다 맞혔어요. 훌륭해요!'
                : score / total >= 0.5
                  ? '절반 이상 맞혔어요. 조금만 더 복습해봐요!'
                  : '틀린 문제가 많아요. 오답노트를 다시 살펴봐요!'}
          </p>
          <button className="btn-quiz-close" onClick={onClose}>닫기</button>
        </div>
      </div>
    </div>
  )

  // ── 퀴즈 화면 ────────────────────────────────────────────────
  return (
    <div className="quiz-overlay" onClick={onClose}>
      <div className="quiz-modal" onClick={e => e.stopPropagation()}>
        {/* 헤더 */}
        <div className="quiz-header">
          <span className="quiz-progress">{idx + 1} / {total}</span>
          <div className="quiz-progress-bar">
            <div className="quiz-progress-fill" style={{ width: `${((idx + 1) / total) * 100}%` }} />
          </div>
          <button className="btn-quiz-x" onClick={onClose}>✕</button>
        </div>

        {/* 출처 */}
        <p className="quiz-source">{q.source_label}</p>

        {/* 문제 */}
        <div className="quiz-question">
          <span className="quiz-marker">{q.marker}</span>
          <MarkdownRenderer>{q.text}</MarkdownRenderer>
        </div>

        <p className="quiz-instruction">위 설명이 맞나요?</p>

        {/* 버튼 */}
        {!answered ? (
          <div className="quiz-btns-wrap">
            <div className="quiz-btns">
              <button className="btn-quiz-o" onClick={() => handleAnswer(true)}>⭕</button>
              <button className="btn-quiz-x2" onClick={() => handleAnswer(false)}>❌</button>
            </div>
            <button className="btn-quiz-skip" onClick={handleNext}>건너뛰기</button>
          </div>
        ) : (
          <div className="quiz-result">
            <div className={`quiz-result-badge ${answered}`}>
              {answered === 'correct' ? '✅ 정답!' : `❌ 오답 — 정답은 ${q.is_correct ? '⭕' : '❌'}`}
            </div>

            {/* 관련 기출문제 */}
            {answered === 'wrong' && (
              <div className="quiz-related-section">
                {relatedLoading && <p className="quiz-related-loading">관련 문제 찾는 중...</p>}
                {related && !showRelated && (
                  <button
                    className="btn-quiz-related"
                    onClick={() => setShowRelated(true)}
                  >
                    📚 관련 기출문제 풀어보기
                  </button>
                )}
                {related && showRelated && (
                  <div className="quiz-related-problem">
                    <p className="quiz-related-label">
                      관련 기출 {related.exam_year && `${related.exam_year}년`}
                    </p>
                    {related.image_data
                      ? <img
                          src={`data:${related.image_mime};base64,${related.image_data}`}
                          alt="관련 기출문제"
                          className="quiz-related-img"
                        />
                      : <p className="quiz-related-text">{related.question}</p>
                    }
                    {related.solution && (
                      <details className="quiz-related-solution">
                        <summary>풀이 보기</summary>
                        <SolutionRenderer>{related.solution}</SolutionRenderer>
                      </details>
                    )}
                  </div>
                )}
              </div>
            )}

            <button className="btn-quiz-next" onClick={handleNext}>
              {idx + 1 >= total ? '결과 보기' : '다음 →'}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
