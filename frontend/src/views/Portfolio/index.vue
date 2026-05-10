<template>
  <div class="portfolio">
    <div class="page-header">
      <h1 class="page-title">
        <el-icon><Wallet /></el-icon>
        我的投资组合
      </h1>
      <p class="page-description">
        管理您持有的股票仓位
      </p>
    </div>

    <!-- 操作栏 -->
    <el-card class="action-card" shadow="never">
      <el-row :gutter="16" align="middle">
        <el-col :span="8">
          <el-input
            v-model="searchKeyword"
            placeholder="搜索股票代码或名称"
            clearable
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </el-col>

        <el-col :span="16">
          <div class="action-buttons" style="text-align: right;">
            <el-button @click="refreshData">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
            <el-button type="primary" @click="showAddDialog">
              <el-icon><Plus /></el-icon>
              添加持仓股票
            </el-button>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- 持仓列表 -->
    <el-card class="portfolio-list-card" shadow="never">
      <el-table
        :data="filteredHoldings"
        v-loading="loading"
        style="width: 100%"
      >
        <el-table-column prop="stock_code" label="股票代码" width="120">
          <template #default="{ row }">
            <el-link type="primary" @click="viewStockDetail(row)">
              {{ row.stock_code }}
            </el-link>
          </template>
        </el-table-column>

        <el-table-column prop="stock_name" label="股票名称" width="150" />

        <el-table-column prop="quantity" label="持有数量" width="120">
          <template #default="{ row }">
            {{ row.quantity }}
          </template>
        </el-table-column>

        <el-table-column prop="avg_price" label="买进均价" width="120">
          <template #default="{ row }">
            <span v-if="row.avg_price !== null && row.avg_price !== undefined">
              ¥{{ formatPrice(row.avg_price) }}
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>

        <el-table-column prop="buy_date" label="买进时间" width="140">
          <template #default="{ row }">
            {{ formatDate(row.buy_date) }}
          </template>
        </el-table-column>

        <el-table-column prop="market" label="市场" width="80">
          <template #default="{ row }">
            {{ row.market || 'A股' }}
          </template>
        </el-table-column>

        <el-table-column prop="notes" label="备注" min-width="150">
          <template #default="{ row }">
            {{ row.notes || '-' }}
          </template>
        </el-table-column>

        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button
              type="text"
              size="small"
              @click="editHolding(row)"
            >
              编辑
            </el-button>
            <el-button
              type="text"
              size="small"
              @click="analyzeHolding(row)"
            >
              分析
            </el-button>
            <el-button
              type="text"
              size="small"
              @click="removeHolding(row)"
              style="color: #f56c6c;"
            >
              移除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 空状态 -->
      <div v-if="!loading && holdings.length === 0" class="empty-state">
        <el-empty description="暂无持仓股票">
          <el-button type="primary" @click="showAddDialog">
            添加第一只持仓股票
          </el-button>
        </el-empty>
      </div>
    </el-card>

    <!-- 添加持仓股票对话框 -->
    <el-dialog
      v-model="addDialogVisible"
      title="添加持仓股票"
      width="500px"
    >
      <el-form :model="addForm" :rules="addRules" ref="addFormRef" label-width="100px">
        <el-form-item label="市场类型" prop="market">
          <el-select v-model="addForm.market">
            <el-option label="A股" value="A股" />
            <el-option label="港股" value="港股" />
            <el-option label="美股" value="美股" />
          </el-select>
        </el-form-item>

        <el-form-item label="股票代码" prop="stock_code">
          <el-input
            v-model="addForm.stock_code"
            placeholder="输入股票代码"
            @blur="fetchStockInfo"
          />
        </el-form-item>

        <el-form-item label="股票名称" prop="stock_name">
          <el-input v-model="addForm.stock_name" placeholder="股票名称" />
        </el-form-item>

        <el-form-item label="持有数量" prop="quantity">
          <el-input-number
            v-model="addForm.quantity"
            :min="1"
            :precision="0"
            controls-position="right"
            style="width: 100%;"
          />
        </el-form-item>

        <el-form-item label="买进均价" prop="avg_price">
          <el-input-number
            v-model="addForm.avg_price"
            :min="0"
            :precision="3"
            controls-position="right"
            style="width: 100%;"
          />
        </el-form-item>

        <el-form-item label="买进时间" prop="buy_date">
          <el-date-picker
            v-model="addForm.buy_date"
            type="date"
            placeholder="选择买进日期"
            style="width: 100%;"
            value-format="YYYY-MM-DD"
          />
        </el-form-item>

        <el-form-item label="备注">
          <el-input
            v-model="addForm.notes"
            type="textarea"
            :rows="2"
            placeholder="可选：添加备注信息"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="addDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleAddHolding" :loading="addLoading">
          添加
        </el-button>
      </template>
    </el-dialog>

    <!-- 编辑持仓对话框 -->
    <el-dialog
      v-model="editDialogVisible"
      title="编辑持仓"
      width="500px"
    >
      <el-form :model="editForm" ref="editFormRef" label-width="100px">
        <el-form-item label="股票">
          <div>{{ editForm.stock_code }}｜{{ editForm.stock_name }}</div>
        </el-form-item>

        <el-form-item label="持有数量">
          <el-input-number
            v-model="editForm.quantity"
            :min="1"
            :precision="0"
            controls-position="right"
            style="width: 100%;"
          />
        </el-form-item>

        <el-form-item label="买进均价">
          <el-input-number
            v-model="editForm.avg_price"
            :min="0"
            :precision="3"
            controls-position="right"
            style="width: 100%;"
          />
        </el-form-item>

        <el-form-item label="买进时间">
          <el-date-picker
            v-model="editForm.buy_date"
            type="date"
            placeholder="选择买进日期"
            style="width: 100%;"
            value-format="YYYY-MM-DD"
          />
        </el-form-item>

        <el-form-item label="备注">
          <el-input
            v-model="editForm.notes"
            type="textarea"
            :rows="2"
            placeholder="可选：添加备注信息"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleEditHolding" :loading="editLoading">
          保存
        </el-button>
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
  Plus
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()

// 响应式数据
const loading = ref(false)
const searchKeyword = ref('')
const holdings = ref<any[]>([])

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

// Mock 数据（后端接口实现后替换为真实请求）
const loadHoldings = async () => {
  loading.value = true
  try {
    // TODO: 替换为真实 API 调用
    // const res = await portfolioApi.list()
    // holdings.value = res.data || []

    // 临时 mock 数据，用于页面展示
    holdings.value = [
      {
        id: '1',
        stock_code: '000001',
        stock_name: '平安银行',
        quantity: 1000,
        avg_price: 10.500,
        buy_date: '2024-03-15',
        market: 'A股',
        notes: '长期持有'
      },
      {
        id: '2',
        stock_code: '600519',
        stock_name: '贵州茅台',
        quantity: 50,
        avg_price: 1680.000,
        buy_date: '2024-01-20',
        market: 'A股',
        notes: ''
      }
    ]
  } catch (error) {
    console.error('加载持仓失败:', error)
    ElMessage.error('加载持仓数据失败')
  } finally {
    loading.value = false
  }
}

const refreshData = () => {
  loadHoldings()
}

// 添加持仓
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
  // TODO: 根据股票代码自动获取股票名称
  if (addForm.value.stock_code && !addForm.value.stock_name) {
    // 临时 mock：假设根据代码推断名称
    const code = addForm.value.stock_code
    if (code === '000001') addForm.value.stock_name = '平安银行'
    else if (code === '600519') addForm.value.stock_name = '贵州茅台'
  }
}

const handleAddHolding = async () => {
  const valid = await addFormRef.value?.validate().catch(() => false)
  if (!valid) return

  addLoading.value = true
  try {
    // TODO: 调用后端 API 添加持仓
    // await portfolioApi.add(addForm.value)

    // 临时：直接添加到本地列表
    holdings.value.push({
      id: String(Date.now()),
      ...addForm.value
    })

    ElMessage.success('添加持仓成功')
    addDialogVisible.value = false
  } catch (error) {
    console.error('添加持仓失败:', error)
    ElMessage.error('添加持仓失败')
  } finally {
    addLoading.value = false
  }
}

// 编辑持仓
const editHolding = (row: any) => {
  editForm.value = { ...row }
  editDialogVisible.value = true
}

const handleEditHolding = async () => {
  editLoading.value = true
  try {
    // TODO: 调用后端 API 更新持仓
    // await portfolioApi.update(editForm.value.id, editForm.value)

    // 临时：更新本地列表
    const idx = holdings.value.findIndex(h => h.id === editForm.value.id)
    if (idx !== -1) {
      holdings.value[idx] = { ...editForm.value }
    }

    ElMessage.success('更新持仓成功')
    editDialogVisible.value = false
  } catch (error) {
    console.error('更新持仓失败:', error)
    ElMessage.error('更新持仓失败')
  } finally {
    editLoading.value = false
  }
}

// 移除持仓
const removeHolding = async (row: any) => {
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

    // TODO: 调用后端 API 删除持仓
    // await portfolioApi.delete(row.id)

    // 临时：从本地列表移除
    holdings.value = holdings.value.filter(h => h.id !== row.id)
    ElMessage.success('移除持仓成功')
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('移除持仓失败:', error)
      ElMessage.error('移除持仓失败')
    }
  }
}

// 分析持仓股票
const analyzeHolding = (row: any) => {
  router.push(`/analysis/single?stock_code=${row.stock_code}`)
}

// 查看股票详情
const viewStockDetail = (row: any) => {
  router.push(`/analysis/single?stock_code=${row.stock_code}`)
}

// 格式化
const formatPrice = (price: number) => {
  return price.toFixed(3)
}

const formatDate = (date: string) => {
  if (!date) return '-'
  return date
}

// 生命周期
onMounted(() => {
  loadHoldings()
})
</script>

<style lang="scss" scoped>
.portfolio {
  .page-header {
    margin-bottom: 24px;

    .page-title {
      font-size: 24px;
      font-weight: 600;
      margin: 0 0 8px 0;
      display: flex;
      align-items: center;
      gap: 12px;

      .el-icon {
        color: var(--el-color-primary);
      }
    }

    .page-description {
      color: var(--el-text-color-secondary);
      margin: 0;
    }
  }

  .action-card {
    margin-bottom: 24px;

    .action-buttons {
      display: flex;
      gap: 12px;
      justify-content: flex-end;
    }
  }

  .portfolio-list-card {
    .empty-state {
      padding: 40px 0;
    }
  }
}
</style>
