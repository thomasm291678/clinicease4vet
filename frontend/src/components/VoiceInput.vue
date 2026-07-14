<template>
  <span class="voice-input-wrap" :class="{ recording: isRecording, uploading: isUploading }">
    <button
      v-if="!isUploading"
      type="button"
      class="voice-btn"
      :class="[size, { 'has-value': modelValue }]"
      :title="isRecording ? '点击停止录音' : modelValue ? '语音录入' : '语音录入'"
      @click="toggleRecording"
    >
      <svg v-if="!isRecording && !modelValue" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
        <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
        <line x1="12" y1="19" x2="12" y2="23"/>
        <line x1="8" y1="23" x2="16" y2="23"/>
      </svg>
      <span v-else-if="isRecording" class="recording-dot"></span>
      <svg v-else-if="modelValue" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
        <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
        <line x1="12" y1="19" x2="12" y2="23"/>
        <line x1="8" y1="23" x2="16" y2="23"/>
      </svg>
    </button>

    <span v-if="isUploading" class="upload-spinner"></span>

    <button
      v-if="modelValue"
      type="button"
      class="voice-clear-btn"
      @click="$emit('update:modelValue', '')"
      title="清除语音输入"
    >
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
      </svg>
    </button>

    <span v-if="isRecording" class="recording-hint">{{ recordingTime }}s 正在录音...</span>
    <span v-if="isUploading" class="recording-hint uploading-hint">正在识别...</span>
  </span>
</template>

<script setup>
import { ref, onUnmounted } from 'vue'
import { aiTranscribe } from '../api'

const props = defineProps({
  modelValue: { type: String, default: '' },
  size: { type: String, default: 'md' },
  placeholder: { type: String, default: '' },
})

const emit = defineEmits(['update:modelValue', 'speech-result', 'error'])

const isRecording = ref(false)
const isUploading = ref(false)
const recordingTime = ref(0)

let mediaRecorder = null
let audioChunks = []
let recordingTimer = null

async function toggleRecording() {
  if (isRecording.value) {
    stopRecording()
    return
  }

  if (isUploading.value) return

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    audioChunks = []
    mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' })

    mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        audioChunks.push(event.data)
      }
    }

    mediaRecorder.onstop = async () => {
      stream.getTracks().forEach((t) => t.stop())
      if (audioChunks.length === 0) return

      const audioBlob = new Blob(audioChunks, { type: 'audio/webm' })
      await uploadAndTranscribe(audioBlob)
    }

    mediaRecorder.start(250)
    isRecording.value = true
    recordingTime.value = 0
    recordingTimer = setInterval(() => {
      recordingTime.value++
    }, 1000)
  } catch (e) {
    emit('error', '无法访问麦克风，请检查权限')
  }
}

function stopRecording() {
  if (recordingTimer) {
    clearInterval(recordingTimer)
    recordingTimer = null
  }
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop()
  }
  isRecording.value = false
}

async function uploadAndTranscribe(audioBlob) {
  isUploading.value = true
  try {
    const res = await aiTranscribe(audioBlob)
    const text = res.data?.text || ''
    if (text) {
      emit('update:modelValue', text)
      emit('speech-result', text)
    } else {
      emit('error', '未识别到语音内容')
    }
  } catch (e) {
    emit('error', '语音识别失败: ' + (e.response?.data?.error || e.message || '网络错误'))
  } finally {
    isUploading.value = false
  }
}

onUnmounted(() => {
  if (recordingTimer) clearInterval(recordingTimer)
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop()
  }
})
</script>

<style scoped>
.voice-input-wrap {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  vertical-align: middle;
}

.voice-btn {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: #f0f4f8;
  color: var(--color-text-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
  border: 1px solid var(--color-border);
  cursor: pointer;
  flex-shrink: 0;
}

.voice-btn:hover {
  background: var(--color-primary-light);
  color: var(--color-primary);
  border-color: var(--color-primary);
}

.voice-btn.has-value {
  background: #dcfce7;
  color: #16a34a;
  border-color: #86efac;
}

.voice-btn.sm {
  width: 24px;
  height: 24px;
}

.voice-btn.sm svg {
  width: 13px;
  height: 13px;
}

.voice-btn.lg {
  width: 48px;
  height: 48px;
}

.voice-btn.lg svg {
  width: 24px;
  height: 24px;
}

.recording .voice-btn {
  background: #fee2e2;
  border-color: #fca5a5;
  color: var(--color-danger);
  animation: pulse-rec 1.2s infinite;
}

.recording-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--color-danger);
}

.voice-clear-btn {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #e2e8f0;
  color: var(--color-text-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  border: none;
  flex-shrink: 0;
}

.voice-clear-btn:hover {
  background: #cbd5e1;
}

.recording-hint {
  font-size: 12px;
  color: var(--color-danger);
  white-space: nowrap;
}

.uploading-hint {
  color: var(--color-primary);
}

.upload-spinner {
  width: 30px;
  height: 30px;
  border: 3px solid #e2e8f0;
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  flex-shrink: 0;
}

@keyframes pulse-rec {
  0%, 100% { box-shadow: 0 0 0 0 rgba(220, 38, 38, 0.4); }
  50% { box-shadow: 0 0 0 8px rgba(220, 38, 38, 0); }
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
