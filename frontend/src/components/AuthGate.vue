<template>
  <div v-if="visible" class="auth-overlay" @click.self="close">
    <div class="auth-modal">
      <h3>🔐 访问受限</h3>
      <p class="auth-desc">API 费用有限，请获取令牌后使用</p>

      <div class="auth-contact">
        <span>📱 联系获取令牌：</span>
        <strong>WX：19267826845</strong>
      </div>

      <div class="auth-input-row">
        <input
          v-model="input"
          type="text"
          placeholder="请输入令牌"
          @keydown.enter="submit"
        />
        <button @click="submit">验证</button>
      </div>

      <p v-if="error" class="auth-error">{{ error }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { setToken } from '../auth.js'

const visible = ref(false)
const input = ref('')
const error = ref('')

function show() {
  visible.value = true
  error.value = ''
}

function close() {
  visible.value = false
}

async function submit() {
  const t = input.value.trim()
  if (!t) return

  try {
    const res = await fetch('http://localhost:8001/api/health', {
      headers: { 'X-DocMind-Token': t },
    })
    const data = await res.json()

    if (res.ok && data.status === 'ok') {
      setToken(t)
      visible.value = false
      error.value = ''
      input.value = ''
    } else {
      error.value = '令牌无效'
    }
  } catch {
    error.value = '验证失败，请检查网络'
  }
}

defineExpose({ show })
</script>

<style scoped>
.auth-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}

.auth-modal {
  background: #fff;
  border-radius: 12px;
  padding: 32px 28px 24px;
  width: 380px;
  max-width: 90vw;
  text-align: center;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.15);
}

h3 {
  margin: 0 0 8px;
  font-size: 18px;
}

.auth-desc {
  color: #666;
  font-size: 13px;
  margin: 0 0 16px;
}

.auth-contact {
  background: #fef3c7;
  border: 1px solid #fcd34d;
  border-radius: 8px;
  padding: 10px;
  margin-bottom: 16px;
  font-size: 13px;
}

.auth-contact strong {
  display: block;
  color: #92400e;
  font-size: 15px;
  margin-top: 2px;
}

.auth-input-row {
  display: flex;
  gap: 8px;
}

.auth-input-row input {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 13px;
  outline: none;
}

.auth-input-row input:focus {
  border-color: #2563eb;
}

.auth-input-row button {
  padding: 8px 16px;
  background: #2563eb;
  color: #fff;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  white-space: nowrap;
}

.auth-error {
  color: #dc2626;
  font-size: 12px;
  margin: 8px 0 0;
}
</style>
