/**
 * 用户偏好设置 API
 */
import request from '@/api/request'

/**
 * 获取用户偏好设置
 */
export function getUserSettings() {
  return request<Record<string, any>>({
    url: '/api/user/settings',
    method: 'get'
  })
}

/**
 * 保存用户偏好设置（增量更新）
 */
export function saveUserSettings(settings: Record<string, any>) {
  return request<{ success: boolean }>({
    url: '/api/user/settings',
    method: 'post',
    data: { settings }
  })
}

/**
 * 获取用户指定 key 的设置值
 */
export function getUserSettingByKey(key: string) {
  return request<{ value: any }>({
    url: `/api/user/settings/${key}`,
    method: 'get'
  })
}
