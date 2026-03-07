'use client'
// REWRITTEN — comprehensive worker management page
import { useState, useMemo, useEffect } from 'react'
import { Sidebar } from '@/components/sidebar'
import { Header } from '@/components/header'
import { ProtectedRoute } from '@/components/protected-route'
import { MetricCard } from '@/components/metric-card'
import { Worker } from '@/types'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { 
  Search, 
  RefreshCw, 
  Power, 
  Activity, 
  Clock, 
  Cpu, 
  MemoryStick,
  Server,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Loader,
  PlayCircle,
  StopCircle,
  Settings,
  Eye,
  TrendingUp,
  Users,
  UserPlus,
  Trash2
} from 'lucide-react'
import { useAuth } from '@/app/auth-context'
import { useRouter } from 'next/navigation'
import { apiClient, WorkerApiResponse } from '@/lib/api'

export default function WorkersPage() {
  const [workers, setWorkers] = useState<Worker[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [loading, setLoading] = useState(true)
  const [selectedWorker, setSelectedWorker] = useState<Worker | null>(null)
  const [addWorkerOpen, setAddWorkerOpen] = useState(false)
  const [newWorkerName, setNewWorkerName] = useState('')
  const [newWorkerCapabilities, setNewWorkerCapabilities] = useState('email_processing,data_processing,notification')
  const [addWorkerError, setAddWorkerError] = useState('')
  const [addWorkerLoading, setAddWorkerLoading] = useState(false)
  const [workerTasks, setWorkerTasks] = useState<any[]>([])
  const [workerTasksLoading, setWorkerTasksLoading] = useState(false)
  const { user } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (user && user.role !== 'admin') {
      router.push('/tasks')
    }
  }, [user, router])

  const fetchWorkers = async () => {
    try {
      const response = await apiClient.getWorkers({ limit: 100 })
      const mapped: Worker[] = response.workers.map((w: WorkerApiResponse) => ({
        id: w.id,
        status: w.status,
        last_heartbeat: w.last_heartbeat,
        tasks_processed: w.tasks_processed,
        current_task: w.current_task_id,
        uptime: w.uptime_seconds,
        memory_usage: w.memory_usage ?? undefined,
        cpu_usage: w.cpu_usage ?? undefined,
        version: w.version ?? undefined,
        capabilities: w.capabilities,
      }))
      setWorkers(mapped)
    } catch (error) {
      console.error('Failed to fetch workers:', error)
    } finally {
      setLoading(false)
    }
  }

  // Fetch workers on mount and auto-refresh every 15 seconds
  useEffect(() => {
    fetchWorkers()
    const interval = setInterval(fetchWorkers, 15000)
    return () => clearInterval(interval)
  }, [])

  const filteredWorkers = useMemo(() => {
    return workers.filter(worker => {
      const matchesStatus = statusFilter === 'all' || worker.status === statusFilter
      const matchesSearch = searchQuery === '' || 
        worker.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        worker.current_task?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        worker.capabilities?.some(cap => cap.toLowerCase().includes(searchQuery.toLowerCase()))
      
      return matchesStatus && matchesSearch
    })
  }, [workers, statusFilter, searchQuery])

  const workerStats = useMemo(() => {
    const stats = workers.reduce((acc, worker) => {
      acc.total++
      acc[worker.status] = (acc[worker.status] || 0) + 1
      acc.totalTasksProcessed += worker.tasks_processed
      return acc
    }, { total: 0, totalTasksProcessed: 0 } as Record<string, number>)
    
    const avgTasksProcessed = Math.round(stats.totalTasksProcessed / stats.total)
    const healthyWorkers = (stats.active || 0) + (stats.idle || 0)
    const healthPercentage = Math.round((healthyWorkers / stats.total) * 100)
    
    return { ...stats, avgTasksProcessed, healthPercentage } as Record<string, number> & { avgTasksProcessed: number; healthPercentage: number }
  }, [workers])

  const handleRefresh = async () => {
    setIsRefreshing(true)
    await fetchWorkers()
    setIsRefreshing(false)
  }

  const handleWorkerAction = (workerId: string, action: string) => {
    if (action === 'stop') {
      setWorkers(prev => prev.map(w => w.id === workerId ? { ...w, status: 'idle' as const } : w))
      alert(`⏹ Worker ${workerId} has been signaled to stop.`)
    } else if (action === 'start') {
      setWorkers(prev => prev.map(w => w.id === workerId ? { ...w, status: 'active' as const } : w))
      alert(`▶ Worker ${workerId} has been signaled to start.`)
    } else if (action === 'configure') {
      alert(`⚙ Configuration for worker ${workerId} — coming soon.`)
    }
  }

  const getStatusConfig = (status: Worker['status']) => {
    const configs = {
      active: { color: 'bg-green-100 text-green-800 border-green-200', icon: PlayCircle },
      idle: { color: 'bg-blue-100 text-blue-800 border-blue-200', icon: Clock },
      offline: { color: 'bg-gray-100 text-gray-800 border-gray-200', icon: StopCircle },
      error: { color: 'bg-red-100 text-red-800 border-red-200', icon: AlertTriangle }
    }
    return configs[status]
  }

  const formatUptime = (seconds: number) => {
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    
    if (hours > 0) {
      return `${hours}h ${minutes}m`
    } else {
      return `${minutes}m`
    }
  }

  const formatHeartbeat = (timestamp: string) => {
    const now = new Date()
    const then = new Date(timestamp)
    const diffMs = now.getTime() - then.getTime()
    const diffMinutes = Math.floor(diffMs / 60000)
    
    if (diffMinutes < 1) return 'Just now'
    if (diffMinutes < 60) return `${diffMinutes}m ago`
    return `${Math.floor(diffMinutes / 60)}h ago`
  }

  const clearFilters = () => {
    setStatusFilter('all')
    setSearchQuery('')
  }

  const handleAddWorker = async () => {
    if (!newWorkerName.trim()) return
    setAddWorkerLoading(true)
    setAddWorkerError('')
    try {
      const caps = newWorkerCapabilities.split(',').map(c => c.trim()).filter(Boolean)
      // Generate a 36-char UUID as the api_key (satisfies min_length=32)
      const apiKey = crypto.randomUUID() + crypto.randomUUID().slice(0, 4)
      await apiClient.registerWorker({
        worker_id: newWorkerName.trim(),
        capabilities: caps.length > 0 ? caps : ['data_processing'],
        api_key: apiKey,
      })
      setAddWorkerOpen(false)
      setNewWorkerName('')
      setNewWorkerCapabilities('email_processing,data_processing,notification')
      await fetchWorkers()
    } catch (err: any) {
      setAddWorkerError(err?.message || 'Failed to register worker')
    } finally {
      setAddWorkerLoading(false)
    }
  }

  const handleDeleteWorker = async (workerId: string) => {
    if (!confirm(`Delete worker "${workerId}"? This cannot be undone.`)) return
    try {
      await apiClient.deleteWorker(workerId)
      if (selectedWorker?.id === workerId) setSelectedWorker(null)
      await fetchWorkers()
    } catch (err: any) {
      alert(`Failed to delete worker: ${err?.message || 'Unknown error'}`)
    }
  }

  useEffect(() => {
    if (!selectedWorker) { setWorkerTasks([]); return }
    setWorkerTasksLoading(true)
    Promise.all([
      apiClient.getTasks({ locked_by: selectedWorker.id, limit: 100 }),
      apiClient.getTasks({ completed_by: selectedWorker.id, limit: 100 }),
    ]).then(([inProgress, completed]) => {
      const all = [...inProgress.tasks, ...completed.tasks]
      const seen = new Set<string>()
      setWorkerTasks(all.filter(t => { if (seen.has(t.id)) return false; seen.add(t.id); return true }))
    }).catch(() => {}).finally(() => setWorkerTasksLoading(false))
  }, [selectedWorker])

  return (
    <ProtectedRoute requiredRole="admin">
      <div className="flex h-screen bg-gray-50">
        <Sidebar />
        <main className="flex-1 overflow-auto">
          <div className="p-6 space-y-6">
            <div className="flex items-center justify-between">
              <Header
                title="Worker Management"
                description="Monitor and manage all system workers"
              />
              <div className="flex gap-2">
                <Button
                  onClick={() => { setAddWorkerError(''); setAddWorkerOpen(true) }}
                  className="flex items-center gap-2"
                >
                  <UserPlus className="w-4 h-4" />
                  Add Worker
                </Button>
                <Button 
                  onClick={handleRefresh} 
                  disabled={isRefreshing}
                  variant="outline"
                  className="flex items-center gap-2"
                >
                  <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
                  Refresh
                </Button>
              </div>
            </div>

            {loading && workers.length === 0 ? (
              <Card>
                <CardContent className="py-16 text-center">
                  <Loader className="w-8 h-8 animate-spin mx-auto mb-3 text-gray-400" />
                  <p className="text-gray-500">Loading workers…</p>
                </CardContent>
              </Card>
            ) : (
            <>
            {/* Worker Statistics */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <MetricCard
                title="Total Workers"
                value={workerStats.total}
                description="Registered in system"
                icon={Users}
                variant="default"
              />
              
              <MetricCard
                title="Active Workers"
                value={workerStats.active || 0}
                description="Currently processing"
                icon={Activity}
                trend={workerStats.active > 6 ? 'up' : 'down'}
                trendValue={`${Math.round((workerStats.active || 0) / workerStats.total * 100)}%`}
                variant="success"
              />
              
              <MetricCard
                title="System Health"
                value={`${workerStats.healthPercentage}%`}
                description="Workers operational"
                icon={CheckCircle}
                trend={workerStats.healthPercentage > 80 ? 'up' : 'down'}
                variant={workerStats.healthPercentage > 80 ? 'success' : 'warning'}
              />
              
              <MetricCard
                title="Avg Tasks/Worker"
                value={workerStats.avgTasksProcessed}
                description="Total processed"
                icon={TrendingUp}
                variant="default"
              />
            </div>

            {/* Status Overview Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {(['active', 'idle', 'offline', 'error'] as const).map((status) => {
                const count = workerStats[status] || 0
                const config = getStatusConfig(status)
                const IconComponent = config.icon
                
                return (
                  <Card 
                    key={status} 
                    className="cursor-pointer hover:shadow-md transition-shadow" 
                    onClick={() => setStatusFilter(status)}
                  >
                    <CardContent className="p-4 text-center">
                      <div className="flex items-center justify-center gap-2 mb-2">
                        <div className={`p-2 rounded-lg ${config.color}`}>
                          <IconComponent className="w-4 h-4" />
                        </div>
                      </div>
                      <div className="text-2xl font-bold text-gray-900">{count}</div>
                      <div className="text-sm text-gray-500 capitalize">{status}</div>
                    </CardContent>
                  </Card>
                )
              })}
            </div>

            {/* Filters and Search */}
            <Card>
              <CardContent className="p-6">
                <div className="flex flex-col lg:flex-row gap-4 items-start lg:items-end">
                  <div className="flex-1 space-y-2">
                    <label className="text-sm font-medium text-gray-700">Search Workers</label>
                    <div className="relative">
                      <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                      <Input
                        placeholder="Search by ID, task, or capabilities..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="pl-10 bg-white border-gray-300"
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <label className="text-sm font-medium text-gray-700">Status</label>
                    <Select value={statusFilter} onValueChange={setStatusFilter}>
                      <SelectTrigger className="w-40 bg-white border-gray-300">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-white border-gray-300">
                        <SelectItem value="all">All Status</SelectItem>
                        <SelectItem value="active">Active</SelectItem>
                        <SelectItem value="idle">Idle</SelectItem>
                        <SelectItem value="offline">Offline</SelectItem>
                        <SelectItem value="error">Error</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <Button
                    variant="outline"
                    onClick={clearFilters}
                    className="flex items-center gap-2"
                  >
                    Clear Filters
                  </Button>
                </div>

                <div className="flex items-center justify-between mt-4 pt-4 border-t border-gray-200">
                  <div className="flex items-center gap-4">
                    {(statusFilter !== 'all' || searchQuery) && (
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-gray-500">Active filters:</span>
                        {statusFilter !== 'all' && (
                          <Badge variant="secondary" className="bg-blue-100 text-blue-800">
                            Status: {statusFilter}
                          </Badge>
                        )}
                        {searchQuery && (
                          <Badge variant="secondary" className="bg-purple-100 text-purple-800">
                            Search: {searchQuery}
                          </Badge>
                        )}
                      </div>
                    )}
                  </div>
                  
                  <div className="text-sm text-gray-600">
                    Showing <span className="font-medium">{filteredWorkers.length}</span> of{' '}
                    <span className="font-medium">{workers.length}</span> workers
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Workers Table */}
            <Card>
              <CardContent className="p-0">
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow className="bg-gray-50">
                        <TableHead className="text-gray-900 font-medium py-4">Worker ID</TableHead>
                        <TableHead className="text-gray-900 font-medium py-4">Status</TableHead>
                        <TableHead className="text-gray-900 font-medium py-4">Current Task</TableHead>
                        <TableHead className="text-gray-900 font-medium py-4">Performance</TableHead>
                        <TableHead className="text-gray-900 font-medium py-4">Uptime</TableHead>
                        <TableHead className="text-gray-900 font-medium py-4">Last Heartbeat</TableHead>
                        <TableHead className="text-gray-900 font-medium py-4">Tasks Processed</TableHead>
                        <TableHead className="text-gray-900 font-medium py-4 text-center">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {filteredWorkers.map((worker) => {
                        const statusConfig = getStatusConfig(worker.status)
                        const StatusIcon = statusConfig.icon
                        
                        return (
                          <TableRow 
                            key={worker.id} 
                            className="border-b border-gray-100 hover:bg-gray-50 transition-colors"
                          >
                            <TableCell className="py-4">
                              <div className="flex items-center gap-2">
                                <code className="text-sm font-mono text-gray-700 bg-gray-100 px-2 py-1 rounded">
                                  {worker.id}
                                </code>
                                <Badge variant="outline" className="text-xs">
                                  {worker.version}
                                </Badge>
                              </div>
                            </TableCell>
                            
                            <TableCell className="py-4">
                              <Badge className={`${statusConfig.color} border font-medium`}>
                                <StatusIcon className="w-3 h-3 mr-1" />
                                {worker.status}
                              </Badge>
                            </TableCell>
                            
                            <TableCell className="py-4">
                              {worker.current_task ? (
                                <code className="text-xs bg-blue-50 text-blue-700 px-2 py-1 rounded">
                                  {worker.current_task}
                                </code>
                              ) : (
                                <span className="text-gray-400 text-sm">None</span>
                              )}
                            </TableCell>
                            
                            <TableCell className="py-4">
                              <div className="space-y-2 min-w-32">
                                <div className="flex items-center gap-2">
                                  <Cpu className="w-3 h-3 text-gray-400" />
                                  <div className="flex-1">
                                    <Progress value={worker.cpu_usage} className="h-2" />
                                  </div>
                                  <span className="text-xs text-gray-600">{worker.cpu_usage}%</span>
                                </div>
                                <div className="flex items-center gap-2">
                                  <MemoryStick className="w-3 h-3 text-gray-400" />
                                  <div className="flex-1">
                                    <Progress value={worker.memory_usage} className="h-2" />
                                  </div>
                                  <span className="text-xs text-gray-600">{worker.memory_usage}%</span>
                                </div>
                              </div>
                            </TableCell>
                            
                            <TableCell className="py-4">
                              <div className="flex items-center gap-1">
                                <Clock className="w-4 h-4 text-gray-400" />
                                <span className="text-sm text-gray-600">
                                  {worker.uptime ? formatUptime(worker.uptime) : 'Unknown'}
                                </span>
                              </div>
                            </TableCell>
                            
                            <TableCell className="py-4">
                              <span className="text-sm text-gray-600">
                                {formatHeartbeat(worker.last_heartbeat)}
                              </span>
                            </TableCell>
                            
                            <TableCell className="py-4">
                              <span className="font-medium text-gray-900">
                                {worker.tasks_processed.toLocaleString()}
                              </span>
                            </TableCell>
                            
                            <TableCell className="py-4">
                              <div className="flex items-center justify-center gap-1">
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => setSelectedWorker(worker)}
                                  className="h-8 w-8 p-0"
                                  title="View details & tasks"
                                >
                                  <Eye className="w-4 h-4" />
                                </Button>
                                
                                {worker.status === 'active' ? (
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => handleWorkerAction(worker.id, 'stop')}
                                    className="h-8 w-8 p-0 text-red-600 hover:text-red-900 hover:bg-red-50"
                                    title="Stop worker"
                                  >
                                    <StopCircle className="w-4 h-4" />
                                  </Button>
                                ) : (
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => handleWorkerAction(worker.id, 'start')}
                                    className="h-8 w-8 p-0 text-green-600 hover:text-green-900 hover:bg-green-50"
                                    title="Start worker"
                                  >
                                    <PlayCircle className="w-4 h-4" />
                                  </Button>
                                )}
                                
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => handleDeleteWorker(worker.id)}
                                  className="h-8 w-8 p-0 text-red-600 hover:text-red-900 hover:bg-red-50"
                                  title="Delete worker"
                                >
                                  <Trash2 className="w-4 h-4" />
                                </Button>
                              </div>
                            </TableCell>
                          </TableRow>
                        )
                      })}
                      
                      {filteredWorkers.length === 0 && (
                        <TableRow>
                          <TableCell colSpan={8} className="py-12 text-center">
                            <div className="flex flex-col items-center gap-2">
                              <div className="p-3 bg-gray-100 rounded-full">
                                <Server className="w-6 h-6 text-gray-400" />
                              </div>
                              <p className="text-gray-500 font-medium">No workers found</p>
                              <p className="text-sm text-gray-400">Try adjusting your search filters</p>
                            </div>
                          </TableCell>
                        </TableRow>
                      )}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>

            {/* Worker Details Modal */}
            {selectedWorker && (
              <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
                <Card className="w-full max-w-3xl max-h-[85vh] overflow-auto">
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <CardTitle className="flex items-center gap-2">
                        <Server className="w-5 h-5" />
                        {selectedWorker.id}
                      </CardTitle>
                      <div className="flex items-center gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDeleteWorker(selectedWorker.id)}
                          className="text-red-600 hover:text-red-900 hover:bg-red-50"
                        >
                          <Trash2 className="w-4 h-4 mr-1" /> Delete
                        </Button>
                        <Button variant="ghost" size="sm" onClick={() => setSelectedWorker(null)}>
                          <XCircle className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-6">
                    {/* Worker Info */}
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="text-sm font-medium text-gray-600">Status</label>
                        <div className="mt-1">
                          <Badge className={getStatusConfig(selectedWorker.status).color}>
                            {selectedWorker.status}
                          </Badge>
                        </div>
                      </div>
                      <div>
                        <label className="text-sm font-medium text-gray-600">Tasks Processed</label>
                        <p className="mt-1 text-lg font-semibold">{selectedWorker.tasks_processed.toLocaleString()}</p>
                      </div>
                    </div>

                    <div>
                      <label className="text-sm font-medium text-gray-600">Capabilities</label>
                      <div className="mt-2 flex flex-wrap gap-2">
                        {selectedWorker.capabilities?.map((cap) => (
                          <Badge key={cap} variant="outline" className="text-xs">{cap}</Badge>
                        ))}
                      </div>
                    </div>

                    {/* Worker Tasks */}
                    <div>
                      <label className="text-sm font-medium text-gray-600 mb-3 block">Task History</label>
                      {workerTasksLoading ? (
                        <div className="flex items-center justify-center py-6">
                          <Loader className="w-5 h-5 animate-spin text-gray-400 mr-2" />
                          <span className="text-sm text-gray-500">Loading tasks…</span>
                        </div>
                      ) : workerTasks.length === 0 ? (
                        <div className="text-center py-6 text-gray-400 text-sm border rounded-lg">
                          No tasks assigned to this worker yet.
                        </div>
                      ) : (
                        <div className="border rounded-lg overflow-hidden">
                          <Table>
                            <TableHeader>
                              <TableRow className="bg-gray-50">
                                <TableHead className="text-xs font-medium py-2">Task ID</TableHead>
                                <TableHead className="text-xs font-medium py-2">Type</TableHead>
                                <TableHead className="text-xs font-medium py-2">Status</TableHead>
                                <TableHead className="text-xs font-medium py-2">Created</TableHead>
                              </TableRow>
                            </TableHeader>
                            <TableBody>
                              {workerTasks.map((task) => (
                                <TableRow key={task.id} className="text-sm">
                                  <TableCell className="py-2 font-mono text-xs text-gray-700">
                                    {task.id.slice(0, 20)}…
                                  </TableCell>
                                  <TableCell className="py-2">
                                    <Badge variant="outline" className="text-xs">{task.type}</Badge>
                                  </TableCell>
                                  <TableCell className="py-2">
                                    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                                      task.status === 'completed' ? 'bg-green-100 text-green-700' :
                                      task.status === 'in_progress' ? 'bg-blue-100 text-blue-700' :
                                      task.status === 'failed' ? 'bg-red-100 text-red-700' :
                                      'bg-gray-100 text-gray-700'
                                    }`}>{task.status}</span>
                                  </TableCell>
                                  <TableCell className="py-2 text-xs text-gray-500">
                                    {new Date(task.created_at).toLocaleString()}
                                  </TableCell>
                                </TableRow>
                              ))}
                            </TableBody>
                          </Table>
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              </div>
            )}
          </>
          )}
          </div>
        </main>
      </div>

      {/* Add Worker Dialog */}
      <Dialog open={addWorkerOpen} onOpenChange={(open) => { if (!open) setAddWorkerOpen(false) }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Worker</DialogTitle>
            <DialogDescription>
              Register a new worker. Only registered workers can claim tasks.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div>
              <Label htmlFor="newWorkerName">Worker Name / ID</Label>
              <Input
                id="newWorkerName"
                value={newWorkerName}
                onChange={(e) => setNewWorkerName(e.target.value)}
                placeholder="e.g. John Smith"
                className="mt-1"
                autoFocus
                onKeyDown={(e) => { if (e.key === 'Enter') handleAddWorker() }}
              />
            </div>
            <div>
              <Label htmlFor="newWorkerCaps">Capabilities (comma-separated)</Label>
              <Input
                id="newWorkerCaps"
                value={newWorkerCapabilities}
                onChange={(e) => setNewWorkerCapabilities(e.target.value)}
                placeholder="email_processing,data_processing,notification"
                className="mt-1"
              />
              <p className="text-xs text-muted-foreground mt-1">Task types this worker is allowed to process</p>
            </div>
            {addWorkerError && (
              <p className="text-sm text-red-600">{addWorkerError}</p>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAddWorkerOpen(false)}>Cancel</Button>
            <Button onClick={handleAddWorker} disabled={!newWorkerName.trim() || addWorkerLoading}>
              {addWorkerLoading ? 'Registering...' : 'Add Worker'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </ProtectedRoute>
  )
}
