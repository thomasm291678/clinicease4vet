import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as apiLogin, register as apiRegister } from '../api'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(JSON.parse(localStorage.getItem('user') || 'null'))
  const token = ref(localStorage.getItem('token') || '')

  const isLoggedIn = computed(() => !!token.value)
  const userRole = computed(() => user.value?.role || '')
  const username = computed(() => user.value?.username || '')
  const isAdmin = computed(() => user.value?.role === 'admin')

  async function login(username, password) {
    const res = await apiLogin(username, password)
    const data = res.data
    token.value = data.token
    user.value = data.user || { username, role: data.role || 'staff' }
    localStorage.setItem('token', token.value)
    localStorage.setItem('user', JSON.stringify(user.value))
    return data
  }

  async function register(username, password, role) {
    const res = await apiRegister(username, password, role)
    return res.data
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('user')
  }

  return {
    user,
    token,
    isLoggedIn,
    userRole,
    username,
    isAdmin,
    login,
    register,
    logout,
  }
})
