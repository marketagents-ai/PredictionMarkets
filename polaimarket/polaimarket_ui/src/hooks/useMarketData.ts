'use client';

import { useState, useEffect } from 'react';
import { ethers } from 'ethers';
import { PREDICTION_MARKET_ABI } from '../contracts/PredictionMarket';

export interface Trade {
  bettor: string;
  outcome: string;
  amount: number;
  price: number;
  timestamp: number;
}

export interface MarketData {
  description: string;
  market_type: string;
  options: string[];
  current_prices: {
    [key: string]: number;
  };
  total_liquidity: number;
  resolved: boolean;
  outcome: string;
  total_bets: {
    [key: string]: number;
  };
  recent_trades: Trade[];
  resolution_date?: string;
}

interface InitialMarketData {
  question: string;
  description: string;
  outcomes: string[];
  initialPrices: { [key: string]: number };
  resolutionDate: string;
}

export function useMarketData(marketAddress?: string, initialMarketData?: InitialMarketData) {
  const [marketData, setMarketData] = useState<MarketData | null>(() => {
    if (initialMarketData) {
      return {
        description: initialMarketData.question,
        market_type: "CATEGORICAL",
        options: initialMarketData.outcomes,
        current_prices: initialMarketData.initialPrices,
        total_liquidity: 0,
        resolved: false,
        outcome: "",
        total_bets: Object.fromEntries(initialMarketData.outcomes.map(o => [o, 0])),
        recent_trades: [],
        resolution_date: initialMarketData.resolutionDate
      };
    }
    return null;
  });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!marketAddress) {
      setIsLoading(false);
      return;
    }

    let isMounted = true;
    let provider: ethers.JsonRpcProvider;
    let marketContract: ethers.Contract;

    const initializeContract = async () => {
      try {
        provider = new ethers.JsonRpcProvider('http://localhost:8545');
        marketContract = new ethers.Contract(marketAddress, PREDICTION_MARKET_ABI, provider);
        
        // Initial fetch
        await fetchMarketData();

        // Listen for BetPlaced events
        marketContract.on('BetPlaced', (bettor, outcome, amount, price, timestamp) => {
          if (isMounted) {
            fetchMarketData();
          }
        });

        // Listen for market state updates from the bridge
        const bridgeContract = new ethers.Contract(
          process.env.NEXT_PUBLIC_BRIDGE_ADDRESS!, 
          ['event EnvironmentStateUpdated(uint256 round, uint256[] marketIds, tuple(string description, uint256 currentPrice, uint256 totalLiquidity, bool resolved, string outcome)[] states)'],
          provider
        );

        bridgeContract.on('EnvironmentStateUpdated', (round, marketIds, states) => {
          if (isMounted) {
            fetchMarketData();
          }
        });

      } catch (err) {
        console.error('Error initializing contracts:', err);
        if (isMounted) {
          setError(err instanceof Error ? err.message : 'Failed to initialize contracts');
          setIsLoading(false);
        }
      }
    };

    const fetchMarketData = async () => {
      try {
        const data = await marketContract.market();
        const filter = marketContract.filters.BetPlaced();
        const events = await marketContract.queryFilter(filter, 0, 'latest');

        const totalBets = {};
        events.forEach(event => {
          const { outcome, amount } = event.args;
          totalBets[outcome] = (totalBets[outcome] || 0) + Number(amount);
        });

        if (isMounted) {
          const newMarketData: MarketData = {
            description: initialMarketData?.question || data.description,
            market_type: data.marketType,
            options: data.options,
            current_prices: Object.fromEntries(
              data.options.map((option: string) => [
                option,
                Number(data.currentPrice) / 1e18
              ])
            ),
            total_liquidity: Number(data.totalLiquidity),
            resolved: data.resolved,
            outcome: data.outcome,
            total_bets: totalBets,
            recent_trades: events.slice(-10).reverse().map(event => ({
              bettor: event.args.bettor,
              outcome: event.args.outcome,
              amount: Number(event.args.amount),
              price: Number(event.args.price) / 1e18,
              timestamp: Number(event.args.timestamp)
            })),
            resolution_date: initialMarketData?.resolutionDate
          };
          setMarketData(newMarketData);
          setIsLoading(false);
        }
      } catch (err) {
        console.error('Error fetching market data:', err);
        if (isMounted) {
          setError(err instanceof Error ? err.message : 'Failed to fetch market data');
          setIsLoading(false);
        }
      }
    };

    initializeContract();

    return () => {
      isMounted = false;
      if (marketContract) {
        marketContract.removeAllListeners();
      }
    };
  }, [marketAddress, initialMarketData]);

  return { marketData, isLoading, error };
}