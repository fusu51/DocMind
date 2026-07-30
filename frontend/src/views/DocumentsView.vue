<template>
  <div class="documents-view">
    <h2>📂 文档管理</h2>

    <!-- 上传区域 -->
    <DocUpload @uploaded="refreshList" />

    <!-- 文档列表 -->
    <DocList :docs="docs" :loading="loading" @deleted="refreshList" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getDocuments } from '../api/index.js'
import DocUpload from '../components/DocUpload.vue'
import DocList from '../components/DocList.vue'

const docs = ref([])
const loading = ref(false)

onMounted(() => refreshList())

async function refreshList() {
  loading.value = true
  try {
    const res = await getDocuments()
    docs.value = res.documents || []
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.documents-view {
  max-width: 800px;
  margin: 0 auto;
  padding: 24px;
}

h2 {
  margin: 0 0 20px;
  font-size: 20px;
}
</style>
