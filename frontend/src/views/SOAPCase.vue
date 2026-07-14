<template>
  <div class="page soap-page">
    <div class="card">
      <div class="card-header">
        <span class="card-title">SOAP 病历</span>
        <span v-if="recordData.id" class="case-id">病例编号: CN{{ String(recordData.id).padStart(4, '0') }}</span>
      </div>

      <!-- ========== 快捷工具栏 ========== -->
      <div class="soap-toolbar">
        <!-- 模板选择 -->
        <div class="toolbar-section">
          <label class="toolbar-label">病历模板</label>
          <div class="toolbar-row">
            <select v-model="selectedTemplate" class="input template-select" @change="onTemplateChange">
              <option value="">-- 选择常见病历模板 --</option>
              <option v-for="t in templates" :key="t.id" :value="t.id">{{ t.name }}</option>
            </select>
            <button class="btn btn-outline btn-sm" @click="applyTemplate" :disabled="!selectedTemplate || aiBusy">
              填充模板
            </button>
          </div>
        </div>

        <!-- 语音录入 -->
        <div class="toolbar-section voice-section">
          <label class="toolbar-label">语音识别录入</label>
          <button
            :class="['btn-voice-big', recording ? 'is-recording' : '', uploading ? 'is-uploading' : '', aiBusy && !recording && !uploading ? 'is-thinking' : '']"
            :disabled="uploading"
            @click="toggleRecording"
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
              <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
              <line x1="12" y1="19" x2="12" y2="23"/>
              <line x1="8" y1="23" x2="16" y2="23"/>
            </svg>
            <span class="voice-btn-text">{{ recording ? '停止录音' : uploading ? '转写中...' : aiBusy ? 'AI 分析中...' : '语音识别录入' }}</span>
          </button>
          <span v-if="recording" class="recording-timer">{{ recordingTime }}s</span>
          <button v-if="transcriptText && !aiBusy" class="btn btn-sm" style="margin-left:8px;" @click="reParseTranscript">
            重新解析
          </button>
        </div>
      </div>

      <!-- 转录文字展示 -->
      <div v-if="transcriptText" class="transcript-display">
        <div class="transcript-header">
          <span>📝 识别文字</span>
          <button class="btn-text" @click="transcriptText = ''">清除</button>
        </div>
        <div class="transcript-body">{{ transcriptText }}</div>
      </div>

      <!-- 状态提示 -->
      <div v-if="aiBusy && !recording && !uploading" class="ai-thinking-bar">
        <span class="thinking-dot"></span> DeepSeek AI 正在分析识别内容，自动填入 SOAP 表单中...
      </div>

      <div class="tabs">
        <button :class="['tab', { active: activeTab === 'soap' }]" @click="activeTab = 'soap'">SOAP病历</button>
        <button :class="['tab', { active: activeTab === 'reasoning' }]" @click="activeTab = 'reasoning'">临床推理</button>
      </div>

      <!-- SOAP Tab -->
      <div v-show="activeTab === 'soap'" class="tab-content">
        <div class="soap-grid">
          <div class="soap-box">
            <div class="soap-label">S 主观信息</div>
            <textarea v-model="soap.subjective" class="input soap-input" rows="6" placeholder="主诉、病程、病史、主人观察..."></textarea>
          </div>
          <div class="soap-box">
            <div class="soap-label">O 客观检查</div>
            <textarea v-model="soap.objective" class="input soap-input" rows="6" placeholder="体温、心率、触诊、听诊、实验室结果..."></textarea>
          </div>
          <div class="soap-box">
            <div class="soap-label">A 评估</div>
            <textarea v-model="soap.assessment" class="input soap-input" rows="5" placeholder="问题列表、鉴别诊断、临床判断..."></textarea>
          </div>
          <div class="soap-box">
            <div class="soap-label">P 计划</div>
            <textarea v-model="soap.plan" class="input soap-input" rows="5" placeholder="检查计划、治疗计划、护理建议、随访..."></textarea>
          </div>
        </div>

        <div class="client-comm-section">
          <h4 class="section-title">客户沟通与反馈</h4>
          <div class="comm-grid">
            <div class="comm-item">
              <label>主人观察</label>
              <input v-model="clientComm.observations" class="input" placeholder="主人观察到的情况" />
            </div>
            <div class="comm-item">
              <label>关切问题</label>
              <input v-model="clientComm.concerns" class="input" placeholder="主人的主要关切和问题" />
            </div>
            <div class="comm-item">
              <label>主人理解</label>
              <input v-model="clientComm.understanding" class="input" placeholder="主人当前理解程度" />
            </div>
            <div class="comm-item">
              <label>共同决策</label>
              <input v-model="clientComm.shared_decision" class="input" placeholder="共同决策和同意方案" />
            </div>
            <div class="comm-item">
              <label>随访计划</label>
              <input v-model="clientComm.follow_up" class="input" placeholder="随访计划" />
            </div>
          </div>
        </div>

        <div class="soap-actions">
          <button class="btn btn-primary" @click="saveSOAP" :disabled="saving">保存 SOAP</button>
        </div>

        <div v-if="summary" class="case-summary">
          <strong>病例摘要：</strong>{{ summary }}
        </div>
      </div>

      <!-- 临床推理 Tab -->
      <div v-show="activeTab === 'reasoning'" class="tab-content">
        <h4 class="section-title">问题清单</h4>
        <table class="data-table" v-if="problemList.length">
          <thead>
            <tr>
              <th>#</th><th>问题</th><th>支持证据</th><th>反对证据</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(p, i) in problemList" :key="i">
              <td>{{ p.rank || i + 1 }}</td>
              <td><strong>{{ p.problem }}</strong></td>
              <td class="evidence-cell">{{ p.evidence_for }}</td>
              <td class="evidence-cell">{{ p.evidence_against }}</td>
            </tr>
          </tbody>
        </table>
        <p v-else class="empty-hint">尚未生成问题清单</p>

        <h4 class="section-title">临床推理路径</h4>
        <div class="reasoning-path-box">{{ reasoningPath || '尚未生成' }}</div>

        <h4 class="section-title">鉴别诊断</h4>
        <table class="data-table" v-if="differentialList.length">
          <thead><tr><th>#</th><th>疾病</th><th>可能性</th><th>理由</th></tr></thead>
          <tbody>
            <tr v-for="(d, i) in differentialList" :key="i">
              <td>{{ d.rank || i + 1 }}</td><td>{{ d.disease }}</td>
              <td><span :class="'prob-tag prob-' + (d.probability || '中')">{{ d.probability }}</span></td>
              <td>{{ d.rationale }}</td>
            </tr>
          </tbody>
        </table>
        <div v-if="mustNotMiss.length" class="must-not-miss">
          <strong>Must Not Miss:</strong>
          <span v-for="m in mustNotMiss" :key="m" class="mnm-tag">{{ m }}</span>
        </div>

        <div class="three-col">
          <div>
            <h4 class="section-title">Missing Info</h4>
            <div class="info-box">{{ missingInfo || '暂无' }}</div>
          </div>
          <div>
            <h4 class="section-title">推荐检查</h4>
            <ul v-if="recommendedTests.length" class="test-list">
              <li v-for="t in recommendedTests" :key="t.test">
                <strong>{{ t.test }}</strong> — {{ t.rationale }}
              </li>
            </ul>
            <p v-else class="empty-hint">暂无</p>
          </div>
          <div>
            <h4 class="section-title">动态问诊建议</h4>
            <div class="info-box">{{ dynamicQuestions || '暂无' }}</div>
          </div>
        </div>

        <div class="soap-actions">
          <button class="btn btn-primary" @click="saveReasoning" :disabled="saving">保存推理</button>
          <button class="btn btn-outline" @click="regenerateReasoning" :disabled="generating">
            {{ generating ? 'AI 生成中...' : 'AI 重新生成推理' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 对话记录区（可折叠） -->
    <div class="card">
      <div class="card-header" @click="showTranscriptCard = !showTranscriptCard" style="cursor:pointer;">
        <span class="card-title">📋 对话记录 {{ showTranscriptCard ? '▼' : '▶' }}</span>
      </div>
      <div v-show="showTranscriptCard">
        <textarea v-model="manualTranscript" class="input" rows="6" placeholder="粘贴医生-主人对话记录，点击下方 AI 生成 SOAP..."></textarea>
        <div style="display:flex;gap:8px;margin-top:8px;">
          <button class="btn btn-primary btn-sm" @click="manualParseTranscript" :disabled="aiBusy || !manualTranscript">
            {{ aiBusy ? 'AI 分析中...' : '粘贴文本 → AI 生成 SOAP' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  soapFromTranscript, soapGet, soapUpdate, soapReasoning, soapClientComm,
  aiTranscribe, aiGetTemplates, aiGetTemplateDetail, aiTranscribeAndFill,
} from '../api'
import { useAiVoiceStore } from '../stores/aiVoice'

const aiVoice = useAiVoiceStore()

const route = useRoute()
const router = useRouter()

const recordId = ref(route.params.id ? Number(route.params.id) : null)
const recordData = ref({})
const activeTab = ref('soap')
const saving = ref(false)
const generating = ref(false)

const manualTranscript = ref('')
const transcriptText = ref('')
const summary = ref('')
const showTranscriptCard = ref(false)

const soap = reactive({ subjective: '', objective: '', assessment: '', plan: '' })
const clientComm = reactive({
  observations: '', concerns: '', understanding: '', shared_decision: '', follow_up: ''
})

const problemList = ref([])
const reasoningPath = ref('')
const differentialList = ref([])
const mustNotMiss = ref([])
const missingInfo = ref('')
const recommendedTests = ref([])
const dynamicQuestions = ref('')

// 模板相关
const templates = ref([])
const selectedTemplate = ref('')

// 录音相关
const recording = ref(false)
const uploading = ref(false)
const aiBusy = ref(false)
const recordingTime = ref(0)
let mediaRecorder = null
let audioChunks = []
let recordingTimer = null

function showToast(msg, type = '') {
  if (type === 'error') {
    alert(msg)
    return
  }
  const toast = document.getElementById('global-toast')
  if (toast) {
    toast.textContent = msg
    toast.className = 'global-toast'
    toast.style.display = 'block'
    setTimeout(() => { toast.style.display = 'none' }, 3000)
  }
}

// ==================== 模板 ====================

async function loadTemplates() {
  try {
    const res = await aiGetTemplates()
    templates.value = res.data?.templates || []
  } catch (e) {
    // ignore
  }
}

function onTemplateChange() {
  // just store selection, wait for explicit button click
}

async function applyTemplate() {
  if (!selectedTemplate.value) return
  try {
    const res = await aiGetTemplateDetail(selectedTemplate.value)
    const content = res.data?.content
    if (content) {
      transcriptText.value = content
      await parseTranscriptText(content)
      showToast('模板内容已填入SOAP字段')
    }
  } catch (e) {
    showToast('模板加载失败', 'error')
  }
}

// ==================== 录音 ====================

function toggleRecording() {
  if (recording.value) {
    stopRecording()
    return
  }
  startRecording()
}

async function startRecording() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    audioChunks = []
    mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' })

    mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) audioChunks.push(e.data)
    }

    mediaRecorder.onstop = async () => {
      stream.getTracks().forEach(t => t.stop())
      if (audioChunks.length === 0) {
        recording.value = false
        return
      }
      const audioBlob = new Blob(audioChunks, { type: 'audio/webm' })
      await transcribeAndFill(audioBlob)
    }

    mediaRecorder.start(250)
    recording.value = true
    recordingTime.value = 0
    recordingTimer = setInterval(() => { recordingTime.value++ }, 1000)
  } catch (e) {
    showToast('无法访问麦克风，请检查权限', 'error')
  }
}

function stopRecording() {
  if (recordingTimer) { clearInterval(recordingTimer); recordingTimer = null }
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop()
  }
  recording.value = false
}

async function transcribeAndFill(audioBlob) {
  uploading.value = true
  try {
    // 第一步：讯飞 ASR 语音转文字
    const asrRes = await aiTranscribe(audioBlob)
    const text = asrRes.data?.text || ''
    uploading.value = false

    if (!text) {
      showToast('未识别到语音内容，请重试', 'error')
      return
    }

    transcriptText.value = text

    // 第二步：DeepSeek 解析文字 → 填入 SOAP
    await parseTranscriptText(text)
  } catch (e) {
    uploading.value = false
    const errMsg = e.response?.data?.error || e.message || '语音识别失败'
    showToast(errMsg, 'error')
  }
}

async function parseTranscriptText(text) {
  if (!text || !text.trim()) return
  aiBusy.value = true
  try {
    const res = await soapFromTranscript({ transcript: text, species: '狗' })
    fillFromAI(res.data)
    showToast('AI 解析完成，SOAP 表单已填充')
  } catch (e) {
    showToast('AI 解析失败: ' + (e.response?.data?.error || e.message), 'error')
  } finally {
    aiBusy.value = false
  }
}

async function reParseTranscript() {
  if (!transcriptText.value) return
  await parseTranscriptText(transcriptText.value)
}

// ==================== 手动粘贴 ====================

async function manualParseTranscript() {
  if (!manualTranscript.value.trim()) return
  await parseTranscriptText(manualTranscript.value)
}

// ==================== SOAP 加载/保存 ====================

async function loadSOAP() {
  if (!recordId.value) return
  try {
    const res = await soapGet(recordId.value)
    const d = res.data
    recordData.value = d.record || {}
    if (d.soap) {
      soap.subjective = d.soap.subjective || ''
      soap.objective = d.soap.objective || ''
      soap.assessment = d.soap.assessment || d.record?.diagnosis || ''
      soap.plan = d.soap.plan || ''
    }
    if (d.reasoning) {
      problemList.value = d.reasoning.problem_list || []
      reasoningPath.value = d.reasoning.reasoning_path || ''
      differentialList.value = d.reasoning.differential_list || []
      mustNotMiss.value = d.reasoning.must_not_miss || []
      missingInfo.value = d.reasoning.missing_info || ''
      recommendedTests.value = d.reasoning.recommended_tests || []
      dynamicQuestions.value = d.reasoning.dynamic_questions || ''
      if (d.reasoning.client_communication) {
        Object.assign(clientComm, d.reasoning.client_communication)
      }
      summary.value = d.reasoning.summary || ''
    }
  } catch (e) {
    // 记录不存在，空白表单
  }
}

function fillFromAI(data) {
  if (data.soap) {
    soap.subjective = data.soap.subjective || ''
    soap.objective = data.soap.objective || ''
    soap.assessment = data.soap.assessment || ''
    soap.plan = data.soap.plan || ''
  }
  if (data.reasoning) {
    problemList.value = data.reasoning.problem_list || []
    reasoningPath.value = data.reasoning.reasoning_path || ''
    differentialList.value = data.reasoning.differential_list || []
    mustNotMiss.value = data.reasoning.must_not_miss || []
    missingInfo.value = data.reasoning.missing_info || ''
    recommendedTests.value = data.reasoning.recommended_tests || []
    dynamicQuestions.value = data.reasoning.dynamic_questions || ''
  }
  if (data.client_communication) {
    Object.assign(clientComm, data.client_communication)
  }
  summary.value = data.summary || ''
  activeTab.value = 'soap'
}

async function saveSOAP() {
  if (!recordId.value) {
    showToast('请先创建诊疗记录', 'error')
    return
  }
  saving.value = true
  try {
    await soapUpdate(recordId.value, {
      subjective: soap.subjective,
      objective: soap.objective,
      assessment: soap.assessment,
      plan: soap.plan,
      reasoning: {
        problem_list: problemList.value,
        reasoning_path: reasoningPath.value,
        differential_list: differentialList.value,
        must_not_miss: mustNotMiss.value,
        missing_info: missingInfo.value,
        recommended_tests: recommendedTests.value,
        dynamic_questions: dynamicQuestions.value,
        client_communication: { ...clientComm },
        summary: summary.value,
      },
    })
    showToast('保存成功')
  } catch (e) {
    showToast('保存失败: ' + (e.response?.data?.error || e.message), 'error')
  } finally {
    saving.value = false
  }
}

async function regenerateReasoning() {
  if (!recordId.value) {
    showToast('请先创建诊疗记录', 'error')
    return
  }
  generating.value = true
  try {
    const res = await soapReasoning(recordId.value)
    const data = res.data.reasoning || {}
    problemList.value = data.problem_list || []
    reasoningPath.value = data.reasoning_path || ''
    differentialList.value = data.differential_list || []
    mustNotMiss.value = data.must_not_miss || []
    missingInfo.value = data.missing_info || ''
    recommendedTests.value = data.recommended_tests || []
    dynamicQuestions.value = data.dynamic_questions || ''
    if (data.client_communication) Object.assign(clientComm, data.client_communication)
    summary.value = data.summary || ''
    showToast('临床推理已重新生成')
  } catch (e) {
    showToast('推理生成失败: ' + (e.response?.data?.error || e.message), 'error')
  } finally {
    generating.value = false
  }
}

async function saveReasoning() {
  await saveSOAP()
}

onMounted(() => {
  loadSOAP()
  loadTemplates()
})

watch(() => aiVoice.lastResult, (result) => {
  if (!result) return
  if (result.soapData) {
    fillFromAI(result)
    showToast('AI 结果已填入 SOAP 表单')
  } else if (result.petInfo || result.medicalInfo) {
    // fill partial data
    if (result.petInfo?.name) transcriptText.value = transcriptText.value || result.transcript || ''
  }
  aiVoice.consumeResult()
}, { deep: true })
</script>

<style scoped>
.soap-page {
  max-width: 1200px;
  margin: 0 auto;
}

.case-id {
  font-size: 13px;
  color: var(--color-text-secondary);
  background: #f1f5f9;
  padding: 2px 12px;
  border-radius: 6px;
}

/* ========== 快捷工具栏 ========== */
.soap-toolbar {
  display: flex;
  align-items: flex-start;
  gap: 24px;
  padding: 16px 0;
  margin-bottom: 12px;
  border-bottom: 1px solid var(--color-border);
  flex-wrap: wrap;
}

.toolbar-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.toolbar-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.toolbar-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.template-select {
  width: 240px;
  padding: 6px 10px;
  font-size: 13px;
}

/* 语音按钮 */
.voice-section {
  margin-left: auto;
}

.btn-voice-big {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 10px 22px;
  background: linear-gradient(135deg, #3b82f6, #6366f1);
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  border-radius: 24px;
  border: none;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 3px 12px rgba(59, 130, 246, 0.3);
  white-space: nowrap;
}

.btn-voice-big:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(59, 130, 246, 0.4);
}

.btn-voice-big:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.btn-voice-big.is-recording {
  background: linear-gradient(135deg, #ef4444, #dc2626);
  box-shadow: 0 3px 12px rgba(239, 68, 68, 0.4);
  animation: pulse-rec 1.2s infinite;
}

.btn-voice-big.is-uploading {
  background: linear-gradient(135deg, #f59e0b, #d97706);
  box-shadow: 0 3px 12px rgba(245, 158, 11, 0.35);
}

.btn-voice-big.is-thinking {
  background: linear-gradient(135deg, #10b981, #059669);
  box-shadow: 0 3px 12px rgba(16, 185, 129, 0.35);
}

@keyframes pulse-rec {
  0%, 100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.4); }
  50% { box-shadow: 0 0 0 14px rgba(239, 68, 68, 0); }
}

.recording-timer {
  font-size: 14px;
  font-weight: 600;
  color: #ef4444;
  margin-left: 8px;
}

/* 转录文字展示 */
.transcript-display {
  margin-bottom: 14px;
  background: #f0f9ff;
  border: 1px solid #bae6fd;
  border-radius: 8px;
  overflow: hidden;
}

.transcript-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 14px;
  background: #e0f2fe;
  font-size: 13px;
  font-weight: 600;
  color: #0369a1;
}

.btn-text {
  font-size: 12px;
  color: #0284c7;
  background: none;
  border: none;
  cursor: pointer;
  text-decoration: underline;
}

.transcript-body {
  padding: 12px 14px;
  font-size: 14px;
  line-height: 1.6;
  color: var(--color-text);
  white-space: pre-wrap;
  max-height: 200px;
  overflow-y: auto;
}

/* AI 思考中 */
.ai-thinking-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  margin-bottom: 14px;
  background: linear-gradient(135deg, #ecfdf5, #d1fae5);
  border: 1px solid #a7f3d0;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  color: #065f46;
}

.thinking-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #10b981;
  animation: thinking-blink 1s infinite;
}

@keyframes thinking-blink {
  0%, 100% { opacity: 0.3; }
  50% { opacity: 1; }
}

/* ========== 原有样式 ========== */
.tabs {
  display: flex;
  gap: 0;
  border-bottom: 2px solid var(--color-border);
  margin-bottom: 16px;
}

.tab {
  padding: 10px 24px;
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text-secondary);
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  cursor: pointer;
  transition: all 0.15s;
}

.tab.active {
  color: var(--color-primary);
  border-bottom-color: var(--color-primary);
}

.tab-content {
  padding: 8px 0;
}

.soap-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.soap-box {
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 12px;
  background: #fff;
}

.soap-box:nth-child(1),
.soap-box:nth-child(3) {
  grid-column: 1;
}

.soap-box:nth-child(2),
.soap-box:nth-child(4) {
  grid-column: 2;
}

.soap-label {
  font-weight: 700;
  font-size: 14px;
  color: var(--color-primary);
  margin-bottom: 8px;
}

.soap-input {
  font-size: 13px;
  resize: vertical;
  width: 100%;
}

.client-comm-section {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid var(--color-border);
}

.section-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text);
  margin: 16px 0 10px;
}

.comm-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 10px;
}

.comm-item label {
  font-size: 12px;
  color: var(--color-text-secondary);
  display: block;
  margin-bottom: 4px;
}

.soap-actions {
  display: flex;
  gap: 10px;
  margin-top: 16px;
}

.case-summary {
  margin-top: 12px;
  padding: 10px 14px;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 6px;
  font-size: 13px;
  line-height: 1.6;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  margin-bottom: 8px;
}

.data-table th,
.data-table td {
  border: 1px solid var(--color-border);
  padding: 8px 10px;
  text-align: left;
  vertical-align: top;
}

.data-table th {
  background: #f8fafc;
  font-weight: 600;
}

.evidence-cell {
  font-size: 12px;
  color: var(--color-text-secondary);
}

.empty-hint {
  color: var(--color-text-light);
  font-size: 13px;
  font-style: italic;
}

.reasoning-path-box {
  padding: 12px 16px;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  font-size: 14px;
  line-height: 1.7;
  white-space: pre-wrap;
}

.prob-tag {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 600;
}

.prob-高 {
  background: #fee2e2;
  color: #dc2626;
}

.prob-中 {
  background: #fef3c7;
  color: #d97706;
}

.prob-低 {
  background: #dbeafe;
  color: #2563eb;
}

.must-not-miss {
  padding: 10px 14px;
  background: #fff1f2;
  border: 1px solid #fecdd3;
  border-radius: 6px;
  margin-top: 8px;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.mnm-tag {
  background: #fecdd3;
  color: #be123c;
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
}

.three-col {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 16px;
  margin-top: 8px;
}

.info-box {
  padding: 10px 14px;
  background: #f8fafc;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  min-height: 60px;
}

.test-list {
  padding: 0;
  margin: 0;
  list-style: none;
  font-size: 13px;
}

.test-list li {
  padding: 6px 10px;
  border-bottom: 1px solid #f1f5f9;
}

.test-list li:last-child {
  border-bottom: none;
}

@media (max-width: 768px) {
  .soap-toolbar {
    flex-direction: column;
  }
  .voice-section {
    margin-left: 0;
  }
  .soap-grid {
    grid-template-columns: 1fr;
  }
  .soap-box:nth-child(1),
  .soap-box:nth-child(2),
  .soap-box:nth-child(3),
  .soap-box:nth-child(4) {
    grid-column: 1;
  }
}
</style>
