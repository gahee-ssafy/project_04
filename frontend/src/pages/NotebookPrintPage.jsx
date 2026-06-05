import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getNotebook } from '../api/notebook'

function extractAnswer(solution) {
  if (!solution) return null
  const m = solution.match(/\[정답\]\s*\n([①②③④⑤\w]+)/)
  return m ? m[1].trim() : null
}

function examGroup(q) {
  const m = q.match(/(\d{4})년\s*(\d+)회차/)
  return m ? `${m[1]}년 ${m[2]}회차` : '직접 추가'
}

function displayQ(q) {
  return q.replace(/^\[(오답노트|모의고사)\]\s*/, '')
}

function problemNum(q) {
  const m = q.match(/(\d+)번/)
  return m ? `${m[1]}번` : null
}

function getNcsAgency(q) {
  const m = q.match(/\[모의고사\]\s+(.+?)\s+\d{4}년/)
  return m ? m[1].trim() : null
}

export default function NotebookPrintPage() {
  const { group, subject, agency } = useParams()
  const navigate = useNavigate()
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)

  const isCivilAll = !!subject
  const isNcsAgency = !!agency
  const agencyName = agency ? decodeURIComponent(agency) : null
  const groupName = isCivilAll
    ? decodeURIComponent(subject)
    : isNcsAgency ? agencyName
    : decodeURIComponent(group)

  useEffect(() => {
    getNotebook()
      .then(res => {
        const all = res.data
        const filtered = isCivilAll
          ? all.filter(i => /\d{4}년\s*\d+회차/.test(i.question))
          : isNcsAgency
          ? all.filter(i => getNcsAgency(i.question) === agencyName)
          : all.filter(i => examGroup(i.question) === groupName)
        setItems(filtered)
      })
      .finally(() => setLoading(false))
  }, [groupName])

  if (loading) return <div className="loading">불러오는 중...</div>

  return (
    <div className="print-page">
      {/* 화면용 헤더 (인쇄 시 숨김) */}
      <div className="print-header-bar no-print">
        <button onClick={() => navigate(-1)} className="print-back-btn">← 돌아가기</button>
        <h2>{isCivilAll ? '경제학 전체' : isNcsAgency ? `${agencyName} 전체` : groupName} 쪽집게 노트</h2>
        <button onClick={() => window.print()} className="print-trigger-btn">🖨️ PDF 저장</button>
      </div>

      {/* 인쇄 영역 */}
      <div className="print-content">
        <div className="print-title">
          <h1>{isCivilAll ? '공무원 기출 경제학 전체' : isNcsAgency ? `NCS ${agencyName} 전체` : groupName}</h1>
          <p className="print-subtitle">오답 쪽집게 노트 · {items.length}문제</p>
        </div>

        <div className="print-items">
          {items.map((item, idx) => {
            const answer = extractAnswer(item.answer)
            const num = problemNum(item.question)
            return (
              <div key={item.id} className="print-item">
                <div className="print-item-header">
                  <span className="print-item-num">{num || `${idx + 1}번`}</span>
                </div>

                {item.image_data && (
                  <img
                    src={`data:${item.image_mime};base64,${item.image_data}`}
                    alt={num || '문제'}
                    className="print-item-img"
                  />
                )}

                {!item.image_data && (
                  <p className="print-item-question">
                    {item.problem_question || displayQ(item.question)}
                  </p>
                )}

                {item.memo ? (
                  <div className="print-item-memo">
                    <span className="print-memo-label">메모</span>
                    <p className="print-memo-text">{item.memo}</p>
                  </div>
                ) : (
                  <div className="print-item-memo empty">
                    <p className="print-memo-empty">메모 없음</p>
                  </div>
                )}

                {(answer || item.problem_correct_answer) && (
                  <div className="print-item-answer-row">
                    <span className="print-item-answer">정답 {item.problem_correct_answer || answer}</span>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
