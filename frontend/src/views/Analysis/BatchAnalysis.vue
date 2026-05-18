<template>
  <div class="batch-analysis">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-content">
        <div class="title-section">
          <h1 class="page-title">
            <el-icon class="title-icon"><Files /></el-icon>
            批量分析
          </h1>
          <p class="page-description">
            AI驱动的批量股票分析，高效处理多只股票
          </p>
        </div>
      </div>

    </div>

    <!-- 股票列表输入区域 -->
    <div class="analysis-container">
      <el-row :gutter="24">
        <el-col :span="24">
          <el-card class="stock-list-card" shadow="hover">
            <template #header>
              <div class="card-header">
                <h3>📋 股票列表</h3>
                <el-tag :type="stockCodes.length > 0 ? 'success' : 'info'" size="small">
                  {{ stockCodes.length }} 只股票
                </el-tag>
              </div>
            </template>

            <div class="stock-input-section">
              <div class="input-area">
                <el-input
                  v-model="stockInput"
                  type="textarea"
                  :rows="8"
                  placeholder="请输入股票代码，每行一个&#10;支持格式：&#10;000001&#10;000002.SZ&#10;600036.SH&#10;AAPL&#10;TSLA"
                  @input="parseStockCodes"
                  class="stock-textarea"
                />
                <div class="input-actions">
                  <el-button type="primary" @click="parseStockCodes" size="small">
                    解析股票代码
                  </el-button>
                  <el-button @click="clearStocks" size="small">清空</el-button>
                </div>
              </div>

              <!-- 股票预览 -->
              <div v-if="stockCodes.length > 0" class="stock-preview">
                <h4>股票预览</h4>
                <div class="stock-tags">
                  <el-tag
                    v-for="(code, index) in stockCodes.slice(0, 20)"
                    :key="code"
                    closable
                    @close="removeStock(index)"
                    class="stock-tag"
                    :type="stockCodeNames[code] ? 'success' : 'info'"
                  >
                    {{ code }}
                    <span v-if="stockCodeNames[code]" style="margin-left: 4px; font-weight: 500;">
                      {{ stockCodeNames[code] }}
                    </span>
                  </el-tag>
                  <el-tag v-if="stockCodes.length > 20" type="info">
                    +{{ stockCodes.length - 20 }} 更多...
                  </el-tag>
                </div>
              </div>

              <!-- 无效代码提示 -->
              <div v-if="invalidCodes.length > 0" class="invalid-codes">
                <el-alert
                  title="以下股票代码格式可能有误，请检查："
                  type="warning"
                  :closable="false"
                >
                  <div class="invalid-list">
                    <el-tag v-for="code in invalidCodes" :key="code" type="danger" size="small">
                      {{ code }}
                    </el-tag>
                  </div>
                </el-alert>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 分析配置区域 -->
      <el-row :gutter="24" style="margin-top: 24px;">
        <!-- 左侧：分析配置 -->
        <el-col :span="18">
          <el-card class="config-card" shadow="hover">
            <template #header>
              <div class="card-header">
                <h3>⚙️ 分析配置</h3>
                <el-tag type="primary" size="small">批量设置</el-tag>
              </div>
            </template>

            <el-form :model="batchForm" label-width="100px" class="batch-form">
              <!-- 基础信息 -->
              <div class="form-section">
                <h4 class="section-title">📋 基础信息</h4>
                <el-form-item label="批次标题" required>
                  <el-input
                    v-model="batchForm.title"
                    placeholder="如：银行板块分析"
                    size="large"
                  />
                </el-form-item>

                <el-form-item label="批次描述">
                  <el-input
                    v-model="batchForm.description"
                    type="textarea"
                    :rows="2"
                    placeholder="描述本次批量分析的目的和背景（可选）"
                  />
                </el-form-item>
              </div>

              <!-- 分析深度 -->
              <div class="form-section">
                <h4 class="section-title">🎯 分析深度</h4>
                <div class="depth-selector">
                  <div
                    v-for="(depth, index) in depthOptions"
                    :key="index"
                    class="depth-option"
                    :class="{ active: Number(batchForm.depth) === index + 1 }"
                    @click="batchForm.depth = String(index + 1)"
                  >
                    <div class="depth-icon">{{ depth.icon }}</div>
                    <div class="depth-info">
                      <div class="depth-name">{{ depth.name }}</div>
                      <div class="depth-desc">{{ depth.description }}</div>
                      <div class="depth-time">{{ depth.time }}</div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 分析师团队 -->
              <div class="form-section">
                <h4 class="section-title">👥 分析师团队</h4>
                <div class="analysts-grid">
                  <div
                    v-for="analyst in ANALYSTS"
                    :key="analyst.id"
                    class="analyst-card"
                    :class="{ active: batchForm.analysts.includes(analyst.name) }"
                    @click="toggleBatchAnalyst(analyst.name)"
                  >
                    <div class="analyst-avatar">
                      <el-icon>
                        <component :is="analyst.icon" />
                      </el-icon>
                    </div>
                    <div class="analyst-content">
                      <div class="analyst-name">{{ analyst.name }}</div>
                      <div class="analyst-desc">{{ analyst.description }}</div>
                    </div>
                    <div class="analyst-check">
                      <el-icon v-if="batchForm.analysts.includes(analyst.name)" class="check-icon">
                        <Check />
                      </el-icon>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 操作按钮 -->
              <div class="form-section">
                <div class="action-buttons" style="display: flex; justify-content: center; align-items: center; width: 100%; text-align: center;">
                  <el-button
                    type="primary"
                    size="large"
                    @click="submitBatchAnalysis"
                    :loading="submitting"
                    :disabled="stockCodes.length === 0"
                    class="submit-btn large-batch-btn"
                    style="width: 320px; height: 56px; font-size: 18px; font-weight: 700; border-radius: 16px;"
                  >
                    <el-icon><TrendCharts /></el-icon>
                    开始批量分析 ({{ stockCodes.length }}只)
                  </el-button>
                </div>
              </div>
            </el-form>
          </el-card>
        </el-col>

        <!-- 右侧：高级配置 -->
        <el-col :span="6">
          <el-card class="advanced-config-card" shadow="hover">
            <template #header>
              <div class="card-header">
                <h3>🔧 高级配置</h3>
              </div>
            </template>

            <div class="config-content">
              <!-- AI模型配置组件 -->
              <ModelConfig
                v-model:quick-analysis-model="modelSettings.quickAnalysisModel"
                v-model:deep-analysis-model="modelSettings.deepAnalysisModel"
                :available-models="availableModels"
                :analysis-depth="batchForm.depth"
              />

              <!-- 分析选项 -->
              <div class="config-section">
                <h4 class="config-title">⚙️ 分析选项</h4>
                <div class="analysis-options">
                  <div class="option-item">
                    <div class="option-info">
                      <span class="option-name">情绪分析</span>
                      <span class="option-desc">分析市场情绪和投资者心理</span>
                    </div>
                    <el-switch v-model="batchForm.includeSentiment" />
                  </div>

                  <div class="option-item">
                    <div class="option-info">
                      <span class="option-name">风险评估</span>
                      <span class="option-desc">包含详细的风险因素分析</span>
                    </div>
                    <el-switch v-model="batchForm.includeRisk" />
                  </div>

                  <div class="option-item">
                    <div class="option-info">
                      <span class="option-name">语言偏好</span>
                    </div>
                    <el-select v-model="batchForm.language" size="small" style="width: 100px">
                      <el-option label="中文" value="zh-CN" />
                      <el-option label="English" value="en-US" />
                    </el-select>
                  </div>
                </div>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <!-- 股票预览 -->
    <el-card v-if="stockCodes.length > 0" class="stock-preview-card" shadow="never">
      <template #header>
        <div class="card-header">
          <h3>股票预览 ({{ stockCodes.length }}只)</h3>
          <el-button type="text" @click="validateStocks">
            <el-icon><Check /></el-icon>
            验证股票代码
          </el-button>
        </div>
      </template>

      <div class="stock-grid">
        <div
          v-for="(code, index) in stockCodes"
          :key="index"
          class="stock-item"
          :class="{ invalid: invalidCodes.includes(code), 'has-name': stockCodeNames[code] }"
        >
          <span class="stock-code">{{ code }}</span>
          <span v-if="stockCodeNames[code]" class="stock-name">{{ stockCodeNames[code] }}</span>
          <el-button
            type="text"
            size="small"
            @click="removeStock(index)"
            class="remove-btn"
          >
            <el-icon><Close /></el-icon>
          </el-button>
        </div>
      </div>

      <div v-if="invalidCodes.length > 0" class="invalid-notice">
        <el-alert
          title="发现无效股票代码"
          type="warning"
          :description="`以下股票代码可能无效：${invalidCodes.join(', ')}`"
          show-icon
          :closable="false"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Files, TrendCharts, Check, Close } from '@element-plus/icons-vue'
import { ANALYSTS, DEFAULT_ANALYSTS, convertAnalystNamesToIds } from '@/constants/analysts'

// 分析深度选项
const depthOptions = [
  { icon: '⚡', name: '1级 - 快速分析', description: '基础数据概览，快速决策', time: '2-4分钟/只' },
  { icon: '📈', name: '2级 - 基础分析', description: '常规投资决策', time: '4-6分钟/只' },
  { icon: '🎯', name: '3级 - 标准分析', description: '技术+基本面，推荐', time: '6-10分钟/只' },
  { icon: '🔍', name: '4级 - 深度分析', description: '多轮辩论，深度研究', time: '10-15分钟/只' },
  { icon: '🏆', name: '5级 - 全面分析', description: '最全面的分析报告', time: '15-25分钟/只' }
]
import { configApi } from '@/api/config'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import ModelConfig from '@/components/ModelConfig.vue'
import { getMarketByStockCode } from '@/utils/market'
import { validateStockCode } from '@/utils/stockValidator'
import { searchStockBasics } from '@/api/cache'

// 路由实例（必须在顶层调用）
const router = useRouter()
const route = useRoute()

const submitting = ref(false)
const stockInput = ref('')
const stockCodes = ref<string[]>([])  // 保留用于表单绑定
const symbols = ref<string[]>([])     // 标准化后的代码列表
const invalidCodes = ref<string[]>([])
const stockCodeNames = ref<Record<string, string>>({}) // 代码 -> 名称映射

// 模型设置
const modelSettings = ref({
  quickAnalysisModel: '',
  deepAnalysisModel: ''
})

// 可用的模型列表（从配置中获取）
const availableModels = ref<any[]>([])

const batchForm = reactive({
  title: '',
  description: '',
  depth: '3',  // 默认3级标准分析，将在 onMounted 中从用户偏好加载
  analysts: [...DEFAULT_ANALYSTS],  // 将在 onMounted 中从用户偏好加载
  includeSentiment: true,
  includeRisk: true,
  language: 'zh-CN'
})

// 使用通用校验器规范化代码，自动识别市场
const normalizeCodeSmart = (raw: string): { symbol?: string; error?: string } => {
  const code = String(raw || '').trim()
  if (!code) return { error: '空代码' }

  // 自动识别市场
  const v = validateStockCode(code)
  if (v.valid && v.normalizedCode) return { symbol: v.normalizedCode }

  return { error: v.message || '代码格式无效' }
}

const parseStockCodes = async () => {
  const codes = stockInput.value
    .split('\n')
    .map(code => code.trim())
    .filter(code => code.length > 0)
    .filter((code, index, arr) => arr.indexOf(code) === index) // 去重

  const normalized: string[] = []
  const invalid: string[] = []
  for (const c of codes) {
    const { symbol } = normalizeCodeSmart(c)
    if (symbol) normalized.push(symbol)
    else invalid.push(c)
  }

  stockCodes.value = normalized
  symbols.value = [...normalized]
  invalidCodes.value = invalid

  // 批量查询本地基础信息补充名称
  if (normalized.length > 0) {
    stockCodeNames.value = {}
    await fetchStockNames(normalized)
  }
}

// 批量查询股票名称
const fetchStockNames = async (codes: string[]) => {
  if (codes.length === 0) return
  try {
    // 一次性查询所有代码（用逗号分隔或直接取第一个代码查询全部）
    // 由于接口是 keyword 搜索，我们用第一个代码作为 keyword，limit 设大些
    // 更好的方式是逐个查询，但为了不频繁请求，我们批量用第一个字符查询
    const response = await searchStockBasics(codes[0], Math.max(codes.length * 5, 50))
    const results = response.data || []
    for (const code of codes) {
      const match = results.find((item: any) => {
        if (!item) return false
        const sym = (item.symbol || '').trim()
        const ts = (item.ts_code || '').trim()
        return sym === code || ts === code || ts.startsWith(code + '.')
      })
      if (match && match.name) {
        stockCodeNames.value[code] = match.name
      }
    }
  } catch (e) {
    console.warn('批量查询股票名称失败:', e)
  }
}

const clearStocks = () => {
  stockInput.value = ''
  stockCodes.value = []
  symbols.value = []
  invalidCodes.value = []
  stockCodeNames.value = {}
}

// 初始化模型设置
const initializeModelSettings = async () => {
  try {
    const sortModelsByNewest = (configs: any[]) => {
      const getTimestamp = (config: any) => {
        const timeValue = config.created_at || config.updated_at
        const timestamp = timeValue ? new Date(timeValue).getTime() : 0
        return Number.isNaN(timestamp) ? 0 : timestamp
      }

      return [...configs].sort((a, b) => getTimestamp(b) - getTimestamp(a))
    }

    // 1️⃣ 先获取所有可用的模型列表
    const llmConfigs = await configApi.getLLMConfigs()
    availableModels.value = sortModelsByNewest(
      llmConfigs.filter((config: any) => config.enabled)
    )

    // 2️⃣ 获取后端推荐的默认模型
    const defaultModels = await configApi.getDefaultModels()
    let quickModel = defaultModels.quick_analysis_model
    let deepModel = defaultModels.deep_analysis_model

    // 3️⃣ 如果后端未返回默认模型，或返回的模型不在可用列表中，自动选择第一个可用模型
    const availableModelNames = new Set(availableModels.value.map(m => m.model_name))
    if (!quickModel || !availableModelNames.has(quickModel)) {
      const fallback = availableModels.value[0]?.model_name || ''
      console.warn(`⚠️ 快速模型 '${quickModel}' 不可用，自动选择第一个可用模型: ${fallback}`)
      quickModel = fallback
    }
    if (!deepModel || !availableModelNames.has(deepModel)) {
      const fallback = availableModels.value[0]?.model_name || ''
      console.warn(`⚠️ 深度模型 '${deepModel}' 不可用，自动选择第一个可用模型: ${fallback}`)
      deepModel = fallback
    }

    modelSettings.value.quickAnalysisModel = quickModel
    modelSettings.value.deepAnalysisModel = deepModel

    console.log('✅ 加载模型配置成功:', {
      quick: modelSettings.value.quickAnalysisModel,
      deep: modelSettings.value.deepAnalysisModel,
      available: availableModels.value.length
    })
  } catch (error) {
    console.error('❌ 加载默认模型配置失败:', error)
    modelSettings.value.quickAnalysisModel = ''
    modelSettings.value.deepAnalysisModel = ''
  }
}

// 页面初始化
onMounted(async () => {
  await initializeModelSettings()

  // 🆕 从用户偏好加载默认设置
  const authStore = useAuthStore()
  const userPrefs = authStore.user?.preferences

  if (userPrefs) {
    // 加载默认分析深度
    if (userPrefs.default_depth) {
      batchForm.depth = userPrefs.default_depth
    }

    // 加载默认分析师
    if (userPrefs.default_analysts && userPrefs.default_analysts.length > 0) {
      batchForm.analysts = [...userPrefs.default_analysts]
    }

    console.log('✅ 批量分析已加载用户偏好设置:', {
      depth: batchForm.depth,
      analysts: batchForm.analysts
    })
  }

  // 读取路由查询参数以便从筛选页预填充（路由参数优先级最高）
  const q = route.query as any
  if (q?.stocks) {
    const parts = String(q.stocks).split(',').map((s) => s.trim()).filter(Boolean)
    stockCodes.value = parts
    stockInput.value = parts.join('\n')
    // 触发解析以更新 symbols
    parseStockCodes()
  }
})

const removeStock = (index: number) => {
  const removedCode = stockCodes.value[index]
  stockCodes.value.splice(index, 1)

  // 更新输入框
  stockInput.value = stockCodes.value.join('\n')

  // 从无效列表中移除
  const invalidIndex = invalidCodes.value.indexOf(removedCode)
  if (invalidIndex > -1) {
    invalidCodes.value.splice(invalidIndex, 1)
  }

  // 从名称映射中移除
  delete stockCodeNames.value[removedCode]
}

// 切换分析师
const toggleBatchAnalyst = (analystName: string) => {
  const index = batchForm.analysts.indexOf(analystName)
  if (index > -1) {
    batchForm.analysts.splice(index, 1)
  } else {
    batchForm.analysts.push(analystName)
  }
}

const validateStocks = async () => {
  // 按当前市场重新规范化并验证
  const invalid: string[] = []
  const valid: string[] = []
  for (const c of stockCodes.value) {
    const { symbol } = normalizeCodeSmart(c)
    if (symbol) valid.push(symbol)
    else invalid.push(c)
  }
  stockCodes.value = valid
  symbols.value = [...valid]
  invalidCodes.value = invalid

  if (invalid.length === 0) {
    ElMessage.success('所有股票代码验证通过')
  } else {
    ElMessage.warning(`发现 ${invalid.length} 个无效股票代码`)
  }
}

const submitBatchAnalysis = async () => {
  if (!batchForm.title) {
    ElMessage.warning('请输入批次标题')
    return
  }

  if (stockCodes.value.length === 0) {
    ElMessage.warning('请输入股票代码')
    return
  }

  if (stockCodes.value.length > 10) {
    ElMessage.warning('单次批量分析最多支持10只股票，请减少股票数量')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确定要提交批量分析任务吗？\n批次：${batchForm.title}\n股票数量：${stockCodes.value.length}只`,
      '确认提交',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'info'
      }
    )

    submitting.value = true

    // 准备批量分析请求参数（真实API调用）
    const batchRequest = {
      title: batchForm.title,
      description: batchForm.description,
      symbols: symbols.value,
      stock_codes: symbols.value,  // 兼容字段
      parameters: {
        // 若全部代码可识别为同一市场则携带；否则省略让后端自行判断
        market_type: (() => {
          const markets = new Set(symbols.value.map(s => getMarketByStockCode(s)))
          return markets.size === 1 ? Array.from(markets)[0] : undefined
        })(),
        research_depth: batchForm.depth,
        selected_analysts: convertAnalystNamesToIds(batchForm.analysts),
        include_sentiment: batchForm.includeSentiment,
        include_risk: batchForm.includeRisk,
        language: batchForm.language,
        quick_analysis_model: modelSettings.value.quickAnalysisModel,
        deep_analysis_model: modelSettings.value.deepAnalysisModel
      }
    }

    // 调用真实的批量分析API
    const { analysisApi } = await import('@/api/analysis')
    const response = await analysisApi.startBatchAnalysis(batchRequest)

    if (!response?.success) {
      throw new Error(response?.message || '批量分析提交失败')
    }

    const { batch_id, total_tasks } = response.data

    // 显示成功提示并引导用户去任务中心
    ElMessageBox.confirm(
      `✅ 批量分析任务已成功提交！\n\n📊 股票数量：${total_tasks}只\n📋 批次ID：${batch_id}\n\n任务正在后台执行中，最多同时执行3个任务，其他任务会自动排队等待。\n\n是否前往任务中心查看进度？`,
      '提交成功',
      {
        confirmButtonText: '前往任务中心',
        cancelButtonText: '留在当前页面',
        type: 'success',
        distinguishCancelAndClose: true,
        closeOnClickModal: false
      }
    ).then(() => {
      // 用户点击"前往任务中心"
      router.push({ path: '/tasks', query: { batch_id } })
    }).catch((action) => {
      // 用户点击"留在当前页面"或关闭对话框
      if (action === 'cancel') {
        ElMessage.info('任务正在后台执行，您可以随时前往任务中心查看进度')
      }
    })

  } catch (error: any) {
    // 处理错误
    if (error !== 'cancel') {
      ElMessage.error(error.message || '批量分析提交失败')
    }
  } finally {
    submitting.value = false
  }
}

</script>

<style lang="scss" scoped>
.batch-analysis {
  min-height: 100vh;
  background: var(--el-bg-color-page);
  padding: 24px;

  .page-header {
    margin-bottom: 24px;

    .header-content {
      background: linear-gradient(135deg, var(--el-color-primary-light-9) 0%, var(--el-fill-color-light) 100%);
      padding: 20px 24px;
      border-radius: 12px;
      border: 1px solid var(--el-border-color-lighter);
      box-shadow: var(--el-box-shadow-lighter);
    }

    .title-section {
      .page-title {
        display: flex;
        align-items: center;
        gap: 10px;
        font-size: 22px;
        font-weight: 600;
        color: var(--el-text-color-primary);
        margin: 0 0 8px 0;

        .title-icon {
          color: var(--el-color-primary);
        }
      }

      .page-description {
        font-size: 13px;
        color: var(--el-text-color-secondary);
        margin: 0;
      }
    }
  }

  .analysis-container {
    .stock-list-card,
    .config-card,
    .advanced-config-card {
      border-radius: 12px;
      border: 1px solid var(--el-border-color-lighter);
      transition: box-shadow 0.3s ease;

      &:hover {
        box-shadow: var(--el-box-shadow-light);
      }

      :deep(.el-card__header) {
        background: var(--el-fill-color-light);
        color: var(--el-text-color-primary);
        border-bottom: 1px solid var(--el-border-color-lighter);
        padding: 16px 20px;

        .card-header {
          display: flex;
          justify-content: space-between;
          align-items: center;

          h3 {
            margin: 0;
            font-size: 16px;
            font-weight: 600;
            color: var(--el-text-color-primary);
          }
        }
      }

      :deep(.el-card__body) {
        padding: 20px;
      }
    }

    .advanced-config-card {
      .config-content {
        .config-section {
          margin-bottom: 20px;

          &:last-child {
            margin-bottom: 0;
          }

          .config-title {
            font-size: 14px;
            font-weight: 600;
            color: var(--el-text-color-primary);
            margin: 0 0 12px 0;
            padding-bottom: 8px;
            border-bottom: 1px solid var(--el-border-color-lighter);
          }

          .analysis-options {
            .option-item {
              display: flex;
              align-items: center;
              justify-content: space-between;
              padding: 10px 0;
              border-bottom: 1px solid var(--el-border-color-lighter);

              &:last-child {
                border-bottom: none;
                padding-bottom: 0;
              }

              .option-info {
                .option-name {
                  font-size: 14px;
                  font-weight: 500;
                  color: var(--el-text-color-primary);
                  display: block;
                  margin-bottom: 2px;
                }

                .option-desc {
                  font-size: 12px;
                  color: var(--el-text-color-secondary);
                }
              }
            }
          }
        }
      }
    }

    .stock-input-section {
      .input-area {
        margin-bottom: 20px;

        .stock-textarea {
          :deep(.el-textarea__inner) {
            border-radius: 8px;
            border: 1px solid var(--el-border-color);
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            font-size: 14px;
            line-height: 1.6;

            &:focus {
              border-color: var(--el-color-primary);
              box-shadow: 0 0 0 2px var(--el-color-primary-light-8);
            }
          }
        }

        .input-actions {
          margin-top: 12px;
          display: flex;
          gap: 10px;
        }
      }

      .stock-preview {
        h4 {
          font-size: 14px;
          font-weight: 600;
          color: var(--el-text-color-primary);
          margin: 0 0 12px 0;
        }

        .stock-tags {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;

          .stock-tag {
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            font-weight: 500;
          }
        }
      }

      .invalid-codes {
        margin-top: 16px;

        .invalid-list {
          margin-top: 8px;
          display: flex;
          flex-wrap: wrap;
          gap: 6px;
        }
      }
    }

    .batch-form {
      .form-section {
        margin-bottom: 24px;

        .section-title {
          font-size: 14px;
          font-weight: 600;
          color: var(--el-text-color-primary);
          margin: 0 0 16px 0;
          padding-bottom: 8px;
          border-bottom: 1px solid var(--el-border-color-lighter);
        }
      }

      .depth-selector {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 12px;

        .depth-option {
          display: flex;
          align-items: center;
          padding: 16px;
          border: 1px solid var(--el-border-color-lighter);
          border-radius: 12px;
          cursor: pointer;
          transition: all 0.3s ease;
          background: var(--el-bg-color);

          &:hover {
            border-color: var(--el-color-primary);
            transform: translateY(-2px);
            box-shadow: var(--el-box-shadow-light);
          }

          &.active {
            border-color: var(--el-color-primary);
            background: var(--el-color-primary-light-9);
            color: var(--el-color-primary);
            transform: translateY(-2px);
            box-shadow: var(--el-box-shadow-light);
          }

          .depth-icon {
            font-size: 24px;
            margin-right: 12px;
          }

          .depth-info {
            .depth-name {
              font-weight: 600;
              margin-bottom: 4px;
            }

            .depth-desc {
              font-size: 12px;
              opacity: 0.8;
              margin-bottom: 2px;
            }

            .depth-time {
              font-size: 11px;
              opacity: 0.7;
            }
          }
        }
      }

      .analysts-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
        gap: 16px;

        .analyst-card {
          display: flex;
          align-items: center;
          padding: 16px;
          border: 1px solid var(--el-border-color-lighter);
          border-radius: 12px;
          cursor: pointer;
          transition: all 0.3s ease;
          background: var(--el-bg-color);

          &:hover {
            border-color: var(--el-color-primary);
            transform: translateY(-2px);
            box-shadow: var(--el-box-shadow-light);
          }

          &.active {
            border-color: var(--el-color-primary);
            background: var(--el-color-primary-light-9);
            color: var(--el-color-primary);
            transform: translateY(-2px);
            box-shadow: var(--el-box-shadow-light);
          }

          .analyst-avatar {
            width: 40px;
            height: 40px;
            border-radius: 10px;
            background: var(--el-fill-color-light);
            display: flex;
            align-items: center;
            justify-content: center;
            margin-right: 14px;
            flex-shrink: 0;
            font-size: 20px;

            .el-icon {
              color: var(--el-color-primary);
            }
          }

          &.active .analyst-avatar {
            background: var(--el-color-primary);
            .el-icon {
              color: #fff;
            }
          }

          .analyst-content {
            flex: 1;

            .analyst-name {
              font-weight: 600;
              margin-bottom: 4px;
              color: var(--el-text-color-primary);
            }

            .analyst-desc {
              font-size: 12px;
              color: var(--el-text-color-secondary);
            }
          }

          .analyst-check {
            margin-left: 12px;
            flex-shrink: 0;

            .check-icon {
              font-size: 18px;
              color: var(--el-color-primary);
            }
          }

          &.disabled {
            opacity: 0.5;
            cursor: not-allowed;

            &:hover {
              transform: none;
              box-shadow: none;
            }
          }
        }
      }
    }

    .action-section {
      margin-top: 24px;
      display: flex;
      justify-content: center;
      align-items: center;
      width: 100%;
      text-align: center;

      .submit-btn.el-button {
        width: 320px;
        height: 56px;
        font-size: 18px;
        font-weight: 600 !important;
        background: var(--el-color-primary);
        border: none;
        border-radius: 12px !important;
        transition: all 0.3s ease;
        box-shadow: 0 4px 12px color-mix(in srgb, var(--el-color-primary) 20%, transparent);
        min-width: 320px;
        max-width: 320px;

        &:hover {
          transform: translateY(-2px);
          box-shadow: 0 8px 24px color-mix(in srgb, var(--el-color-primary) 30%, transparent);
          background: var(--el-color-primary-light-3);
        }

        &:disabled {
          opacity: 0.6;
          transform: none;
          box-shadow: none;
        }

        .el-icon {
          margin-right: 8px;
          font-size: 20px;
        }

        span {
          font-size: 18px;
          font-weight: 600;
        }
      }
    }
  }

  .stock-preview-card {
    border-radius: 12px;
    border: 1px solid var(--el-border-color-lighter);
    margin-top: 24px;
    transition: box-shadow 0.3s ease;

    &:hover {
      box-shadow: var(--el-box-shadow-light);
    }

    :deep(.el-card__header) {
      background: var(--el-fill-color-light);
      color: var(--el-text-color-primary);
      border-bottom: 1px solid var(--el-border-color-lighter);
      padding: 16px 20px;

      .card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;

        h3 {
          margin: 0;
          font-size: 16px;
          font-weight: 600;
          color: var(--el-text-color-primary);
        }
      }
    }

    :deep(.el-card__body) {
      padding: 20px;
    }

    .stock-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
      gap: 12px;
      margin-bottom: 16px;

      .stock-item {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 8px 12px;
        background: var(--el-fill-color-light);
        border: 1px solid var(--el-border-color-lighter);
        border-radius: 8px;
        transition: all 0.2s ease;

        &.invalid {
          border-color: var(--el-color-danger-light-5);
          background: var(--el-color-danger-light-9);
        }

        .stock-code {
          font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
          font-size: 14px;
          color: var(--el-text-color-primary);
        }

        .remove-btn {
          padding: 2px;
          color: var(--el-text-color-secondary);

          &:hover {
            color: var(--el-color-danger);
          }
        }
      }
    }

    .invalid-notice {
      margin-top: 16px;
    }
  }
}
</style>

<style>
/* 全局样式确保按钮样式生效 */
.action-section {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 100%;
  text-align: center;
}

.large-batch-btn.el-button {
  width: 320px;
  height: 56px;
  font-size: 18px;
  font-weight: 600 !important;
  background: var(--el-color-primary);
  border: none;
  border-radius: 12px !important;
  transition: all 0.3s ease;
  box-shadow: 0 4px 12px color-mix(in srgb, var(--el-color-primary) 20%, transparent);
  min-width: 320px;
  max-width: 320px;
}

.large-batch-btn.el-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px color-mix(in srgb, var(--el-color-primary) 30%, transparent);
  background: var(--el-color-primary-light-3);
}

.large-batch-btn.el-button:disabled {
  opacity: 0.6;
  transform: none;
  box-shadow: none;
}

.large-batch-btn.el-button .el-icon {
  margin-right: 8px;
  font-size: 20px;
}

.large-batch-btn.el-button span {
  font-size: 18px;
  font-weight: 600;
}
</style>
