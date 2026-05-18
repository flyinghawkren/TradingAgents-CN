import { ApiClient } from './request'

export interface PortfolioHolding {
  id: string
  stock_code: string
  stock_name: string
  market: string
  quantity: number
  avg_price: number
  buy_date: string
  notes: string
  created_at?: string
  updated_at?: string
}

export interface AddHoldingRequest {
  stock_code: string
  stock_name: string
  market?: string
  quantity: number
  avg_price: number
  buy_date: string
  notes?: string
}

export interface UpdateHoldingRequest {
  quantity?: number
  avg_price?: number
  buy_date?: string
  notes?: string
}

export const portfolioApi = {
  /**
   * 获取持仓列表
   */
  list(): Promise<{ success: boolean; data: PortfolioHolding[]; message?: string }> {
    return ApiClient.get('/api/portfolio/')
  },

  /**
   * 添加持仓
   */
  add(request: AddHoldingRequest): Promise<{ success: boolean; data: PortfolioHolding; message?: string }> {
    return ApiClient.post('/api/portfolio/', request)
  },

  /**
   * 更新持仓
   */
  update(
    holdingId: string,
    request: UpdateHoldingRequest
  ): Promise<{ success: boolean; data: PortfolioHolding; message?: string }> {
    return ApiClient.put(`/api/portfolio/${holdingId}`, request)
  },

  /**
   * 删除持仓
   */
  remove(holdingId: string): Promise<{ success: boolean; data: { id: string }; message?: string }> {
    return ApiClient.delete(`/api/portfolio/${holdingId}`)
  },

  /**
   * 获取单条持仓
   */
  get(holdingId: string): Promise<{ success: boolean; data: PortfolioHolding; message?: string }> {
    return ApiClient.get(`/api/portfolio/${holdingId}`)
  },
}

// ==================== 基金持仓 ====================

export interface FundHolding {
  id: string
  fund_code: string
  fund_name: string
  fund_type: string
  quantity: number
  avg_nav: number
  buy_date: string
  notes: string
  created_at?: string
  updated_at?: string
}

export interface AddFundHoldingRequest {
  fund_code: string
  fund_name: string
  fund_type?: string
  quantity: number
  avg_nav: number
  buy_date: string
  notes?: string
}

export interface UpdateFundHoldingRequest {
  quantity?: number
  avg_nav?: number
  buy_date?: string
  notes?: string
}

// ==================== 现金管理 ====================

export interface CashItem {
  id: string
  currency: string
  amount: number
  notes: string
  created_at?: string
  updated_at?: string
}

export interface AddCashRequest {
  currency: string
  amount: number
  notes?: string
}

export const cashApi = {
  list(): Promise<{ success: boolean; data: CashItem[]; message?: string }> {
    return ApiClient.get('/api/portfolio/cash/')
  },
  add(request: AddCashRequest): Promise<{ success: boolean; data: CashItem; message?: string }> {
    return ApiClient.post('/api/portfolio/cash/', request)
  },
  update(cashId: string, request: Partial<AddCashRequest>): Promise<{ success: boolean; data: CashItem; message?: string }> {
    return ApiClient.put(`/api/portfolio/cash/${cashId}`, request)
  },
  remove(cashId: string): Promise<{ success: boolean; data: { id: string }; message?: string }> {
    return ApiClient.delete(`/api/portfolio/cash/${cashId}`)
  }
}

export const fundPortfolioApi = {
  /**
   * 获取基金持仓列表
   */
  list(): Promise<{ success: boolean; data: FundHolding[]; message?: string }> {
    return ApiClient.get('/api/portfolio/fund/')
  },

  /**
   * 添加基金持仓
   */
  add(request: AddFundHoldingRequest): Promise<{ success: boolean; data: FundHolding; message?: string }> {
    return ApiClient.post('/api/portfolio/fund/', request)
  },

  /**
   * 更新基金持仓
   */
  update(
    holdingId: string,
    request: UpdateFundHoldingRequest
  ): Promise<{ success: boolean; data: FundHolding; message?: string }> {
    return ApiClient.put(`/api/portfolio/fund/${holdingId}`, request)
  },

  /**
   * 删除基金持仓
   */
  remove(holdingId: string): Promise<{ success: boolean; data: { id: string }; message?: string }> {
    return ApiClient.delete(`/api/portfolio/fund/${holdingId}`)
  },
}
