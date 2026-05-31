import { useState } from 'react'
import client from '../api/client'

const NCS_DOMAINS = [
  '의사소통능력','수리능력','문제해결능력','자기개발능력','자원관리능력',
  '대인관계능력','정보능력','기술능력','조직이해능력','직업윤리',
]

export default function AdminPage() {
  const [agency,     setAgency]     = useState('')
  const [year,       setYear]       = useState(new Date().getFullYear())
  const [domain,     setDomain]     = useState(NCS_DOMAINS[0])
  const [sampleText, setSampleText] = useState('')
  const [count,      setCount]      = useState(5)

  const [generating, setGenerating] = useState(false)
  const [generated,  setGenerated]  = useState([])  // 생성된 문제들
  const [checked,    setChecked]    = useState({})   // 저장할 문제 선택
  const [saving,     setSaving]     = useState(false)
  const [savedCount, setSavedCount] = useState(null)
  const [error,      setError]      = useState('')

  const handleGenerate = async () => {
    if (!agency.trim()) return setError('대행사를 입력하세요.')
    if (!sampleText.trim()) return setError('예시 문제를 입력하세요.')
    setError('')
    setGenerating(true)
    setGenerated([])
    setSavedCount(null)
    try {
      const res = await client.post('/admin/generate', {
        agency, exam_year: parseInt(year), domain, sample_text: sampleText, count,
      })
      const qs = res.data.questions
      setGenerated(qs)
      // 전체 선택
      const all = {}
      qs.forEach((_, i) => { all[i] = true })
      setChecked(all)
    } catch (e) {
      setError(e.response?.data?.detail || '생성 실패')
    } finally {
      setGenerating(false)
    }
  }

  const handleSave = async () => {
    const toSave = generated.filter((_, i) => checked[i])
    if (toSave.length === 0) return setError('저장할 문제를 선택하세요.')
    setSaving(true)
    setError('')
    try {
      const res = await client.post('/admin/save-ncs', {
        agency, exam_year: parseInt(year), domain, questions: toSave,
      })
      setSavedCount(res.data.saved)
      setGenerated([])
      setChecked({})
    } catch (e) {
      setError(e.response?.data?.detail || '저장 실패')
    } finally {
      setSaving(false)
    }
  }

  const toggleAll = () => {
    const allChecked = generated.every((_, i) => checked[i])
    const next = {}
    generated.forEach((_, i) => { next[i] = !allChecked })
    setChecked(next)
  }

  return (
    <div style={{ maxWidth: 720, margin: '0 auto', padding: '24px 16px' }}>
      <h2 style={{ fontWeight: 800, fontSize: '1.3rem', marginBottom: 24, letterSpacing: '-0.02em' }}>
        NCS 문제 생성
      </h2>

      {/* 설정 */}
      <div className="admin-form-card">
        <div className="admin-form-row">
          <label>대행사</label>
          <input
            className="admin-input"
            placeholder="예: 사람인HR, 트리피, 인크루트"
            value={agency}
            onChange={e => setAgency(e.target.value)}
          />
        </div>
        <div className="admin-form-row">
          <label>연도</label>
          <input
            className="admin-input"
            type="number"
            value={year}
            onChange={e => setYear(e.target.value)}
            style={{ width: 100 }}
          />
        </div>
        <div className="admin-form-row">
          <label>분야</label>
          <select className="admin-input" value={domain} onChange={e => setDomain(e.target.value)}>
            {NCS_DOMAINS.map(d => <option key={d} value={d}>{d}</option>)}
          </select>
        </div>
        <div className="admin-form-row">
          <label>생성 개수</label>
          <div style={{ display: 'flex', gap: 8 }}>
            {[5, 10, 15, 20].map(n => (
              <button
                key={n}
                className={`admin-count-btn ${count === n ? 'active' : ''}`}
                onClick={() => setCount(n)}
              >{n}개</button>
            ))}
          </div>
        </div>
      </div>

      {/* 샘플 문제 */}
      <div className="admin-form-card">
        <div style={{ marginBottom: 8 }}>
          <label style={{ fontWeight: 700, fontSize: '0.88rem' }}>
            예시 문제 (2~3개 붙여넣기)
          </label>
          <p style={{ fontSize: '0.78rem', color: 'var(--text-3)', marginTop: 2 }}>
            문제 이미지를 Claude에게 보내면 텍스트로 추출해줘요. 그걸 여기 붙여넣으세요.
          </p>
        </div>
        <textarea
          className="admin-textarea"
          placeholder={`예시:\n1. 다음 중 의사소통의 기본 원칙으로 옳지 않은 것은?\n① 명확성 ② 간결성 ③ 복잡성 ④ 일관성\n정답: ③\n\n2. ...`}
          value={sampleText}
          onChange={e => setSampleText(e.target.value)}
          rows={10}
        />
      </div>

      {error && <p style={{ color: '#E53E3E', fontSize: '0.85rem', marginBottom: 12 }}>{error}</p>}

      <button
        className="admin-generate-btn"
        onClick={handleGenerate}
        disabled={generating}
      >
        {generating ? '생성 중...' : `✨ ${count}개 문제 생성`}
      </button>

      {/* 생성 결과 */}
      {generated.length > 0 && (
        <div style={{ marginTop: 32 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h3 style={{ fontWeight: 700, fontSize: '1rem' }}>
              생성된 문제 ({generated.length}개)
            </h3>
            <div style={{ display: 'flex', gap: 8 }}>
              <button className="admin-select-all-btn" onClick={toggleAll}>
                {generated.every((_, i) => checked[i]) ? '전체 해제' : '전체 선택'}
              </button>
              <button
                className="admin-save-btn"
                onClick={handleSave}
                disabled={saving || !Object.values(checked).some(Boolean)}
              >
                {saving ? '저장 중...' : `선택 저장 (${Object.values(checked).filter(Boolean).length}개)`}
              </button>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {generated.map((q, i) => (
              <div
                key={i}
                className={`admin-question-card ${checked[i] ? 'selected' : ''}`}
                onClick={() => setChecked(prev => ({ ...prev, [i]: !prev[i] }))}
              >
                <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
                  <div className={`admin-check ${checked[i] ? 'checked' : ''}`}>
                    {checked[i] && '✓'}
                  </div>
                  <div style={{ flex: 1 }}>
                    <p style={{ fontWeight: 600, fontSize: '0.9rem', marginBottom: 10 }}>
                      {i + 1}. {q.question}
                    </p>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginBottom: 10 }}>
                      {Object.entries(q.choices || {}).map(([k, v]) => (
                        <span
                          key={k}
                          style={{
                            fontSize: '0.85rem',
                            color: k === q.answer ? 'var(--primary)' : 'var(--text-2)',
                            fontWeight: k === q.answer ? 700 : 400,
                          }}
                        >
                          {k} {v} {k === q.answer ? '← 정답' : ''}
                        </span>
                      ))}
                    </div>
                    {q.explanation && (
                      <p style={{ fontSize: '0.8rem', color: 'var(--text-3)', borderTop: '1px solid var(--border)', paddingTop: 8 }}>
                        💡 {q.explanation}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {savedCount !== null && (
        <div className="admin-success">
          ✅ {savedCount}개 문제가 저장되었어요! ({agency} · {year}년 · {domain})
        </div>
      )}
    </div>
  )
}
