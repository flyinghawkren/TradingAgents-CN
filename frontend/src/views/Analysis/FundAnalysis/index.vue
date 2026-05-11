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

    <!-- 基金搜索与分析区域 -->
    <div class="analysis-container">
      <el-row :gutter="24">
        <!-- 左侧：基金搜索与选择 -->
        <el-col :span="18">
          <el-card class="search-card" shadow="hover">
            <template #header>
              <div class="card-header">
                <h3>🔍 基金搜索</h3>
                <el-tag type="primary" size="small">支持代码/名称搜索</el-tag>
              </div>
            </template>

            <div class="search-section">
              <el-input
                v-model="searchKeyword"
                placeholder="输入基金代码或名称，如：510050 或 华夏上证50"
                size="large"
                clearable
                @keyup.enter="searchFunds"
                class="search-input"
              >
                <template #append>
                  <el-button type="primary" @click="searchFunds" :loading="searching">
                    <el-icon><Search /></el-icon>
                    搜索
                  </el-button>
                </template>
              </el-input>

              <!-- 搜索结果 -->
              <div v-if="searchResults.length > 0" class="search-results">
                <el-table :data="searchResults" style="width: 100%" @row-click="selectFund">
                  <el-table-column prop="ts_code" label="基金代码" width="120" />
                  <el-table-column prop="name" label="基金名称" />
                  <el-table-column prop="fund_type" label="类型" width="100" />
                  <el-table-column prop="market" label="市场" width="80">
                    <template #default="{ row }">
                      <el-tag size="small" :type="row.market === 'E' ? 'success' : 'info'">
                        {{ row.market === 'E' ? '场内' : '场外' }}
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column label="操作" width="100">
                    <template #default="{ row }">
                      <el-button type="primary" size="small" @click.stop="selectFund(row)">
                        分析
                      </el-button>
                    </template>
                  </el-table-column>
                </el-table>
              </div>

              <!-- 空状态 -->
              <div v-else-if="searched && !searching" class="empty-results">
                <el-empty description="未找到相关基金" />
              </div>
            </div>
          </el-card>

          <!-- 选中的基金信息 -->
          <el-card v-if="selectedFund" class="fund-info-card" shadow="hover" style="margin-top: 24px;">
            <template #header>
              <div class="card-header">
                <h3>📋 基金信息</h3>
                <el-tag type="success" size="small">{{ selectedFund.ts_code }}</el-tag>
              </div>
            </template>

            <div class="fund-info">
              <el-descriptions :column="2" border>
                <el-descriptions-item label="基金名称">{{ selectedFund.name }}</el-descriptions-item>
                <el-descriptions-item label="基金类型">{{ selectedFund.fund_type || '-' }}</el-descriptions-item>
                <el-descriptions-item label="管理人">{{ selectedFund.management || '-' }}</el-descriptions-item>
                <el-descriptions-item label="市场">{{ selectedFund.market === 'E' ? '场内(ETF/LOF)' : '场外' }}</el-descriptions-item>
              </el-descriptions>

              <div class="action-buttons" style="margin-top: 24px; display: flex; justify-content: center;">
                <el-button
                  type="primary"
                  size="large"
                  @click="startFundAnalysis"
                  :loading="analyzing"
                  class="submit-btn"
                  style="width: 280px; height: 56px; font-size: 18px; font-weight: 700; border-radius: 16px;"
                >
                  <el-icon><TrendCharts /></el-icon>
                  开始基金分析
                </el-button>
              </div>
            </div>
          </el-card>
        </el-col>

        <!-- 右侧：分析配置 -->
        <el-col :span="6">
          <el-card class="config-card" shadow="hover">
            <template #header>
              <div class="card-header">
                <h3>⚙️ 分析配置</h3>
              </div>
            </template>

            <div class="config-content">
              <div class="config-section">
                <h4 class="config-title">🤖 AI模型</h4>
                <el-select v-model="analysisConfig.model" size="small" style="width: 100%">
                  <el-option label="自动选择" value="auto" />
                  <el-option label="深度分析模型" value="deep" />
                </el-select>
              </div>

              <div class="config-section">
                <h4 class="config-title">⚙️ 分析选项</h4>
                <div class="analysis-options">
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
            </div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 分析结果 -->
      <el-row v-if="analysisResult" :gutter="24" style="margin-top: 24px;">
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
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { Money, Search, TrendCharts } from '@element-plus/icons-vue'
import { analysisApi } from '@/api/analysis'
import { marked } from 'marked'

marked.setOptions({ breaks: true, gfm: true })

const searchKeyword = ref('')
const searching = ref(false)
const searched = ref(false)
const searchResults = ref<any[]>([])
const selectedFund = ref<any>(null)
const analyzing = ref(false)
const analysisResult = ref<any>(null)

const analysisConfig = reactive({
  model: 'auto',
  includeNav: true,
  includePortfolio: true,
  includeManager: true,
  includeRisk: true,
})

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
  ElMessage.info(`已选择基金：${row.name}`)
}

// 开始基金分析
const startFundAnalysis = async () => {
  if (!selectedFund.value) {
    ElMessage.warning('请先选择一只基金')
    return
  }

  analyzing.value = true
  analysisResult.value = null

  try {
    const response = await analysisApi.analyzeFund({
      ts_code: selectedFund.value.ts_code,
      fund_name: selectedFund.value.name,
    })

    if (response?.success && response.data) {
      analysisResult.value = response.data
      ElMessage.success('基金分析完成')
    } else {
      throw new Error(response?.message || '分析失败')
    }
  } catch (error: any) {
    ElMessage.error(error.message || '基金分析失败')
  } finally {
    analyzing.value = false
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
    .search-card, .fund-info-card, .results-card {
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

    .search-section {
      .search-input {
        :deep(.el-input__inner) {
          border-radius: 12px;
        }
      }

      .search-results {
        margin-top: 20px;
      }

      .empty-results {
        margin-top: 40px;
      }
    }

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
                }
              }
            }
          }
        }
      }
    }

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
</style>

<style>
/* 全局样式确保按钮样式生效 */
.submit-btn.el-button {
  background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%) !important;
  border: none !important;
  transition: all 0.3s ease !important;
  box-shadow: 0 4px 15px rgba(139, 92, 246, 0.2) !important;
}

.submit-btn.el-button:hover {
  transform: translateY(-3px) !important;
  box-shadow: 0 12px 30px rgba(139, 92, 246, 0.4) !important;
  background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%) !important;
}
</style>
