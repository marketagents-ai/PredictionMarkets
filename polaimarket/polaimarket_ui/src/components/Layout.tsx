'use client'
import React from 'react'
import { Header } from './Header'
import { SimulationPanel } from './SimulationPanel'

export function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-zinc-900 text-white">
      <Header />
      <div className="flex">
        <SimulationPanel />
        <main className="flex-1 p-6">
          {children}
        </main>
      </div>
    </div>
  )
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="dark h-full">
      <body className="h-full overflow-hidden bg-zinc-900 text-white">
        {children}
      </body>
    </html>
  )
}