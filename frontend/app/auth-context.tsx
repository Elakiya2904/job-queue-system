'use client'

import { createContext, useContext, useState, ReactNode, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { User } from '@/types'
import { apiClient } from '@/lib/api'

interface AuthContextType {
  user: User | null
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  isAuthenticated: boolean
  isLoading: boolean
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const router = useRouter()

  const logout = useCallback(() => {
    setUser(null)
    localStorage.removeItem('user')
    localStorage.removeItem('auth_token')
    apiClient.clearToken()
    router.push('/login')
  }, [router])

  // Load user from localStorage on mount
  useEffect(() => {
    const savedUser = localStorage.getItem('user')
    const savedToken = localStorage.getItem('auth_token')
    
    if (savedUser && savedToken) {
      try {
        const parsedUser = JSON.parse(savedUser)
        setUser(parsedUser)
        // Ensure API client has the token
        apiClient.setToken(savedToken)
      } catch (e) {
        localStorage.removeItem('user')
        localStorage.removeItem('auth_token')
      }
    }
    setIsLoading(false)
  }, [])

  // Listen for 401 errors from the API client to trigger logout
  useEffect(() => {
    const handleUnauthorized = () => {
      if (user) {
        logout()
      }
    }
    window.addEventListener('auth:unauthorized', handleUnauthorized)
    return () => window.removeEventListener('auth:unauthorized', handleUnauthorized)
  }, [user, logout])

  const login = async (email: string, password: string) => {
    try {
      // Call real API to get token
      const response = await apiClient.login(email, password)
      
      const newUser: User = {
        id: response.user.id,
        email: response.user.email,
        role: response.user.role as 'admin' | 'user',
      }
      setUser(newUser)
      localStorage.setItem('user', JSON.stringify(newUser))
    } catch (error) {
      console.error('Login failed:', error)
      throw error
    }
  }

  return (
    <AuthContext.Provider value={{ user, login, logout, isAuthenticated: !!user, isLoading }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
