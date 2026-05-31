import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getExamRounds, getNcsList } from '../api/exam'

const NCS_DOMAINS = [
  '의사소통능력','수리능력','문제해결능력','자기개발능력','자원관리능력',
  '대인관계능력','정보능력','기술능력','조직이해능력','직업윤리',
]

// 공무원 기출 과목 목록 (추후 확장 가능)
const CIVIL_SUBJECTS = ['경제학']

export default function ExamListPage() {
  const [tab, setTab]               = useState('civil') // 'civil' | 'ncs'
  const [rounds, setRounds]         = useState([])
  const [ncsList, setNcsList]       = useState([])
  const [loading, setLoading]       = useState(true)

  // 공무원 드릴다운 상태
  const [selSubject, setSelSubject] = useState(null)

  // NCS 드릴다운 상태
  const [selAgency, setSelAgency]   = useState(null)
  const [selYear,   setSelYear]     = useState(null)

  const navigate = useNavigate()

  useEffect(() => {
    Promise.all([getExamRounds(), getNcsList()])
      .then(([r, n]) => { setRounds(r.data); setNcsList(n.data) })
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <p className="loading">불러오는 중...</p>

  // ── NCS 그룹핑 ─────────────────────────────────────────────
  const ncsAgencies = [...new Set(ncsList.map(r => r.ncs_agency))]
  const ncsYears = selAgency
    ? [...new Set(ncsList.filter(r => r.ncs_agency === selAgency).map(r => r.exam_year))].sort((a,b)=>b-a)
    : []
  const ncsDomains = (selAgency && selYear)
    ? ncsList.filter(r => r.ncs_agency === selAgency && r.exam_year === selYear)
    : []

  return (
    <div className="exam-list-page">
      {/* 탭 */}
      <div className="home-tabs" style={{ marginBottom: 24 }}>
        <button className={`home-tab ${tab === 'civil' ? 'active' : ''}`} onClick={() => setTab('civil')}>
          공무원 기출
        </button>
        <button className={`home-tab ${tab === 'ncs' ? 'active' : ''}`} onClick={() => setTab('ncs')}>
          NCS
        </button>
      </div>

      {/* ── 공무원 기출 ── */}
      {tab === 'civil' && (
        <>
          {/* 브레드크럼 */}
          {selSubject && (
            <div className="ncs-breadcrumb">
              <button onClick={() => setSelSubject(null)}>공무원 기출</button>
              <span className="ncs-bc-sep">›</span>
              <span>{selSubject}</span>
            </div>
          )}

          {/* 과목 선택 */}
          {!selSubject && (
            <>
              <div className="exam-list-header">
                <h2>공무원 기출</h2>
                <p className="exam-desc">과목을 선택하세요</p>
              </div>
              <div className="ncs-agency-grid">
                {CIVIL_SUBJECTS.map(subject => (
                  <button
                    key={subject}
                    className="ncs-agency-card"
                    onClick={() => setSelSubject(subject)}
                  >
                    <span className="ncs-agency-name">{subject}</span>
                  </button>
                ))}
              </div>
            </>
          )}

          {/* 연도 선택 */}
          {selSubject && (
            <>
              <div className="exam-list-header">
                <h2>{selSubject}</h2>
                <p className="exam-desc">풀고 싶은 연도를 선택하세요</p>
              </div>
              {rounds.length === 0 ? (
                <div className="empty-box"><p>아직 등록된 문제가 없어요.</p></div>
              ) : (
                <div className="round-grid">
                  {rounds.map(r => (
                    <button
                      key={`${r.exam_year}-${r.exam_round}`}
                      className="round-card"
                      onClick={() => navigate(`/exam/civil/${r.exam_year}/${r.exam_round}`)}
                    >
                      <span className="round-year">{r.exam_year}년</span>
                      <span className="round-count">{r.problem_count}문제</span>
                    </button>
                  ))}
                </div>
              )}
            </>
          )}
        </>
      )}

      {/* ── NCS ── */}
      {tab === 'ncs' && (
        <>
          {/* 브레드크럼 */}
          {(selAgency || selYear) && (
            <div className="ncs-breadcrumb">
              <button onClick={() => { setSelAgency(null); setSelYear(null) }}>NCS</button>
              {selAgency && (
                <>
                  <span className="ncs-bc-sep">›</span>
                  <button onClick={() => setSelYear(null)}>{selAgency}</button>
                </>
              )}
              {selYear && (
                <>
                  <span className="ncs-bc-sep">›</span>
                  <span>{selYear}년</span>
                </>
              )}
            </div>
          )}

          {/* 대행사 선택 */}
          {!selAgency && (
            <>
              <div className="exam-list-header">
                <h2>NCS 문제은행</h2>
                <p className="exam-desc">출제 기관을 선택하세요</p>
              </div>
              {ncsAgencies.length === 0 ? (
                <div className="empty-box">
                  <p>아직 등록된 NCS 문제가 없어요.</p>
                </div>
              ) : (
                <div className="ncs-agency-grid">
                  {ncsAgencies.map(agency => {
                    const count = ncsList.filter(r => r.ncs_agency === agency)
                      .reduce((s, r) => s + r.problem_count, 0)
                    return (
                      <button key={agency} className="ncs-agency-card"
                        onClick={() => setSelAgency(agency)}>
                        <span className="ncs-agency-name">{agency}</span>
                        <span className="round-count">{count}문제</span>
                      </button>
                    )
                  })}
                </div>
              )}
            </>
          )}

          {/* 연도 선택 */}
          {selAgency && !selYear && (
            <>
              <div className="exam-list-header">
                <h2>{selAgency}</h2>
                <p className="exam-desc">출제 연도를 선택하세요</p>
              </div>
              <div className="round-grid">
                {ncsYears.map(year => {
                  const count = ncsList
                    .filter(r => r.ncs_agency === selAgency && r.exam_year === year)
                    .reduce((s, r) => s + r.problem_count, 0)
                  return (
                    <button key={year} className="round-card"
                      onClick={() => setSelYear(year)}>
                      <span className="round-year">{year}년</span>
                      <span className="round-count">{count}문제</span>
                    </button>
                  )
                })}
              </div>
            </>
          )}

          {/* 분야 선택 */}
          {selAgency && selYear && (
            <>
              <div className="exam-list-header">
                <h2>{selYear}년</h2>
                <p className="exam-desc">풀 분야를 선택하세요</p>
              </div>
              <div className="ncs-domain-list">
                {ncsDomains.map(r => (
                  <button
                    key={r.ncs_domain}
                    className="ncs-domain-card"
                    onClick={() => navigate(
                      `/exam/ncs/${encodeURIComponent(selAgency)}/${selYear}/${encodeURIComponent(r.ncs_domain)}`
                    )}
                  >
                    <span className="ncs-domain-name">{r.ncs_domain}</span>
                    <span className="round-count">{r.problem_count}문제</span>
                  </button>
                ))}
              </div>
            </>
          )}
        </>
      )}
    </div>
  )
}
