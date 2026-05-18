/**
 * 缓存管理 API
 */
import request from '@/api/request'

/**
 * 缓存统计数据
 */
export interface CacheStats {
  totalFiles: number
  totalSize: number
  maxSize: number
  stockDataCount: number
  newsDataCount: number
  analysisDataCount: number
}

/**
 * 缓存详情项
 */
export interface CacheDetailItem {
  type: string
  symbol: string
  size: number
  created_at: string
  last_accessed: string
  hit_count: number
}

/**
 * 缓存详情响应
 */
export interface CacheDetailsResponse {
  items: CacheDetailItem[]
  total: number
  page: number
  page_size: number
}

/**
 * 缓存后端信息
 */
export interface CacheBackendInfo {
  system: string
  primary_backend: string
  fallback_enabled: boolean
  mongodb_available?: boolean
  redis_available?: boolean
}

/**
 * 获取缓存统计
 */
export function getCacheStats() {
  return request<CacheStats>({
    url: '/api/cache/stats',
    method: 'get'
  })
}

/**
 * 清理过期缓存
 * @param days 清理多少天前的缓存
 */
export function cleanupOldCache(days: number) {
  return request({
    url: '/api/cache/cleanup',
    method: 'delete',
    params: { days }
  })
}

/**
 * 清空所有缓存
 */
export function clearAllCache() {
  return request({
    url: '/api/cache/clear',
    method: 'delete'
  })
}

/**
 * 获取缓存详情列表
 * @param page 页码
 * @param pageSize 每页数量
 */
export function getCacheDetails(page: number = 1, pageSize: number = 20) {
  return request<CacheDetailsResponse>({
    url: '/api/cache/details',
    method: 'get',
    params: { page, page_size: pageSize }
  })
}

/**
 * 获取缓存后端信息
 */
export function getCacheBackendInfo() {
  return request<CacheBackendInfo>({
    url: '/api/cache/backend-info',
    method: 'get'
  })
}

// ==================== 基础信息同步 ====================

export interface BasicsSyncStatus {
  is_running: boolean
  last_sync_time: string | null
  last_result: {
    success: boolean
    message: string
    stock: { count: number; message: string }
    fund: { count: number; message: string }
  } | null
  stock_count: number
  fund_count: number
}

/**
 * 获取基础信息同步状态
 */
export function getBasicsSyncStatus() {
  return request<BasicsSyncStatus>({
    url: '/api/basics/status',
    method: 'get'
  })
}

/**
 * 手动触发基础信息同步
 */
export function triggerBasicsSync() {
  return request<{ success: boolean; already_running: boolean; message: string }>({
    url: '/api/basics/sync',
    method: 'post'
  })
}

/**
 * 股票基础信息项
 */
export interface StockBasicItem {
  ts_code: string
  symbol: string
  name: string
  area?: string
  industry?: string
  market?: string
  list_date?: string
}

/**
 * 基金基础信息项
 */
export interface FundBasicItem {
  ts_code: string
  name: string
  fund_type?: string
}

/**
 * 搜索股票基础信息
 */
export function searchStockBasics(keyword: string, limit: number = 20) {
  return request<StockBasicItem[]>({
    url: '/api/basics/stocks',
    method: 'get',
    params: { keyword, limit }
  })
}

/**
 * 搜索基金基础信息
 */
export function searchFundBasics(keyword: string, limit: number = 20) {
  return request<FundBasicItem[]>({
    url: '/api/basics/funds',
    method: 'get',
    params: { keyword, limit }
  })
}

