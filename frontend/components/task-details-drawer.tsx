'use client'

import { useState } from 'react'
import { Task } from '@/types'
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '@/components/ui/sheet'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { Copy, Clock, User, RefreshCw, AlertCircle, CheckCircle, XCircle, Loader, Eye } from 'lucide-react'

interface TaskDetailsDrawerProps {
  task: Task | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onRetry?: (taskId: string) => void
  onCancel?: (taskId: string) => void
}

export function TaskDetailsDrawer({ task, open, onOpenChange, onRetry, onCancel }: TaskDetailsDrawerProps) {
  const [copiedId, setCopiedId] = useState(false)
  const [showFullResult, setShowFullResult] = useState(false)

  if (!task) return null

  const getStatusConfig = (status: string) => {
    const configs = {
      queued: { color: 'bg-blue-100 text-blue-800 border-blue-200', icon: Clock },
      processing: { color: 'bg-yellow-100 text-yellow-800 border-yellow-200', icon: Loader },
      completed: { color: 'bg-green-100 text-green-800 border-green-200', icon: CheckCircle },
      failed: { color: 'bg-red-100 text-red-800 border-red-200', icon: AlertCircle },
      failed_permanent: { color: 'bg-gray-100 text-gray-800 border-gray-200', icon: XCircle }
    }
    return configs[status as keyof typeof configs] || configs.queued
  }

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopiedId(true)
      setTimeout(() => setCopiedId(false), 2000)
    } catch (err) {
      console.error('Failed to copy text: ', err)
    }
  }

  const formatDuration = (createdAt: string) => {
    const now = new Date()
    const created = new Date(createdAt)
    const diffMs = now.getTime() - created.getTime()
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
    const diffMinutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60))
    
    if (diffHours > 0) {
      return `${diffHours}h ${diffMinutes}m ago`
    } else if (diffMinutes > 0) {
      return `${diffMinutes}m ago`
    } else {
      return 'Just now'
    }
  }

  const statusConfig = getStatusConfig(task.status)
  const StatusIcon = statusConfig.icon

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full sm:w-[600px] bg-gray-50 overflow-y-auto">
        <SheetHeader className="space-y-4 pb-6">
          <div className="flex items-center justify-between">
            <SheetTitle className="text-2xl font-semibold text-gray-900">Task Details</SheetTitle>
            <div className="flex items-center gap-2">
              <Badge variant="outline" className={`${statusConfig.color} font-medium border`}>
                <StatusIcon className="w-3 h-3 mr-1" />
                {task.status}
              </Badge>
            </div>
          </div>
          
          <div className="flex items-center gap-2 text-sm text-gray-600">
            <span className="font-medium">Task ID:</span>
            <code className="bg-gray-100 px-2 py-1 rounded text-xs font-mono">{task.id}</code>
            <Button 
              variant="ghost" 
              size="sm" 
              onClick={() => copyToClipboard(task.id)}
              className="h-6 w-6 p-0"
            >
              <Copy className={`w-3 h-3 ${copiedId ? 'text-green-600' : 'text-gray-400'}`} />
            </Button>
            {copiedId && <span className="text-xs text-green-600 font-medium">Copied!</span>}
          </div>
        </SheetHeader>

        <div className="space-y-6">
          {/* Basic Information Card */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Eye className="w-4 h-4" />
                Overview
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm font-medium text-gray-600 mb-1">Task Type</p>
                  <div className="flex items-center gap-2">
                    <Badge variant="secondary" className="bg-blue-50 text-blue-700 border-blue-200">
                      {task.type}
                    </Badge>
                  </div>
                </div>
                
                <div>
                  <p className="text-sm font-medium text-gray-600 mb-1">Retry Attempts</p>
                  <div className="flex items-center gap-2">
                    <RefreshCw className="w-4 h-4 text-gray-400" />
                    <span className="text-base font-medium">{task.retry_count}</span>
                    <span className="text-sm text-gray-500">/ 3 max</span>
                  </div>
                </div>
              </div>

              <Separator />

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm font-medium text-gray-600 mb-1">{task.completed_by ? 'Completed By' : 'Assigned Worker'}</p>
                  <div className="flex items-center gap-2">
                    <User className="w-4 h-4 text-gray-400" />
                    <span className="text-base">{task.completed_by || task.locked_by || 'Unassigned'}</span>
                  </div>
                </div>
                
                <div>
                  <p className="text-sm font-medium text-gray-600 mb-1">Created</p>
                  <div className="flex items-center gap-2">
                    <Clock className="w-4 h-4 text-gray-400" />
                    <div className="flex flex-col">
                      <span className="text-sm">{formatDuration(task.created_at)}</span>
                      <span className="text-xs text-gray-500">
                        {new Date(task.created_at).toLocaleString()}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Result Section */}
          {task.result && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <CheckCircle className="w-4 h-4 text-green-600" />
                    Execution Result
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setShowFullResult(!showFullResult)}
                  >
                    {showFullResult ? 'Collapse' : 'Expand'}
                  </Button>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="relative">
                  <pre className={`text-xs bg-green-50 border border-green-200 rounded-lg p-4 overflow-auto font-mono text-green-900 ${
                    showFullResult ? 'max-h-none' : 'max-h-32'
                  }`}>
                    {JSON.stringify(task.result, null, 2)}
                  </pre>
                  {!showFullResult && (
                    <div className="absolute bottom-0 left-0 right-0 h-8 bg-gradient-to-t from-green-50 to-transparent pointer-events-none" />
                  )}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Error Section */}
          {task.error_message && (
            <Card className="border-red-200">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2 text-red-700">
                  <XCircle className="w-4 h-4" />
                  Error Details
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                  <p className="text-sm text-red-800 font-medium mb-2">Error Message:</p>
                  <p className="text-sm text-red-700 whitespace-pre-wrap">{task.error_message}</p>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Actions Section */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Actions</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex gap-3 flex-wrap">
                {task.status === 'failed' && onRetry && (
                  <Button 
                    onClick={() => onRetry(task.id)}
                    className="flex items-center gap-2"
                    variant="default"
                  >
                    <RefreshCw className="w-4 h-4" />
                    Retry Task
                  </Button>
                )}
                
                {(task.status === 'queued' || task.status === 'processing') && onCancel && (
                  <Button 
                    onClick={() => onCancel(task.id)}
                    variant="destructive"
                    className="flex items-center gap-2"
                  >
                    <XCircle className="w-4 h-4" />
                    Cancel Task
                  </Button>
                )}

                <Button 
                  variant="outline"
                  onClick={() => copyToClipboard(JSON.stringify(task, null, 2))}
                  className="flex items-center gap-2"
                >
                  <Copy className="w-4 h-4" />
                  Copy Task Data
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </SheetContent>
    </Sheet>
  )
}
