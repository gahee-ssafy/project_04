import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getExamRounds } from '../api/exam'

export default function ExamListPage() {
  const [rounds, setRounds] = useState([])
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    getExamRounds()
      .then((res) => setRounds(res.data))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <p className="loading">불러오는 중...</p>

  return (
    <div className="exam-list-page">
      <h2>📚 모의고사</h2>
      <p className="exam-desc">풀고 싶은 회차를 선택하세요.</p>

      {rounds.length === 0 ? (
        <div className="empty-box">
          <p>아직 등록된 모의고사가 없어요.</p>
          <p className="hint">관리자가 기출문제를 업로드하면 여기에 표시돼요.</p>
        </div>
      ) : (
        <div className="round-grid">
          {rounds.map((r) => (
            <button
              key={`${r.exam_year}-${r.exam_round}`}
              className="round-card"
              onClick={() => navigate(`/exam/${r.exam_year}/${r.exam_round}`)}
            >
              <span className="round-year">{r.exam_year}년</span>
              <span className="round-num">{r.exam_round}회차</span>
              <span className="round-count">{r.problem_count}문제</span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
