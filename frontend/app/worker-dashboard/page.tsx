'use client'

import { useState, useEffect } from 'react'
import { Sidebar } from '@/components/sidebar'
import { Header } from '@/components/header'
import { ProtectedRoute } from '@/components/protected-route'
import { apiClient } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
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
import { Clock, RefreshCw, Play, CheckCircle, XCircle, AlertCircle, Loader, User, Zap } from 'lucide-react'

interface Task {
  id: string
  type: string
  status: string
  priority: number
  payload: any
  result?: any
  created_at: string
  locked_by?: string
  progress_percentage?: number
}

interface WorkerTaskClaim {
  task_id: string
  task: Task
  lock_expires_at: string
}

export default function WorkerDashboardPage() {
  const [availableTasks, setAvailableTasks] = useState<Task[]>([])
  const [claimedTasks, setClaimedTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)
  const [workerId, setWorkerId] = useState('worker_frontend_01')
  const [taskTypes, setTaskTypes] = useState('email_processing,data_processing,notification')
  
  // Task execution dialog
  const [executingTask, setExecutingTask] = useState<Task | null>(null)
  const [executionProgress, setExecutionProgress] = useState(0)
  const [executionStatus, setExecutionStatus] = useState('')
  const [executionResult, setExecutionResult] = useState('')

  const fetchAvailableTasks = async () => {
    try {
      const response = await apiClient.getWorkerTasks(taskTypes)
      // Ensure we only show queued tasks that are available for claiming
      const queuedTasks = response.tasks.filter((task: Task) => task.status === 'queued')
      setAvailableTasks(queuedTasks)
    } catch (error) {
      console.error('Failed to fetch available tasks:', error)
    }
  }

  const fetchClaimedTasks = async () => {
    try {
      // Get only tasks locked by this specific worker
      const response = await apiClient.getTasks({
        status: 'in_progress',
        locked_by: workerId,
        limit: 50
      })
      setClaimedTasks(response.tasks)
    } catch (error) {
      console.error('Failed to fetch claimed tasks:', error)
    }
  }

  const refreshData = async () => {
    setLoading(true)
    await Promise.all([fetchAvailableTasks(), fetchClaimedTasks()])
    setLoading(false)
  }

  useEffect(() => {
    refreshData()
    
    // Auto-refresh every 5 seconds
    const interval = setInterval(refreshData, 5000)
    return () => clearInterval(interval)
  }, [taskTypes, workerId])

  const handleClaimTask = async (taskId: string) => {
    try {
      const claim: WorkerTaskClaim = await apiClient.claimTask(taskId, {
        worker_id: workerId,
        lock_timeout: 300
      })
      
      console.log('🎯 Task claimed successfully:', claim)
      await refreshData()
      
      // Start executing the task
      setExecutingTask(claim.task)
      setExecutionProgress(0)
      setExecutionStatus('Task claimed, starting execution...')
      executeTask(claim.task)
      
    } catch (error) {
      console.error('Failed to claim task:', error)
      alert('Failed to claim task: ' + error)
    }
  }

  const executeTask = async (task: Task) => {
    try {
      // Simulate task execution with progress updates
      const steps = [
        'Initializing task...',
        'Processing payload...',
        'Executing business logic...',
        'Generating results...',
        'Finalizing...'
      ]
      
      for (let i = 0; i < steps.length; i++) {
        setExecutionStatus(steps[i])
        setExecutionProgress(((i + 1) / steps.length) * 100)
        
        // Update progress via API
        await apiClient.updateTaskProgress(task.id, {
          worker_id: workerId,
          progress_percentage: ((i + 1) / steps.length) * 100,
          status_message: steps[i]
        })
        
        // Simulate work delay
        await new Promise(resolve => setTimeout(resolve, 1500))
      }
      
      // Generate mock result based on task type
      let result = {}
      if (task.type === 'email_processing') {
        result = {
          email_sent: true,
          recipient: task.payload.to || 'user@example.com',
          message_id: `msg_${Date.now()}`,
          delivery_time: new Date().toISOString()
        }
      } else if (task.type === 'data_processing') {
        result = {
          records_processed: Math.floor(Math.random() * 1000) + 100,
          processing_time: `${(Math.random() * 5 + 1).toFixed(2)}s`,
          output_file: `processed_${Date.now()}.csv`
        }
      } else if (task.type === 'notification') {
        result = {
          notifications_sent: task.payload.user_ids?.length || 1,
          channels: task.payload.channels || ['email'],
          delivery_status: 'delivered'
        }
      } else {
        result = {
          status: 'completed',
          execution_time: `${(Math.random() * 3 + 1).toFixed(2)}s`,
          message: `Successfully processed ${task.type} task`
        }
      }
      
      setExecutionResult(JSON.stringify(result, null, 2))
      
      // Complete the task
      await apiClient.completeTask(task.id, {
        worker_id: workerId,
        result: result,
        execution_time: 7.5
      })
      
      setExecutionStatus('✅ Task completed successfully!')
      
      // Refresh data and close dialog after 2 seconds
      setTimeout(() => {
        setExecutingTask(null)
        refreshData()
      }, 2000)
      
    } catch (error) {
      console.error('Task execution failed:', error)
      
      // Mark task as failed
      try {
        await apiClient.failTask(task.id, {
          worker_id: workerId,
          error_message: `Execution failed: ${error}`,
          should_retry: true
        })
      } catch (failError) {
        console.error('Failed to mark task as failed:', failError)
      }
      
      setExecutionStatus(`❌ Task failed: ${error}`)
      setTimeout(() => {
        setExecutingTask(null)
        refreshData()
      }, 2000)
    }
  }

  const handleFailTask = async (taskId: string, errorMessage: string) => {
    try {
      await apiClient.failTask(taskId, {
        worker_id: workerId,
        error_message: errorMessage,
        should_retry: true
      })
      await refreshData()
    } catch (error) {
      console.error('Failed to fail task:', error)
    }
  }

  const getPriorityBadge = (priority: number) => {
    const variants = {
      4: { variant: 'destructive' as const, text: 'Critical' },
      3: { variant: 'default' as const, text: 'High' },
      2: { variant: 'secondary' as const, text: 'Normal' },
      1: { variant: 'outline' as const, text: 'Low' }
    }
    return variants[priority as keyof typeof variants] || variants[2]
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'queued': return <Clock className="h-4 w-4" />
      case 'in_progress': return <Loader className="h-4 w-4 animate-spin" />
      case 'completed': return <CheckCircle className="h-4 w-4" />
      case 'failed': return <XCircle className="h-4 w-4" />
      case 'dead_letter': return <AlertCircle className="h-4 w-4" />
      default: return <Clock className="h-4 w-4" />
    }
  }

  return (
    <ProtectedRoute>
      <div className="flex h-screen bg-background">
        <Sidebar />
        <div className="flex-1 flex flex-col overflow-hidden">
          <Header 
            title="Worker Dashboard" 
            description="Claim and process available tasks from the queue"
          />
          <main className="flex-1 overflow-x-hidden overflow-y-auto bg-background p-6">
            <div className="mb-6">
              <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
                <User className="h-8 w-8" />
                Worker Dashboard
              </h1>
              <p className="text-muted-foreground">
                Claim and process available tasks from the queue
              </p>
            </div>

            {/* Worker Configuration */}
            <Card className="mb-6">
              <CardHeader>
                <CardTitle>Worker Configuration</CardTitle>
                <CardDescription>Configure your worker settings</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="workerId">Worker ID</Label>
                    <Input
                      id="workerId"
                      value={workerId}
                      onChange={(e) => setWorkerId(e.target.value)}
                      placeholder="Enter worker ID"
                    />
                  </div>
                  <div>
                    <Label htmlFor="taskTypes">Supported Task Types</Label>
                    <Input
                      id="taskTypes"
                      value={taskTypes}
                      onChange={(e) => setTaskTypes(e.target.value)}
                      placeholder="email_processing,data_processing"
                    />
                  </div>
                </div>
              </CardContent>
            </Card>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              
              {/* Available Tasks */}
              <Card>
                <CardHeader className="flex flex-row items-center justify-between">
                  <div>
                    <CardTitle className="flex items-center gap-2">
                      <Zap className="h-5 w-5" />
                      Available Tasks ({availableTasks.length})
                    </CardTitle>
                    <CardDescription>Queued tasks ready to be claimed</CardDescription>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={refreshData}
                    disabled={loading}
                  >
                    <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
                  </Button>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {availableTasks.length === 0 ? (
                      <p className="text-muted-foreground text-center py-8">
                        No tasks available for claiming
                      </p>
                    ) : (
                      availableTasks.map((task) => (
                        <div key={task.id} className="border rounded-lg p-3">
                          <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-2">
                              {getStatusIcon(task.status)}
                              <span className="font-medium">{task.type}</span>
                            </div>
                            <Badge {...getPriorityBadge(task.priority)}>
                              {getPriorityBadge(task.priority).text}
                            </Badge>
                          </div>
                          <p className="text-sm text-muted-foreground mb-3">
                            ID: {task.id}
                          </p>
                          <p className="text-sm text-muted-foreground mb-3">
                            Created: {new Date(task.created_at).toLocaleString()}
                          </p>
                          <Button
                            size="sm"
                            onClick={() => handleClaimTask(task.id)}
                            className="w-full"
                          >
                            <Play className="h-4 w-4 mr-2" />
                            Claim Task
                          </Button>
                        </div>
                      ))
                    )}
                  </div>
                </CardContent>
              </Card>

              {/* Claimed Tasks */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Loader className="h-5 w-5" />
                    My Tasks ({claimedTasks.length})
                  </CardTitle>
                  <CardDescription>Tasks currently being processed by you</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {claimedTasks.length === 0 ? (
                      <p className="text-muted-foreground text-center py-8">
                        No tasks currently claimed
                      </p>
                    ) : (
                      claimedTasks.map((task) => (
                        <div key={task.id} className="border rounded-lg p-3">
                          <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-2">
                              {getStatusIcon(task.status)}
                              <span className="font-medium">{task.type}</span>
                            </div>
                            <Badge variant="default">In Progress</Badge>
                          </div>
                          <p className="text-sm text-muted-foreground mb-2">
                            ID: {task.id}
                          </p>
                          {task.result?.progress_percentage && (
                            <div className="mb-2">
                              <div className="flex justify-between text-sm">
                                <span>Progress</span>
                                <span>{task.result.progress_percentage}%</span>
                              </div>
                              <div className="w-full bg-gray-200 rounded-full h-2">
                                <div 
                                  className="bg-blue-600 h-2 rounded-full" 
                                  style={{ width: `${task.result.progress_percentage}%` }}
                                />
                              </div>
                            </div>
                          )}
                          <div className="flex gap-2">
                            <Button
                              size="sm"
                              variant="destructive"
                              onClick={() => handleFailTask(task.id, 'Manual failure by worker')}
                              className="flex-1"
                            >
                              <XCircle className="h-4 w-4 mr-2" />
                              Mark Failed
                            </Button>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Task Execution Dialog */}
            <Dialog open={!!executingTask} onOpenChange={() => setExecutingTask(null)}>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Executing Task</DialogTitle>
                  <DialogDescription>
                    Task {executingTask?.id} is being processed...
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4">
                  <div>
                    <div className="flex justify-between text-sm mb-2">
                      <span>Progress</span>
                      <span>{Math.round(executionProgress)}%</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-3">
                      <div 
                        className="bg-blue-600 h-3 rounded-full transition-all duration-300" 
                        style={{ width: `${executionProgress}%` }}
                      />
                    </div>
                  </div>
                  <div>
                    <Label>Status</Label>
                    <p className="text-sm text-muted-foreground">{executionStatus}</p>
                  </div>
                  {executionResult && (
                    <div>
                      <Label>Result</Label>
                      <Textarea
                        value={executionResult}
                        readOnly
                        className="font-mono text-xs"
                        rows={8}
                      />
                    </div>
                  )}
                </div>
                <DialogFooter>
                  <Button 
                    variant="outline" 
                    onClick={() => setExecutingTask(null)}
                    disabled={executionProgress > 0 && executionProgress < 100}
                  >
                    Close
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>

          </main>
        </div>
      </div>
    </ProtectedRoute>
  )
}