<template>
  <Teleport to="body">
    <div v-if="store.showModal" class="modal-overlay" @click.self="close">
      <div class="modal-container">
        <div class="modal-header">
          <h3 class="modal-title">AI 录音现场</h3>
          <button class="modal-close" @click="close">&times;</button>
        </div>

        <div class="modal-body">
          <!-- 录音按钮 -->
          <div class="record-area">
            <button
              :class="['btn-record-big', recording ? 'is-recording' : '', uploading ? 'is-uploading' : '', store.isProcessing ? 'is-thinking' : '']"
              :disabled="uploading || store.isProcessing"
              @click="toggleRecording"
            >
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
                <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
                <line x1="12" y1="19" x2="12" y2="23"/>
                <line x1="8" y1="23" x2="16" y2="23"/>
              </svg>
              <span>{{ recording ? '停止录音' : uploading ? '转写中...' : store.isProcessing ? 'AI 分析中...' : '点击开始录音' }}</span>
            </button>
            <span v-if="recording" class="record-timer">{{ recordingTime }}s</span>
          </div>

          <!-- 转录文字 -->
          <div v-if="transcriptText" class="transcript-box">
            <div class="transcript-header">
              <span>📝 识别文字</span>
              <button class="btn-text" @click="transcriptText = ''">清除</button>
            </div>
            <div class="transcript-body">{{ transcriptText }}</div>
          </div>

          <!-- 手动输入 -->
          <div class="manual-area">
            <label class="field-label">或手动输入诊疗对话</label>
            <textarea v-model="manualText" class="input" rows="3" placeholder="粘贴医生-主人对话..."></textarea>
            <button
              class="btn btn-primary btn-sm"
              style="margin-top:6px"
              @click="parseManual"
              :disabled="store.isProcessing || !manualText.trim()"
            >
              {{ store.isProcessing ? 'AI 解析中...' : '提交文本 AI 解析' }}
            </button>
          </div>

          <!-- AI 解析结果卡片 -->
          <div v-if="resultCards.length" class="result-cards">
            <h4 class="section-label">AI 解析结果 — 可快速跳转页面并自动填充</h4>
            <div class="cards-grid">
              <div v-if="hasPetCard" class="result-card">
                <div class="card-icon">🐕</div>
                <div class="card-info">
                  <strong>宠物信息</strong>
                  <span v-if="petName">{{ petName }} | {{ petSpecies || '' }}</span>
                </div>
                <button class="btn btn-outline btn-xs" @click="goFill('pets')">去填宠物</button>
              </div>
              <div v-if="hasMedicalCard" class="result-card">
                <div class="card-icon">🏥</div>
                <div class="card-info">
                  <strong>诊疗记录</strong>
                  <span v-if="medDiagnosis">诊断: {{ medDiagnosis }}</span>
                </div>
                <button class="btn btn-outline btn-xs" @click="goFill('medical')">去填诊疗</button>
              </div>
              <div v-if="hasVaccineCard" class="result-card">
                <div class="card-icon">💉</div>
                <div class="card-info">
                  <strong>疫苗接种</strong>
                  <span v-if="vaccineName">{{ vaccineName }}</span>
                </div>
                <button class="btn btn-outline btn-xs" @click="goFill('vaccines')">去填疫苗</button>
              </div>
              <div v-if="hasSOAPCard" class="result-card">
                <div class="card-icon">📋</div>
                <div class="card-info">
                  <strong>SOAP 病历</strong>
                  <span>已生成完整 SOAP</span>
                </div>
                <button class="btn btn-outline btn-xs" @click="goFill('soap')">打开 SOAP</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAiVoiceStore } from '../stores/aiVoice'
import { aiTranscribe, aiTranscribeAndFill } from '../api'

const store = useAiVoiceStore()
const router = useRouter()

const recording = ref(false)
const uploading = ref(false)
const recordingTime = ref(0)
const transcriptText = ref('')
const manualText = ref('')
const parseResult = ref(null)

let mediaRecorder = null
let audioChunks = []
let recordingTimer = null

const resultCards = computed(() => {
  if (!parseResult.value) return []
  const r = parseResult.value
  const cards = []
  if (r.petInfo && (r.petInfo.name || r.petInfo.species)) cards.push('pet')
  if (r.medicalInfo && (r.medicalInfo.diagnosis || r.medicalInfo.symptoms)) cards.push('medical')
  if (r.vaccineInfo && r.vaccineInfo.vaccine_name) cards.push('vaccine')
  if (r.soapData) cards.push('soap')
  if (!cards.length && (r.petInfo || r.medicalInfo || r.vaccineInfo || r.soapData)) {
    return ['pet', 'medical', 'vaccine', 'soap'].filter(k => r[k + 'Info'] || (k === 'soap' && r.soapData))
  }
  return cards
})

const hasPetCard = computed(() => resultCards.value.includes('pet'))
const hasMedicalCard = computed(() => resultCards.value.includes('medical'))
const hasVaccineCard = computed(() => resultCards.value.includes('vaccine'))
const hasSOAPCard = computed(() => resultCards.value.includes('soap'))

const petName = computed(() => parseResult.value?.petInfo?.name || parseResult.value?.petInfo?.pet_name || '')
const petSpecies = computed(() => parseResult.value?.petInfo?.species || parseResult.value?.petInfo?.pet_species || '')
const medDiagnosis = computed(() => parseResult.value?.medicalInfo?.diagnosis || parseResult.value?.medicalInfo?.disease || '')
const vaccineName = computed(() => parseResult.value?.vaccineInfo?.vaccine_name || '')

function close() {
  store.showModal = false
}

function goFill(page) {
  store.setResult(parseResult.value || { text: transcriptText.value })
  store.showModal = false
  router.push('/' + page)
}

async function toggleRecording() {
  if (recording.value) { stopRecording(); return }
  startRecording()
}

async function startRecording() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    audioChunks = []
    mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' })
    mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0) audioChunks.push(e.data) }
    mediaRecorder.onstop = async () => {
      stream.getTracks().forEach(t => t.stop())
      if (audioChunks.length === 0) { recording.value = false; return }
      await doTranscribeAndParse(new Blob(audioChunks, { type: 'audio/webm' }))
    }
    mediaRecorder.start(250)
    recording.value = true
    recordingTime.value = 0
    recordingTimer = setInterval(() => { recordingTime.value++ }, 1000)
  } catch (e) {
    alert('无法访问麦克风，请检查权限')
  }
}

function stopRecording() {
  if (recordingTimer) { clearInterval(recordingTimer); recordingTimer = null }
  if (mediaRecorder && mediaRecorder.state !== 'inactive') mediaRecorder.stop()
  recording.value = false
}

async function doTranscribeAndParse(audioBlob) {
  uploading.value = true
  try {
    const fd = new FormData()
    fd.append('audio', audioBlob, 'recording.webm')
    const res = await aiTranscribeAndFill(fd)
    const data = res.data || {}
    transcriptText.value = data.text || ''
    parseResult.value = data
    store.setResult(data)
  } catch (e) {
    // fallback: just transcribe without fill
    try {
      const res = await aiTranscribe(audioBlob)
      transcriptText.value = (res.data || {}).text || ''
    } catch (e2) {
      alert('语音识别失败，请检查讯飞 API 配置')
    }
  } finally {
    uploading.value = false
  }
}

async function parseManual() {
  if (!manualText.value.trim()) return
  store.isProcessing = true
  try {
    const { default: api } = await import('../api')
    const res = await api.soapFromTranscript({ transcript: manualText.value, species: '狗' })
    const data = res.data || {}
    transcriptText.value = manualText.value
    
    // Build structured parse result from SOAP response
    const soap = data.soap || {}
    const reasoning = data.reasoning || {}
    const diag = reasoning.differential_list?.[0]
    parseResult.value = {
      text: manualText.value,
      petInfo: { name: '', species: '狗' },
      medicalInfo: {
        symptoms: soap.subjective || '',
        diagnosis: soap.assessment || reasoning.assessment || (diag?.disease || ''),
        treatment: soap.plan || reasoning.plan || '',
      },
      vaccineInfo: null,
      soapData: soap,
      summary: data.summary || '',
    }
    store.setResult(parseResult.value)
  } catch (e) {
    alert('AI 解析失败: ' + (e.response?.data?.error || e.message))
  } finally {
    store.isProcessing = false
  }
}

onUnmounted(() => {
  if (recordingTimer) clearInterval(recordingTimer)
  if (mediaRecorder && mediaRecorder.state !== 'inactive') mediaRecorder.stop()
})
</script>

<style scoped>
.modal-overlay {
  position: fixed; inset: 0; z-index: 9999;
  background: rgba(0, 0, 0, 0.5);
  display: flex; align-items: center; justify-content: center;
  animation: fadeIn 0.2s;
}
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }

.modal-container {
  width: 560px; max-height: 90vh;
  background: #fff; border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0,0,0,0.3);
  display: flex; flex-direction: column;
  overflow: hidden;
  animation: slideUp 0.25s;
}
@keyframes slideUp { from { transform: translateY(40px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }

.modal-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 16px 24px; border-bottom: 1px solid #e5e7eb;
}
.modal-title { font-size: 17px; font-weight: 700; color: var(--color-text); }
.modal-close {
  width: 32px; height: 32px; border-radius: 50%;
  border: none; background: #f3f4f6;
  font-size: 20px; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
}
.modal-close:hover { background: #e5e7eb; }

.modal-body { padding: 20px 24px 24px; overflow-y: auto; }

.record-area { display: flex; align-items: center; justify-content: center; gap: 16px; margin-bottom: 16px; }

.btn-record-big {
  display: inline-flex; align-items: center; gap: 10px;
  padding: 14px 32px; border: none; border-radius: 32px;
  font-size: 15px; font-weight: 600; color: #fff; cursor: pointer;
  background: linear-gradient(135deg, #3b82f6, #6366f1);
  box-shadow: 0 4px 16px rgba(59, 130, 246, 0.3);
  transition: all 0.2s;
}
.btn-record-big:hover { transform: translateY(-1px); box-shadow: 0 6px 20px rgba(59, 130, 246, 0.4); }
.btn-record-big:disabled { opacity: 0.7; cursor: not-allowed; }
.btn-record-big.is-recording { background: linear-gradient(135deg, #ef4444, #dc2626); animation: pulse-rec 1.2s infinite; }
.btn-record-big.is-uploading { background: linear-gradient(135deg, #f59e0b, #d97706); }
.btn-record-big.is-thinking { background: linear-gradient(135deg, #10b981, #059669); }
@keyframes pulse-rec { 0%,100% { box-shadow: 0 0 0 0 rgba(239,68,68,0.4) } 50% { box-shadow: 0 0 0 16px rgba(239,68,68,0) } }

.record-timer { font-size: 16px; font-weight: 700; color: #ef4444; }

.transcript-box {
  margin-bottom: 16px; background: #f0f9ff;
  border: 1px solid #bae6fd; border-radius: 8px; overflow: hidden;
}
.transcript-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 6px 12px; background: #e0f2fe;
  font-size: 13px; font-weight: 600; color: #0369a1;
}
.btn-text { font-size: 12px; color: #0284c7; background: none; border: none; cursor: pointer; text-decoration: underline; }
.transcript-body { padding: 10px 12px; font-size: 14px; line-height: 1.6; white-space: pre-wrap; max-height: 150px; overflow-y: auto; }

.manual-area { margin-bottom: 16px; }
.field-label { font-size: 12px; font-weight: 600; color: var(--color-text-secondary); display: block; margin-bottom: 4px; }

.section-label { font-size: 13px; font-weight: 600; color: var(--color-text-secondary); margin-bottom: 10px; }
.cards-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }

.result-card {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 14px; background: #f9fafb;
  border: 1px solid #e5e7eb; border-radius: 10px;
}
.card-icon { font-size: 22px; }
.card-info { flex: 1; min-width: 0; }
.card-info strong { font-size: 13px; display: block; }
.card-info span { font-size: 11px; color: var(--color-text-secondary); }
.btn-xs { font-size: 11px; padding: 3px 10px; white-space: nowrap; }
</style>
