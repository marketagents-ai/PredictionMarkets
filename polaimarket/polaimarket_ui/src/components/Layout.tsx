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