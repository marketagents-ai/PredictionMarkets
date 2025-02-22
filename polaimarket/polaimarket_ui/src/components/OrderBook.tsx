'use client'
import { useEffect, useState } from 'react'
import cx from 'clsx'

interface Bet {
  bettor: string
  outcome: string
  amount: number
  price: number
  timestamp: number
}

interface OrderBookProps {
  marketId: string
  source: 'simulator' | 'testnet'
}

export function OrderBook({ marketId, source }: OrderBookProps) {
  const [bets, setBets] = useState<Bet[]>([])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    let ws: WebSocket

    const connectWebSocket = () => {
      // Connect to appropriate websocket based on source
      const wsUrl = source === 'simulator' 
        ? `ws://localhost:8004/market/${marketId}/bets`
        : `ws://localhost:8545/market/${marketId}/bets`

      ws = new WebSocket(wsUrl)

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data)
        if (source === 'simulator') {
          // Handle simulator format
          setBets(data.trades.map((trade: any) => ({
            bettor: trade.agent_id,
            outcome: trade.position,
            amount: trade.amount,
            price: trade.price,
            timestamp: new Date(trade.timestamp).getTime()
          })))
        } else {
          // Handle testnet format (from contract events)
          setBets(data.map((bet: any) => ({
            bettor: bet.bettor,
            outcome: bet.outcome,
            amount: Number(bet.amount) / 1e18, // Convert from wei
            price: Number(bet.price) / 1e18,
            timestamp: Number(bet.timestamp)
          })))
        }
        setIsLoading(false)
      }

      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        setIsLoading(false)
      }

      ws.onclose = () => {
        console.log('WebSocket closed, attempting to reconnect...')
        setTimeout(connectWebSocket, 3000)
      }
    }

    connectWebSocket()

    return () => {
      if (ws) ws.close()
    }
  }, [marketId, source])

  if (isLoading) {
    return <div className="text-zinc-400">Loading order book...</div>
  }

  // Group bets by price and outcome
  const groupedBets = bets.reduce((acc, bet) => {
    const key = `${bet.outcome}-${bet.price}`
    if (!acc[key]) {
      acc[key] = {
        outcome: bet.outcome,
        price: bet.price,
        totalAmount: 0
      }
    }
    acc[key].totalAmount += bet.amount
    return acc
  }, {} as Record<string, { outcome: string; price: number; totalAmount: number }>)

  // Sort by price descending
  const sortedOrders = Object.values(groupedBets).sort((a, b) => b.price - a.price)

  return (
    <div className="bg-zinc-800 rounded-lg p-4">
      <div className="flex items-center justify-between mb-2 text-zinc-400 text-sm">
        <div>Price</div>
        <div>Size</div>
      </div>
      
      <div className="space-y-1">
        {sortedOrders.map((order, index) => (
          <div 
            key={`${order.outcome}-${order.price}`}
            className={cx("flex items-center justify-between p-2 rounded", {
              'bg-zinc-700': index % 2 === 0
            })}
          >
            <div className="flex items-center">
              <span className={cx("w-2 h-2 rounded-full mr-2", {
                'bg-green-500': order.outcome === 'Yes',
                'bg-red-500': order.outcome === 'No',
                'bg-blue-500': !['Yes', 'No'].includes(order.outcome)
              })} />
              <span>{(order.price * 100).toFixed(1)}%</span>
            </div>
            <div>${order.totalAmount.toLocaleString()}</div>
          </div>
        ))}
      </div>
    </div>
  )
}