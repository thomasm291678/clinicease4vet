<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-header">
        <div class="login-logo">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
          </svg>
        </div>
        <h1>PetCare</h1>
        <p>宠物医院管理系统</p>
      </div>

      <form @submit.prevent="handleSubmit">
        <div class="form-group">
          <label>用户名</label>
          <input v-model="form.username" type="text" class="input" placeholder="请输入用户名" autocomplete="username" />
        </div>
        <div class="form-group">
          <label>密码</label>
          <input v-model="form.password" type="password" class="input" placeholder="请输入密码" autocomplete="current-password" />
        </div>
        <div v-if="isRegister" class="form-group">
          <label>角色</label>
          <select v-model="form.role" class="input">
            <option value="staff">员工 (Staff)</option>
            <option value="vet">兽医 (Vet)</option>
            <option value="admin">管理员 (Admin)</option>
          </select>
        </div>
        <div v-if="error" :class="errorType === 'success' ? 'success-msg' : 'error-msg'">{{ error }}</div>
        <button type="submit" class="btn btn-primary btn-lg login-btn" :disabled="loading">
          {{ loading ? '请稍候...' : (isRegister ? '注册' : '登录') }}
        </button>
      </form>

      <div class="login-footer">
        <span v-if="!isRegister">
          没有账号？
          <a href="#" @click.prevent="isRegister = true; error = ''">立即注册</a>
        </span>
        <span v-else>
          已有账号？
          <a href="#" @click.prevent="isRegister = false; error = ''">返回登录</a>
        </span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()

onMounted(() => {
  auth.logout()
})

const isRegister = ref(false)
const loading = ref(false)
const error = ref('')
const errorType = ref('error')

const form = reactive({
  username: '',
  password: '',
  role: 'staff',
})

async function handleSubmit() {
  error.value = ''
  errorType.value = 'error'
  if (!form.username.trim() || !form.password.trim()) {
    error.value = '用户名和密码不能为空'
    return
  }
  if (isRegister.value && form.password.length < 6) {
    error.value = '密码至少需要6个字符'
    return
  }

  loading.value = true
  try {
    if (isRegister.value) {
      await auth.register(form.username, form.password, form.role)
      error.value = '注册成功，请登录'
      errorType.value = 'success'
      isRegister.value = false
      form.password = ''
    } else {
      await auth.login(form.username, form.password)
      router.push('/dashboard')
    }
  } catch (e) {
    const msg = e?.response?.data?.error || e?.message || '操作失败，请重试'
    error.value = msg
    errorType.value = 'error'
    console.error('Auth error:', e)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1a2744 0%, #2563eb 100%);
}

.login-card {
  background: #fff;
  border-radius: 16px;
  padding: 40px;
  width: 400px;
  max-width: 90vw;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
}

.login-header {
  text-align: center;
  margin-bottom: 32px;
}

.login-logo {
  margin-bottom: 12px;
}

.login-header h1 {
  font-size: 24px;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: 4px;
}

.login-header p {
  font-size: 14px;
  color: var(--color-text-secondary);
}

.error-msg {
  background: #fee2e2;
  color: var(--color-danger);
  padding: 8px 12px;
  border-radius: var(--radius);
  font-size: 13px;
  margin-bottom: 12px;
}

.success-msg {
  background: #d1fae5;
  color: #065f46;
  padding: 8px 12px;
  border-radius: var(--radius);
  font-size: 13px;
  margin-bottom: 12px;
}

.login-btn {
  width: 100%;
  margin-top: 4px;
}

.login-footer {
  text-align: center;
  margin-top: 20px;
  font-size: 13px;
  color: var(--color-text-secondary);
}
</style>
