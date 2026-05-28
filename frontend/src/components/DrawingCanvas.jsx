import { useRef, useEffect, useState, useCallback, useImperativeHandle, forwardRef } from 'react'

const COLORS = ['#1a1a1a', '#2563eb', '#dc2626', '#16a34a', '#9333ea']
const PEN_SIZES = [2, 4, 7]

const DrawingCanvas = forwardRef(function DrawingCanvas({ questionId, children }, ref) {
  const canvasRef  = useRef(null)
  const isDrawing  = useRef(false)
  const lastPos    = useRef(null)
  const lastMid    = useRef(null)

  const [tool,  setTool]  = useState('pen')
  const [color, setColor] = useState('#1a1a1a')
  const [size,  setSize]  = useState(4)

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
  const onPointerDown = useCallback((e) => {
    e.preventDefault()
    canvasRef.current.setPointerCapture(e.pointerId)
    isDrawing.current = true
    const pos = getPos(e)
    lastPos.current = pos
    lastMid.current = pos

    if (tool !== 'eraser') {
      const ctx = canvasRef.current.getContext('2d')
      ctx.globalCompositeOperation = 'source-over'
      ctx.strokeStyle = color
      ctx.lineWidth   = size
      ctx.beginPath()
      ctx.arc(pos.x, pos.y, size / 2, 0, Math.PI * 2)
      ctx.fillStyle = color
      ctx.fill()
    }
  }, [tool, color, size])

  // ── 포인터 이동 (베지어 곡선으로 부드럽게) ──────────
  const onPointerMove = useCallback((e) => {
    if (!isDrawing.current) return
    e.preventDefault()
    const canvas = canvasRef.current
    const ctx    = canvas.getContext('2d')
    const pos    = getPos(e)
    const prev   = lastPos.current
    const mid    = { x: (prev.x + pos.x) / 2, y: (prev.y + pos.y) / 2 }

    ctx.beginPath()
    ctx.moveTo(lastMid.current.x, lastMid.current.y)

    if (tool === 'eraser') {
      ctx.globalCompositeOperation = 'destination-out'
      ctx.strokeStyle = 'rgba(0,0,0,1)'
      ctx.lineWidth   = size * 6
      ctx.quadraticCurveTo(prev.x, prev.y, mid.x, mid.y)
    } else {
      ctx.globalCompositeOperation = 'source-over'
      ctx.strokeStyle = color
      ctx.lineWidth   = size
      ctx.quadraticCurveTo(prev.x, prev.y, mid.x, mid.y)
    }

    ctx.stroke()
    lastPos.current = pos
    lastMid.current = mid
  }, [tool, color, size])

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
      {/* 왼쪽: 문제 콘텐츠 + 투명 캔버스 오버레이 */}
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

      {/* 오른쪽: 세로 툴바 */}
      <div className="drawing-toolbar-right">
        <button
          className={`drawing-tool-btn ${tool === 'pen' ? 'active' : ''}`}
          onClick={() => setTool('pen')}
          title="펜"
        >✏️</button>
        <button
          className={`drawing-tool-btn ${tool === 'eraser' ? 'active' : ''}`}
          onClick={() => setTool('eraser')}
          title="지우개"
        >🧹</button>

        <div className="drawing-divider-h" />

        {tool === 'pen' && (
          <>
            <div className="drawing-colors-vert">
              {COLORS.map(c => (
                <button
                  key={c}
                  className={`drawing-color-btn ${color === c ? 'active' : ''}`}
                  style={{ background: c }}
                  onClick={() => setColor(c)}
                />
              ))}
            </div>
            <div className="drawing-divider-h" />
            <div className="drawing-sizes-vert">
              {PEN_SIZES.map(s => (
                <button
                  key={s}
                  className={`drawing-size-btn ${size === s ? 'active' : ''}`}
                  onClick={() => setSize(s)}
                >
                  <span style={{
                    width: s * 2.5, height: s * 2.5,
                    borderRadius: '50%', background: '#555', display: 'block'
                  }} />
                </button>
              ))}
            </div>
            <div className="drawing-divider-h" />
          </>
        )}

        <button className="drawing-clear-btn" onClick={clearCanvas} title="전체 지우기">🗑️</button>
      </div>
    </div>
  )
})

export default DrawingCanvas
