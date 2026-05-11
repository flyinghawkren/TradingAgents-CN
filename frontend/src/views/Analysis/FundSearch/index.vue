<template>
  <div class="fund-search">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-content">
        <div class="title-section">
          <h1 class="page-title">
            <el-icon class="title-icon"><Search /></el-icon>
            基金搜索
          </h1>
          <p class="page-description">
            搜索公募基金信息，查看净值、费率、持仓、基金经理等核心数据
          </p>
        </div>
      </div>
    </div>

    <!-- 搜索区域 -->
    <el-card class="search-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <h3>🔍 基金搜索</h3>
          <el-tag type="primary" size="small">支持代码/名称/拼音首字母</el-tag>
        </div>
      </template>

      <div class="search-box">
        <el-input
          v-model="searchKeyword"
          placeholder="输入基金代码或名称，如：510050 或 华夏上证50"
          size="large"
          clearable
          class="search-input"
          @keyup.enter="searchFunds"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
          <template #append>
            <el-button type="primary" @click="searchFunds" :loading="searching">
              <el-icon><Search /></el-icon>
              搜索
            </el-button>
          </template>
        </el-input>
      </div>

      <!-- 搜索结果 -->
      <div v-if="searchResults.length > 0" class="search-results">
        <el-table
          :data="searchResults"
          style="width: 100%"
          @row-click="selectFund"
          highlight-current-row
          :row-class-name="getRowClassName"
        >
          <el-table-column prop="ts_code" label="基金代码" width="130" />
          <el-table-column prop="name" label="基金名称" min-width="200" />
          <el-table-column prop="fund_type" label="类型" width="120" />
          <el-table-column prop="market" label="市场" width="90">
            <template #default="{ row }">
              <el-tag size="small" :type="row.market === 'E' ? 'success' : 'info'">
                {{ row.market === 'E' ? '场内' : '场外' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120" fixed="right">
            <template #default="{ row }">
              <el-button type="primary" size="small" @click.stop="selectFund(row)">
                查看详情
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- 空状态 -->
      <div v-else-if="searched && !searching" class="empty-results">
        <el-empty description="未找到相关基金，请尝试其他关键词" />
      </div>

      <!-- 初始提示 -->
      <div v-else-if="!searched && !searching" class="initial-hint">
        <el-empty :image-size="120" description="">
          <template #description>
            <div class="hint-text">
              <p>输入基金代码（如 <el-tag size="small">510050</el-tag>）</p>
              <p>或基金名称（如 <el-tag size="small">华夏上证50ETF</el-tag>）</p>
              <p>即可查询基金详细信息</p>
            </div>
          </template>
        </el-empty>
      </div>
    </el-card>

    <!-- 详情加载中 -->
    <div v-if="detailLoading" class="detail-loading">
      <el-card class="loading-card" shadow="hover">
        <div class="loading-content">
          <el-icon class="loading-icon is-loading"><Loading /></el-icon>
          <p class="loading-text">正在获取 {{ selectedFund?.name }} 的详情数据...</p>
          <el-progress :percentage="detailProgress" :show-text="false" :stroke-width="8" class="loading-progress" />
          <p class="loading-hint">数据源：优先 AKShare，备用 Tushare</p>
        </div>
      </el-card>
    </div>

    <!-- 基金详情 -->
    <template v-if="detailLoaded && fundDetail">
      <!-- 基本信息 + 费率与规模 -->
      <el-row :gutter="24" class="detail-row">
        <!-- 基本信息 -->
        <el-col :span="12">
          <el-card class="detail-card" shadow="hover">
            <template #header>
              <div class="card-header">
                <h3>📋 基本信息</h3>
                <el-tag type="success" size="small">{{ fundDetail.ts_code }}</el-tag>
              </div>
            </template>
            <el-descriptions :column="1" border>
              <el-descriptions-item label="基金名称">{{ fundDetail.basic?.name || '-' }}</el-descriptions-item>
              <el-descriptions-item label="基金类型">{{ fundDetail.basic?.fund_type || '-' }}</el-descriptions-item>
              <el-descriptions-item label="管理人">{{ fundDetail.basic?.management || '-' }}</el-descriptions-item>
              <el-descriptions-item label="托管人">{{ fundDetail.basic?.custodian || '-' }}</el-descriptions-item>
              <el-descriptions-item label="市场">
                <el-tag v-if="fundDetail.basic?.market === 'E'" type="success" size="small">场内(ETF/LOF)</el-tag>
                <el-tag v-else type="info" size="small">场外</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="状态">
                <el-tag v-if="fundDetail.basic?.status === 'L'" type="success" size="small">存续</el-tag>
                <el-tag v-else-if="fundDetail.basic?.status === 'D'" type="danger" size="small">清盘</el-tag>
                <el-tag v-else type="info" size="small">{{ fundDetail.basic?.status || '-' }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="成立日期">{{ fundDetail.basic?.found_date || '-' }}</el-descriptions-item>
              <el-descriptions-item label="投资风格">{{ fundDetail.basic?.invest_type || '-' }}</el-descriptions-item>
            </el-descriptions>
          </el-card>
        </el-col>

        <!-- 费率与规模 -->
        <el-col :span="12">
          <el-card class="detail-card" shadow="hover">
            <template #header>
              <div class="card-header">
                <h3>💰 费率与规模</h3>
              </div>
            </template>
            <el-descriptions :column="1" border>
              <el-descriptions-item label="管理费">
                <span v-if="fundDetail.basic?.m_fee != null" class="fee-value">{{ fundDetail.basic.m_fee }}%</span>
                <span v-else>-</span>
              </el-descriptions-item>
              <el-descriptions-item label="托管费">
                <span v-if="fundDetail.basic?.c_fee != null" class="fee-value">{{ fundDetail.basic.c_fee }}%</span>
                <span v-else>-</span>
              </el-descriptions-item>
              <el-descriptions-item label="销售服务费">
                <span v-if="fundDetail.basic?.s_fee != null" class="fee-value">{{ fundDetail.basic.s_fee }}%</span>
                <span v-else>-</span>
              </el-descriptions-item>
              <el-descriptions-item label="申购费">
                <span v-if="fundDetail.basic?.p_fee != null" class="fee-value">{{ fundDetail.basic.p_fee }}%</span>
                <span v-else>-</span>
              </el-descriptions-item>
              <el-descriptions-item label="赎回费">
                <span v-if="fundDetail.basic?.r_fee != null" class="fee-value">{{ fundDetail.basic.r_fee }}%</span>
                <span v-else>-</span>
              </el-descriptions-item>
              <el-descriptions-item label="最新规模">
                <span v-if="fundDetail.latest_share?.fd_share" class="scale-value">{{ formatScale(fundDetail.latest_share.fd_share) }}</span>
                <span v-else-if="fundDetail.latest_share?.fd_amount" class="scale-value">{{ formatScale(fundDetail.latest_share.fd_amount) }}</span>
                <span v-else>-</span>
              </el-descriptions-item>
              <el-descriptions-item label="业绩比较基准">{{ fundDetail.basic?.benchmark || '-' }}</el-descriptions-item>
            </el-descriptions>
          </el-card>
        </el-col>
      </el-row>

      <!-- 最新净值 + 基金经理 -->
      <el-row :gutter="24" class="detail-row">
        <el-col :span="12">
          <el-card class="detail-card" shadow="hover">
            <template #header>
              <div class="card-header">
                <h3>📈 最新净值</h3>
              </div>
            </template>
            <div v-if="fundDetail.latest_nav" class="nav-info">
              <div class="nav-main">
                <div class="nav-value">{{ fundDetail.latest_nav.nav || '-' }}</div>
                <div class="nav-date">净值日期：{{ fundDetail.latest_nav.nav_date || '-' }}</div>
              </div>
              <div class="nav-change">
                <div class="change-item">
                  <span class="label">日涨跌幅</span>
                  <span :class="['value', getChangeClass(fundDetail.latest_nav.daily_return)]">
                    {{ formatPercent(fundDetail.latest_nav.daily_return) }}
                  </span>
                </div>
                <div class="change-item">
                  <span class="label">累计净值</span>
                  <span class="value">{{ fundDetail.latest_nav.acc_nav || '-' }}</span>
                </div>
              </div>
            </div>
            <el-empty v-else description="暂无净值数据" />
          </el-card>
        </el-col>

        <el-col :span="12">
          <el-card class="detail-card" shadow="hover">
            <template #header>
              <div class="card-header">
                <h3>👤 基金经理</h3>
              </div>
            </template>
            <div v-if="fundDetail.managers && fundDetail.managers.length > 0" class="manager-list">
              <div
                v-for="(manager, idx) in fundDetail.managers"
                :key="idx"
                class="manager-item"
              >
                <div class="manager-name">{{ manager.name || '-' }}</div>
                <div class="manager-info">
                  <el-tag v-if="manager.gender" size="small">{{ manager.gender }}</el-tag>
                  <span v-if="manager.birth_year">{{ manager.birth_year }}年生</span>
                  <span v-if="manager.edu">{{ manager.edu }}</span>
                  <span v-if="manager.begin_date">任职：{{ manager.begin_date }}</span>
                </div>
                <div v-if="manager.resume" class="manager-resume">{{ manager.resume }}</div>
              </div>
            </div>
            <el-empty v-else description="暂无基金经理数据" />
          </el-card>
        </el-col>
      </el-row>

      <!-- 去分析按钮 -->
      <div class="action-bar">
        <el-button
          type="primary"
          size="large"
          @click="goToAnalysis"
          class="analysis-btn"
        >
          <el-icon><TrendCharts /></el-icon>
          前往基金分析
        </el-button>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Search, TrendCharts, Loading } from '@element-plus/icons-vue'
import { analysisApi } from '@/api/analysis'

const router = useRouter()

const searchKeyword = ref('')
const searching = ref(false)
const searched = ref(false)
const searchResults = ref<any[]>([])
const selectedFund = ref<any>(null)
const fundDetail = ref<any>(null)
const detailLoading = ref(false)
const detailLoaded = ref(false)
const detailProgress = ref(0)

// 模拟进度条动画
let progressTimer: ReturnType<typeof setInterval> | null = null
const startProgress = () => {
  detailProgress.value = 0
  progressTimer = setInterval(() => {
    if (detailProgress.value < 90) {
      detailProgress.value += Math.random() * 15
      if (detailProgress.value > 90) detailProgress.value = 90
    }
  }, 300)
}
const stopProgress = () => {
  if (progressTimer) {
    clearInterval(progressTimer)
    progressTimer = null
  }
  detailProgress.value = 100
}

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
  fundDetail.value = null
  detailLoaded.value = false

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

// 选择基金并获取详情
const selectFund = async (row: any) => {
  selectedFund.value = row
  fundDetail.value = null
  detailLoaded.value = false
  detailLoading.value = true
  startProgress()

  try {
    const response = await analysisApi.getFundDetail(row.ts_code)
    if (response?.success && response.data) {
      fundDetail.value = response.data
      detailLoaded.value = true
      ElMessage.success(`「${row.name}」详情获取成功`)
    } else {
      ElMessage.warning(response?.message || '获取基金详情失败')
    }
  } catch (error: any) {
    console.error('获取基金详情失败:', error)
    ElMessage.error(error.message || '获取基金详情失败')
  } finally {
    stopProgress()
    detailLoading.value = false
  }
}

// 行样式
const getRowClassName = ({ row }: { row: any }) => {
  if (selectedFund.value && row.ts_code === selectedFund.value.ts_code) {
    return 'selected-row'
  }
  return ''
}

// 格式化规模
const formatScale = (share: number) => {
  if (!share) return '-'
  if (share >= 100000000) {
    return (share / 100000000).toFixed(2) + ' 亿份'
  }
  if (share >= 10000) {
    return (share / 10000).toFixed(2) + ' 万份'
  }
  return share.toFixed(2) + ' 份'
}

// 格式化涨跌幅
const formatPercent = (val: number) => {
  if (val === undefined || val === null) return '-'
  const sign = val >= 0 ? '+' : ''
  return `${sign}${(val * 100).toFixed(2)}%`
}

// 涨跌样式
const getChangeClass = (val: number) => {
  if (val === undefined || val === null) return ''
  return val >= 0 ? 'up' : 'down'
}

// 前往分析页面
const goToAnalysis = () => {
  if (!fundDetail.value) return
  const basic = fundDetail.value.basic || {}
  router.push({
    path: '/analysis/fund',
    query: {
      ts_code: fundDetail.value.ts_code,
      name: basic.name || '',
      fund_type: basic.fund_type || '',
      market: basic.market || '',
      management: basic.management || ''
    }
  })
}
</script>

<style lang="scss" scoped>
.fund-search {
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

  .search-card {
    border-radius: 16px;
    border: none;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
    margin-bottom: 24px;

    :deep(.el-card__header) {
      background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%);
      color: white;
      border-radius: 16px 16px 0 0;
      padding: 18px 24px;

      .card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;

        h3 {
          margin: 0;
          font-size: 17px;
          font-weight: 600;
        }
      }
    }

    :deep(.el-card__body) {
      padding: 24px;
    }

    .search-box {
      .search-input {
        :deep(.el-input__inner) {
          height: 52px;
          font-size: 15px;
          border-radius: 10px 0 0 10px;
        }
        :deep(.el-input-group__append) {
          border-radius: 0 10px 10px 0;
          background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%);
          color: white;
          border: none;
          padding: 0 24px;

          .el-button {
            color: white;
            font-weight: 500;
            font-size: 15px;
          }
        }
      }
    }

    .search-results {
      margin-top: 20px;

      :deep(.selected-row) {
        background-color: var(--el-color-primary-light-9) !important;
      }
    }

    .empty-results {
      margin-top: 40px;
    }

    .initial-hint {
      margin-top: 20px;

      .hint-text {
        text-align: center;
        color: #64748b;
        line-height: 2;
        font-size: 14px;

        p {
          margin: 4px 0;
        }
      }
    }
  }

  // 详情加载中
  .detail-loading {
    margin-bottom: 24px;

    .loading-card {
      border-radius: 16px;
      border: none;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);

      :deep(.el-card__body) {
        padding: 48px 24px;
      }

      .loading-content {
        display: flex;
        flex-direction: column;
        align-items: center;
        text-align: center;

        .loading-icon {
          font-size: 48px;
          color: #8b5cf6;
          margin-bottom: 16px;
        }

        .loading-text {
          font-size: 16px;
          font-weight: 600;
          color: #1a202c;
          margin: 0 0 20px 0;
        }

        .loading-progress {
          width: 320px;
          margin-bottom: 12px;
        }

        .loading-hint {
          font-size: 13px;
          color: #9ca3af;
          margin: 0;
        }
      }
    }
  }

  .detail-row {
    margin-bottom: 0 !important;

    .detail-card {
      border-radius: 16px;
      border: none;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
      margin-bottom: 24px;

      :deep(.el-card__header) {
        background: linear-gradient(135deg, #06b6d4 0%, #0891b2 100%);
        color: white;
        border-radius: 16px 16px 0 0;
        padding: 16px 20px;

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
        padding: 20px;
      }

      .fee-value {
        color: #f59e0b;
        font-weight: 600;
      }

      .scale-value {
        color: #10b981;
        font-weight: 600;
      }

      .nav-info {
        .nav-main {
          text-align: center;
          margin-bottom: 20px;

          .nav-value {
            font-size: 36px;
            font-weight: 700;
            color: #1a202c;
          }

          .nav-date {
            font-size: 13px;
            color: #64748b;
            margin-top: 4px;
          }
        }

        .nav-change {
          display: flex;
          justify-content: space-around;

          .change-item {
            text-align: center;

            .label {
              display: block;
              font-size: 12px;
              color: #9ca3af;
              margin-bottom: 4px;
            }

            .value {
              font-size: 18px;
              font-weight: 600;

              &.up {
                color: #ef4444;
              }

              &.down {
                color: #10b981;
              }
            }
          }
        }
      }

      .manager-list {
        .manager-item {
          padding: 12px 0;
          border-bottom: 1px solid #f3f4f6;

          &:last-child {
            border-bottom: none;
            padding-bottom: 0;
          }

          &:first-child {
            padding-top: 0;
          }

          .manager-name {
            font-size: 15px;
            font-weight: 600;
            color: #1a202c;
            margin-bottom: 6px;
          }

          .manager-info {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 13px;
            color: #64748b;
            margin-bottom: 6px;
            flex-wrap: wrap;
          }

          .manager-resume {
            font-size: 12px;
            color: #9ca3af;
            line-height: 1.6;
            display: -webkit-box;
            -webkit-line-clamp: 3;
            -webkit-box-orient: vertical;
            overflow: hidden;
          }
        }
      }
    }
  }

  .action-bar {
    display: flex;
    justify-content: center;
    margin-bottom: 24px;

    .analysis-btn {
      min-width: 240px;
      height: 52px;
      font-size: 17px;
      font-weight: 700;
      border-radius: 14px;
      background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%);
      border: none;
      box-shadow: 0 4px 15px rgba(139, 92, 246, 0.25);
      transition: all 0.3s ease;

      &:hover {
        transform: translateY(-3px);
        box-shadow: 0 12px 30px rgba(139, 92, 246, 0.4);
      }
    }
  }
}
</style>
