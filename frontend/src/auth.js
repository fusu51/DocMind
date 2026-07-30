import { ref } from 'vue'

const STORAGE_KEY = 'docmind_token'

const token = ref(localStorage.getItem(STORAGE_KEY) || '')

export function getToken() {
  return token.value
}

export function setToken(t) {
  token.value = t
  if (t) {
    localStorage.setItem(STORAGE_KEY, t)
  } else {
    localStorage.removeItem(STORAGE_KEY)
  }
}

export function isAuthed() {
  return !!token.value
}

// 事件总线：未认证时触发
let _showCallback = null

export function onShowAuth(fn) {
  _showCallback = fn
}

export function requireAuth() {
  if (isAuthed()) return true
  _showCallback?.()
  return false
}
