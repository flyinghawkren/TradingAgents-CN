<template>
  <div class="my-investment">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-content">
        <h1 class="page-title">
          <el-icon class="title-icon"><Wallet /></el-icon>
          <span>我的投资</span>
        </h1>
        <p class="page-description">
          管理我的投资，展示各类投资渠道中的资产分布
        </p>
      </div>
      <div class="header-stats">
        <div class="stat-item highlight">
          <div class="stat-value">{{ formatWan(totalAssets) }}万元</div>
          <div class="stat-label">总资产</div>
        </div>
        <div class="stat-item">
          <div class="stat-value">{{ holdings.length }}</div>
          <div class="stat-label">持仓股票</div>
        </div>
        <div class="stat-item">
          <div class="stat-value">{{ fundHoldings.length }}</div>
          <div class="stat-label">持仓基金</div>
        </div>
        <div class="stat-item">
          <div class="stat-value">2</div>
          <div class="stat-label">投资渠道</div>
        </div>
      </div>
    </div>

    <!-- 投资板块网格 -->
    <div class="investment-grid">
      <!-- 股票板块 — 全宽 -->
      <div class="investment-block stock-block">
        <div class="block-header">
          <div class="block-title-group">
            <div class="block-icon stock-icon">
              <el-icon><TrendCharts /></el-icon>
            </div>
            <div class="block-title-info">
              <h2 class="block-title">股票</h2>
              <span class="block-subtitle">{{ holdings.length }} 只持仓，{{ formatWan(stockTotalValue) }}万元</span>
            </div>
          </div>
          <div class="block-actions">
            <el-input
              v-model="searchKeyword"
              placeholder="搜索股票代码或名称"
              clearable
              size="small"
              class="search-input"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
            <el-button size="small" @click="refreshData">
              <el-icon><Refresh /></el-icon>
            </el-button>
            <el-button type="primary" size="small" @click="showAddDialog">
              <el-icon><Plus /></el-icon>
              添加
            </el-button>
          </div>
        </div>
        <div class="block-body">
          <el-table
            :data="filteredHoldings"
            v-loading="loading"
            size="small"
            class="modern-table"
          >
            <el-table-column prop="stock_code" label="股票代码" width="110">
              <template #default="{ row }">
                <el-link type="primary" @click="viewStockDetail(row)">
                  {{ row.stock_code }}
                </el-link>
              </template>
            </el-table-column>
            <el-table-column prop="stock_name" label="股票名称" width="130" />
            <el-table-column prop="quantity" label="持有数量" width="100" align="right" />
            <el-table-column prop="avg_price" label="买进均价" width="110" align="right">
              <template #default="{ row }">
                <span v-if="row.avg_price !== null && row.avg_price !== undefined">
                  ¥{{ formatPrice(row.avg_price) }}
                </span>
                <span v-else>-</span>
              </template>
            </el-table-column>
            <el-table-column prop="buy_date" label="买进时间" width="110">
              <template #default="{ row }">
                {{ formatDate(row.buy_date) }}
              </template>
            </el-table-column>
            <el-table-column prop="market" label="市场" width="70">
              <template #default="{ row }">
                <el-tag size="small" effect="plain">{{ row.market || 'A股' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="notes" label="备注" min-width="120" show-overflow-tooltip />
            <el-table-column label="操作" width="160" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" size="small" @click="editHolding(row)">
                  编辑
                </el-button>
                <el-button link type="primary" size="small" @click="analyzeHolding(row)">
                  分析
                </el-button>
                <el-button link type="danger" size="small" @click="removeHolding(row)">
                  移除
                </el-button>
              </template>
            </el-table-column>
          </el-table>
          <div v-if="!loading && holdings.length === 0" class="empty-state">
            <el-empty description="暂无持仓股票" :image-size="80">
              <el-button type="primary" size="small" @click="showAddDialog">
                添加第一只持仓股票
              </el-button>
            </el-empty>
          </div>
        </div>
      </div>

      <!-- 基金板块 — 全宽 -->
      <div class="investment-block">
        <div class="block-header">
          <div class="block-title-group">
            <div class="block-icon fund-icon">
              <el-icon><Money /></el-icon>
            </div>
            <div class="block-title-info">
              <h2 class="block-title">基金</h2>
              <span class="block-subtitle">{{ fundHoldings.length }} 只持仓，{{ formatWan(fundTotalValue) }}万元</span>
            </div>
          </div>
          <div class="block-actions">
            <el-input
              v-model="fundSearchKeyword"
              placeholder="搜索基金代码或名称"
              clearable
              size="small"
              class="search-input"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
            <el-button size="small" @click="refreshFundData">
              <el-icon><Refresh /></el-icon>
            </el-button>
            <el-button type="primary" size="small" @click="showAddFundDialog">
              <el-icon><Plus /></el-icon>
              添加
            </el-button>
          </div>
        </div>
        <div class="block-body">
          <el-table
            :data="filteredFundHoldings"
            v-loading="fundLoading"
            size="small"
            class="modern-table"
          >
            <el-table-column prop="fund_code" label="基金代码" width="110">
              <template #default="{ row }">
                <el-link type="primary" @click="viewFundDetail(row)">
                  {{ row.fund_code }}
                </el-link>
              </template>
            </el-table-column>
            <el-table-column prop="fund_name" label="基金名称" width="150" />
            <el-table-column prop="fund_type" label="类型" width="90">
              <template #default="{ row }">
                <el-tag size="small" effect="plain">{{ row.fund_type || '混合型' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="quantity" label="持有份额" width="110" align="right">
              <template #default="{ row }">
                {{ formatShares(row.quantity) }}
              </template>
            </el-table-column>
            <el-table-column prop="avg_nav" label="买入净值" width="110" align="right">
              <template #default="{ row }">
                <span v-if="row.avg_nav !== null && row.avg_nav !== undefined">
                  ¥{{ formatPrice(row.avg_nav) }}
                </span>
                <span v-else>-</span>
              </template>
            </el-table-column>
            <el-table-column prop="buy_date" label="买进时间" width="110">
              <template #default="{ row }">
                {{ formatDate(row.buy_date) }}
              </template>
            </el-table-column>
            <el-table-column prop="notes" label="备注" min-width="120" show-overflow-tooltip />
            <el-table-column label="操作" width="160" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" size="small" @click="editFundHolding(row)">
                  编辑
                </el-button>
                <el-button link type="primary" size="small" @click="analyzeFundHolding(row)">
                  分析
                </el-button>
                <el-button link type="danger" size="small" @click="removeFundHolding(row)">
                  移除
                </el-button>
              </template>
            </el-table-column>
          </el-table>
          <div v-if="!fundLoading && fundHoldings.length === 0" class="empty-state">
            <el-empty description="暂无持仓基金" :image-size="80">
              <el-button type="primary" size="small" @click="showAddFundDialog">
                添加第一只持仓基金
              </el-button>
            </el-empty>
          </div>
        </div>
      </div>
    </div>

    <!-- 添加持仓股票对话框 -->
    <el-dialog v-model="addDialogVisible" title="添加持仓股票" width="500px">
      <el-form :model="addForm" :rules="addRules" ref="addFormRef" label-width="100px">
        <el-form-item label="市场类型" prop="market">
          <el-select v-model="addForm.market">
            <el-option label="A股" value="A股" />
            <el-option label="港股" value="港股" />
            <el-option label="美股" value="美股" />
          </el-select>
        </el-form-item>
        <el-form-item label="股票代码" prop="stock_code">
          <el-input v-model="addForm.stock_code" placeholder="输入股票代码" @blur="fetchStockInfo" />
        </el-form-item>
        <el-form-item label="股票名称" prop="stock_name">
          <el-input v-model="addForm.stock_name" placeholder="股票名称" />
        </el-form-item>
        <el-form-item label="持有数量" prop="quantity">
          <el-input-number v-model="addForm.quantity" :min="1" :precision="0" controls-position="right" style="width: 100%;" />
        </el-form-item>
        <el-form-item label="买进均价" prop="avg_price">
          <el-input-number v-model="addForm.avg_price" :min="0" :precision="3" controls-position="right" style="width: 100%;" />
        </el-form-item>
        <el-form-item label="买进时间" prop="buy_date">
          <el-date-picker v-model="addForm.buy_date" type="date" placeholder="选择买进日期" style="width: 100%;" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="addForm.notes" type="textarea" :rows="2" placeholder="可选：添加备注信息" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleAddHolding" :loading="addLoading">添加</el-button>
      </template>
    </el-dialog>

    <!-- 编辑持仓对话框 -->
    <el-dialog v-model="editDialogVisible" title="编辑持仓" width="500px">
      <el-form :model="editForm" ref="editFormRef" label-width="100px">
        <el-form-item label="股票">
          <div>{{ editForm.stock_code }}｜{{ editForm.stock_name }}</div>
        </el-form-item>
        <el-form-item label="持有数量">
          <el-input-number v-model="editForm.quantity" :min="1" :precision="0" controls-position="right" style="width: 100%;" />
        </el-form-item>
        <el-form-item label="买进均价">
          <el-input-number v-model="editForm.avg_price" :min="0" :precision="3" controls-position="right" style="width: 100%;" />
        </el-form-item>
        <el-form-item label="买进时间">
          <el-date-picker v-model="editForm.buy_date" type="date" placeholder="选择买进日期" style="width: 100%;" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="editForm.notes" type="textarea" :rows="2" placeholder="可选：添加备注信息" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleEditHolding" :loading="editLoading">保存</el-button>
      </template>
    </el-dialog>

    <!-- 添加基金持仓对话框 -->
    <el-dialog v-model="addFundDialogVisible" title="添加基金持仓" width="500px">
      <el-form :model="addFundForm" :rules="addFundRules" ref="addFundFormRef" label-width="100px">
        <el-form-item label="基金代码" prop="fund_code">
          <el-input v-model="addFundForm.fund_code" placeholder="输入基金代码，如 000001" />
        </el-form-item>
        <el-form-item label="基金名称" prop="fund_name">
          <el-input v-model="addFundForm.fund_name" placeholder="基金名称" />
        </el-form-item>
        <el-form-item label="基金类型" prop="fund_type">
          <el-select v-model="addFundForm.fund_type" style="width: 100%;">
            <el-option label="混合型" value="混合型" />
            <el-option label="股票型" value="股票型" />
            <el-option label="债券型" value="债券型" />
            <el-option label="指数型" value="指数型" />
            <el-option label="QDII" value="QDII" />
            <el-option label="FOF" value="FOF" />
            <el-option label="货币型" value="货币型" />
          </el-select>
        </el-form-item>
        <el-form-item label="持有份额" prop="quantity">
          <el-input-number v-model="addFundForm.quantity" :min="0" :precision="2" controls-position="right" style="width: 100%;" />
        </el-form-item>
        <el-form-item label="买入净值" prop="avg_nav">
          <el-input-number v-model="addFundForm.avg_nav" :min="0" :precision="4" controls-position="right" style="width: 100%;" />
        </el-form-item>
        <el-form-item label="买进时间" prop="buy_date">
          <el-date-picker v-model="addFundForm.buy_date" type="date" placeholder="选择买进日期" style="width: 100%;" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="addFundForm.notes" type="textarea" :rows="2" placeholder="可选：添加备注信息" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addFundDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleAddFundHolding" :loading="addFundLoading">添加</el-button>
      </template>
    </el-dialog>

    <!-- 编辑基金持仓对话框 -->
    <el-dialog v-model="editFundDialogVisible" title="编辑基金持仓" width="500px">
      <el-form :model="editFundForm" ref="editFundFormRef" label-width="100px">
        <el-form-item label="基金">
          <div>{{ editFundForm.fund_code }}｜{{ editFundForm.fund_name }}</div>
        </el-form-item>
        <el-form-item label="持有份额">
          <el-input-number v-model="editFundForm.quantity" :min="0" :precision="2" controls-position="right" style="width: 100%;" />
        </el-form-item>
        <el-form-item label="买入净值">
          <el-input-number v-model="editFundForm.avg_nav" :min="0" :precision="4" controls-position="right" style="width: 100%;" />
        </el-form-item>
        <el-form-item label="买进时间">
          <el-date-picker v-model="editFundForm.buy_date" type="date" placeholder="选择买进日期" style="width: 100%;" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="editFundForm.notes" type="textarea" :rows="2" placeholder="可选：添加备注信息" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editFundDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleEditFundHolding" :loading="editFundLoading">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  Wallet,
  Search,
  Refresh,
  Plus,
  TrendCharts,
  Money
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { portfolioApi, fundPortfolioApi, type PortfolioHolding, type FundHolding } from '@/api/portfolio'

const router = useRouter()

// ==================== 股票持仓 ====================
const loading = ref(false)
const searchKeyword = ref('')
const holdings = ref<PortfolioHolding[]>([])

// 添加对话框
const addDialogVisible = ref(false)
const addLoading = ref(false)
const addFormRef = ref()
const addForm = ref({
  market: 'A股',
  stock_code: '',
  stock_name: '',
  quantity: 100,
  avg_price: undefined as number | undefined,
  buy_date: '',
  notes: ''
})

const addRules = {
  market: [{ required: true, message: '请选择市场类型', trigger: 'change' }],
  stock_code: [{ required: true, message: '请输入股票代码', trigger: 'blur' }],
  stock_name: [{ required: true, message: '请输入股票名称', trigger: 'blur' }],
  quantity: [{ required: true, message: '请输入持有数量', trigger: 'blur' }],
  avg_price: [{ required: true, message: '请输入买进均价', trigger: 'blur' }],
  buy_date: [{ required: true, message: '请选择买进时间', trigger: 'change' }]
}

// 编辑对话框
const editDialogVisible = ref(false)
const editLoading = ref(false)
const editFormRef = ref()
const editForm = ref({
  id: '',
  stock_code: '',
  stock_name: '',
  quantity: 100,
  avg_price: undefined as number | undefined,
  buy_date: '',
  notes: ''
})

// 过滤后的持仓列表
const filteredHoldings = computed(() => {
  let result = holdings.value
  if (searchKeyword.value) {
    const keyword = searchKeyword.value.toLowerCase()
    result = result.filter(
      h =>
        h.stock_code.toLowerCase().includes(keyword) ||
        h.stock_name.toLowerCase().includes(keyword)
    )
  }
  return result
})

// 股票总资产（元）
const stockTotalValue = computed(() => {
  return holdings.value.reduce((sum, h) => {
    const price = h.avg_price || 0
    return sum + h.quantity * price
  }, 0)
})

// ==================== 基金持仓 ====================
const fundLoading = ref(false)
const fundSearchKeyword = ref('')
const fundHoldings = ref<FundHolding[]>([])

// 基金添加对话框
const addFundDialogVisible = ref(false)
const addFundLoading = ref(false)
const addFundFormRef = ref()
const addFundForm = ref({
  fund_code: '',
  fund_name: '',
  fund_type: '混合型',
  quantity: 100,
  avg_nav: undefined as number | undefined,
  buy_date: '',
  notes: ''
})

const addFundRules = {
  fund_code: [{ required: true, message: '请输入基金代码', trigger: 'blur' }],
  fund_name: [{ required: true, message: '请输入基金名称', trigger: 'blur' }],
  fund_type: [{ required: true, message: '请选择基金类型', trigger: 'change' }],
  quantity: [{ required: true, message: '请输入持有份额', trigger: 'blur' }],
  avg_nav: [{ required: true, message: '请输入买入净值', trigger: 'blur' }],
  buy_date: [{ required: true, message: '请选择买进时间', trigger: 'change' }]
}

// 基金编辑对话框
const editFundDialogVisible = ref(false)
const editFundLoading = ref(false)
const editFundFormRef = ref()
const editFundForm = ref({
  id: '',
  fund_code: '',
  fund_name: '',
  quantity: 100,
  avg_nav: undefined as number | undefined,
  buy_date: '',
  notes: ''
})

// 过滤后的基金持仓列表
const filteredFundHoldings = computed(() => {
  let result = fundHoldings.value
  if (fundSearchKeyword.value) {
    const keyword = fundSearchKeyword.value.toLowerCase()
    result = result.filter(
      h =>
        h.fund_code.toLowerCase().includes(keyword) ||
        h.fund_name.toLowerCase().includes(keyword)
    )
  }
  return result
})

// 基金总资产（元）
const fundTotalValue = computed(() => {
  return fundHoldings.value.reduce((sum, h) => {
    const nav = h.avg_nav || 0
    return sum + h.quantity * nav
  }, 0)
})

// 总资产
const totalAssets = computed(() => {
  return stockTotalValue.value + fundTotalValue.value
})

// ==================== 股票 CRUD ====================

const loadHoldings = async () => {
  loading.value = true
  try {
    const res = await portfolioApi.list()
    if (res.success && res.data) {
      holdings.value = res.data
    } else {
      holdings.value = []
    }
  } catch (error) {
    console.error('加载持仓失败:', error)
    ElMessage.error('加载持仓数据失败')
    holdings.value = []
  } finally {
    loading.value = false
  }
}

const refreshData = () => {
  loadHoldings()
}

const showAddDialog = () => {
  addForm.value = {
    market: 'A股',
    stock_code: '',
    stock_name: '',
    quantity: 100,
    avg_price: undefined,
    buy_date: '',
    notes: ''
  }
  addDialogVisible.value = true
}

const fetchStockInfo = async () => {
  if (addForm.value.stock_code && !addForm.value.stock_name) {
    console.log('股票代码变更:', addForm.value.stock_code)
  }
}

const handleAddHolding = async () => {
  const valid = await addFormRef.value?.validate().catch(() => false)
  if (!valid) return

  addLoading.value = true
  try {
    const res = await portfolioApi.add({
      stock_code: addForm.value.stock_code,
      stock_name: addForm.value.stock_name,
      market: addForm.value.market,
      quantity: addForm.value.quantity,
      avg_price: addForm.value.avg_price || 0,
      buy_date: addForm.value.buy_date,
      notes: addForm.value.notes
    })

    if (res.success) {
      ElMessage.success('添加持仓成功')
      addDialogVisible.value = false
      await loadHoldings()
    } else {
      ElMessage.error(res.message || '添加持仓失败')
    }
  } catch (error: any) {
    console.error('添加持仓失败:', error)
    ElMessage.error(error?.response?.data?.detail || '添加持仓失败')
  } finally {
    addLoading.value = false
  }
}

const editHolding = (row: PortfolioHolding) => {
  editForm.value = {
    id: row.id,
    stock_code: row.stock_code,
    stock_name: row.stock_name,
    quantity: row.quantity,
    avg_price: row.avg_price,
    buy_date: row.buy_date,
    notes: row.notes
  }
  editDialogVisible.value = true
}

const handleEditHolding = async () => {
  editLoading.value = true
  try {
    const res = await portfolioApi.update(editForm.value.id, {
      quantity: editForm.value.quantity,
      avg_price: editForm.value.avg_price,
      buy_date: editForm.value.buy_date,
      notes: editForm.value.notes
    })

    if (res.success) {
      ElMessage.success('更新持仓成功')
      editDialogVisible.value = false
      await loadHoldings()
    } else {
      ElMessage.error(res.message || '更新持仓失败')
    }
  } catch (error: any) {
    console.error('更新持仓失败:', error)
    ElMessage.error(error?.response?.data?.detail || '更新持仓失败')
  } finally {
    editLoading.value = false
  }
}

const removeHolding = async (row: PortfolioHolding) => {
  try {
    await ElMessageBox.confirm(
      `确定要移除 ${row.stock_name}(${row.stock_code}) 的持仓记录吗？`,
      '确认移除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    const res = await portfolioApi.remove(row.id)
    if (res.success) {
      ElMessage.success('移除持仓成功')
      await loadHoldings()
    } else {
      ElMessage.error(res.message || '移除持仓失败')
    }
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('移除持仓失败:', error)
      ElMessage.error(error?.response?.data?.detail || '移除持仓失败')
    }
  }
}

const analyzeHolding = (row: PortfolioHolding) => {
  router.push(`/analysis/single?stock_code=${row.stock_code}`)
}

const viewStockDetail = (row: PortfolioHolding) => {
  router.push(`/analysis/single?stock_code=${row.stock_code}`)
}

// ==================== 基金 CRUD ====================

const loadFundHoldings = async () => {
  fundLoading.value = true
  try {
    const res = await fundPortfolioApi.list()
    if (res.success && res.data) {
      fundHoldings.value = res.data
    } else {
      fundHoldings.value = []
    }
  } catch (error) {
    console.error('加载基金持仓失败:', error)
    ElMessage.error('加载基金持仓数据失败')
    fundHoldings.value = []
  } finally {
    fundLoading.value = false
  }
}

const refreshFundData = () => {
  loadFundHoldings()
}

const showAddFundDialog = () => {
  addFundForm.value = {
    fund_code: '',
    fund_name: '',
    fund_type: '混合型',
    quantity: 100,
    avg_nav: undefined,
    buy_date: '',
    notes: ''
  }
  addFundDialogVisible.value = true
}

const handleAddFundHolding = async () => {
  const valid = await addFundFormRef.value?.validate().catch(() => false)
  if (!valid) return

  addFundLoading.value = true
  try {
    const res = await fundPortfolioApi.add({
      fund_code: addFundForm.value.fund_code,
      fund_name: addFundForm.value.fund_name,
      fund_type: addFundForm.value.fund_type,
      quantity: addFundForm.value.quantity,
      avg_nav: addFundForm.value.avg_nav || 0,
      buy_date: addFundForm.value.buy_date,
      notes: addFundForm.value.notes
    })

    if (res.success) {
      ElMessage.success('添加基金持仓成功')
      addFundDialogVisible.value = false
      await loadFundHoldings()
    } else {
      ElMessage.error(res.message || '添加基金持仓失败')
    }
  } catch (error: any) {
    console.error('添加基金持仓失败:', error)
    ElMessage.error(error?.response?.data?.detail || '添加基金持仓失败')
  } finally {
    addFundLoading.value = false
  }
}

const editFundHolding = (row: FundHolding) => {
  editFundForm.value = {
    id: row.id,
    fund_code: row.fund_code,
    fund_name: row.fund_name,
    quantity: row.quantity,
    avg_nav: row.avg_nav,
    buy_date: row.buy_date,
    notes: row.notes
  }
  editFundDialogVisible.value = true
}

const handleEditFundHolding = async () => {
  editFundLoading.value = true
  try {
    const res = await fundPortfolioApi.update(editFundForm.value.id, {
      quantity: editFundForm.value.quantity,
      avg_nav: editFundForm.value.avg_nav,
      buy_date: editFundForm.value.buy_date,
      notes: editFundForm.value.notes
    })

    if (res.success) {
      ElMessage.success('更新基金持仓成功')
      editFundDialogVisible.value = false
      await loadFundHoldings()
    } else {
      ElMessage.error(res.message || '更新基金持仓失败')
    }
  } catch (error: any) {
    console.error('更新基金持仓失败:', error)
    ElMessage.error(error?.response?.data?.detail || '更新基金持仓失败')
  } finally {
    editFundLoading.value = false
  }
}

const removeFundHolding = async (row: FundHolding) => {
  try {
    await ElMessageBox.confirm(
      `确定要移除 ${row.fund_name}(${row.fund_code}) 的基金持仓记录吗？`,
      '确认移除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    const res = await fundPortfolioApi.remove(row.id)
    if (res.success) {
      ElMessage.success('移除基金持仓成功')
      await loadFundHoldings()
    } else {
      ElMessage.error(res.message || '移除基金持仓失败')
    }
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('移除基金持仓失败:', error)
      ElMessage.error(error?.response?.data?.detail || '移除基金持仓失败')
    }
  }
}

const analyzeFundHolding = (row: FundHolding) => {
  router.push(`/analysis/fund?ts_code=${row.fund_code}&name=${encodeURIComponent(row.fund_name)}`)
}

const viewFundDetail = (row: FundHolding) => {
  router.push(`/analysis/fund?ts_code=${row.fund_code}&name=${encodeURIComponent(row.fund_name)}`)
}

// ==================== 格式化 ====================

const formatPrice = (price: number) => {
  return price.toFixed(3)
}

const formatShares = (shares: number) => {
  return shares.toFixed(2)
}

const formatDate = (date: string) => {
  if (!date) return '-'
  return date
}

const formatWan = (value: number) => {
  if (value === 0) return '0'
  const wan = value / 10000
  if (wan < 1) {
    return wan.toFixed(2)
  }
  if (wan >= 100) {
    return wan.toFixed(1)
  }
  return wan.toFixed(2)
}

// 生命周期
onMounted(() => {
  loadHoldings()
  loadFundHoldings()
})
</script>

<style lang="scss" scoped>
.my-investment {
  .page-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 28px;
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

    .header-stats {
      display: flex;
      gap: 32px;

      .stat-item {
        text-align: center;
        padding: 0 16px;
        position: relative;

        &:not(:last-child)::after {
          content: '';
          position: absolute;
          right: 0;
          top: 50%;
          transform: translateY(-50%);
          width: 1px;
          height: 24px;
          background: var(--el-border-color-lighter);
        }

        &.highlight {
          .stat-value {
            font-size: 28px;
            color: var(--el-color-danger);
          }
        }

        .stat-value {
          font-size: 22px;
          font-weight: 700;
          color: var(--el-color-primary);
          line-height: 1.2;
        }

        .stat-label {
          font-size: 12px;
          color: var(--el-text-color-secondary);
          margin-top: 4px;
        }
      }
    }
  }

  .investment-grid {
    display: flex;
    flex-direction: column;
    gap: 20px;

    .investment-row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 20px;

      @media (max-width: 992px) {
        grid-template-columns: 1fr;
      }
    }

    .investment-block {
      background: var(--el-bg-color);
      border-radius: 12px;
      border: 1px solid var(--el-border-color-lighter);
      overflow: hidden;
      transition: box-shadow 0.3s ease, transform 0.2s ease;

      &:hover {
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06);
      }

      &.stock-block {
        .block-icon.stock-icon {
          background: linear-gradient(135deg, #409eff 0%, #67c23a 100%);
          color: #fff;
        }
      }

      .block-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 16px 20px;
        border-bottom: 1px solid var(--el-border-color-lighter);
        background: var(--el-fill-color-light);

        .block-title-group {
          display: flex;
          align-items: center;
          gap: 12px;

          .block-icon {
            width: 40px;
            height: 40px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            flex-shrink: 0;

            &.fund-icon {
              background: linear-gradient(135deg, #e6a23c 0%, #f89898 100%);
              color: #fff;
            }
          }

          .block-title-info {
            .block-title {
              font-size: 16px;
              font-weight: 600;
              margin: 0;
              color: var(--el-text-color-primary);
            }

            .block-subtitle {
              font-size: 12px;
              color: var(--el-text-color-secondary);
            }
          }
        }

        .block-actions {
          display: flex;
          align-items: center;
          gap: 8px;

          .search-input {
            width: 200px;
          }
        }
      }

      .block-body {
        padding: 0;

        &.compact {
          padding: 32px 24px;
        }

        .modern-table {
          --el-table-header-bg-color: var(--el-fill-color-light);
          --el-table-header-text-color: var(--el-text-color-regular);
          --el-table-row-hover-bg-color: var(--el-fill-color-lighter);

          :deep(th.el-table__cell) {
            font-weight: 600;
            font-size: 12px;
            padding: 10px 0;
          }

          :deep(td.el-table__cell) {
            font-size: 13px;
            padding: 10px 0;
          }
        }

        .empty-state {
          padding: 32px 0;
        }

        .placeholder-content {
          text-align: center;

          .placeholder-icon {
            color: var(--el-border-color);
            margin-bottom: 12px;
          }

          .placeholder-title {
            font-size: 15px;
            font-weight: 600;
            color: var(--el-text-color-primary);
            margin: 0 0 8px 0;
          }

          .placeholder-desc {
            font-size: 13px;
            color: var(--el-text-color-secondary);
            margin: 0 0 20px 0;
            line-height: 1.6;
            max-width: 320px;
            margin-left: auto;
            margin-right: auto;
          }
        }
      }
    }
  }
}
</style>
