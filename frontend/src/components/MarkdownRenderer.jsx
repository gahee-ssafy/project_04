import ReactMarkdown from 'react-markdown'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import 'katex/dist/katex.min.css'

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
        {children}
      </ReactMarkdown>
    </div>
  )
}
