<template>
  <div class="source-card">
    <span class="source-index">[{{ index }}]</span>
    <span class="source-icon">{{ icon }}</span>
    <span class="source-name">{{ source.doc_name }}</span>
    <span class="source-meta">
      · 第{{ source.page }}页
      · 相关度 {{ (source.score * 100).toFixed(0) }}%
    </span>
    <p class="source-text">{{ source.text.slice(0, 120) }}...</p>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  source: { type: Object, required: true },
  index: { type: Number, default: 1 },
})

const icon = computed(() => {
  const name = props.source.doc_name
  if (name.endsWith('.pdf')) return '📄'
  if (name.endsWith('.docx') || name.endsWith('.doc')) return '📝'
  if (name.endsWith('.md')) return '📋'
  return '📎'
})
</script>


<style scoped>
.source-card {
  background: #fff;
  border: 1px solid #e5e5e5;
  border-radius: 8px;
  padding: 8px 10px;
  margin-top: 6px;
  font-size: 12px;
  line-height: 1.5;
}

.source-index {
  font-weight: 600;
  color: #2563eb;
  margin-right: 4px;
}

.source-name {
  font-weight: 500;
  color: #333;
}

.source-meta {
  color: #888;
}

.source-text {
  margin: 4px 0 0;
  color: #666;
  font-size: 11px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
