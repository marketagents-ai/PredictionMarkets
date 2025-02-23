'use client'
import { useState, useEffect } from 'react'

interface AgentAction {
  agentId: string
  round: number
  action: string
  outcome?: string
  price?: number
  timestamp: string
}

export function AgentActivityLog() {
  const [actions, setActions] = useState<AgentAction[]>([])
  const [isConnected, setIsConnected] = useState(false)

  useEffect(() => {
    let ws: WebSocket

    const connect = () => {
      ws = new WebSocket('ws://localhost:8004/agent_activity')
      
      ws.onopen = () => {
        console.log('Connected to agent activity feed')
        setIsConnected(true)
      }

      ws.onmessage = (event) => {
        const action = JSON.parse(event.data)
        setActions(prev => [action, ...prev].slice(0, 100))
      }

      ws.onclose = () => {
        console.log('Disconnected from agent activity feed')
        setIsConnected(false)
        setTimeout(connect, 3000)
      }

      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
      }
    }

    connect()
    return () => ws?.close()
  }, [])

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Agent Activity</h3>
        <div className={`h-2 w-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
      </div>
      
      <div className="h-[600px] overflow-y-auto space-y-2">
        {actions.map((action, i) => (
          <div key={i} className="bg-zinc-700 p-2 rounded text-sm">
            <div className="flex justify-between">
              <span className="font-bold">{action.agentId}</span>
              <span className="text-zinc-400">Round {action.round}</span>
            </div>
            <div>{action.action}</div>
            {action.outcome && (
              <div className="text-zinc-300">
                {action.outcome} @ {(action.price! * 100).toFixed(1)}%
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}