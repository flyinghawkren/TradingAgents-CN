<template>
  <div class="fund-portfolio-page">
    <div class="page-header">
      <div class="page-title">
        <span>基金组合分析</span>
      </div>
      <div class="page-description">
        功能开发中，敬请期待
      </div>
    </div>
    <el-card>
      <el-empty description="功能开发中，敬请期待" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
// 基金组合分析占位页面
</script>

<style lang="scss" scoped>
.fund-portfolio-page {
  padding: 20px;
}

.page-header {
  background: linear-gradient(135deg, var(--el-color-primary-light-9) 0%, var(--el-fill-color-light) 100%);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 12px;
  padding: 20px 24px;
  margin-bottom: 20px;
}

.page-title {
  font-size: 22px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--el-text-color-primary);
}

.page-description {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  margin-top: 8px;
}

:deep(.el-card) {
  border-radius: 12px;
  border: 1px solid var(--el-border-color-lighter);
}
</style>
