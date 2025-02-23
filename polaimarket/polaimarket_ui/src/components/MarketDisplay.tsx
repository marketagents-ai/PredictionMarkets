'use client';

import { useEffect, useState } from 'react';
import { useMarketData } from '../hooks/useMarketData';

interface MarketDisplayProps {
  marketAddress?: string;
  isLoading: boolean;
  logs: string[];
  initialMarketData?: {
    question: string;
    description: string;
    outcomes: string[];
    initialPrices: { [key: string]: number };
    resolutionDate: string;
  };
}

interface MarketState {
  question: string;
  description: string;
  outcomes: string[];
  current_prices: { [key: string]: number };
  total_bets: { [key: string]: number };
  resolutionDate: string;
}

export function MarketDisplay({ 
    marketAddress, 
    isLoading: parentLoading, 
    logs,
    initialMarketData 
  }: MarketDisplayProps) {
    
    const [marketState, setMarketState] = useState<MarketState>(() => ({
      question: initialMarketData?.question || '',
      description: initialMarketData?.description || '',
      outcomes: initialMarketData?.outcomes || [],
      current_prices: initialMarketData?.initialPrices || {},
      total_bets: {},
      resolutionDate: initialMarketData?.resolutionDate || ''
    }));

    // Update from simulation data
    useEffect(() => {
      if (initialMarketData) {
        setMarketState(prev => ({
          ...prev,
          question: initialMarketData.question,
          description: initialMarketData.description,
          outcomes: initialMarketData.outcomes,
          current_prices: initialMarketData.initialPrices,
          resolutionDate: initialMarketData.resolutionDate
        }));
      }
    }, [initialMarketData]);

    // Update from simulation logs
    useEffect(() => {
      if (!logs.length) return;
      
      for (const log of logs) {
        try {
          if (log.includes('MARKET_STATES')) {
            const match = log.match(/current_prices=({[^}]+})/);
            if (match) {
              const pricesStr = match[1].replace(/'/g, '"');
              const prices = JSON.parse(pricesStr);
              setMarketState(prev => ({
                ...prev,
                current_prices: prices
              }));
            }

            const betsMatch = log.match(/total_bets=({[^}]+})/);
            if (betsMatch) {
              const betsStr = betsMatch[1].replace(/'/g, '"');
              const bets = JSON.parse(betsStr);
              setMarketState(prev => ({
                ...prev,
                total_bets: bets
              }));
            }
          }
        } catch (e) {
          console.error('Error parsing market state:', e);
        }
      }
    }, [logs]);
    
    // Show empty state
    if (!marketState.question || !marketState.outcomes.length) {
      return (
        <div className="text-sm opacity-75">
          Configure market parameters above...
        </div>
      );
    }

    return (
      <div className="bg-zinc-900 rounded-lg p-6">
        {/* Market Question */}
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-3xl font-bold">
            {marketState.question}
          </h2>
          <div className="text-zinc-400">
            Resolution Date: {marketState.resolutionDate}
          </div>
        </div>
  
        {/* Market Description */}
        <div className="text-xl mb-8 text-zinc-300">
          {marketState.description}
        </div>
  
        {/* Outcomes */}
        <div className="space-y-3">
          {marketState.outcomes.map(option => (
            <div key={option} className="bg-zinc-800 rounded-lg p-4">
              <div className="flex items-center justify-between">
                <div className="text-xl">{option}</div>
                <div className="flex items-center gap-8">
                  <div className="text-2xl font-bold text-green-400">
                    {(marketState.current_prices[option] * 100).toFixed(1)}%
                  </div>
                  <div className="text-zinc-400">
                    Volume: ${marketState.total_bets[option]?.toLocaleString() || '0'}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
  
        {/* Total Volume */}
        <div className="mt-6 pt-4 border-t border-zinc-700 text-zinc-400">
          Total Volume: ${Object.values(marketState.total_bets).reduce((a, b) => a + b, 0).toLocaleString()}
        </div>
      </div>
    );
  }