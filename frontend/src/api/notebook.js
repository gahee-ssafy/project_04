import client from './client'

export const getNotebook = () => client.get('/notebook')

export const addNotebook = (data) => client.post('/notebook', data)

export const updateNotebook = (sessionId, data) =>
  client.put(`/notebook/${sessionId}`, data)

export const deleteNotebook = (sessionId) =>
  client.delete(`/notebook/${sessionId}`)

export const saveMemo = (sessionId, memo) =>
  client.put(`/notebook/${sessionId}/memo`, { memo })

export const debate = (problem, solution, history, userMsg) =>
  client.post('/notebook/debate', {
    problem,
    solution,
    history,
    user_msg: userMsg,
  })
