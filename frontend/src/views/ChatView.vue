<template>
  <div class="chat-view">
    <!-- 左侧历史 -->
    <ConversationHistory
        ref="historyRef"
        :activeId="activeConvId"
        @select="loadConversation"
        @newChat="newChat"
    />

    <!-- 右侧聊天区 -->
    <div class="chat-main">
      <div class="chat-toolbar">
        <DocSelect v-model="selectedDocId" />
      </div>

      <ChatPanel ref="chatPanel" />

      <MessageInput
          :disabled="loading"
          @send="handleSend"
      />
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import DocSelect from '../components/DocSelect.vue'
import ChatPanel from '../components/ChatPanel.vue'
import MessageInput from '../components/MessageInput.vue'
import ConversationHistory from '../components/ConversationHistory.vue'
import { requireAuth } from '../auth.js'

const route = useRoute()
const chatPanel = ref(null)
const historyRef = ref(null)
const loading = ref(false)
const activeConvId = ref(null)

const selectedDocId = ref(route.params.docId || null)

function handleSend(question) {
  if (!requireAuth()) return
  activeConvId.value = null
  chatPanel.value?.sendMessage(question, selectedDocId.value)
}

function loadConversation(conv) {
  activeConvId.value = conv.id
  chatPanel.value?.loadHistoryMessages(conv)
}

function newChat() {
  activeConvId.value = null
  chatPanel.value?.clearMessages()
}
</script>

<style scoped>
.chat-view {
  display: flex;
  height: 100%;
}

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.chat-toolbar {
  padding: 8px 16px;
  border-bottom: 1px solid #eee;
  background: #fafafa;
}
</style>
