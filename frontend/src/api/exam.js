import client from './client'

export const getExamRounds = () => client.get('/exam/rounds')
export const getExamProblems = (year, round) => client.get(`/exam/rounds/${year}/${round}`)
export const submitExam = (data) => client.post('/exam/submit', data)
export const getSolution = (problemId) => client.get(`/ai/solution/${problemId}`)
