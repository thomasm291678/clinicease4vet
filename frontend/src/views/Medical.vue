<template>
  <div class="page">
    <div class="card">
      <div class="card-header">
        <span class="card-title">诊疗记录</span>
        <button class="btn btn-primary btn-sm" @click="openCreate">添加记录</button>
      </div>

      <div v-if="loading" class="loading"><span class="spinner"></span>加载中...</div>

      <table v-else-if="records.length">
        <thead>
          <tr>
            <th>宠物ID</th>
            <th>动态</th>
            <th>兽医</th>
            <th>就诊日期</th>
            <th>诊断</th>
            <th>治疗方案</th>
            <th>费用</th>
            <th>复诊日期</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in records" :key="r.id">
            <td>{{ r.pet_id }}</td>
            <td>{{ r.symptoms || '-' }}</td>
            <td>{{ r.vet_name || '-' }}</td>
            <td>{{ r.visit_date }}</td>
            <td>{{ r.diagnosis || '-' }}</td>
            <td>{{ r.treatment || '-' }}</td>
            <td>{{ r.fee_charged || 0 }}</td>
            <td>{{ r.follow_up_date || '-' }}</td>
            <td>
              <div class="td-actions">
                <button class="btn btn-outline btn-sm" @click="openEdit(r)">编辑</button>
                <button class="btn btn-outline btn-sm" @click="$router.push('/soap/' + r.id)">SOAP</button>
                <button class="btn btn-danger btn-sm" @click="handleDelete(r.id)">删除</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else class="empty-state">暂无诊疗记录</div>
    </div>

    <div v-if="showModal" class="modal-overlay" @click.self="showModal = false">
      <div class="modal">
        <h3 class="modal-title">{{ editingRecord ? '编辑记录' : '添加诊疗记录' }}</h3>

        <div class="ai-toolbar" v-if="!editingRecord">
          <select v-model="aiTemplate" class="input template-select" @change="loadAITemplate">
            <option value="">-- 病历模板 --</option>
            <option v-for="t in aiTemplates" :key="t.id" :value="t.id">{{ t.name }}</option>
          </select>
          <button class="btn btn-outline btn-sm" @click="showAiInput = !showAiInput">
            {{ showAiInput ? '收起' : 'AI 智能填充' }}
          </button>
        </div>

        <div v-if="showAiInput && !editingRecord" class="ai-fill-row">
          <textarea v-model="aiFillText" class="input" rows="2" placeholder="粘贴一段描述文字，或语音录入，AI 自动填充全部字段..."></textarea>
          <div class="ai-fill-actions">
            <VoiceInput v-model="aiFillText" />
            <button class="btn btn-primary btn-sm" @click="handleAiFill" :disabled="aiFilling">{{ aiFilling ? '解析中...' : 'AI 填充' }}</button>
          </div>
        </div>

        <form @submit.prevent="handleSave">
          <div class="inline-form">
            <div class="form-group">
              <label>宠物ID *</label>
              <input v-model.number="form.pet_id" type="number" class="input" required min="1" />
            </div>
            <div class="form-group">
              <label>兽医</label>
              <div style="display:flex;align-items:center;gap:4px;">
                <input v-model="form.vet_name" class="input" />
                <VoiceInput v-model="form.vet_name" size="sm" />
              </div>
            </div>
          </div>
          <div class="form-group">
            <label>症状 / 主诉</label>
            <div style="display:flex;align-items:flex-start;gap:4px;">
              <textarea v-model="form.symptoms" class="input" rows="2" placeholder="如：呕吐、腹泻、精神萎靡..."></textarea>
              <VoiceInput v-model="form.symptoms" size="sm" />
            </div>
          </div>
          <div class="form-group">
            <label>就诊日期 *</label>
            <input v-model="form.visit_date" type="date" class="input" required />
          </div>
          <div class="form-group">
            <label>诊断</label>
            <div style="display:flex;align-items:flex-start;gap:4px;">
              <textarea v-model="form.diagnosis" class="input" rows="2"></textarea>
              <VoiceInput v-model="form.diagnosis" size="sm" />
            </div>
          </div>
          <div class="form-group">
            <label>治疗方案</label>
            <div style="display:flex;align-items:flex-start;gap:4px;">
              <textarea v-model="form.treatment" class="input" rows="2"></textarea>
              <VoiceInput v-model="form.treatment" size="sm" />
            </div>
            <button
              type="button"
              class="btn btn-outline btn-sm"
              @click="handleAiTreatment"
              :disabled="generatingTreatment"
              style="margin-top:6px;"
            >
              {{ generatingTreatment ? '生成中...' : 'AI 辅助治疗方案' }}
            </button>
          </div>
          <div class="inline-form">
            <div class="form-group">
              <label>费用</label>
              <input v-model.number="form.fee_charged" type="number" class="input" min="0" />
            </div>
            <div class="form-group">
              <label>复诊日期</label>
              <input v-model="form.follow_up_date" type="date" class="input" />
            </div>
          </div>
          <div class="form-group">
            <label>备注</label>
            <textarea v-model="form.notes" class="input" rows="2"></textarea>
          </div>
          <div class="modal-actions">
            <button type="button" class="btn btn-outline" @click="showModal = false">取消</button>
            <button type="submit" class="btn btn-primary" :disabled="saving">{{ saving ? '保存中...' : '保存' }}</button>
          </div>
        </form>
      </div>
    </div>

    <div v-if="toast.show" :class="['toast', 'toast-' + toast.type]">{{ toast.msg }}</div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { getMedicalRecords, createMedicalRecord, updateMedicalRecord, deleteMedicalRecord, aiAutoFill, aiGetTemplates, aiGetTemplateDetail, aiGenerateTreatment } from '../api'
import VoiceInput from '../components/VoiceInput.vue'

const records = ref([])
const loading = ref(false)
const showModal = ref(false)
const editingRecord = ref(null)
const saving = ref(false)
const toast = reactive({ show: false, msg: '', type: 'success' })

const showAiInput = ref(false)
const aiFillText = ref('')
const aiFilling = ref(false)
const aiTemplate = ref('')
const aiTemplates = ref([])
const generatingTreatment = ref(false)

const form = reactive({
  pet_id: null, vet_name: '', visit_date: '', diagnosis: '',
  treatment: '', symptoms: '', notes: '', follow_up_date: '', fee_charged: 0,
})

function showToast(msg, type = 'success') {
  toast.msg = msg; toast.type = type; toast.show = true
  setTimeout(() => { toast.show = false }, 3000)
}

function resetForm() {
  form.pet_id = null; form.vet_name = ''; form.visit_date = ''; form.diagnosis = ''
  form.treatment = ''; form.symptoms = ''; form.notes = ''; form.follow_up_date = ''; form.fee_charged = 0
}

async function fetchRecords() {
  loading.value = true
  try {
    const res = await getMedicalRecords()
    records.value = res.data.data || []
  } catch (e) {
    showToast('加载失败', 'error')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingRecord.value = null
  resetForm()
  showAiInput.value = false
  aiFillText.value = ''
  aiTemplate.value = ''

  const prefill = localStorage.getItem('ai_prefill_medical')
  if (prefill) {
    try {
      const mf = JSON.parse(prefill)
      if (mf.diagnosis) form.diagnosis = mf.diagnosis
      if (mf.treatment) form.treatment = mf.treatment
      if (mf.symptoms) form.symptoms = mf.symptoms
      if (mf.notes) form.notes = mf.notes
      if (mf.fee_charged) form.fee_charged = mf.fee_charged
      if (mf.vet_name) form.vet_name = mf.vet_name
      if (mf.visit_date) form.visit_date = mf.visit_date
      if (mf.follow_up_date) form.follow_up_date = mf.follow_up_date
      localStorage.removeItem('ai_prefill_medical')
    } catch (e) { /* ignore */ }
  }

  showModal.value = true
}

function openEdit(r) {
  editingRecord.value = r
  form.pet_id = r.pet_id
  form.vet_name = r.vet_name || ''
  form.visit_date = r.visit_date || ''
  form.diagnosis = r.diagnosis || ''
  form.treatment = r.treatment || ''
  form.symptoms = r.symptoms || ''
  form.notes = r.notes || ''
  form.follow_up_date = r.follow_up_date || ''
  form.fee_charged = r.fee_charged || 0
  showModal.value = true
}

async function handleSave() {
  saving.value = true
  try {
    const data = { ...form }
    if (editingRecord.value) {
      await updateMedicalRecord(editingRecord.value.id, data)
      showToast('更新成功')
    } else {
      await createMedicalRecord(data)
      showToast('添加成功')
    }
    showModal.value = false
    fetchRecords()
  } catch (e) {
    showToast(e.response?.data?.error || '保存失败', 'error')
  } finally {
    saving.value = false
  }
}

async function handleAiFill() {
  if (!aiFillText.value.trim()) { showToast('请输入描述文字', 'error'); return }
  aiFilling.value = true
  try {
    const res = await aiAutoFill(aiFillText.value, form.pet_id || null)
    const fd = res.data?.form_data
    if (fd) {
      if (fd.diagnosis) form.diagnosis = fd.diagnosis
      if (fd.treatment) form.treatment = fd.treatment
      if (fd.symptoms) form.symptoms = fd.symptoms
      if (fd.notes) form.notes = fd.notes
      if (fd.fee_charged) form.fee_charged = fd.fee_charged
      if (fd.vet_name) form.vet_name = fd.vet_name
      if (fd.visit_date) form.visit_date = fd.visit_date
      if (fd.follow_up_date) form.follow_up_date = fd.follow_up_date
      if (fd.pet_id && !form.pet_id) form.pet_id = fd.pet_id
    }
    const vd = res.data?.vaccine_data
    if (vd) {
      localStorage.setItem('ai_prefill_vaccine', JSON.stringify(vd))
    }
    showToast('填充完成 (置信度: ' + (res.data?.confidence || 0) + '%)')
  } catch (e) {
    showToast(e.response?.data?.error || 'AI 填充失败', 'error')
  } finally {
    aiFilling.value = false
  }
}

async function handleAiTreatment() {
  if (!form.symptoms && !form.diagnosis) {
    showToast('请先填写症状或诊断', 'error')
    return
  }
  generatingTreatment.value = true
  try {
    const res = await aiGenerateTreatment({
      symptoms: form.symptoms,
      diagnosis: form.diagnosis,
      species: '',
    })
    const treatment = res.data?.treatment
    if (treatment) {
      form.treatment = form.treatment
        ? form.treatment + '\n\n--- AI 建议 ---\n' + treatment
        : treatment
      showToast('治疗方案已生成')
    } else {
      showToast('生成失败，请重试', 'error')
    }
  } catch (e) {
    showToast(e.response?.data?.error || 'AI 生成失败', 'error')
  } finally {
    generatingTreatment.value = false
  }
}

function cleanTemplateText(text) {
  if (!text) return ''
  return text.replace(/_{3,}/g, '\n').replace(/_{1,2}/g, '\n').replace(/\n{3,}/g, '\n\n').trim()
}

function extractSection(content, startKeyword, endKeywords = []) {
  const lines = content.split('\n')
  let startIdx = -1
  let endIdx = lines.length

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim()
    if (startIdx === -1 && line.includes(startKeyword)) {
      startIdx = i + 1
      continue
    }
    if (startIdx >= 0 && endKeywords.some(kw => line.includes(kw))) {
      endIdx = i
      break
    }
  }

  if (startIdx === -1) return ''
  const section = lines.slice(startIdx, endIdx).join('\n')
  return cleanTemplateText(section)
}

async function loadAITemplate() {
  if (!aiTemplate.value) return
  try {
    const res = await aiGetTemplateDetail(aiTemplate.value)
    const content = res.data?.content
    if (content) {
      const diagnosisSection = extractSection(content, '诊断', ['七', '治疗', '八', '九'])
        || extractSection(content, '六', ['七', '治疗'])
      const symptomsSection = extractSection(content, '主诉', ['现病史', '四', '临床', '五'])
        || extractSection(content, '三', ['四', '临床', '检查'])
      const treatmentSection = extractSection(content, '治疗', ['八', '九', '十', '转归', '十一', '讨论'])
        || extractSection(content, '七', ['八', '九', '十', '转归'])

      if (diagnosisSection) form.diagnosis = diagnosisSection
      if (symptomsSection) form.symptoms = symptomsSection
      if (treatmentSection) form.treatment = treatmentSection

      showToast('模板已分段填充（您可手动编辑）')
    }
    aiTemplate.value = ''
  } catch (e) {
    showToast('模板加载失败', 'error')
  }
}

async function handleDelete(id) {
  if (!confirm('确定删除该记录？')) return
  try {
    await deleteMedicalRecord(id)
    showToast('删除成功')
    fetchRecords()
  } catch (e) {
    showToast('删除失败', 'error')
  }
}

onMounted(async () => {
  fetchRecords()
  try {
    const res = await aiGetTemplates()
    aiTemplates.value = res.data?.templates || []
  } catch (e) { /* ignore */ }
})
</script>

<style scoped>
.page { max-width: 1100px; }
.td-actions { display: flex; gap: 6px; }

.ai-toolbar {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--color-border);
}

.template-select { width: 160px; }

.ai-fill-row {
  margin-bottom: 12px;
  padding: 10px;
  background: #f0f9ff;
  border: 1px solid #bae6fd;
  border-radius: var(--radius);
}

.ai-fill-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 6px;
}
</style>
