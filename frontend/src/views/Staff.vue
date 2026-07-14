<template>
  <div class="page">
    <div class="staff-tabs">
      <button :class="['tab', activeTab === 'vet' ? 'tab-active' : '']" @click="switchTab('vet')">兽医</button>
      <button :class="['tab', activeTab === 'assistant' ? 'tab-active' : '']" @click="switchTab('assistant')">助理</button>
      <button :class="['tab', activeTab === 'worker' ? 'tab-active' : '']" @click="switchTab('worker')">其他员工</button>
    </div>

    <div class="card">
      <div class="card-header">
        <span class="card-title">{{ tabLabel }}</span>
        <button class="btn btn-primary btn-sm" @click="openCreate">添加</button>
      </div>

      <div v-if="loading" class="loading"><span class="spinner"></span>加载中...</div>

      <table v-else-if="staff.length">
        <thead>
          <tr>
            <th>姓名</th>
            <th v-if="activeTab === 'vet'">专业</th>
            <th v-if="activeTab === 'vet'">执照号</th>
            <th v-else>角色</th>
            <th>年龄</th>
            <th>联系方式</th>
            <th v-if="activeTab === 'vet'">问诊费</th>
            <th>月薪</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="s in staff" :key="s.id">
            <td><strong>{{ s.name }}</strong></td>
            <td v-if="activeTab === 'vet'">{{ s.specialisation || '-' }}</td>
            <td v-else-if="activeTab === 'vet'">{{ s.license_no || '-' }}</td>
            <td v-else>{{ s.role || '-' }}</td>
            <td>{{ s.age || '-' }}</td>
            <td>{{ s.contact || '-' }}</td>
            <td v-if="activeTab === 'vet'">{{ s.consultation_fee || '-' }}</td>
            <td>{{ s.monthly_salary || '-' }}</td>
            <td>
              <button class="btn btn-danger btn-sm" @click="handleDelete(s.id)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else class="empty-state">暂无数据</div>
    </div>

    <div v-if="showModal" class="modal-overlay" @click.self="showModal = false">
      <div class="modal">
        <h3 class="modal-title">添加{{ tabLabel }}</h3>
        <form @submit.prevent="handleSave">
          <div class="inline-form">
            <div class="form-group">
              <label>姓名 *</label>
              <input v-model="form.name" class="input" required />
            </div>
            <div v-if="activeTab !== 'vet'" class="form-group">
              <label>角色</label>
              <input v-model="form.role" class="input" />
            </div>
            <div v-if="activeTab === 'vet'" class="form-group">
              <label>专业</label>
              <input v-model="form.specialisation" class="input" />
            </div>
            <div class="form-group">
              <label>年龄</label>
              <input v-model.number="form.age" type="number" class="input" min="0" />
            </div>
            <div v-if="activeTab === 'vet'" class="form-group">
              <label>执照号</label>
              <input v-model="form.license_no" class="input" />
            </div>
            <div class="form-group">
              <label>联系方式</label>
              <input v-model="form.contact" class="input" />
            </div>
            <div v-if="activeTab === 'vet'" class="form-group">
              <label>问诊费</label>
              <input v-model.number="form.consultation_fee" type="number" class="input" min="0" />
            </div>
            <div class="form-group">
              <label>月薪</label>
              <input v-model.number="form.monthly_salary" type="number" class="input" min="0" />
            </div>
            <div class="form-group full-width">
              <label>地址</label>
              <input v-model="form.address" class="input" />
            </div>
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
import { ref, reactive, computed } from 'vue'
import { getStaff, createStaff, deleteStaff } from '../api'

const activeTab = ref('vet')
const staff = ref([])
const loading = ref(false)
const showModal = ref(false)
const saving = ref(false)
const toast = reactive({ show: false, msg: '', type: 'success' })

const tabLabel = computed(() => {
  const map = { vet: '兽医', assistant: '助理', worker: '其他员工' }
  return map[activeTab.value] || ''
})

const form = reactive({
  name: '', role: '', specialisation: '', license_no: '', age: null,
  address: '', contact: '', consultation_fee: null, monthly_salary: null,
})

function showToast(msg, type = 'success') {
  toast.msg = msg; toast.type = type; toast.show = true
  setTimeout(() => { toast.show = false }, 3000)
}

function resetForm() {
  Object.keys(form).forEach(k => { form[k] = null })
  form.name = ''
  form.role = ''
}

async function switchTab(tab) {
  activeTab.value = tab
  await fetchStaff()
}

async function fetchStaff() {
  loading.value = true
  try {
    const res = await getStaff(activeTab.value)
    staff.value = res.data.data || res.data || []
  } catch (e) {
    showToast('加载失败', 'error')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  resetForm()
  showModal.value = true
}

async function handleSave() {
  saving.value = true
  try {
    await createStaff(activeTab.value, { ...form })
    showToast('添加成功')
    showModal.value = false
    fetchStaff()
  } catch (e) {
    showToast(e.response?.data?.error || '保存失败', 'error')
  } finally {
    saving.value = false
  }
}

async function handleDelete(id) {
  if (!confirm('确定删除？')) return
  try {
    await deleteStaff(activeTab.value, id)
    showToast('删除成功')
    fetchStaff()
  } catch (e) {
    showToast('删除失败', 'error')
  }
}

switchTab('vet')
</script>

<style scoped>
.page { max-width: 1100px; }

.staff-tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 16px;
}

.tab {
  padding: 8px 20px;
  background: #fff;
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-secondary);
  transition: all 0.15s;
}

.tab:hover {
  color: var(--color-primary);
  border-color: var(--color-primary);
}

.tab-active {
  background: var(--color-primary);
  color: #fff;
  border-color: var(--color-primary);
}

.tab-active:hover {
  color: #fff;
}
</style>
