'use client'
import { useState } from 'react'
import { SimulationControls } from './SimulationControls'
import { AgentActivityLog } from './AgentActivityLog'

export function SimulationPanel() {
  return (
    <div className="w-96 bg-zinc-800 min-h-screen p-4 border-r border-zinc-700">
      <h2 className="text-xl font-bold mb-4">Simulation Controls</h2>
      <SimulationControls />
      <div className="mt-6">
        <h3 className="text-lg font-semibold mb-3">Agent Activity</h3>
        <AgentActivityLog />
      </div>
    </div>
  )
}