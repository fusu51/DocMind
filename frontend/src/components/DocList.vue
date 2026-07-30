<template>
  <div class="doc-list">
    <div v-if="loading" class="list-empty">加载中...</div>
    <div v-else-if="docs.length === 0" class="list-empty">暂无文档，上传一个开始吧</div>

    <div v-else class="list-table">
      <div class="list-header">
        <span class="col-name">文件名</span>
        <span class="col-size">大小</span>
        <span class="col-chunks">分块数</span>
        <span class="col-time">上传时间</span>
        <span class="col-action">操作</span>
      </div>

      <div v-for="doc in docs" :key="doc.id" class="list-row">
        <span class="col-name">{{ doc.name }}</span>
        <span class="col-size">{{ formatSize(doc.size) }}</span>
        <span class="col-chunks">{{ doc.chunks }}</span>
        <span class="col-time">{{ formatTime(doc.created_at) }}</span>
        <span class="col-action">
          <button @click="handleDelete(doc)" class="btn-delete">删除</button>
        </span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { deleteDocument } from '../api/index.js'

const props = defineProps({
  docs: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['deleted'])

async function handleDelete(doc) {
  if (!confirm(`确定删除「${doc.name}」吗？`)) return
  try {
    await deleteDocument(doc.id)
    emit('deleted')
  } catch (e) {
    alert('删除失败：' + e.message)
  }
}

function formatSize(bytes) {
  if (!bytes) return '-'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function formatTime(ts) {
  if (!ts) return '-'
  return ts.replace('T', ' ').slice(0, 19)
}
</script>

<style scoped>
.list-empty {
  text-align: center;
  color: #999;
  padding: 40px;
  font-size: 14px;
}

.list-header, .list-row {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr 1.5fr 0.8fr;
  gap: 8px;
  align-items: center;
  padding: 10px 0;
  font-size: 13px;
}

.list-header {
  color: #999;
  border-bottom: 1px solid #eee;
  font-weight: 500;
}

.list-row {
  border-bottom: 1px solid #f5f5f5;
}

.col-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.btn-delete {
  padding: 2px 10px;
  border: 1px solid #fca5a5;
  background: #fff;
  color: #dc2626;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
}

.btn-delete:hover {
  background: #fef2f2;
}
</style>
