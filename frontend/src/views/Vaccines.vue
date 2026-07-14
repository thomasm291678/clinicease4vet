<template>
  <div class="page">
    <div class="card">
      <div class="card-header">
        <span class="card-title">疫苗接种记录</span>
        <button class="btn btn-primary btn-sm" @click="openCreate">添加记录</button>
      </div>

      <div v-if="loading" class="loading"><span class="spinner"></span>加载中...</div>

      <table v-else-if="records.length">
        <thead>
          <tr>
            <th>宠物</th>
            <th>种类</th>
            <th>主人</th>
            <th>疫苗名称</th>
            <th>剂量</th>
            <th>接种日期</th>
            <th>下次接种</th>
            <th>兽医</th>
            <th>批号</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in records" :key="r.id">
            <td><strong>{{ r.pet_name || '宠物#' + r.pet_id }}</strong></td>
            <td>{{ r.species || '-' }}</td>
            <td><strong>{{ r.owner_name || '-' }}</strong></td>
            <td><strong>{{ r.vaccine_name }}</strong></td>
            <td>{{ r.dose_number || 1 }}</td>
            <td>{{ r.administered_date }}</td>
            <td>
              <span v-if="r.next_due_date" :class="r.next_due_date <= today ? 'badge badge-red' : 'badge badge-green'">
                {{ r.next_due_date }}
              </span>
              <span v-else>-</span>
            </td>
            <td>{{ r.vet_name || '-' }}</td>
            <td>{{ r.batch_number || '-' }}</td>
            <td>
              <button class="btn btn-danger btn-sm" @click="handleDelete(r.id)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else class="empty-state">暂无疫苗接种记录</div>
    </div>

    <div v-if="showModal" class="modal-overlay" @click.self="showModal = false">
      <div class="modal">
        <h3 class="modal-title">添加疫苗接种记录</h3>
        <form @submit.prevent="handleSave">
          <div class="form-group">
            <label>宠物 *</label>
            <select v-model.number="form.pet_id" class="input" required>
              <option :value="null" disabled>请选择宠物</option>
              <option v-for="p in petList" :key="p.id" :value="p.id">
                {{ p.name }} ({{ p.species }}{{ p.breed ? ' · ' + p.breed : '' }}) — {{ p.owner_name }}
              </option>
            </select>
          </div>
          <div class="inline-form">
            <div class="form-group">
              <label>疫苗名称 *</label>
              <div style="display:flex;align-items:center;gap:4px;">
                <input v-model="form.vaccine_name" class="input" required />
                <VoiceInput v-model="form.vaccine_name" size="sm" />
              </div>
            </div>
            <div class="form-group">
              <label>剂量</label>
              <input v-model.number="form.dose_number" type="number" class="input" min="1" />
            </div>
          </div>
          <div class="inline-form">
            <div class="form-group">
              <label>接种日期 *</label>
              <input v-model="form.administered_date" type="date" class="input" required />
            </div>
            <div class="form-group">
              <label>下次接种</label>
              <input v-model="form.next_due_date" type="date" class="input" />
            </div>
          </div>
          <div class="inline-form">
            <div class="form-group">
              <label>兽医</label>
              <div style="display:flex;align-items:center;gap:4px;">
                <input v-model="form.vet_name" class="input" />
                <VoiceInput v-model="form.vet_name" size="sm" />
              </div>
            </div>
            <div class="form-group">
              <label>批号</label>
              <input v-model="form.batch_number" class="input" />
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
import { ref, reactive, onMounted, watch } from 'vue'
import { getVaccinations, createVaccination, deleteVaccination, getPets } from '../api'
import { useAiVoiceStore } from '../stores/aiVoice'

const aiVoice = useAiVoiceStore()
import VoiceInput from '../components/VoiceInput.vue'

const records = ref([])
const petList = ref([])
const loading = ref(false)
const showModal = ref(false)
const saving = ref(false)
const toast = reactive({ show: false, msg: '', type: 'success' })

const today = new Date().toISOString().split('T')[0]

const form = reactive({
  pet_id: null, vaccine_name: '', dose_number: 1, administered_date: '',
  next_due_date: '', vet_name: '', batch_number: '', notes: '',
})

function showToast(msg, type = 'success') {
  toast.msg = msg; toast.type = type; toast.show = true
  setTimeout(() => { toast.show = false }, 3000)
}

function resetForm() {
  form.pet_id = null; form.vaccine_name = ''; form.dose_number = 1
  form.administered_date = ''; form.next_due_date = ''; form.vet_name = ''
  form.batch_number = ''; form.notes = ''
}

async function fetchRecords() {
  loading.value = true
  try {
    const [vacRes, petRes] = await Promise.all([getVaccinations(), getPets()])
    records.value = vacRes.data.data || []
    petList.value = petRes.data.data || []
  } catch (e) {
    showToast('加载失败', 'error')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  resetForm()

  const prefill = localStorage.getItem('ai_prefill_vaccine')
  if (prefill) {
    try {
      const vf = JSON.parse(prefill)
      if (vf.vaccine_name) form.vaccine_name = vf.vaccine_name
      if (vf.vet_name) form.vet_name = vf.vet_name
      if (vf.administered_date) form.administered_date = vf.administered_date
      if (vf.next_due_date) form.next_due_date = vf.next_due_date
      localStorage.removeItem('ai_prefill_vaccine')
    } catch (e) { /* ignore */ }
  }

  showModal.value = true
}

async function handleSave() {
  saving.value = true
  try {
    await createVaccination({ ...form })
    showToast('添加成功')
    showModal.value = false
    fetchRecords()
  } catch (e) {
    showToast(e.response?.data?.error || '保存失败', 'error')
  } finally {
    saving.value = false
  }
}

async function handleDelete(id) {
  if (!confirm('确定删除该记录？')) return
  try {
    await deleteVaccination(id)
    showToast('删除成功')
    fetchRecords()
  } catch (e) {
    showToast('删除失败', 'error')
  }
}

onMounted(fetchRecords)

watch(() => aiVoice.lastResult, (result) => {
  if (!result || !result.vaccineInfo) return
  const info = result.vaccineInfo
  if (!info.vaccine_name) return
  resetForm()
  if (info.vaccine_name) form.vaccine_name = info.vaccine_name
  if (info.vet_name) form.vet_name = info.vet_name
  if (info.administered_date) form.administered_date = info.administered_date
  if (info.next_due_date) form.next_due_date = info.next_due_date
  if (info.batch_number) form.batch_number = info.batch_number
  if (info.dose_number) form.dose_number = info.dose_number
  showModal.value = true
  aiVoice.consumeResult()
}, { deep: true })
</script>

<style scoped>
.page { max-width: 1100px; }
</style>
