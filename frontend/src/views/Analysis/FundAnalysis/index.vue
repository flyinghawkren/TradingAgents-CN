<template>
  <div class="fund-analysis">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-content">
        <div class="title-section">
          <h1 class="page-title">
            <el-icon class="title-icon"><Money /></el-icon>
            基金分析
          </h1>
          <p class="page-description">
            AI驱动的公募基金综合分析，提供净值走势、持仓结构、基金经理等多维度分析
          </p>
        </div>
      </div>
    </div>

    <!-- 未选择基金时的提示 -->
    <div v-if="!selectedFund" class="empty-state">
      <el-card class="empty-card" shadow="hover">
        <el-empty :image-size="160" description="">
          <template #description>
            <div class="empty-content">
              <h3>暂未选择基金</h3>
              <p>请先前往基金搜索页面，选择一只基金后再进行分析</p>
              <el-button type="primary" size="large" @click="goToSearch" class="search-btn">
                <el-icon><Search /></el-icon>
                前往基金搜索
              </el-button>
            </div>
          </template>
        </el-empty>
      </el-card>
    </div>

    <!-- 主要分析区域 -->
    <div v-else class="analysis-container">
      <!-- 已选基金信息条 -->
      <el-card class="fund-bar-card" shadow="hover">
        <div class="fund-bar">
          <div class="fund-info">
            <span class="fund-name">{{ selectedFund.name }}</span>
            <el-tag type="success" size="small">{{ selectedFund.ts_code }}</el-tag>
            <el-tag v-if="selectedFund.fund_type" size="small" type="info">{{ selectedFund.fund_type }}</el-tag>
          </div>
          <el-button type="primary" size="small" @click="goToSearch">
            <el-icon><Refresh /></el-icon>
            更换基金
          </el-button>
        </div>
      </el-card>

      <el-row :gutter="24" style="margin-top: 24px;">
        <!-- 左侧：分析配置 -->
        <el-col :span="18">
          <el-card class="main-form-card" shadow="hover">
            <template #header>
              <div class="card-header">
                <h3>分析配置</h3>
                <el-tag type="info" size="small">选填信息</el-tag>
              </div>
            </template>

            <el-form label-position="top" class="analysis-form">
              <!-- 分析时间范围 -->
              <div class="form-section">
                <h4 class="section-title">📅 分析时间范围</h4>
                <div class="time-range-selector">
                  <el-radio-group v-model="analysisConfig.timeRange" size="large">
                    <el-radio-button label="1m">近1月</el-radio-button>
                    <el-radio-button label="3m">近3月</el-radio-button>
                    <el-radio-button label="6m">近6月</el-radio-button>
                    <el-radio-button label="1y">近1年</el-radio-button>
                    <el-radio-button label="2y">近2年</el-radio-button>
                    <el-radio-button label="3y">近3年</el-radio-button>
                    <el-radio-button label="5y">近5年</el-radio-button>
                    <el-radio-button label="all">成立以来</el-radio-button>
                  </el-radio-group>
                </div>
              </div>

              <!-- 业绩对比基准 -->
              <div class="form-section">
                <h4 class="section-title">📊 业绩对比基准</h4>
                <el-select v-model="analysisConfig.benchmark" size="large" style="width: 280px">
                  <el-option label="业绩比较基准（默认）" value="default" />
                  <el-option label="沪深300指数" value="hs300" />
                  <el-option label="中证500指数" value="zz500" />
                  <el-option label="中证全债指数" value="bond" />
                  <el-option label="同类基金平均" value="peer_avg" />
                  <el-option label="货币基金平均" value="mmf_avg" />
                </el-select>
              </div>

              <!-- 分析深度 -->
              <div class="form-section">
                <h4 class="section-title">🎯 分析深度</h4>
                <div class="depth-selector">
                  <div
                    v-for="(depth, index) in depthOptions"
                    :key="index"
                    class="depth-option"
                    :class="{ active: analysisConfig.researchDepth === index + 1 }"
                    @click="analysisConfig.researchDepth = index + 1"
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
                    v-for="analyst in FUND_ANALYSTS"
                    :key="analyst.id"
                    class="analyst-card"
                    :class="{ active: analysisConfig.selectedAnalysts.includes(analyst.name) }"
                    @click="toggleAnalyst(analyst.name)"
                  >
                    <div class="analyst-avatar">
                      <el-icon size="20"><component :is="analyst.iconComponent" /></el-icon>
                    </div>
                    <div class="analyst-content">
                      <div class="analyst-name">{{ analyst.name }}</div>
                      <div class="analyst-desc">{{ analyst.description }}</div>
                    </div>
                    <div class="analyst-check">
                      <el-icon v-if="analysisConfig.selectedAnalysts.includes(analyst.name)" class="check-icon" size="20"><Check /></el-icon>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 操作按钮 -->
              <div class="form-section action-section">
                <div class="action-buttons">
                  <el-button
                    v-if="analysisStatus === 'idle'"
                    type="primary"
                    size="large"
                    @click="submitAnalysis"
                    :loading="analyzing"
                    class="submit-btn large-analysis-btn"
                  >
                    <el-icon><TrendCharts /></el-icon>
                    开始智能分析
                  </el-button>

                  <el-button
                    v-else-if="analysisStatus === 'running'"
                    type="warning"
                    size="large"
                    disabled
                    class="submit-btn large-analysis-btn"
                  >
                    <el-icon class="is-loading"><Loading /></el-icon>
                    分析进行中...
                  </el-button>

                  <div v-else-if="analysisStatus === 'completed'" class="result-btn-group">
                    <el-button
                      type="success"
                      size="large"
                      @click="showResults = !showResults"
                      class="submit-btn"
                    >
                      <el-icon><Document /></el-icon>
                      {{ showResults ? '隐藏结果' : '查看结果' }}
                    </el-button>

                    <el-button
                      type="primary"
                      size="large"
                      @click="restartAnalysis"
                      class="submit-btn"
                    >
                      <el-icon><Refresh /></el-icon>
                      重新分析
                    </el-button>
                  </div>

                  <el-button
                    v-else-if="analysisStatus === 'failed'"
                    type="danger"
                    size="large"
                    @click="restartAnalysis"
                    class="submit-btn large-analysis-btn"
                  >
                    <el-icon><Refresh /></el-icon>
                    重新分析
                  </el-button>
                </div>
              </div>

              <!-- 分析进度 -->
              <div v-if="analysisStatus === 'running'" class="progress-section">
                <el-card class="progress-card" shadow="hover">
                  <template #header>
                    <div class="progress-header">
                      <h4>
                        <el-icon class="is-loading"><Loading /></el-icon>
                        分析进行中...
                      </h4>
                      <el-tag type="warning" size="small">{{ taskProgress }}%</el-tag>
                    </div>
                  </template>
                  <div class="progress-content">
                    <el-progress
                      :percentage="taskProgress"
                      :stroke-width="12"
                      status="warning"
                      class="analysis-progress-bar"
                    />
                    <div class="current-task-info">
                      <div class="task-title">
                        <el-icon class="task-icon is-loading"><Loading /></el-icon>
                        {{ taskStep || 'AI正在分析基金数据...' }}
                      </div>
                      <div class="task-description">
                        已选择 {{ analysisConfig.selectedAnalysts.length }} 位分析师，正在多维度并行分析中，请稍候
                      </div>
                    </div>
                  </div>
                </el-card>
              </div>
            </el-form>
          </el-card>
        </el-col>

        <!-- 右侧：高级配置 -->
        <el-col :span="6">
          <el-card class="config-card" shadow="hover">
            <template #header>
              <div class="card-header">
                <h3>高级配置</h3>
                <el-tag type="warning" size="small">可选设置</el-tag>
              </div>
            </template>

            <div class="config-content">
              <!-- AI模型配置 -->
              <div class="config-section">
                <h4 class="config-title">🤖 AI模型配置</h4>
                <div class="model-config">
                  <div class="model-item">
                    <div class="model-label">
                      <span>快速分析模型</span>
                    </div>
                    <el-select v-model="modelSettings.quickAnalysisModel" size="default" style="width: 100%" filterable>
                      <el-option
                        v-for="model in availableModels"
                        :key="`quick-${model.provider}/${model.model_name}`"
                        :label="model.model_display_name || model.model_name"
                        :value="model.model_name"
                      />
                    </el-select>
                  </div>

                  <div class="model-item">
                    <div class="model-label">
                      <span>深度决策模型</span>
                    </div>
                    <el-select v-model="modelSettings.deepAnalysisModel" size="default" style="width: 100%" filterable>
                      <el-option
                        v-for="model in availableModels"
                        :key="`deep-${model.provider}/${model.model_name}`"
                        :label="model.model_display_name || model.model_name"
                        :value="model.model_name"
                      />
                    </el-select>
                  </div>
                </div>
              </div>

              <!-- 分析选项 -->
              <div class="config-section">
                <h4 class="config-title">⚙️ 分析选项</h4>
                <div class="option-list">
                  <div class="option-item">
                    <span class="option-name">净值走势分析</span>
                    <el-switch v-model="analysisConfig.includeNav" />
                  </div>
                  <div class="option-item">
                    <span class="option-name">持仓结构分析</span>
                    <el-switch v-model="analysisConfig.includePortfolio" />
                  </div>
                  <div class="option-item">
                    <span class="option-name">基金经理评估</span>
                    <el-switch v-model="analysisConfig.includeManager" />
                  </div>
                  <div class="option-item">
                    <span class="option-name">风险评估</span>
                    <el-switch v-model="analysisConfig.includeRisk" />
                  </div>
                  <div class="option-item">
                    <span class="option-name">费率分析</span>
                    <el-switch v-model="analysisConfig.includeFee" />
                  </div>
                  <div class="option-item">
                    <span class="option-name">规模变动分析</span>
                    <el-switch v-model="analysisConfig.includeScale" />
                  </div>
                  <div class="option-item">
                    <span class="option-name">机构持仓分析</span>
                    <el-switch v-model="analysisConfig.includeInstitution" />
                  </div>
                  <div class="option-item">
                    <span class="option-name">语言偏好</span>
                    <el-select v-model="analysisConfig.language" size="default" style="width: 100px">
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

      <!-- 分析结果显示 -->
      <div v-if="showResults && analysisResult" class="results-section">
        <el-row :gutter="24">
          <el-col :span="24">
            <el-card class="results-card" shadow="hover">
              <template #header>
                <div class="results-header">
                  <h3>📊 基金分析报告</h3>
                  <div class="result-meta">
                    <el-tag type="success">{{ selectedFund?.name }}</el-tag>
                    <el-tag>{{ selectedFund?.ts_code }}</el-tag>
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

                <!-- 投资摘要卡片 -->
                <div v-if="analysisResult.summary || analysisResult.recommendation" class="summary-card-section">
                  <el-row :gutter="16">
                    <el-col :span="12">
                      <el-card class="insight-card" shadow="hover">
                        <template #header>
                          <div class="insight-header">
                            <el-icon><Document /></el-icon>
                            <span>分析摘要</span>
                          </div>
                        </template>
                        <div class="insight-body">
                          <div
                            v-for="(line, idx) in analysisResult.summary.split('\n').filter(Boolean)"
                            :key="idx"
                            class="summary-line"
                          >
                            <span class="summary-label">{{ line.split('：')[0] }}：</span>
                            <span class="summary-value">{{ line.split('：').slice(1).join('：') }}</span>
                          </div>
                        </div>
                      </el-card>
                    </el-col>
                    <el-col :span="12">
                      <el-card class="insight-card recommendation" shadow="hover">
                        <template #header>
                          <div class="insight-header">
                            <el-icon><TrendCharts /></el-icon>
                            <span>投资建议</span>
                          </div>
                        </template>
                        <div class="insight-body markdown-body" v-html="renderMarkdown(cleanLLMFluff(analysisResult.recommendation))" />
                      </el-card>
                    </el-col>
                  </el-row>
                </div>

                <!-- 关键要点 -->
                <div v-if="analysisResult.key_points && analysisResult.key_points.length > 0" class="keypoints-section">
                  <div class="keypoints-header">
                    <el-icon size="18"><Key /></el-icon>
                    <span>关键要点</span>
                  </div>
                  <div class="keypoints-list">
                    <div
                      v-for="(point, idx) in analysisResult.key_points"
                      :key="idx"
                      class="keypoint-item"
                    >
                      <div class="keypoint-index">{{ idx + 1 }}</div>
                      <div class="keypoint-text">{{ point }}</div>
                    </div>
                  </div>
                </div>

                <!-- 各分析师子报告 -->
                <div v-if="analysisResult.nav_trend || analysisResult.holdings_analysis || analysisResult.manager_assessment || analysisResult.risk_assessment" class="sub-reports-section">
                  <h4>📑 分析师报告</h4>
                  <el-collapse>
                    <el-collapse-item v-if="analysisResult.nav_trend" title="📈 净值走势分析">
                      <div class="sub-report-content" v-html="renderMarkdown(analysisResult.nav_trend)"></div>
                    </el-collapse-item>
                    <el-collapse-item v-if="analysisResult.holdings_analysis" title="📊 持仓结构分析">
                      <div class="sub-report-content" v-html="renderMarkdown(analysisResult.holdings_analysis)"></div>
                    </el-collapse-item>
                    <el-collapse-item v-if="analysisResult.manager_assessment" title="👤 基金经理评估">
                      <div class="sub-report-content" v-html="renderMarkdown(analysisResult.manager_assessment)"></div>
                    </el-collapse-item>
                    <el-collapse-item v-if="analysisResult.risk_assessment" title="⚠️ 风险评估">
                      <div class="sub-report-content" v-html="renderMarkdown(analysisResult.risk_assessment)"></div>
                    </el-collapse-item>
                  </el-collapse>
                </div>

                <!-- 综合报告 -->
                <div v-if="analysisResult.comprehensive_report" class="report-section">
                  <h4>🎯 综合分析报告</h4>
                  <div class="comprehensive-report" v-html="renderMarkdown(analysisResult.comprehensive_report)" />
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
import { ref, reactive, watch, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  Money,
  Search,
  TrendCharts,
  Document,
  Refresh,
  Loading,
  Check,
  DataAnalysis,
  Wallet,
  User,
  WarningFilled,
  Coin,
  Key
} from '@element-plus/icons-vue'
import { analysisApi } from '@/api/analysis'
import { configApi } from '@/api/config'
import { marked } from 'marked'

marked.setOptions({ breaks: true, gfm: true })

const route = useRoute()
const router = useRouter()

// ==================== 页面状态缓存 ====================
const CACHE_KEY = 'fund_analysis_state'

const saveState = () => {
  const state = {
    selectedFund: selectedFund.value,
    analysisConfig: {
      timeRange: analysisConfig.timeRange,
      benchmark: analysisConfig.benchmark,
      researchDepth: analysisConfig.researchDepth,
      selectedAnalysts: analysisConfig.selectedAnalysts,
      includeNav: analysisConfig.includeNav,
      includePortfolio: analysisConfig.includePortfolio,
      includeManager: analysisConfig.includeManager,
      includeRisk: analysisConfig.includeRisk,
      includeFee: analysisConfig.includeFee,
      includeScale: analysisConfig.includeScale,
      includeInstitution: analysisConfig.includeInstitution,
      language: analysisConfig.language,
    },
    modelSettings: modelSettings.value,
    // 保存分析任务状态，支持页面切换后恢复进度或结果
    analysisStatus: analysisStatus.value,
    showResults: showResults.value,
    analysisResult: analysisResult.value,
    currentTaskId: currentTaskId.value,
    taskProgress: taskProgress.value,
    taskStep: taskStep.value,
  }
  sessionStorage.setItem(CACHE_KEY, JSON.stringify(state))
}

const restoreState = () => {
  const raw = sessionStorage.getItem(CACHE_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw)
  } catch (e) {
    console.warn('恢复基金分析状态失败:', e)
    return null
  }
}

const clearState = () => {
  sessionStorage.removeItem(CACHE_KEY)
}

// ==================== 基金信息（从URL参数获取，优先于缓存） ====================
const selectedFund = ref<any>(null)

const initFundFromQuery = () => {
  const tsCode = route.query.ts_code as string
  const name = route.query.name as string
  if (tsCode && name) {
    selectedFund.value = {
      ts_code: tsCode,
      name: name,
      fund_type: route.query.fund_type as string || undefined,
      market: route.query.market as string || undefined,
      management: route.query.management as string || undefined
    }
    return true
  }
  return false
}

// ==================== 分析状态 ====================
const analyzing = ref(false)
const analysisStatus = ref<'idle' | 'running' | 'completed' | 'failed'>('idle')
const showResults = ref(false)
const analysisResult = ref<any>(null)

// ==================== 分析配置 ====================
const depthOptions = [
  { icon: '⚡', name: '1级 - 快速分析', description: '基础数据概览，快速决策', time: '1-3分钟' },
  { icon: '📈', name: '2级 - 基础分析', description: '常规基金评估', time: '2-4分钟' },
  { icon: '🎯', name: '3级 - 标准分析', description: '净值+持仓+经理，推荐', time: '3-6分钟' },
  { icon: '🔍', name: '4级 - 深度分析', description: '多轮辩论，深度研究', time: '5-9分钟' },
  { icon: '🏆', name: '5级 - 全面分析', description: '最全面的基金分析报告', time: '7-12分钟' }
]

const FUND_ANALYSTS = [
  { id: 'nav', name: '净值分析师', description: '分析净值走势、历史业绩、回撤控制', iconComponent: TrendCharts },
  { id: 'portfolio', name: '持仓分析师', description: '分析持仓结构、行业分布、重仓股', iconComponent: Wallet },
  { id: 'manager', name: '基金经理评估师', description: '评估基金经理能力、任期、历史业绩', iconComponent: User },
  { id: 'risk', name: '风险评估师', description: '评估波动率、夏普比率、最大回撤', iconComponent: WarningFilled },
  { id: 'fee', name: '费率分析师', description: '分析管理费、托管费、综合费率水平', iconComponent: Coin },
  { id: 'macro', name: '宏观分析师', description: '分析市场环境对基金的影响', iconComponent: DataAnalysis }
]

const analysisConfig = reactive({
  timeRange: '1y',
  benchmark: 'default',
  researchDepth: 3,
  selectedAnalysts: ['净值分析师', '持仓分析师', '基金经理评估师'],
  includeNav: true,
  includePortfolio: true,
  includeManager: true,
  includeRisk: true,
  includeFee: true,
  includeScale: false,
  includeInstitution: false,
  language: 'zh-CN' as 'zh-CN' | 'en-US'
})

// ==================== 模型配置 ====================
const modelSettings = ref({
  quickAnalysisModel: '',
  deepAnalysisModel: ''
})

const availableModels = ref<any[]>([])

// ==================== 异步任务轮询 ====================
let pollTimer: ReturnType<typeof setInterval> | null = null
const currentTaskId = ref('')
const taskProgress = ref(0)
const taskStep = ref('')

// 自动缓存关键状态变化（配置 + 分析任务状态均缓存）
watch([selectedFund, analysisStatus, showResults, analysisResult, currentTaskId, taskProgress, taskStep], () => {
  saveState()
}, { deep: true })

watch(() => ({
  timeRange: analysisConfig.timeRange,
  benchmark: analysisConfig.benchmark,
  researchDepth: analysisConfig.researchDepth,
  selectedAnalysts: analysisConfig.selectedAnalysts,
  includeNav: analysisConfig.includeNav,
  includePortfolio: analysisConfig.includePortfolio,
  includeManager: analysisConfig.includeManager,
  includeRisk: analysisConfig.includeRisk,
  includeFee: analysisConfig.includeFee,
  includeScale: analysisConfig.includeScale,
  includeInstitution: analysisConfig.includeInstitution,
  language: analysisConfig.language,
  quickAnalysisModel: modelSettings.value.quickAnalysisModel,
  deepAnalysisModel: modelSettings.value.deepAnalysisModel,
}), () => {
  saveState()
}, { deep: true })

// ==================== 方法 ====================

const goToSearch = () => {
  saveState() // 切换前保存当前分析状态
  router.push('/analysis/fund-search')
}

// 切换分析师
const toggleAnalyst = (analystName: string) => {
  const index = analysisConfig.selectedAnalysts.indexOf(analystName)
  if (index > -1) {
    if (analysisConfig.selectedAnalysts.length > 1) {
      analysisConfig.selectedAnalysts.splice(index, 1)
    } else {
      ElMessage.warning('请至少选择一个分析师')
    }
  } else {
    analysisConfig.selectedAnalysts.push(analystName)
  }
}

const clearPollTimer = () => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

const startPolling = (taskId: string) => {
  clearPollTimer()
  currentTaskId.value = taskId

  pollTimer = setInterval(async () => {
    try {
      const resp = await analysisApi.getTaskStatus(taskId)
      if (resp?.success && resp.data) {
        const data = resp.data
        taskProgress.value = data.progress || 0
        taskStep.value = data.current_step || data.message || ''

        if (data.status === 'completed') {
          clearPollTimer()
          await fetchTaskResult(taskId)
        } else if (data.status === 'failed') {
          clearPollTimer()
          analysisStatus.value = 'failed'
          analyzing.value = false
          ElMessage.error(data.message || '基金分析失败')
        }
      }
    } catch (e) {
      console.warn('轮询进度失败:', e)
    }
  }, 2000)
}

const fetchTaskResult = async (taskId: string) => {
  try {
    const resp = await analysisApi.getTaskResult(taskId)
    if (resp?.success && resp.data) {
      const data = resp.data
      // 兼容基金分析结果结构
      analysisResult.value = {
        summary: data.summary || '',
        recommendation: data.recommendation || '',
        comprehensive_report: data.comprehensive_report || data.reports?.comprehensive_report || '',
        nav_trend: data.nav_trend || data.reports?.nav_trend || '',
        holdings_analysis: data.holdings_analysis || data.reports?.holdings_analysis || '',
        manager_assessment: data.manager_assessment || data.reports?.manager_assessment || '',
        risk_assessment: data.risk_assessment || data.reports?.risk_assessment || '',
        key_points: data.key_points || [],
        execution_time: data.execution_time || 0,
        tokens_used: data.tokens_used || 0,
        model_info: data.model_info || '',
      }
      analysisStatus.value = 'completed'
      showResults.value = true
      analyzing.value = false
      ElMessage.success('基金分析完成')
      saveState()
    } else {
      throw new Error(resp?.message || '获取分析结果失败')
    }
  } catch (e: any) {
    analysisStatus.value = 'failed'
    analyzing.value = false
    ElMessage.error(e.message || '获取分析结果失败')
  }
}

// 提交分析
const submitAnalysis = async () => {
  if (!selectedFund.value) {
    ElMessage.warning('请先选择一只基金')
    return
  }

  if (analysisConfig.selectedAnalysts.length === 0) {
    ElMessage.warning('请至少选择一个分析师')
    return
  }

  if (!modelSettings.value.quickAnalysisModel || !modelSettings.value.deepAnalysisModel) {
    ElMessage.warning('暂无可用AI模型，请检查模型配置（需启用且配置有效API Key）')
    return
  }

  analyzing.value = true
  analysisStatus.value = 'running'
  analysisResult.value = null
  showResults.value = false
  currentTaskId.value = ''
  taskProgress.value = 0
  taskStep.value = '正在提交分析任务...'

  try {
    const response = await analysisApi.analyzeFund({
      ts_code: selectedFund.value.ts_code,
      fund_name: selectedFund.value.name,
      parameters: {
        research_depth: getDepthDescription(analysisConfig.researchDepth),
        selected_analysts: analysisConfig.selectedAnalysts,
        time_range: analysisConfig.timeRange,
        benchmark: analysisConfig.benchmark,
        include_nav: analysisConfig.includeNav,
        include_portfolio: analysisConfig.includePortfolio,
        include_manager: analysisConfig.includeManager,
        include_risk: analysisConfig.includeRisk,
        include_fee: analysisConfig.includeFee,
        include_scale: analysisConfig.includeScale,
        include_institution: analysisConfig.includeInstitution,
        language: analysisConfig.language,
        quick_analysis_model: modelSettings.value.quickAnalysisModel || undefined,
        deep_analysis_model: modelSettings.value.deepAnalysisModel || undefined
      }
    })

    if (response?.success && response.data?.task_id) {
      const taskId = response.data.task_id
      currentTaskId.value = taskId
      ElMessage.success('分析任务已提交，正在后台执行')
      startPolling(taskId)
    } else {
      throw new Error(response?.message || '提交分析任务失败')
    }
  } catch (error: any) {
    clearPollTimer()
    analysisStatus.value = 'failed'
    analyzing.value = false
    ElMessage.error(error.message || '基金分析失败')
  }
}

// 重新开始分析
const restartAnalysis = () => {
  analysisStatus.value = 'idle'
  showResults.value = false
  analysisResult.value = null
  saveState()
}

// 获取深度描述
const getDepthDescription = (depth: number): string => {
  const depthMap: Record<number, string> = {
    1: '快速',
    2: '基础',
    3: '标准',
    4: '深度',
    5: '全面'
  }
  return depthMap[depth] || '标准'
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

// 清理 LLM 套话
const cleanLLMFluff = (text: string): string => {
  if (!text) return ''
  const fluffPatterns = [
    /^好的[，,].*?(?:报告|分析|如下)[。:\n]*/,
    /^作为.*?[，,].*?(?:为您|为你|向您).*?[。:\n]*/,
    /^现[为為].*?(?:呈现|提供|展示).*?[。:\n]*/,
    /^以下是.*?[的]?[权威]?投资分析[报告]?[。:\n]*/,
    /^本文[将]?[对].*?进行.*?[分析|研究|评估][。:\n]*/,
    /^综合.*?[报告|分析].*?[，,].*?(?:现|以下|给出|提出)[。:\n]*/,
    /^(?:首先|综上|总的来说|简而言之)[，,].*?[:：\n]/,
    /^---\s*$/gm,
    /^#{2,6}\s*\*\*.*?\*\*\s*$/gm,
  ]
  let cleaned = text
  fluffPatterns.forEach(pattern => {
    cleaned = cleaned.replace(pattern, '')
  })
  // 去除多余空行
  cleaned = cleaned.replace(/\n{3,}/g, '\n\n').trim()
  return cleaned || text
}

// 获取可用模型列表（与个股分析保持完全一致）
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

    // 1️⃣ 先获取所有可用的模型列表（只过滤 enabled，不检查 api_key）
    const llmConfigs = await configApi.getLLMConfigs()
    availableModels.value = sortModelsByNewest(
      llmConfigs.filter((config: any) => config.enabled)
    )

    console.log('📋 可用模型列表:', availableModels.value.map(m => ({
      model_name: m.model_name,
      provider: m.provider,
      enabled: m.enabled
    })))

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
    // 出错时清空模型选择，避免提交不可用模型
    modelSettings.value.quickAnalysisModel = ''
    modelSettings.value.deepAnalysisModel = ''
  }
}

// 页面加载
onMounted(() => {
  const hasQuery = initFundFromQuery()
  const cached = restoreState()

  // 恢复基金选择和分析配置
  if (hasQuery) {
    if (cached && cached.selectedFund?.ts_code === selectedFund.value?.ts_code) {
      if (cached.analysisConfig) {
        Object.assign(analysisConfig, cached.analysisConfig)
      }
      ElMessage.success('已恢复上次的分析配置')
    } else {
      ElMessage.info(`已选择基金：${selectedFund.value?.name}`)
    }
  } else if (cached && cached.selectedFund) {
    selectedFund.value = cached.selectedFund
    if (cached.analysisConfig) {
      Object.assign(analysisConfig, cached.analysisConfig)
    }
    ElMessage.success('已恢复上次分析状态')
  }

  // 判断是否同一支基金：是则恢复分析任务状态，否则重置
  const isSameFund = cached && cached.selectedFund?.ts_code === selectedFund.value?.ts_code
  if (isSameFund && cached) {
    // 恢复分析任务状态
    if (cached.analysisStatus) {
      analysisStatus.value = cached.analysisStatus
    }
    if (cached.showResults !== undefined) {
      showResults.value = cached.showResults
    }
    if (cached.analysisResult) {
      analysisResult.value = cached.analysisResult
    }
    if (cached.currentTaskId) {
      currentTaskId.value = cached.currentTaskId
    }
    if (cached.taskProgress !== undefined) {
      taskProgress.value = cached.taskProgress
    }
    if (cached.taskStep) {
      taskStep.value = cached.taskStep
    }

    // 如果之前正在分析，恢复轮询
    if (analysisStatus.value === 'running' && currentTaskId.value) {
      analyzing.value = true
      startPolling(currentTaskId.value)
      ElMessage.info('分析任务正在继续，已恢复进度跟踪')
    } else if (analysisStatus.value === 'completed') {
      analyzing.value = false
      showResults.value = true
    } else if (analysisStatus.value === 'failed') {
      analyzing.value = false
    }
  } else {
    // 不同基金或首次分析，重置分析状态
    analysisStatus.value = 'idle'
    showResults.value = false
    analysisResult.value = null
    currentTaskId.value = ''
    taskProgress.value = 0
    taskStep.value = ''
  }

  // 加载模型配置：先恢复缓存的选择，再验证有效性
  const cachedQuick = cached?.modelSettings?.quickAnalysisModel || ''
  const cachedDeep = cached?.modelSettings?.deepAnalysisModel || ''
  initializeModelSettings()
})

onBeforeUnmount(() => {
  clearPollTimer()
  saveState()
})
</script>

<style lang="scss" scoped>
.fund-analysis {
  min-height: 100vh;
  background: var(--el-bg-color-page);
  padding: 24px;

  .page-header {
    margin-bottom: 24px;
    background: linear-gradient(135deg, var(--el-color-primary-light-9) 0%, var(--el-color-primary-light-8) 100%);
    border: 1px solid var(--el-border-color-lighter);
    border-radius: 12px;
    padding: 20px 24px;

    .header-content {
      // wrapper only
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

  // 空状态
  .empty-state {
    .empty-card {
      border-radius: 12px;
      border: 1px solid var(--el-border-color-lighter);
      transition: box-shadow 0.3s ease;

      &:hover {
        box-shadow: var(--el-box-shadow-light);
      }

      :deep(.el-card__body) {
        padding: 48px 24px;
      }

      .empty-content {
        text-align: center;

        h3 {
          font-size: 20px;
          font-weight: 600;
          color: var(--el-text-color-primary);
          margin: 0 0 8px 0;
        }

        p {
          font-size: 14px;
          color: var(--el-text-color-secondary);
          margin: 0 0 24px 0;
        }

        .search-btn {
          // standard element-plus style
        }
      }
    }
  }

  // 已选基金信息条
  .fund-bar-card {
    border-radius: 12px;
    border: 1px solid var(--el-border-color-lighter);
    transition: box-shadow 0.3s ease;

    &:hover {
      box-shadow: var(--el-box-shadow-light);
    }

    :deep(.el-card__body) {
      padding: 16px 24px;
    }

    .fund-bar {
      display: flex;
      justify-content: space-between;
      align-items: center;

      .fund-info {
        display: flex;
        align-items: center;
        gap: 10px;

        .fund-name {
          font-size: 18px;
          font-weight: 600;
          color: var(--el-text-color-primary);
        }
      }
    }
  }

  .analysis-container {
    .main-form-card,
    .results-card {
      border-radius: 12px;
      border: 1px solid var(--el-border-color-lighter);
      transition: box-shadow 0.3s ease;

      &:hover {
        box-shadow: var(--el-box-shadow-light);
      }

      :deep(.el-card__header) {
        background: linear-gradient(135deg, var(--el-color-primary-light-9) 0%, var(--el-color-primary-light-8) 100%);
        color: var(--el-text-color-primary);
        border-bottom: 1px solid var(--el-border-color-lighter);
        border-radius: 12px 12px 0 0;
        padding: 16px 24px;

        .card-header {
          display: flex;
          justify-content: space-between;
          align-items: center;

          h3 {
            margin: 0;
            font-size: 16px;
            font-weight: 600;
          }
        }
      }

      :deep(.el-card__body) {
        padding: 24px;
      }
    }

    .analysis-form {
      .form-section {
        margin-bottom: 32px;

        &:last-child {
          margin-bottom: 0;
        }

        .section-title {
          font-size: 16px;
          font-weight: 600;
          color: var(--el-text-color-primary);
          margin: 0 0 16px 0;
          padding-bottom: 8px;
          border-bottom: 1px solid var(--el-border-color-light);
        }
      }

      .time-range-selector {
        :deep(.el-radio-group) {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
        }
        :deep(.el-radio-button__inner) {
          border-radius: 8px !important;
          border: 1px solid var(--el-border-color);
          box-shadow: none !important;
        }
      }
    }

    // 分析深度选择器
    .depth-selector {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
      gap: 12px;

      .depth-option {
        display: flex;
        align-items: center;
        padding: 14px;
        border: 1px solid var(--el-border-color-light);
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
          box-shadow: var(--el-box-shadow-light);
        }

        .depth-icon {
          font-size: 26px;
          margin-right: 10px;
          flex-shrink: 0;
        }

        .depth-info {
          flex: 1;
          min-width: 0;

          .depth-name {
            font-weight: 600;
            font-size: 13px;
            color: var(--el-text-color-primary);
            margin-bottom: 2px;
          }

          .depth-desc {
            font-size: 11px;
            color: var(--el-text-color-secondary);
            margin-bottom: 2px;
          }

          .depth-time {
            font-size: 11px;
            color: var(--el-color-primary);
            font-weight: 500;
          }
        }
      }
    }

    // 分析师团队
    .analysts-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
      gap: 12px;

      .analyst-card {
        display: flex;
        align-items: center;
        padding: 14px;
        border: 1px solid var(--el-border-color-light);
        border-radius: 12px;
        cursor: pointer;
        transition: all 0.3s ease;
        background: var(--el-bg-color);
        position: relative;

        &:hover {
          border-color: var(--el-color-primary);
          transform: translateY(-2px);
          box-shadow: var(--el-box-shadow-light);
        }

        &.active {
          border-color: var(--el-color-primary);
          background: var(--el-color-primary-light-9);
          box-shadow: var(--el-box-shadow-light);
        }

        .analyst-avatar {
          width: 40px;
          height: 40px;
          border-radius: 10px;
          background: var(--el-color-primary);
          display: flex;
          align-items: center;
          justify-content: center;
          margin-right: 12px;
          color: white;
          flex-shrink: 0;
        }

        .analyst-content {
          flex: 1;
          min-width: 0;

          .analyst-name {
            font-weight: 600;
            font-size: 13px;
            color: var(--el-text-color-primary);
            margin-bottom: 3px;
          }

          .analyst-desc {
            font-size: 11px;
            color: var(--el-text-color-secondary);
            line-height: 1.4;
          }
        }

        .analyst-check {
          flex-shrink: 0;
          margin-left: 8px;

          .check-icon {
            color: var(--el-color-primary);
            font-weight: bold;
          }
        }
      }
    }

    // 操作按钮
    .action-section {
      padding-top: 8px;
    }

    .action-buttons {
      display: flex;
      justify-content: center;
      align-items: center;
      width: 100%;

      .submit-btn {
        // standard element-plus style
      }

      .large-analysis-btn {
        // standard element-plus style
      }

      .result-btn-group {
        display: flex;
        gap: 12px;
      }
    }

    // 进度区域
    .progress-section {
      margin-top: 8px;

      .progress-card {
        border-radius: 12px;
        border: 1px solid var(--el-border-color-lighter);

        :deep(.el-card__header) {
          background: linear-gradient(135deg, var(--el-color-warning-light-9) 0%, var(--el-color-warning-light-8) 100%);
          color: var(--el-text-color-primary);
          border-bottom: 1px solid var(--el-border-color-lighter);
          border-radius: 12px 12px 0 0;
          padding: 16px 20px;
        }

        :deep(.el-card__body) {
          padding: 20px;
        }

        .progress-content {
          .current-task-info {
            .task-title {
              display: flex;
              align-items: center;
              font-size: 15px;
              font-weight: 600;
              color: var(--el-text-color-primary);
              margin-bottom: 8px;

              .task-icon {
                margin-right: 8px;
                color: var(--el-color-warning);
              }
            }

            .task-description {
              font-size: 13px;
              color: var(--el-text-color-secondary);
              line-height: 1.6;
            }
          }
        }
      }
    }

    // 右侧配置卡片
    .config-card {
      border-radius: 12px;
      border: 1px solid var(--el-border-color-lighter);
      transition: box-shadow 0.3s ease;

      &:hover {
        box-shadow: var(--el-box-shadow-light);
      }

      :deep(.el-card__header) {
        background: linear-gradient(135deg, var(--el-color-warning-light-9) 0%, var(--el-color-warning-light-8) 100%);
        color: var(--el-text-color-primary);
        border-bottom: 1px solid var(--el-border-color-lighter);
        border-radius: 12px 12px 0 0;
        padding: 16px 24px;

        .card-header {
          display: flex;
          justify-content: space-between;
          align-items: center;

          h3 {
            margin: 0;
            font-size: 16px;
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

          .config-title {
            font-size: 14px;
            font-weight: 600;
            color: var(--el-text-color-primary);
            margin: 0 0 12px 0;
          }

          .model-config {
            .model-item {
              margin-bottom: 12px;

              &:last-child {
                margin-bottom: 0;
              }

              .model-label {
                display: flex;
                align-items: center;
                justify-content: space-between;
                margin-bottom: 8px;
                font-size: 13px;
                color: var(--el-text-color-regular);
              }
            }
          }

          .option-list {
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

              .option-name {
                font-size: 13px;
                font-weight: 500;
                color: var(--el-text-color-regular);
              }
            }

            .language-option {
              padding: 8px 0;
            }
          }
        }
      }
    }

    // 结果区域
    .results-section {
      margin-top: 24px;

      .results-card {
        :deep(.el-card__header) {
          background: linear-gradient(135deg, var(--el-color-success-light-9) 0%, var(--el-color-success-light-8) 100%);
          color: var(--el-text-color-primary);
          border-bottom: 1px solid var(--el-border-color-lighter);
        }

        .results-content {
          :deep(table) {
            width: 100%;
            border-collapse: collapse;
            margin: 12px 0;
            font-size: 13px;

            th, td {
              padding: 8px 12px;
              text-align: left;
              border-bottom: 1px solid var(--el-border-color-lighter);
            }

            th {
              font-weight: 600;
              color: var(--el-text-color-primary);
              background: var(--el-fill-color-light);
            }

            tr:hover td {
              background: var(--el-fill-color);
            }
          }

          .risk-disclaimer {
            margin-bottom: 24px;
          }

          .report-section,
          .summary-section,
          .recommendation-section {
            margin-bottom: 32px;

            h4 {
              font-size: 16px;
              font-weight: 600;
              color: var(--el-text-color-primary);
              margin: 0 0 16px 0;
              padding-bottom: 8px;
              border-bottom: 1px solid var(--el-border-color-light);
            }
          }

          .comprehensive-report {
            line-height: 1.8;
            color: var(--el-text-color-regular);

            :deep(h3) {
              color: var(--el-text-color-primary);
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
              color: var(--el-text-color-primary);
            }
          }

          // 关键要点
          .keypoints-section {
            margin-bottom: 24px;
            background: var(--el-bg-color);
            border-radius: 12px;
            padding: 20px 24px;
            border: 1px solid var(--el-border-color-lighter);
            transition: box-shadow 0.3s ease;

            &:hover {
              box-shadow: var(--el-box-shadow-light);
            }

            .keypoints-header {
              display: flex;
              align-items: center;
              gap: 8px;
              font-size: 16px;
              font-weight: 600;
              color: var(--el-text-color-primary);
              margin-bottom: 16px;
              padding-bottom: 12px;
              border-bottom: 1px solid var(--el-border-color-light);

              .el-icon {
                color: var(--el-color-primary);
              }
            }

            .keypoints-list {
              display: flex;
              flex-direction: column;
              gap: 12px;

              .keypoint-item {
                display: flex;
                align-items: flex-start;
                gap: 12px;
                padding: 14px 16px;
                background: var(--el-fill-color-light);
                border-radius: 10px;
                border-left: 3px solid var(--el-color-primary);
                transition: all 0.2s ease;

                &:hover {
                  background: var(--el-color-primary-light-9);
                  transform: translateX(4px);
                }

                .keypoint-index {
                  width: 24px;
                  height: 24px;
                  border-radius: 50%;
                  background: var(--el-color-primary);
                  color: white;
                  display: flex;
                  align-items: center;
                  justify-content: center;
                  font-size: 12px;
                  font-weight: 700;
                  flex-shrink: 0;
                  margin-top: 2px;
                }

                .keypoint-text {
                  flex: 1;
                  font-size: 14px;
                  line-height: 1.7;
                  color: var(--el-text-color-regular);
                }
              }
            }
          }

          // 摘要与建议卡片
          .summary-card-section {
            margin-bottom: 24px;

            .insight-card {
              border-radius: 12px;
              border: 1px solid var(--el-border-color-lighter);
              height: 100%;
              transition: box-shadow 0.3s ease;

              &:hover {
                box-shadow: var(--el-box-shadow-light);
              }

              :deep(.el-card__header) {
                background: linear-gradient(135deg, var(--el-color-info-light-9) 0%, var(--el-color-info-light-8) 100%);
                color: var(--el-text-color-primary);
                border-bottom: 1px solid var(--el-border-color-lighter);
                border-radius: 12px 12px 0 0;
                padding: 14px 20px;

                .insight-header {
                  display: flex;
                  align-items: center;
                  gap: 8px;
                  font-size: 15px;
                  font-weight: 600;

                  .el-icon {
                    font-size: 18px;
                  }
                }
              }

              :deep(.el-card__body) {
                padding: 16px 20px;
                max-height: 320px;
                overflow-y: auto;
              }

              .insight-body {
                font-size: 14px;
                line-height: 1.7;
                color: var(--el-text-color-regular);

                :deep(p) {
                  margin: 0 0 10px 0;

                  &:last-child {
                    margin-bottom: 0;
                  }
                }

                :deep(strong) {
                  color: var(--el-text-color-primary);
                  font-weight: 600;
                }

                :deep(h1, h2, h3, h4) {
                  font-size: 15px;
                  font-weight: 600;
                  color: var(--el-text-color-primary);
                  margin: 12px 0 8px 0;
                }

                :deep(ul, ol) {
                  padding-left: 18px;
                  margin: 8px 0;
                }

                :deep(li) {
                  margin-bottom: 4px;
                }

                :deep(blockquote) {
                  margin: 8px 0;
                  padding: 8px 12px;
                  border-left: 3px solid var(--el-color-info);
                  background: var(--el-color-info-light-9);
                  color: var(--el-text-color-regular);
                  font-size: 13px;
                }

                :deep(code) {
                  background: var(--el-fill-color-light);
                  padding: 2px 6px;
                  border-radius: 4px;
                  font-size: 13px;
                  color: var(--el-text-color-regular);
                }

                .summary-line {
                  display: flex;
                  align-items: baseline;
                  gap: 4px;
                  margin-bottom: 12px;
                  font-size: 14px;
                  line-height: 1.6;

                  &:last-child {
                    margin-bottom: 0;
                  }

                  .summary-label {
                    font-weight: 600;
                    color: var(--el-text-color-primary);
                    white-space: nowrap;
                    flex-shrink: 0;
                  }

                  .summary-value {
                    color: var(--el-text-color-regular);
                    font-weight: 500;
                  }
                }
              }

              &.recommendation {
                :deep(.el-card__header) {
                  background: linear-gradient(135deg, var(--el-color-warning-light-9) 0%, var(--el-color-warning-light-8) 100%);
                }

                .insight-body {
                  :deep(blockquote) {
                    border-left-color: var(--el-color-warning);
                    background: var(--el-color-warning-light-9);
                    color: var(--el-text-color-regular);
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
</style>
