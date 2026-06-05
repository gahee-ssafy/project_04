import client from './client'

export const getQuiz            = ()                         => client.get('/quiz')
export const saveQuizAttempt    = (question_id, is_correct)  => client.post('/quiz/attempt', { question_id, is_correct })
export const getRelatedProblem  = (text)                     => client.post('/quiz/related', { text })
