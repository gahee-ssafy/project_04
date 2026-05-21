import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { register } from '../api/auth'

export default function RegisterPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [password2, setPassword2] = useState('')
  const [error, setError] = useState('')
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    if (password !== password2) return setError('비밀번호가 일치하지 않아요.')
    try {
      await register(username, password)
      navigate('/login')
    } catch {
      setError('이미 존재하는 아이디예요.')
    }
  }

  return (
    <div className="auth-container">
      <h2>회원가입</h2>
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
        <input
          type="password"
          placeholder="비밀번호 확인"
          value={password2}
          onChange={(e) => setPassword2(e.target.value)}
        />
        {error && <p className="error">{error}</p>}
        <button type="submit">회원가입</button>
      </form>
      <p>이미 계정이 있으신가요? <Link to="/login">로그인</Link></p>
    </div>
  )
}
