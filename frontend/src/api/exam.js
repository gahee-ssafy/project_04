import client from './client'

// 공무원 기출
export const getExamRounds   = () => client.get('/exam/rounds')
export const getExamProblems = (year, round) => client.get(`/exam/rounds/${year}/${round}`)
export const submitExam      = (data) => client.post('/exam/submit', data)

// NCS
export const getNcsList       = () => client.get('/exam/ncs')
export const getNcsProblems   = (agency, year, domain) =>
  client.get(`/exam/ncs/${encodeURIComponent(agency)}/${year}/${encodeURIComponent(domain)}`)
export const submitNcs        = (data) => client.post('/exam/ncs/submit', data)

export const getSolution = (problemId) => client.get(`/ai/solution/${problemId}`)
