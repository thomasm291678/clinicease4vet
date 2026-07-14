<template>
  <div class="layout">
    <AppSidebar />
    <div class="main">
      <header class="topbar">
        <div class="topbar-left">
          <h2 class="page-title">{{ $route.meta.title || '' }}</h2>
        </div>
        <div class="topbar-right">
          <button class="btn-ai-quick" @click="openAiModal">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
              <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
              <line x1="12" y1="19" x2="12" y2="23"/>
              <line x1="8" y1="23" x2="16" y2="23"/>
            </svg>
            AI 语音工作台
          </button>
          <span class="user-info">
            <span class="user-avatar">{{ auth.username.charAt(0).toUpperCase() }}</span>
            {{ auth.username }}
          </span>
          <span class="role-badge badge-blue">{{ auth.userRole === 'admin' ? '管理员' : auth.userRole === 'vet' ? '兽医' : '员工' }}</span>
          <button class="btn btn-outline btn-sm" @click="handleLogout">退出登录</button>
        </div>
      </header>
      <div class="content">
        <router-view />
      </div>
    </div>
    <AiVoiceModal />
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useAiVoiceStore } from '../stores/aiVoice'
import AppSidebar from './AppSidebar.vue'
import AiVoiceModal from './AiVoiceModal.vue'

const router = useRouter()
const auth = useAuthStore()
const aiVoice = useAiVoiceStore()

function handleLogout() {
  auth.logout()
  router.push('/login')
}

function openAiModal() {
  aiVoice.showModal = true
}
</script>

<style scoped>
.layout {
  display: flex;
  height: 100%;
}

.main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  height: 56px;
  background: #fff;
  border-bottom: 1px solid var(--color-border);
  flex-shrink: 0;
}

.page-title {
  font-size: 17px;
  font-weight: 600;
  color: var(--color-text);
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.btn-ai-quick {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  background: linear-gradient(135deg, #10b981, #059669);
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  border-radius: 20px;
  text-decoration: none;
  transition: all 0.2s;
  box-shadow: 0 2px 8px rgba(16, 185, 129, 0.3);
}

.btn-ai-quick:hover {
  background: linear-gradient(135deg, #34d399, #10b981);
  box-shadow: 0 4px 14px rgba(16, 185, 129, 0.45);
  transform: translateY(-1px);
}

.btn-ai-quick.router-link-active,
.btn-ai-quick.router-link-exact-active {
  background: linear-gradient(135deg, #047857, #065f46);
}

.user-info {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--color-text);
}

.user-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--color-primary);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
}

.role-badge {
  font-size: 11px;
}

.content {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}
</style>
