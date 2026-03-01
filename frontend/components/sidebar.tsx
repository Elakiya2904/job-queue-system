'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useAuth } from '@/app/auth-context'
import { cn } from '@/lib/utils'
import { LayoutGrid, ListTodo, Users, LogOut, Zap, AlertTriangle } from 'lucide-react'
import { Button } from '@/components/ui/button'

export function Sidebar() {
  const pathname = usePathname()
  const { user, logout } = useAuth()

  if (!user) return null

  const adminLinks = [
    { href: '/dashboard', label: 'Dashboard', icon: LayoutGrid },
    { href: '/tasks', label: 'Tasks', icon: ListTodo },
    { href: '/workers', label: 'Workers', icon: Users },
    { href: '/worker-dashboard', label: 'Worker View', icon: Zap },
    { href: '/dead-letter-queue', label: 'Failed Tasks', icon: AlertTriangle },
  ]

  const workerLinks = [
    { href: '/tasks', label: 'Tasks', icon: ListTodo },
    { href: '/worker-dashboard', label: 'Worker Dashboard', icon: Zap },
  ]

  const links = user.role === 'admin' ? adminLinks : workerLinks

  return (
    <div className="w-64 bg-white border-r border-neutral-300 h-screen flex flex-col">
      <div className="p-6 border-b border-neutral-300">
        <h1 className="text-2xl font-bold text-black">Queue</h1>
        <p className="text-sm text-neutral-600 mt-1">{user.role === 'admin' ? 'Admin' : 'Worker'}</p>
      </div>

      <nav className="flex-1 px-4 py-6 space-y-2">
        {links.map(({ href, label, icon: Icon }) => (
          <Link key={href} href={href}>
            <Button
              variant="ghost"
              className={cn(
                'w-full justify-start gap-2 rounded-xl',
                pathname === href
                  ? 'bg-black text-white'
                  : 'text-black hover:bg-neutral-100'
              )}
            >
              <Icon className="w-4 h-4" />
              {label}
            </Button>
          </Link>
        ))}
      </nav>

      <div className="p-4 border-t border-neutral-300">
        <div className="mb-4 text-sm text-neutral-600">
          <p className="font-medium text-black">{user.email}</p>
        </div>
        <Button
          onClick={logout}
          variant="outline"
          className="w-full justify-start gap-2 rounded-xl border-black text-black hover:bg-neutral-100"
        >
          <LogOut className="w-4 h-4" />
          Logout
        </Button>
      </div>
    </div>
  )
}
