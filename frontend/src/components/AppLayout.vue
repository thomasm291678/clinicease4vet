<template>
  <div class="layout">
    <AppSidebar />
    <div class="main">
      <header class="topbar">
        <div class="topbar-left">
          <h2 class="page-title">{{ $route.meta.title || '' }}</h2>
        </div>
        <div class="topbar-right">
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
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import AppSidebar from './AppSidebar.vue'

const router = useRouter()
const auth = useAuthStore()

function handleLogout() {
  auth.logout()
  router.push('/login')
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
