'use client'
import { useEffect, useRef } from 'react'

// Handle both ANSI codes and Rich markup
function processLog(text: string): string {
  // First handle ANSI color codes
  const ansiToHtml = (text: string): string => {
    return text
      // ANSI Bold
      .replace(/\u001b\[1m/g, '<span class="font-bold">')
      // ANSI Colors
      .replace(/\u001b\[30m/g, '<span class="text-black">')
      .replace(/\u001b\[31m/g, '<span class="text-red-500">')
      .replace(/\u001b\[32m/g, '<span class="text-green-500">')
      .replace(/\u001b\[33m/g, '<span class="text-yellow-500">')
      .replace(/\u001b\[34m/g, '<span class="text-blue-500">')
      .replace(/\u001b\[35m/g, '<span class="text-purple-500">')
      .replace(/\u001b\[36m/g, '<span class="text-cyan-500">')
      .replace(/\u001b\[37m/g, '<span class="text-white">')
      // ANSI Reset
      .replace(/\u001b\[0m/g, '</span>')
  }

  // Then handle Rich markup
  const richToHtml = (text: string): string => {
    return text
      // Rich color markup
      .replace(/\[([a-z-]+)\](.*?)\[\/\1\]/g, (_, color, content) => {
        const tailwindColor = getRichColor(color)
        return `<span class="${tailwindColor}">${content}</span>`
      })
      // Rich background colors
      .replace(/\[black on ([a-z-]+)\](.*?)\[\/(?:black on \1|)\]/g, (_, bgColor, content) => {
        const tailwindBg = getRichBgColor(bgColor)
        return `<span class="${tailwindBg} text-black">${content}</span>`
      })
      // Handle emojis
      .replace(/[🎭👁️🎯💭🔔🛒💼🏛️📈📉🎉⏭️🏁🔧📢💰🤝🏆🥇🥈🥉]/g, emoji => 
        `<span class="inline-block">${emoji}</span>`
      )
      // Handle newlines
      .replace(/\n/g, '<br/>')
  }

  // Apply both transformations
  return richToHtml(ansiToHtml(text))
}

function getRichColor(color: string): string {
  const colorMap: Record<string, string> = {
    'cyan': 'text-cyan-400',
    'green': 'text-green-400',
    'yellow': 'text-yellow-400',
    'blue': 'text-blue-400',
    'magenta': 'text-pink-400',
    'red': 'text-red-400',
    'white': 'text-white',
    'black': 'text-black',
    'bold': 'font-bold'
  }
  return colorMap[color] || 'text-white'
}

function getRichBgColor(color: string): string {
  const bgColorMap: Record<string, string> = {
    'cyan': 'bg-cyan-500',
    'green': 'bg-green-500',
    'yellow': 'bg-yellow-500',
    'blue': 'bg-blue-500',
    'magenta': 'bg-pink-500',
    'red': 'bg-red-500',
    'white': 'bg-white'
  }
  return bgColorMap[color] || 'bg-transparent'
}

interface LogPanelProps {
  logs: string[]
  isRunning: boolean
}

export function LogPanel({ logs, isRunning }: LogPanelProps) {
  const logContainerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight
    }
  }, [logs])

  return (
    <div className="flex flex-col h-full max-h-screen"> {/* Added max-h-screen */}
      <h2 className="text-xl font-bold mb-4">Simulation Logs</h2>
      <div 
        ref={logContainerRef}
        className="flex-1 overflow-y-auto font-mono text-sm bg-black/50 rounded-lg p-4 min-h-0" 
        // Changed to overflow-y-auto to ensure vertical scrolling
      >
        {logs.length === 0 ? (
          <div className="text-zinc-500">
            {isRunning ? 'Starting simulation...' : 'No logs yet. Start the simulation to see output.'}
          </div>
        ) : (
          logs.map((log, i) => (
            <div 
              key={i} 
              className="whitespace-pre-wrap my-1"
              dangerouslySetInnerHTML={{ 
                __html: processLog(log)
              }} 
            />
          ))
        )}
      </div>
    </div>
  )
}