'use client'
import { useState, useEffect } from 'react'
import Image from 'next/image'
import Link from 'next/link'

interface MarketStats {
  totalVolume: number
  resolutionDate: string
}

export function Header() {
  const [stats, setStats] = useState<MarketStats>({
    totalVolume: 0,
    resolutionDate: ''
  })

  useEffect(() => {
    // Connect to your Python backend websocket for market stats
    const ws = new WebSocket('ws://localhost:8004/market_stats')
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      setStats(data)
    }

    return () => ws.close()
  }, [])

  return (
    <header className="bg-zinc-900 border-b border-zinc-800">
      <div className="max-w-7xl mx-auto px-6 py-5 flex items-center justify-between">
        <Link href="/" className="flex items-center space-x-4">
          <div className="relative w-16 h-16"> {/* Increased size for better visibility */}
            <Image 
              src="/images/marketagents_logo.png"
              alt="AI Prediction Markets"
              fill
              style={{ objectFit: 'contain' }}
              priority
            />
          </div>
          <span className="text-2xl font-semibold text-white">AI Prediction Markets</span>
        </Link>

        <div className="flex items-center space-x-8">
          <div className="flex items-center space-x-2">
            <span className="text-zinc-400">
              <svg className="w-5 h-5" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
              </svg>
            </span>
            <span className="text-zinc-400">{stats.resolutionDate || 'Loading...'}</span>
          </div>
          <div className="flex items-center space-x-2">
            <span className="text-zinc-400">
              <svg className="w-5 h-5" viewBox="0 0 20 20" fill="currentColor">
                <path d="M8.433 7.418c.155-.103.346-.196.567-.267v1.698a2.305 2.305 0 01-.567-.267C8.07 8.34 8 8.114 8 8c0-.114.07-.34.433-.582zM11 12.849v-1.698c.22.071.412.164.567.267.364.243.433.468.433.582 0 .114-.07.34-.433.582a2.305 2.305 0 01-.567.267z" />
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-13a1 1 0 10-2 0v.092a4.535 4.535 0 00-1.676.662C6.602 6.234 6 7.009 6 8c0 .99.602 1.765 1.324 2.246.48.32 1.054.545 1.676.662v1.941c-.391-.127-.68-.317-.843-.504a1 1 0 10-1.51 1.31c.562.649 1.413 1.076 2.353 1.253V15a1 1 0 102 0v-.092a4.535 4.535 0 001.676-.662C13.398 13.766 14 12.991 14 12c0-.99-.602-1.765-1.324-2.246A4.535 4.535 0 0011 9.092V7.151c.391.127.68.317.843.504a1 1 0 101.511-1.31c-.563-.649-1.413-1.076-2.354-1.253V5z" clipRule="evenodd" />
              </svg>
            </span>
            <span className="text-zinc-400">${(stats.totalVolume || 0).toLocaleString()} Vol.</span>
          </div>
        </div>

        <nav className="flex items-center space-x-8">
          <Link 
            href="/markets" 
            className="text-zinc-300 hover:text-white transition-colors"
          >
            Markets
          </Link>
          <Link 
            href="/agents" 
            className="text-zinc-300 hover:text-white transition-colors"
          >
            Agents
          </Link>
          <Link 
            href="/simulation" 
            className="text-zinc-300 hover:text-white transition-colors"
          >
            Simulation
          </Link>
        </nav>
      </div>
    </header>
  )
}