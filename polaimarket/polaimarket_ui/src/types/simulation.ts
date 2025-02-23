export interface Agent {
    id: string
    type: 'RANDOM' | 'STRATEGIC'
    balance: number
    currentBet?: number
  }
  
  export interface MarketState {
    round: number
    price: number
    volume: number
    isRunning: boolean
    lastUpdate: string
  }
  
  export interface SimulationConfig {
    numAgents: number
    maxRounds: number
    marketType: 'BINARY' | 'CATEGORICAL'
    agentBehavior: 'RANDOM' | 'STRATEGIC'
    updateInterval: number
  }