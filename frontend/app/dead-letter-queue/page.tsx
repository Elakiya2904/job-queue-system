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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { AlertTriangle, RefreshCw, RotateCcw, Trash2, Eye, Clock } from 'lucide-react'

interface DeadLetterTask {
  task_id: string
  original_task: {
    id: string
    type: string
    status: string
    priority: number
    payload: any
    result?: any
    created_at: string
    retry_count: number
    max_retries: number
  }
  failure_count: number
  last_error?: string
  moved_to_dlq_at: string
}

export default function DeadLetterQueuePage() {
  const [deadLetterTasks, setDeadLetterTasks] = useState<DeadLetterTask[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedTask, setSelectedTask] = useState<DeadLetterTask | null>(null)
  const [retryDialogOpen, setRetryDialogOpen] = useState(false)
  const [retryResetCount, setRetryResetCount] = useState(true)
  const [retryNewPriority, setRetryNewPriority] = useState<number | ''>('')

  const fetchDeadLetterTasks = async () => {
    try {
      setLoading(true)
      const response = await apiClient.getDeadLetterTasks()
      setDeadLetterTasks(response.tasks)
    } catch (error) {
      console.error('Failed to fetch dead letter tasks:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchDeadLetterTasks()
  }, [])

  const handleRetryTask = async (task: DeadLetterTask) => {
    setSelectedTask(task)
    setRetryNewPriority('')
    setRetryResetCount(true)
    setRetryDialogOpen(true)
  }

  const confirmRetry = async () => {
    if (!selectedTask) return

    try {
      await apiClient.retryDeadLetterTask(selectedTask.task_id, {
        reset_retry_count: retryResetCount,
        new_priority: retryNewPriority ? Number(retryNewPriority) : undefined
      })
      
      setRetryDialogOpen(false)
      setSelectedTask(null)
      await fetchDeadLetterTasks()
      
      alert('✅ Task successfully moved back to processing queue!')
    } catch (error) {
      console.error('Failed to retry task:', error)
      alert('❌ Failed to retry task: ' + error)
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

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString()
  }

  const formatError = (error: string) => {
    if (error.length > 50) {
      return error.substring(0, 50) + '...'
    }
    return error
  }

  return (
    <ProtectedRoute>
      <div className="flex h-screen bg-background">
        <Sidebar />
        <div className="flex-1 flex flex-col overflow-hidden">
          <Header 
            title="Dead Letter Queue" 
            description="Manage tasks that have failed multiple times and need manual intervention"
          />
          <main className="flex-1 overflow-x-hidden overflow-y-auto bg-background p-6">
            <div className="mb-6">
              <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
                <AlertTriangle className="h-8 w-8 text-red-500" />
                Dead Letter Queue
              </h1>
              <p className="text-muted-foreground">
                Manage tasks that have failed multiple times and need manual intervention
              </p>
            </div>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <div>
                  <CardTitle>Failed Tasks ({deadLetterTasks.length})</CardTitle>
                  <CardDescription>
                    Tasks that have exceeded their maximum retry attempts
                  </CardDescription>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={fetchDeadLetterTasks}
                  disabled={loading}
                >
                  <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
                  Refresh
                </Button>
              </CardHeader>
              <CardContent>
                {deadLetterTasks.length === 0 ? (
                  <div className="text-center py-12">
                    <AlertTriangle className="h-16 w-16 text-muted-foreground mx-auto mb-4" />
                    <p className="text-muted-foreground text-lg">
                      No tasks in dead letter queue
                    </p>
                    <p className="text-muted-foreground text-sm">
                      All tasks are processing successfully!
                    </p>
                  </div>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Task ID</TableHead>
                        <TableHead>Type</TableHead>
                        <TableHead>Priority</TableHead>
                        <TableHead>Failures</TableHead>
                        <TableHead>Last Error</TableHead>
                        <TableHead>Failed At</TableHead>
                        <TableHead>Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {deadLetterTasks.map((dlTask) => (
                        <TableRow key={dlTask.task_id}>
                          <TableCell className="font-mono text-sm">
                            {dlTask.task_id.substring(0, 12)}...
                          </TableCell>
                          <TableCell>
                            <Badge variant="outline">
                              {dlTask.original_task.type}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            <Badge {...getPriorityBadge(dlTask.original_task.priority)}>
                              {getPriorityBadge(dlTask.original_task.priority).text}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            <span className="text-red-600 font-medium">
                              {dlTask.failure_count}/{dlTask.original_task.max_retries}
                            </span>
                          </TableCell>
                          <TableCell>
                            {dlTask.last_error ? (
                              <span className="text-muted-foreground text-sm" title={dlTask.last_error}>
                                {formatError(dlTask.last_error)}
                              </span>
                            ) : (
                              <span className="text-muted-foreground">-</span>
                            )}
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center gap-1 text-sm text-muted-foreground">
                              <Clock className="h-3 w-3" />
                              {formatDate(dlTask.moved_to_dlq_at)}
                            </div>
                          </TableCell>
                          <TableCell>
                            <div className="flex gap-2">
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => handleRetryTask(dlTask)}
                              >
                                <RotateCcw className="h-3 w-3 mr-1" />
                                Retry
                              </Button>
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => {
                                  setSelectedTask(dlTask)
                                  // Show task details in a modal (could be implemented)
                                }}
                              >
                                <Eye className="h-3 w-3" />
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </CardContent>
            </Card>

            {/* Retry Task Dialog */}
            <Dialog open={retryDialogOpen} onOpenChange={setRetryDialogOpen}>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Retry Failed Task</DialogTitle>
                  <DialogDescription>
                    Configure retry settings for task {selectedTask?.task_id}
                  </DialogDescription>
                </DialogHeader>
                
                {selectedTask && (
                  <div className="space-y-4">
                    <div className="bg-muted p-3 rounded-lg">
                      <h4 className="font-medium mb-2">Task Details</h4>
                      <div className="text-sm space-y-1">
                        <p><span className="font-medium">Type:</span> {selectedTask.original_task.type}</p>
                        <p><span className="font-medium">Priority:</span> {selectedTask.original_task.priority}</p>
                        <p><span className="font-medium">Failed:</span> {selectedTask.failure_count} times</p>
                        <p><span className="font-medium">Created:</span> {formatDate(selectedTask.original_task.created_at)}</p>
                        {selectedTask.last_error && (
                          <p><span className="font-medium">Last Error:</span> {selectedTask.last_error}</p>
                        )}
                      </div>
                    </div>

                    <div className="space-y-4">
                      <div className="flex items-center space-x-2">
                        <input
                          type="checkbox"
                          id="resetRetryCount"
                          checked={retryResetCount}
                          onChange={(e) => setRetryResetCount(e.target.checked)}
                          className="rounded border-gray-300"
                        />
                        <Label htmlFor="resetRetryCount" className="text-sm">
                          Reset retry count to 0
                        </Label>
                      </div>

                      <div>
                        <Label htmlFor="newPriority" className="text-sm">
                          New Priority (optional)
                        </Label>
                        <Input
                          id="newPriority"
                          type="number"
                          min="1"
                          max="4"
                          value={retryNewPriority}
                          onChange={(e) => setRetryNewPriority(e.target.value ? parseInt(e.target.value) : '')}
                          placeholder="Leave empty to keep current priority"
                          className="mt-1"
                        />
                        <p className="text-xs text-muted-foreground mt-1">
                          1=Low, 2=Normal, 3=High, 4=Critical
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                <DialogFooter>
                  <Button
                    variant="outline"
                    onClick={() => setRetryDialogOpen(false)}
                  >
                    Cancel
                  </Button>
                  <Button onClick={confirmRetry}>
                    <RotateCcw className="h-4 w-4 mr-2" />
                    Retry Task
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