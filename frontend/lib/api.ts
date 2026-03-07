/**
 * API client for Job Queue System
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export interface Task {
  id: string
  type: string
  status: 'queued' | 'processing' | 'completed' | 'failed' | 'failed_permanent' | 'in_progress' | 'dead_letter'
  priority: number
  payload: any
  result?: any
  scheduled_for?: string
  timeout: number
  max_retries: number
  retry_count: number
  created_at: string
  updated_at: string
  started_at?: string
  completed_at?: string
  failed_at?: string
  locked_by?: string
  locked_at?: string
  completed_by?: string
  created_by: string
  correlation_id?: string
  error_message?: string
}

export interface TaskListResponse {
  tasks: Task[]
  total: number
  limit: number
  offset: number
  has_more: boolean
}

export interface WorkerApiResponse {
  id: string
  status: 'active' | 'idle' | 'offline' | 'error'
  capabilities: string[]
  version?: string
  current_task_id?: string
  last_heartbeat: string
  tasks_processed: number
  tasks_failed: number
  tasks_completed: number
  uptime_seconds: number
  memory_usage?: number
  cpu_usage?: number
  hostname?: string
  ip_address?: string
  created_at: string
}

export interface WorkerListApiResponse {
  workers: WorkerApiResponse[]
  total: number
  limit: number
  offset: number
  has_more: boolean
}

export interface AuthResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  user: {
    id: string
    email: string
    role: string
    created_at: string
  }
}

class ApiClient {
  private baseUrl: string
  private token: string | null = null

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl
    // Try to get token from localStorage if available
    if (typeof window !== 'undefined') {
      this.token = localStorage.getItem('auth_token')
    }
  }

  setToken(token: string) {
    this.token = token
    if (typeof window !== 'undefined') {
      localStorage.setItem('auth_token', token)
    }
  }

  clearToken() {
    this.token = null
    if (typeof window !== 'undefined') {
      localStorage.removeItem('auth_token')
    }
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}/api/v1${endpoint}`
    
    console.log(`[API] Making request to: ${url}`)
    
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...((options.headers as Record<string, string>) || {})
    }

    // Always check for token in localStorage before making requests
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('auth_token')
      if (token) {
        this.token = token
        headers.Authorization = `Bearer ${token}`
      }
    } else if (this.token) {
      headers.Authorization = `Bearer ${this.token}`
    }

    const config: RequestInit = {
      ...options,
      headers
    }
    
    console.log(`[API] Request config:`, config)

    try {
      const response = await fetch(url, config)
      
      console.log(`[API] Response status: ${response.status}`)
      
      if (!response.ok) {
        const errorText = await response.text()
        console.error(`[API] Error response:`, errorText)
        let error
        try {
          error = JSON.parse(errorText)
        } catch {
          error = { detail: errorText }
        }
        
        // If we get a 401, clear the invalid token and notify listeners
        if (response.status === 401) {
          this.clearToken()
          if (typeof window !== 'undefined') {
            localStorage.removeItem('user')
            window.dispatchEvent(new Event('auth:unauthorized'))
          }
        }
        
        throw new Error(error.detail || `HTTP ${response.status}`)
      }

      // 204 No Content — nothing to parse
      if (response.status === 204 || response.headers.get('content-length') === '0') {
        return undefined as unknown as T
      }

      const result = await response.json()
      console.log(`[API] Success response:`, result)
      return result
    } catch (error) {
      console.error(`API Error [${endpoint}]:`, error)
      throw error
    }
  }

  // Authentication
  async login(email: string, password: string): Promise<AuthResponse> {
    const response = await this.request<AuthResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password })
    })
    
    this.setToken(response.access_token)
    return response
  }

  async logout(): Promise<void> {
    this.clearToken()
  }

  // Tasks
  async getTasks(params?: {
    status?: string
    task_type?: string
    priority?: number
    created_by?: string
    locked_by?: string
    completed_by?: string
    correlation_id?: string
    limit?: number
    offset?: number
    sort_by?: string
    sort_order?: 'asc' | 'desc'
  }): Promise<TaskListResponse> {
    const searchParams = new URLSearchParams()
    
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          searchParams.append(key, value.toString())
        }
      })
    }

    const endpoint = `/tasks/${searchParams.toString() ? '?' + searchParams.toString() : ''}`
    return this.request<TaskListResponse>(endpoint)
  }

  async createTask(task: {
    task_type: string
    payload: any
    priority?: number
    scheduled_for?: string
    timeout?: number
    max_retries?: number
    correlation_id?: string
  }): Promise<Task> {
    return this.request<Task>('/tasks/', {
      method: 'POST',
      body: JSON.stringify(task)
    })
  }

  async getTask(taskId: string): Promise<Task> {
    return this.request<Task>(`/tasks/${taskId}`)
  }

  // Metrics (placeholder - implement based on actual API)
  async getMetrics() {
    try {
      // Try to get basic task metrics with a smaller limit
      const tasks = await this.getTasks({ limit: 50 })
      
      const totalTasks = tasks.total
      const failedTasks = tasks.tasks.filter(t => t.status === 'failed' || t.status === 'failed_permanent').length
      const completedTasks = tasks.tasks.filter(t => t.status === 'completed').length
      const queuedTasks = tasks.tasks.filter(t => t.status === 'queued').length
      const processingTasks = tasks.tasks.filter(t => t.status === 'processing').length
      
      return {
        totalTasks,
        failedTasks,
        completedTasks,
        queuedTasks,
        processingTasks,
        activeWorkers: 2, // Mock value - needs worker API
        queueLength: queuedTasks,
        successRate: totalTasks > 0 ? (completedTasks / totalTasks) * 100 : 0,
        avgProcessingTime: 1.8 // Mock value - needs actual metrics
      }
    } catch (error) {
      console.error('Error fetching metrics:', error)
      // Return mock data if API fails
      return {
        totalTasks: 0,
        failedTasks: 0,
        completedTasks: 0,
        queuedTasks: 0,
        processingTasks: 0,
        activeWorkers: 0,
        queueLength: 0,
        successRate: 0,
        avgProcessingTime: 0
      }
    }
  }

  // Worker Task Management Methods
  async getWorkerTasks(taskTypes?: string): Promise<{ tasks: Task[]; total_available: number }> {
    const params = new URLSearchParams()
    if (taskTypes) {
      params.append('task_types', taskTypes)
    }
    params.append('limit', '20')
    
    return this.request(`/tasks/worker/available?${params}`)
  }

  async claimTask(taskId: string, claimData: { worker_id: string; lock_timeout?: number }): Promise<{
    task_id: string
    task: Task
    lock_expires_at: string
  }> {
    return this.request(`/tasks/${taskId}/claim`, {
      method: 'POST',
      body: JSON.stringify(claimData)
    })
  }

  async updateTaskProgress(taskId: string, progressData: {
    worker_id: string
    progress_percentage?: number
    status_message?: string
    intermediate_result?: any
  }): Promise<Task> {
    return this.request(`/tasks/${taskId}/progress`, {
      method: 'PUT',
      body: JSON.stringify(progressData)
    })
  }

  async completeTask(taskId: string, completionData: {
    worker_id: string
    result?: any
    execution_time?: number
  }): Promise<Task> {
    return this.request(`/tasks/${taskId}/complete`, {
      method: 'POST',
      body: JSON.stringify(completionData)
    })
  }

  async failTask(taskId: string, failureData: {
    worker_id: string
    error_message: string
    error_details?: any
    should_retry?: boolean
  }): Promise<Task> {
    return this.request(`/tasks/${taskId}/fail`, {
      method: 'POST',
      body: JSON.stringify(failureData)
    })
  }

  async getDeadLetterTasks(limit = 100, offset = 0): Promise<{
    tasks: Array<{
      task_id: string
      original_task: Task
      failure_count: number
      last_error?: string
      moved_to_dlq_at: string
    }>
    total: number
  }> {
    const params = new URLSearchParams()
    params.append('limit', limit.toString())
    params.append('offset', offset.toString())
    
    return this.request(`/tasks/dead-letter-queue?${params}`)
  }

  async retryDeadLetterTask(taskId: string, retryData: {
    reset_retry_count?: boolean
    new_priority?: number
  } = {}): Promise<Task> {
    return this.request(`/tasks/${taskId}/retry-from-dlq`, {
      method: 'POST',
      body: JSON.stringify(retryData)
    })
  }

  async performTaskAction(taskId: string, action: 'cancel' | 'retry' | 'reschedule' | 'reset', scheduledFor?: string): Promise<Task> {
    return this.request<Task>(`/tasks/${taskId}/actions`, {
      method: 'POST',
      body: JSON.stringify({ action, scheduled_for: scheduledFor })
    })
  }

  async getWorkers(params?: {
    status?: string
    limit?: number
    offset?: number
  }): Promise<WorkerListApiResponse> {
    const searchParams = new URLSearchParams()
    if (params?.status) searchParams.append('status', params.status)
    if (params?.limit) searchParams.append('limit', params.limit.toString())
    if (params?.offset) searchParams.append('offset', params.offset.toString())

    const query = searchParams.toString()
    return this.request<WorkerListApiResponse>(`/workers/${query ? '?' + query : ''}`)
  }

  async registerWorker(data: {
    worker_id: string
    capabilities: string[]
    api_key: string
    version?: string
  }): Promise<{ worker_id: string; status: string; message: string }> {
    return this.request('/workers/register', {
      method: 'POST',
      body: JSON.stringify(data)
    })
  }

  async deleteWorker(workerId: string): Promise<void> {
    return this.request(`/workers/${encodeURIComponent(workerId)}`, {
      method: 'DELETE'
    })
  }

  async deleteTask(taskId: string): Promise<void> {
    return this.request(`/tasks/${taskId}`, {
      method: 'DELETE'
    })
  }
}

export const apiClient = new ApiClient()