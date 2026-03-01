'use client'

import { Task } from '@/lib/api'
import { useState } from 'react'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { TaskDetailsDrawer } from './task-details-drawer'
import { useAuth } from '@/app/auth-context'
import { Eye, RotateCcw, Trash2, Clock, User, Copy, AlertCircle, CheckCircle, XCircle, Loader } from 'lucide-react'

interface TasksTableProps {
  tasks: Task[]
  onRetry?: (taskId: string) => void
  onDelete?: (taskId: string) => void
}

export function TasksTable({ tasks, onRetry, onDelete }: TasksTableProps) {
  const [selectedTask, setSelectedTask] = useState<Task | null>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [copiedId, setCopiedId] = useState<string | null>(null)
  const { user } = useAuth()

  const getStatusBadge = (status: string) => {
    const statusConfigs = {
      queued: { 
        color: 'bg-blue-100 text-blue-800 border-blue-200', 
        icon: Clock 
      },
      processing: { 
        color: 'bg-yellow-100 text-yellow-800 border-yellow-200', 
        icon: Loader 
      },
      completed: { 
        color: 'bg-green-100 text-green-800 border-green-200', 
        icon: CheckCircle 
      },
      failed: { 
        color: 'bg-red-100 text-red-800 border-red-200', 
        icon: AlertCircle 
      },
      failed_permanent: { 
        color: 'bg-gray-100 text-gray-800 border-gray-200', 
        icon: XCircle 
      }
    }

    const config = statusConfigs[status as keyof typeof statusConfigs] || statusConfigs.queued
    const IconComponent = config.icon

    return (
      <Badge className={`${config.color} border font-medium`}>
        <IconComponent className="w-3 h-3 mr-1" />
        {status}
      </Badge>
    )
  }

  const copyToClipboard = async (text: string, taskId: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopiedId(taskId)
      setTimeout(() => setCopiedId(null), 2000)
    } catch (err) {
      console.error('Failed to copy text: ', err)
    }
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
    
    if (diffHours < 24) {
      return date.toLocaleTimeString('en-US', { 
        hour: '2-digit', 
        minute: '2-digit' 
      })
    } else {
      return date.toLocaleDateString('en-US', { 
        month: 'short', 
        day: 'numeric' 
      })
    }
  }

  const isAdmin = user?.role === 'admin'

  return (
    <>
      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader className="bg-gray-50">
              <TableRow className="border-b border-gray-200 hover:bg-gray-50">
                <TableHead className="text-gray-900 font-medium py-3">Task ID</TableHead>
                <TableHead className="text-gray-900 font-medium py-3">Type</TableHead>
                <TableHead className="text-gray-900 font-medium py-3">Status</TableHead>
                <TableHead className="text-gray-900 font-medium py-3 text-center">Retries</TableHead>
                <TableHead className="text-gray-900 font-medium py-3">Worker</TableHead>
                <TableHead className="text-gray-900 font-medium py-3">Created</TableHead>
                <TableHead className="text-gray-900 font-medium py-3 text-center">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {tasks.map((task) => (
                <TableRow 
                  key={task.id} 
                  className="border-b border-gray-100 hover:bg-gray-50 transition-colors duration-150"
                >
                  <TableCell className="py-4">
                    <div className="flex items-center gap-2 max-w-xs">
                      <code className="text-xs font-mono text-gray-700 bg-gray-100 px-2 py-1 rounded truncate">
                        {task.id}
                      </code>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => copyToClipboard(task.id, task.id)}
                        className="h-6 w-6 p-0 hover:bg-gray-200"
                      >
                        <Copy className={`w-3 h-3 ${copiedId === task.id ? 'text-green-600' : 'text-gray-400'}`} />
                      </Button>
                    </div>
                  </TableCell>
                  
                  <TableCell className="py-4">
                    <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200 font-medium">
                      {task.type}
                    </Badge>
                  </TableCell>
                  
                  <TableCell className="py-4">
                    {getStatusBadge(task.status)}
                  </TableCell>
                  
                  <TableCell className="py-4 text-center">
                    <div className="flex items-center justify-center gap-1">
                      <span className="text-sm font-medium text-gray-900">{task.retry_count}</span>
                      <span className="text-xs text-gray-500">/ {task.max_retries}</span>
                    </div>
                  </TableCell>
                  
                  <TableCell className="py-4">
                    <div className="flex items-center gap-2">
                      <User className="w-4 h-4 text-gray-400" />
                      <span className="text-sm text-gray-700">
                        {task.locked_by || 'Unassigned'}
                      </span>
                    </div>
                  </TableCell>
                  
                  <TableCell className="py-4">
                    <div className="flex items-center gap-2">
                      <Clock className="w-4 h-4 text-gray-400" />
                      <span className="text-sm text-gray-600">
                        {formatDate(task.created_at)}
                      </span>
                    </div>
                  </TableCell>
                  
                  <TableCell className="py-4">
                    <div className="flex items-center justify-center gap-1">
                      <Button
                        size="sm"
                        variant="ghost"
                        className="text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-md h-8 w-8 p-0"
                        onClick={() => {
                          setSelectedTask(task)
                          setDrawerOpen(true)
                        }}
                        title="View details"
                      >
                        <Eye className="w-4 h-4" />
                      </Button>
                      {isAdmin && task.status === 'failed' && (
                        <Button
                          size="sm"
                          variant="ghost"
                          className="text-blue-600 hover:text-blue-900 hover:bg-blue-50 rounded-md h-8 w-8 p-0"
                          onClick={() => onRetry?.(task.id)}
                          title="Retry task"
                        >
                          <RotateCcw className="w-4 h-4" />
                        </Button>
                      )}
                      {isAdmin && (
                        <Button
                          size="sm"
                          variant="ghost"
                          className="text-red-600 hover:text-red-900 hover:bg-red-50 rounded-md h-8 w-8 p-0"
                          onClick={() => onDelete?.(task.id)}
                          title="Delete task"
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
              {tasks.length === 0 && (
                <TableRow>
                  <TableCell colSpan={7} className="py-12 text-center">
                    <div className="flex flex-col items-center gap-2">
                      <div className="p-3 bg-gray-100 rounded-full">
                        <Clock className="w-6 h-6 text-gray-400" />
                      </div>
                      <p className="text-gray-500 font-medium">No tasks found</p>
                      <p className="text-sm text-gray-400">Tasks will appear here when they are created</p>
                    </div>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
      </div>

      <TaskDetailsDrawer
        task={selectedTask}
        open={drawerOpen}
        onOpenChange={setDrawerOpen}
        onRetry={onRetry}
        onCancel={onDelete}
      />
    </>
  )
}
