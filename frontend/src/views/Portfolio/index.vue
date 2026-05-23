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
          <div class="stat-value">{{ cashList.length }}</div>
          <div class="stat-label">现金账户</div>
        </div>
        <div class="stat-item">
          <div class="stat-value">{{ assetList.length }}</div>
          <div class="stat-label">实物资产</div>
        </div>
      </div>
    </div>

    <!-- 投资偏好栏 -->
    <div class="preference-bar">
      <div class="preference-bar-content">
        <div class="preference-label">
          <el-icon><Opportunity /></el-icon>
          <span>投资偏好</span>
        </div>
        <el-select
          v-model="investmentPreference"
          placeholder="选择您的投资风险偏好"
          clearable
          @change="onPreferenceChange"
          class="preference-select"
        >
          <el-option label="保守型" value="保守型" />
          <el-option label="谨慎型" value="谨慎型" />
          <el-option label="稳健型" value="稳健型" />
          <el-option label="进取型" value="进取型" />
          <el-option label="激进型" value="激进型" />
        </el-select>
        <span v-if="investmentPreference" class="preference-tip">
          {{ getPreferenceTip(investmentPreference) }}
        </span>
      </div>
    </div>

    <!-- 投资板块网格 -->
    <div class="investment-grid">
      <!-- 股票板块 — 全宽 -->
      <div
        class="investment-block stock-block"
        draggable="true"
        @dragstart="onDragStart('stock')"
        @dragover.prevent="onDragOver('stock')"
        @drop.prevent="onDrop('stock')"
        @dragend="onDragEnd"
        :class="{ 'is-dragging': draggingBlock === 'stock', 'is-drag-over': dragOverBlock === 'stock' }"
      >
        <div class="block-header">
          <div class="block-title-group">
            <div class="drag-handle" title="拖动排序">
              <el-icon><Rank /></el-icon>
            </div>
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
      <div
        class="investment-block fund-block"
        draggable="true"
        @dragstart="onDragStart('fund')"
        @dragover.prevent="onDragOver('fund')"
        @drop.prevent="onDrop('fund')"
        @dragend="onDragEnd"
        :class="{ 'is-dragging': draggingBlock === 'fund', 'is-drag-over': dragOverBlock === 'fund' }"
      >
        <div class="block-header">
          <div class="block-title-group">
            <div class="drag-handle" title="拖动排序">
              <el-icon><Rank /></el-icon>
            </div>
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

      <!-- 现金板块 — 全宽 -->
      <div
        class="investment-block cash-block"
        draggable="true"
        @dragstart="onDragStart('cash')"
        @dragover.prevent="onDragOver('cash')"
        @drop.prevent="onDrop('cash')"
        @dragend="onDragEnd"
        :class="{ 'is-dragging': draggingBlock === 'cash', 'is-drag-over': dragOverBlock === 'cash' }"
      >
        <div class="block-header">
          <div class="block-title-group">
            <div class="drag-handle" title="拖动排序">
              <el-icon><Rank /></el-icon>
            </div>
            <div class="block-icon cash-icon">
              <el-icon><Coin /></el-icon>
            </div>
            <div class="block-title-info">
              <h2 class="block-title">现金</h2>
              <span class="block-subtitle">{{ cashList.length }} 个账户，{{ formatWan(totalCashCny) }}万元</span>
            </div>
          </div>
          <div class="block-actions">
            <el-button type="primary" size="small" @click="addCashDialogVisible = true">
              <el-icon><Plus /></el-icon>
              添加
            </el-button>
          </div>
        </div>
        <div class="block-body">
          <el-table
            :data="cashList"
            v-loading="cashLoading"
            size="small"
            class="modern-table"
          >
            <el-table-column label="币种" width="150">
              <template #default="{ row }">
                <el-tag size="small" :type="row.currency === 'CNY' ? 'success' : row.currency === 'USD' ? 'warning' : 'info'">
                  {{ getCurrencyInfo(row.currency).symbol }} {{ row.currency }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="amount" label="金额" width="160" align="right">
              <template #default="{ row }">
                <span style="font-weight: 600; font-family: 'Monaco', 'Menlo', monospace;">
                  {{ getCurrencyInfo(row.currency).symbol }}{{ formatPrice(row.amount) }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="notes" label="备注" min-width="200" show-overflow-tooltip />
            <el-table-column label="操作" width="120" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" size="small" @click="editCash(row)">编辑</el-button>
                <el-button link type="danger" size="small" @click="removeCash(row)">移除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div v-if="!cashLoading && cashList.length === 0" class="empty-state">
            <el-empty description="暂无现金记录" :image-size="80">
              <el-button type="primary" size="small" @click="addCashDialogVisible = true">
                添加第一笔现金
              </el-button>
            </el-empty>
          </div>
        </div>
      </div>

      <!-- 实物资产板块 — 全宽 -->
      <div
        class="investment-block asset-block"
        draggable="true"
        @dragstart="onDragStart('asset')"
        @dragover.prevent="onDragOver('asset')"
        @drop.prevent="onDrop('asset')"
        @dragend="onDragEnd"
        :class="{ 'is-dragging': draggingBlock === 'asset', 'is-drag-over': dragOverBlock === 'asset' }"
      >
        <div class="block-header">
          <div class="block-title-group">
            <div class="drag-handle" title="拖动排序">
              <el-icon><Rank /></el-icon>
            </div>
            <div class="block-icon asset-icon">
              <el-icon><Coin /></el-icon>
            </div>
            <div class="block-title-info">
              <h2 class="block-title">实物资产</h2>
              <span class="block-subtitle">{{ assetList.length }} 项，估值 {{ formatWan(totalAssetValue) }}万元</span>
            </div>
          </div>
          <div class="block-actions">
            <el-button type="primary" size="small" @click="addAssetDialogVisible = true">
              <el-icon><Plus /></el-icon>
              添加
            </el-button>
          </div>
        </div>
        <div class="block-body">
          <el-table
            :data="assetList"
            v-loading="assetLoading"
            size="small"
            class="modern-table"
          >
            <el-table-column prop="name" label="名称" width="130">
              <template #default="{ row }">
                <el-tag size="small" effect="plain" type="warning">{{ row.name }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="数量" width="150" align="right">
              <template #default="{ row }">
                <span style="font-weight: 600; font-family: Monaco, Menlo, monospace;">
                  {{ row.quantity }} {{ row.unit }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="估值" width="160" align="right">
              <template #default="{ row }">
                <span style="font-weight: 600;">¥{{ formatPrice(row.estimated_value) }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="notes" label="备注" min-width="200" show-overflow-tooltip />
            <el-table-column label="操作" width="120" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" size="small" @click="editAsset(row)">编辑</el-button>
                <el-button link type="danger" size="small" @click="removeAsset(row)">移除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div v-if="!assetLoading && assetList.length === 0" class="empty-state">
            <el-empty description="暂无实物资产" :image-size="80">
              <el-button type="primary" size="small" @click="addAssetDialogVisible = true">
                添加第一项实物资产
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
          <div style="font-size: 12px; color: #909399; margin-top: 4px;">
            <template v-if="addForm.market === 'A股'">输入代码后失焦，将自动填充股票名称</template>
            <template v-else>{{ addForm.market }}不支持自动获取名称，请手动输入</template>
          </div>
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
          <el-input v-model="addFundForm.fund_code" placeholder="输入基金代码，如 000001" @blur="fetchFundInfo" />
          <div style="font-size: 12px; color: #909399; margin-top: 4px;">
            输入基金代码后失焦，将自动填充基金名称
          </div>
        </el-form-item>
        <el-form-item label="基金名称" prop="fund_name">
          <el-input v-model="addFundForm.fund_name" placeholder="基金名称" />
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

    <!-- 添加现金对话框 -->
    <el-dialog v-model="addCashDialogVisible" title="添加现金" width="450px">
      <el-form :model="addCashForm" label-width="80px">
        <el-form-item label="币种">
          <el-select v-model="addCashForm.currency" style="width: 100%;">
            <el-option v-for="c in currencyOptions" :key="c.value" :label="c.label" :value="c.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="金额">
          <el-input-number v-model="addCashForm.amount" :min="0" :precision="2" controls-position="right" style="width: 100%;" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="addCashForm.notes" type="textarea" :rows="2" placeholder="可选：添加备注信息" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addCashDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleAddCash" :loading="addCashLoading">添加</el-button>
      </template>
    </el-dialog>

    <!-- 编辑现金对话框 -->
    <el-dialog v-model="editCashDialogVisible" title="编辑现金" width="450px">
      <el-form :model="editCashForm" label-width="80px">
        <el-form-item label="币种">
          <el-select v-model="editCashForm.currency" style="width: 100%;">
            <el-option v-for="c in currencyOptions" :key="c.value" :label="c.label" :value="c.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="金额">
          <el-input-number v-model="editCashForm.amount" :min="0" :precision="2" controls-position="right" style="width: 100%;" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="editCashForm.notes" type="textarea" :rows="2" placeholder="可选：添加备注信息" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editCashDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleEditCash" :loading="editCashLoading">保存</el-button>
      </template>
    </el-dialog>

    <!-- 添加实物资产对话框 -->
    <el-dialog v-model="addAssetDialogVisible" title="添加实物资产" width="450px">
      <el-form :model="addAssetForm" label-width="80px">
        <el-form-item label="名称">
          <el-input v-model="addAssetForm.name" placeholder="如：黄金、白银" />
        </el-form-item>
        <el-form-item label="数量">
          <el-input-number v-model="addAssetForm.quantity" :min="0" :precision="3" controls-position="right" style="width: 100%;" />
        </el-form-item>
        <el-form-item label="单位">
          <el-select v-model="addAssetForm.unit" style="width: 100%;">
            <el-option label="克 (g)" value="克" />
            <el-option label="盎司 (oz)" value="盎司" />
            <el-option label="千克 (kg)" value="千克" />
            <el-option label="件" value="件" />
            <el-option label="吨" value="吨" />
          </el-select>
        </el-form-item>
        <el-form-item label="估值 (¥)">
          <el-input-number v-model="addAssetForm.estimated_value" :min="0" :precision="2" controls-position="right" style="width: 100%;" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="addAssetForm.notes" type="textarea" :rows="2" placeholder="可选" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addAssetDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleAddAsset" :loading="addAssetLoading">添加</el-button>
      </template>
    </el-dialog>

    <!-- 编辑实物资产对话框 -->
    <el-dialog v-model="editAssetDialogVisible" title="编辑实物资产" width="450px">
      <el-form :model="editAssetForm" label-width="80px">
        <el-form-item label="名称">
          <el-input v-model="editAssetForm.name" />
        </el-form-item>
        <el-form-item label="数量">
          <el-input-number v-model="editAssetForm.quantity" :min="0" :precision="3" controls-position="right" style="width: 100%;" />
        </el-form-item>
        <el-form-item label="单位">
          <el-select v-model="editAssetForm.unit" style="width: 100%;">
            <el-option label="克 (g)" value="克" />
            <el-option label="盎司 (oz)" value="盎司" />
            <el-option label="千克 (kg)" value="千克" />
            <el-option label="件" value="件" />
            <el-option label="吨" value="吨" />
          </el-select>
        </el-form-item>
        <el-form-item label="估值 (¥)">
          <el-input-number v-model="editAssetForm.estimated_value" :min="0" :precision="2" controls-position="right" style="width: 100%;" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="editAssetForm.notes" type="textarea" :rows="2" placeholder="可选" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editAssetDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleEditAsset" :loading="editAssetLoading">保存</el-button>
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
  Money,
  Rank,
  Coin,
  Opportunity
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { portfolioApi, fundPortfolioApi, cashApi, assetApi, type PortfolioHolding, type FundHolding, type CashItem, type AssetItem } from '@/api/portfolio'
import { searchStockBasics, searchFundBasics } from '@/api/cache'
import { getUserSettings, saveUserSettings } from '@/api/userSettings'

const router = useRouter()

// ==================== 区块拖拽排序 ====================
const BLOCK_ORDER_KEY = 'portfolio_block_order'

const VALID_BLOCKS = ['stock', 'fund', 'cash', 'asset']

// 从 localStorage 恢复顺序（用于页面切换时快速展示，避免白屏）
const restoreBlockOrderFromLocal = (): string[] => {
  try {
    const saved = localStorage.getItem(BLOCK_ORDER_KEY)
    if (saved) {
      const parsed = JSON.parse(saved)
      if (Array.isArray(parsed) && parsed.length >= 2 &&
          parsed.includes('stock') && parsed.includes('fund') &&
          parsed.every(item => VALID_BLOCKS.includes(item))) {
        return parsed
      }
    }
  } catch (e) {
    console.warn('从本地恢复区块顺序失败:', e)
  }
  return ['stock', 'fund', 'cash']
}

const blockOrder = ref<string[]>(restoreBlockOrderFromLocal())
const draggingBlock = ref<string | null>(null)
const dragOverBlock = ref<string | null>(null)

const stockOrder = computed(() => blockOrder.value.indexOf('stock'))
const fundOrder = computed(() => blockOrder.value.indexOf('fund'))
const cashOrder = computed(() => blockOrder.value.indexOf('cash'))
const assetOrder = computed(() => blockOrder.value.indexOf('asset'))

// 保存顺序到本地 + 后端
const saveBlockOrder = async () => {
  // 1. 先保存到 localStorage（即时响应）
  try {
    localStorage.setItem(BLOCK_ORDER_KEY, JSON.stringify(blockOrder.value))
  } catch (e) {
    console.warn('保存区块顺序到本地失败:', e)
  }

  // 2. 异步保存到后端
  try {
    await saveUserSettings({ portfolio_block_order: blockOrder.value })
    console.log('✅ 区块顺序已同步到后端')
  } catch (e: any) {
    console.warn('同步区块顺序到后端失败:', e)
    ElMessage.warning('排序已本地保存，但同步到服务器失败')
  }
}

// 从后端获取配置并覆盖本地（强制刷新 / 首次加载时调用）
const fetchBlockOrderFromServer = async () => {
  try {
    const response = await getUserSettings()
    const data = response.data || {}
    const serverOrder = data.portfolio_block_order
    if (
      Array.isArray(serverOrder) &&
      serverOrder.length >= 2 &&
      serverOrder.includes('stock') &&
      serverOrder.includes('fund') &&
      serverOrder.every(item => VALID_BLOCKS.includes(item))
    ) {
      blockOrder.value = serverOrder
      localStorage.setItem(BLOCK_ORDER_KEY, JSON.stringify(serverOrder))
      console.log('✅ 已从后端同步区块顺序:', serverOrder)
    }
  } catch (e: any) {
    console.warn('从后端获取区块顺序失败:', e)
  }
}

const onDragStart = (blockKey: string) => {
  draggingBlock.value = blockKey
}

const onDragOver = (blockKey: string) => {
  dragOverBlock.value = blockKey
}

const onDrop = (targetKey: string) => {
  if (!draggingBlock.value || draggingBlock.value === targetKey) {
    draggingBlock.value = null
    dragOverBlock.value = null
    return
  }
  // 交换位置
  const fromIndex = blockOrder.value.indexOf(draggingBlock.value)
  const toIndex = blockOrder.value.indexOf(targetKey)
  if (fromIndex !== -1 && toIndex !== -1) {
    const newOrder = [...blockOrder.value]
    newOrder.splice(fromIndex, 1)
    newOrder.splice(toIndex, 0, draggingBlock.value)
    blockOrder.value = newOrder
    // 持久化（本地 + 后端异步）
    saveBlockOrder()
  }
  draggingBlock.value = null
  dragOverBlock.value = null
}

const onDragEnd = () => {
  draggingBlock.value = null
  dragOverBlock.value = null
}

// ==================== 投资偏好 ====================
const PREFERENCE_KEY = 'investment_preference'
const investmentPreference = ref('稳健型')

const loadPreference = () => {
  // 先读 localStorage（快速展示）
  try {
    const saved = localStorage.getItem(PREFERENCE_KEY)
    if (saved && ['保守型', '谨慎型', '稳健型', '进取型', '激进型'].includes(saved)) {
      investmentPreference.value = saved
    }
  } catch (e) {
    console.warn('读取本地偏好失败:', e)
  }
  // 无本地记录时，将默认值同步到后端
  if (!localStorage.getItem(PREFERENCE_KEY)) {
    savePreferenceToServer()
  }
  // 从后端获取最新偏好
  fetchPreferenceFromServer()
}

const fetchPreferenceFromServer = async () => {
  try {
    const response = await getUserSettings()
    const data = response.data || {}
    const pref = data.investment_preference
    if (pref && ['保守型', '谨慎型', '稳健型', '进取型', '激进型'].includes(pref)) {
      investmentPreference.value = pref
      localStorage.setItem(PREFERENCE_KEY, pref)
    }
  } catch (e) {
    console.warn('从后端获取投资偏好失败:', e)
  }
}

const savePreferenceToServer = async () => {
  try {
    await saveUserSettings({ investment_preference: investmentPreference.value })
    localStorage.setItem(PREFERENCE_KEY, investmentPreference.value)
  } catch (e) {
    console.warn('保存投资偏好到后端失败:', e)
    ElMessage.warning('偏好已本地保存，但同步到服务器失败')
  }
}

const onPreferenceChange = () => {
  if (!investmentPreference.value) {
    localStorage.removeItem(PREFERENCE_KEY)
  }
  savePreferenceToServer()
  if (investmentPreference.value) {
    ElMessage.success(`投资偏好已设为「${investmentPreference.value}」`)
  }
}

const getPreferenceTip = (pref: string): string => {
  const tips: Record<string, string> = {
    '保守型': '低风险偏好，优先保障本金安全',
    '谨慎型': '较低风险偏好，可接受小幅波动',
    '稳健型': '中等风险偏好，追求稳健增值',
    '进取型': '较高风险偏好，可接受较大波动',
    '激进型': '高风险偏好，追求高收益回报'
  }
  return tips[pref] || ''
}

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
  return stockTotalValue.value + fundTotalValue.value + totalCashCny.value + totalAssetValue.value
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
  const code = addForm.value.stock_code.trim()
  if (!code || addForm.value.stock_name) return

  try {
    const response = await searchStockBasics(code, 10)
    const results = response.data || []
    const match = results.find((item: any) => {
      if (!item) return false
      const sym = (item.symbol || '').trim()
      const ts = (item.ts_code || '').trim()
      return sym === code || ts === code || ts.startsWith(code + '.')
    })
    if (match && match.name) {
      addForm.value.stock_name = match.name
    }
  } catch (e) {
    console.warn('查询股票基础信息失败:', e)
  }
}

const fetchFundInfo = async () => {
  const code = addFundForm.value.fund_code.trim()
  if (!code || addFundForm.value.fund_name) return

  try {
    const response = await searchFundBasics(code, 10)
    const results = response.data || []
    const match = results.find((item: any) => {
      if (!item) return false
      return (item.ts_code || '').trim() === code
    })
    if (match && match.name) {
      addFundForm.value.fund_name = match.name
      if (match.fund_type && !addFundForm.value.fund_type) {
        addFundForm.value.fund_type = match.fund_type
      }
    }
  } catch (e) {
    console.warn('查询基金基础信息失败:', e)
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
    fund_type: '',
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
      fund_type: addFundForm.value.fund_type || '混合型',
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

// ==================== 现金管理 ====================
const cashList = ref<CashItem[]>([])
const cashLoading = ref(false)

const currencyOptions = [
  { label: '人民币 (CNY)', value: 'CNY', symbol: '¥', rate: 1 },
  { label: '美元 (USD)', value: 'USD', symbol: '$', rate: 7.2 },
  { label: '港币 (HKD)', value: 'HKD', symbol: 'HK$', rate: 0.92 }
]

const getCurrencyInfo = (currency: string) => {
  return currencyOptions.find(c => c.value === currency) || currencyOptions[0]
}

const totalCashCny = computed(() => {
  return cashList.value.reduce((sum, c) => {
    const info = getCurrencyInfo(c.currency)
    return sum + c.amount * info.rate
  }, 0)
})

const loadCash = async () => {
  cashLoading.value = true
  try {
    const res = await cashApi.list()
    cashList.value = res.data || []
  } catch (error: any) {
    console.error('加载现金失败:', error)
  } finally {
    cashLoading.value = false
  }
}

// 添加现金对话框
const addCashDialogVisible = ref(false)
const addCashLoading = ref(false)
const addCashForm = ref({
  currency: 'CNY',
  amount: undefined as number | undefined,
  notes: ''
})

const handleAddCash = async () => {
  if (addCashForm.value.amount == null || addCashForm.value.amount <= 0) {
    ElMessage.warning('请输入资金数额')
    return
  }
  addCashLoading.value = true
  try {
    const res = await cashApi.add({
      currency: addCashForm.value.currency,
      amount: addCashForm.value.amount,
      notes: addCashForm.value.notes
    })
    if (res.success) {
      ElMessage.success('添加现金成功')
      addCashDialogVisible.value = false
      await loadCash()
    } else {
      ElMessage.error(res.message || '添加现金失败')
    }
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '添加现金失败')
  } finally {
    addCashLoading.value = false
  }
}

// 编辑现金对话框
const editCashDialogVisible = ref(false)
const editCashLoading = ref(false)
const editCashForm = ref({
  id: '',
  currency: 'CNY',
  amount: undefined as number | undefined,
  notes: ''
})

const editCash = (row: CashItem) => {
  editCashForm.value = {
    id: row.id,
    currency: row.currency,
    amount: row.amount,
    notes: row.notes
  }
  editCashDialogVisible.value = true
}

const handleEditCash = async () => {
  editCashLoading.value = true
  try {
    const res = await cashApi.update(editCashForm.value.id, {
      currency: editCashForm.value.currency,
      amount: editCashForm.value.amount,
      notes: editCashForm.value.notes
    })
    if (res.success) {
      ElMessage.success('更新现金成功')
      editCashDialogVisible.value = false
      await loadCash()
    } else {
      ElMessage.error(res.message || '更新现金失败')
    }
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '更新现金失败')
  } finally {
    editCashLoading.value = false
  }
}

// ==================== 实物资产管理 ====================
const assetList = ref<AssetItem[]>([])
const assetLoading = ref(false)

const totalAssetValue = computed(() => {
  return assetList.value.reduce((sum, a) => sum + (a.estimated_value || 0), 0)
})

const loadAssets = async () => {
  assetLoading.value = true
  try {
    const res = await assetApi.list()
    assetList.value = res.data || []
  } catch (error: any) {
    console.error('加载实物资产失败:', error)
  } finally {
    assetLoading.value = false
  }
}

// 添加对话框
const addAssetDialogVisible = ref(false)
const addAssetLoading = ref(false)
const addAssetForm = ref({
  name: '',
  quantity: 1,
  unit: '克',
  estimated_value: 0,
  notes: ''
})

const handleAddAsset = async () => {
  if (!addAssetForm.value.name) {
    ElMessage.warning('请输入资产名称')
    return
  }
  addAssetLoading.value = true
  try {
    const res = await assetApi.add(addAssetForm.value)
    if (res.success) {
      ElMessage.success('添加实物资产成功')
      addAssetDialogVisible.value = false
      await loadAssets()
    } else {
      ElMessage.error(res.message || '添加失败')
    }
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '添加失败')
  } finally {
    addAssetLoading.value = false
  }
}

// 编辑对话框
const editAssetDialogVisible = ref(false)
const editAssetLoading = ref(false)
const editAssetForm = ref({
  id: '',
  name: '',
  quantity: 1,
  unit: '克',
  estimated_value: 0,
  notes: ''
})

const editAsset = (row: AssetItem) => {
  editAssetForm.value = {
    id: row.id,
    name: row.name,
    quantity: row.quantity,
    unit: row.unit,
    estimated_value: row.estimated_value,
    notes: row.notes
  }
  editAssetDialogVisible.value = true
}

const handleEditAsset = async () => {
  editAssetLoading.value = true
  try {
    const res = await assetApi.update(editAssetForm.value.id, {
      name: editAssetForm.value.name,
      quantity: editAssetForm.value.quantity,
      unit: editAssetForm.value.unit,
      estimated_value: editAssetForm.value.estimated_value,
      notes: editAssetForm.value.notes
    })
    if (res.success) {
      ElMessage.success('更新成功')
      editAssetDialogVisible.value = false
      await loadAssets()
    } else {
      ElMessage.error(res.message || '更新失败')
    }
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '更新失败')
  } finally {
    editAssetLoading.value = false
  }
}

const removeAsset = async (row: AssetItem) => {
  try {
    await ElMessageBox.confirm(
      `确定要移除 ${row.name}（${row.quantity} ${row.unit}）的记录吗？`,
      '确认移除',
      { type: 'warning' }
    )
    const res = await assetApi.remove(row.id)
    if (res.success) {
      ElMessage.success('删除实物资产成功')
      await loadAssets()
    } else {
      ElMessage.error(res.message || '删除失败')
    }
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error?.response?.data?.detail || '删除失败')
    }
  }
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
  loadCash()
  loadAssets()
  loadPreference()
  // 从后端获取最新配置并覆盖本地缓存（强制刷新时生效）
  fetchBlockOrderFromServer()
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

  .preference-bar {
    margin-bottom: 20px;
    padding: 14px 24px;
    background: linear-gradient(135deg, #fdf6ec 0%, #fef0e6 50%, #fff5e6 100%);
    border: 1px solid #f5d9b3;
    border-radius: 12px;
    display: flex;
    align-items: center;

    .preference-bar-content {
      display: flex;
      align-items: center;
      gap: 16px;
      flex-wrap: wrap;
      width: 100%;

      .preference-label {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 15px;
        font-weight: 700;
        color: #d48806;
        white-space: nowrap;

        .el-icon {
          font-size: 20px;
        }
      }

      .preference-select {
        width: 160px;

        :deep(.el-select__wrapper) {
          background: #fff;
          border-color: #f5d9b3;
          height: 34px;
          min-height: 34px;
          font-size: 14px;
          font-weight: 600;

          &.is-hovering,
          &:hover {
            border-color: #d48806;
          }
        }

        :deep(.el-select__placeholder) {
          font-size: 13px;
          color: #b3863c;
        }

        :deep(.el-select__selected-item) {
          color: #d48806;
        }
      }

      .preference-tip {
        font-size: 12px;
        color: #b3863c;
        flex: 1;
        min-width: 180px;
      }
    }
  }

  .investment-grid {
    display: flex;
    flex-direction: column;
    gap: 20px;

    .stock-block {
      order: v-bind(stockOrder);
    }

    .fund-block {
      order: v-bind(fundOrder);
    }

    .cash-block {
      order: v-bind(cashOrder);
    }

    .asset-block {
      order: v-bind(assetOrder);
    }

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

      &.is-dragging {
        opacity: 0.6;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
        cursor: grabbing;
      }

      &.is-drag-over {
        position: relative;

        &::before {
          content: '';
          position: absolute;
          top: -10px;
          left: 0;
          right: 0;
          height: 3px;
          background: var(--el-color-primary);
          border-radius: 2px;
          z-index: 1;
        }
      }

      .drag-handle {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 28px;
        height: 28px;
        border-radius: 6px;
        cursor: grab;
        color: var(--el-text-color-placeholder);
        transition: all 0.2s ease;

        &:hover {
          background: var(--el-fill-color-darker);
          color: var(--el-text-color-secondary);
        }

        &:active {
          cursor: grabbing;
        }
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

            &.cash-icon {
              background: linear-gradient(135deg, #67c23a 0%, #409eff 100%);
              color: #fff;
            }

            &.asset-icon {
              background: linear-gradient(135deg, #e6a23c 0%, #f56c6c 100%);
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
