'use client'
import Image from 'next/image'
import Link from 'next/link'

export function Header() {
  return (
    <header className="bg-zinc-900 border-b border-zinc-800">
      <div className="max-w-7xl mx-auto px-6 py-5 flex items-center justify-between">
        <Link href="/" className="flex items-center space-x-4">
          <div className="relative w-16 h-16">
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