import { useEffect, useState, useRef } from 'react'
import { getNotebook, saveMemo, deleteNotebook, notebookChat, getNotebookChatHistory } from '../api/notebook'
import MarkdownRenderer from '../components/MarkdownRenderer'
import SolutionRenderer from '../components/SolutionRenderer'

export default function NotebookPage() {
  const [items, setItems]         = useState([])
  const [loading, setLoading]     = useState(true)
  const [page, setPage]           = useState(0)
  const [pageInput, setPageInput] = useState('')
  const [editingPage, setEditingPage] = useState(false)
  const [editMode, setEditMode]   = useState(false)
  const [selectedIds, setSelectedIds] = useState(new Set())
  const [deleting, setDeleting]   = useState(false)
  const [sortNewest, setSortNewest] = useState(true)
  const [memoFilter, setMemoFilter] = useState('all') // 'all' | 'has' | 'none'
  const [selectedGroup, setSelectedGroup] = useState(null) // null = 회차 목록

  const setFilter = (f) => { setMemoFilter(f); setPage(0) }
  const selectGroup = (g) => { setSelectedGroup(g); setPage(0) }

  useEffect(() => {
    getNotebook()
      .then((res) => setItems(res.data))
      .finally(() => setLoading(false))
  }, [])

  const handleSaveMemo = async (sessionId, memo) => {
    await saveMemo(sessionId, memo)
    setItems((prev) => prev.map((i) => (i.id === sessionId ? { ...i, memo } : i)))
  }

  const handleDelete = async (sessionId) => {
    if (!confirm('정말 삭제할까요?')) return
    await deleteNotebook(sessionId)
    setItems((prev) => {
      const next = prev.filter((i) => i.id !== sessionId)
      setPage((p) => Math.min(p, Math.max(0, next.length - 1)))
      return next
    })
  }

  const toggleSelect = (id) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  const toggleSelectAll = () => {
    if (selectedIds.size === items.length) setSelectedIds(new Set())
    else setSelectedIds(new Set(items.map((i) => i.id)))
  }

  const handleDeleteSelected = async () => {
    if (selectedIds.size === 0) return
    if (!confirm(`${selectedIds.size}개를 삭제할까요?`)) return
    setDeleting(true)
    try {
      await Promise.all([...selectedIds].map((id) => deleteNotebook(id)))
      setItems((prev) => prev.filter((i) => !selectedIds.has(i.id)))
      setSelectedIds(new Set())
      setEditMode(false)
      setPage(0)
    } finally {
      setDeleting(false)
    }
  }

  const displayQ = (q) => q.replace(/^\[(오답노트|모의고사)\]\s*/, '')
  const examTag  = (q) => {
    const m = q.match(/(\d{4})년\s*(\d+)회차/)
    return m ? `${m[1]}년` : null
  }
  const examGroup = (q) => {
    const m = q.match(/(\d{4})년\s*(\d+)회차/)
    return m ? `${m[1]}년 ${m[2]}회차` : '직접 추가'
  }
  const problemNum = (q) => {
    const m = q.match(/(\d+)번/)
    return m ? `${m[1]}번` : null
  }

  // 편집 모드용 그룹핑
  const groupedItems = () => {
    const filtered = memoFilter === 'has'  ? items.filter(i => i.memo?.trim())
                   : memoFilter === 'none' ? items.filter(i => !i.memo?.trim())
                   : items
    const sorted = [...filtered].sort((a, b) => sortNewest
      ? new Date(b.created_at) - new Date(a.created_at)
      : new Date(a.created_at) - new Date(b.created_at)
    )
    const groups = {}
    sorted.forEach(it => {
      const key = examGroup(it.question)
      if (!groups[key]) groups[key] = []
      groups[key].push(it)
    })
    return Object.entries(groups)
  }

  if (loading) return <p className="loading">불러오는 중...</p>

  // 일반 보기용 그룹 (등록순 고정)
  const viewGroups = () => {
    const groups = {}
    items.forEach(it => {
      const key = examGroup(it.question)
      if (!groups[key]) groups[key] = []
      groups[key].push(it)
    })
    return groups
  }

  const groups = viewGroups()
  const groupNames = Object.keys(groups)
  const currentGroupItems = selectedGroup ? (groups[selectedGroup] || []) : []
  const total = selectedGroup ? currentGroupItems.length : items.length
  const item  = selectedGroup ? currentGroupItems[page] : null

  return (
    <div className="notebook-page">
      {/* 헤더 */}
      <div className="notebook-header">
        <h2>오답노트 <span className="notebook-count">{total}개</span></h2>
        {total > 0 && (
          editMode ? (
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <button className="btn-select-all" onClick={toggleSelectAll}>
                {selectedIds.size === total ? '전체 해제' : '전체 선택'}
              </button>
              <button className="btn-edit-done" onClick={() => { setEditMode(false); setSelectedIds(new Set()) }}>완료</button>
            </div>
          ) : (
            <button className="btn-edit-mode" onClick={() => setEditMode(true)}>편집</button>
          )
        )}
      </div>

      {total === 0 ? (
        <p className="empty">아직 등록된 문제가 없어요.</p>

      ) : editMode ? (
        /* ── 편집 모드: 목록 ── */
        <>
          {/* 정렬 + 필터 */}
          <div className="notebook-edit-sort">
            <button className={`btn-sort ${sortNewest ? 'active' : ''}`} onClick={() => setSortNewest(true)}>최신순</button>
            <button className={`btn-sort ${!sortNewest ? 'active' : ''}`} onClick={() => setSortNewest(false)}>등록순</button>
            <div style={{ flex: 1 }} />
            <button className={`btn-sort ${memoFilter === 'all'  ? 'active' : ''}`} onClick={() => setFilter('all')}>전체</button>
            <button className={`btn-sort ${memoFilter === 'none' ? 'active' : ''}`} onClick={() => setFilter('none')}>메모 없음</button>
            <button className={`btn-sort ${memoFilter === 'has'  ? 'active' : ''}`} onClick={() => setFilter('has')}>메모 있음</button>
          </div>

          <div className="notebook-edit-list">
            {groupedItems().map(([groupName, groupList]) => {
              const allGroupSelected = groupList.every(it => selectedIds.has(it.id))
              const toggleGroup = () => {
                setSelectedIds(prev => {
                  const next = new Set(prev)
                  groupList.forEach(it => allGroupSelected ? next.delete(it.id) : next.add(it.id))
                  return next
                })
              }
              return (
                <div key={groupName} className="notebook-edit-group">
                  <div className="notebook-edit-group-header" onClick={toggleGroup}>
                    <span className="notebook-edit-group-name">{groupName}</span>
                    <span className="notebook-edit-group-count">{groupList.length}개</span>
                    <span className="notebook-edit-group-toggle">
                      {allGroupSelected ? '전체 해제' : '전체 선택'}
                    </span>
                  </div>
                  {groupList.map((it) => (
                    <div
                      key={it.id}
                      className={`notebook-edit-item ${selectedIds.has(it.id) ? 'selected' : ''}`}
                      onClick={() => toggleSelect(it.id)}
                    >
                      <div className={`note-check-circle ${selectedIds.has(it.id) ? 'checked' : ''}`}>
                        {selectedIds.has(it.id) && <span>✓</span>}
                      </div>
                      <div className="notebook-edit-info">
                        <span className="notebook-edit-num">{problemNum(it.question) || '—'}</span>
                        {it.image_data
                          ? <img src={`data:${it.image_mime};base64,${it.image_data}`} alt="" className="notebook-edit-thumb" />
                          : <span className="notebook-edit-q">{displayQ(it.question).slice(0, 40)}…</span>
                        }
                      </div>
                    </div>
                  ))}
                </div>
              )
            })}
          </div>
          <div className="notebook-edit-bar">
            <span className="edit-bar-count">
              {selectedIds.size > 0 ? `${selectedIds.size}개 선택됨` : '항목을 선택하세요'}
            </span>
            <button
              className="btn-delete-selected"
              onClick={handleDeleteSelected}
              disabled={selectedIds.size === 0 || deleting}
            >
              {deleting ? '삭제 중...' : '삭제'}
            </button>
          </div>
        </>

      ) : !selectedGroup ? (
        /* ── 회차 목록 ── */
        <div className="notebook-group-list">
          {groupNames.length === 0
            ? <p className="empty">아직 등록된 문제가 없어요.</p>
            : groupNames.map(name => {
                const list = groups[name]
                const memoCount = list.filter(i => i.memo?.trim()).length
                return (
                  <div key={name} className="notebook-group-card" onClick={() => selectGroup(name)}>
                    <div className="notebook-group-card-title">{name}</div>
                    <div className="notebook-group-card-meta">
                      <span>{list.length}문제</span>
                      <span className="notebook-group-memo-bar">
                        <span
                          className="notebook-group-memo-fill"
                          style={{ width: `${Math.round(memoCount / list.length * 100)}%` }}
                        />
                      </span>
                      <span>메모 {memoCount}/{list.length}</span>
                    </div>
                  </div>
                )
              })
          }
        </div>

      ) : (
        /* ── 일반 모드: 한 문제씩 ── */
        <>
          {/* 뒤로가기 */}
          <button className="btn-nb-back" onClick={() => selectGroup(null)}>
            ← {selectedGroup}
          </button>

          {/* 페이지 네비게이션 */}
          <div className="notebook-nav">
            <button
              className="btn-nb-prev"
              onClick={() => setPage((p) => p - 1)}
              disabled={page === 0}
            >← 이전</button>

            {editingPage ? (
              <input
                className="notebook-pager-input"
                type="number"
                min={1}
                max={total}
                value={pageInput}
                autoFocus
                onChange={e => setPageInput(e.target.value)}
                onKeyDown={e => {
                  if (e.key === 'Enter') {
                    const n = parseInt(pageInput)
                    if (n >= 1 && n <= total) setPage(n - 1)
                    setEditingPage(false)
                    setPageInput('')
                  } else if (e.key === 'Escape') {
                    setEditingPage(false)
                    setPageInput('')
                  }
                }}
                onBlur={() => { setEditingPage(false); setPageInput('') }}
              />
            ) : (
              <span
                className="notebook-pager"
                onClick={() => { setEditingPage(true); setPageInput(String(page + 1)) }}
                title="클릭해서 페이지 이동"
              >
                {page + 1} / {total}
              </span>
            )}

            <button
              className="btn-nb-next"
              onClick={() => setPage((p) => p + 1)}
              disabled={page === total - 1}
            >다음 →</button>
          </div>

          <NoteCard
            key={item.id}
            item={item}
            displayQ={displayQ}
            examTag={examTag(item.question)}
            onSaveMemo={handleSaveMemo}
            onDelete={handleDelete}
          />
        </>
      )}
    </div>
  )
}

function NoteCard({ item, displayQ, examTag, onSaveMemo, onDelete }) {
  const [memo, setMemo]           = useState(item.memo || '')
  const [editing, setEditing]     = useState(false)
  const [showSolution, setShowSolution] = useState(false)
  const [showChat, setShowChat]   = useState(false)
  const [chatHistory, setChatHistory] = useState([])
  const [chatInput, setChatInput] = useState('')
  const [chatLoading, setChatLoading] = useState(false)
  const chatBottomRef = useRef(null)
  const hasMemo = !!item.memo

  // 문제가 바뀌면 채팅 초기화
  useEffect(() => {
    setShowChat(false)
    setChatHistory([])
    setChatInput('')
    setShowSolution(false)
  }, [item.id])

  const handleSave = async () => {
    await onSaveMemo(item.id, memo)
    setEditing(false)
  }

  const openChat = async () => {
    setShowChat(true)
    if (chatHistory.length === 0) {
      setChatLoading(true)
      try {
        const saved = await getNotebookChatHistory(item.id)
        if (saved.data.history.length > 0) {
          setChatHistory(saved.data.history)
        } else {
          const res = await notebookChat(item.id, displayQ(item.question), item.memo || '', item.answer || '')
          setChatHistory(res.data.history)
        }
      } finally {
        setChatLoading(false)
      }
    }
  }

  const sendMessage = async () => {
    const msg = chatInput.trim()
    if (!msg || chatLoading) return
    setChatHistory(prev => [...prev, { role: 'user', content: msg }])
    setChatInput('')
    setChatLoading(true)
    try {
      const res = await notebookChat(item.id, displayQ(item.question), item.memo || '', item.answer || '', msg)
      setChatHistory(res.data.history)
    } finally {
      setChatLoading(false)
    }
  }

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatHistory, chatLoading])

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
      {item.answer && (
        <div className="note-solution-toggle">
          <button className="btn-toggle-solution" onClick={() => setShowSolution(v => !v)}>
            {showSolution ? 'AI 풀이 접기 ▲' : 'AI 풀이 보기 ▼'}
          </button>
          {showSolution && (
            <div className="solution-body">
              <SolutionRenderer
                onAddToMemo={(text) => {
                  const next = memo ? memo + '\n' + text : text
                  setMemo(next)
                  onSaveMemo(item.id, next)
                }}
              >{item.answer}</SolutionRenderer>
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
        {!editing && (
          <button className="btn-memo-edit" onClick={() => setEditing(true)}>수정</button>
        )}
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
        memo
          ? <MarkdownRenderer className="memo-content">{memo}</MarkdownRenderer>
          : <p className="memo-content empty-memo">(메모 없음)</p>
      )}
    </div>
  )

  return (
    <div className={`note-card ${hasMemo ? 'note-card--split' : ''}`}>
      {/* 메타 */}
      <div className="note-card-meta">
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span className="note-date">{item.created_at?.slice(0, 16)}</span>
          {examTag && <span className="note-exam-tag">{examTag}</span>}
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          {!hasMemo && !editing && (
            <button className="btn-memo-add" onClick={() => setEditing(true)}>+ 메모 추가</button>
          )}
          <button className="btn-delete-sm" onClick={() => onDelete(item.id)}>삭제</button>
        </div>
      </div>

      {/* 본문 */}
      {hasMemo ? (
        showSolution ? (
          // 풀이 열리면 단열로 전환
          <div className="note-single-layout">
            {QuestionPanel}
            {MemoPanel}
          </div>
        ) : (
          <div className="note-split-layout">
            {QuestionPanel}
            {MemoPanel}
          </div>
        )
      ) : (
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

      {/* AI 토론 */}
      <div className="note-chat-section">
        <button
          className="btn-chat-toggle"
          onClick={() => showChat ? setShowChat(false) : openChat()}
        >
          {showChat ? 'AI 토론 닫기 ▲' : '🤖 AI와 토론하기 ▼'}
        </button>
        {showChat && (
          <div className="note-chat-panel">
            <div className="chat-messages">
              {chatHistory.map((msg, i) => {
                const memoMatch = msg.role === 'assistant' && msg.content.match(/📝 메모 제안[:：]\s*(.+)/s)
                const memoSuggestion = memoMatch ? memoMatch[1].trim().split('\n')[0].trim() : null
                return (
                  <div key={i} className={`chat-bubble ${msg.role}`}>
                    <MarkdownRenderer>{msg.content}</MarkdownRenderer>
                    {memoSuggestion && (
                      <button
                        className="btn-save-memo-suggestion"
                        onClick={async () => {
                          await onSaveMemo(item.id, memoSuggestion)
                          setMemo(memoSuggestion)
                        }}
                      >
                        📋 메모에 바로 저장
                      </button>
                    )}
                  </div>
                )
              })}
              {chatLoading && (
                <div className="chat-bubble assistant chat-loading">
                  <span>●</span><span>●</span><span>●</span>
                </div>
              )}
              <div ref={chatBottomRef} />
            </div>
            <div className="chat-input-row">
              <textarea
                className="chat-input"
                value={chatInput}
                onChange={e => setChatInput(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage() } }}
                placeholder="이해한 내용을 설명해보세요..."
                rows={2}
              />
              <button className="btn-chat-send" onClick={sendMessage} disabled={chatLoading || !chatInput.trim()}>
                전송
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
