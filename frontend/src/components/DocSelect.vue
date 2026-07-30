<template>
  <div class="doc-select">
    <label>📂 检索范围：</label>
    <select v-model="selected" @change="emit('update:modelValue', selected)">
      <option :value="null">全部文档（全局检索）</option>
      <option
          v-for="doc in docs"
          :key="doc.id"
          :value="doc.id"
      >
        {{ doc.name }}（{{ doc.chunks }} 块）
      </option>
    </select>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getDocuments } from '../api/index.js'

const props = defineProps({
  modelValue: { default: null },  // 当前选中的 doc_id, null = 全部
})

const emit = defineEmits(['update:modelValue'])

const docs = ref([])
const selected = ref(props.modelValue)

onMounted(async () => {
  try {
    const res = await getDocuments()
    docs.value = res.documents || []
  } catch (e) {
    console.error('获取文档列表失败:', e)
  }
})
</script>

<style scoped>
.doc-select {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

select {
  padding: 4px 8px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 13px;
  outline: none;
  min-width: 200px;
}

select:focus {
  border-color: #2563eb;
}
</style>
