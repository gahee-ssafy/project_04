import { useEffect, useState } from 'react'
import { getReport } from '../api/report'
import MarkdownRenderer from '../components/MarkdownRenderer'

// 개념 빈도 바 (최대값 기준 상대 너비)
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

// 섹션 카드
function Section({ icon, title, children }) {
  return (
    <div className="report-section">
      <div className="report-section-header">
        <span className="report-section-icon">{icon}</span>
        <span className="report-section-title">{title}</span>
      </div>
      <div className="report-section-body">
        {children}
      </div>
    </div>
  )
}

export default function ReportPage() {
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]   = useState(null)

  const load = () => {
    setLoading(true)
    setError(null)
    getReport()
      .then(res => setReport(res.data))
      .catch(() => setError('보고서를 불러오지 못했어요.'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  if (loading) return <p className="loading">학습일지 생성 중...</p>
  if (error)   return <p className="loading">{error}</p>
  if (!report?.has_data) {
    return (
      <div className="report-empty">
        <p>📭</p>
        <p>{report?.message}</p>
      </div>
    )
  }

  const { generated_at, stats, overview, concepts, quotes, advice } = report
  const maxConceptCount = concepts.length > 0 ? concepts[0][1] : 1

  return (
    <div className="report-page">
      {/* 헤더 */}
      <div className="report-header">
        <h2 className="report-title">📋 학습일지</h2>
        <span className="report-date">{generated_at} 기준</span>
        <button className="btn-report-refresh" onClick={load} title="새로고침">↺</button>
      </div>

      {/* 숫자 요약 칩 */}
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

      {/* 전체 현황 */}
      <Section icon="📊" title="전체 현황">
        <MarkdownRenderer>{overview}</MarkdownRenderer>
      </Section>

      {/* 자주 다룬 개념 */}
      {concepts.length > 0 && (
        <Section icon="🏷️" title="자주 다룬 개념">
          <div className="report-concepts">
            {concepts.map(([name, count]) => (
              <ConceptBar key={name} name={name} count={count} max={maxConceptCount} />
            ))}
          </div>
          <p className="report-concepts-note">메모와 AI 토론에서 등장한 경제학 개념을 분석했어요.</p>
        </Section>
      )}

      {/* 직접 했던 질문들 */}
      {quotes.length > 0 && (
        <Section icon="💬" title="직접 했던 질문들">
          <ul className="report-quotes">
            {quotes.map((q, i) => (
              <li key={i} className="report-quote-item">
                <span className="report-quote-mark">"</span>
                {q}
                <span className="report-quote-mark">"</span>
              </li>
            ))}
          </ul>
          <p className="report-concepts-note">AI 토론에서 직접 작성한 질문이에요.</p>
        </Section>
      )}

      {/* 학습 조언 */}
      <Section icon="💡" title="학습 조언">
        <MarkdownRenderer>{advice}</MarkdownRenderer>
      </Section>
    </div>
  )
}
