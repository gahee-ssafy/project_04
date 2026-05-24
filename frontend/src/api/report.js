import client from './client'

export const getReport        = () => client.get('/report')
export const regenerateReport = () => client.post('/report/regenerate')
