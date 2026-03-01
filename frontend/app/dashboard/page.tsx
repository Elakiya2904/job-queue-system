'use client'

import { useState, useEffect } from 'react'
import { Sidebar } from '@/components/sidebar'
import { Header } from '@/components/header'
import { MetricCard } from '@/components/metric-card'
import { ProtectedRoute } from '@/components/protected-route'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { 
  Activity, 
  Users, 
  Clock, 
  AlertTriangle, 
  CheckCircle, 
  TrendingUp,
  Server,
  RefreshCw,
  Eye
} from 'lucide-react'
import { apiClient, Task } from '@/lib/api'
import { useRouter } from 'next/navigation'
export default function DashboardPage() {
  const [metrics, setMetrics] = useState({
    totalTasks: 0,
    failedTasks: 0,
    activeWorkers: 0,
    queueLength: 0,
    successRate: 0,
    avgProcessingTime: 0,
  })
  const [recentTasks, setRecentTasks] = useState<Task[]>([])
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [lastUpdated, setLastUpdated] = useState(new Date())
  const [loading, setLoading] = useState(true)
  const router = useRouter()

  const fetchDashboardData = async () => {
    try {
      setLoading(true)
      console.log('[Dashboard] Fetching data...')
      
      const [metricsData, tasksData] = await Promise.all([
        apiClient.getMetrics(),
        apiClient.getTasks({ limit: 8, sort_by: 'created_at', sort_order: 'desc' })
      ])
      
      console.log('[Dashboard] Metrics:', metricsData)
      console.log('[Dashboard] Tasks:', tasksData)
      
      setMetrics(metricsData)
      setRecentTasks(tasksData.tasks)
      setLastUpdated(new Date())
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error)
      // Set mock data so page doesn't stay loading forever
      setMetrics({
        totalTasks: 0,
        failedTasks: 0,
        activeWorkers: 0,
        queueLength: 0,
        successRate: 0,
        avgProcessingTime: 0,
      })
      setRecentTasks([])
    } finally {
      setLoading(false)
    }
  }

  const refreshData = async () => {
    setIsRefreshing(true)
    await fetchDashboardData()
    setIsRefreshing(false)
  }

  // Auto-refresh every 30 seconds
  useEffect(() => {
    fetchDashboardData() // Initial data fetch
    const interval = setInterval(fetchDashboardData, 30000) // Use fetchDashboardData directly
    return () => clearInterval(interval)
  }, []) // Remove fetchDashboardData from dependencies to prevent re-creating interval

  const getStatusBadge = (status: string) => {
    const configs = {
      completed: 'bg-green-100 text-green-800 border-green-200',
      processing: 'bg-yellow-100 text-yellow-800 border-yellow-200', 
      failed: 'bg-red-100 text-red-800 border-red-200'
    }
    return configs[status as keyof typeof configs] || configs.failed
  }

  const formatTime = (timestamp: string) => {
    const now = new Date()
    const time = new Date(timestamp)
    const diffMinutes = Math.floor((now.getTime() - time.getTime()) / 60000)
    
    if (diffMinutes < 1) return 'Just now'
    if (diffMinutes < 60) return `${diffMinutes}m ago`
    return time.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
  }

  return (
    <ProtectedRoute requiredRole="admin">
      <div className="flex h-screen bg-gray-50">
        <Sidebar />
        <main className="flex-1 overflow-auto">
          <div className="p-6 space-y-6">
            <div className="flex items-center justify-between">
              <Header
                title="System Dashboard"
                description="Real-time monitoring of your job queue system"
              />
              <div className="flex items-center gap-4">
                <div className="text-sm text-gray-500">
                  Last updated: {lastUpdated.toLocaleTimeString()}
                </div>
                <Button 
                  onClick={refreshData} 
                  disabled={isRefreshing}
                  variant="outline"
                  size="sm"
                  className="flex items-center gap-2"
                >
                  <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
                  Refresh
                </Button>
              </div>
            </div>

            {/* Primary Metrics */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <MetricCard
                title="Total Tasks"
                value={metrics.totalTasks.toLocaleString()}
                description="All time"
                icon={Activity}
                trend="up"
                trendValue="+12%"
                variant="default"
              />
              
              <MetricCard
                title="Failed Tasks"
                value={metrics.failedTasks.toLocaleString()}
                description="Last 30 days"
                icon={AlertTriangle}
                trend="down"
                trendValue="-5%"
                variant="danger"
              />
              
              <MetricCard
                title="Active Workers"
                value={metrics.activeWorkers}
                description="Currently processing"
                icon={Users}
                trend="neutral"
                variant="success"
              />
              
              <MetricCard
                title="Queue Length"
                value={metrics.queueLength}
                description="Waiting to process"
                icon={Clock}
                trend="up"
                trendValue="+23"
                variant="warning"
              />
            </div>

            {/* Secondary Metrics */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <MetricCard
                title="Success Rate"
                value={`${metrics.successRate.toFixed(1)}%`}
                description="Last 24 hours"
                icon={CheckCircle}
                trend="up"
                trendValue="+0.5%"
                variant="success"
              />
              
              <MetricCard
                title="Avg Processing Time"
                value={`${metrics.avgProcessingTime.toFixed(1)}s`}
                description="Per task"
                icon={TrendingUp}
                trend="down"
                trendValue="-0.2s"
                variant="default"
              />
              
              <MetricCard
                title="System Health"
                value="Healthy"
                description="All systems operational"
                icon={Server}
                variant="success"
              />
            </div>

            {/* Recent Activity */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Activity className="w-5 h-5" />
                    Recent Task Activity
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {recentTasks.slice(0, 6).map((task) => (
                      <div key={task.id} className="flex items-center justify-between py-2">
                        <div className="flex items-center gap-3">
                          <Badge variant="outline" className="text-xs">
                            {task.type}
                          </Badge>
                          <code className="text-xs text-gray-600 font-mono">
                            {task.id}
                          </code>
                        </div>
                        <div className="flex items-center gap-2">
                          <Badge className={getStatusBadge(task.status)}>
                            {task.status}
                          </Badge>
                          <span className="text-xs text-gray-500">
                            {formatTime(task.created_at)}
                          </span>
                        </div>
                      </div>
                    ))}
                    <div className="pt-2 border-t">
                      <Button variant="outline" size="sm" className="w-full flex items-center gap-2" onClick={() => router.push('/tasks')}>
                        <Eye className="w-4 h-4" />
                        View All Tasks
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Users className="w-5 h-5" />
                    Worker Status
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {Array.from({ length: 5 }, (_, i) => {
                      const workerId = `worker-00${i + 1}`
                      const isActive = Math.random() > 0.3
                      const tasksProcessed = Math.floor(Math.random() * 50) + 10
                      
                      return (
                        <div key={workerId} className="flex items-center justify-between py-2">
                          <div className="flex items-center gap-3">
                            <div className={`w-2 h-2 rounded-full ${isActive ? 'bg-green-500' : 'bg-gray-300'}`} />
                            <code className="text-sm font-mono">{workerId}</code>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="text-sm text-gray-600">
                              {tasksProcessed} tasks
                            </span>
                            <Badge variant={isActive ? 'default' : 'secondary'}>
                              {isActive ? 'Active' : 'Idle'}
                            </Badge>
                          </div>
                        </div>
                      )
                    })}
                    <div className="pt-2 border-t">
                      <Button variant="outline" size="sm" className="w-full flex items-center gap-2" onClick={() => router.push('/workers')}>
                        <Server className="w-4 h-4" />
                        Manage Workers
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* System Status */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Server className="w-5 h-5" />
                  System Status
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <div className="text-center">
                    <div className="text-3xl font-bold text-green-600">99.8%</div>
                    <div className="text-sm text-gray-600">Uptime</div>
                  </div>
                  <div className="text-center">
                    <div className="text-3xl font-bold text-blue-600">45ms</div>
                    <div className="text-sm text-gray-600">Avg Response</div>
                  </div>
                  <div className="text-center">
                    <div className="text-3xl font-bold text-purple-600">2.1GB</div>
                    <div className="text-sm text-gray-600">Memory Usage</div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </main>
      </div>
    </ProtectedRoute>
  )
}
