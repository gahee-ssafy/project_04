import { useEffect, useState } from 'react'
import { getReport, regenerateReport } from '../api/report'
import MarkdownRenderer from '../components/MarkdownRenderer'
import QuizModal from '../components/QuizModal'

function ConceptBar({ name, count, max }) {
  const pct = max > 0 ? Math.round((count / max) * 100) : 0
  return (
    <div className="report-concept-row">
      <span className="report-concept-name">{name}</span>
      <div className="report-concept-bar-wrap">
        <div className="report-concept-bar" style={{ width: `${pct}%` }} />
      </div>
      <span className="report-concept-count">{count}회</span>
    </div>
  )
}

function Section({ icon, title, children, aside }) {
  return (
    <div className="report-section">
      <div className="report-section-header">
        <span className="report-section-icon">{icon}</span>
        <span className="report-section-title">{title}</span>
        {aside && <span className="report-section-aside">{aside}</span>}
      </div>
      <div className="report-section-body">{children}</div>
    </div>
  )
}

export default function ReportPage() {
  const [report, setReport]           = useState(null)
  const [loading, setLoading]         = useState(true)
  const [aiVisible, setAiVisible]     = useState(false)
  const [aiLoading, setAiLoading]     = useState(false)
  const [error, setError]             = useState(null)
  const [showQuiz, setShowQuiz]       = useState(false)
  useEffect(() => {
    getReport()
      .then(res => {
        setReport(res.data)
        if (res.data?.ai_pattern) setAiVisible(true)  // 캐시 있으면 바로 펼침
      })
      .catch(() => setError('보고서를 불러오지 못했어요.'))
      .finally(() => setLoading(false))
  }, [])

  // AI 분석 요청 or 캐시 보기
  const handleAiRequest = async () => {
    if (aiVisible) { setAiVisible(false); return }

    // 이미 캐시된 데이터 있으면 바로 보여줌
    if (report?.ai_pattern) { setAiVisible(true); return }

    // 없으면 Gemini 호출
    setAiLoading(true)
    try {
      const res = await regenerateReport()
      setReport(res.data)
      setAiVisible(true)
    } catch {
      alert('AI 분석에 실패했어요.')
    } finally {
      setAiLoading(false)
    }
  }

  const handleRegenerate = async () => {
    if (!confirm('AI 분석을 다시 생성할까요?')) return
    setAiLoading(true)
    try {
      const res = await regenerateReport()
      setReport(res.data)
      setAiVisible(true)
    } catch {
      alert('재생성에 실패했어요.')
    } finally {
      setAiLoading(false)
    }
  }

  if (loading) return <p className="loading">학습일지 불러오는 중...</p>
  if (error)   return <p className="loading">{error}</p>
  if (!report?.has_data) return (
    <div className="report-empty">
      <p>📭</p>
      <p>{report?.message}</p>
    </div>
  )

  const { generated_at, ai_generated, ai_is_cached, stats, concepts, quotes, ai_pattern, ai_advice } = report
  const maxCount = concepts?.length > 0 ? concepts[0][1] : 1

  // “…” / “…” 인용 부분을 굵은 기울임꼴로 변환 (따옴표 유지)
  const formatAdvice = (text) =>
    text
      .replace(/“([^”\n]+)”/g, '“***$1***”') // “…” 곡따옴표
      .replace(/”([^”\n]+)”/g, '”***$1***”')                          // “…” 직따옴표

  return (
    <div className="report-page">

      {/* 헤더 */}
      <div className="report-header">
        <h2 className="report-title">📋 학습일지</h2>
        <span className="report-date">{generated_at} 기준</span>
      </div>

      {/* AI 분석 — 핵심 기능, 최상단 */}
      <div className="report-ai-request">
        <button
          className="btn-ai-request"
          onClick={handleAiRequest}
          disabled={aiLoading}
        >
          {aiLoading
            ? '🤖 AI 분석 중...'
            : aiVisible
              ? '▲ AI 분석 접기'
              : ai_pattern
                ? '🤖 AI 분석 보기 ▼'
                : '🤖 AI 분석 받기 ▼'}
        </button>
        {ai_is_cached && ai_generated && !aiLoading && (
          <span className="report-ai-cached-note">{ai_generated} 분석됨</span>
        )}
      </div>

      {aiVisible && (
        <div className="report-ai-panel">
          {ai_pattern && (
            <div className="report-ai-block-pattern">
              <span className="report-ai-label">📊 학습 패턴</span>
              <MarkdownRenderer>{formatAdvice(ai_pattern)}</MarkdownRenderer>
            </div>
          )}
          {ai_advice && (
            <div className="report-ai-block-advice">
              <span className="report-ai-label">💡 추천 학습 방향</span>
              <MarkdownRenderer>{formatAdvice(ai_advice)}</MarkdownRenderer>
            </div>
          )}
          <div className="report-ai-footer">
            <button
              className="btn-report-regenerate"
              onClick={handleRegenerate}
              disabled={aiLoading}
            >
              {aiLoading ? '분석 중...' : '↺ 다시 분석하기'}
            </button>
          </div>
        </div>
      )}

      {/* 숫자 칩 */}
      <div className="report-chips">
        <div className="report-chip">
          <span className="chip-num">{stats.total}</span>
          <span className="chip-label">오답 문제</span>
        </div>
        <div className="report-chip">
          <span className="chip-num">{stats.memo_count}</span>
          <span className="chip-label">메모 작성</span>
        </div>
        <div className="report-chip">
          <span className="chip-num">{stats.chat_sessions}</span>
          <span className="chip-label">AI 토론</span>
        </div>
        <div className="report-chip">
          <span className="chip-num">{stats.active_days}</span>
          <span className="chip-label">학습한 날</span>
        </div>
      </div>

      {/* 자주 다룬 개념 */}
      {concepts?.length > 0 && (
        <Section icon="🏷️" title="자주 다룬 개념">
          <div className="report-concepts">
            {concepts.map(([name, count]) => (
              <ConceptBar key={name} name={name} count={count} max={maxCount} />
            ))}
          </div>
          <p className="report-concepts-note">메모와 AI 토론에서 등장한 개념을 분석했어요.</p>
        </Section>
      )}

      {/* 복습 퀴즈 버튼 */}
      <button className="btn-quiz-start" onClick={() => setShowQuiz(true)}>
        📝 오늘의 복습 퀴즈
      </button>

      {showQuiz && <QuizModal onClose={() => setShowQuiz(false)} />}
    </div>
  )
}
