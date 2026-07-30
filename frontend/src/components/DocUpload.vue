<template>
  <div
      class="doc-upload"
      :class="{ dragging }"
      @dragover.prevent="dragging = true"
      @dragleave.prevent="dragging = false"
      @drop.prevent="handleDrop"
  >
    <div class="upload-area">
      <span class="upload-icon">📤</span>
      <p v-if="!uploading">拖拽文件到此处，或 <label class="file-label">点击选择文件<input type="file" hidden @change="handleFile" :accept="accept" /></label></p>
      <p v-else>⏳ 正在上传解析中...</p>
      <p class="upload-hint">支持 PDF / Word / Markdown / TXT</p>
    </div>

    <p v-if="error" class="upload-error">{{ error }}</p>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { uploadDocument } from '../api/index.js'
import { requireAuth } from '../auth.js'

const emit = defineEmits(['uploaded'])

const accept = '.pdf,.docx,.doc,.md,.txt'
const dragging = ref(false)
const uploading = ref(false)
const error = ref('')

function handleDrop(e) {
  dragging.value = false
  const file = e.dataTransfer.files[0]
  if (file) upload(file)
}

function handleFile(e) {
  const file = e.target.files[0]
  if (file) upload(file)
}

async function upload(file) {
  if (!requireAuth()) return
  error.value = ''
  uploading.value = true
  try {
    await uploadDocument(file)
    emit('uploaded')
  } catch (e) {
    error.value = e.message
  } finally {
    uploading.value = false
  }
}
</script>

<style scoped>
.doc-upload {
  margin-bottom: 24px;
}

.upload-area {
  border: 2px dashed #ccc;
  border-radius: 12px;
  padding: 40px;
  text-align: center;
  transition: border-color 0.2s;
  background: #fafafa;
}

.dragging .upload-area {
  border-color: #2563eb;
  background: #eef2ff;
}

.upload-icon {
  font-size: 36px;
}

.upload-area p {
  margin: 8px 0 0;
  color: #666;
  font-size: 14px;
}

.file-label {
  color: #2563eb;
  cursor: pointer;
  text-decoration: underline;
}

.upload-hint {
  color: #999 !important;
  font-size: 12px !important;
}

.upload-error {
  color: #dc2626;
  font-size: 13px;
  margin-top: 8px;
}
</style>
