import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { login } from '../api/auth'

export default function LoginPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    try {
      await login(username, password)
      navigate('/')
    } catch {
      setError('아이디 또는 비밀번호가 틀렸어요.')
    }
  }

  return (
    <div className="auth-container">
      <h2>로그인</h2>
      <form onSubmit={handleSubmit}>
        <input
          placeholder="아이디"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          autoFocus
        />
        <input
          type="password"
          placeholder="비밀번호"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        {error && <p className="error">{error}</p>}
        <button type="submit">로그인</button>
      </form>
      <p>계정이 없으신가요? <Link to="/register">회원가입</Link></p>
    </div>
  )
}
