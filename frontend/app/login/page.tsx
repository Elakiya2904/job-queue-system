'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/app/auth-context'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const router = useRouter()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    
    try {
      await login(email, password)
      // Role is determined by backend, redirect based on response
      router.push('/dashboard')
    } catch (err) {
      setError('Login failed. Please check your credentials.')
      console.error('Login error:', err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-white flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="bg-white border border-neutral-300 rounded-xl p-8 shadow-sm">
          <h1 className="text-3xl font-bold text-black mb-2">Sign In</h1>
          <p className="text-neutral-600 mb-6">Access the job queue dashboard</p>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <Label htmlFor="email" className="text-black font-medium">
                Email
              </Label>
              <Input
                id="email"
                type="email"
                placeholder="admin@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="mt-2 border-neutral-300 rounded-lg text-black placeholder:text-neutral-400 focus:border-black focus:ring-black"
                required
              />
            </div>

            <div>
              <Label htmlFor="password" className="text-black font-medium">
                Password
              </Label>
              <Input
                id="password"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="mt-2 border-neutral-300 rounded-lg text-black placeholder:text-neutral-400 focus:border-black focus:ring-black"
                required
              />
            </div>

            {error && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-sm text-red-600">{error}</p>
              </div>
            )}

            <Button
              type="submit"
              disabled={loading}
              className="w-full bg-black text-white hover:bg-neutral-800 rounded-lg font-medium mt-6 disabled:opacity-50"
            >
              {loading ? 'Logging in...' : 'Login'}
            </Button>
          </form>

          <div className="mt-6 p-4 bg-neutral-100 rounded-lg border border-neutral-300">
            <p className="text-sm text-neutral-600 font-medium mb-2">Demo Credentials:</p>
            <p className="text-xs text-neutral-600">
              <span className="font-medium">Admin:</span> admin@example.com / admin12345
            </p>
            <p className="text-xs text-neutral-600">
              <span className="font-medium">User:</span> user@example.com / user12345
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
