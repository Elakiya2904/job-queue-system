import type { Metadata } from 'next'
import { AuthProvider } from './auth-context'
import './globals.css'

export const metadata: Metadata = {
  title: 'Job Queue Dashboard',
  description: 'Distributed job queue management system',
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en">
      <body className="font-sans antialiased bg-white">
        <AuthProvider>
          {children}
        </AuthProvider>
      </body>
    </html>
  )
}
