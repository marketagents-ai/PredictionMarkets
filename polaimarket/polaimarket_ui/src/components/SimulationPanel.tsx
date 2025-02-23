'use client'
import { useState } from 'react'
import { SimulationControls } from './SimulationControls'
import { AgentActivityLog } from './AgentActivityLog'
import { LogPanel } from './LogPanel'
import { MarketDisplay } from './MarketDisplay'

export function SimulationPanel() {
  const [logs, setLogs] = useState<string[]>([])
  const [isRunning, setIsRunning] = useState(false)

  return (
    <div className="flex gap-4">
      {/* Controls panel - fixed width */}
      <div className="w-96 bg-zinc-800 min-h-screen p-4 border-r border-zinc-700">
        <h2 className="text-xl font-bold mb-4">Simulation Controls</h2>
        <SimulationControls 
          onLogsUpdate={setLogs}
          onRunningChange={setIsRunning}
          isRunning={isRunning}
        />
        <div className="mt-6">
          <h3 className="text-lg font-semibold mb-3">Agent Activity</h3>
          <AgentActivityLog />
        </div>
      </div>
      
      {/* Log panel - flexible width */}
      <div className="flex-1 min-w-[600px]">
        <LogPanel logs={logs} isRunning={isRunning} />
      </div>

      {/* Market display panel - fixed width */}
      <div className="w-96 bg-zinc-800 min-h-screen p-4 border-l border-zinc-700">
        <MarketDisplay 
          isLoading={isRunning}
          logs={logs.filter(log => log.includes('market_states') || log.includes('total_bets'))}
        />
      </div>
    </div>
  )
}