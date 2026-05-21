import { useEffect, useState } from 'react'
import { getNotebook, saveMemo, deleteNotebook } from '../api/notebook'
import MarkdownRenderer from '../components/MarkdownRenderer'

export default function NotebookPage() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getNotebook()
      .then((res) => setItems(res.data))
      .finally(() => setLoading(false))
  }, [])

  const handleSaveMemo = async (sessionId, memo) => {
    await saveMemo(sessionId, memo)
    setItems((prev) =>
      prev.map((i) => (i.id === sessionId ? { ...i, memo } : i))
    )
  }

  const handleDelete = async (sessionId) => {
    if (!confirm('정말 삭제할까요?')) return
    await deleteNotebook(sessionId)
    setItems((prev) => prev.filter((i) => i.id !== sessionId))
  }

  const displayQ = (q) => q.replace(/^\[(오답노트|모의고사)\]\s*/, '')

  const examTag = (q) => {
    const m = q.match(/(\d{4})년\s*(\d+)회차/)
    return m ? `${m[1]}년` : null
  }

  if (loading) return <p className="loading">불러오는 중...</p>

  return (
    <div className="notebook-page">
      <h2>오답노트</h2>
      {items.length === 0 ? (
        <p className="empty">아직 등록된 문제가 없어요.</p>
      ) : (
        items.map((item) => (
          <NoteCard
            key={item.id}
            item={item}
            displayQ={displayQ}
            examTag={examTag(item.question)}
            onSaveMemo={handleSaveMemo}
            onDelete={handleDelete}
          />
        ))
      )}
    </div>
  )
}

function NoteCard({ item, displayQ, examTag, onSaveMemo, onDelete }) {
  const [memo, setMemo]       = useState(item.memo || '')
  const [editing, setEditing] = useState(false)
  const [showSolution, setShowSolution] = useState(false)
  const isDirect = true // 모든 항목 삭제 가능
  const hasMemo  = !!item.memo

  const handleSave = async () => {
    await onSaveMemo(item.id, memo)
    setEditing(false)
  }

  // ── 왼쪽: 문제 영역 ─────────────────────────────────
  const QuestionPanel = (
    <div className="note-question-panel">
      {item.image_data ? (
        <img
          src={`data:${item.image_mime};base64,${item.image_data}`}
          alt="문제 이미지"
          className="note-img"
        />
      ) : (
        <p className="note-question">{displayQ(item.question)}</p>
      )}

      {/* AI 풀이 토글 */}
      {item.answer && (
        <div className="note-solution-toggle">
          <button
            className="btn-toggle-solution"
            onClick={() => setShowSolution((v) => !v)}
          >
            {showSolution ? 'AI 풀이 접기 ▲' : 'AI 풀이 보기 ▼'}
          </button>
          {showSolution && (
            <div className="solution-body">
              <MarkdownRenderer>{item.answer}</MarkdownRenderer>
            </div>
          )}
        </div>
      )}
    </div>
  )

  // ── 오른쪽: 메모 영역 ───────────────────────────────
  const MemoPanel = (
    <div className="note-memo-panel">
      <div className="memo-panel-header">
        <span className="memo-panel-title">메모</span>
        <div style={{ display: 'flex', gap: 6 }}>
          {!editing && (
            <button className="btn-memo-edit" onClick={() => setEditing(true)}>
              수정
            </button>
          )}
        </div>
      </div>

      {editing ? (
        <>
          <textarea
            className="memo-textarea"
            value={memo}
            onChange={(e) => setMemo(e.target.value)}
            placeholder="핵심 개념, 오답 이유를 적어보세요."
            autoFocus
          />
          <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
            <button className="btn-save" onClick={handleSave}>저장</button>
            <button className="btn-cancel" onClick={() => { setMemo(item.memo || ''); setEditing(false) }}>취소</button>
          </div>
        </>
      ) : (
        <p className="memo-content">{memo || '(메모 없음)'}</p>
      )}
    </div>
  )

  // ── 레이아웃 결정 ────────────────────────────────────
  return (
    <div className={`note-card ${hasMemo ? 'note-card--split' : ''}`}>
      <div className="note-card-meta">
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span className="note-date">{item.created_at?.slice(0, 16)}</span>
          {examTag && <span className="note-exam-tag">{examTag}</span>}
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          {!hasMemo && !editing && (
            <button className="btn-memo-add" onClick={() => setEditing(true)}>
              + 메모 추가
            </button>
          )}
          <button className="btn-delete-sm" onClick={() => onDelete(item.id)}>
            삭제
          </button>
        </div>
      </div>

      {hasMemo ? (
        // 2열: 왼쪽 문제 / 오른쪽 메모
        <div className="note-split-layout">
          {QuestionPanel}
          {MemoPanel}
        </div>
      ) : (
        // 단열: 문제만
        <div className="note-single-layout">
          {QuestionPanel}
          {editing && (
            <div className="note-memo-panel note-memo-inline">
              <textarea
                className="memo-textarea"
                value={memo}
                onChange={(e) => setMemo(e.target.value)}
                placeholder="핵심 개념, 오답 이유를 적어보세요."
                autoFocus
              />
              <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                <button className="btn-save" onClick={handleSave}>저장</button>
                <button className="btn-cancel" onClick={() => setEditing(false)}>취소</button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
