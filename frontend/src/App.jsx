import { BrowserRouter, Routes, Route, Navigate, Link, useLocation, useNavigate } from 'react-router-dom'
import { isLoggedIn, logout, getUsername } from './api/auth'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import NotebookPage from './pages/NotebookPage'
import ExamListPage from './pages/ExamListPage'
import ExamPage from './pages/ExamPage'
import './App.css'

function PrivateRoute({ children }) {
  return isLoggedIn() ? children : <Navigate to="/login" replace />
}

function Nav() {
  if (!isLoggedIn()) return null
  return (
    <nav className="navbar">
      <Link to="/" className="nav-logo">AI 경제학 튜터</Link>
      <div className="nav-links">
        <span className="nav-user">{getUsername()}</span>
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
      </div>
      {tab === 'exam' ? <ExamListPage /> : <NotebookPage />}
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
          <Route path="/exam/:year/:round" element={<PrivateRoute><ExamPage /></PrivateRoute>} />
          <Route path="/" element={<PrivateRoute><HomePage /></PrivateRoute>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </BrowserRouter>
  )
}
