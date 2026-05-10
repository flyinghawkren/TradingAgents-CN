<template>
  <div class="portfolio-analysis">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-content">
        <div class="title-section">
          <h1 class="page-title">
            <el-icon class="title-icon"><Grid /></el-icon>
            组合分析
          </h1>
          <p class="page-description">
            AI驱动的股票持仓组合分析，高效分析持仓组合给出调仓建议
          </p>
        </div>
      </div>
    </div>

    <!-- 组合配置区域 -->
    <div class="analysis-container">
      <el-row :gutter="24">
        <el-col :span="24">
          <el-card class="stock-list-card" shadow="hover">
            <template #header>
              <div class="card-header">
                <h3>📋 组合配置</h3>
                <el-tag :type="portfolioStocks.length > 0 ? 'success' : 'info'" size="small">
                  {{ portfolioStocks.length }} 只持仓
                </el-tag>
              </div>
            </template>

            <!-- 持仓列表表格 -->
            <el-table
              :data="portfolioStocks"
              v-loading="loading"
              style="width: 100%"
              class="portfolio-table"
              :max-height="240"
            >
              <el-table-column prop="stock_code" label="股票代码" width="120">
                <template #default="{ row, $index }">
                  <el-input
                    v-model="row.stock_code"
                    size="small"
                    placeholder="代码"
                    @blur="fetchStockName(row)"
                  />
                </template>
              </el-table-column>

              <el-table-column prop="stock_name" label="股票名称" width="150">
                <template #default="{ row }">
                  <el-input v-model="row.stock_name" size="small" placeholder="名称" />
                </template>
              </el-table-column>

              <el-table-column prop="quantity" label="持有数量" width="130">
                <template #default="{ row }">
                  <el-input-number
                    v-model="row.quantity"
                    :min="1"
                    :precision="0"
                    size="small"
                    controls-position="right"
                    style="width: 100px;"
                  />
                </template>
              </el-table-column>

              <el-table-column prop="avg_price" label="买进均价" width="130">
                <template #default="{ row }">
                  <el-input-number
                    v-model="row.avg_price"
                    :min="0"
                    :precision="3"
                    size="small"
                    controls-position="right"
                    style="width: 100px;"
                  />
                </template>
              </el-table-column>

              <el-table-column prop="weight" label="权重(%)" width="100">
                <template #default="{ row }">
                  <span :class="getWeightClass(row.weight)">
                    {{ formatWeight(row.weight) }}
                  </span>
                </template>
              </el-table-column>

              <el-table-column prop="market" label="市场" width="100">
                <template #default="{ row }">
                  <el-select v-model="row.market" size="small" style="width: 80px;">
                    <el-option label="A股" value="A股" />
                    <el-option label="港股" value="港股" />
                    <el-option label="美股" value="美股" />
                  </el-select>
                </template>
              </el-table-column>

              <el-table-column label="操作" width="80" fixed="right">
                <template #default="{ $index }">
                  <el-button
                    type="text"
                    size="small"
                    @click="removeStock($index)"
                    style="color: #f56c6c;"
                  >
                    <el-icon><Delete /></el-icon>
                  </el-button>
                </template>
              </el-table-column>
            </el-table>

            <!-- 添加股票按钮 -->
            <div class="add-stock-row" style="margin-top: 8px;">
              <el-button type="primary" plain @click="addStockRow">
                <el-icon><Plus /></el-icon>
                添加股票
              </el-button>
            </div>

            <!-- 组合统计 -->
            <div v-if="portfolioStocks.length > 0" class="portfolio-stats" style="margin-top: 12px; padding-top: 12px; border-top: 1px solid #e2e8f0;">
              <el-row :gutter="24">
                <el-col :span="6">
                  <div class="stat-item">
                    <div class="stat-label">持仓股票数</div>
                    <div class="stat-value">{{ portfolioStocks.length }} 只</div>
                  </div>
                </el-col>
                <el-col :span="6">
                  <div class="stat-item">
                    <div class="stat-label">总持仓市值</div>
                    <div class="stat-value">¥{{ formatMoney(totalMarketValue) }}</div>
                  </div>
                </el-col>
                <el-col :span="6">
                  <div class="stat-item">
                    <div class="stat-label">平均持仓成本</div>
                    <div class="stat-value">¥{{ formatMoney(avgCost) }}</div>
                  </div>
                </el-col>
                <el-col :span="6">
                  <div class="stat-item">
                    <div class="stat-label">最大持仓</div>
                    <div class="stat-value">{{ maxWeightStock }}</div>
                  </div>
                </el-col>
              </el-row>
            </div>

            <!-- 空状态 -->
            <div v-if="!loading && portfolioStocks.length === 0" class="empty-state">
              <el-empty description="暂无组合股票">
                <el-button type="primary" @click="importFromPortfolio" :loading="importing">
                  <el-icon><Download /></el-icon>
                  从投资组合导入
                </el-button>
              </el-empty>
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
                <el-tag type="primary" size="small">组合设置</el-tag>
              </div>
            </template>

            <el-form :model="analysisForm" label-width="100px" class="batch-form">
              <!-- 基础信息 -->
              <div class="form-section">
                <h4 class="section-title">📋 基础信息</h4>
                <el-form-item label="组合名称" required>
                  <el-input
                    v-model="analysisForm.title"
                    placeholder="如：我的A股核心持仓组合"
                    size="large"
                  />
                </el-form-item>

                <el-form-item label="组合描述">
                  <el-input
                    v-model="analysisForm.description"
                    type="textarea"
                    :rows="2"
                    placeholder="描述本次组合分析的目的和关注点（可选）"
                  />
                </el-form-item>
              </div>

              <!-- 分析参数 -->
              <div class="form-section">
                <h4 class="section-title">⚙️ 分析参数</h4>
                <el-form-item label="分析深度">
                  <el-select v-model="analysisForm.depth" placeholder="选择深度" size="large" style="width: 100%">
                    <el-option label="⚡ 1级 - 快速分析 (2-4分钟)" value="1" />
                    <el-option label="📈 2级 - 基础分析 (4-6分钟)" value="2" />
                    <el-option label="🎯 3级 - 标准分析 (6-10分钟，推荐)" value="3" />
                    <el-option label="🔍 4级 - 深度分析 (10-15分钟)" value="4" />
                    <el-option label="🏆 5级 - 全面分析 (15-25分钟)" value="5" />
                  </el-select>
                </el-form-item>
              </div>

              <!-- 分析师选择 -->
              <div class="form-section">
                <h4 class="section-title">👥 分析师团队</h4>
                <div class="analysts-selection">
                  <el-checkbox-group v-model="analysisForm.analysts" class="analysts-group">
                    <div
                      v-for="analyst in ANALYSTS"
                      :key="analyst.id"
                      class="analyst-option"
                    >
                      <el-checkbox :label="analyst.name" class="analyst-checkbox">
                        <div class="analyst-info">
                          <span class="analyst-name">{{ analyst.name }}</span>
                          <span class="analyst-desc">{{ analyst.description }}</span>
                        </div>
                      </el-checkbox>
                    </div>
                  </el-checkbox-group>
                </div>
              </div>

              <!-- 操作按钮 -->
              <div class="form-section">
                <div class="action-buttons" style="display: flex; justify-content: center; align-items: center; width: 100%; text-align: center;">
                  <el-button
                    type="primary"
                    size="large"
                    @click="submitPortfolioAnalysis"
                    :loading="submitting"
                    :disabled="portfolioStocks.length === 0"
                    class="submit-btn large-batch-btn"
                    style="width: 320px; height: 56px; font-size: 18px; font-weight: 700; border-radius: 16px;"
                  >
                    <el-icon><TrendCharts /></el-icon>
                    开始组合分析 ({{ portfolioStocks.length }}只)
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
                :analysis-depth="analysisForm.depth"
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
                    <el-switch v-model="analysisForm.includeSentiment" />
                  </div>

                  <div class="option-item">
                    <div class="option-info">
                      <span class="option-name">风险评估</span>
                      <span class="option-desc">包含详细的风险因素分析</span>
                    </div>
                    <el-switch v-model="analysisForm.includeRisk" />
                  </div>

                  <div class="option-item">
                    <div class="option-info">
                      <span class="option-name">调仓建议</span>
                      <span class="option-desc">基于分析给出持仓调整建议</span>
                    </div>
                    <el-switch v-model="analysisForm.includeRebalance" />
                  </div>

                  <div class="option-item">
                    <div class="option-info">
                      <span class="option-name">语言偏好</span>
                    </div>
                    <el-select v-model="analysisForm.language" size="small" style="width: 100px">
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

      <!-- 分析进度显示 -->
      <div v-if="analysisStatus === 'running'" class="progress-section" style="margin-top: 24px;">
        <el-card class="progress-card" shadow="hover">
          <template #header>
            <div class="progress-header">
              <h4>
                <el-icon class="rotating-icon"><Loading /></el-icon>
                组合分析进行中...
              </h4>
              <el-tag type="warning">{{ progressInfo.currentStep }}</el-tag>
            </div>
          </template>

          <div class="progress-content">
            <div class="overall-progress-info">
              <div class="progress-stats">
                <div class="stat-item">
                  <div class="stat-label">已用时间</div>
                  <div class="stat-value">{{ formatDuration(progressInfo.elapsedTime) }}</div>
                </div>
                <div class="stat-item">
                  <div class="stat-label">预计剩余</div>
                  <div class="stat-value">{{ formatDuration(progressInfo.remainingTime) }}</div>
                </div>
                <div class="stat-item">
                  <div class="stat-label">预计总时长</div>
                  <div class="stat-value">{{ formatDuration(progressInfo.totalTime) }}</div>
                </div>
              </div>
            </div>

            <div class="progress-bar-section">
              <el-progress
                :percentage="Math.round(progressInfo.progress)"
                :stroke-width="12"
                :show-text="true"
                status="success"
                class="main-progress-bar"
              />
            </div>

            <div class="current-task-info">
              <div class="task-title">
                <el-icon class="task-icon"><Loading /></el-icon>
                {{ progressInfo.currentStep || '正在初始化分析引擎...' }}
              </div>
              <div class="task-description" style="white-space: pre-wrap; line-height: 1.6;">
                {{ progressInfo.message || 'AI正在分析您的持仓组合...' }}
              </div>
            </div>
          </div>
        </el-card>
      </div>

      <!-- 分析结果显示 -->
      <div v-if="showResults && analysisResults" class="results-section" style="margin-top: 24px;">
        <el-row :gutter="24">
          <el-col :span="24">
            <el-card class="results-card" shadow="hover">
              <template #header>
                <div class="results-header">
                  <h3>📊 组合分析报告</h3>
                  <div class="result-meta">
                    <el-tag type="success">{{ analysisForm.title }}</el-tag>
                    <el-tag>{{ analysisResults.analysis_date || new Date().toISOString().slice(0, 10) }}</el-tag>
                  </div>
                </div>
              </template>

              <div class="results-content">
                <!-- 风险提示 -->
                <div class="risk-disclaimer">
                  <el-alert type="warning" :closable="false" show-icon>
                    <template #title>
                      <span style="font-weight: bold;">⚠️ 报告依据真实交易数据使用AI分析生成，仅供参考，不构成任何投资建议。市场有风险，投资需谨慎。</span>
                    </template>
                  </el-alert>
                </div>

                <!-- 调仓分析结论 -->
                <div v-if="analysisResults.comprehensive_report?.report_text" class="decision-section">
                  <h4>🎯 调仓分析结论</h4>
                  <div class="decision-card">
                    <div class="comprehensive-report" v-html="renderMarkdown(analysisResults.comprehensive_report.report_text)"></div>
                  </div>
                </div>

                <!-- 各成分股票分析结论 -->
                <div v-if="analysisResults.stock_results" class="overview-section">
                  <h4>📋 成分股票分析摘要</h4>
                  <div class="stock-results-list">
                    <el-collapse>
                      <el-collapse-item
                        v-for="(stockResult, symbol) in analysisResults.stock_results"
                        :key="symbol"
                        :title="`${symbol} - ${stockResult.stock_name}`"
                      >
                        <div class="stock-result-item">
                          <div v-if="stockResult.summary" class="stock-summary">
                            <h5>分析摘要</h5>
                            <p>{{ stockResult.summary }}</p>
                          </div>
                          <div v-if="stockResult.recommendation" class="stock-recommendation">
                            <h5>投资建议</h5>
                            <p>{{ stockResult.recommendation }}</p>
                          </div>
                          <div v-if="stockResult.decision?.action" class="stock-decision">
                            <h5>AI倾向</h5>
                            <el-tag :type="getActionTagType(stockResult.decision.action)">
                              {{ stockResult.decision.action }}
                            </el-tag>
                            <span v-if="stockResult.decision.confidence" style="margin-left: 8px; color: #666;">
                              置信度: {{ (stockResult.decision.confidence * 100).toFixed(1) }}%
                            </span>
                          </div>
                        </div>
                      </el-collapse-item>
                    </el-collapse>
                  </div>
                </div>

                <!-- 组合持仓概览 -->
                <div v-if="analysisResults.stocks" class="overview-section">
                  <h4>📊 组合持仓概览</h4>
                  <div class="overview-card">
                    <el-table :data="analysisResults.stocks" style="width: 100%">
                      <el-table-column prop="stock_code" label="股票代码" width="120" />
                      <el-table-column prop="stock_name" label="股票名称" width="150" />
                      <el-table-column prop="quantity" label="持有数量" width="120" />
                      <el-table-column prop="avg_price" label="买进均价" width="120">
                        <template #default="{ row }">
                          ¥{{ row.avg_price?.toFixed(2) }}
                        </template>
                      </el-table-column>
                      <el-table-column prop="market" label="市场" width="100" />
                    </el-table>
                  </div>
                </div>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Grid, TrendCharts, Download, Delete, Plus, Loading, Check, Document } from '@element-plus/icons-vue'
import { ANALYSTS, DEFAULT_ANALYSTS, convertAnalystNamesToIds } from '@/constants/analysts'
import { configApi } from '@/api/config'
import { portfolioApi } from '@/api/portfolio'
import { analysisApi } from '@/api/analysis'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import ModelConfig from '@/components/ModelConfig.vue'
import { marked } from 'marked'

marked.setOptions({ breaks: true, gfm: true })

const router = useRouter()

const submitting = ref(false)
const loading = ref(false)
const importing = ref(false)

// 分析进度和结果状态
const currentTaskId = ref('')
const analysisStatus = ref<'idle' | 'running' | 'completed' | 'failed'>('idle')
const showResults = ref(false)
const analysisResults = ref<any>(null)
const progressInfo = ref({
  progress: 0,
  currentStep: '',
  message: '',
  elapsedTime: 0,
  remainingTime: 0,
  totalTime: 0
})
const pollingTimer = ref<any>(null)

// 组合股票列表
const portfolioStocks = ref<any[]>([])

// 模型设置
const modelSettings = ref({
  quickAnalysisModel: '',
  deepAnalysisModel: ''
})

// 可用的模型列表
const availableModels = ref<any[]>([])

const analysisForm = reactive({
  title: '',
  description: '',
  depth: '3',
  analysts: [...DEFAULT_ANALYSTS],
  includeSentiment: true,
  includeRisk: true,
  includeRebalance: true,
  language: 'zh-CN'
})

// 组合统计计算
const totalMarketValue = computed(() => {
  return portfolioStocks.value.reduce((sum, s) => {
    return sum + (s.quantity || 0) * (s.avg_price || 0)
  }, 0)
})

const avgCost = computed(() => {
  const totalQty = portfolioStocks.value.reduce((sum, s) => sum + (s.quantity || 0), 0)
  if (totalQty === 0) return 0
  return totalMarketValue.value / totalQty
})

const maxWeightStock = computed(() => {
  if (portfolioStocks.value.length === 0) return '-'
  const maxStock = portfolioStocks.value.reduce((max, s) =>
    (s.quantity * s.avg_price) > (max.quantity * max.avg_price) ? s : max
  )
  return `${maxStock.stock_name} (${formatWeight(maxStock.weight)})`
})

// 监听持仓变化，自动计算权重
watch(() => portfolioStocks.value, (newVal) => {
  const total = totalMarketValue.value
  newVal.forEach(s => {
    const value = (s.quantity || 0) * (s.avg_price || 0)
    s.weight = total > 0 ? (value / total) * 100 : 0
  })
}, { deep: true })

import { watch } from 'vue'

// 从投资组合导入
const importFromPortfolio = async () => {
  importing.value = true
  try {
    const res = await portfolioApi.list()
    if (res.success && res.data && res.data.length > 0) {
      portfolioStocks.value = res.data.map((h: any) => ({
        stock_code: h.stock_code,
        stock_name: h.stock_name,
        quantity: h.quantity,
        avg_price: h.avg_price,
        market: h.market || 'A股',
        weight: 0
      }))
      ElMessage.success(`成功导入 ${res.data.length} 只持仓股票`)
    } else {
      ElMessage.warning('投资组合中暂无持仓股票')
    }
  } catch (error) {
    console.error('导入投资组合失败:', error)
    ElMessage.error('导入投资组合失败')
  } finally {
    importing.value = false
  }
}

// 添加一行股票
const addStockRow = () => {
  portfolioStocks.value.push({
    stock_code: '',
    stock_name: '',
    quantity: 100,
    avg_price: 0,
    market: 'A股',
    weight: 0
  })
}

// 删除一行
const removeStock = (index: number) => {
  portfolioStocks.value.splice(index, 1)
}

// 根据代码自动获取名称（简单mock，后续可接真实API）
const fetchStockName = (row: any) => {
  if (row.stock_code && !row.stock_name) {
    const code = row.stock_code
    // 这里可以接入股票基础信息API
    // 暂时简单的mock映射
    const mockNames: Record<string, string> = {
      '000001': '平安银行',
      '600519': '贵州茅台',
      '000858': '五粮液',
      '002594': '比亚迪',
      '300750': '宁德时代',
      '600036': '招商银行',
      '601318': '中国平安',
      '600276': '恒瑞医药'
    }
    if (mockNames[code]) {
      row.stock_name = mockNames[code]
    }
  }
}

// 格式化
const formatWeight = (weight: number) => {
  if (weight === undefined || weight === null) return '-'
  return weight.toFixed(2) + '%'
}

const getWeightClass = (weight: number) => {
  if (weight > 30) return 'weight-high'
  if (weight > 15) return 'weight-medium'
  return 'weight-low'
}

const formatMoney = (value: number) => {
  if (!value) return '0.00'
  return value.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',')
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

    const llmConfigs = await configApi.getLLMConfigs()
    availableModels.value = sortModelsByNewest(
      llmConfigs.filter((config: any) => config.enabled)
    )

    const defaultModels = await configApi.getDefaultModels()
    let quickModel = defaultModels.quick_analysis_model
    let deepModel = defaultModels.deep_analysis_model

    const availableModelNames = new Set(availableModels.value.map(m => m.model_name))
    if (!quickModel || !availableModelNames.has(quickModel)) {
      quickModel = availableModels.value[0]?.model_name || ''
    }
    if (!deepModel || !availableModelNames.has(deepModel)) {
      deepModel = availableModels.value[0]?.model_name || ''
    }

    modelSettings.value.quickAnalysisModel = quickModel
    modelSettings.value.deepAnalysisModel = deepModel
  } catch (error) {
    console.error('加载模型配置失败:', error)
  }
}

// 格式化时间
const formatDuration = (seconds: number) => {
  if (!seconds || seconds < 0) return '-'
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  if (m > 0) return `${m}分${s}秒`
  return `${s}秒`
}

// 轮询任务状态
const startPolling = (taskId: string) => {
  stopPolling()
  currentTaskId.value = taskId
  analysisStatus.value = 'running'
  showResults.value = false

  const poll = async () => {
    try {
      const res = await analysisApi.getTaskStatus(taskId)
      const data = res?.data?.data || res?.data
      if (!data) return

      const status = data.status || 'pending'
      const progress = data.progress || 0

      progressInfo.value = {
        progress,
        currentStep: data.current_step || data.message || '分析中...',
        message: data.message || '',
        elapsedTime: data.elapsed_time || 0,
        remainingTime: data.remaining_time || 0,
        totalTime: data.estimated_total_time || 0
      }

      if (status === 'completed') {
        analysisStatus.value = 'completed'
        stopPolling()
        // 获取结果
        try {
          const resultRes = await analysisApi.getTaskResult(taskId)
          const resultData = resultRes?.data?.data || resultRes?.data
          if (resultData) {
            analysisResults.value = resultData
            showResults.value = true
            ElMessage.success('组合分析完成')
          }
        } catch (e) {
          console.error('获取结果失败:', e)
        }
      } else if (status === 'failed') {
        analysisStatus.value = 'failed'
        stopPolling()
        ElMessage.error(data.error_message || '组合分析失败')
      }
    } catch (e) {
      console.error('轮询状态失败:', e)
    }
  }

  poll()
  pollingTimer.value = setInterval(poll, 5000)
}

const stopPolling = () => {
  if (pollingTimer.value) {
    clearInterval(pollingTimer.value)
    pollingTimer.value = null
  }
}

// Markdown 渲染
const renderMarkdown = (content: string) => {
  if (!content) return ''
  try {
    return marked.parse(content) as string
  } catch {
    return content
  }
}

// 提交组合分析
const submitPortfolioAnalysis = async () => {
  if (!analysisForm.title) {
    ElMessage.warning('请输入组合名称')
    return
  }

  if (portfolioStocks.value.length === 0) {
    ElMessage.warning('请至少添加一只股票到组合中')
    return
  }

  // 检查是否有空代码或名称
  const invalid = portfolioStocks.value.filter(s => !s.stock_code || !s.stock_name)
  if (invalid.length > 0) {
    ElMessage.warning('请完善股票代码和名称')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确定要提交组合分析任务吗？\n组合：${analysisForm.title}\n股票数量：${portfolioStocks.value.length}只`,
      '确认提交',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'info'
      }
    )

    submitting.value = true
    analysisStatus.value = 'running'
    showResults.value = false

    // 准备组合分析请求参数
    const portfolioRequest = {
      title: analysisForm.title,
      description: analysisForm.description,
      stocks: portfolioStocks.value.map(s => ({
        stock_code: s.stock_code,
        stock_name: s.stock_name,
        quantity: s.quantity,
        avg_price: s.avg_price,
        market: s.market,
        weight: s.weight
      })),
      parameters: {
        research_depth: analysisForm.depth,
        selected_analysts: convertAnalystNamesToIds(analysisForm.analysts),
        include_sentiment: analysisForm.includeSentiment,
        include_risk: analysisForm.includeRisk,
        include_rebalance: analysisForm.includeRebalance,
        language: analysisForm.language,
        quick_analysis_model: modelSettings.value.quickAnalysisModel,
        deep_analysis_model: modelSettings.value.deepAnalysisModel
      }
    }

    // 调用真实的组合分析API
    const response = await analysisApi.startPortfolioAnalysis(portfolioRequest)

    if (!response?.success) {
      throw new Error(response?.message || '组合分析提交失败')
    }

    const { task_id, total_stocks } = response.data
    currentTaskId.value = task_id

    ElMessage.success(`组合分析任务已提交，共${total_stocks}只股票，正在后台执行`)

    // 开始轮询任务状态
    startPolling(task_id)
    submitting.value = false

  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '组合分析提交失败')
    }
    analysisStatus.value = 'idle'
    submitting.value = false
  }
}

// 页面卸载时停止轮询
onUnmounted(() => {
  stopPolling()
})

// AI倾向标签类型
const getActionTagType = (action: string): 'success' | 'danger' | 'warning' | 'info' => {
  if (!action) return 'info'
  const a = action.toLowerCase()
  if (a.includes('买入') || a.includes('增持') || a.includes('看多')) return 'success'
  if (a.includes('卖出') || a.includes('减持') || a.includes('看空')) return 'danger'
  if (a.includes('持有') || a.includes('观望') || a.includes('中性')) return 'warning'
  return 'info'
}

// 页面初始化
onMounted(async () => {
  await initializeModelSettings()

  // 从用户偏好加载默认设置
  const authStore = useAuthStore()
  const userPrefs = authStore.user?.preferences

  if (userPrefs) {
    if (userPrefs.default_depth) {
      analysisForm.depth = userPrefs.default_depth
    }
    if (userPrefs.default_analysts && userPrefs.default_analysts.length > 0) {
      analysisForm.analysts = [...userPrefs.default_analysts]
    }
  }
})
</script>

<style lang="scss" scoped>
.portfolio-analysis {
  min-height: 100vh;
  background: var(--el-bg-color-page);
  padding: 24px;

  .page-header {
    margin-bottom: 32px;

    .header-content {
      background: var(--el-bg-color);
      padding: 32px;
      border-radius: 16px;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
    }

    .title-section {
      .page-title {
        display: flex;
        align-items: center;
        font-size: 32px;
        font-weight: 700;
        color: #1a202c;
        margin: 0 0 8px 0;

        .title-icon {
          margin-right: 12px;
          color: #10b981;
        }
      }

      .page-description {
        font-size: 16px;
        color: #64748b;
        margin: 0;
      }
    }
  }

  .analysis-container {
    .stock-list-card, .config-card {
      border-radius: 16px;
      border: none;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);

      :deep(.el-card__header) {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: white;
        border-radius: 16px 16px 0 0;
        padding: 20px 24px;

        .card-header {
          display: flex;
          justify-content: space-between;
          align-items: center;

          h3 {
            margin: 0;
            font-size: 18px;
            font-weight: 600;
          }

          .header-actions {
            display: flex;
            align-items: center;
          }
        }
      }

      :deep(.el-card__body) {
        padding: 24px;
      }
    }

    .stock-list-card {
      :deep(.el-card__body) {
        padding: 16px 24px;
      }
    }

    .portfolio-table {
      :deep(.el-input__inner) {
        font-size: 13px;
      }
    }

    .portfolio-stats {
      .stat-item {
        text-align: center;
        padding: 8px;
        background: var(--el-fill-color-light);
        border-radius: 8px;

        .stat-label {
          font-size: 12px;
          color: var(--el-text-color-secondary);
          margin-bottom: 4px;
        }

        .stat-value {
          font-size: 18px;
          font-weight: 600;
          color: var(--el-text-color-primary);
        }
      }
    }

    // 右侧高级配置卡片样式
    .advanced-config-card {
      border-radius: 16px;
      border: none;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);

      :deep(.el-card__header) {
        background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
        color: white;
        border-radius: 16px 16px 0 0;
        padding: 20px 24px;

        .card-header {
          display: flex;
          justify-content: space-between;
          align-items: center;

          h3 {
            margin: 0;
            font-size: 18px;
            font-weight: 600;
          }
        }
      }

      :deep(.el-card__body) {
        padding: 24px;
      }

      .config-content {
        .config-section {
          margin-bottom: 24px;

          &:last-child {
            margin-bottom: 0;
          }

          .analysis-options {
            .option-item {
              display: flex;
              align-items: center;
              justify-content: space-between;
              padding: 12px 0;
              border-bottom: 1px solid #f3f4f6;

              &:last-child {
                border-bottom: none;
                padding-bottom: 0;
              }

              .option-info {
                .option-name {
                  font-size: 14px;
                  font-weight: 500;
                  color: #374151;
                  display: block;
                  margin-bottom: 2px;
                }

                .option-desc {
                  font-size: 12px;
                  color: #6b7280;
                }
              }
            }
          }
        }
      }
    }

    .batch-form {
      .form-section {
        margin-bottom: 32px;

        .section-title {
          font-size: 16px;
          font-weight: 600;
          color: #1a202c;
          margin: 0 0 16px 0;
          padding-bottom: 8px;
          border-bottom: 2px solid #e2e8f0;
        }
      }

      .analysts-selection {
        .analysts-group {
          display: flex;
          flex-direction: column;
          gap: 12px;

          .analyst-option {
            .analyst-checkbox {
              width: 100%;

              :deep(.el-checkbox__label) {
                width: 100%;
              }

              :deep(.el-checkbox__input.is-checked .el-checkbox__inner) {
                background-color: #10b981;
                border-color: #10b981;
              }

              :deep(.el-checkbox__input.is-checked + .el-checkbox__label) {
                color: #10b981;
              }

              .analyst-info {
                display: flex;
                flex-direction: column;
                gap: 4px;

                .analyst-name {
                  font-weight: 500;
                  color: #374151;
                }

                .analyst-desc {
                  font-size: 12px;
                  color: #6b7280;
                }
              }
            }
          }
        }
      }
    }

    .weight-high {
      color: #f56c6c;
      font-weight: 600;
    }

    .weight-medium {
      color: #e6a23c;
      font-weight: 500;
    }

    .weight-low {
      color: #67c23a;
    }
  }
}

.empty-state {
  padding: 24px 0;
}

// 进度卡片样式
.progress-section {
  .progress-card {
    border-radius: 16px;
    border: none;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);

    :deep(.el-card__header) {
      background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
      color: white;
      border-radius: 16px 16px 0 0;
      padding: 16px 24px;

      .progress-header {
        display: flex;
        justify-content: space-between;
        align-items: center;

        h4 {
          margin: 0;
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 16px;
        }
      }
    }

    :deep(.el-card__body) {
      padding: 24px;
    }

    .progress-content {
      .progress-stats {
        display: flex;
        justify-content: space-around;
        margin-bottom: 20px;

        .stat-item {
          text-align: center;

          .stat-label {
            font-size: 12px;
            color: #6b7280;
            margin-bottom: 4px;
          }

          .stat-value {
            font-size: 18px;
            font-weight: 600;
            color: #1a202c;
          }
        }
      }

      .progress-bar-section {
        margin-bottom: 20px;
      }

      .current-task-info {
        background: var(--el-fill-color-light);
        border-radius: 12px;
        padding: 16px;

        .task-title {
          display: flex;
          align-items: center;
          gap: 8px;
          font-weight: 600;
          color: #1a202c;
          margin-bottom: 8px;

          .task-icon {
            color: #3b82f6;
          }
        }

        .task-description {
          font-size: 14px;
          color: #4b5563;
        }
      }
    }
  }
}

// 结果卡片样式
.results-section {
  .results-card {
    border-radius: 16px;
    border: none;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);

    :deep(.el-card__header) {
      background: linear-gradient(135deg, #10b981 0%, #059669 100%);
      color: white;
      border-radius: 16px 16px 0 0;
      padding: 20px 24px;

      .results-header {
        display: flex;
        justify-content: space-between;
        align-items: center;

        h3 {
          margin: 0;
          font-size: 18px;
          font-weight: 600;
        }

        .result-meta {
          display: flex;
          gap: 8px;
        }
      }
    }

    :deep(.el-card__body) {
      padding: 24px;
    }

    .results-content {
      .risk-disclaimer {
        margin-bottom: 24px;
      }

      .decision-section,
      .overview-section {
        margin-bottom: 32px;

        h4 {
          font-size: 18px;
          font-weight: 600;
          color: #1a202c;
          margin: 0 0 16px 0;
          padding-bottom: 8px;
          border-bottom: 2px solid #e2e8f0;
        }
      }

      .decision-card {
        background: var(--el-fill-color-light);
        border-radius: 12px;
        padding: 20px;

        .comprehensive-report {
          line-height: 1.8;
          color: #374151;

          :deep(h3) {
            color: #1a202c;
            margin-top: 16px;
            margin-bottom: 8px;
          }

          :deep(p) {
            margin-bottom: 12px;
          }

          :deep(ul) {
            padding-left: 20px;
            margin-bottom: 12px;
          }

          :deep(li) {
            margin-bottom: 4px;
          }

          :deep(strong) {
            color: #1a202c;
          }
        }
      }

      .stock-results-list {
        .stock-result-item {
          padding: 12px;

          h5 {
            font-size: 14px;
            font-weight: 600;
            color: #374151;
            margin: 12px 0 8px 0;
          }

          p {
            font-size: 13px;
            color: #4b5563;
            line-height: 1.6;
            margin: 0;
          }

          .stock-decision {
            margin-top: 12px;
            display: flex;
            align-items: center;
          }
        }
      }

      .overview-card {
        background: var(--el-fill-color-light);
        border-radius: 12px;
        padding: 16px;
      }
    }
  }
}

// 旋转动画
.rotating-icon {
  animation: rotate 2s linear infinite;
}

@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>

<style>
/* 全局样式确保按钮样式生效 */
.action-section {
  display: flex !important;
  justify-content: center !important;
  align-items: center !important;
  width: 100% !important;
  text-align: center !important;
}

.large-batch-btn.el-button {
  width: 320px !important;
  height: 56px !important;
  font-size: 18px !important;
  font-weight: 700 !important;
  background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
  border: none !important;
  border-radius: 16px !important;
  transition: all 0.3s ease !important;
  box-shadow: 0 4px 15px rgba(16, 185, 129, 0.2) !important;
  min-width: 320px !important;
  max-width: 320px !important;
}

.large-batch-btn.el-button:hover {
  transform: translateY(-3px) !important;
  box-shadow: 0 12px 30px rgba(16, 185, 129, 0.4) !important;
  background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
}

.large-batch-btn.el-button:disabled {
  opacity: 0.6 !important;
  transform: none !important;
  box-shadow: 0 4px 15px rgba(16, 185, 129, 0.1) !important;
}

.large-batch-btn.el-button .el-icon {
  margin-right: 8px !important;
  font-size: 20px !important;
}

.large-batch-btn.el-button span {
  font-size: 18px !important;
  font-weight: 700 !important;
}
</style>
