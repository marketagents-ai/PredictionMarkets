export const API_BASE_URL = 'http://localhost:8004'
export const WS_BASE_URL = 'ws://localhost:8004'

export const DEFAULT_CONFIG = {
  numAgents: 2,
  maxRounds: 10,
  marketType: 'BINARY',
  agentBehavior: 'STRATEGIC',
  updateInterval: 1000
} as const

export const ENDPOINTS = {
  START: '/start',
  STOP: '/stop',
  MARKET: '/market',
  AGENTS: '/agents'
} as const

export const WS_ENDPOINTS = {
  MARKET: '/market',
  AGENT_ACTIVITY: '/agent_activity'
} as const