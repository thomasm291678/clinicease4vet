import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAiVoiceStore = defineStore('aiVoice', () => {
  const lastResult = ref(null)
  const transcript = ref('')
  const isProcessing = ref(false)
  const showModal = ref(false)

  function setResult(data) {
    lastResult.value = {
      transcript: data.text || data.transcript || '',
      petInfo: data.pet_form || data.pet_info || null,
      medicalInfo: data.medical_form || data.medical_info || null,
      vaccineInfo: data.vaccine_form || data.vaccine_info || null,
      soapData: data.soap || null,
      summary: data.summary || '',
      timestamp: Date.now(),
    }
    transcript.value = data.text || data.transcript || ''
  }

  function consumeResult() {
    const r = lastResult.value
    lastResult.value = null
    return r
  }

  function clear() {
    lastResult.value = null
    transcript.value = ''
    isProcessing.value = false
  }

  return { lastResult, transcript, isProcessing, showModal, setResult, consumeResult, clear }
})
