<template>
  <div class="page">
    <div class="card">
      <div class="card-header">
        <span class="card-title">宠物列表 ({{ total }})</span>
        <div class="actions">
          <input v-model="search" class="input search-input" placeholder="搜索宠物/主人..." @input="debouncedSearch" />
          <button class="btn btn-primary btn-sm" @click="openCreate">添加宠物</button>
        </div>
      </div>

      <div v-if="loading" class="loading"><span class="spinner"></span>加载中...</div>

      <table v-else-if="pets.length">
        <thead>
          <tr>
            <th>名称</th>
            <th>种类</th>
            <th>品种</th>
            <th>性别</th>
            <th>年龄(月)</th>
            <th>体重(kg)</th>
            <th>主人</th>
            <th>最近诊断</th>
            <th>就诊次数</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="pet in pets" :key="pet.id">
            <td><strong>{{ pet.name }}</strong></td>
            <td><span class="badge" :class="speciesBadge(pet.species)">{{ pet.species }}</span></td>
            <td>{{ pet.breed || '-' }}</td>
            <td>{{ pet.gender || '-' }}</td>
            <td>{{ pet.age_months || '-' }}</td>
            <td>{{ pet.weight_kg || '-' }}</td>
            <td>{{ pet.owner_name }}</td>
            <td>
              <span v-if="pet.recent_diagnosis" style="font-size:12px;color:var(--color-text);">
                {{ pet.recent_diagnosis.length > 20 ? pet.recent_diagnosis.slice(0,20) + '...' : pet.recent_diagnosis }}
              </span>
              <span v-else style="color:var(--color-text-light);">-</span>
            </td>
            <td>
              <span :class="['badge', (pet.total_visits || 0) > 0 ? 'badge-blue' : '']">
                {{ pet.total_visits || 0 }}
              </span>
            </td>
            <td>
              <div class="td-actions">
                <button class="btn btn-outline btn-sm" @click="openEdit(pet)">编辑</button>
                <button class="btn btn-outline btn-sm" @click="handleAiSummary(pet.id)">AI摘要</button>
                <button class="btn btn-danger btn-sm" @click="handleDelete(pet.id)">删除</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else class="empty-state">暂无宠物数据，点击"添加宠物"开始</div>
    </div>

    <div v-if="showModal" class="modal-overlay" @click.self="showModal = false">
      <div class="modal">
        <h3 class="modal-title">{{ editingPet ? '编辑宠物' : '添加宠物' }}</h3>

        <div v-if="editingPet" class="pet-health-brief">
          <div class="brief-row">
            <span class="brief-label">诊断</span>
            <input v-model="editDiagnosis" class="input input-sm" style="width:260px;" placeholder="输入诊断" />
            <button class="btn btn-primary btn-sm" @click="saveDiagnosis" :disabled="savingDiagnosis" style="margin-left: 6px;">保存</button>
          </div>
          <div class="brief-row">
            <span class="brief-label">治疗方案</span>
            <input v-model="editTreatment" class="input input-sm" style="width:260px;" placeholder="输入治疗方案" />
            <button class="btn btn-primary btn-sm" @click="saveTreatment" :disabled="savingTreatment" style="margin-left: 6px;">保存</button>
          </div>
          <div class="brief-row">
            <span class="brief-label">就诊次数</span>
            <span class="brief-value">{{ editingPet.total_visits || 0 }} 次</span>
          </div>
          <div class="brief-row" v-if="editingPet.recent_visit_date">
            <span class="brief-label">最近就诊</span>
            <span class="brief-value">{{ editingPet.recent_visit_date }}</span>
          </div>
          <button class="btn btn-outline btn-sm" @click="handleAiSummary(editingPet.id)">AI 病程全文</button>
        </div>

        <form @submit.prevent="handleSave">
          <div class="inline-form">
            <div class="form-group">
              <label>名称 *</label>
              <div style="display:flex;align-items:center;gap:4px;">
                <input v-model="form.name" class="input" required maxlength="30" />
                <VoiceInput v-model="form.name" size="sm" />
              </div>
            </div>
            <div class="form-group">
              <label>种类 *</label>
              <select v-model="form.species" class="input" required>
                <option value="">请选择</option>
                <option value="狗">狗</option>
                <option value="猫">猫</option>
                <option value="兔">兔</option>
                <option value="鸟">鸟</option>
                <option value="其他">其他</option>
              </select>
            </div>
            <div class="form-group">
              <label>品种</label>
              <div style="display:flex;align-items:center;gap:4px;">
                <input v-model="form.breed" class="input" maxlength="30" />
                <VoiceInput v-model="form.breed" size="sm" />
              </div>
            </div>
            <div class="form-group">
              <label>性别</label>
              <select v-model="form.gender" class="input">
                <option value="">未知</option>
                <option value="公">公</option>
                <option value="母">母</option>
              </select>
            </div>
            <div class="form-group">
              <label>年龄(月)</label>
              <input v-model.number="form.age_months" type="number" class="input" min="0" />
            </div>
            <div class="form-group">
              <label>体重(kg)</label>
              <input v-model.number="form.weight_kg" type="number" class="input" min="0" step="0.1" />
            </div>
            <div class="form-group">
              <label>颜色</label>
              <input v-model="form.color" class="input" maxlength="20" />
            </div>
            <div class="form-group">
              <label>主人姓名 *</label>
              <input v-model="form.owner_name" class="input" required maxlength="30" />
            </div>
            <div class="form-group">
              <label>联系方式</label>
              <input v-model="form.owner_contact" class="input" maxlength="15" />
            </div>
            <div class="form-group full-width">
              <label>地址</label>
              <input v-model="form.owner_address" class="input" maxlength="100" />
            </div>
          </div>
          <div class="modal-actions">
            <button type="button" class="btn btn-outline" @click="showModal = false">取消</button>
            <button type="submit" class="btn btn-primary" :disabled="saving">{{ saving ? '保存中...' : '保存' }}</button>
          </div>
        </form>
      </div>
    </div>

    <div v-if="aiSummaryModal" class="modal-overlay" @click.self="aiSummaryModal = false">
      <div class="modal">
        <h3 class="modal-title">AI 病程摘要 - {{ aiSummaryData?.pet_name || '' }}</h3>
        <div v-if="aiSummaryLoading" class="loading"><span class="spinner"></span>加载中...</div>
        <div v-else-if="aiSummaryData">
          <p style="font-size:13px;color:var(--color-text-secondary);margin-bottom:12px;">
            共 {{ aiSummaryData.total_visits || 0 }} 次诊疗，{{ aiSummaryData.total_vaccines || 0 }} 次疫苗
          </p>
          <div class="ai-summary-text">{{ aiSummaryData.summary }}</div>
          <div v-if="aiSummaryData.timeline?.length" class="ai-timeline">
            <h4 style="font-size:13px;margin-bottom:8px;">时间线</h4>
            <div v-for="(t, i) in aiSummaryData.timeline" :key="i" class="tl-item">
              <span class="tl-date">{{ t.date }}</span>
              <span :class="['badge', t.type === '诊疗' ? 'badge-blue' : 'badge-green']">{{ t.type }}</span>
              <span v-if="t.type === '诊疗'" class="tl-info">{{ t.diagnosis }}</span>
              <span v-else class="tl-info">{{ t.vaccine }}</span>
            </div>
          </div>
        </div>
        <div class="modal-actions">
          <button class="btn btn-outline" @click="aiSummaryModal = false">关闭</button>
        </div>
      </div>
    </div>

    <div v-if="toast.show" :class="['toast', 'toast-' + toast.type]">{{ toast.msg }}</div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { getPets, createPet, updatePet, deletePet, aiPetSummary, createMedicalRecord, updateMedicalRecord } from '../api'
import VoiceInput from '../components/VoiceInput.vue'

const pets = ref([])
const total = ref(0)
const loading = ref(false)
const search = ref('')
const showModal = ref(false)
const editingPet = ref(null)
const saving = ref(false)
const toast = reactive({ show: false, msg: '', type: 'success' })

const aiSummaryModal = ref(false)
const aiSummaryData = ref(null)
const aiSummaryLoading = ref(false)

const editDiagnosis = ref('')
const savingDiagnosis = ref(false)
const editTreatment = ref('')
const savingTreatment = ref(false)

const form = reactive({
  name: '', species: '', breed: '', gender: '', age_months: null,
  weight_kg: null, color: '', owner_name: '', owner_contact: '', owner_address: '',
})

let searchTimer = null

function showToast(msg, type = 'success') {
  toast.msg = msg; toast.type = type; toast.show = true
  setTimeout(() => { toast.show = false }, 3000)
}

function speciesBadge(species) {
  const map = { '狗': 'badge-blue', '猫': 'badge-green', '兔': 'badge-yellow', '鸟': 'badge-blue' }
  return map[species] || 'badge-blue'
}

function debouncedSearch() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(fetchPets, 300)
}

async function fetchPets() {
  loading.value = true
  try {
    const params = {}
    if (search.value) params.search = search.value
    const res = await getPets(params)
    pets.value = res.data.data || []
    total.value = res.data.count || pets.value.length
  } catch (e) {
    showToast('加载失败', 'error')
  } finally {
    loading.value = false
  }
}

function resetForm() {
  Object.keys(form).forEach(k => { form[k] = k.endsWith('_months') || k.endsWith('_kg') ? null : '' })
}

function openCreate() {
  editingPet.value = null
  resetForm()

  const prefill = localStorage.getItem('ai_prefill_pet')
  if (prefill) {
    try {
      const pf = JSON.parse(prefill)
      if (pf.name) form.name = pf.name
      if (pf.species) form.species = pf.species
      if (pf.breed) form.breed = pf.breed
      if (pf.gender) form.gender = pf.gender
      if (pf.owner_name) form.owner_name = pf.owner_name
      if (pf.owner_contact) form.owner_contact = pf.owner_contact
      localStorage.removeItem('ai_prefill_pet')
    } catch (e) { /* ignore */ }
  }

  showModal.value = true
}

function openEdit(pet) {
  editingPet.value = pet
  Object.keys(form).forEach(k => { form[k] = pet[k] ?? (typeof pet[k] === 'number' ? null : '') })
  editDiagnosis.value = pet.recent_diagnosis || ''
  editTreatment.value = pet.recent_treatment || ''
  showModal.value = true
}

async function handleSave() {
  saving.value = true
  try {
    const data = { ...form }
    if (editingPet.value) {
      await updatePet(editingPet.value.id, data)
      showToast('更新成功')
    } else {
      await createPet(data)
      showToast('添加成功')
    }
    showModal.value = false
    fetchPets()
  } catch (e) {
    showToast(e.response?.data?.error || '保存失败', 'error')
  } finally {
    saving.value = false
  }
}

async function handleDelete(id) {
  if (!confirm('确定删除该宠物？')) return
  try {
    await deletePet(id)
    showToast('删除成功')
    fetchPets()
  } catch (e) {
    showToast('删除失败', 'error')
  }
}

async function handleAiSummary(petId) {
  aiSummaryModal.value = true
  aiSummaryData.value = null
  aiSummaryLoading.value = true
  try {
    const res = await aiPetSummary(petId)
    aiSummaryData.value = res.data
  } catch (e) {
    showToast('AI 摘要获取失败', 'error')
    aiSummaryModal.value = false
  } finally {
    aiSummaryLoading.value = false
  }
}

async function saveDiagnosis() {
  savingDiagnosis.value = true
  try {
    const recordId = editingPet.value?.recent_record_id
    const treatment = editTreatment.value || ''
    const visitDate = editingPet.value?.recent_visit_date || ''
    if (recordId) {
      await updateMedicalRecord(recordId, {
        pet_id: editingPet.value.id,
        diagnosis: editDiagnosis.value,
        treatment,
        visit_date: visitDate,
      })
    } else {
      await createMedicalRecord({
        pet_id: editingPet.value.id,
        diagnosis: editDiagnosis.value,
        treatment: '',
        visit_date: new Date().toISOString().split('T')[0],
      })
      editingPet.value.recent_visit_date = new Date().toISOString().split('T')[0]
    }
    editingPet.value.recent_diagnosis = editDiagnosis.value
    if (!editingPet.value.total_visits || editingPet.value.total_visits === 0) {
      editingPet.value.total_visits = 1
    }
    showToast('诊断已更新')
  } catch (e) {
    showToast('保存失败', 'error')
  } finally {
    savingDiagnosis.value = false
  }
}

async function saveTreatment() {
  savingTreatment.value = true
  try {
    const recordId = editingPet.value?.recent_record_id
    const diagnosis = editDiagnosis.value || ''
    const visitDate = editingPet.value?.recent_visit_date || ''
    if (recordId) {
      await updateMedicalRecord(recordId, {
        pet_id: editingPet.value.id,
        diagnosis,
        treatment: editTreatment.value,
        visit_date: visitDate,
      })
    } else {
      await createMedicalRecord({
        pet_id: editingPet.value.id,
        diagnosis: '',
        treatment: editTreatment.value,
        visit_date: new Date().toISOString().split('T')[0],
      })
      editingPet.value.recent_visit_date = new Date().toISOString().split('T')[0]
    }
    editingPet.value.recent_treatment = editTreatment.value
    if (!editingPet.value.total_visits || editingPet.value.total_visits === 0) {
      editingPet.value.total_visits = 1
    }
    showToast('治疗方案已更新')
  } catch (e) {
    showToast('保存失败', 'error')
  } finally {
    savingTreatment.value = false
  }
}

onMounted(fetchPets)
</script>

<style scoped>
.page {
  max-width: 1100px;
}

.actions {
  display: flex;
  gap: 8px;
}

.search-input {
  width: 200px;
}

.td-actions {
  display: flex;
  gap: 6px;
}

.ai-summary-text {
  background: #f0f9ff;
  border: 1px solid #bae6fd;
  border-radius: var(--radius);
  padding: 14px;
  font-size: 14px;
  line-height: 1.8;
  color: var(--color-text);
  margin-bottom: 16px;
}

.ai-timeline {
  max-height: 200px;
  overflow-y: auto;
}

.tl-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 0;
  border-bottom: 1px solid var(--color-border);
  font-size: 13px;
}

.tl-date {
  color: var(--color-text-secondary);
  flex-shrink: 0;
}

.tl-info {
  color: var(--color-text);
}

.pet-health-brief {
  background: #f0f9ff;
  border: 1px solid #bae6fd;
  border-radius: var(--radius);
  padding: 12px 14px;
  margin-bottom: 16px;
}

.brief-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.brief-row:last-of-type {
  margin-bottom: 8px;
}

.brief-label {
  font-size: 12px;
  color: var(--color-text-secondary);
  min-width: 60px;
}

.brief-value {
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text);
}

.input-sm {
  padding: 4px 8px;
  font-size: 12px;
}
</style>
