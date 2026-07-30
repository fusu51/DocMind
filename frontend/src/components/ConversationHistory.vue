<template>
  <div class="history-panel">
    <div class="history-header">
      <span>💬 对话历史</span>
      <button class="btn-new" @click="$emit('newChat')">+ 新对话</button>
    </div>

    <div v-if="loading" class="history-empty">加载中...</div>
    <div v-else-if="conversations.length === 0" class="history-empty">暂无历史对话</div>

    <div v-else class="history-list">
      <div
          v-for="conv in conversations"
          :key="conv.id"
          class="history-item"
          :class="{ active: activeId === conv.id }"
          @click="$emit('select', conv)"
      >
        <div class="history-question">{{ truncate(conv.question) }}</div>
        <div class="history-meta">
          <span v-if="conv.doc_id" class="history-doc-badge">📄 单文档</span>
          <span v-else class="history-doc-badge">🌐 全局</span>
          <span class="history-time">{{ formatTime(conv.created_at) }}</span>
        </div>
        <button class="btn-delete" @click.stop="handleDelete(conv)" title="删除">×</button>
      </div>
    </div>

    <!-- 刷新按钮 -->
    <div class="history-footer">
      <button class="btn-refresh" @click="loadHistory">🔄 刷新</button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getConversations, deleteConversation } from '../api/index.js'

const props = defineProps({
  activeId: { type: Number, default: null },
})

defineEmits(['select', 'newChat'])

const conversations = ref([])
const loading = ref(false)

onMounted(() => loadHistory())

async function loadHistory() {
  loading.value = true
  try {
    const res = await getConversations()
    conversations.value = res.conversations || []
  } catch (e) {
    console.error('加载对话历史失败:', e)
  } finally {
    loading.value = false
  }
}

async function handleDelete(conv) {
  if (!confirm(`删除这条对话？`)) return
  try {
    await deleteConversation(conv.id)
    conversations.value = conversations.value.filter(c => c.id !== conv.id)
  } catch (e) {
    alert('删除失败：' + e.message)
  }
}

function truncate(text) {
  if (!text) return '(空)'
  return text.length > 40 ? text.slice(0, 40) + '...' : text
}

function formatTime(ts) {
  if (!ts) return ''
  // SQLite CURRENT_TIMESTAMP 是 UTC，转本地时间
  const d = new Date(ts.replace(' ', 'T') + 'Z')  // 加 Z 标记为 UTC
  if (isNaN(d.getTime())) return ts.slice(5, 16)  // fallback
  const m = d.getMonth() + 1
  const day = d.getDate()
  const h = d.getHours().toString().padStart(2, '0')
  const min = d.getMinutes().toString().padStart(2, '0')
  return `${m.toString().padStart(2, '0')}-${day.toString().padStart(2, '0')} ${h}:${min}`
}


defineExpose({ loadHistory })
</script>

<style scoped>
.history-panel {
  width: 260px;
  height: 100%;
  display: flex;
  flex-direction: column;
  border-right: 1px solid #e5e5e5;
  background: #fafafa;
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  border-bottom: 1px solid #e5e5e5;
  font-size: 14px;
  font-weight: 600;
}

.btn-new {
  padding: 3px 10px;
  border: 1px solid #2563eb;
  background: #2563eb;
  color: #fff;
  border-radius: 4px;
  cursor: pointer;
  font-size: 11px;
}

.btn-new:hover {
  background: #1d4ed8;
}

.history-empty {
  padding: 20px 12px;
  color: #999;
  font-size: 13px;
  text-align: center;
}

.history-list {
  flex: 1;
  overflow-y: auto;
}

.history-item {
  position: relative;
  padding: 10px 12px;
  border-bottom: 1px solid #f0f0f0;
  cursor: pointer;
  transition: background 0.15s;
}

.history-item:hover {
  background: #f0f4ff;
}

.history-item.active {
  background: #eef2ff;
  border-left: 3px solid #2563eb;
}

.history-question {
  font-size: 13px;
  color: #333;
  line-height: 1.4;
  margin-bottom: 4px;
}

.history-meta {
  display: flex;
  gap: 6px;
  align-items: center;
}

.history-doc-badge {
  font-size: 10px;
  padding: 1px 6px;
  background: #e5e5e5;
  border-radius: 3px;
  color: #666;
}

.history-time {
  font-size: 11px;
  color: #999;
}

.history-footer {
  padding: 8px 12px;
  border-top: 1px solid #e5e5e5;
}

.btn-refresh {
  width: 100%;
  padding: 4px;
  border: 1px solid #ddd;
  background: #fff;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  color: #666;
}

.btn-refresh:hover {
  background: #f5f5f5;
}

.btn-delete {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 20px;
  height: 20px;
  border: none;
  background: transparent;
  color: #ccc;
  font-size: 16px;
  cursor: pointer;
  line-height: 1;
  padding: 0;
  border-radius: 3px;
}

.btn-delete:hover {
  color: #dc2626;
  background: #fef2f2;
}
</style>
