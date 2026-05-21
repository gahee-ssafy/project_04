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
