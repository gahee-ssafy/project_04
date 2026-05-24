import ReactMarkdown from 'react-markdown'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import 'katex/dist/katex.min.css'

// 수식 닫힘 뒤 한글 등 비공백 문자 판별
const NON_BREAK = /[^\s$.,!?;:()\[\]{}'"\d\n]/

/**
 * 문자 단위 스캔으로 수식 블록을 찾아 두 가지 처리:
 * 1) 수식 내부 \$ → ＄(전각 달러, U+FF04) 로 교체 — remark-math 오파싱 방지
 * 2) 닫히는 $ 뒤에 한글 등이 바로 붙으면 공백 삽입 — remark-math 인식 보조
 */
function preprocessMath(text) {
  if (!text) return text
  const DOLLAR = '＄' // 전각 달러 — KaTeX에서 $ 처럼 보임
  let out = ''
  let i = 0

  while (i < text.length) {
    // 블록 수식 $$...$$
    if (text[i] === '$' && text[i + 1] === '$') {
      const end = text.indexOf('$$', i + 2)
      if (end !== -1) {
        const inner = text.slice(i + 2, end).replace(/\\\$/g, DOLLAR)
        out += '$$' + inner + '$$'
        i = end + 2
        if (i < text.length && NON_BREAK.test(text[i])) out += ' '
        continue
      }
    }

    // 인라인 수식 $...$  (앞에 \가 없을 때만)
    if (text[i] === '$' && (i === 0 || text[i - 1] !== '\\')) {
      let j = i + 1
      let found = false
      while (j < text.length) {
        if (text[j] === '\\' && text[j + 1] === '$') {
          j += 2 // \$ 건너뜀
        } else if (text[j] === '$') {
          // 닫히는 $ 발견
          const inner = text.slice(i + 1, j).replace(/\\\$/g, DOLLAR)
          out += '$' + inner + '$'
          j++
          if (j < text.length && NON_BREAK.test(text[j])) out += ' '
          i = j
          found = true
          break
        } else if (text[j] === '\n') {
          break // 인라인 수식은 줄바꿈 없음
        } else {
          j++
        }
      }
      if (!found) { out += text[i]; i++ }
      continue
    }

    out += text[i]
    i++
  }

  return out
}

/**
 * 마크다운 + LaTeX 수식 렌더러
 * 인라인: $수식$  /  블록: $$수식$$
 */
export default function MarkdownRenderer({ children, className = '' }) {
  if (!children) return null
  return (
    <div className={`markdown-body ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkMath]}
        rehypePlugins={[rehypeKatex]}
      >
        {preprocessMath(children)}
      </ReactMarkdown>
    </div>
  )
}
