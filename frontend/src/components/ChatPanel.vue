<template>
  <div class="chat-panel" ref="scrollRef">
    <div v-if="messages.length === 0" class="empty-hint">
      👋 上传文档后开始提问
    </div>

    <div
        v-for="(msg, i) in messages"
        :key="i"
        class="message"
        :class="msg.role"
    >
      <div class="message-avatar">{{ msg.role === 'user' ? '👤' : '🤖' }}</div>
      <div class="message-body">
        <div v-if="msg.role === 'user'" class="message-text">{{ msg.content }}</div>

        <template v-else>
          <!-- 管线面板 -->
          <details v-if="msg.pipeline" class="pipeline-box" :open="msg.streaming && !msg.content">
            <summary>🔬 检索管线</summary>
            <div class="pipeline-grid">
              <!-- L1 -->
              <div class="pipe-layer">
                <span class="pipe-label">L1 查询</span>
                <span class="pipe-value">{{ msg.pipeline.l1.method }}</span>
              </div>
              <!-- L2 -->
              <div class="pipe-layer">
                <span class="pipe-label">L2 召回</span>
                <span class="pipe-value">
                  语义 {{ msg.pipeline.l2.dense }} 条 + 关键词 {{ msg.pipeline.l2.sparse }} 条 → {{ msg.pipeline.l2.method }}
                </span>
              </div>
              <!-- L3 -->
              <div class="pipe-layer">
                <span class="pipe-label">L3 重排</span>
                <span class="pipe-value">
                  <template v-if="msg.pipeline.l3.enabled">
                    候选 {{ msg.pipeline.l3.candidates }} → 精选 {{ msg.pipeline.l3.final }} 条 ({{ msg.pipeline.l3.method }})
                  </template>
                  <template v-else>
                    候选不足，跳过 → {{ msg.pipeline.l3.final }} 条
                  </template>
                </span>
              </div>
              <!-- 拒答判定 -->
              <div v-if="msg.pipeline?.abstain_level && msg.pipeline.abstain_level !== 'none'" class="pipe-layer">
                <span class="pipe-label" style="color:#dc2626">拒答判定</span>
                <span class="pipe-value" style="color:#dc2626">
                  Top1 分数 {{ msg.pipeline.top1_score }} → {{ msg.pipeline.abstain_level === 'hard' ? '硬拒答（跳过 LLM）' : '软拒答（注入强拒答指令）' }}
                </span>
              </div>

              <!-- L4 -->
              <div class="pipe-layer">
                <span class="pipe-label">L4 压缩</span>
                <span class="pipe-value">
                  {{ msg.pipeline.l4.original }} 条 · 预算 {{ msg.pipeline.l4.max_tokens }} tokens
                </span>
              </div>
            </div>
          </details>

          <!-- 拒答提示 -->
          <div v-if="msg.abstain" class="abstain-notice">⚠️ {{ msg.abstain }}</div>

          <!-- 思考中占位 -->
          <div v-if="msg.streaming && !msg.reasoning && !msg.content" class="thinking-hint">
            🤔 正在分析文档...
          </div>

          <!-- 思考过程 -->
          <details v-if="msg.reasoning" class="reasoning-box" :open="msg.streaming">
            <summary>{{ msg.streaming ? '🧠 思考中...' : '🧠 思考过程' }}</summary>
            <p class="reasoning-text">{{ msg.reasoning }}</p>
          </details>

          <!-- 正式回答 -->
          <div v-if="msg.content" class="message-text" v-html="renderMarkdown(msg.content)"></div>

          <!-- 来源引用 -->
          <div v-if="msg.sources && msg.sources.length" class="sources-list">
            <SourceCard
                v-for="(s, si) in msg.sources"
                :key="si"
                :source="s"
                :index="si + 1"
            />
          </div>

          <span v-if="msg.streaming" class="streaming-cursor">▍</span>
        </template>
      </div>
    </div>
  </div>
</template>


<script setup>
import { ref, nextTick } from 'vue'
import { chatStream } from '../api/index.js'
import SourceCard from './SourceCard.vue'

const messages = ref([])
const scrollRef = ref(null)


function sendMessage(question, docId) {
  // 收集最近 3 轮对话
  const history = messages.value
      .filter(m => !m.streaming && (m.role === 'user' || m.role === 'assistant'))
      .slice(-6)
      .map(m => ({ role: m.role, content: m.content }))

  messages.value.push({ role: 'user', content: question })
  const aiIndex = messages.value.length
  messages.value.push({
    role: 'assistant',
    content: '',
    reasoning: '',
    sources: [],
    pipeline: null,
    streaming: true,
  })

  chatStream(question, docId, history, {
    onPipeline(pipeline) {
      messages.value[aiIndex].pipeline = pipeline
    },
    onToken(token) {
      messages.value[aiIndex].content += token
      scrollToBottom()
    },
    onReasoning(token) {
      messages.value[aiIndex].reasoning += token
      scrollToBottom()
    },
    onSources(sources) {
      messages.value[aiIndex].sources = sources
    },
    onAbstain(message) {
      messages.value[aiIndex].abstain = message
      messages.value[aiIndex].streaming = false
    },
    onDone() {
      messages.value[aiIndex].streaming = false
      scrollToBottom()
    },
    onError(err) {
      messages.value[aiIndex].content = `❌ 出错了：${err.message}`
      messages.value[aiIndex].streaming = false
    },
  })
}


function scrollToBottom() {
  nextTick(() => {
    if (scrollRef.value) {
      scrollRef.value.scrollTop = scrollRef.value.scrollHeight
    }
  })
}


function loadHistoryMessages(conv) {
  messages.value = []

  messages.value.push({ role: 'user', content: conv.question })

  let sources = []
  try { sources = JSON.parse(conv.sources) || [] } catch {}

  let pipeline = null
  try { pipeline = JSON.parse(conv.pipeline) || null } catch {}

  messages.value.push({
    role: 'assistant',
    content: conv.answer,
    reasoning: conv.reasoning || '',
    sources: sources,
    pipeline: pipeline,
    streaming: false,
  })

  scrollToBottom()
}


function renderMarkdown(text) {
  if (!text) return ''
  let html = text
      // 转义 HTML
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      // 粗体 **text**
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      // 斜体 *text*
      .replace(/\*(.+?)\*/g, '<em>$1</em>')
      // 行内代码 `code`
      .replace(/`(.+?)`/g, '<code>$1</code>')
      // 换行 → <br>
      .replace(/\n/g, '<br>')
  return html
}


function clearMessages() {
  messages.value = []
}

defineExpose({ sendMessage, loadHistoryMessages, clearMessages })
</script>

<style scoped>
.chat-panel {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.empty-hint {
  text-align: center;
  color: #999;
  margin-top: 120px;
  font-size: 15px;
}

.message {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
}

.message.assistant {
  flex-direction: row;
}

.message.user {
  flex-direction: row-reverse;
}

.message-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #f0f0f0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  flex-shrink: 0;
}

.message-body {
  max-width: 75%;
  background: #f5f5f5;
  border-radius: 12px;
  padding: 10px 14px;
  line-height: 1.6;
  font-size: 14px;
}

.message.user .message-body {
  background: #2563eb;
  color: #fff;
}

.streaming-cursor {
  animation: blink 1s infinite;
  color: #2563eb;
}

@keyframes blink {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0;
  }
}

.sources-list {
  margin-top: 10px;
  border-top: 1px solid #e5e5e5;
  padding-top: 8px;
}

.reasoning-box {
  margin-bottom: 10px;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  padding: 6px 10px;
  background: #fafafa;
}

.reasoning-box summary {
  font-size: 12px;
  color: #888;
  cursor: pointer;
}

.reasoning-text {
  margin: 6px 0 0;
  font-size: 12px;
  color: #999;
  white-space: pre-wrap;
  line-height: 1.5;
}

.thinking-hint {
  color: #999;
  font-size: 13px;
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.4;
  }
}

.pipeline-box {
  margin-bottom: 10px;
  border: 1px solid #dbeafe;
  border-radius: 8px;
  padding: 8px 12px;
  background: #f8fafc;
}

.pipeline-box summary {
  font-size: 13px;
  font-weight: 600;
  color: #2563eb;
  cursor: pointer;
}

.pipeline-grid {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-top: 6px;
}

.pipe-layer {
  display: flex;
  gap: 8px;
  font-size: 11px;
  line-height: 1.6;
}

.pipe-label {
  flex-shrink: 0;
  width: 52px;
  color: #64748b;
  font-weight: 500;
}

.pipe-value {
  color: #334155;
}

.abstain-notice {
  color: #dc2626;
  font-size: 13px;
  font-weight: 500;
  padding: 8px 0;
}
</style>
