<template>
  <div class="message-input">
    <textarea
        v-model="text"
        :disabled="disabled"
        placeholder="输入问题，按 Enter 发送..."
        rows="1"
        @keydown.enter.exact.prevent="handleSend"
        ref="inputRef"
    />
    <button :disabled="!text.trim() || disabled" @click="handleSend">
      发送
    </button>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'

const props = defineProps({
  disabled: { type: Boolean, default: false },
})

const emit = defineEmits(['send'])

const text = ref('')
const inputRef = ref(null)

function handleSend() {
  const q = text.value.trim()
  if (!q || props.disabled) return

  emit('send', q)
  text.value = ''

  // 自动重新聚焦
  nextTick(() => {
    inputRef.value?.focus()
  })
}
</script>

<style scoped>
.message-input {
  display: flex;
  gap: 10px;
  padding: 12px 16px;
  border-top: 1px solid #eee;
  background: #fff;
}

textarea {
  flex: 1;
  resize: none;
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 10px;
  font-size: 14px;
  font-family: inherit;
  outline: none;
}

textarea:focus {
  border-color: #2563eb;
}

button {
  padding: 8px 20px;
  background: #2563eb;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
}

button:disabled {
  background: #ccc;
  cursor: not-allowed;
}
</style>
