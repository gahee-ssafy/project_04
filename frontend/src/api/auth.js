import client from './client'

export const register = (username, password) =>
  client.post('/auth/register', { username, password })

export const login = async (username, password) => {
  const res = await client.post('/auth/login', { username, password })
  localStorage.setItem('token', res.data.access_token)
  localStorage.setItem('username', res.data.username)
  return res.data
}

export const logout = () => {
  localStorage.removeItem('token')
  localStorage.removeItem('username')
}

export const getUsername = () => localStorage.getItem('username')
export const isLoggedIn = () => !!localStorage.getItem('token')

export const getMyCredits = () => client.get('/auth/me').then(r => r.data.credits)

// 크레딧 로컬 캐시
export const getCachedCredits = () => {
  const v = localStorage.getItem('credits')
  return v !== null ? parseInt(v) : null
}
export const setCachedCredits = (n) => localStorage.setItem('credits', String(n))

// AI 응답에서 크레딧 업데이트 트리거 (커스텀 이벤트)
export const dispatchCreditsUpdate = (n) => {
  setCachedCredits(n)
  window.dispatchEvent(new CustomEvent('credits-update', { detail: n }))
}
