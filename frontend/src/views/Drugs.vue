<template>
  <div class="page">
    <div class="card">
      <div class="card-header">
        <span class="card-title">药品库存</span>
        <button class="btn btn-primary btn-sm" @click="openCreate">添加药品</button>
      </div>

      <div v-if="loading" class="loading"><span class="spinner"></span>加载中...</div>

      <table v-else-if="drugs.length">
        <thead>
          <tr>
            <th>药品名称</th>
            <th>类别</th>
            <th>数量</th>
            <th>单位</th>
            <th>单价</th>
            <th>有效期</th>
            <th>状态</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="d in drugs" :key="d.id">
            <td><strong>{{ d.drug_name }}</strong></td>
            <td>{{ d.category || '-' }}</td>
            <td>{{ d.quantity }}</td>
            <td>{{ d.unit || '瓶' }}</td>
            <td>{{ d.unit_price || '-' }}</td>
            <td>{{ d.expiry_date || '-' }}</td>
            <td>
              <span :class="['badge', d.quantity <= (d.min_stock_level || 5) ? 'badge-red' : 'badge-green']">
                {{ d.quantity <= (d.min_stock_level || 5) ? '低库存' : '正常' }}
              </span>
            </td>
            <td>
              <div class="td-actions">
                <button class="btn btn-outline btn-sm" @click="openStock(d, 'in')">入库</button>
                <button class="btn btn-outline btn-sm" @click="openStock(d, 'out')">出库</button>
                <button class="btn btn-outline btn-sm" @click="openEdit(d)">编辑</button>
                <button class="btn btn-danger btn-sm" @click="handleDelete(d.id)">删除</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else class="empty-state">暂无药品</div>
    </div>

    <div v-if="showModal" class="modal-overlay" @click.self="showModal = false">
      <div class="modal">
        <h3 class="modal-title">{{ editingDrug ? '编辑药品' : '添加药品' }}</h3>
        <form @submit.prevent="handleSave">
          <div class="inline-form">
            <div class="form-group">
              <label>药品名称 *</label>
              <div style="display:flex;align-items:center;gap:4px;">
                <input v-model="form.drug_name" class="input" required />
                <VoiceInput v-model="form.drug_name" size="sm" />
              </div>
            </div>
            <div class="form-group">
              <label>类别</label>
              <input v-model="form.category" class="input" />
            </div>
          </div>
          <div class="inline-form">
            <div class="form-group">
              <label>数量</label>
              <input v-model.number="form.quantity" type="number" class="input" min="0" />
            </div>
            <div class="form-group">
              <label>单位</label>
              <input v-model="form.unit" class="input" />
            </div>
          </div>
          <div class="inline-form">
            <div class="form-group">
              <label>单价</label>
              <input v-model.number="form.unit_price" type="number" class="input" min="0" step="0.01" />
            </div>
            <div class="form-group">
              <label>有效期</label>
              <input v-model="form.expiry_date" type="date" class="input" />
            </div>
          </div>
          <div class="inline-form">
            <div class="form-group">
              <label>最低库存</label>
              <input v-model.number="form.min_stock_level" type="number" class="input" min="0" />
            </div>
            <div class="form-group">
              <label>存储条件</label>
              <input v-model="form.storage_condition" class="input" />
            </div>
          </div>
          <div class="form-group">
            <label>生产商</label>
            <input v-model="form.manufacturer" class="input" />
          </div>
          <div class="modal-actions">
            <button type="button" class="btn btn-outline" @click="showModal = false">取消</button>
            <button type="submit" class="btn btn-primary" :disabled="saving">{{ saving ? '保存中...' : '保存' }}</button>
          </div>
        </form>
      </div>
    </div>

    <div v-if="stockModal" class="modal-overlay" @click.self="stockModal = false">
      <div class="modal">
        <h3 class="modal-title">{{ stockType === 'in' ? '药品入库' : '药品出库' }} - {{ stockDrug?.drug_name }}</h3>
        <form @submit.prevent="handleStock">
          <div class="form-group">
            <label>数量 *</label>
            <input v-model.number="stockQty" type="number" class="input" required min="1" />
          </div>
          <div class="modal-actions">
            <button type="button" class="btn btn-outline" @click="stockModal = false">取消</button>
            <button type="submit" class="btn btn-primary" :disabled="stockSaving">确认</button>
          </div>
        </form>
      </div>
    </div>

    <div v-if="toast.show" :class="['toast', 'toast-' + toast.type]">{{ toast.msg }}</div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { getDrugs, createDrug, updateDrug, deleteDrug, drugStockIn, drugStockOut } from '../api'
import VoiceInput from '../components/VoiceInput.vue'

const drugs = ref([])
const loading = ref(false)
const showModal = ref(false)
const editingDrug = ref(null)
const saving = ref(false)
const stockModal = ref(false)
const stockDrug = ref(null)
const stockType = ref('in')
const stockQty = ref(1)
const stockSaving = ref(false)
const toast = reactive({ show: false, msg: '', type: 'success' })

const form = reactive({
  drug_name: '', category: '', manufacturer: '', batch_number: '',
  quantity: 0, unit: '瓶', unit_price: null, expiry_date: '',
  storage_condition: '', min_stock_level: 5, notes: '',
})

function showToast(msg, type = 'success') {
  toast.msg = msg; toast.type = type; toast.show = true
  setTimeout(() => { toast.show = false }, 3000)
}

function resetForm() {
  Object.keys(form).forEach(k => { form[k] = form.unit === '瓶' ? '瓶' : (typeof form[k] === 'number' ? (k === 'min_stock_level' ? 5 : 0) : '') })
}

async function fetchDrugs() {
  loading.value = true
  try {
    const res = await getDrugs()
    drugs.value = res.data.data || []
  } catch (e) {
    showToast('加载失败', 'error')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingDrug.value = null
  resetForm()
  showModal.value = true
}

function openEdit(d) {
  editingDrug.value = d
  Object.keys(form).forEach(k => { form[k] = d[k] ?? '' })
  showModal.value = true
}

async function handleSave() {
  saving.value = true
  try {
    const data = { ...form }
    if (editingDrug.value) {
      await updateDrug(editingDrug.value.id, data)
      showToast('更新成功')
    } else {
      await createDrug(data)
      showToast('添加成功')
    }
    showModal.value = false
    fetchDrugs()
  } catch (e) {
    showToast(e.response?.data?.error || '保存失败', 'error')
  } finally {
    saving.value = false
  }
}

async function handleDelete(id) {
  if (!confirm('确定删除该药品？')) return
  try {
    await deleteDrug(id)
    showToast('删除成功')
    fetchDrugs()
  } catch (e) {
    showToast('删除失败', 'error')
  }
}

function openStock(d, type) {
  stockDrug.value = d
  stockType.value = type
  stockQty.value = 1
  stockModal.value = true
}

async function handleStock() {
  stockSaving.value = true
  try {
    if (stockType.value === 'in') {
      await drugStockIn(stockDrug.value.id, stockQty.value)
    } else {
      await drugStockOut(stockDrug.value.id, stockQty.value)
    }
    showToast('操作成功')
    stockModal.value = false
    fetchDrugs()
  } catch (e) {
    showToast(e.response?.data?.error || '操作失败', 'error')
  } finally {
    stockSaving.value = false
  }
}

onMounted(fetchDrugs)
</script>

<style scoped>
.page { max-width: 1100px; }
.td-actions { display: flex; gap: 4px; flex-wrap: wrap; }
</style>
