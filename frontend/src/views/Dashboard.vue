<template>
  <div class="dashboard">
    <div class="quick-ai-bar">
      <div class="quick-ai-inner">
        <div class="quick-ai-left">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
            <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
            <line x1="12" y1="19" x2="12" y2="23"/>
            <line x1="8" y1="23" x2="16" y2="23"/>
          </svg>
          <span>语音快速录入：说出病情，AI 自动解析并创建诊疗记录</span>
        </div>
        <button class="btn btn-primary btn-sm" @click="startQuickRecord" :disabled="quickUploading">
          <span v-if="quickRecording" class="btn-recording-text">停止录音</span>
          <span v-else-if="quickUploading">识别中...</span>
          <span v-else>开始录音</span>
        </button>
      </div>
      <p v-if="quickText" class="quick-result">识别结果：{{ quickText }}</p>
      <p v-if="quickUploading" class="quick-status">正在上传录音并识别...</p>
      <p v-else-if="quickProcessing" class="quick-status">AI 正在分析...</p>
    </div>

    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-label">宠物总数</div>
        <div class="stat-value">{{ stats.totalPets }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">本月诊疗</div>
        <div class="stat-value">{{ stats.monthRecords }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">待接种疫苗</div>
        <div class="stat-value">{{ stats.pendingVaccines }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">药品库存预警</div>
        <div class="stat-value warn">{{ stats.lowStockDrugs }}</div>
      </div>
    </div>

    <div class="charts-row">
      <div class="card" style="flex: 2;">
        <div class="card-header">
          <span class="card-title">宠物种类分布</span>
        </div>
        <div class="species-chart" v-if="stats.species.length">
          <div v-for="(item, i) in stats.species" :key="i" class="species-bar-row">
            <span class="species-name">{{ item.name }}</span>
            <div class="species-bar-wrap">
              <div class="species-bar" :style="{ width: item.percent + '%', background: barColors[i % barColors.length] }"></div>
            </div>
            <span class="species-count">{{ item.count }}</span>
          </div>
        </div>
        <div v-else class="empty-state">暂无数据</div>
      </div>
      <div class="card" style="flex: 1;">
        <div class="card-header">
          <span class="card-title">最近诊疗</span>
        </div>
        <div v-if="recentRecords.length" class="recent-list">
          <div v-for="r in recentRecords" :key="r.id" class="recent-item">
            <div class="recent-main">
              <span class="recent-pet">{{ r.pet_name || '宠物 #' + r.pet_id }}</span>
              <span class="recent-date">{{ r.visit_date }}</span>
            </div>
            <div class="recent-diag">{{ r.diagnosis || '暂无诊断' }}</div>
          </div>
        </div>
        <div v-else class="empty-state">暂无记录</div>
      </div>
    </div>

    <div v-if="toast.show" :class="['toast', 'toast-' + toast.type]">{{ toast.msg }}</div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getPets, getPetStats, getMedicalRecords, getVaccinations, getDrugs, createMedicalRecord, aiTranscribeAndFill, aiTranscribe } from '../api'

const router = useRouter()
const toast = reactive({ show: false, msg: '', type: 'success' })

const quickRecording = ref(false)
const quickText = ref('')
const quickProcessing = ref(false)
const quickUploading = ref(false)
let quickMediaRecorder = null
let quickChunks = []

const stats = reactive({
  totalPets: 0,
  monthRecords: 0,
  pendingVaccines: 0,
  lowStockDrugs: 0,
  species: [],
})

const recentRecords = ref([])
const barColors = ['#2563eb', '#3b82f6', '#60a5fa', '#93c5fd', '#1d4ed8']

function showToast(msg, type = 'success') {
  toast.msg = msg
  toast.type = type
  toast.show = true
  setTimeout(() => { toast.show = false }, 3000)
}

async function startQuickRecord() {
  if (quickRecording.value) {
    stopQuickRecord()
    return
  }

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    quickChunks = []
    quickMediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' })

    quickMediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        quickChunks.push(event.data)
      }
    }

    quickMediaRecorder.onstop = async () => {
      stream.getTracks().forEach((t) => t.stop())
      if (quickChunks.length === 0) return

      const audioBlob = new Blob(quickChunks, { type: 'audio/webm' })
      quickUploading.value = true
      quickProcessing.value = true

      try {
        const res = await aiTranscribe(audioBlob)
        quickText.value = res.data?.text || ''
        quickUploading.value = false

        if (quickText.value) {
          const fillRes = await aiTranscribeAndFill({ text: quickText.value })
          const mf = fillRes.data?.medical_form
          if (mf) {
            localStorage.setItem('ai_prefill_medical', JSON.stringify(mf))
            showToast('AI 解析完成，正在跳转到诊疗记录...')
            setTimeout(() => router.push('/medical'), 500)
          } else {
            showToast('未能解析出诊疗信息，请重试', 'error')
          }
        } else {
          showToast('未识别到语音内容', 'error')
        }
      } catch (e) {
        showToast('语音识别失败: ' + (e.response?.data?.error || e.message || '网络错误'), 'error')
      } finally {
        quickProcessing.value = false
        quickUploading.value = false
      }
    }

    quickMediaRecorder.start(250)
    quickRecording.value = true
  } catch (e) {
    showToast('无法访问麦克风，请检查权限', 'error')
  }
}

function stopQuickRecord() {
  if (quickMediaRecorder && quickMediaRecorder.state !== 'inactive') {
    quickMediaRecorder.stop()
  }
  quickRecording.value = false
}

onMounted(async () => {
  try {
    const [petsRes, statsRes, recordsRes, vaccinesRes, drugsRes] = await Promise.all([
      getPets(),
      getPetStats().catch(() => ({ data: {} })),
      getMedicalRecords(),
      getVaccinations(),
      getDrugs(),
    ])

    stats.totalPets = petsRes.data.count || petsRes.data.data?.length || 0
    stats.totalPets = petsRes.data.count || petsRes.data.data?.length || 0

    const pets = petsRes.data.data || []
    const speciesMap = {}
    pets.forEach(p => {
      const s = p.species || '未知'
      speciesMap[s] = (speciesMap[s] || 0) + 1
    })
    stats.species = Object.entries(speciesMap).map(([name, count]) => ({
      name,
      count,
      percent: stats.totalPets ? Math.round((count / stats.totalPets) * 100) : 0,
    }))

    const records = recordsRes.data.data || []
    const now = new Date()
    stats.monthRecords = records.filter(r => {
      const d = new Date(r.visit_date || r.created_at)
      return d.getMonth() === now.getMonth() && d.getFullYear() === now.getFullYear()
    }).length
    recentRecords.value = records.slice(0, 5)

    const vaccines = vaccinesRes.data.data || []
    const today = new Date().toISOString().split('T')[0]
    stats.pendingVaccines = vaccines.filter(v => v.next_due_date && v.next_due_date <= today).length

    const drugs = drugsRes.data.data || []
    stats.lowStockDrugs = drugs.filter(d => d.quantity <= (d.min_stock_level || 5)).length
  } catch (e) {
    console.error(e)
  }
})
</script>

<style scoped>
.dashboard {
  max-width: 1100px;
}

.quick-ai-bar {
  background: linear-gradient(135deg, #eff6ff, #dbeafe);
  border: 1px solid #bfdbfe;
  border-radius: var(--radius);
  padding: 14px 18px;
  margin-bottom: 20px;
}

.quick-ai-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.quick-ai-left {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--color-primary);
  font-size: 13px;
}

.quick-result {
  margin-top: 8px;
  font-size: 13px;
  color: var(--color-text);
  padding: 6px 10px;
  background: #fff;
  border-radius: 4px;
}

.quick-status {
  margin-top: 4px;
  font-size: 12px;
  color: var(--color-text-secondary);
  font-style: italic;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  background: #fff;
  border-radius: var(--radius);
  padding: 20px;
  box-shadow: var(--shadow);
}

.stat-label {
  font-size: 12px;
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 6px;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--color-text);
}

.stat-value.warn {
  color: var(--color-danger);
}

.charts-row {
  display: flex;
  gap: 16px;
}

.species-chart {
  padding-top: 4px;
}

.species-bar-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
}

.species-name {
  width: 50px;
  font-size: 13px;
  color: var(--color-text);
  text-align: right;
  flex-shrink: 0;
}

.species-bar-wrap {
  flex: 1;
  height: 20px;
  background: #f1f5f9;
  border-radius: 4px;
  overflow: hidden;
}

.species-bar {
  height: 100%;
  border-radius: 4px;
  min-width: 4px;
  transition: width 0.6s ease;
}

.species-count {
  width: 30px;
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text);
}

.recent-list {
  padding-top: 4px;
}

.recent-item {
  padding: 10px 0;
  border-bottom: 1px solid var(--color-border);
}

.recent-item:last-child {
  border-bottom: none;
}

.recent-main {
  display: flex;
  justify-content: space-between;
  margin-bottom: 4px;
}

.recent-pet {
  font-weight: 600;
  font-size: 13px;
}

.recent-date {
  font-size: 12px;
  color: var(--color-text-secondary);
}

.recent-diag {
  font-size: 12px;
  color: var(--color-text-secondary);
}

.btn-recording-text {
  color: #dc2626;
}

@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .charts-row {
    flex-direction: column;
  }
}
</style>
