import axios from 'axios'

const api = axios.create({
  baseURL: 'http://localhost:5000/api', // ou apenas '/api' se usar o proxy do Vite
  timeout: 5000
})

export default api