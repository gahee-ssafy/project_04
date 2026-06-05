import axios from 'axios'

const isProd = !['localhost', '127.0.0.1'].includes(window.location.hostname)
const client = axios.create({
  baseURL: isProd
    ? 'https://project04-production.up.railway.app'
    : `http://${window.location.hostname}:8000`,
})

// 요청마다 토큰 자동 첨부
client.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 인증 만료 시 로그인 페이지로
client.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('username')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

export default client
