<template>
  <div class="page ai-page">
    <div class="card">
      <div class="card-header">
        <span class="card-title">AI 语音工作台</span>
        <span class="badge" :class="engineOk ? 'badge-green' : 'badge-red'">
          {{ engineOk ? 'DeepSeek 已连接' : 'DeepSeek 未连接' }}
        </span>
      </div>

      <div class="ai-tabs">
        <button :class="['tab', aiTab === 'voice' ? 'tab-active' : '']" @click="aiTab = 'voice'">语音工作台</button>
        <button :class="['tab', aiTab === 'parse' ? 'tab-active' : '']" @click="aiTab = 'parse'">病历解析</button>
        <button :class="['tab', aiTab === 'suggest' ? 'tab-active' : '']" @click="aiTab = 'suggest'">疾病建议</button>
      </div>

      <div v-if="aiTab === 'voice'" class="voice-workspace">
        <div class="voice-center">
          <button
            :class="['btn-voice-record', recording ? 'is-recording' : '']"
            @click="startVoiceRecording"
            :disabled="aiBusy || uploading"
          >
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
              <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
              <line x1="12" y1="19" x2="12" y2="23"/>
              <line x1="8" y1="23" x2="16" y2="23"/>
            </svg>
          </button>
          <p class="voice-label">{{ uploading ? '正在上传录音并识别...' : recording ? '正在录音... 点击停止' : '点击开始录音' }}</p>
          <p v-if="!recording && !uploading && !voiceText" class="voice-desc">说出病情描述，AI 自动解析并引导跳转到对应模块</p>
          <p v-if="voiceText && !uploading" class="voice-result">{{ voiceText }}</p>
          <p v-if="uploading" class="voice-desc">语音识别中，请稍候...</p>
          <p v-if="aiBusy && !uploading" class="voice-desc">AI 正在分析...</p>
        </div>

        <div v-if="voiceResult" class="action-grid">
          <div v-if="voiceResult.pet_form" class="action-card">
            <h4>宠物信息已识别</h4>
            <p>{{ voiceResult.pet_form.name || '未知' }} / {{ voiceResult.pet_form.species || '未知' }} / {{ voiceResult.pet_form.owner_name || '未知主人' }}</p>
            <button class="btn btn-primary btn-sm" @click="jumpToPet">创建该宠物</button>
          </div>
          <div v-if="voiceResult.medical_form" class="action-card">
            <h4>诊疗信息已解析</h4>
            <p>诊断: {{ voiceResult.medical_form.diagnosis || '待填' }}</p>
            <p v-if="voiceResult.medical_form.treatment">治疗: {{ voiceResult.medical_form.treatment }}</p>
            <button class="btn btn-primary btn-sm" @click="jumpToMedical">创建诊疗记录</button>
          </div>
          <div v-if="voiceResult.vaccine_form" class="action-card">
            <h4>疫苗信息已识别</h4>
            <p>{{ voiceResult.vaccine_form.vaccine_name || '疫苗' }}</p>
            <button class="btn btn-primary btn-sm" @click="jumpToVaccine">创建接种记录</button>
          </div>
          <div v-if="!voiceResult.pet_form && !voiceResult.medical_form && !voiceResult.vaccine_form" class="action-card empty-card">
            <p>未能从语音中解析出有效信息，请重试或切换到"病历解析"标签手动输入。</p>
          </div>
        </div>
      </div>

      <div v-if="aiTab === 'parse'">
        <div class="parse-toolbar">
          <select v-model="selectedTemplate" class="input template-select" @change="loadTemplate">
            <option value="">-- 选择病历模板 --</option>
            <option v-for="t in templates" :key="t.id" :value="t.id">{{ t.name }}</option>
          </select>
          <VoiceInput v-model="parseText" size="sm" placeholder="语音录入病历" />
        </div>
        <div class="form-group">
          <textarea v-model="parseText" class="input" rows="6" placeholder="输入或语音录入病历文本..."></textarea>
        </div>
        <div class="ai-actions">
          <button class="btn btn-primary" @click="handleParse" :disabled="parsing">
            {{ parsing ? '解析中...' : 'AI 解析' }}
          </button>
        </div>

        <div v-if="parseResult" class="result-card">
          <div class="result-header">
            <span>解析结果</span>
            <span class="badge badge-blue">置信度: {{ parseResult.result?.diagnosis?.confidence || parseResult.result?.confidence || '-' }}%</span>
          </div>
          <div class="result-grid" v-if="parseResult.result">
            <div v-if="parseResult.result.pet_info">
              <strong>宠物信息</strong>
              <p>名称: {{ parseResult.result.pet_info.pet_name || '-' }}</p>
              <p>种类: {{ parseResult.result.pet_info.species || '-' }}</p>
              <p>品种: {{ parseResult.result.pet_info.breed || '-' }}</p>
              <p>主人: {{ parseResult.result.pet_info.owner_name || '-' }}</p>
            </div>
            <div v-if="parseResult.result.diagnosis">
              <strong>诊断</strong>
              <p>{{ parseResult.result.diagnosis.name || '-' }}</p>
            </div>
            <div v-if="parseResult.result.treatment">
              <strong>治疗方案</strong>
              <p>{{ parseResult.result.treatment.plan || '-' }}</p>
            </div>
            <div v-if="parseResult.result.vitals">
              <strong>体征</strong>
              <p>体重: {{ parseResult.result.vitals.weight_kg || '-' }} kg</p>
              <p>体温: {{ parseResult.result.vitals.temperature || '-' }} C</p>
            </div>
            <div v-if="parseResult.result.fee">
              <strong>费用</strong>
              <p>{{ parseResult.result.fee.fee_charged || 0 }} 元</p>
            </div>
          </div>
          <div v-if="parseResult.result?.summary" class="result-summary">{{ parseResult.result.summary }}</div>
        </div>
      </div>

      <div v-if="aiTab === 'suggest'">
        <div class="form-group">
          <label>输入症状（用逗号分隔多个症状）</label>
          <div style="display: flex; align-items: center; gap: 6px;">
            <input v-model="symptomsText" class="input" style="flex:1;" placeholder="如：呕吐, 腹泻, 食欲不振" />
            <VoiceInput v-model="symptomsText" size="sm" placeholder="语音输入症状" />
          </div>
        </div>
        <div class="ai-actions">
          <button class="btn btn-primary" @click="handleSuggest" :disabled="suggesting">
            {{ suggesting ? '查询中...' : '查询建议' }}
          </button>
        </div>

        <div v-if="suggestResult" class="result-card">
          <div class="result-header"><span>疾病建议</span></div>
          <div v-if="suggestResult.suggestions?.length" class="suggest-list">
            <div v-for="(s, i) in suggestResult.suggestions" :key="i" class="suggest-item">
              <div class="suggest-top">
                <span class="suggest-name">{{ s.disease }}</span>
                <span class="badge badge-blue">{{ s.confidence }}%</span>
              </div>
              <p class="suggest-desc" v-if="s.description">{{ s.description }}</p>
            </div>
          </div>
          <div v-else class="empty-state">暂无匹配结果</div>
        </div>
      </div>
    </div>

    <div v-if="toast.show" :class="['toast', 'toast-' + toast.type]">{{ toast.msg }}</div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  aiParseRecord, aiDiseaseSuggest, aiEngineStatus, aiGetTemplates, aiGetTemplateDetail, aiTranscribeAndFill, aiTranscribe,
} from '../api'
import VoiceInput from '../components/VoiceInput.vue'

const router = useRouter()

const aiTab = ref('voice')
const engineOk = ref(false)
const toast = reactive({ show: false, msg: '', type: 'success' })

// 语音工作台
const recording = ref(false)
const uploading = ref(false)
const voiceText = ref('')
const voiceResult = ref(null)
const aiBusy = ref(false)

let mediaRecorder = null
let audioChunks = []

// 病历解析
const parseText = ref('')
const parseResult = ref(null)
const parsing = ref(false)

// 模板
const templates = ref([])
const selectedTemplate = ref('')

// 疾病建议
const symptomsText = ref('')
const suggestResult = ref(null)
const suggesting = ref(false)

function showToast(msg, type = 'success') {
  toast.msg = msg; toast.type = type; toast.show = true
  setTimeout(() => { toast.show = false }, 3000)
}

// ============ 语音工作台 ============

async function startVoiceRecording() {
  if (recording.value) {
    stopRecording()
    return
  }

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    audioChunks = []
    mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' })

    mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        audioChunks.push(event.data)
      }
    }

    mediaRecorder.onstop = async () => {
      stream.getTracks().forEach((t) => t.stop())
      if (audioChunks.length === 0) return

      const audioBlob = new Blob(audioChunks, { type: 'audio/webm' })
      uploading.value = true

      try {
        const res = await aiTranscribe(audioBlob)
        voiceText.value = res.data?.text || ''
        uploading.value = false

        if (voiceText.value) {
          await processVoiceText(voiceText.value)
        } else {
          showToast('未识别到语音内容', 'error')
        }
      } catch (e) {
        showToast('语音识别失败: ' + (e.response?.data?.error || e.message || '网络错误'), 'error')
        uploading.value = false
      }
    }

    mediaRecorder.start(250)
    recording.value = true
  } catch (e) {
    showToast('无法访问麦克风，请检查权限', 'error')
  }
}

function stopRecording() {
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop()
  }
  recording.value = false
}

async function processVoiceText(text) {
  if (!text || !text.trim()) return

  aiBusy.value = true
  try {
    const res = await aiTranscribeAndFill({ text: text.trim() })
    voiceResult.value = res.data
  } catch (e) {
    showToast('AI 解析失败，请重试', 'error')
  } finally {
    aiBusy.value = false
  }
}

function jumpToPet() {
  const pf = voiceResult.value?.pet_form
  if (pf) {
    localStorage.setItem('ai_prefill_pet', JSON.stringify(pf))
  }
  router.push('/pets')
}

function jumpToMedical() {
  const mf = voiceResult.value?.medical_form
  if (mf) {
    localStorage.setItem('ai_prefill_medical', JSON.stringify(mf))
  }
  router.push('/medical')
}

function jumpToVaccine() {
  const vf = voiceResult.value?.vaccine_form
  if (vf) {
    localStorage.setItem('ai_prefill_vaccine', JSON.stringify(vf))
  }
  router.push('/vaccines')
}

// ============ 病历解析 ============

async function loadTemplate() {
  if (!selectedTemplate.value) return
  try {
    const res = await aiGetTemplateDetail(selectedTemplate.value)
    const content = res.data?.content
    if (content) {
      parseText.value = content
    }
  } catch (e) {
    showToast('模板加载失败', 'error')
  }
}

async function handleParse() {
  if (!parseText.value.trim()) { showToast('请输入病历文本', 'error'); return }
  parsing.value = true
  try {
    const res = await aiParseRecord(parseText.value)
    parseResult.value = res.data
  } catch (e) {
    showToast(e.response?.data?.error || '解析失败', 'error')
  } finally {
    parsing.value = false
  }
}

// ============ 疾病建议 ============

async function handleSuggest() {
  if (!symptomsText.value.trim()) { showToast('请输入症状', 'error'); return }
  suggesting.value = true
  try {
    const res = await aiDiseaseSuggest(symptomsText.value)
    suggestResult.value = res.data
  } catch (e) {
    showToast(e.response?.data?.error || '查询失败', 'error')
  } finally {
    suggesting.value = false
  }
}

onMounted(async () => {
  try {
    const [statusRes, tmplRes] = await Promise.all([
      aiEngineStatus(),
      aiGetTemplates(),
    ])
    engineOk.value = statusRes.data?.deepseek_configured || false
    templates.value = tmplRes.data?.templates || []
  } catch (e) {
    // 引擎状态获取失败，忽略
  }
})
</script>

<style scoped>
.ai-page { max-width: 800px; }

.ai-tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 20px;
}

.tab {
  padding: 6px 16px;
  background: #f8fafc;
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  font-size: 13px;
  color: var(--color-text-secondary);
  transition: all 0.15s;
  cursor: pointer;
}

.tab:hover { color: var(--color-primary); border-color: var(--color-primary); }
.tab-active { background: var(--color-primary); color: #fff; border-color: var(--color-primary); }
.tab-active:hover { color: #fff; }

.template-select {
  width: 200px;
}

.parse-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.ai-actions { margin-bottom: 16px; }

/* 语音工作台 */
.voice-workspace {
  padding: 8px 0;
}

.voice-center {
  text-align: center;
  padding: 24px 0;
}

.btn-voice-record {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  background: var(--color-primary);
  color: #fff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  box-shadow: 0 4px 14px rgba(37, 99, 235, 0.3);
  cursor: pointer;
  border: none;
}

.btn-voice-record:hover {
  transform: scale(1.05);
  box-shadow: 0 6px 20px rgba(37, 99, 235, 0.4);
}

.btn-voice-record:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-voice-record.is-recording {
  background: var(--color-danger);
  box-shadow: 0 4px 14px rgba(220, 38, 38, 0.4);
  animation: pulse-rec 1.2s infinite;
}

@keyframes pulse-rec {
  0%, 100% { box-shadow: 0 0 0 0 rgba(220, 38, 38, 0.4); }
  50% { box-shadow: 0 0 0 16px rgba(220, 38, 38, 0); }
}

.voice-label {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text);
  margin-top: 12px;
}

.voice-desc {
  font-size: 13px;
  color: var(--color-text-secondary);
  margin-top: 4px;
}

.voice-result {
  margin-top: 12px;
  padding: 12px 20px;
  background: #f0f9ff;
  border: 1px solid #bae6fd;
  border-radius: var(--radius);
  font-size: 14px;
  color: var(--color-text);
  text-align: left;
  display: inline-block;
  max-width: 500px;
  word-break: break-word;
}

.action-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-top: 16px;
}

.action-card {
  background: #f8fafc;
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 14px;
}

.action-card h4 {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 6px;
  color: var(--color-text);
}

.action-card p {
  font-size: 12px;
  color: var(--color-text-secondary);
  margin-bottom: 8px;
}

.action-card.empty-card {
  grid-column: 1 / -1;
  text-align: center;
}

.empty-card p {
  color: var(--color-text-light);
  margin-bottom: 0;
}

/* 结果卡片 */
.result-card {
  background: #f8fafc;
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 16px;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  font-weight: 600;
  font-size: 14px;
}

.result-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 12px;
}

.result-grid > div {
  background: #fff;
  border-radius: 6px;
  padding: 12px;
}

.result-grid strong {
  display: block;
  font-size: 11px;
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 4px;
}

.result-grid p { font-size: 13px; color: var(--color-text); margin-bottom: 2px; }

.result-summary {
  background: #fff;
  border-radius: 6px;
  padding: 12px;
  font-size: 13px;
  color: var(--color-text);
}

.suggest-list { display: flex; flex-direction: column; gap: 8px; }

.suggest-item {
  background: #fff;
  border-radius: 6px;
  padding: 12px;
}

.suggest-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.suggest-name { font-weight: 600; font-size: 14px; }
.suggest-desc { font-size: 13px; color: var(--color-text-secondary); }

@media (max-width: 768px) {
  .action-grid { grid-template-columns: 1fr; }
  .result-grid { grid-template-columns: 1fr; }
}
</style>
