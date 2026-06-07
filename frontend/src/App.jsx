import { BrowserRouter, Routes, Route, Navigate, Link, useLocation, useNavigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { isLoggedIn, logout, getUsername, getMyCredits, getCachedCredits, setCachedCredits } from './api/auth'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import NotebookPage from './pages/NotebookPage'
import ExamListPage from './pages/ExamListPage'
import ExamPage from './pages/ExamPage'
import ReportPage from './pages/ReportPage'
import NotebookPrintPage from './pages/NotebookPrintPage'
import AdminPage from './pages/AdminPage'
import './App.css'

function PrivateRoute({ children }) {
  return isLoggedIn() ? children : <Navigate to="/login" replace />
}

function Nav() {
  const [credits, setCredits] = useState(getCachedCredits())

  useEffect(() => {
    if (isLoggedIn()) {
      getMyCredits().then(n => { setCredits(n); setCachedCredits(n) }).catch(() => {})
    }
    const handler = (e) => setCredits(e.detail)
    window.addEventListener('credits-update', handler)
    return () => window.removeEventListener('credits-update', handler)
  }, [])

  if (!isLoggedIn()) return null
  return (
    <nav className="navbar">
      <Link to="/" className="nav-logo">AI 경제학 튜터</Link>
      <div className="nav-links">
        <span className="nav-user">{getUsername()}</span>
        {credits !== null && (
          <span style={{
            fontSize: '0.8rem',
            color: credits <= 5 ? '#E53E3E' : 'var(--text-3)',
            fontWeight: credits <= 5 ? 700 : 400,
          }}>
            💳 {credits}크레딧
          </span>
        )}
        <Link to="/admin" style={{ fontSize: '0.82rem', color: 'var(--text-3)' }}>관리자</Link>
        <button onClick={() => { logout(); window.location.href = '/login' }}>
          로그아웃
        </button>
      </div>
    </nav>
  )
}

function HomePage() {
  const location = useLocation()
  const navigate = useNavigate()
  const tab = new URLSearchParams(location.search).get('tab') || 'exam'

  return (
    <div>
      <div className="home-tabs">
        <button
          className={`home-tab ${tab === 'exam' ? 'active' : ''}`}
          onClick={() => navigate('/?tab=exam')}
        >
          모의고사
        </button>
        <button
          className={`home-tab ${tab === 'notebook' ? 'active' : ''}`}
          onClick={() => navigate('/?tab=notebook')}
        >
          오답노트
        </button>
        <button
          className={`home-tab ${tab === 'report' ? 'active' : ''}`}
          onClick={() => navigate('/?tab=report')}
        >
          학습일지
        </button>
      </div>
      {tab === 'exam' && <ExamListPage />}
      {tab === 'notebook' && <NotebookPage />}
      {tab === 'report' && <ReportPage />}
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Nav />
      <main>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/exam/civil/:year/:round" element={<PrivateRoute><ExamPage /></PrivateRoute>} />
          <Route path="/exam/ncs/:agency/:year/:domain" element={<PrivateRoute><ExamPage /></PrivateRoute>} />
          <Route path="/exam/:year/:round" element={<PrivateRoute><ExamPage /></PrivateRoute>} />
          <Route path="/notebook/print/civil/:subject" element={<PrivateRoute><NotebookPrintPage /></PrivateRoute>} />
          <Route path="/notebook/print/ncs/:agency" element={<PrivateRoute><NotebookPrintPage /></PrivateRoute>} />
          <Route path="/notebook/print/:group" element={<PrivateRoute><NotebookPrintPage /></PrivateRoute>} />
          <Route path="/admin" element={<PrivateRoute><AdminPage /></PrivateRoute>} />
          <Route path="/" element={<PrivateRoute><HomePage /></PrivateRoute>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </BrowserRouter>
  )
}
