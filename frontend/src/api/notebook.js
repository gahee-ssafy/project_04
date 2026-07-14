import client from './client'

export const getNotebook = () => client.get('/notebook')

export const addNotebook = (data) => client.post('/notebook', data)

export const updateNotebook = (sessionId, data) =>
  client.put(`/notebook/${sessionId}`, data)

export const deleteNotebook = (sessionId) =>
  client.delete(`/notebook/${sessionId}`)

export const saveMemo = (sessionId, memo) =>
  client.put(`/notebook/${sessionId}/memo`, { memo })

export const getNotebookChatHistory = (sessionId, mode = 'teacher') =>
  client.get(`/ai/notebook-chat/${sessionId}`, { params: { mode } })

export const notebookChat = (sessionId, question, memo, solution, userMessage = '', imageData = null) =>
  client.post('/ai/notebook-chat', {
    session_id: sessionId,
    question,
    memo,
    solution,
    user_message: userMessage,
    image_data: imageData || '',
    image_mime: 'image/png',
  })
