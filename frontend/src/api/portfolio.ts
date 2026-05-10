import { ApiClient } from './client'

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
