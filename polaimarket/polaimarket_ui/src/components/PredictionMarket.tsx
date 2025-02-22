'use client'
import { useState, useEffect } from 'react'
import { OrderBook } from './OrderBook'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'

interface MarketState {
  description: string
  marketType: "BINARY" | "CATEGORICAL"
  currentPrices: Record<string, number>
  totalLiquidity: number
  outcomes: string[]
  volume: number
  resolutionDate: string
  priceHistory: Array<{
    timestamp: number
    prices: Record<string, number>
  }>
}

interface AgentAction {
  agent_id: string
  action_type: "BET" | "HOLD"
  outcome?: string
  stake?: number
  price?: number
  timestamp: string
}

export function PredictionMarket() {
  const [marketState, setMarketState] = useState<MarketState | null>(null)
  const [agentActions, setAgentActions] = useState<AgentAction[]>([])
  const [timeRange, setTimeRange] = useState<'1H' | '6H' | '1D' | '1W' | '1M' | 'ALL'>('ALL')

  useEffect(() => {
    // Market state websocket
    const marketWs = new WebSocket('ws://localhost:8004/market')
    const agentWs = new WebSocket('ws://localhost:8004/agent_activity')
    
    marketWs.onmessage = (event) => {
      const data = JSON.parse(event.data)
      setMarketState(data)
    }

    agentWs.onmessage = (event) => {
      const action = JSON.parse(event.data)
      setAgentActions(prev => [action, ...prev].slice(0, 50)) // Keep last 50 actions
    }

    return () => {
      marketWs.close()
      agentWs.close()
    }
  }, [])

  if (!marketState) return <div>Loading market...</div>

  const timeRangeButtons = [
    { label: '1H', value: '1H' },
    { label: '6H', value: '6H' },
    { label: '1D', value: '1D' },
    { label: '1W', value: '1W' },
    { label: '1M', value: '1M' },
    { label: 'ALL', value: 'ALL' },
  ]

  return (
    <div className="max-w-7xl mx-auto">
      {/* Market Header */}
      <div className="bg-zinc-900 p-4 rounded-t-lg border-b border-zinc-800">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold">{marketState.description}</h2>
          <div className="flex items-center space-x-4 text-sm text-zinc-400">
            <div className="flex items-center">
              <span className="mr-2">📅</span>
              <span>{marketState.resolutionDate}</span>
            </div>
            <div className="flex items-center">
              <span className="mr-2">💰</span>
              <span>${marketState.volume.toLocaleString()} Vol.</span>
            </div>
          </div>
        </div>

        {/* Time Range Selector */}
        <div className="flex space-x-2">
          {timeRangeButtons.map(({ label, value }) => (
            <button
              key={value}
              onClick={() => setTimeRange(value as typeof timeRange)}
              className={`px-3 py-1 rounded-md text-sm ${
                timeRange === value 
                  ? 'bg-white text-black' 
                  : 'bg-zinc-800 text-zinc-300 hover:bg-zinc-700'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-12 gap-4 p-4 bg-zinc-900">
        {/* Left Column - Chart and Outcomes */}
        <div className="col-span-8 space-y-4">
          {/* Price Chart */}
          <div className="bg-zinc-800 p-4 rounded-lg h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={marketState.priceHistory}>
                {Object.keys(marketState.currentPrices).map((outcome, idx) => (
                  <Line
                    key={outcome}
                    type="monotone"
                    dataKey={`prices.${outcome}`}
                    stroke={
                      outcome === 'Yes' ? '#22c55e' : 
                      outcome === 'No' ? '#ef4444' : 
                      `#${Math.floor(Math.random()*16777215).toString(16)}`
                    }
                    dot={false}
                  />
                ))}
                <XAxis 
                  dataKey="timestamp" 
                  tickFormatter={(timestamp) => new Date(timestamp).toLocaleTimeString()}
                />
                <YAxis 
                  domain={[0, 1]} 
                  tickFormatter={(value) => `${(value * 100).toFixed(0)}%`}
                />
                <Tooltip 
                  formatter={(value: number) => `${(value * 100).toFixed(1)}%`}
                  labelFormatter={(timestamp) => new Date(timestamp).toLocaleString()}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Outcomes Grid */}
          <div className="grid gap-4">
            {marketState.outcomes.map((outcome) => (
              <div 
                key={outcome} 
                className="flex justify-between items-center bg-zinc-700 p-4 rounded-lg"
              >
                <span>{outcome}</span>
                <div className="flex items-center gap-4">
                  <span className="text-2xl font-bold">
                    {(marketState.currentPrices[outcome] * 100).toFixed(1)}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right Column - Order Book and Agent Activity */}
        <div className="col-span-4 space-y-4">
          <OrderBook marketId={marketState.description} source="simulator" />
          
          {/* Agent Activity Feed */}
          <div className="bg-zinc-800 rounded-lg p-4">
            <h3 className="text-lg font-semibold mb-3">Agent Activity</h3>
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {agentActions.map((action, idx) => (
                <div 
                  key={idx} 
                  className="bg-zinc-700 p-2 rounded text-sm"
                >
                  <div className="flex justify-between">
                    <span className="font-bold">{action.agent_id}</span>
                    <span className="text-zinc-400">
                      {new Date(action.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                  {action.action_type === 'BET' && action.outcome && (
                    <div className="text-zinc-300">
                      Bet {action.outcome} @ {(action.price! * 100).toFixed(1)}%
                      <span className="ml-2 text-zinc-400">
                        ${action.stake!.toLocaleString()}
                      </span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Market Footer */}
      <div className="bg-zinc-900 p-4 rounded-b-lg border-t border-zinc-800">
        <div className="flex justify-between text-zinc-400">
          <span>Total Liquidity:</span>
          <span>${marketState.totalLiquidity.toLocaleString()}</span>
        </div>
      </div>
    </div>
  )
}