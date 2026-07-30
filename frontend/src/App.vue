<template>
  <div id="app">
    <header class="app-header">
      <h1 class="app-title">📚 DocMind</h1>
      <nav class="app-nav">
        <router-link to="/chat">问答</router-link>
        <router-link to="/documents">文档管理</router-link>
      </nav>
    </header>
    <main class="app-main">
      <router-view v-slot="{ Component }">
        <KeepAlive>
          <component :is="Component" />
        </KeepAlive>
      </router-view>
    </main>
  </div>
</template>

<script setup>
// 根组件，仅提供导航和路由出口
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
