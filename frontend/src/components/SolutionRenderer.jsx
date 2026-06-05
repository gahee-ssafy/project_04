import MarkdownRenderer from './MarkdownRenderer'

const CHOICE_REGEX = /^([①②③④⑤])\s*/

/**
 * AI 풀이 텍스트를 [정답] / [풀이] / 선지별로 파싱해서 렌더링
 */
export default function SolutionRenderer({ children, onAddToMemo, hideAnswer = false }) {
  if (!children) return null

  // $$...$$ 블록 수식이 줄바꿈에 의해 끊기지 않도록 먼저 보호
  const normalized = children.replace(/\$\$([\s\S]+?)\$\$/g, (_, inner) =>
    `$$${inner.replace(/\n/g, ' ')}$$`
  )

  const lines = normalized.split('\n')
  const sections = []
  let current = null

  for (const raw of lines) {
    const line = raw.trim()
    if (!line) continue

    if (line.startsWith('[정답]')) {
      current = { type: 'answer', content: line.replace('[정답]', '').trim() }
      sections.push(current)
    } else if (line.startsWith('[풀이]')) {
      current = { type: 'section', label: '풀이', items: [] }
      sections.push(current)
    } else if (current?.type === 'section') {
      const m = line.match(CHOICE_REGEX)
      if (m) {
        current.items.push({ marker: m[1], text: line.replace(CHOICE_REGEX, '') })
      } else if (current.items.length > 0) {
        current.items[current.items.length - 1].text += '\n' + line
      } else {
        current.items.push({ marker: null, text: line })
      }
    } else {
      if (!current || current.type !== 'misc') {
        current = { type: 'misc', content: line }
        sections.push(current)
      } else {
        current.content += '\n' + line
      }
    }
  }

  return (
    <div className="solution-renderer">
      {sections.map((sec, i) => {
        if (sec.type === 'answer') {
          if (hideAnswer) return null
          return (
            <div key={i} className="sol-answer-row">
              <span className="sol-label">정답</span>
              <span className="sol-answer-val">{sec.content}</span>
            </div>
          )
        }

        if (sec.type === 'section') {
          return (
            <div key={i} className="sol-section">
              <div className="sol-section-label">풀이</div>
              <div className="sol-items">
                {sec.items.map((item, j) => (
                  <div key={j} className="sol-item">
                    {item.marker && (
                      <span className="sol-marker">{item.marker}</span>
                    )}
                    <span className="sol-text">
                      <MarkdownRenderer>{item.text}</MarkdownRenderer>
                    </span>
                    {onAddToMemo && (
                      <button
                        className="btn-sol-to-memo"
                        title="메모에 추가"
                        onClick={() => onAddToMemo(
                          item.marker ? `${item.marker} ${item.text}` : item.text
                        )}
                      >+</button>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )
        }

        if (sec.type === 'misc') {
          if (hideAnswer && /^[①②③④⑤](\s*\n\s*풀이)?\s*$/.test(sec.content.trim())) return null
          return (
            <div key={i} className="sol-misc">
            <MarkdownRenderer>{sec.content}</MarkdownRenderer>
          </div>
          )
        }

        return null
      })}
    </div>
  )
}
