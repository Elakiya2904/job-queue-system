export interface Task {
  id: string
  type: string
  status: 'queued' | 'processing' | 'completed' | 'failed' | 'failed_permanent' | 'in_progress' | 'dead_letter'
  retry_count: number
  max_retries: number
  created_at: string
  locked_by?: string
  completed_by?: string
  result?: any
  error_message?: string
}

export interface User {
  id: string
  email: string
  role: 'admin' | 'user'
}

export interface Worker {
  id: string
  status: 'active' | 'idle' | 'offline' | 'error'
  last_heartbeat: string
  tasks_processed: number
  tasks_completed: number
  tasks_failed: number
  current_task?: string
  uptime?: number
  memory_usage?: number
  cpu_usage?: number
  version?: string
  capabilities?: string[]
  hostname?: string
  ip_address?: string
  created_at?: string
}

export interface Metrics {
  total_tasks: number
  failed_tasks: number
  active_workers: number
  queue_length: number
}
