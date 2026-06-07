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

// 인증 만료 / 크레딧 부족 처리
client.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('username')
      window.location.href = '/login'
    }
    if (err.response?.status === 402) {
      alert('크레딧이 부족해요. 관리자에게 충전을 요청하세요.')
    }
    return Promise.reject(err)
  }
)

export default client
