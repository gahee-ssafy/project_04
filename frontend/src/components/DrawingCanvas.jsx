import { useRef, useEffect, useState, useCallback } from 'react'

const COLORS = ['#1a1a1a', '#2563eb', '#dc2626', '#16a34a', '#9333ea']
const PEN_SIZES = [2, 4, 7]

export default function DrawingCanvas({ questionId }) {
  const canvasRef = useRef(null)
  const isDrawing = useRef(false)
  const lastPos   = useRef(null)
  const [tool, setTool]   = useState('pen')
  const [color, setColor] = useState('#1a1a1a')
  const [size, setSize]   = useState(4)

  const STORAGE_KEY = `drawing_${questionId}`

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    const dpr  = window.devicePixelRatio || 1
    const rect  = canvas.getBoundingClientRect()
    canvas.width  = rect.width  * dpr
    canvas.height = rect.height * dpr
    ctx.scale(dpr, dpr)
    ctx.lineCap  = 'round'
    ctx.lineJoin = 'round'

    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) {
      const img = new Image()
      img.onload = () => ctx.drawImage(img, 0, 0, rect.width, rect.height)
      img.src = saved
    }
  }, [questionId])

  const getPos = (e, canvas) => {
    const rect = canvas.getBoundingClientRect()
    const src  = e.touches ? e.touches[0] : e
    return { x: src.clientX - rect.left, y: src.clientY - rect.top }
  }

  const startDraw = useCallback((e) => {
    e.preventDefault()
    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')
    isDrawing.current = true
    lastPos.current = getPos(e, canvas)
    const { x, y } = lastPos.current
    if (tool === 'eraser') {
      ctx.clearRect(x - size * 4, y - size * 4, size * 8, size * 8)
    } else {
      ctx.beginPath()
      ctx.arc(x, y, size / 2, 0, Math.PI * 2)
      ctx.fillStyle = color
      ctx.fill()
    }
  }, [tool, color, size])

  const draw = useCallback((e) => {
    if (!isDrawing.current) return
    e.preventDefault()
    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')
    const pos = getPos(e, canvas)
    ctx.beginPath()
    ctx.moveTo(lastPos.current.x, lastPos.current.y)
    ctx.lineTo(pos.x, pos.y)
    if (tool === 'eraser') {
      ctx.globalCompositeOperation = 'destination-out'
      ctx.strokeStyle = 'rgba(0,0,0,1)'
      ctx.lineWidth = size * 5
    } else {
      ctx.globalCompositeOperation = 'source-over'
      ctx.strokeStyle = color
      ctx.lineWidth = size
    }
    ctx.stroke()
    lastPos.current = pos
  }, [tool, color, size])

  const endDraw = useCallback(() => {
    if (!isDrawing.current) return
    isDrawing.current = false
    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')
    ctx.globalCompositeOperation = 'source-over'
    localStorage.setItem(STORAGE_KEY, canvas.toDataURL())
  }, [STORAGE_KEY])

  const clearCanvas = () => {
    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')
    const dpr  = window.devicePixelRatio || 1
    const rect  = canvas.getBoundingClientRect()
    ctx.clearRect(0, 0, rect.width * dpr, rect.height * dpr)
    localStorage.removeItem(STORAGE_KEY)
  }

  return (
    <div className="drawing-overlay">
      {/* 플로팅 툴바 */}
      <div className="drawing-overlay-toolbar">
        <button
          className={`drawing-tool-btn ${tool === 'pen' ? 'active' : ''}`}
          onClick={() => setTool('pen')}
        >펜</button>
        <button
          className={`drawing-tool-btn ${tool === 'eraser' ? 'active' : ''}`}
          onClick={() => setTool('eraser')}
        >지우개</button>

        {tool === 'pen' && (
          <>
            <div className="drawing-divider" />
            <div className="drawing-colors">
              {COLORS.map(c => (
                <button
                  key={c}
                  className={`drawing-color-btn ${color === c ? 'active' : ''}`}
                  style={{ background: c }}
                  onClick={() => setColor(c)}
                />
              ))}
            </div>
            <div className="drawing-divider" />
            <div className="drawing-sizes">
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
          </>
        )}

        <div className="drawing-divider" />
        <button className="drawing-clear-btn" onClick={clearCanvas}>전체 지우기</button>
      </div>

      {/* 투명 캔버스 */}
      <canvas
        ref={canvasRef}
        className="drawing-canvas-overlay"
        onMouseDown={startDraw}
        onMouseMove={draw}
        onMouseUp={endDraw}
        onMouseLeave={endDraw}
        onTouchStart={startDraw}
        onTouchMove={draw}
        onTouchEnd={endDraw}
      />
    </div>
  )
}
