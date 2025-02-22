'use client'
import { useState } from 'react'

interface MarketConfig {
  numAgents: number
  maxRounds: number
  marketType: "BINARY" | "CATEGORICAL"
  market: string
  description: string
  outcomes: string[]
  initialPrices: Record<string, number>
  initialLiquidity: number
  resolutionDate: string
}

export function SimulationControls() {
  const [isRunning, setIsRunning] = useState(false)
  const [config, setConfig] = useState<MarketConfig>({
    numAgents: 2,
    maxRounds: 10,
    marketType: "CATEGORICAL",
    market: "What will be the Fed's rate decision in March 2024 FOMC meeting?",
    description: "This market predicts the exact size of the Federal Reserve's interest rate decision at the March 2024 FOMC meeting.",
    outcomes: ["No Change", "25 bps decrease", "50+ bps decrease", "25+ bps increase"],
    initialPrices: {
      "No Change": 0.972,
      "25 bps decrease": 0.014,
      "50+ bps decrease": 0.01,
      "25+ bps increase": 0.004
    },
    initialLiquidity: 12228577,
    resolutionDate: "2024-03-20"
  })

  const startSimulation = async () => {
    try {
      setIsRunning(true)
      const response = await fetch('/api/simulation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          numAgents: config.numAgents,
          maxRounds: config.maxRounds,
          marketConfig: {
            market_type: config.marketType,
            market: config.market,
            description: config.description,
            outcomes: config.outcomes,
            initial_prices: config.initialPrices,
            initial_liquidity: config.initialLiquidity,
            resolution_date: config.resolutionDate
          }
        })
      })
      
      if (!response.ok) {
        throw new Error('Failed to start simulation')
      }
      
      const data = await response.json()
      console.log('Simulation response:', data)
    } catch (error) {
      console.error('Error starting simulation:', error)
      alert('Failed to start simulation')
    } finally {
      setIsRunning(false)
    }
  }

  const updateOutcome = (index: number, value: string) => {
    const newOutcomes = [...config.outcomes]
    newOutcomes[index] = value
    
    // Update initial prices with the new outcome
    const newPrices = { ...config.initialPrices }
    delete newPrices[config.outcomes[index]]
    newPrices[value] = 0.25 // Default to equal distribution

    setConfig({
      ...config,
      outcomes: newOutcomes,
      initialPrices: newPrices
    })
  }

  const updatePrice = (outcome: string, value: number) => {
    setConfig({
      ...config,
      initialPrices: {
        ...config.initialPrices,
        [outcome]: value
      }
    })
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-4">
        <div>
          <label className="text-sm block mb-1">Number of Agents</label>
          <input 
            type="number" 
            value={config.numAgents}
            onChange={(e) => setConfig({...config, numAgents: +e.target.value})}
            className="w-full bg-zinc-700 p-2 rounded"
            min={1}
            max={10}
            disabled={isRunning}
          />
        </div>

        <div>
          <label className="text-sm block mb-1">Max Rounds</label>
          <input 
            type="number"
            value={config.maxRounds}
            onChange={(e) => setConfig({...config, maxRounds: +e.target.value})}
            className="w-full bg-zinc-700 p-2 rounded"
            min={1}
            disabled={isRunning}
          />
        </div>

        <div>
          <label className="text-sm block mb-1">Market Type</label>
          <select
            value={config.marketType}
            onChange={(e) => setConfig({...config, marketType: e.target.value as "BINARY" | "CATEGORICAL"})}
            className="w-full bg-zinc-700 p-2 rounded"
            disabled={isRunning}
          >
            <option value="BINARY">Binary</option>
            <option value="CATEGORICAL">Categorical</option>
          </select>
        </div>

        <div>
          <label className="text-sm block mb-1">Market Question</label>
          <input
            type="text"
            value={config.market}
            onChange={(e) => setConfig({...config, market: e.target.value})}
            className="w-full bg-zinc-700 p-2 rounded"
            disabled={isRunning}
          />
        </div>

        <div>
          <label className="text-sm block mb-1">Description</label>
          <textarea
            value={config.description}
            onChange={(e) => setConfig({...config, description: e.target.value})}
            className="w-full bg-zinc-700 p-2 rounded"
            rows={3}
            disabled={isRunning}
          />
        </div>

        <div>
          <label className="text-sm block mb-1">Outcomes & Initial Prices</label>
          {config.outcomes.map((outcome, index) => (
            <div key={index} className="flex gap-2 mb-2">
              <input
                type="text"
                value={outcome}
                onChange={(e) => updateOutcome(index, e.target.value)}
                className="flex-grow bg-zinc-700 p-2 rounded"
                disabled={isRunning}
              />
              <input
                type="number"
                value={config.initialPrices[outcome]}
                onChange={(e) => updatePrice(outcome, +e.target.value)}
                className="w-24 bg-zinc-700 p-2 rounded"
                step="0.001"
                min="0"
                max="1"
                disabled={isRunning}
              />
            </div>
          ))}
        </div>

        <div>
          <label className="text-sm block mb-1">Initial Liquidity ($)</label>
          <input
            type="number"
            value={config.initialLiquidity}
            onChange={(e) => setConfig({...config, initialLiquidity: +e.target.value})}
            className="w-full bg-zinc-700 p-2 rounded"
            min={1000}
            disabled={isRunning}
          />
        </div>

        <div>
          <label className="text-sm block mb-1">Resolution Date</label>
          <input
            type="date"
            value={config.resolutionDate}
            onChange={(e) => setConfig({...config, resolutionDate: e.target.value})}
            className="w-full bg-zinc-700 p-2 rounded"
            disabled={isRunning}
          />
        </div>
      </div>

      <button
        onClick={startSimulation}
        disabled={isRunning}
        className={`w-full p-3 rounded-lg font-bold ${
          isRunning 
            ? 'bg-blue-400 cursor-not-allowed' 
            : 'bg-blue-500 hover:bg-blue-600'
        }`}
      >
        {isRunning ? 'Starting Simulation...' : 'Start Simulation'}
      </button>
    </div>
  )
}