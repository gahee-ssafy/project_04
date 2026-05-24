import client from './client'

export const getQuiz          = ()     => client.get('/quiz')
export const getRelatedProblem = (text) => client.post('/quiz/related', { text })
