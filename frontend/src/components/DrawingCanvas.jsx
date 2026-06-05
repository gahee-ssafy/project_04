import { useRef, useEffect, useState, useCallback, useImperativeHandle, forwardRef } from 'react'


const DrawingCanvas = forwardRef(function DrawingCanvas({ questionId, children }, ref) {
  const canvasRef  = useRef(null)
  const isDrawing  = useRef(false)
  const lastPos    = useRef(null)
  const lastMid    = useRef(null)

  // tool: 'pen' | 'highlight' | 'eraser'
  const [tool, setTool] = useState('pen')

  const STORAGE_KEY = `drawing_${questionId}`

  // 캔버스 초기화 + 저장된 필기 복원
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const initCanvas = () => {
      const ctx  = canvas.getContext('2d')
      const dpr  = window.devicePixelRatio || 1
      const rect = canvas.getBoundingClientRect()
      if (rect.width === 0 || rect.height === 0) return
      canvas.width  = Math.round(rect.width  * dpr)
      canvas.height = Math.round(rect.height * dpr)
      ctx.scale(dpr, dpr)
      ctx.lineCap  = 'round'
      ctx.lineJoin = 'round'

      const saved = localStorage.getItem(STORAGE_KEY)
      if (saved) {
        const img = new Image()
        img.onload = () => ctx.drawImage(img, 0, 0, rect.width, rect.height)
        img.src = saved
      }
    }

    // 이미지 로드 후 레이아웃이 확정되면 초기화
    initCanvas()

    // ResizeObserver로 크기 변경 시 재초기화 (이미지 로드 후 레이아웃 변경 대응)
    const ro = new ResizeObserver(() => {
      const ctx  = canvas.getContext('2d')
      const dpr  = window.devicePixelRatio || 1
      const rect = canvas.getBoundingClientRect()
      if (rect.width === 0 || rect.height === 0) return
      const newW = Math.round(rect.width  * dpr)
      const newH = Math.round(rect.height * dpr)
      if (canvas.width === newW && canvas.height === newH) return

      // 기존 내용 스냅샷
      const tmp = document.createElement('canvas')
      tmp.width  = canvas.width
      tmp.height = canvas.height
      if (canvas.width > 0 && canvas.height > 0) {
        tmp.getContext('2d').drawImage(canvas, 0, 0)
      }

      canvas.width  = newW
      canvas.height = newH
      ctx.scale(dpr, dpr)
      ctx.lineCap  = 'round'
      ctx.lineJoin = 'round'

      if (tmp.width > 0 && tmp.height > 0) {
        ctx.drawImage(tmp, 0, 0, rect.width, rect.height)
      }
    })
    ro.observe(canvas)
    return () => ro.disconnect()
  }, [questionId])

  // CSS 좌표 → ctx 좌표 (dpr 스케일 보정)
  const getPos = (e) => {
    const canvas = canvasRef.current
    const rect   = canvas.getBoundingClientRect()
    return { x: e.clientX - rect.left, y: e.clientY - rect.top }
  }

  // ── 포인터 다운 ──────────────────────────────────────
  const toolConfig = {
    pen:    { color: '#1a1a1a', size: 3,  composite: 'source-over' },
    eraser: { color: 'rgba(0,0,0,1)', size: 18, composite: 'destination-out' },
  }

  const onPointerDown = useCallback((e) => {
    e.preventDefault()
    canvasRef.current.setPointerCapture(e.pointerId)
    isDrawing.current = true
    const pos = getPos(e)
    lastPos.current = pos
    lastMid.current = pos
  }, [])

  // ── 포인터 이동 (베지어 곡선으로 부드럽게) ──────────
  const onPointerMove = useCallback((e) => {
    if (!isDrawing.current) return
    e.preventDefault()
    const canvas = canvasRef.current
    const ctx    = canvas.getContext('2d')
    const pos    = getPos(e)
    const prev   = lastPos.current
    const mid    = { x: (prev.x + pos.x) / 2, y: (prev.y + pos.y) / 2 }
    const cfg    = toolConfig[tool]

    ctx.beginPath()
    ctx.moveTo(lastMid.current.x, lastMid.current.y)
    ctx.globalCompositeOperation = cfg.composite
    ctx.strokeStyle = cfg.color
    ctx.lineWidth   = cfg.size
    ctx.lineCap     = 'round'
    ctx.lineJoin    = 'round'
    ctx.quadraticCurveTo(prev.x, prev.y, mid.x, mid.y)
    ctx.stroke()

    lastPos.current = pos
    lastMid.current = mid
  }, [tool])

  // ── 포인터 업 ────────────────────────────────────────
  const onPointerUp = useCallback(() => {
    if (!isDrawing.current) return
    isDrawing.current = false
    const canvas = canvasRef.current
    const ctx    = canvas.getContext('2d')
    ctx.globalCompositeOperation = 'source-over'
    localStorage.setItem(STORAGE_KEY, canvas.toDataURL())
  }, [STORAGE_KEY])

  // 외부에서 캔버스 이미지 캡처
  useImperativeHandle(ref, () => ({
    capture: () => canvasRef.current?.toDataURL('image/png') ?? null,
  }))

  const clearCanvas = () => {
    const canvas = canvasRef.current
    const ctx    = canvas.getContext('2d')
    const dpr    = window.devicePixelRatio || 1
    ctx.clearRect(0, 0, canvas.width / dpr, canvas.height / dpr)
    localStorage.removeItem(STORAGE_KEY)
  }

  return (
    <div className="question-canvas-wrapper">
      {/* 상단 툴바 */}
      <div className="drawing-toolbar-top">
        <button
          className={`dtool-btn ${tool === 'pen' ? 'active' : ''}`}
          onClick={() => setTool('pen')}
          title="펜"
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>
        </button>
        <button
          className={`dtool-btn ${tool === 'eraser' ? 'active' : ''}`}
          onClick={() => setTool('eraser')}
          title="지우개"
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M20 20H7L3 16l10-10 7 7-3.5 3.5"/><path d="M6.0001 17.0001L17 6"/></svg>
        </button>
        <div className="dtool-divider" />
        <button className="dtool-btn dtool-clear" onClick={clearCanvas} title="전체 지우기">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4h6v2"/></svg>
        </button>
      </div>

      {/* 문제 콘텐츠 + 투명 캔버스 오버레이 */}
      <div className="question-canvas-area">
        {children}
        <canvas
          ref={canvasRef}
          className="drawing-canvas-overlay"
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
          onPointerLeave={onPointerUp}
        />
      </div>
    </div>
  )
})

export default DrawingCanvas
