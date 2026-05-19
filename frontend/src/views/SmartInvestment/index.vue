<template>
  <div class="smart-investment">
    <div class="page-header">
      <div class="header-content">
        <h1 class="page-title">
          <el-icon class="title-icon"><MagicStick /></el-icon>
          <span>智能投资</span>
        </h1>
        <p class="page-description">
          通过自然语言与 AI 对话，查看投资状况、分析持仓、获取投资建议
        </p>
      </div>
    </div>

    <el-card class="chat-card" shadow="never">
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
            <div class="message-text">{{ msg.content }}</div>
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

      <div class="chat-input">
        <el-input
          v-model="inputText"
          type="textarea"
          :rows="3"
          placeholder="输入您的问题，例如：&#10;- 我的投资组合整体风险如何？&#10;- 帮我分析一下持仓的股票&#10;- 根据我的投资偏好，有什么调仓建议？"
          :disabled="loading"
          @keydown.enter.ctrl="sendMessage"
        />
        <div class="input-footer">
          <span class="input-hint">Ctrl+Enter 发送</span>
          <el-button type="primary" @click="sendMessage" :loading="loading">
            <el-icon><Promotion /></el-icon>
            发送
          </el-button>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { MagicStick, User, Loading, Promotion } from '@element-plus/icons-vue'

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
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

const scrollToBottom = async () => {
  await nextTick()
  if (chatRef.value) {
    chatRef.value.scrollTop = chatRef.value.scrollHeight
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
    const response = await fetch('/api/agent/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: text,
        context: {
          user_id: 'current',
          source: 'smart_investment'
        }
      })
    })

    if (!response.ok) throw new Error('请求失败')

    const data = await response.json()
    messages.value.push({
      role: 'assistant',
      content: data.reply || '抱歉，暂时无法回答这个问题。'
    })
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
  .page-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 24px;
    padding: 20px 24px;
    background: linear-gradient(135deg, var(--el-color-primary-light-9) 0%, var(--el-fill-color-light) 100%);
    border-radius: 12px;
    border: 1px solid var(--el-border-color-lighter);

    .header-content {
      .page-title {
        font-size: 22px;
        font-weight: 600;
        margin: 0 0 6px 0;
        display: flex;
        align-items: center;
        gap: 10px;
        color: var(--el-text-color-primary);

        .title-icon {
          color: var(--el-color-primary);
          font-size: 26px;
        }
      }

      .page-description {
        color: var(--el-text-color-secondary);
        margin: 0;
        font-size: 13px;
      }
    }
  }

  .chat-card {
    border-radius: 12px;
    border: 1px solid var(--el-border-color-lighter);

    .chat-messages {
      height: 480px;
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
          line-height: 1.6;
          color: var(--el-text-color-primary);

          .typing-indicator {
            display: flex;
            gap: 4px;
            padding: 4px 0;

            span {
              animation: blink 1.4s infinite both;

              &:nth-child(2) { animation-delay: 0.2s; }
              &:nth-child(3) { animation-delay: 0.4s; }
            }
          }
        }
      }

      @keyframes blink {
        0%, 80%, 100% { opacity: 0; }
        40% { opacity: 1; }
      }
    }

    .chat-input {
      border-top: 1px solid var(--el-border-color-lighter);
      padding: 16px 20px;

      .input-footer {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-top: 12px;

        .input-hint {
          font-size: 12px;
          color: var(--el-text-color-placeholder);
        }
      }
    }
  }
}
</style>
