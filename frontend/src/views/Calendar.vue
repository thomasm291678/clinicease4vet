<template>
  <div class="page calendar-page">
    <div class="card">
      <div class="card-header">
        <span class="card-title">日程日历</span>
        <div class="cal-actions">
          <button class="btn btn-sm" @click="syncNow" :disabled="syncing">{{ syncing ? '同步中...' : '同步诊疗' }}</button>
          <button class="btn btn-primary btn-sm" @click="openCreate()">新建日程</button>
        </div>
      </div>

      <!-- 月导航 -->
      <div class="cal-nav">
        <button class="btn btn-sm btn-outline" @click="prevMonth">&lt;</button>
        <span class="cal-month-label">{{ currentMonthLabel }}</span>
        <button class="btn btn-sm btn-outline" @click="nextMonth">&gt;</button>
        <button class="btn btn-sm" @click="goToday">今天</button>
        <div class="cal-view-tabs">
          <button :class="['tab-sm', viewMode === 'month' ? 'tab-active' : '']" @click="viewMode = 'month'">月</button>
          <button :class="['tab-sm', viewMode === 'week' ? 'tab-active' : '']" @click="viewMode = 'week'">周</button>
          <button :class="['tab-sm', viewMode === 'day' ? 'tab-active' : '']" @click="viewMode = 'day'">日</button>
        </div>
      </div>

      <!-- 月视图 -->
      <div v-if="viewMode === 'month'" class="cal-month-grid">
        <div class="cal-weekday" v-for="d in weekDays" :key="d">{{ d }}</div>
        <div
          v-for="(day, i) in monthDays"
          :key="i"
          :class="['cal-day', { 'is-today': day.isToday, 'is-other-month': !day.isCurrentMonth, 'is-selected': selectedDate === day.dateStr }]"
          @click="selectDate(day.dateStr)"
        >
          <span class="cal-day-num">{{ day.day }}</span>
          <div class="cal-day-events">
            <div
              v-for="evt in day.events.slice(0, 3)"
              :key="evt.id"
              :class="['cal-event-dot', 'type-' + (evt.event_type || 'appointment')]"
              :style="{ background: evt.color }"
              :title="evt.title"
              @click.stop="openDetail(evt)"
            >
              {{ evt.start_time }} {{ evt.title.slice(0, 8) }}
            </div>
            <div v-if="day.events.length > 3" class="cal-more">+{{ day.events.length - 3 }} 更多</div>
          </div>
        </div>
      </div>

      <!-- 周/日视图 -->
      <div v-if="viewMode !== 'month'" class="cal-timeline">
        <div class="cal-timeline-header">
          <div class="tl-hour-label"></div>
          <div v-for="d in timelineDays" :key="d.dateStr" :class="['tl-day-col', { 'is-today': d.isToday }]">
            <span class="tl-day-name">{{ d.weekDay }}</span>
            <span class="tl-day-date">{{ d.day }}</span>
          </div>
        </div>
        <div class="cal-timeline-body">
          <div v-for="h in timeSlots" :key="h" class="tl-row">
            <div class="tl-hour-label">{{ h }}</div>
            <div v-for="d in timelineDays" :key="d.dateStr" class="tl-cell" @click="openCreate(d.dateStr, h)">
              <div
                v-for="evt in getEventsAtHour(d.dateStr, h)"
                :key="evt.id"
                :class="['tl-event', 'type-' + (evt.event_type || 'appointment')]"
                :style="{ background: evt.color || '#2563eb' }"
                @click.stop="openDetail(evt)"
              >
                <span class="tl-event-time">{{ evt.start_time }}-{{ evt.end_time }}</span>
                <span class="tl-event-title">{{ evt.title }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 今日摘要 -->
      <div v-if="selectedDate" class="cal-day-detail">
        <div class="detail-header">
          <span class="detail-date">{{ selectedDateLabel }}</span>
          <button class="btn btn-primary btn-sm" @click="openCreate(selectedDate)">+ 添加日程</button>
        </div>
        <div v-if="selectedEvents.length === 0" class="empty-state">暂无日程</div>
        <div v-for="evt in selectedEvents" :key="evt.id" class="detail-item" :style="{ borderLeftColor: evt.color || '#2563eb' }">
          <div class="di-time">
            <span class="di-time-text">{{ evt.start_time }} - {{ evt.end_time }}</span>
            <span class="badge" :class="'badge-' + getStatusClass(evt)">{{ statusLabels[evt.status] || evt.status }}</span>
          </div>
          <div class="di-title">{{ evt.title }}</div>
          <div v-if="evt.pet_name" class="di-meta">宠物: {{ evt.pet_name }} | 主人: {{ evt.owner_name || '未知' }}</div>
          <div v-if="evt.notes" class="di-notes">{{ evt.notes }}</div>
          <div class="di-actions">
            <button class="btn btn-outline btn-sm" @click="openEdit(evt)">编辑</button>
            <button class="btn btn-danger btn-sm" @click="handleDelete(evt.id)">删除</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 新建/编辑弹窗 -->
    <div v-if="showModal" class="modal-overlay" @click.self="showModal = false">
      <div class="modal">
        <h3 class="modal-title">{{ editingEvent ? '编辑日程' : '新建日程' }}</h3>
        <form @submit.prevent="handleSave">
          <div class="form-group">
            <label>标题 *</label>
            <input v-model="form.title" class="input" required placeholder="如：复诊 - 小白" />
          </div>
          <div class="inline-form">
            <div class="form-group">
              <label>日期 *</label>
              <input v-model="form.event_date" type="date" class="input" required />
            </div>
            <div class="form-group">
              <label>类型</label>
              <select v-model="form.event_type" class="input" @change="onTypeChange">
                <option value="appointment">就诊</option>
                <option value="surgery">手术</option>
                <option value="vaccine">疫苗</option>
                <option value="follow_up">复诊</option>
                <option value="checkup">体检</option>
                <option value="other">其他</option>
              </select>
            </div>
          </div>
          <div class="inline-form">
            <div class="form-group">
              <label>开始时间</label>
              <input v-model="form.start_time" type="time" class="input" />
            </div>
            <div class="form-group">
              <label>结束时间</label>
              <input v-model="form.end_time" type="time" class="input" />
            </div>
          </div>
          <div class="inline-form">
            <div class="form-group">
              <label>宠物名</label>
              <input v-model="form.pet_name" class="input" placeholder="宠物名" />
            </div>
            <div class="form-group">
              <label>主人</label>
              <input v-model="form.owner_name" class="input" placeholder="主人姓名" />
            </div>
          </div>
          <div class="form-group">
            <label>备注</label>
            <textarea v-model="form.notes" class="input" rows="2" placeholder="备注信息..."></textarea>
          </div>
          <div class="inline-form">
            <div class="form-group">
              <label>状态</label>
              <select v-model="form.status" class="input">
                <option value="scheduled">已预约</option>
                <option value="checked_in">已签到</option>
                <option value="in_progress">进行中</option>
                <option value="completed">已完成</option>
                <option value="cancelled">已取消</option>
              </select>
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
import { ref, reactive, computed, onMounted } from 'vue'

const weekDays = ['日', '一', '二', '三', '四', '五', '六']
const timeSlots = ['08:00', '09:00', '10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '16:00', '17:00', '18:00']
const statusLabels = { scheduled: '已预约', checked_in: '已签到', in_progress: '进行中', completed: '已完成', cancelled: '已取消' }

const toast = reactive({ show: false, msg: '', type: 'success' })
const viewMode = ref('month')
const currentDate = ref(new Date())
const selectedDate = ref('')
const events = ref([])
const showModal = ref(false)
const editingEvent = ref(null)
const saving = ref(false)
const syncing = ref(false)

const form = reactive({
  title: '', event_date: '', start_time: '09:00', end_time: '09:30',
  event_type: 'appointment', pet_name: '', owner_name: '', notes: '', status: 'scheduled', color: '#2563eb',
})

const currentMonthLabel = computed(() => {
  return `${currentDate.value.getFullYear()}年 ${currentDate.value.getMonth() + 1}月`
})

const selectedDateLabel = computed(() => {
  if (!selectedDate.value) return ''
  const d = new Date(selectedDate.value)
  return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日 ${weekDays[d.getDay()]}`
})

const selectedEvents = computed(() => {
  return events.value.filter(e => e.event_date === selectedDate.value)
})

function showToast(msg, type = 'success') { toast.msg = msg; toast.type = type; toast.show = true; setTimeout(() => { toast.show = false }, 3000) }

// ===== 月视图 =====
const monthDays = computed(() => {
  const y = currentDate.value.getFullYear()
  const m = currentDate.value.getMonth()
  const first = new Date(y, m, 1)
  const last = new Date(y, m + 1, 0)
  const startDay = first.getDay()
  const daysInMonth = last.getDate()
  const today = new Date()
  const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`

  const days = []
  // 上月尾巴
  const prevLast = new Date(y, m, 0).getDate()
  for (let i = startDay - 1; i >= 0; i--) {
    const d = prevLast - i
    const ds = `${y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`
    days.push({ day: d, dateStr: ds, isToday: ds === todayStr, isCurrentMonth: false, events: getDayEvents(ds) })
  }
  // 本月
  for (let d = 1; d <= daysInMonth; d++) {
    const ds = `${y}-${String(m + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`
    days.push({ day: d, dateStr: ds, isToday: ds === todayStr, isCurrentMonth: true, events: getDayEvents(ds) })
  }
  // 下月头
  const remaining = 42 - days.length
  for (let d = 1; d <= remaining; d++) {
    const ds = `${y}-${String(m + 2).padStart(2, '0')}-${String(d).padStart(2, '0')}`
    days.push({ day: d, dateStr: ds, isToday: ds === todayStr, isCurrentMonth: false, events: getDayEvents(ds) })
  }
  return days
})

// ===== 周/日视图 =====
const timelineDays = computed(() => {
  const days = []
  const d = new Date(currentDate.value)
  const today = new Date()
  const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`

  const count = viewMode.value === 'day' ? 1 : 7
  const start = viewMode.value === 'week' ? d.getDate() - d.getDay() : d.getDate()
  d.setDate(start)

  for (let i = 0; i < count; i++) {
    const ds = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
    days.push({ day: d.getDate(), weekDay: weekDays[d.getDay()], dateStr: ds, isToday: ds === todayStr })
    d.setDate(d.getDate() + 1)
  }
  return days
})

function getDayEvents(dateStr) {
  return events.value.filter(e => e.event_date === dateStr)
}

function getEventsAtHour(dateStr, hour) {
  return events.value.filter(e => e.event_date === dateStr && e.start_time && e.start_time.slice(0, 2) === hour.slice(0, 2))
}

function getStatusClass(evt) {
  if (evt.status === 'completed') return 'green'
  if (evt.status === 'cancelled') return 'red'
  if (evt.status === 'in_progress') return 'blue'
  return 'blue'
}

// ===== 导航 =====
function prevMonth() { const d = new Date(currentDate.value); d.setMonth(d.getMonth() - 1); currentDate.value = d; fetchEvents() }
function nextMonth() { const d = new Date(currentDate.value); d.setMonth(d.getMonth() + 1); currentDate.value = d; fetchEvents() }
function goToday() { currentDate.value = new Date(); selectDate(new Date().toISOString().slice(0, 10)); fetchEvents() }

function selectDate(ds) {
  selectedDate.value = ds
  if (viewMode.value === 'month') viewMode.value = 'day'
  const d = new Date(ds)
  currentDate.value = d
}

// ===== API =====
async function fetchEvents() {
  const d = new Date(currentDate.value)
  const y = d.getFullYear(); const m = d.getMonth()
  const start = `${y}-${String(m).padStart(2, '0')}-01`
  const end = `${y}-${String(m + 2).padStart(2, '0')}-01`
  try {
    const api = await import('../api')
    const res = await api.aiCalendarEvents(start, end)
    events.value = res.data?.events || []
  } catch (e) { /* ignore */ }
}

async function syncNow() {
  syncing.value = true
  try {
    const api = await import('../api')
    const res = await api.aiCalendarSync()
    showToast(res.data?.message || '同步完成')
    fetchEvents()
  } catch (e) { showToast('同步失败', 'error') } finally { syncing.value = false }
}

function openCreate(dateStr, time) {
  editingEvent.value = null
  form.title = ''; form.event_date = dateStr || selectedDate.value || new Date().toISOString().slice(0, 10)
  form.start_time = time || '09:00'
  form.end_time = time ? `${String(parseInt(time) + 1).padStart(2, '0')}:00` : '09:30'
  form.event_type = 'appointment'; form.pet_name = ''; form.owner_name = ''; form.notes = ''; form.status = 'scheduled'
  form.color = '#2563eb'
  showModal.value = true
}

function openEdit(evt) {
  editingEvent.value = evt
  form.title = evt.title || ''; form.event_date = evt.event_date || ''
  form.start_time = evt.start_time || '09:00'; form.end_time = evt.end_time || '09:30'
  form.event_type = evt.event_type || 'appointment'; form.pet_name = evt.pet_name || ''
  form.owner_name = evt.owner_name || ''; form.notes = evt.notes || ''; form.status = evt.status || 'scheduled'
  form.color = evt.color || '#2563eb'
  showModal.value = true
}

function openDetail(evt) {
  selectedDate.value = evt.event_date
  viewMode.value = 'day'
}

function onTypeChange() {
  const colors = { appointment: '#2563eb', surgery: '#dc2626', vaccine: '#16a34a', follow_up: '#f59e0b', checkup: '#8b5cf6', other: '#6b7280' }
  form.color = colors[form.event_type] || '#2563eb'
}

async function handleSave() {
  if (!form.title.trim() || !form.event_date) { showToast('请填写标题和日期', 'error'); return }
  saving.value = true
  try {
    const api = await import('../api')
    const data = { ...form }
    if (editingEvent.value) {
      await api.aiCalendarUpdate(editingEvent.value.id, data)
      showToast('日程已更新')
    } else {
      await api.aiCalendarCreate(data)
      showToast('日程已创建')
    }
    showModal.value = false
    fetchEvents()
  } catch (e) { showToast('保存失败: ' + (e.response?.data?.error || e.message), 'error') } finally { saving.value = false }
}

async function handleDelete(id) {
  if (!confirm('确定删除该日程？')) return
  try {
    const api = await import('../api')
    await api.aiCalendarDelete(id)
    showToast('已删除')
    fetchEvents()
  } catch (e) { showToast('删除失败', 'error') }
}

onMounted(() => {
  selectedDate.value = new Date().toISOString().slice(0, 10)
  fetchEvents()
})
</script>

<style scoped>
.calendar-page { width: 100%; max-width: 1100px; }
.card-header { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px; margin-bottom: 16px; }
.card-title { font-size: 18px; font-weight: 700; color: var(--color-text); }
.cal-actions { display: flex; gap: 8px; }

.cal-nav { display: flex; align-items: center; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; }
.cal-month-label { font-size: 16px; font-weight: 700; color: var(--color-text); min-width: 120px; text-align: center; }
.cal-view-tabs { display: flex; gap: 2px; margin-left: auto; }
.tab-sm { padding: 4px 12px; border: 1px solid var(--color-border); background: #f8fafc; border-radius: var(--radius); font-size: 12px; cursor: pointer; }
.tab-sm:hover { border-color: var(--color-primary); color: var(--color-primary); }
.tab-active { background: var(--color-primary); color: #fff; border-color: var(--color-primary); }

/* 月视图 */
.cal-month-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 1px; background: var(--color-border); border: 1px solid var(--color-border); border-radius: var(--radius); overflow: hidden; }
.cal-weekday { background: #f8fafc; padding: 8px 4px; text-align: center; font-size: 12px; font-weight: 600; color: var(--color-text-secondary); }
.cal-day { background: #fff; min-height: 90px; padding: 4px 6px; cursor: pointer; transition: background 0.1s; }
.cal-day:hover { background: #f0f7ff; }
.cal-day.is-today { background: #eff6ff; }
.cal-day.is-today .cal-day-num { background: var(--color-primary); color: #fff; border-radius: 50%; width: 22px; height: 22px; display: inline-flex; align-items: center; justify-content: center; }
.cal-day.is-other-month { background: #fafafa; }
.cal-day.is-selected { box-shadow: inset 0 0 0 2px var(--color-primary); }
.cal-day-num { font-size: 13px; font-weight: 600; color: var(--color-text); }
.cal-day-events { margin-top: 4px; }
.cal-event-dot { font-size: 10px; padding: 1px 4px; border-radius: 3px; color: #fff; margin-bottom: 1px; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; cursor: pointer; }
.cal-more { font-size: 10px; color: var(--color-text-light); margin-top: 2px; }

/* 周/日时间线 */
.cal-timeline { border: 1px solid var(--color-border); border-radius: var(--radius); overflow: hidden; }
.cal-timeline-header { display: flex; background: #f8fafc; border-bottom: 1px solid var(--color-border); }
.tl-hour-label { width: 60px; flex-shrink: 0; }
.tl-day-col { flex: 1; text-align: center; padding: 8px 4px; border-left: 1px solid var(--color-border); }
.tl-day-col.is-today { background: #eff6ff; }
.tl-day-name { display: block; font-size: 11px; color: var(--color-text-secondary); }
.tl-day-date { display: block; font-size: 16px; font-weight: 700; color: var(--color-text); }
.cal-timeline-body { max-height: 500px; overflow-y: auto; }
.tl-row { display: flex; border-bottom: 1px solid #f1f5f9; min-height: 50px; }
.tl-row:last-child { border-bottom: none; }
.tl-hour-label { width: 60px; flex-shrink: 0; padding: 4px 8px; font-size: 11px; color: var(--color-text-light); text-align: right; border-right: 1px solid var(--color-border); }
.tl-cell { flex: 1; border-left: 1px solid #f1f5f9; padding: 2px; cursor: pointer; position: relative; }
.tl-cell:hover { background: #f8fafc; }
.tl-event { font-size: 10px; color: #fff; padding: 2px 4px; border-radius: 3px; margin-bottom: 1px; cursor: pointer; overflow: hidden; }
.tl-event-time { font-weight: 600; margin-right: 4px; }
.tl-event-title { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

/* 日详情 */
.cal-day-detail { margin-top: 20px; padding-top: 16px; border-top: 1px solid var(--color-border); }
.detail-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.detail-date { font-size: 15px; font-weight: 700; color: var(--color-text); }
.detail-item { background: #f8fafc; border: 1px solid var(--color-border); border-left: 4px solid #2563eb; border-radius: var(--radius); padding: 12px 14px; margin-bottom: 8px; }
.di-time { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.di-time-text { font-size: 12px; color: var(--color-text-secondary); font-weight: 600; }
.di-title { font-size: 14px; font-weight: 600; color: var(--color-text); margin-bottom: 4px; }
.di-meta { font-size: 12px; color: var(--color-text-secondary); }
.di-notes { font-size: 12px; color: var(--color-text-light); margin-top: 4px; }
.di-actions { display: flex; gap: 6px; margin-top: 8px; }

@media (max-width: 768px) {
  .cal-month-grid { font-size: 11px; }
  .cal-day { min-height: 60px; padding: 2px 3px; }
  .tl-hour-label { width: 40px; font-size: 10px; }
}
</style>
