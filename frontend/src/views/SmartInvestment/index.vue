<template>
  <div class="smart-investment">
    <div class="chat-messages" ref="chatRef">
      <div
        v-for="(msg, i) in messages"
        :key="i"
        class="message"
        :class="msg.role"
      >
        <div class="message-avatar">
          <el-icon v-if="msg.role === 'assistant'"><MagicStick /></el-icon>
          <el-icon v-else><User /></el-icon>
        </div>
        <div class="message-content">
          <div class="message-text" v-html="renderMarkdown(msg.content)"></div>
        </div>
      </div>
      <div v-if="loading" class="message assistant">
        <div class="message-avatar">
          <el-icon class="is-loading"><Loading /></el-icon>
        </div>
        <div class="message-content">
          <div class="typing-indicator">
            <span>.</span><span>.</span><span>.</span>
          </div>
        </div>
      </div>
    </div>

    <div class="chat-input-bar">
      <el-input
        v-model="inputText"
        type="textarea"
        :rows="1"
        autosize
        placeholder="输入您的问题，Enter 发送，Shift+Enter 换行"
        :disabled="loading"
        @keydown="onInputKeydown"
      />
      <el-button
        type="primary"
        @click="sendMessage"
        :loading="loading"
        :disabled="!inputText.trim()"
        class="send-btn"
      >
        <el-icon><Promotion /></el-icon>
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, watch, onMounted, onBeforeUnmount, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { MagicStick, User, Loading, Promotion } from '@element-plus/icons-vue'
import { ApiClient } from '@/api/request'
import { marked } from 'marked'

marked.setOptions({ breaks: true, gfm: true })

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

const CACHE_KEY = 'smart_investment_state'

const saveState = () => {
  sessionStorage.setItem(CACHE_KEY, JSON.stringify({
    messages: messages.value
  }))
}

const restoreState = () => {
  try {
    const raw = sessionStorage.getItem(CACHE_KEY)
    if (raw) {
      const state = JSON.parse(raw)
      if (state?.messages?.length) {
        messages.value = state.messages
        return true
      }
    }
  } catch (e) {
    console.warn('恢复智能投资状态失败:', e)
  }
  return false
}

const inputText = ref('')
const loading = ref(false)
const messages = ref<ChatMessage[]>([
  {
    role: 'assistant',
    content: '你好！我是你的智能投资助手。你可以问我关于投资组合、持仓分析、市场趋势等方面的问题。'
  }
])
const chatRef = ref<HTMLElement | null>(null)

// 自动缓存消息变化
watch(messages, saveState, { deep: true })

const renderMarkdown = (content: string): string => {
  if (!content) return ''
  try {
    return marked.parse(content) as string
  } catch {
    return content
  }
}

const scrollToBottom = async () => {
  await nextTick()
  if (chatRef.value) {
    chatRef.value.scrollTop = chatRef.value.scrollHeight
  }
}

// 页面加载时恢复
onMounted(() => {
  if (restoreState()) {
    // 恢复后滚动到底部
    setTimeout(scrollToBottom, 100)
  }
})

// 页面离开前保存
onBeforeUnmount(() => {
  saveState()
})

const onInputKeydown = (e: KeyboardEvent) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage()
  }
}

const sendMessage = async () => {
  const text = inputText.value.trim()
  if (!text || loading.value) return

  messages.value.push({ role: 'user', content: text })
  inputText.value = ''
  loading.value = true
  await scrollToBottom()

  try {
    const response = await ApiClient.post('/api/agent/chat', { message: text })

    if (response?.success && response.data?.reply) {
      messages.value.push({
        role: 'assistant',
        content: response.data.reply
      })
    } else {
      messages.value.push({
        role: 'assistant',
        content: response.data?.reply || '抱歉，暂时无法回答这个问题。'
      })
    }
  } catch (e: any) {
    messages.value.push({
      role: 'assistant',
      content: '抱歉，暂时无法连接到智能服务，请稍后再试。'
    })
    console.warn('智能投资对话失败:', e)
  } finally {
    loading.value = false
    await scrollToBottom()
  }
}
</script>

<style lang="scss" scoped>
.smart-investment {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 100px);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 12px;
  background: var(--el-bg-color);
  overflow: hidden;

  .chat-messages {
    flex: 1;
    overflow-y: auto;
    padding: 20px;
    display: flex;
    flex-direction: column;
    gap: 16px;

    .message {
      display: flex;
      gap: 12px;
      max-width: 80%;

      &.user {
        align-self: flex-end;
        flex-direction: row-reverse;

        .message-avatar {
          background: var(--el-color-primary);
          color: #fff;
        }

        .message-content {
          background: var(--el-color-primary-light-8);
          border-radius: 12px 4px 12px 12px;
        }
      }

      &.assistant {
        .message-avatar {
          background: var(--el-color-success-light-7);
          color: var(--el-color-success);
        }

        .message-content {
          background: var(--el-fill-color-light);
          border-radius: 4px 12px 12px 12px;
        }
      }

      .message-avatar {
        width: 36px;
        height: 36px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
        font-size: 18px;
      }

      .message-content {
        padding: 12px 16px;
        font-size: 14px;
        line-height: 1.7;
        color: var(--el-text-color-primary);

        .message-text {
          :deep(h1), :deep(h2), :deep(h3) {
            margin: 16px 0 8px 0;
            font-weight: 600;
            color: var(--el-text-color-primary);
          }

          :deep(h1) { font-size: 18px; }
          :deep(h2) { font-size: 16px; }
          :deep(h3) { font-size: 15px; }

          :deep(p) {
            margin: 8px 0;
            line-height: 1.7;
          }

          :deep(ul), :deep(ol) {
            margin: 8px 0;
            padding-left: 24px;

            li { margin: 4px 0; line-height: 1.7; }
          }

          :deep(strong) { font-weight: 600; color: var(--el-text-color-primary); }

          :deep(code) {
            background: var(--el-fill-color-darker);
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 13px;
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
          }

          :deep(pre) {
            background: var(--el-fill-color-darker);
            padding: 14px 16px;
            border-radius: 8px;
            overflow-x: auto;
            margin: 12px 0;
            code { background: none; padding: 0; font-size: 13px; }
          }

          :deep(blockquote) {
            margin: 12px 0;
            padding: 8px 16px;
            border-left: 3px solid var(--el-color-primary-light-5);
            background: var(--el-fill-color-lighter);
            border-radius: 0 8px 8px 0;
            color: var(--el-text-color-secondary);
            font-size: 13px;
          }

          :deep(table) {
            width: 100%;
            border-collapse: collapse;
            margin: 12px 0;
            font-size: 13px;
            th, td { padding: 8px 12px; border: 1px solid var(--el-border-color-lighter); text-align: left; }
            th { background: var(--el-fill-color-light); font-weight: 600; }
          }

          :deep(hr) { margin: 16px 0; border: none; border-top: 1px solid var(--el-border-color-lighter); }
        }

        .typing-indicator {
          display: flex; gap: 4px; padding: 4px 0;
          span { animation: blink 1.4s infinite both; &:nth-child(2) { animation-delay: 0.2s; } &:nth-child(3) { animation-delay: 0.4s; } }
        }
      }
    }

    @keyframes blink { 0%, 80%, 100% { opacity: 0; } 40% { opacity: 1; } }
  }

  .chat-input-bar {
    display: flex;
    align-items: flex-end;
    gap: 12px;
    padding: 16px 20px;
    border-top: 1px solid var(--el-border-color-lighter);
    background: var(--el-bg-color);

    .el-textarea {
      flex: 1;
    }

    :deep(.el-textarea__inner) {
      border-radius: 10px;
      padding: 10px 14px;
      font-size: 14px;
      line-height: 1.5;
      min-height: 42px;
      max-height: 120px;
    }

    .send-btn {
      flex-shrink: 0;
      height: 42px;
      width: 42px;
      padding: 0;
      border-radius: 10px;
      font-size: 18px;
    }
  }
}
</style>
