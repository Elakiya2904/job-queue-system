'use client'

interface HeaderProps {
  title: string
  description?: string
}

export function Header({ title, description }: HeaderProps) {
  return (
    <div className="mb-8">
      <h1 className="text-4xl font-bold text-black">{title}</h1>
      {description && <p className="text-neutral-600 mt-2">{description}</p>}
    </div>
  )
}
