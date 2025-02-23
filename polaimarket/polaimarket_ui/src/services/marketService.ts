import { ethers } from 'ethers';

// ABI matches our PredictionMarket.sol contract
const PREDICTION_MARKET_ABI = [
  {
    "inputs": [],
    "name": "market",
    "outputs": [
      {
        "components": [
          { "name": "description", "type": "string" },
          { "name": "marketType", "type": "string" },
          { "name": "options", "type": "string[]" },
          { "name": "currentPrice", "type": "uint256" },
          { "name": "totalLiquidity", "type": "uint256" },
          { "name": "resolved", "type": "bool" },
          { "name": "outcome", "type": "string" }
        ],
        "type": "tuple"
      }
    ],
    "stateMutability": "view",
    "type": "function"
  },
  {
    "anonymous": false,
    "inputs": [
      { "indexed": false, "name": "bettor", "type": "address" },
      { "indexed": false, "name": "outcome", "type": "string" },
      { "indexed": false, "name": "amount", "type": "uint256" },
      { "indexed": false, "name": "price", "type": "uint256" },
      { "indexed": false, "name": "timestamp", "type": "uint256" }
    ],
    "name": "BetPlaced",
    "type": "event"
  }
];

export interface MarketData {
  description: string;
  marketType: string;
  options: string[];
  currentPrices: Record<string, number>;
  totalLiquidity: number;
  resolved: boolean;
  outcome: string;
  totalBets: Record<string, number>;
  recentTrades: {
    bettor: string;
    outcome: string;
    amount: number;
    price: number;
    timestamp: number;
  }[];
}

class MarketService {
  private provider: ethers.providers.JsonRpcProvider;

  constructor() {
    this.provider = new ethers.providers.JsonRpcProvider('http://localhost:8545');
  }

  async getMarketDetails(marketAddress: string): Promise<MarketData> {
    try {
      const contract = new ethers.Contract(marketAddress, PREDICTION_MARKET_ABI, this.provider);
      
      // Get market data
      const marketData = await contract.market();
      
      // Get bet history
      const betFilter = contract.filters.BetPlaced();
      const events = await contract.queryFilter(betFilter);
      
      // Calculate total bets per outcome
      const totalBets: Record<string, number> = {};
      events.forEach(event => {
        const { outcome, amount } = event.args;
        totalBets[outcome] = (totalBets[outcome] || 0) + Number(amount);
      });

      // Format the response to match Python interface
      return {
        description: marketData[0],
        marketType: marketData[1],
        options: marketData[2],
        currentPrices: {
          [marketData[2][0]]: Number(marketData[3]) / 1e18,
          [marketData[2][1]]: 1 - (Number(marketData[3]) / 1e18)
        },
        totalLiquidity: Number(marketData[3]),
        resolved: marketData[4],
        outcome: marketData[5],
        totalBets,
        recentTrades: events.slice(-10).map(event => ({
          bettor: event.args.bettor,
          outcome: event.args.outcome,
          amount: Number(event.args.amount),
          price: Number(event.args.price),
          timestamp: Number(event.args.timestamp)
        }))
      };
    } catch (error) {
      console.error('Error fetching market details:', error);
      throw error;
    }
  }

  // Subscribe to live updates
  subscribeToMarketUpdates(marketAddress: string, callback: (data: MarketData) => void) {
    const contract = new ethers.Contract(marketAddress, PREDICTION_MARKET_ABI, this.provider);
    
    // Listen for new bets
    contract.on('BetPlaced', async () => {
      // Fetch updated market data when new bet is placed
      const data = await this.getMarketDetails(marketAddress);
      callback(data);
    });

    // Initial fetch
    this.getMarketDetails(marketAddress).then(callback);

    // Return unsubscribe function
    return () => {
      contract.removeAllListeners();
    };
  }
}

export const marketService = new MarketService();