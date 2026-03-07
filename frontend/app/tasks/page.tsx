'use client'

import { useState, useMemo, useEffect } from 'react'
import { Sidebar } from '@/components/sidebar'
import { Header } from '@/components/header'
import { TasksTable } from '@/components/tasks-table'
import { ProtectedRoute } from '@/components/protected-route'
import { Task, apiClient } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Search, Filter, RefreshCw, Plus, Clock, CheckCircle, XCircle, AlertCircle, Loader } from 'lucide-react'
import { useAuth } from '@/app/auth-context'

export default function TasksPage() {
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin'
  const [tasks, setTasks] = useState<Task[]>([])
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [typeFilter, setTypeFilter] = useState<string>('all')
  const [searchQuery, setSearchQuery] = useState<string>('')
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [loading, setLoading] = useState(true)
  const [totalTasks, setTotalTasks] = useState(0)
  
  // Create task dialog state
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false)
  const [isCreating, setIsCreating] = useState(false)
  const [newTask, setNewTask] = useState({
    task_type: 'email_processing',
    payload: '{}',
    priority: 2,
  })

  const fetchTasks = async () => {
    try {
      setLoading(true)
      const params: any = { limit: 100, sort_by: 'created_at', sort_order: 'desc' }
      
      if (statusFilter !== 'all') params.status = statusFilter
      if (typeFilter !== 'all') params.task_type = typeFilter
      
      const response = await apiClient.getTasks(params)
      setTasks(response.tasks)
      setTotalTasks(response.total)
    } catch (error) {
      console.error('Failed to fetch tasks:', error)
    } finally {
      setLoading(false)
    }
  }

  const refreshTasks = async () => {
    setIsRefreshing(true)
    await fetchTasks()
    setIsRefreshing(false)
  }

  const handleCreateTask = async () => {
    try {
      setIsCreating(true)
      
      // Validate and parse JSON
      let payload
      try {
        payload = JSON.parse(newTask.payload)
      } catch (jsonError) {
        alert('Invalid JSON format. Please check your payload syntax.')
        return
      }
      
      // Create the task
      await apiClient.createTask({
        task_type: newTask.task_type,
        payload: payload,
        priority: newTask.priority,
      })
      
      // Success - close dialog and refresh
      setIsCreateDialogOpen(false)
      setNewTask({ task_type: 'email_processing', payload: '{}', priority: 2 })
      await fetchTasks() // Refresh the list
      
      // Show success message
      alert('✅ Task created successfully! It will be processed shortly.')
    } catch (error: any) {
      console.error('Failed to create task:', error)
      const errorMessage = error?.message || 'Unknown error'
      
      // Handle authentication errors specifically
      if (errorMessage.includes('401') || errorMessage.includes('authenticated') || errorMessage.includes('Unauthorized')) {
        alert('⚠️ Session expired. Please refresh the page and log in again.')
        // Optionally redirect to login
        window.location.href = '/login'
      } else {
        alert(`Failed to create task: ${errorMessage}\n\nIf you see authentication errors, please log in again.`)
      }
    } finally {
      setIsCreating(false)
    }
  }

  useEffect(() => {
    fetchTasks()
  }, [statusFilter, typeFilter])

  const filteredTasks = useMemo(() => {
    return tasks.filter((task) => {
      const matchesStatus = statusFilter === 'all' || task.status === statusFilter
      const matchesType = typeFilter === 'all' || task.type === typeFilter
      const matchesSearch = 
        searchQuery === '' ||
        task.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        task.type.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (task.locked_by && task.locked_by.toLowerCase().includes(searchQuery.toLowerCase()))
      
      return matchesStatus && matchesType && matchesSearch
    })
  }, [tasks, statusFilter, typeFilter, searchQuery])

  const taskStats = useMemo(() => {
    const stats = tasks.reduce((acc, task) => {
      acc.total++
      acc[task.status] = (acc[task.status] || 0) + 1
      return acc
    }, { total: 0 } as Record<string, number>)
    
    return stats
  }, [tasks])

  const handleRetry = async (taskId: string) => {
    try {
      await apiClient.performTaskAction(taskId, 'retry')
      await fetchTasks()
    } catch (error: any) {
      alert(`Failed to retry task: ${error?.message || 'Unknown error'}`)
    }
  }

  const handleDelete = async (taskId: string) => {
    if (!confirm('Permanently delete this task? This cannot be undone.')) return
    try {
      await apiClient.deleteTask(taskId)
      await fetchTasks()
    } catch (error: any) {
      alert(`Failed to delete task: ${error?.message || 'Unknown error'}`)
    }
  }

  const handleRefresh = async () => {
    await refreshTasks()
  }

  const clearFilters = () => {
    setStatusFilter('all')
    setTypeFilter('all')
    setSearchQuery('')
  }

  const uniqueTaskTypes = [...new Set(tasks.map(task => task.type))].sort()

  const statusConfig = isAdmin ? {
    queued: { icon: Clock, color: 'text-blue-600 bg-blue-100', count: taskStats.queued || 0 },
    processing: { icon: Loader, color: 'text-yellow-600 bg-yellow-100', count: taskStats.processing || 0 },
    completed: { icon: CheckCircle, color: 'text-green-600 bg-green-100', count: taskStats.completed || 0 },
    failed: { icon: AlertCircle, color: 'text-red-600 bg-red-100', count: taskStats.failed || 0 },
    failed_permanent: { icon: XCircle, color: 'text-gray-600 bg-gray-100', count: taskStats.failed_permanent || 0 },
  } : {
    queued: { icon: Clock, color: 'text-blue-600 bg-blue-100', count: taskStats.queued || 0 },
  }

  return (
    <ProtectedRoute>
      <div className="flex h-screen bg-gray-50">
        <Sidebar />
        <main className="flex-1 overflow-auto">
          <div className="p-6 space-y-6">
            <Header
              title="Task Management"
              description="Monitor and manage all job queue tasks across your system"
            />

            {/* Quick Stats */}
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
              <Card>
                <CardContent className="p-4 text-center">
                  <div className="text-2xl font-bold text-gray-900">{taskStats.total}</div>
                  <div className="text-sm text-gray-500">Total Tasks</div>
                </CardContent>
              </Card>
              
              {Object.entries(statusConfig).map(([status, config]) => {
                const IconComponent = config.icon
                return (
                  <Card key={status} className="cursor-pointer hover:shadow-md transition-shadow" onClick={() => setStatusFilter(status)}>
                    <CardContent className="p-4 text-center">
                      <div className="flex items-center justify-center gap-2 mb-2">
                        <div className={`p-1 rounded ${config.color}`}>
                          <IconComponent className="w-4 h-4" />
                        </div>
                      </div>
                      <div className="text-2xl font-bold text-gray-900">{config.count}</div>
                      <div className="text-sm text-gray-500 capitalize">{status.replace('_', ' ')}</div>
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
                    <label className="text-sm font-medium text-gray-700">Search Tasks</label>
                    <div className="relative">
                      <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                      <Input
                        placeholder="Search by ID, type, or worker..."
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
                        {isAdmin ? (
                          <>
                            <SelectItem value="all">All Statuses</SelectItem>
                            <SelectItem value="queued">Queued</SelectItem>
                            <SelectItem value="processing">Processing</SelectItem>
                            <SelectItem value="completed">Completed</SelectItem>
                            <SelectItem value="failed">Failed</SelectItem>
                            <SelectItem value="failed_permanent">Failed Permanent</SelectItem>
                          </>
                        ) : (
                          <SelectItem value="all">Queued</SelectItem>
                        )}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <label className="text-sm font-medium text-gray-700">Type</label>
                    <Select value={typeFilter} onValueChange={setTypeFilter}>
                      <SelectTrigger className="w-40 bg-white border-gray-300">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-white border-gray-300">
                        <SelectItem value="all">All Types</SelectItem>
                        {uniqueTaskTypes.map((type) => (
                          <SelectItem key={type} value={type} className="capitalize">
                            {type}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      onClick={clearFilters}
                      className="flex items-center gap-2"
                    >
                      <Filter className="w-4 h-4" />
                      Clear
                    </Button>
                    
                    <Button
                      onClick={handleRefresh}
                      disabled={isRefreshing}
                      className="flex items-center gap-2"
                    >
                      <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
                      Refresh
                    </Button>
                    
                    {isAdmin && (
                    <Button
                      onClick={() => setIsCreateDialogOpen(true)}
                      className="flex items-center gap-2 bg-black hover:bg-gray-800"
                    >
                      <Plus className="w-4 h-4" />
                      Create Task
                    </Button>
                    )}
                  </div>
                </div>

                <div className="flex items-center justify-between mt-4 pt-4 border-t border-gray-200">
                  <div className="flex items-center gap-4">
                    {(statusFilter !== 'all' || typeFilter !== 'all' || searchQuery) && (
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-gray-500">Active filters:</span>
                        {statusFilter !== 'all' && (
                          <Badge variant="secondary" className="bg-blue-100 text-blue-800">
                            Status: {statusFilter}
                          </Badge>
                        )}
                        {typeFilter !== 'all' && (
                          <Badge variant="secondary" className="bg-green-100 text-green-800">
                            Type: {typeFilter}
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
                    Showing <span className="font-medium">{filteredTasks.length}</span> of{' '}
                    <span className="font-medium">{tasks.length}</span> tasks
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Tasks Table */}
            <TasksTable
              tasks={filteredTasks}
              onRetry={handleRetry}
              onDelete={handleDelete}
            />
          </div>
        </main>
      </div>

      {/* Create Task Dialog */}
      <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>Create New Task</DialogTitle>
            <DialogDescription>
              Add a new task to the job queue system
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="task_type">Task Type</Label>
              <Select
                value={newTask.task_type}
                onValueChange={(value) => setNewTask({ ...newTask, task_type: value })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="email_processing">Email Processing</SelectItem>
                  <SelectItem value="data_processing">Data Processing</SelectItem>
                  <SelectItem value="file_conversion">File Conversion</SelectItem>
                  <SelectItem value="notification">Notification</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="priority">Priority</Label>
              <Select
                value={newTask.priority.toString()}
                onValueChange={(value) => setNewTask({ ...newTask, priority: parseInt(value) })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="1">Low (1)</SelectItem>
                  <SelectItem value="2">Normal (2)</SelectItem>
                  <SelectItem value="3">High (3)</SelectItem>
                  <SelectItem value="4">Urgent (4)</SelectItem>
                  <SelectItem value="5">Critical (5)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="payload">Payload (JSON)</Label>
              <Textarea
                id="payload"
                placeholder='{"key": "value"}'
                value={newTask.payload}
                onChange={(e) => setNewTask({ ...newTask, payload: e.target.value })}
                className="font-mono text-sm"
                rows={6}
              />
              <p className="text-xs text-gray-500">
                Enter valid JSON. Example for email_processing: {'{"recipient": "user@example.com", "template": "welcome"}'}
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setIsCreateDialogOpen(false)}
              disabled={isCreating}
            >
              Cancel
            </Button>
            <Button
              onClick={handleCreateTask}
              disabled={isCreating}
              className="bg-black hover:bg-gray-800"
            >
              {isCreating ? 'Creating...' : 'Create Task'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </ProtectedRoute>
  )
}
