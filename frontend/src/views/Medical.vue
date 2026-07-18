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

        <form @submit.prevent="handleSave">
          <div class="inline-form">
            <div class="form-group">
              <label>宠物ID *</label>
              <input v-model.number="form.pet_id" type="number" class="input" required min="1" />
            </div>
            <div class="form-group">
              <label>兽医</label>
              <input v-model="form.vet_name" class="input" />
            </div>
          </div>
          <div class="form-group">
            <label>症状 / 主诉</label>
            <textarea v-model="form.symptoms" class="input" rows="2" placeholder="如：呕吐、腹泻、精神萎靡..."></textarea>
          </div>
          <div class="form-group">
            <label>就诊日期 *</label>
            <input v-model="form.visit_date" type="date" class="input" required />
          </div>
          <div class="form-group">
            <label>诊断</label>
            <textarea v-model="form.diagnosis" class="input" rows="2"></textarea>
          </div>
          <div class="form-group">
            <label>治疗方案</label>
            <textarea v-model="form.treatment" class="input" rows="2"></textarea>
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
import { getMedicalRecords, createMedicalRecord, updateMedicalRecord, deleteMedicalRecord } from '../api'

const records = ref([])
const loading = ref(false)
const showModal = ref(false)
const editingRecord = ref(null)
const saving = ref(false)
const toast = reactive({ show: false, msg: '', type: 'success' })

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

onMounted(() => {
  fetchRecords()
})
</script>

<style scoped>
.page { max-width: 1100px; }
.td-actions { display: flex; gap: 6px; }
</style>
