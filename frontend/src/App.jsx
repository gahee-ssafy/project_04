import { BrowserRouter, Routes, Route, Navigate, Link } from 'react-router-dom'
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
      <Link to="/" className="nav-logo">📈 AI 경제학 튜터</Link>
      <div className="nav-links">
        <Link to="/exam">모의고사</Link>
        <Link to="/notebook">오답노트</Link>
        <span className="nav-user">{getUsername()}</span>
        <button onClick={() => { logout(); window.location.href = '/login' }}>
          로그아웃
        </button>
      </div>
    </nav>
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
          <Route path="/notebook" element={<PrivateRoute><NotebookPage /></PrivateRoute>} />
          <Route path="/exam" element={<PrivateRoute><ExamListPage /></PrivateRoute>} />
          <Route path="/exam/:year/:round" element={<PrivateRoute><ExamPage /></PrivateRoute>} />
          <Route path="/" element={<PrivateRoute><ExamListPage /></PrivateRoute>} />
        </Routes>
      </main>
    </BrowserRouter>
  )
}
