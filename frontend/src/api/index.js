import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 15000,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response && err.response.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

export function login(username, password) {
  return api.post('/auth/login', { username, password })
}

export function register(username, password, role) {
  return api.post('/auth/register', { username, password, role })
}

export function getPets(params) {
  return api.get('/pets', { params })
}

export function getPet(id) {
  return api.get(`/pets/${id}`)
}

export function createPet(data) {
  return api.post('/pets', data)
}

export function updatePet(id, data) {
  return api.put(`/pets/${id}`, data)
}

export function deletePet(id) {
  return api.delete(`/pets/${id}`)
}

export function getPetStats() {
  return api.get('/pets/stats')
}

export function getMedicalRecords(params) {
  return api.get('/medical-records', { params })
}

export function createMedicalRecord(data) {
  return api.post('/medical-records', data)
}

export function updateMedicalRecord(id, data) {
  return api.put(`/medical-records/${id}`, data)
}

export function deleteMedicalRecord(id) {
  return api.delete(`/medical-records/${id}`)
}

export function getVaccinations(params) {
  return api.get('/vaccinations', { params })
}

export function createVaccination(data) {
  return api.post('/vaccinations', data)
}

export function deleteVaccination(id) {
  return api.delete(`/vaccinations/${id}`)
}

export function getDrugs(params) {
  return api.get('/drugs', { params })
}

export function createDrug(data) {
  return api.post('/drugs', data)
}

export function updateDrug(id, data) {
  return api.put(`/drugs/${id}`, data)
}

export function deleteDrug(id) {
  return api.delete(`/drugs/${id}`)
}

export function drugStockIn(id, quantity) {
  return api.post(`/drugs/${id}/stock-in`, { quantity })
}

export function drugStockOut(id, quantity) {
  return api.post(`/drugs/${id}/stock-out`, { quantity })
}

export function getStaff(role) {
  return api.get(`/admin/${role}`)
}

export function createStaff(role, data) {
  return api.post(`/admin/${role}`, data)
}

export function deleteStaff(role, id) {
  return api.delete(`/admin/${role}/${id}`)
}

export function aiParseRecord(text) {
  return api.post('/ai/parse-record', { text })
}

export function aiAutoFill(text, petId) {
  return api.post('/ai/auto-fill', { text, pet_id: petId })
}

export function aiDiseaseSuggest(symptoms) {
  return api.get('/ai/disease-suggest', { params: { symptoms } })
}

export function aiEngineStatus() {
  return api.get('/ai/engine-status')
}

export function aiGetTemplates() {
  return api.get('/ai/templates')
}

export function aiGetTemplateDetail(templateId) {
  return api.get(`/ai/templates/${templateId}`)
}

export function aiTranscribeAndFill(payload) {
  if (payload instanceof FormData) {
    return api.post('/ai/transcribe-and-fill', payload, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 30000,
    })
  }
  return api.post('/ai/transcribe-and-fill', payload, { timeout: 30000 })
}

export function aiPetSummary(petId) {
  return api.get('/ai/pet-summary', { params: { pet_id: petId } })
}

export function aiTranscribe(audioBlob) {
  const formData = new FormData()
  formData.append('audio', audioBlob, 'recording.wav')
  return api.post('/ai/transcribe', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 180000,
  })
}

export function aiGenerateTreatment({ symptoms, diagnosis, species }) {
  return api.post('/ai/generate-treatment', { symptoms, diagnosis, species })
}

export function soapFromTranscript(data) {
  return api.post('/soap/from-transcript', data, { timeout: 120000 })
}

export function soapFromTranscriptAudio(audioBlob) {
  const formData = new FormData()
  formData.append('audio', audioBlob, 'recording.webm')
  return api.post('/soap/from-transcript-audio', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 300000,
  })
}

export function soapGet(recordId) {
  return api.get(`/soap/${recordId}`)
}

export function soapUpdate(recordId, data) {
  return api.put(`/soap/${recordId}`, data)
}

export function soapReasoning(recordId) {
  return api.post(`/soap/${recordId}/reasoning`, {}, { timeout: 60000 })
}

export function soapClientComm(recordId) {
  return api.post(`/soap/${recordId}/client`, {}, { timeout: 30000 })
}

export default api
