<template>
  <div class="page soap-page">
    <div class="card">
      <div class="card-header">
        <span class="card-title">SOAP 病历</span>
        <span v-if="recordData.id" class="case-id">病例编号: CN{{ String(recordData.id).padStart(4, '0') }}</span>
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
            <div class="soap-input-wrap">
              <textarea v-model="soap.subjective" class="input soap-input" rows="6" placeholder="主诉、病程、病史、主人观察..."></textarea>
              <VoiceInput v-model="soap.subjective" size="sm" />
            </div>
          </div>
          <div class="soap-box">
            <div class="soap-label">O 客观检查</div>
            <div class="soap-input-wrap">
              <textarea v-model="soap.objective" class="input soap-input" rows="6" placeholder="体温、心率、触诊、听诊、实验室结果..."></textarea>
              <VoiceInput v-model="soap.objective" size="sm" />
            </div>
          </div>
          <div class="soap-box">
            <div class="soap-label">A 评估</div>
            <div class="soap-input-wrap">
              <textarea v-model="soap.assessment" class="input soap-input" rows="5" placeholder="问题列表、鉴别诊断、临床判断..."></textarea>
              <VoiceInput v-model="soap.assessment" size="sm" />
            </div>
          </div>
          <div class="soap-box">
            <div class="soap-label">P 计划</div>
            <div class="soap-input-wrap">
              <textarea v-model="soap.plan" class="input soap-input" rows="5" placeholder="检查计划、治疗计划、护理建议、随访..."></textarea>
              <VoiceInput v-model="soap.plan" size="sm" />
            </div>
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
          <button class="btn btn-outline" @click="generateFromAI" :disabled="generating">
            {{ generating ? 'AI 生成中...' : 'AI 一键生成 SOAP' }}
          </button>
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

    <!-- 对话输入区 -->
    <div class="card">
      <div class="card-header">
        <span class="card-title">对话记录</span>
      </div>
      <textarea v-model="transcript" class="input" rows="8" placeholder="粘贴医生-主人对话记录，或点击下方按钮录音..."></textarea>
      <div style="display:flex;gap:8px;margin-top:8px;">
        <button class="btn btn-outline btn-sm" @click="transcribeAndGenerate" :disabled="generating">
          {{ generating ? '处理中...' : '录音 → AI 生成完整 SOAP' }}
        </button>
        <button class="btn btn-primary btn-sm" @click="parseTranscript" :disabled="generating || !transcript">
          {{ generating ? 'AI 分析中...' : '粘贴文本 → AI 生成 SOAP' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import VoiceInput from '../components/VoiceInput.vue'
import {
  soapFromTranscript, soapFromTranscriptAudio, soapGet, soapUpdate,
  soapReasoning, soapClientComm,
} from '../api'

const route = useRoute()
const router = useRouter()

const recordId = ref(route.params.id ? Number(route.params.id) : null)
const recordData = ref({})
const activeTab = ref('soap')
const saving = ref(false)
const generating = ref(false)

const transcript = ref('')
const summary = ref('')

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

function showToast(msg, type = '') {
  const toast = document.getElementById('global-toast')
  if (toast) {
    toast.textContent = msg
    toast.className = `global-toast ${type}` || 'global-toast'
    toast.style.display = 'block'
    setTimeout(() => { toast.style.display = 'none' }, 3000)
  }
}

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
    // 记录不存在，保持空白表单
  }
}

async function parseTranscript() {
  if (!transcript.value) return
  generating.value = true
  try {
    const res = await soapFromTranscript({ transcript: transcript.value })
    fillFromAI(res.data)
    showToast('AI 分析完成')
  } catch (e) {
    showToast('AI 分析失败: ' + (e.response?.data?.error || e.message), 'error')
  } finally {
    generating.value = false
  }
}

async function transcribeAndGenerate() {
  generating.value = true
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm' })
    const chunks = []

    recorder.ondataavailable = (e) => { if (e.data.size > 0) chunks.push(e.data) }
    recorder.start(250)

    await new Promise((resolve) => {
      recorder.onstop = resolve
      showToast('正在录音... 点击停止')
      setTimeout(() => {
        if (recorder.state !== 'inactive') {
          recorder.stop()
        }
      }, 60000)
    })

    stream.getTracks().forEach(t => t.stop())
    if (chunks.length === 0) {
      showToast('未录制到音频', 'error')
      generating.value = false
      return
    }

    const audioBlob = new Blob(chunks, { type: 'audio/webm' })
    const res = await soapFromTranscriptAudio(audioBlob)
    fillFromAI(res.data)
    transcript.value = res.data.transcript || ''
    showToast('语音转写 + AI 分析完成')
  } catch (e) {
    showToast(e.response?.data?.error || '操作失败', 'error')
  } finally {
    generating.value = false
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
}

async function generateFromAI() {
  if (!transcript.value) {
    showToast('请先在对话记录区输入内容', 'error')
    return
  }
  generating.value = true
  try {
    const res = await soapFromTranscript({ transcript: transcript.value })
    fillFromAI(res.data)
    showToast('AI 生成完成')
  } catch (e) {
    showToast('AI 生成失败: ' + (e.response?.data?.error || e.message), 'error')
  } finally {
    generating.value = false
  }
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
})
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

.soap-input-wrap {
  display: flex;
  align-items: flex-start;
  gap: 6px;
}

.soap-input {
  flex: 1;
  font-size: 13px;
  resize: vertical;
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
</style>
