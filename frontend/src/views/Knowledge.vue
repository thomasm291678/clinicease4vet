<template>
  <div class="page kb-page">
    <div class="card">
      <div class="card-header">
        <span class="card-title">兽医知识库</span>
        <span v-if="kbStats" class="badge badge-green">{{ kbStats.total_chunks || 0 }} 篇文献</span>
      </div>

      <!-- 搜索栏 -->
      <div class="kb-search-bar">
        <div class="search-input-wrap">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="search-icon">
            <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
          </svg>
          <input
            v-model="searchQuery"
            class="input search-input"
            placeholder="搜索兽医知识：药物指南、疾病、症状、诊疗方案..."
            @keyup.enter="doSearch"
          />
        </div>
        <button class="btn btn-primary" @click="doSearch" :disabled="searching">
          {{ searching ? '搜索中...' : '搜索' }}
        </button>
      </div>

      <!-- 搜索结果 -->
      <div v-if="searchResults.length > 0" class="kb-results">
        <div class="results-header">
          找到 {{ searchResults.length }} 条相关文献
        </div>
        <div v-for="(r, i) in searchResults" :key="i" class="kb-result-item">
          <div class="kb-result-source">
            <span class="badge badge-blue">{{ r.source || r.chapter || '知识库' }}</span>
            <span v-if="r.score" class="kb-score">相关度: {{ (r.score * 100).toFixed(0) }}%</span>
          </div>
          <p class="kb-result-text">{{ r.text || r.content }}</p>
        </div>
      </div>

      <!-- AI 问答 -->
      <div class="kb-chat-section">
        <div class="section-title">AI 兽医问答</div>
        <div class="chat-input-row">
          <input v-model="chatQuestion" class="input" placeholder="输入兽医专业问题..." @keyup.enter="doChat" />
          <select v-model="chatSpecies" class="input" style="width:100px;">
            <option value="狗">狗</option>
            <option value="猫">猫</option>
            <option value="兔">兔</option>
            <option value="鸟">鸟</option>
            <option value="其他">其他</option>
          </select>
          <button class="btn btn-primary" @click="doChat" :disabled="chatting">
            {{ chatting ? '回答中...' : '提问' }}
          </button>
        </div>

        <div v-if="chatAnswer" class="chat-answer-card">
          <div class="answer-header">
            <span class="badge badge-blue">AI 回答</span>
            <span class="answer-species">{{ chatSpecies }}</span>
          </div>
          <div class="answer-text" v-text="chatAnswer"></div>
        </div>
      </div>

      <!-- 药物安全快速检测 -->
      <div class="kb-drug-section">
        <div class="section-title">药物安全快速检测</div>
        <div class="drug-check-row">
          <input v-model="drugName" class="input" placeholder="药物名称" style="flex:1;" />
          <select v-model="drugSpecies" class="input" style="width:100px;">
            <option value="狗">狗</option>
            <option value="猫">猫</option>
          </select>
          <input v-model="drugWeight" class="input" placeholder="体重(kg)" style="width:100px;" type="number" step="0.1" />
          <button class="btn btn-primary" @click="doDrugCheck" :disabled="drugChecking">
            {{ drugChecking ? '检测中...' : '检测' }}
          </button>
        </div>

        <div v-if="drugResult" class="drug-result-card" :class="'severity-' + (drugResult.risk_level || 'low')">
          <div class="drug-result-header">
            <span class="badge" :class="drugResult.safe ? 'badge-green' : 'badge-red'">
              {{ drugResult.safe ? '安全' : '风险' }}
            </span>
            <span v-if="drugResult.risk_level">风险等级: {{ drugResult.risk_level }}</span>
          </div>
          <p v-if="drugResult.summary">{{ drugResult.summary }}</p>
          <ul v-if="drugResult.warnings?.length">
            <li v-for="(w, i) in drugResult.warnings" :key="i">{{ w }}</li>
          </ul>
          <p v-if="drugResult.recommendation">{{ drugResult.recommendation }}</p>
        </div>
      </div>

      <!-- 知识库统计 -->
      <div v-if="kbStats" class="kb-stats">
        <div class="stat-item">
          <span class="stat-val">{{ kbStats.total_chunks || 0 }}</span>
          <span class="stat-label">知识片段</span>
        </div>
        <div class="stat-item">
          <span class="stat-val">{{ kbStats.total_sources || 0 }}</span>
          <span class="stat-label">文献来源</span>
        </div>
        <div class="stat-item">
          <span class="stat-val">{{ kbStats.embedding_model || 'BGE' }}</span>
          <span class="stat-label">嵌入模型</span>
        </div>
      </div>
    </div>

    <div v-if="toast.show" :class="['toast', 'toast-' + toast.type]">{{ toast.msg }}</div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { aiKbSearch, aiKbChat, aiKbStats, aiDrugSafety } from '../api'

const searchQuery = ref('')
const searchResults = ref([])
const searching = ref(false)

const chatQuestion = ref('')
const chatSpecies = ref('狗')
const chatAnswer = ref('')
const chatting = ref(false)

const drugName = ref('')
const drugSpecies = ref('狗')
const drugWeight = ref('')
const drugResult = ref(null)
const drugChecking = ref(false)

const kbStats = ref(null)
const toast = reactive({ show: false, msg: '', type: 'success' })

function showToast(msg, type = 'success') {
  toast.msg = msg; toast.type = type; toast.show = true
  setTimeout(() => { toast.show = false }, 3000)
}

async function doSearch() {
  if (!searchQuery.value.trim()) { showToast('请输入搜索关键词', 'error'); return }
  searching.value = true
  try {
    const res = await aiKbSearch(searchQuery.value, 10)
    searchResults.value = res.data?.results || []
    if (searchResults.value.length === 0) {
      showToast('未找到相关文献，尝试用 AI 问答')
    }
  } catch (e) {
    showToast('搜索失败: ' + (e.response?.data?.error || e.message), 'error')
  } finally {
    searching.value = false
  }
}

async function doChat() {
  if (!chatQuestion.value.trim()) { showToast('请输入问题', 'error'); return }
  chatting.value = true
  try {
    const res = await aiKbChat(chatQuestion.value, chatSpecies.value)
    chatAnswer.value = res.data?.answer || '未获取到回答'
  } catch (e) {
    showToast('问答失败: ' + (e.response?.data?.error || e.message), 'error')
  } finally {
    chatting.value = false
  }
}

async function doDrugCheck() {
  if (!drugName.value.trim()) { showToast('请输入药物名称', 'error'); return }
  drugChecking.value = true
  try {
    const res = await aiDrugSafety(drugName.value, drugSpecies.value, drugWeight.value ? parseFloat(drugWeight.value) : undefined)
    drugResult.value = res.data
  } catch (e) {
    showToast('检测失败: ' + (e.response?.data?.error || e.message), 'error')
  } finally {
    drugChecking.value = false
  }
}

onMounted(async () => {
  try {
    const res = await aiKbStats()
    kbStats.value = res.data
  } catch (e) { /* ignore */ }
})
</script>

<style scoped>
.kb-page { width: 100%; }
.card-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; flex-wrap: wrap; gap: 10px; }
.card-title { font-size: 18px; font-weight: 700; color: var(--color-text); }

.kb-search-bar { display: flex; gap: 10px; margin-bottom: 20px; }
.search-input-wrap { flex: 1; position: relative; }
.search-icon { position: absolute; left: 10px; top: 50%; transform: translateY(-50%); color: var(--color-text-light); }
.search-input { padding-left: 36px; }

.kb-results { margin-bottom: 24px; }
.results-header { font-size: 13px; font-weight: 600; color: var(--color-text-secondary); margin-bottom: 12px; }
.kb-result-item { background: #f8fafc; border: 1px solid var(--color-border); border-radius: var(--radius); padding: 12px 14px; margin-bottom: 8px; }
.kb-result-source { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.kb-score { font-size: 11px; color: var(--color-text-light); }
.kb-result-text { font-size: 13px; color: var(--color-text); line-height: 1.6; }

.section-title { font-size: 15px; font-weight: 600; color: var(--color-text); margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid var(--color-border); }

.chat-input-row, .drug-check-row { display: flex; gap: 8px; margin-bottom: 16px; }

.chat-answer-card, .drug-result-card { background: #f0f9ff; border: 1px solid #bae6fd; border-radius: var(--radius); padding: 16px; margin-bottom: 24px; }
.answer-header, .drug-result-header { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.answer-text { font-size: 14px; color: var(--color-text); line-height: 1.7; white-space: pre-wrap; }
.answer-species { font-size: 12px; color: var(--color-text-secondary); }

.kb-drug-section { margin-bottom: 24px; }
.drug-result-card.severity-high { background: #fef2f2; border-color: #fecaca; }
.drug-result-card.severity-medium { background: #fffbeb; border-color: #fde68a; }
.drug-result-card ul { margin: 8px 0; padding-left: 20px; font-size: 13px; }
.drug-result-card li { color: var(--color-text); margin-bottom: 4px; }

.kb-stats { display: flex; gap: 20px; padding-top: 16px; border-top: 1px solid var(--color-border); }
.stat-item { display: flex; flex-direction: column; align-items: center; }
.stat-val { font-size: 20px; font-weight: 700; color: var(--color-primary); }
.stat-label { font-size: 11px; color: var(--color-text-light); margin-top: 2px; }

@media (max-width: 768px) {
  .chat-input-row, .drug-check-row { flex-wrap: wrap; }
  .kb-stats { flex-wrap: wrap; gap: 16px; }
}
</style>
