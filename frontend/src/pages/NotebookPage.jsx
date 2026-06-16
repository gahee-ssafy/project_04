import { useEffect, useState, useRef } from 'react'
import { useNavigate as useNav } from 'react-router-dom'
import { getNotebook, saveMemo, deleteNotebook, notebookChat, getNotebookChatHistory } from '../api/notebook'
import { dispatchCreditsUpdate } from '../api/auth'
import MarkdownRenderer from '../components/MarkdownRenderer'
import SolutionRenderer from '../components/SolutionRenderer'
import DrawingCanvas from '../components/DrawingCanvas'

export default function NotebookPage() {
  const navigate = useNav()
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
  const [selectedGroup, setSelectedGroup] = useState(null)

  // 네비게이션 레벨
  const [nbTab, setNbTab]         = useState(null)  // null | 'civil' | 'ncs'
  const [selSubject, setSelSubject] = useState(null) // 공무원: 과목
  const [selAgency, setSelAgency]  = useState(null)  // NCS: 대행사

  const setFilter = (f) => { setMemoFilter(f); setPage(0) }
  const selectGroup = (g) => { setSelectedGroup(g); setPage(0) }
  const resetNav = () => { setNbTab(null); setSelSubject(null); setSelAgency(null); selectGroup(null) }

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

  const displayQ  = (q) => q.replace(/^\[(오답노트|모의고사)\]\s*/, '')
  const isCivil   = (q) => /\d{4}년\s*\d+회차/.test(q)
  const isNcs     = (q) => /\[모의고사\]\s+.+\s+\d{4}년\s+/.test(q) && !isCivil(q)
  const getNcsAgency = (q) => { const m = q.match(/\[모의고사\]\s+(.+?)\s+\d{4}년/); return m ? m[1].trim() : '기타' }
  const getNcsDomain = (q) => { const m = q.match(/\d{4}년\s+(.+)$/); return m ? m[1].trim() : '기타' }
  const examTag  = (q) => {
    const m = q.match(/(\d{4})년\s*(\d+)회차/)
    return m ? `${m[1]}년` : null
  }
  const examGroup = (q) => {
    // 공무원: "2025년 1회차"
    const civil = q.match(/(\d{4})년\s*(\d+)회차/)
    if (civil) return `${civil[1]}년 ${civil[2]}회차`
    // NCS: "사람인HR 2024년 의사소통능력"
    const ncs = q.match(/([^\]]+)\s+(\d{4})년\s+(.+)/)
    if (ncs) return `${ncs[1].trim()} ${ncs[2]}년 ${ncs[3].trim()}`
    return '직접 추가'
  }
  const problemNum = (q) => {
    const m = q.match(/(\d+)번/)
    if (m) return `${m[1]}번`
    // NCS: 분야명을 번호 대신 표시
    const ncs = q.match(/\d{4}년\s+(.+)$/)
    if (ncs) return ncs[1].trim().slice(0, 6)
    return null
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

  // 카테고리별 분류
  const civilItems = items.filter(i => isCivil(i.question))
  const ncsItems   = items.filter(i => isNcs(i.question))

  // 공무원: 연도/회차별 그룹
  const civilGroups = (() => {
    const g = {}
    civilItems.forEach(it => {
      const key = examGroup(it.question)
      if (!g[key]) g[key] = []
      g[key].push(it)
    })
    return g
  })()

  // NCS: 대행사 목록
  const ncsAgencies = [...new Set(ncsItems.map(i => getNcsAgency(i.question)))]

  // NCS: 선택된 대행사의 도메인별 그룹
  const ncsAgencyItems = selAgency ? ncsItems.filter(i => getNcsAgency(i.question) === selAgency) : []
  const ncsDomainGroups = (() => {
    const g = {}
    ncsAgencyItems.forEach(it => {
      const key = getNcsDomain(it.question)
      if (!g[key]) g[key] = []
      g[key].push(it)
    })
    return g
  })()

  // 최종 선택된 그룹의 아이템
  const currentGroupItems = selectedGroup
    ? (nbTab === 'civil' ? civilGroups[selectedGroup] : ncsDomainGroups[selectedGroup]) || []
    : []
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
        /* ── 카테고리 네비게이션 ── */
        <>
          {/* 브레드크럼 */}
          {(nbTab || selSubject || selAgency) && (
            <div className="ncs-breadcrumb" style={{ marginBottom: 16 }}>
              <button onClick={resetNav}>오답노트</button>
              {nbTab && (
                <>
                  <span className="ncs-bc-sep">›</span>
                  <button onClick={() => { setSelSubject(null); setSelAgency(null) }}>
                    {nbTab === 'civil' ? '공무원 기출' : 'NCS'}
                  </button>
                </>
              )}
              {(selSubject || selAgency) && (
                <>
                  <span className="ncs-bc-sep">›</span>
                  <span>{selSubject || selAgency}</span>
                </>
              )}
            </div>
          )}

          {/* 1단계: 카테고리 선택 */}
          {!nbTab && (
            <div className="home-tabs" style={{ marginBottom: 20 }}>
              <button className="home-tab" onClick={() => setNbTab('civil')}>공무원 기출</button>
              <button className="home-tab" onClick={() => setNbTab('ncs')}>NCS</button>
            </div>
          )}

          {/* 공무원: 과목 선택 */}
          {nbTab === 'civil' && !selSubject && (
            <div className="ncs-agency-grid">
              <div className="ncs-agency-card" style={{ cursor: 'default' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
                  <span className="ncs-agency-name" style={{ cursor: 'pointer' }} onClick={() => setSelSubject('경제학')}>경제학</span>
                  <button
                    className="btn-print-note"
                    onClick={e => { e.stopPropagation(); navigate(`/notebook/print/civil/경제학`) }}
                  >쪽집게 노트</button>
                </div>
                <span className="round-count" style={{ cursor: 'pointer' }} onClick={() => setSelSubject('경제학')}>{civilItems.length}문제</span>
              </div>
            </div>
          )}

          {/* 공무원: 연도/회차 그룹 */}
          {nbTab === 'civil' && selSubject && (
            <div className="notebook-group-list">
              {Object.keys(civilGroups).length === 0
                ? <p className="empty">아직 등록된 문제가 없어요.</p>
                : Object.entries(civilGroups).map(([name, list]) => {
                    const memoCount = list.filter(i => i.memo?.trim()).length
                    return (
                      <div key={name} className="notebook-group-card" onClick={() => selectGroup(name)}>
                        <div className="notebook-group-card-title">{name}</div>
                        <div className="notebook-group-card-meta">
                          <span>{list.length}문제</span>
                          <span className="notebook-group-memo-bar">
                            <span className="notebook-group-memo-fill"
                              style={{ width: `${Math.round(memoCount / list.length * 100)}%` }} />
                          </span>
                          <span>메모 {memoCount}/{list.length}</span>
                        </div>
                      </div>
                    )
                  })
              }
            </div>
          )}

          {/* NCS: 대행사 선택 */}
          {nbTab === 'ncs' && !selAgency && (
            <div className="ncs-agency-grid">
              {ncsAgencies.length === 0
                ? <p className="empty">아직 등록된 NCS 오답이 없어요.</p>
                : ncsAgencies.map(agency => (
                    <div key={agency} className="ncs-agency-card" style={{ cursor: 'default' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
                        <span className="ncs-agency-name" style={{ cursor: 'pointer' }} onClick={() => setSelAgency(agency)}>{agency}</span>
                        <button
                          className="btn-print-note"
                          onClick={e => { e.stopPropagation(); navigate(`/notebook/print/ncs/${encodeURIComponent(agency)}`) }}
                        >쪽집게 노트</button>
                      </div>
                      <span className="round-count" style={{ cursor: 'pointer' }} onClick={() => setSelAgency(agency)}>
                        {ncsItems.filter(i => getNcsAgency(i.question) === agency).length}문제
                      </span>
                    </div>
                  ))
              }
            </div>
          )}

          {/* NCS: 영역별 그룹 */}
          {nbTab === 'ncs' && selAgency && (
            <div className="notebook-group-list">
              {Object.keys(ncsDomainGroups).length === 0
                ? <p className="empty">아직 등록된 문제가 없어요.</p>
                : Object.entries(ncsDomainGroups).map(([domain, list]) => {
                    const memoCount = list.filter(i => i.memo?.trim()).length
                    return (
                      <div key={domain} className="notebook-group-card" onClick={() => selectGroup(domain)}>
                        <div className="notebook-group-card-title">{domain}</div>
                        <div className="notebook-group-card-meta">
                          <span>{list.length}문제</span>
                          <span className="notebook-group-memo-bar">
                            <span className="notebook-group-memo-fill"
                              style={{ width: `${Math.round(memoCount / list.length * 100)}%` }} />
                          </span>
                          <span>메모 {memoCount}/{list.length}</span>
                        </div>
                      </div>
                    )
                  })
              }
            </div>
          )}
        </>

      ) : (
        /* ── 일반 모드: 한 문제씩 ── */
        <>
          {/* 뒤로가기 */}
          <button className="btn-nb-back" onClick={() => selectGroup(null)}>
            ← {nbTab === 'ncs' ? `${selAgency} · ${selectedGroup}` : selectedGroup}
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
  const [showMemo, setShowMemo]   = useState(!!item.memo) // 메모 있으면 기본 펼침
  const [showSolution, setShowSolution] = useState(false)
  const [showChat, setShowChat]   = useState(false)
  const [chatHistory, setChatHistory] = useState([])
  const [chatInput, setChatInput] = useState('')
  const [chatLoading, setChatLoading] = useState(false)
  const [pendingImage, setPendingImage] = useState(null)
  const [chatMode, setChatMode]   = useState('teacher') // 'teacher' | 'student'
  const chatBottomRef = useRef(null)
  const canvasRef = useRef(null)
  const hasMemo = !!item.memo

  // 문제가 바뀌면 초기화
  useEffect(() => {
    setShowChat(false)
    setChatHistory([])
    setChatInput('')
    setShowSolution(false)
    setShowMemo(!!item.memo)
    setEditing(false)
    setMemo(item.memo || '')
    setChatMode('teacher')
  }, [item.id])

  const handleSave = async () => {
    await onSaveMemo(item.id, memo)
    setEditing(false)
  }

  const streamChat = async ({ userMsg = '', imgToSend = null, isOpener = false, modeOverride = null } = {}) => {
    const isProd = !['localhost', '127.0.0.1'].includes(window.location.hostname)
    const baseUrl = isProd
      ? 'https://project04-production.up.railway.app'
      : `http://${window.location.hostname}:8000`
    const token = localStorage.getItem('token')

    // 유저 메시지 먼저 UI에 추가
    if (!isOpener) {
      setChatHistory(prev => [...prev, { role: 'user', content: userMsg || '(필기 전송)', has_image: !!imgToSend }])
    }
    // 빈 AI 버블 추가 (스트리밍 중 채워짐)
    setChatHistory(prev => [...prev, { role: 'assistant', content: '' }])
    setChatLoading(true)

    try {
      const res = await fetch(`${baseUrl}/ai/notebook-chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          session_id: item.id,
          question: displayQ(item.question),
          memo: item.memo || '',
          solution: item.answer || '',
          user_message: userMsg,
          image_data: imgToSend || '',
          image_mime: 'image/png',
          mode: modeOverride ?? chatMode,
        }),
      })

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buf = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buf += decoder.decode(value, { stream: true })
        const lines = buf.split('\n')
        buf = lines.pop() // 미완성 줄 보관
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const data = JSON.parse(line.slice(6))
          if (data.text) {
            setChatHistory(prev => {
              const next = [...prev]
              next[next.length - 1] = { role: 'assistant', content: next[next.length - 1].content + data.text }
              return next
            })
          }
          if (data.done) {
            setChatHistory(data.history)
            if (data.credits_remaining !== undefined) dispatchCreditsUpdate(data.credits_remaining)
          }
        }
      }
    } finally {
      setChatLoading(false)
    }
  }

  const openChat = async () => {
    setShowChat(true)
    if (chatHistory.length === 0) {
      const saved = await getNotebookChatHistory(item.id)
      if (saved.data.history.length > 0) {
        setChatHistory(saved.data.history)
      } else {
        await streamChat({ isOpener: true })
      }
    }
  }

  const switchMode = async (newMode) => {
    if (newMode === chatMode) return
    setChatMode(newMode)
    setChatHistory([])
    setShowChat(true)
    await streamChat({ isOpener: true, modeOverride: newMode })
  }

  const captureDrawing = () => {
    const dataUrl = canvasRef.current?.capture()
    if (!dataUrl) return
    const b64 = dataUrl.split(',')[1]
    setPendingImage(b64)
  }

  const sendMessage = async () => {
    const msg = chatInput.trim()
    if ((!msg && !pendingImage) || chatLoading) return
    setChatInput('')
    const imgToSend = pendingImage
    setPendingImage(null)
    await streamChat({ userMsg: msg, imgToSend })
  }

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatHistory, chatLoading])

  return (
    <div className="note-card">
      {/* 메타 */}
      <div className="note-card-meta">
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span className="note-date">{item.created_at?.slice(0, 16)}</span>
          {examTag && <span className="note-exam-tag">{examTag}</span>}
        </div>
        <button className="btn-delete-sm" onClick={() => onDelete(item.id)}>삭제</button>
      </div>

      {/* ① 문제 영역 */}
      <div className="note-single-layout">
        <div className="note-question-panel">
          <DrawingCanvas ref={canvasRef} questionId={`note_${item.id}`}>
            {item.image_data ? (
              <img
                src={`data:${item.image_mime};base64,${item.image_data}`}
                alt="문제 이미지"
                className="note-img"
              />
            ) : item.problem_question ? (
              <div className="note-question-text">
                <p className="note-question">{item.problem_question}</p>
              </div>
            ) : (
              <p className="note-question">{displayQ(item.question)}</p>
            )}
          </DrawingCanvas>
        </div>
      </div>

      {/* ② 메모 (접기/펼치기) */}
      <div className="note-collapsible-section">
        <button
          className="note-section-toggle"
          onClick={() => { setShowMemo(v => !v); if (!showMemo && !hasMemo) setEditing(true) }}
        >
          <span className="note-step-info">
            <span className="note-step-badge">Step 1</span>
            <span className="note-step-title">메모</span>
            {!showMemo && !hasMemo && <span className="note-step-hint">모르는 내용을 적어보세요</span>}
          </span>
          <span className={`toggle-arrow ${showMemo ? 'open' : ''}`}>›</span>
        </button>
        {showMemo && (
          <div className="note-memo-panel">
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
            ) : memo ? (
              <>
                <MarkdownRenderer className="memo-content">{memo}</MarkdownRenderer>
                <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                  <button className="btn-memo-edit" onClick={() => setEditing(true)}>수정</button>
                  <button className="btn-cancel" onClick={async () => {
                    if (!confirm('메모를 전체 삭제할까요?')) return
                    setMemo('')
                    await onSaveMemo(item.id, '')
                  }}>전체 삭제</button>
                </div>
              </>
            ) : (
              <button className="btn-memo-add" onClick={() => setEditing(true)}>+ 메모 추가</button>
            )}
          </div>
        )}
      </div>

      {/* ③ AI 풀이 */}
      {item.answer && (
        <div className="note-collapsible-section">
          <button
            className="note-section-toggle"
            onClick={() => setShowSolution(v => !v)}
          >
            <span className="note-step-info">
              <span className="note-step-badge">Step 2</span>
              <span className="note-step-title">풀이</span>
            </span>
            <span className={`toggle-arrow ${showSolution ? 'open' : ''}`}>›</span>
          </button>
          {showSolution && (
            <div className="solution-body" style={{ margin: '0 0 0 0', borderRadius: '0 0 12px 12px' }}>
              {item.problem_correct_answer && (
                <div className="solution-correct-answer">
                  정답: <strong>{item.problem_correct_answer}</strong>
                </div>
              )}
              <SolutionRenderer
                hideAnswer={!!item.problem_correct_answer}
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

      {/* ④ AI 토론 */}
      <div className="note-collapsible-section note-chat-section">
        <button
          className="note-section-toggle"
          onClick={() => showChat ? setShowChat(false) : openChat()}
        >
          <span className="note-step-info">
            <span className="note-step-badge">{item.answer ? 'Step 3' : 'Step 2'}</span>
            <span className="note-step-title">AI 토론</span>
          </span>
          <span className={`toggle-arrow ${showChat ? 'open' : ''}`}>›</span>
        </button>
        {showChat && (
          <div className="note-chat-panel">
            {/* 모드 선택 */}
            <div className="chat-mode-bar">
              <button
                className={`btn-chat-mode ${chatMode === 'teacher' ? 'active' : ''}`}
                onClick={() => switchMode('teacher')}
              >
                선생모드
              </button>
              <button
                className={`btn-chat-mode ${chatMode === 'student' ? 'active' : ''}`}
                onClick={() => switchMode('student')}
              >
                생선모드 🐟
              </button>
              {chatMode === 'student' && (
                <span className="chat-mode-hint">AI가 학생이 되어 질문해요. 개념을 설명해보세요!</span>
              )}
            </div>
            <div className="chat-messages">
              {chatHistory.map((msg, i) => {
                const memoMatch = msg.role === 'assistant' && msg.content.match(/📝 메모 제안[:：]\s*(.+)/s)
                const memoSuggestion = memoMatch ? memoMatch[1].trim().split('\n')[0].trim() : null

                // assistant 메시지를 문단별로 분리
                const paragraphs = msg.role === 'assistant'
                  ? msg.content.split(/\n{2,}/).map(p => p.trim()).filter(Boolean)
                  : null

                return (
                  <div key={i} className={`chat-bubble ${msg.role}`}>
                    {paragraphs ? (
                      <div className="chat-bubble-paragraphs">
                        {paragraphs.map((para, j) => (
                          <div key={j} className="chat-para-row">
                            <MarkdownRenderer>{para}</MarkdownRenderer>
                            <button
                              className="btn-para-save"
                              title="메모에 추가"
                              onClick={async () => {
                                const next = memo ? memo + '\n\n' + para : para
                                setMemo(next)
                                await onSaveMemo(item.id, next)
                              }}
                            >+</button>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <MarkdownRenderer>{msg.content}</MarkdownRenderer>
                    )}
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
            {pendingImage && (
              <div className="chat-image-preview">
                <img src={`data:image/png;base64,${pendingImage}`} alt="필기 미리보기" />
                <button className="btn-remove-image" onClick={() => setPendingImage(null)}>✕</button>
              </div>
            )}
            <div className="chat-input-row">
              <button
                className={`btn-capture-drawing ${pendingImage ? 'has-image' : ''}`}
                onClick={captureDrawing}
                title="필기 캡처해서 전송"
              >✏️</button>
              <textarea
                className="chat-input"
                value={chatInput}
                onChange={e => setChatInput(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage() } }}
                placeholder="이해한 내용을 설명하거나 필기를 전송해보세요..."
                rows={2}
              />
              <button className="btn-chat-send" onClick={sendMessage} disabled={chatLoading || (!chatInput.trim() && !pendingImage)}>
                전송
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
