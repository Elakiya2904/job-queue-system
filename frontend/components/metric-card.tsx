import { LucideIcon, TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { cn } from '@/lib/utils'

interface MetricCardProps {
  title: string
  value: number | string
  description?: string
  icon?: LucideIcon
  trend?: 'up' | 'down' | 'neutral'
  trendValue?: string
  variant?: 'default' | 'success' | 'warning' | 'danger'
  className?: string
  loading?: boolean
}

export function MetricCard({ 
  title, 
  value, 
  description, 
  icon: Icon,
  trend,
  trendValue,
  variant = 'default',
  className,
  loading = false
}: MetricCardProps) {
  const variantStyles = {
    default: 'bg-white border-gray-200',
    success: 'bg-green-50 border-green-200',
    warning: 'bg-yellow-50 border-yellow-200',
    danger: 'bg-red-50 border-red-200'
  }

  const getTrendIcon = () => {
    switch (trend) {
      case 'up':
        return <TrendingUp className="w-4 h-4 text-green-600" />
      case 'down':
        return <TrendingDown className="w-4 h-4 text-red-600" />
      case 'neutral':
        return <Minus className="w-4 h-4 text-gray-600" />
      default:
        return null
    }
  }

  const getTrendValueColor = () => {
    switch (trend) {
      case 'up':
        return 'text-green-600'
      case 'down':
        return 'text-red-600'
      case 'neutral':
        return 'text-gray-600'
      default:
        return 'text-gray-600'
    }
  }

  return (
    <div className={cn(
      "border rounded-lg p-6 shadow-sm transition-all duration-200 hover:shadow-md",
      variantStyles[variant],
      className
    )}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            {Icon && (
              <div className={cn(
                "p-2 rounded-lg",
                variant === 'success' && "bg-green-100 text-green-600",
                variant === 'warning' && "bg-yellow-100 text-yellow-600",
                variant === 'danger' && "bg-red-100 text-red-600",
                variant === 'default' && "bg-gray-100 text-gray-600"
              )}>
                <Icon className="w-5 h-5" />
              </div>
            )}
            <p className="text-sm font-medium text-gray-600">{title}</p>
          </div>
          
          {loading ? (
            <div className="animate-pulse">
              <div className="h-8 bg-gray-200 rounded w-20 mb-2"></div>
              {description && <div className="h-3 bg-gray-200 rounded w-32"></div>}
            </div>
          ) : (
            <>
              <p className="text-3xl font-bold text-gray-900 mb-1">
                {typeof value === 'number' ? value.toLocaleString() : value}
              </p>
              
              {(description || (trend && trendValue)) && (
                <div className="flex items-center gap-2 text-sm">
                  {trend && trendValue && (
                    <div className="flex items-center gap-1">
                      {getTrendIcon()}
                      <span className={getTrendValueColor()}>{trendValue}</span>
                    </div>
                  )}
                  {description && (
                    <span className="text-gray-500">
                      {trend && trendValue ? '•' : ''} {description}
                    </span>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
