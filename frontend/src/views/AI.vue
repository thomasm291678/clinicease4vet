<template>
  <div class="page ai-page">
    <div class="card">
      <div class="card-header">
        <span class="card-title">AI 智能工作台</span>
        <span class="badge" :class="engineOk ? 'badge-green' : 'badge-red'">
          {{ engineOk ? 'DeepSeek 已连接' : 'DeepSeek 未连接' }}
        </span>
      </div>

      <!-- Tabs -->
      <div class="ai-tabs">
        <button :class="['tab', tab === 'voice' ? 'tab-active' : '']" @click="tab = 'voice'">语音录入</button>
        <button :class="['tab', tab === 'parse' ? 'tab-active' : '']" @click="tab = 'parse'">病历解析</button>
        <button :class="['tab', tab === 'suggest' ? 'tab-active' : '']" @click="tab = 'suggest'">疾病建议</button>
        <button :class="['tab', tab === 'image' ? 'tab-active' : '']" @click="tab = 'image'">影像分析</button>
        <button :class="['tab', tab === 'multiagent' ? 'tab-active' : '']" @click="tab = 'multiagent'">会诊</button>
        <button :class="['tab', tab === 'grpo' ? 'tab-active' : '']" @click="tab = 'grpo'">GRPO</button>
        <button :class="['tab', tab === 'triage' ? 'tab-active' : '']" @click="tab = 'triage'">分诊</button>
        <button :class="['tab', tab === 'guided' ? 'tab-active' : '']" @click="tab = 'guided'">引导诊断</button>
      </div>

      <!-- ========== 语音录入（联动模式）========== -->
      <div v-if="tab === 'voice'" class="voice-workspace">
        <div class="voice-center">
          <button :class="['btn-voice-record', recording ? 'is-recording' : '']" @click="startVoiceRecording" :disabled="aiBusy || uploading || applyAllRunning">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/>
            </svg>
          </button>
          <p class="voice-label">{{ uploading ? '识别中...' : aiBusy ? 'AI 解析中...' : recording ? '录音中... 点击停止' : applyAllRunning ? '录入中...' : '点击开始录音，一次性录入所有信息' }}</p>
          <p v-if="voiceText && !uploading && !applyAllRunning" class="voice-result">{{ voiceText }}</p>
        </div>

        <!-- 解析结果汇总 -->
        <div v-if="voiceResult" class="voice-summary">
          <div class="summary-header">
            <span class="summary-title">AI 识别结果汇总</span>
            <span class="badge badge-blue">一次录入 · 联动全部模块</span>
          </div>

          <div class="summary-grid">
            <div class="summary-block" :class="{ filled: voiceResult.pet_form?.name }">
              <div class="sb-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/></svg>
              </div>
              <div class="sb-content">
                <strong>宠物档案</strong>
                <p v-if="voiceResult.pet_form?.name">{{ voiceResult.pet_form.name }} / {{ voiceResult.pet_form.species || '?' }} / {{ voiceResult.pet_form.breed || '?' }}</p>
                <p v-else class="sb-empty">未识别到宠物信息</p>
              </div>
              <span v-if="applyResults.pet === 'done'" class="sb-check">✓</span>
              <span v-else-if="applyResults.pet === 'error'" class="sb-err">✗</span>
            </div>
            <div class="summary-block" :class="{ filled: voiceResult.medical_form?.diagnosis }">
              <div class="sb-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
              </div>
              <div class="sb-content">
                <strong>诊疗记录</strong>
                <p v-if="voiceResult.medical_form?.diagnosis">诊断: {{ voiceResult.medical_form.diagnosis }}</p>
                <p v-else class="sb-empty">未识别到诊疗信息</p>
              </div>
              <span v-if="applyResults.medical === 'done'" class="sb-check">✓</span>
              <span v-else-if="applyResults.medical === 'error'" class="sb-err">✗</span>
            </div>
            <div class="summary-block" :class="{ filled: voiceResult.vaccine_form }">
              <div class="sb-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
              </div>
              <div class="sb-content">
                <strong>疫苗接种</strong>
                <p v-if="voiceResult.vaccine_form">{{ voiceResult.vaccine_form.vaccine_name || '疫苗' }}</p>
                <p v-else class="sb-empty">未识别到疫苗信息</p>
              </div>
              <span v-if="applyResults.vaccine === 'done'" class="sb-check">✓</span>
              <span v-else-if="applyResults.vaccine === 'error'" class="sb-err">✗</span>
            </div>
          </div>

          <!-- 一键应用按钮 -->
          <div class="apply-all-bar">
            <button
              class="btn btn-primary btn-lg apply-all-btn"
              @click="applyAllRecords"
              :disabled="applyAllRunning || !voiceResult"
            >
              <svg v-if="!applyAllRunning" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
              <span v-else class="spinner-sm"></span>
              {{ applyAllRunning ? '录入中...' : '一键全部录入' }}
            </button>
            <span class="apply-hint">自动创建宠物档案 + 诊疗记录 + 疫苗接种</span>
          </div>

          <!-- 结果反馈 -->
          <div v-if="applyAllDone" class="apply-result" :class="applyAllOk ? 'apply-ok' : 'apply-partial'">
            <div v-if="applyAllOk" class="apply-ok-msg">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
              全部录入成功！
              <button class="btn btn-sm" @click="$router.push('/medical')">查看诊疗</button>
              <button class="btn btn-sm" @click="$router.push('/pets')">查看宠物</button>
            </div>
            <div v-else>
              <span class="apply-err-msg">部分录入失败，请检查后手动补充</span>
              <button class="btn btn-sm" @click="resetVoiceAll">重新录音</button>
            </div>
          </div>
        </div>
      </div>

      <!-- ========== 病历解析 ========== -->
      <div v-if="tab === 'parse'">
        <div class="parse-toolbar">
          <select v-model="selectedTemplate" class="input template-select" @change="loadTemplate">
            <option value="">-- 选择模板 --</option>
            <option v-for="t in templates" :key="t.id" :value="t.id">{{ t.name }}</option>
          </select>
          <VoiceInput v-model="parseText" size="sm" />
        </div>
        <textarea v-model="parseText" class="input" rows="6" placeholder="输入或语音录入病历文本..."></textarea>
        <div class="ai-actions">
          <button class="btn btn-primary" @click="handleParse" :disabled="parsing">{{ parsing ? '解析中...' : 'AI 解析' }}</button>
        </div>
        <div v-if="parseResult" class="result-card">
          <div class="result-header"><span>解析结果</span><span class="badge badge-blue">置信度: {{ parseResult.result?.confidence || '-' }}%</span></div>
          <div class="result-grid" v-if="parseResult.result">
            <div v-if="parseResult.result.pet_info"><strong>宠物</strong><p>{{ parseResult.result.pet_info.pet_name || '-' }} / {{ parseResult.result.pet_info.species || '-' }}</p></div>
            <div v-if="parseResult.result.diagnosis"><strong>诊断</strong><p>{{ parseResult.result.diagnosis.name || '-' }}</p></div>
            <div v-if="parseResult.result.treatment"><strong>治疗</strong><p>{{ parseResult.result.treatment.plan || '-' }}</p></div>
          </div>
        </div>
      </div>

      <!-- ========== 疾病建议 ========== -->
      <div v-if="tab === 'suggest'">
        <div class="form-group">
          <label>症状（逗号分隔）</label>
          <div style="display:flex;align-items:center;gap:6px;">
            <input v-model="symptomsText" class="input" style="flex:1;" placeholder="呕吐, 腹泻, 食欲不振" />
            <VoiceInput v-model="symptomsText" size="sm" />
          </div>
        </div>
        <div class="ai-actions">
          <button class="btn btn-primary" @click="handleSuggest" :disabled="suggesting">{{ suggesting ? '查询中...' : '查询建议' }}</button>
        </div>
        <div v-if="suggestResult" class="result-card">
          <div class="suggest-list">
            <div v-for="(s, i) in suggestResult.suggestions" :key="i" class="suggest-item">
              <div class="suggest-top"><span class="suggest-name">{{ s.disease }}</span><span class="badge badge-blue">{{ s.confidence }}%</span></div>
              <p class="suggest-desc" v-if="s.description">{{ s.description }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- ========== 影像分析 ========== -->
      <div v-if="tab === 'image'">
        <div class="form-group">
          <label>上传影像文件</label>
          <div class="image-upload-area" @click="triggerFileInput" @dragover.prevent @drop.prevent="handleDrop">
            <input ref="fileInput" type="file" accept="image/*" @change="handleFileSelect" style="display:none" />
            <svg v-if="!imagePreview" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>
            <img v-else :src="imagePreview" class="image-preview" />
            <p v-if="!imagePreview" class="upload-hint">点击或拖拽上传 DR/X光/CT/MRI/B超 影像</p>
            <p v-else class="upload-hint">点击更换图片</p>
          </div>
        </div>
        <div class="image-options">
          <select v-model="imageType" class="input" style="width:140px;">
            <option value="xray">DR/X光片</option>
            <option value="ct">CT 扫描</option>
            <option value="mri">MRI 核磁</option>
            <option value="ultrasound">B超/超声</option>
          </select>
          <select v-model="imageSpecies" class="input" style="width:100px;">
            <option value="狗">狗</option><option value="猫">猫</option><option value="兔">兔</option><option value="其他">其他</option>
          </select>
          <input v-model="imageContext" class="input" placeholder="临床背景（选填）" style="flex:1;" />
          <button class="btn btn-primary" @click="doImageAnalyze" :disabled="!imageFile || imageAnalyzing">
            {{ imageAnalyzing ? '分析中...' : 'AI 分析' }}
          </button>
        </div>
        <div v-if="imageResult" class="result-card">
          <div class="result-header">
            <span>影像分析结果</span>
            <span class="badge" :class="imageResult.confidence > 70 ? 'badge-green' : 'badge-blue'">置信度: {{ imageResult.confidence }}%</span>
          </div>
          <div v-if="imageResult.error" class="error-msg">{{ imageResult.error }}</div>
          <template v-else>
            <div class="image-finding-row">
              <div class="finding-block severity" :class="'sev-' + (imageResult.severity || 'normal')">
                <strong>危急程度</strong><span>{{ imageResult.severity || '-' }}</span>
              </div>
              <div class="finding-block"><strong>诊断意见</strong><p>{{ imageResult.diagnosis || '-' }}</p></div>
            </div>
            <div class="finding-block"><strong>影像所见</strong><p>{{ imageResult.findings || '-' }}</p></div>
            <div v-if="imageResult.abnormalities?.length" class="finding-block"><strong>异常发现</strong><ul><li v-for="a in imageResult.abnormalities" :key="a">{{ a }}</li></ul></div>
            <div v-if="imageResult.differential?.length" class="finding-block"><strong>鉴别诊断</strong><ul><li v-for="d in imageResult.differential" :key="d">{{ d }}</li></ul></div>
            <div v-if="imageResult.recommendations" class="finding-block"><strong>建议</strong><p>{{ imageResult.recommendations }}</p></div>
          </template>
        </div>
      </div>

      <!-- ========== Multi-Agent 会诊 ========== -->
      <div v-if="tab === 'multiagent'">
        <div class="form-group"><label>病例描述</label><textarea v-model="maCaseInfo" class="input" rows="5" placeholder="请输入病例详情：主诉、症状、检查结果等..."></textarea></div>
        <div class="ma-options">
          <select v-model="maSpecies" class="input" style="width:100px;"><option value="狗">狗</option><option value="猫">猫</option><option value="其他">其他</option></select>
          <label class="checkbox-label"><input type="checkbox" v-model="maAgents" value="internal_medicine" checked /> 内科</label>
          <label class="checkbox-label"><input type="checkbox" v-model="maAgents" value="surgery" checked /> 外科</label>
          <label class="checkbox-label"><input type="checkbox" v-model="maAgents" value="dermatology" checked /> 皮肤科</label>
          <label class="checkbox-label"><input type="checkbox" v-model="maAgents" value="pharmacology" checked /> 药理</label>
          <button class="btn btn-primary" @click="doMultiAgent" :disabled="maRunning">{{ maRunning ? '会诊中...' : '开始会诊' }}</button>
        </div>
        <div v-if="maResult" class="result-card">
          <div class="result-header"><span>会诊结果</span><span class="badge badge-green">{{ maResult.agents?.length || 0 }} 位专家参与</span></div>
          <div v-for="(agent, i) in maResult.agents" :key="i" class="agent-opinion">
            <div class="agent-name">{{ agent.specialty || '专家 ' + (i+1) }}</div>
            <p>{{ agent.opinion || agent.analysis || JSON.stringify(agent) }}</p>
          </div>
          <div v-if="maResult.synthesis" class="synthesis-block">
            <strong>综合诊断</strong><p>{{ maResult.synthesis }}</p>
          </div>
          <div v-if="maResult.primary_diagnosis" class="synthesis-block">
            <strong>主要诊断: {{ maResult.primary_diagnosis }}</strong>
            <p v-if="maResult.treatment_plan">治疗方案: {{ maResult.treatment_plan }}</p>
          </div>
        </div>
      </div>

      <!-- ========== GRPO 自我验证 ========== -->
      <div v-if="tab === 'grpo'">
        <div class="form-group"><label>病例描述</label><textarea v-model="grpoCaseInfo" class="input" rows="5" placeholder="输入病例详情..."></textarea></div>
        <div class="ma-options">
          <select v-model="grpoSpecies" class="input" style="width:100px;"><option value="狗">狗</option><option value="猫">猫</option></select>
          <span>候选方案数: </span>
          <select v-model="grpoCandidates" class="input" style="width:80px;"><option :value="2">2</option><option :value="3">3</option><option :value="5">5</option></select>
          <button class="btn btn-primary" @click="doGrpo" :disabled="grpoRunning">{{ grpoRunning ? '验证中...' : 'GRPO 自我验证' }}</button>
        </div>
        <div v-if="grpoResult" class="result-card">
          <div class="result-header"><span>GRPO 验证结果</span><span class="badge badge-blue">{{ grpoResult.candidates?.length || 0 }} 候选</span></div>
          <div v-for="(c, i) in grpoResult.candidates" :key="i" class="agent-opinion" :class="{ 'best-candidate': i === grpoResult.best_index }">
            <div class="agent-name">候选 {{ i+1 }} <span v-if="c.score" class="badge" :class="c.score > 7 ? 'badge-green' : 'badge-blue'">评分: {{ c.score }}</span></div>
            <p>{{ c.diagnosis || c.content || JSON.stringify(c).slice(0, 200) }}</p>
          </div>
          <div v-if="grpoResult.best" class="synthesis-block"><strong>最优方案</strong><p>{{ grpoResult.best.diagnosis || grpoResult.best }}</p></div>
        </div>
      </div>

      <!-- ========== 分诊评估 ========== -->
      <div v-if="tab === 'triage'">
        <div class="form-group"><label>病例描述</label><textarea v-model="triageCaseInfo" class="input" rows="4" placeholder="简要描述病情..."></textarea></div>
        <div class="ma-options">
          <select v-model="triageSpecies" class="input" style="width:100px;"><option value="狗">狗</option><option value="猫">猫</option></select>
          <button class="btn btn-primary" @click="doTriage" :disabled="triageRunning">{{ triageRunning ? '评估中...' : '分诊评估' }}</button>
        </div>
        <div v-if="triageResult" class="result-card">
          <div class="result-header">
            <span>分诊结果</span>
            <span class="badge" :class="triageResult.urgency === '紧急' ? 'badge-red' : triageResult.urgency === '亚紧急' ? 'badge-yellow' : 'badge-green'">
              {{ triageResult.urgency || '-' }}
            </span>
          </div>
          <div class="finding-block"><strong>推荐科室</strong><p>{{ triageResult.department || triageResult.recommended_department || '-' }}</p></div>
          <div v-if="triageResult.reasoning" class="finding-block"><strong>评估依据</strong><p>{{ triageResult.reasoning }}</p></div>
        </div>
      </div>

      <!-- ========== 引导式诊断 ========== -->
      <div v-if="tab === 'guided'">
        <div class="form-group">
          <label>患者信息 + 主诉</label>
          <div class="guided-input-row">
            <input v-model="gdChiefComplaint" class="input" style="flex:2;" placeholder="主诉（如：呕吐2天，精神差）" />
            <select v-model="gdSpecies" class="input" style="width:90px;"><option value="狗">狗</option><option value="猫">猫</option></select>
            <input v-model="gdBreed" class="input" style="width:120px;" placeholder="品种" />
            <input v-model="gdAge" class="input" style="width:90px;" placeholder="年龄" />
            <select v-model="gdGender" class="input" style="width:80px;"><option value="未知">性别</option><option value="公">公</option><option value="母">母</option></select>
          </div>
        </div>
        <div class="guided-steps">
          <button class="btn" :class="gdStep === 'history' ? 'btn-primary' : 'btn-outline'" @click="runGuided('history')" :disabled="gdRunning">1. 问诊引导</button>
          <button class="btn" :class="gdStep === 'exam' ? 'btn-primary' : 'btn-outline'" @click="runGuided('exam')" :disabled="gdRunning || !gdResult">2. 检查推荐</button>
          <button class="btn" :class="gdStep === 'diagnosis' ? 'btn-primary' : 'btn-outline'" @click="runGuided('diagnosis')" :disabled="gdRunning || !gdResult">3. 诊断方案</button>
        </div>
        <div v-if="gdRunning" class="loading-state">AI 正在分析...</div>
        <div v-if="gdResult" class="result-card">
          <!-- 问诊引导 -->
          <template v-if="gdResult.step === 'history'">
            <div class="result-header"><span>问诊引导</span></div>
            <div v-if="gdResult.differential_initial?.length" class="finding-block"><strong>初步鉴别诊断</strong><ul><li v-for="d in gdResult.differential_initial" :key="d">{{ d }}</li></ul></div>
            <div v-if="gdResult.red_flags?.length" class="finding-block red-flags"><strong>危险信号</strong><ul><li v-for="r in gdResult.red_flags" :key="r">{{ r }}</li></ul></div>
            <div v-if="gdResult.questions_to_ask?.length" class="finding-block"><strong>建议问诊问题</strong>
              <div v-for="(q, i) in gdResult.questions_to_ask" :key="i" class="question-item">
                <span class="badge" :class="q.importance === '必须' ? 'badge-red' : 'badge-blue'">{{ q.importance }}</span>
                <span class="q-cat">{{ q.category }}</span>
                <span>{{ q.question }}</span>
              </div>
            </div>
          </template>
          <!-- 检查推荐 -->
          <template v-if="gdResult.step === 'exam'">
            <div class="result-header"><span>检查推荐</span></div>
            <div v-if="gdResult.physical_exam?.length" class="finding-block"><strong>体格检查</strong>
              <div v-for="(e, i) in gdResult.physical_exam" :key="i" class="question-item"><span class="badge" :class="e.importance === '必须' ? 'badge-red' : 'badge-blue'">{{ e.importance }}</span><span>{{ e.item }} - {{ e.focus }}</span></div>
            </div>
            <div v-if="gdResult.lab_tests?.length" class="finding-block"><strong>实验室检查</strong>
              <div v-for="(t, i) in gdResult.lab_tests" :key="i" class="question-item"><span class="badge" :class="t.importance === '必须' ? 'badge-red' : 'badge-blue'">{{ t.importance }}</span><span>{{ t.test }} — {{ t.rationale }}</span></div>
            </div>
            <div v-if="gdResult.imaging?.length" class="finding-block"><strong>影像检查</strong>
              <div v-for="(m, i) in gdResult.imaging" :key="i" class="question-item"><span class="badge" :class="m.importance === '必须' ? 'badge-red' : 'badge-blue'">{{ m.importance }}</span><span>{{ m.type }} ({{ m.region }}) — {{ m.rationale }}</span></div>
            </div>
          </template>
          <!-- 诊断 -->
          <template v-if="gdResult.step === 'diagnosis'">
            <div class="result-header"><span>诊断与方案</span><span class="badge badge-green">置信度: {{ gdResult.primary_diagnosis?.confidence }}%</span></div>
            <div class="finding-block"><strong>主要诊断: {{ gdResult.primary_diagnosis?.name }}</strong>
              <p v-if="gdResult.primary_diagnosis?.evidence_for?.length"><em>支持证据:</em> {{ gdResult.primary_diagnosis.evidence_for.join('；') }}</p>
            </div>
            <div v-if="gdResult.differential_diagnoses?.length" class="finding-block"><strong>鉴别诊断</strong>
              <div v-for="d in gdResult.differential_diagnoses" :key="d.name" class="question-item"><span class="badge badge-blue">{{ d.likelihood }}</span><span>{{ d.name }} — {{ d.key_differentiators }}</span></div>
            </div>
            <div v-if="gdResult.must_not_miss?.length" class="finding-block red-flags"><strong>不能漏诊</strong><ul><li v-for="m in gdResult.must_not_miss" :key="m">{{ m }}</li></ul></div>
            <div v-if="gdResult.treatment_plan" class="finding-block"><strong>治疗方案</strong>
              <p v-if="gdResult.treatment_plan.immediate"><em>立即处理:</em> {{ gdResult.treatment_plan.immediate }}</p>
              <p v-if="gdResult.treatment_plan.medications"><em>药物:</em> {{ gdResult.treatment_plan.medications }}</p>
              <p v-if="gdResult.treatment_plan.monitoring"><em>监测:</em> {{ gdResult.treatment_plan.monitoring }}</p>
              <p v-if="gdResult.treatment_plan.follow_up"><em>复诊:</em> {{ gdResult.treatment_plan.follow_up }}</p>
            </div>
          </template>
        </div>
      </div>
    </div>

    <div v-if="toast.show" :class="['toast', 'toast-' + toast.type]">{{ toast.msg }}</div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  aiParseRecord, aiDiseaseSuggest, aiEngineStatus, aiGetTemplates, aiGetTemplateDetail,
  aiMultiAgentDiagnose, aiGrpoVerify, aiTriage, aiImageAnalyze, aiGuidedDiagnosis,
  aiVoiceProcess,
} from '../api'
import { createPet, createMedicalRecord, createVaccination } from '../api'
import VoiceInput from '../components/VoiceInput.vue'

const router = useRouter()
const tab = ref('voice')
const engineOk = ref(false)
const toast = reactive({ show: false, msg: '', type: 'success' })

// 语音
const recording = ref(false); const uploading = ref(false); const voiceText = ref(''); const voiceResult = ref(null); const aiBusy = ref(false)
let mediaRecorder = null; let audioChunks = []
const applyAllRunning = ref(false)
const applyResults = reactive({ pet: '', medical: '', vaccine: '' })
const applyAllDone = ref(false)
const applyAllOk = ref(false)

// 病历解析
const parseText = ref(''); const parseResult = ref(null); const parsing = ref(false)
const templates = ref([]); const selectedTemplate = ref('')

// 疾病建议
const symptomsText = ref(''); const suggestResult = ref(null); const suggesting = ref(false)

// 影像分析
const imageFile = ref(null); const imagePreview = ref(''); const imageType = ref('xray'); const imageSpecies = ref('狗'); const imageContext = ref(''); const imageResult = ref(null); const imageAnalyzing = ref(false)
const fileInput = ref(null)

// Multi-Agent
const maCaseInfo = ref(''); const maSpecies = ref('狗'); const maAgents = ref(['internal_medicine', 'surgery', 'dermatology', 'pharmacology']); const maResult = ref(null); const maRunning = ref(false)

// GRPO
const grpoCaseInfo = ref(''); const grpoSpecies = ref('狗'); const grpoCandidates = ref(3); const grpoResult = ref(null); const grpoRunning = ref(false)

// 分诊
const triageCaseInfo = ref(''); const triageSpecies = ref('狗'); const triageResult = ref(null); const triageRunning = ref(false)

// 引导诊断
const gdChiefComplaint = ref(''); const gdSpecies = ref('狗'); const gdBreed = ref(''); const gdAge = ref(''); const gdGender = ref('未知'); const gdStep = ref('history'); const gdResult = ref(null); const gdRunning = ref(false)

function showToast(msg, type = 'success') { toast.msg = msg; toast.type = type; toast.show = true; setTimeout(() => { toast.show = false }, 3000) }

// ===== 语音 =====
async function startVoiceRecording() {
  if (recording.value) { stopRecording(); return }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    audioChunks = []; mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' })
    mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0) audioChunks.push(e.data) }
    mediaRecorder.onstop = async () => {
      stream.getTracks().forEach(t => t.stop())
      if (audioChunks.length === 0) return
      const blob = new Blob(audioChunks, { type: 'audio/webm' })
      uploading.value = true
      aiBusy.value = true
      try {
        // 一次请求：后端完成 ffmpeg转格式 → 降采样 → FunASR转文字 → DeepSeek解析
        const res = await aiVoiceProcess(blob)
        voiceText.value = res.data?.text || ''
        voiceResult.value = res.data
        applyAllDone.value = false
        applyResults.pet = ''; applyResults.medical = ''; applyResults.vaccine = ''
      } catch (e) {
        showToast('语音处理失败: ' + (e.response?.data?.error || e.message), 'error')
      } finally {
        uploading.value = false
        aiBusy.value = false
      }
    }
    mediaRecorder.start(250); recording.value = true
  } catch (e) { showToast('无法访问麦克风', 'error') }
}
function stopRecording() { if (mediaRecorder && mediaRecorder.state !== 'inactive') mediaRecorder.stop(); recording.value = false }

function resetVoiceAll() {
  voiceResult.value = null; voiceText.value = ''; applyAllDone.value = false
  applyResults.pet = ''; applyResults.medical = ''; applyResults.vaccine = ''
}

async function applyAllRecords() {
  if (!voiceResult.value) return
  applyAllRunning.value = true
  applyAllDone.value = false
  applyResults.pet = ''; applyResults.medical = ''; applyResults.vaccine = ''
  let petId = null
  let allOk = true

  // 1. 创建宠物档案
  const pf = voiceResult.value.pet_form
  if (pf && pf.name) {
    try {
      const res = await createPet({
        name: pf.name,
        species: pf.species || '狗',
        breed: pf.breed || '',
        gender: pf.gender || '未知',
        owner_name: pf.owner_name || '未知',
        owner_contact: pf.owner_contact || '',
      })
      petId = res.data?.id || res.data?.pet_id
      applyResults.pet = 'done'
    } catch (e) {
      applyResults.pet = 'error'
      allOk = false
    }
  }

  // 2. 创建诊疗记录
  const mf = voiceResult.value.medical_form
  if (mf) {
    try {
      await createMedicalRecord({
        pet_id: petId || mf.pet_id || 1,
        vet_name: mf.vet_name || '',
        visit_date: mf.visit_date || new Date().toISOString().slice(0, 10),
        diagnosis: mf.diagnosis || '',
        treatment: mf.treatment || '',
        symptoms: mf.symptoms || voiceText.value || '',
        notes: mf.notes || '',
        follow_up_date: mf.follow_up_date || null,
        fee_charged: mf.fee_charged || 0,
      })
      applyResults.medical = 'done'
    } catch (e) {
      applyResults.medical = 'error'
      allOk = false
    }
  }

  // 3. 创建疫苗接种
  const vf = voiceResult.value.vaccine_form
  if (vf && vf.vaccine_name) {
    try {
      await createVaccination({
        pet_id: petId || vf.pet_id || 1,
        vaccine_name: vf.vaccine_name,
        administered_date: vf.administered_date || new Date().toISOString().slice(0, 10),
        next_due_date: vf.next_due_date || null,
        vet_name: vf.vet_name || '',
      })
      applyResults.vaccine = 'done'
    } catch (e) {
      applyResults.vaccine = 'error'
      allOk = false
    }
  }

  applyAllOk.value = allOk && (applyResults.pet === 'done' || applyResults.medical === 'done')
  applyAllDone.value = true
  applyAllRunning.value = false
}

function jumpToPet() {
  const pf = voiceResult.value?.pet_form
  if (pf) localStorage.setItem('ai_prefill_pet', JSON.stringify(pf))
  router.push('/pets')
}
function jumpToMedical() {
  const mf = voiceResult.value?.medical_form
  if (mf) localStorage.setItem('ai_prefill_medical', JSON.stringify(mf))
  router.push('/medical')
}
function jumpToVaccine() {
  const vf = voiceResult.value?.vaccine_form
  if (vf) localStorage.setItem('ai_prefill_vaccine', JSON.stringify(vf))
  router.push('/vaccines')
}

// ===== 病历解析 =====
async function loadTemplate() { if (!selectedTemplate.value) return; try { const r = await aiGetTemplateDetail(selectedTemplate.value); if (r.data?.content) parseText.value = r.data.content } catch (e) { showToast('模板加载失败', 'error') } }
async function handleParse() { if (!parseText.value.trim()) return; parsing.value = true; try { parseResult.value = (await aiParseRecord(parseText.value)).data } catch (e) { showToast('解析失败', 'error') } finally { parsing.value = false } }

// ===== 疾病建议 =====
async function handleSuggest() { if (!symptomsText.value.trim()) return; suggesting.value = true; try { suggestResult.value = (await aiDiseaseSuggest(symptomsText.value)).data } catch (e) { showToast('查询失败', 'error') } finally { suggesting.value = false } }

// ===== 影像分析 =====
function triggerFileInput() { fileInput.value?.click() }
function handleFileSelect(e) { const f = e.target.files[0]; if (f) readImageFile(f) }
function handleDrop(e) { const f = e.dataTransfer.files[0]; if (f) readImageFile(f) }
function readImageFile(file) {
  imageFile.value = file
  const reader = new FileReader(); reader.onload = (e) => { imagePreview.value = e.target.result }; reader.readAsDataURL(file)
  imageResult.value = null
}
async function doImageAnalyze() {
  if (!imageFile.value) return
  imageAnalyzing.value = true
  try { imageResult.value = (await aiImageAnalyze(imageFile.value, imageType.value, imageSpecies.value, imageContext.value)).data }
  catch (e) { showToast('分析失败: ' + (e.response?.data?.error || e.message), 'error') }
  finally { imageAnalyzing.value = false }
}

// ===== Multi-Agent =====
async function doMultiAgent() { if (!maCaseInfo.value.trim()) return; maRunning.value = true; try { maResult.value = (await aiMultiAgentDiagnose(maCaseInfo.value, maSpecies.value, maAgents.value)).data } catch (e) { showToast('会诊失败', 'error') } finally { maRunning.value = false } }

// ===== GRPO =====
async function doGrpo() { if (!grpoCaseInfo.value.trim()) return; grpoRunning.value = true; try { grpoResult.value = (await aiGrpoVerify(grpoCaseInfo.value, grpoSpecies.value, grpoCandidates.value)).data } catch (e) { showToast('验证失败', 'error') } finally { grpoRunning.value = false } }

// ===== 分诊 =====
async function doTriage() { if (!triageCaseInfo.value.trim()) return; triageRunning.value = true; try { triageResult.value = (await aiTriage(triageCaseInfo.value, triageSpecies.value)).data } catch (e) { showToast('分诊失败', 'error') } finally { triageRunning.value = false } }

// ===== 引导诊断 =====
async function runGuided(step) {
  if (!gdChiefComplaint.value.trim()) { showToast('请输入主诉', 'error'); return }
  gdStep.value = step; gdRunning.value = true
  try {
    gdResult.value = (await aiGuidedDiagnosis({
      chief_complaint: gdChiefComplaint.value,
      species: gdSpecies.value, breed: gdBreed.value, age: gdAge.value, gender: gdGender.value,
      step,
    })).data
  } catch (e) { showToast('诊断失败', 'error') } finally { gdRunning.value = false }
}

onMounted(async () => {
  try {
    const [s, t] = await Promise.all([aiEngineStatus(), aiGetTemplates()])
    engineOk.value = s.data?.deepseek_configured || false
    templates.value = t.data?.templates || []
  } catch (e) { /* ignore */ }
})
</script>

<style scoped>
.ai-page { width: 100%; }
.card-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; flex-wrap: wrap; gap: 10px; }
.card-title { font-size: 18px; font-weight: 700; color: var(--color-text); }

.ai-tabs { display: flex; gap: 2px; margin-bottom: 20px; flex-wrap: wrap; }
.tab { padding: 6px 12px; background: #f8fafc; border: 1px solid var(--color-border); border-radius: var(--radius); font-size: 12px; color: var(--color-text-secondary); transition: all 0.15s; cursor: pointer; white-space: nowrap; }
.tab:hover { color: var(--color-primary); border-color: var(--color-primary); }
.tab-active { background: var(--color-primary); color: #fff; border-color: var(--color-primary); }
.tab-active:hover { color: #fff; }

.ai-actions { margin-bottom: 16px; }
.form-group { margin-bottom: 12px; }
.form-group label { display: block; font-size: 13px; font-weight: 600; margin-bottom: 6px; color: var(--color-text); }

/* Voice */
.voice-center { text-align: center; padding: 20px; }
.btn-voice-record { width: 72px; height: 72px; border-radius: 50%; background: var(--color-primary); color: #fff; display: inline-flex; align-items: center; justify-content: center; transition: all 0.2s; box-shadow: 0 4px 14px rgba(37, 99, 235, 0.3); cursor: pointer; border: none; }
.btn-voice-record:hover { transform: scale(1.05); }
.btn-voice-record:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-voice-record.is-recording { background: var(--color-danger); animation: pulse-rec 1.2s infinite; }
@keyframes pulse-rec { 0%,100%{box-shadow: 0 0 0 0 rgba(220,38,38,0.4)} 50%{box-shadow: 0 0 0 16px rgba(220,38,38,0)} }
.voice-label { font-size: 15px; font-weight: 600; margin-top: 12px; }
.voice-result { margin-top: 12px; padding: 12px 20px; background: #f0f9ff; border: 1px solid #bae6fd; border-radius: var(--radius); font-size: 14px; display: inline-block; max-width: 500px; word-break: break-word; }

/* Voice summary */
.voice-summary { margin-top: 20px; }
.summary-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.summary-title { font-size: 16px; font-weight: 700; color: var(--color-text); }
.summary-grid { display: flex; flex-direction: column; gap: 8px; margin-bottom: 16px; }
.summary-block { display: flex; align-items: center; gap: 12px; padding: 12px 14px; background: #f8fafc; border: 1px solid var(--color-border); border-radius: var(--radius); transition: all 0.2s; }
.summary-block.filled { background: #f0fdf4; border-color: #bbf7d0; }
.sb-icon { color: var(--color-text-light); flex-shrink: 0; }
.summary-block.filled .sb-icon { color: #16a34a; }
.sb-content { flex: 1; min-width: 0; }
.sb-content strong { display: block; font-size: 13px; margin-bottom: 2px; }
.sb-content p { font-size: 12px; color: var(--color-text-secondary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.sb-empty { font-style: italic; color: var(--color-text-light) !important; }
.sb-check { color: #16a34a; font-size: 18px; font-weight: 700; flex-shrink: 0; }
.sb-err { color: #dc2626; font-size: 18px; font-weight: 700; flex-shrink: 0; }

.apply-all-bar { display: flex; align-items: center; gap: 14px; padding: 14px 0; border-top: 1px solid var(--color-border); }
.apply-all-btn { display: flex; align-items: center; gap: 8px; padding: 10px 24px; font-size: 15px; }
.apply-hint { font-size: 12px; color: var(--color-text-light); }
.spinner-sm { width: 18px; height: 18px; border: 2px solid rgba(255,255,255,0.3); border-top-color: #fff; border-radius: 50%; animation: spin .6s linear infinite; display: inline-block; }
@keyframes spin { to { transform: rotate(360deg); } }

.apply-result { margin-top: 12px; padding: 14px; border-radius: var(--radius); font-size: 14px; }
.apply-ok { background: #f0fdf4; border: 1px solid #bbf7d0; }
.apply-partial { background: #fef2f2; border: 1px solid #fecaca; }
.apply-ok-msg { display: flex; align-items: center; gap: 8px; color: #16a34a; font-weight: 600; flex-wrap: wrap; }
.apply-err-msg { color: #dc2626; font-weight: 600; margin-right: 8px; }

/* Result card */
.result-card { background: #f8fafc; border: 1px solid var(--color-border); border-radius: var(--radius); padding: 16px; margin-top: 16px; }
.result-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; font-weight: 600; font-size: 14px; }
.result-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 12px; }
.result-grid > div { background: #fff; border-radius: 6px; padding: 12px; }
.result-grid strong { display: block; font-size: 11px; color: var(--color-text-secondary); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; }
.suggest-list { display: flex; flex-direction: column; gap: 8px; }
.suggest-item { background: #fff; border-radius: 6px; padding: 12px; }
.suggest-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.suggest-name { font-weight: 600; font-size: 14px; }
.suggest-desc { font-size: 13px; color: var(--color-text-secondary); }

/* Image analysis */
.image-upload-area { border: 2px dashed var(--color-border); border-radius: var(--radius); padding: 30px; text-align: center; cursor: pointer; transition: all 0.2s; min-height: 120px; display: flex; flex-direction: column; align-items: center; justify-content: center; color: var(--color-text-light); }
.image-upload-area:hover { border-color: var(--color-primary); color: var(--color-primary); }
.image-preview { max-width: 100%; max-height: 250px; border-radius: 6px; }
.upload-hint { font-size: 13px; margin-top: 8px; }
.image-options { display: flex; gap: 8px; margin-top: 12px; align-items: center; }
.finding-block { background: #fff; border-radius: 6px; padding: 12px; margin-bottom: 8px; }
.finding-block strong { display: block; font-size: 12px; color: var(--color-text-secondary); margin-bottom: 4px; }
.finding-block p, .finding-block ul { font-size: 13px; color: var(--color-text); margin: 0; }
.finding-block ul { padding-left: 18px; }
.finding-block li { margin-bottom: 3px; }
.image-finding-row { display: grid; grid-template-columns: 120px 1fr; gap: 8px; }
.severity { text-align: center; }
.severity span { font-size: 18px; font-weight: 700; display: block; margin-top: 4px; }
.sev-正常 span { color: #16a34a; }
.sev-轻度 span { color: #ca8a04; }
.sev-中度 span { color: #ea580c; }
.sev-重度 span, .sev-危急 span { color: #dc2626; }
.red-flags { background: #fef2f2; border: 1px solid #fecaca; }
.red-flags li { color: #dc2626; }

/* Multi-agent / GRPO */
.ma-options { display: flex; gap: 8px; align-items: center; margin-bottom: 12px; flex-wrap: wrap; }
.checkbox-label { display: flex; align-items: center; gap: 4px; font-size: 12px; cursor: pointer; }
.agent-opinion { background: #fff; border-radius: 6px; padding: 12px; margin-bottom: 8px; }
.agent-name { font-weight: 600; font-size: 13px; color: var(--color-primary); margin-bottom: 4px; display: flex; align-items: center; gap: 8px; }
.agent-opinion p { font-size: 13px; color: var(--color-text); white-space: pre-wrap; }
.synthesis-block { background: #f0f9ff; border: 1px solid #bae6fd; border-radius: 6px; padding: 14px; margin-top: 12px; }
.synthesis-block strong { display: block; font-size: 14px; margin-bottom: 6px; }
.synthesis-block p { font-size: 13px; color: var(--color-text); }
.best-candidate { border: 2px solid var(--color-primary); background: #f0f7ff; }

/* Guided Diagnosis */
.guided-input-row { display: flex; gap: 8px; flex-wrap: wrap; }
.guided-steps { display: flex; gap: 8px; margin-bottom: 16px; }
.btn-outline { background: transparent; border: 1px solid var(--color-border); color: var(--color-text-secondary); padding: 8px 16px; border-radius: var(--radius); font-size: 13px; cursor: pointer; }
.btn-outline:hover { border-color: var(--color-primary); color: var(--color-primary); }
.question-item { display: flex; align-items: flex-start; gap: 8px; padding: 6px 0; font-size: 13px; border-bottom: 1px solid #f1f5f9; }
.question-item:last-child { border-bottom: none; }
.q-cat { font-size: 11px; color: var(--color-text-light); white-space: nowrap; }

.loading-state { text-align: center; padding: 30px; color: var(--color-text-secondary); font-size: 14px; }
.error-msg { color: var(--color-danger); font-size: 13px; }
.parse-toolbar { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }
.template-select { width: 200px; }

@media (max-width: 768px) {
  .action-grid, .result-grid, .image-finding-row { grid-template-columns: 1fr; }
  .ai-tabs { overflow-x: auto; }
  .guided-input-row { flex-direction: column; }
}
</style>
