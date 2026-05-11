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

    <!-- 主要分析区域 -->
    <div class="analysis-container">
      <el-row :gutter="24">
        <!-- 左侧：基金数据 + 分析配置 -->
        <el-col :span="18">
          <!-- 基金搜索与数据展示 -->
          <el-card class="main-form-card" shadow="hover">
            <template #header>
              <div class="card-header">
                <h3>基金数据</h3>
                <el-tag type="info" size="small">支持代码/名称搜索</el-tag>
              </div>
            </template>

            <el-form label-width="100px" class="analysis-form">
              <!-- 基金搜索 -->
              <div class="form-section">
                <h4 class="section-title">🔍 基金搜索</h4>
                <el-row :gutter="16">
                  <el-col :span="24">
                    <el-form-item label="基金代码/名称" required>
                      <el-input
                        v-model="searchKeyword"
                        placeholder="输入基金代码或名称，如：510050 或 华夏上证50"
                        clearable
                        size="large"
                        class="stock-input"
                        @keyup.enter="searchFunds"
                      >
                        <template #prefix>
                          <el-icon><Search /></el-icon>
                        </template>
                        <template #append>
                          <el-button type="primary" @click="searchFunds" :loading="searching">
                            搜索
                          </el-button>
                        </template>
                      </el-input>
                    </el-form-item>
                  </el-col>
                </el-row>

                <!-- 搜索结果 -->
                <div v-if="searchResults.length > 0" class="search-results">
                  <el-table :data="searchResults" style="width: 100%" @row-click="selectFund" highlight-current-row>
                    <el-table-column prop="ts_code" label="基金代码" width="120" />
                    <el-table-column prop="name" label="基金名称" />
                    <el-table-column prop="fund_type" label="类型" width="120" />
                    <el-table-column prop="market" label="市场" width="100">
                      <template #default="{ row }">
                        <el-tag size="small" :type="row.market === 'E' ? 'success' : 'info'">
                          {{ row.market === 'E' ? '场内' : '场外' }}
                        </el-tag>
                      </template>
                    </el-table-column>
                    <el-table-column label="操作" width="100">
                      <template #default="{ row }">
                        <el-button type="primary" size="small" @click.stop="selectFund(row)">
                          选择
                        </el-button>
                      </template>
                    </el-table-column>
                  </el-table>
                </div>

                <!-- 空状态 -->
                <div v-else-if="searched && !searching && !selectedFund" class="empty-results">
                  <el-empty description="未找到相关基金" />
                </div>
              </div>

              <!-- 选中基金信息 -->
              <div v-if="selectedFund" class="form-section">
                <h4 class="section-title">📋 基金信息</h4>
                <el-descriptions :column="2" border>
                  <el-descriptions-item label="基金名称">{{ selectedFund.name }}</el-descriptions-item>
                  <el-descriptions-item label="基金代码">{{ selectedFund.ts_code }}</el-descriptions-item>
                  <el-descriptions-item label="基金类型">{{ selectedFund.fund_type || '-' }}</el-descriptions-item>
                  <el-descriptions-item label="管理人">{{ selectedFund.management || '-' }}</el-descriptions-item>
                  <el-descriptions-item label="市场">{{ selectedFund.market === 'E' ? '场内(ETF/LOF)' : '场外' }}</el-descriptions-item>
                  <el-descriptions-item label="状态">
                    <el-tag v-if="selectedFund.status === 'L'" type="success">存续</el-tag>
                    <el-tag v-else type="info">{{ selectedFund.status || '-' }}</el-tag>
                  </el-descriptions-item>
                </el-descriptions>
              </div>
            </el-form>
          </el-card>

          <!-- 分析配置 -->
          <el-card v-if="selectedFund" class="main-form-card" shadow="hover" style="margin-top: 24px;">
            <template #header>
              <div class="card-header">
                <h3>分析配置</h3>
                <el-tag type="info" size="small">选填信息</el-tag>
              </div>
            </template>

            <el-form label-width="100px" class="analysis-form">
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
                      <el-icon>
                        <component :is="analyst.icon" />
                      </el-icon>
                    </div>
                    <div class="analyst-content">
                      <div class="analyst-name">{{ analyst.name }}</div>
                      <div class="analyst-desc">{{ analyst.description }}</div>
                    </div>
                    <div class="analyst-check">
                      <el-icon v-if="analysisConfig.selectedAnalysts.includes(analyst.name)" class="check-icon">
                        <Check />
                      </el-icon>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 操作按钮 -->
              <div class="form-section">
                <div class="action-buttons">
                  <el-button
                    v-if="analysisStatus === 'idle'"
                    type="primary"
                    size="large"
                    @click="submitAnalysis"
                    :loading="analyzing"
                    :disabled="!selectedFund"
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

                  <div v-else-if="analysisStatus === 'completed'" style="display: flex; gap: 12px;">
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
                    <el-select v-model="modelSettings.quickAnalysisModel" size="small" style="width: 100%">
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
                    <el-select v-model="modelSettings.deepAnalysisModel" size="small" style="width: 100%">
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
                    <div class="option-info">
                      <span class="option-name">净值走势分析</span>
                    </div>
                    <el-switch v-model="analysisConfig.includeNav" />
                  </div>

                  <div class="option-item">
                    <div class="option-info">
                      <span class="option-name">持仓结构分析</span>
                    </div>
                    <el-switch v-model="analysisConfig.includePortfolio" />
                  </div>

                  <div class="option-item">
                    <div class="option-info">
                      <span class="option-name">基金经理评估</span>
                    </div>
                    <el-switch v-model="analysisConfig.includeManager" />
                  </div>

                  <div class="option-item">
                    <div class="option-info">
                      <span class="option-name">风险评估</span>
                    </div>
                    <el-switch v-model="analysisConfig.includeRisk" />
                  </div>
                </div>
              </div>

              <!-- 语言偏好 -->
              <div class="config-section">
                <h4 class="config-title">🌐 语言偏好</h4>
                <div class="option-item">
                  <div class="option-info">
                    <span class="option-name">报告语言</span>
                  </div>
                  <el-select v-model="analysisConfig.language" size="small" style="width: 100px">
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
  InfoFilled
} from '@element-plus/icons-vue'
import { analysisApi } from '@/api/analysis'
import { configApi } from '@/api/config'
import { marked } from 'marked'

marked.setOptions({ breaks: true, gfm: true })

// ==================== 搜索相关 ====================
const searchKeyword = ref('')
const searching = ref(false)
const searched = ref(false)
const searchResults = ref<any[]>([])
const selectedFund = ref<any>(null)

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
  { id: 'nav', name: '净值分析师', description: '分析净值走势、历史业绩、回撤控制', icon: 'TrendCharts' },
  { id: 'portfolio', name: '持仓分析师', description: '分析持仓结构、行业分布、重仓股', icon: 'Wallet' },
  { id: 'manager', name: '基金经理评估师', description: '评估基金经理能力、任期、历史业绩', icon: 'User' },
  { id: 'risk', name: '风险评估师', description: '评估波动率、夏普比率、最大回撤', icon: 'WarningFilled' },
  { id: 'macro', name: '宏观分析师', description: '分析市场环境对基金的影响', icon: 'DataAnalysis' }
]

const analysisConfig = reactive({
  researchDepth: 3,
  selectedAnalysts: ['净值分析师', '持仓分析师', '基金经理评估师'],
  includeNav: true,
  includePortfolio: true,
  includeManager: true,
  includeRisk: true,
  language: 'zh-CN' as 'zh-CN' | 'en-US'
})

// ==================== 模型配置 ====================
const modelSettings = ref({
  quickAnalysisModel: 'auto',
  deepAnalysisModel: 'auto'
})

const availableModels = ref<any[]>([])

// ==================== 方法 ====================

// 搜索基金
const searchFunds = async () => {
  if (!searchKeyword.value.trim()) {
    ElMessage.warning('请输入基金代码或名称')
    return
  }

  searching.value = true
  searched.value = true
  searchResults.value = []
  selectedFund.value = null
  analysisResult.value = null
  analysisStatus.value = 'idle'
  showResults.value = false

  try {
    const response = await analysisApi.searchFunds(searchKeyword.value.trim())
    if (response?.success && response.data) {
      searchResults.value = response.data
      if (searchResults.value.length === 0) {
        ElMessage.info('未找到相关基金')
      } else {
        ElMessage.success(`找到 ${searchResults.value.length} 只基金`)
      }
    } else {
      ElMessage.warning(response?.message || '搜索失败')
    }
  } catch (error: any) {
    ElMessage.error(error.message || '搜索失败')
  } finally {
    searching.value = false
  }
}

// 选择基金
const selectFund = (row: any) => {
  selectedFund.value = row
  analysisResult.value = null
  analysisStatus.value = 'idle'
  showResults.value = false
  ElMessage.success(`已选择基金：${row.name}`)
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
        include_sentiment: analysisConfig.includeNav,
        include_risk: analysisConfig.includeRisk,
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
  fetchAvailableModels()
})
</script>

<style lang="scss" scoped>
.fund-analysis {
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
          color: #8b5cf6;
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

      .search-results {
        margin-top: 16px;
      }

      .empty-results {
        margin-top: 40px;
      }
    }

    // 分析深度选择器
    .depth-selector {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
      gap: 12px;

      .depth-option {
        display: flex;
        align-items: center;
        padding: 16px;
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
          font-size: 28px;
          margin-right: 12px;
        }

        .depth-info {
          flex: 1;

          .depth-name {
            font-weight: 600;
            font-size: 14px;
            color: #1a202c;
            margin-bottom: 4px;
          }

          .depth-desc {
            font-size: 12px;
            color: #64748b;
            margin-bottom: 4px;
          }

          .depth-time {
            font-size: 12px;
            color: #8b5cf6;
            font-weight: 500;
          }
        }
      }
    }

    // 分析师团队
    .analysts-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
      gap: 12px;

      .analyst-card {
        display: flex;
        align-items: center;
        padding: 16px;
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
          font-size: 18px;
        }

        .analyst-content {
          flex: 1;

          .analyst-name {
            font-weight: 600;
            font-size: 14px;
            color: #1a202c;
            margin-bottom: 4px;
          }

          .analyst-desc {
            font-size: 12px;
            color: #64748b;
            line-height: 1.4;
          }
        }

        .analyst-check {
          .check-icon {
            color: #8b5cf6;
            font-size: 20px;
            font-weight: bold;
          }
        }
      }
    }

    // 操作按钮
    .action-buttons {
      display: flex;
      justify-content: center;
      align-items: center;
      width: 100%;
      text-align: center;

      .submit-btn {
        width: 280px;
        height: 56px;
        font-size: 18px;
        font-weight: 700;
        border-radius: 16px;
        background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%);
        border: none;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(139, 92, 246, 0.2);

        &:hover {
          transform: translateY(-3px);
          box-shadow: 0 12px 30px rgba(139, 92, 246, 0.4);
        }
      }
    }

    // 进度区域
    .progress-section {
      margin-top: 24px;

      .progress-card {
        border-radius: 12px;

        :deep(.el-card__header) {
          background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
          color: white;
          border-radius: 12px 12px 0 0;
        }

        .progress-content {
          .current-task-info {
            .task-title {
              display: flex;
              align-items: center;
              font-size: 16px;
              font-weight: 600;
              color: #1a202c;
              margin-bottom: 12px;

              .task-icon {
                margin-right: 8px;
                color: #f59e0b;
              }
            }

            .task-description {
              font-size: 14px;
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
                }

                .option-desc {
                  font-size: 12px;
                  color: #9ca3af;
                  margin-top: 2px;
                }
              }
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

<style>
/* 全局样式确保按钮样式生效 */
.large-analysis-btn.el-button {
  background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%) !important;
  border: none !important;
  transition: all 0.3s ease !important;
  box-shadow: 0 4px 15px rgba(139, 92, 246, 0.2) !important;
}

.large-analysis-btn.el-button:hover {
  transform: translateY(-3px) !important;
  box-shadow: 0 12px 30px rgba(139, 92, 246, 0.4) !important;
  background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%) !important;
}
</style>
