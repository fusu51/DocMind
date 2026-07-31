<template>
  <div id="app">
    <header class="app-header">
      <h1 class="app-title">📚 DocMind</h1>
      <nav class="app-nav">
        <router-link to="/chat">问答</router-link>
        <router-link to="/documents">文档管理</router-link>
        <a href="https://fusu.pw/article/18" target="_blank">使用演示</a>
        <a href="https://github.com/fusu51/DocMind" target="_blank">GitHub</a>
      </nav>
    </header>
    <main class="app-main">
      <router-view v-slot="{ Component }">
        <KeepAlive>
          <component :is="Component" />
        </KeepAlive>
      </router-view>
    </main>
    <AuthGate ref="authGate" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import AuthGate from './components/AuthGate.vue'
import { onShowAuth, isAuthed } from './auth.js'

const authGate = ref(null)

onMounted(() => {
  // 如果已有令牌，不弹窗
  if (isAuthed()) return
  // 注册全局认证拦截
  onShowAuth(() => authGate.value?.show())
})
</script>

<style scoped>
#app {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-header {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 12px 24px;
  border-bottom: 1px solid #e5e5e5;
  background: #fff;
}

.app-title {
  margin: 0;
  font-size: 20px;
}

.app-nav a {
  margin-right: 16px;
  text-decoration: none;
  color: #555;
  font-size: 14px;
}

.app-nav a.router-link-active {
  color: #2563eb;
  font-weight: 600;
}

.app-main {
  flex: 1;
  overflow: hidden;
}
</style>
