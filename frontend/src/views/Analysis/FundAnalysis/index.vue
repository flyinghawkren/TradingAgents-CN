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
                    </div>
                  </template>
                  <div class="progress-content">
                    <div class="current-task-info">
                      <div class="task-title">
                        <el-icon class="task-icon is-loading"><Loading /></el-icon>
                        AI正在分析基金数据...
                      </div>
                      <div class="task-description">
                        正在获取净值走势、持仓结构、基金经理等多维度数据，请稍候
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
                    <el-select v-model="modelSettings.quickAnalysisModel" size="default" style="width: 100%">
                      <el-option label="自动选择" value="auto" />
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
                    <el-select v-model="modelSettings.deepAnalysisModel" size="default" style="width: 100%">
                      <el-option label="自动选择" value="auto" />
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
                </div>
              </div>

              <!-- 语言偏好 -->
              <div class="config-section">
                <h4 class="config-title">🌐 语言偏好</h4>
                <div class="option-item language-option">
                  <span class="option-name">报告语言</span>
                  <el-select v-model="analysisConfig.language" size="default" style="width: 100px">
                    <el-option label="中文" value="zh-CN" />
                    <el-option label="English" value="en-US" />
                  </el-select>
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

                <!-- 综合报告 -->
                <div v-if="analysisResult.comprehensive_report" class="report-section">
                  <h4>🎯 综合分析报告</h4>
                  <div class="comprehensive-report" v-html="renderMarkdown(analysisResult.comprehensive_report)"></div>
                </div>

                <!-- 摘要 -->
                <div v-if="analysisResult.summary" class="summary-section">
                  <h4>📋 分析摘要</h4>
                  <p>{{ analysisResult.summary }}</p>
                </div>

                <!-- 建议 -->
                <div v-if="analysisResult.recommendation" class="recommendation-section">
                  <h4>💡 投资建议</h4>
                  <p>{{ analysisResult.recommendation }}</p>
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
import { ref, reactive, onMounted } from 'vue'
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
  Coin
} from '@element-plus/icons-vue'
import { analysisApi } from '@/api/analysis'
import { configApi } from '@/api/config'
import { marked } from 'marked'

marked.setOptions({ breaks: true, gfm: true })

const route = useRoute()
const router = useRouter()

// ==================== 基金信息（从URL参数获取） ====================
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
  }
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
  quickAnalysisModel: 'auto',
  deepAnalysisModel: 'auto'
})

const availableModels = ref<any[]>([])

// ==================== 方法 ====================

const goToSearch = () => {
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

  analyzing.value = true
  analysisStatus.value = 'running'
  analysisResult.value = null
  showResults.value = false

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
        quick_analysis_model: modelSettings.value.quickAnalysisModel === 'auto' ? undefined : modelSettings.value.quickAnalysisModel,
        deep_analysis_model: modelSettings.value.deepAnalysisModel === 'auto' ? undefined : modelSettings.value.deepAnalysisModel
      }
    })

    if (response?.success && response.data) {
      analysisResult.value = response.data
      analysisStatus.value = 'completed'
      showResults.value = true
      ElMessage.success('基金分析完成')
    } else {
      throw new Error(response?.message || '分析失败')
    }
  } catch (error: any) {
    analysisStatus.value = 'failed'
    ElMessage.error(error.message || '基金分析失败')
  } finally {
    analyzing.value = false
  }
}

// 重新开始分析
const restartAnalysis = () => {
  analysisStatus.value = 'idle'
  showResults.value = false
  analysisResult.value = null
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

// 获取可用模型列表
const fetchAvailableModels = async () => {
  try {
    const configs = await configApi.getLLMConfigs()
    if (configs && Array.isArray(configs)) {
      availableModels.value = configs.filter((c: any) => c.enabled)
    }
  } catch (error) {
    console.warn('获取模型列表失败:', error)
  }
}

// 页面加载
onMounted(() => {
  initFundFromQuery()
  fetchAvailableModels()
})
</script>

<style lang="scss" scoped>
.fund-analysis {
  min-height: 100vh;
  background: var(--el-bg-color-page);
  padding: 24px;

  .page-header {
    margin-bottom: 24px;

    .header-content {
      background: var(--el-bg-color);
      padding: 28px 32px;
      border-radius: 16px;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
    }

    .title-section {
      .page-title {
        display: flex;
        align-items: center;
        font-size: 28px;
        font-weight: 700;
        color: #1a202c;
        margin: 0 0 8px 0;

        .title-icon {
          margin-right: 12px;
          color: #8b5cf6;
        }
      }

      .page-description {
        font-size: 15px;
        color: #64748b;
        margin: 0;
      }
    }
  }

  // 空状态
  .empty-state {
    .empty-card {
      border-radius: 16px;
      border: none;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);

      :deep(.el-card__body) {
        padding: 48px 24px;
      }

      .empty-content {
        text-align: center;

        h3 {
          font-size: 20px;
          font-weight: 600;
          color: #1a202c;
          margin: 0 0 8px 0;
        }

        p {
          font-size: 14px;
          color: #64748b;
          margin: 0 0 24px 0;
        }

        .search-btn {
          min-width: 200px;
          height: 48px;
          font-size: 16px;
          font-weight: 600;
          border-radius: 12px;
        }
      }
    }
  }

  // 已选基金信息条
  .fund-bar-card {
    border-radius: 12px;
    border: none;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);

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
          color: #1a202c;
        }
      }
    }
  }

  .analysis-container {
    .main-form-card,
    .results-card {
      border-radius: 16px;
      border: none;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);

      :deep(.el-card__header) {
        background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%);
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
          color: #1a202c;
          margin: 0 0 16px 0;
          padding-bottom: 8px;
          border-bottom: 2px solid #e2e8f0;
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
          border: 1px solid #e2e8f0;
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
        border: 2px solid #e2e8f0;
        border-radius: 12px;
        cursor: pointer;
        transition: all 0.3s ease;
        background: white;

        &:hover {
          border-color: #8b5cf6;
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(139, 92, 246, 0.15);
        }

        &.active {
          border-color: #8b5cf6;
          background: linear-gradient(135deg, #f3e8ff 0%, #e9d5ff 100%);
          box-shadow: 0 4px 12px rgba(139, 92, 246, 0.2);
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
            color: #1a202c;
            margin-bottom: 2px;
          }

          .depth-desc {
            font-size: 11px;
            color: #64748b;
            margin-bottom: 2px;
          }

          .depth-time {
            font-size: 11px;
            color: #8b5cf6;
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
        border: 2px solid #e2e8f0;
        border-radius: 12px;
        cursor: pointer;
        transition: all 0.3s ease;
        background: white;
        position: relative;

        &:hover {
          border-color: #8b5cf6;
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(139, 92, 246, 0.15);
        }

        &.active {
          border-color: #8b5cf6;
          background: linear-gradient(135deg, #f3e8ff 0%, #e9d5ff 100%);
          box-shadow: 0 4px 12px rgba(139, 92, 246, 0.2);
        }

        .analyst-avatar {
          width: 40px;
          height: 40px;
          border-radius: 10px;
          background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%);
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
            color: #1a202c;
            margin-bottom: 3px;
          }

          .analyst-desc {
            font-size: 11px;
            color: #64748b;
            line-height: 1.4;
          }
        }

        .analyst-check {
          flex-shrink: 0;
          margin-left: 8px;

          .check-icon {
            color: #8b5cf6;
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
        min-width: 200px;
        height: 52px;
        font-size: 17px;
        font-weight: 700;
        border-radius: 14px;
        border: none;
        transition: all 0.3s ease;
      }

      .large-analysis-btn {
        min-width: 280px;
        background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%);
        box-shadow: 0 4px 15px rgba(139, 92, 246, 0.25);

        &:hover {
          transform: translateY(-3px);
          box-shadow: 0 12px 30px rgba(139, 92, 246, 0.4);
          background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%);
        }
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
        border: none;

        :deep(.el-card__header) {
          background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
          color: white;
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
              color: #1a202c;
              margin-bottom: 8px;

              .task-icon {
                margin-right: 8px;
                color: #f59e0b;
              }
            }

            .task-description {
              font-size: 13px;
              color: #64748b;
              line-height: 1.6;
            }
          }
        }
      }
    }

    // 右侧配置卡片
    .config-card {
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

          .config-title {
            font-size: 14px;
            font-weight: 600;
            color: #374151;
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
                color: #4b5563;
              }
            }
          }

          .option-list {
            .option-item {
              display: flex;
              align-items: center;
              justify-content: space-between;
              padding: 10px 0;
              border-bottom: 1px solid #f3f4f6;

              &:last-child {
                border-bottom: none;
                padding-bottom: 0;
              }

              .option-name {
                font-size: 13px;
                font-weight: 500;
                color: #374151;
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
          background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        }

        .results-content {
          .risk-disclaimer {
            margin-bottom: 24px;
          }

          .report-section,
          .summary-section,
          .recommendation-section {
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
      }
    }
  }
}
</style>
