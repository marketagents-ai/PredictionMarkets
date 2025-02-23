export const PREDICTION_MARKET_ABI = [
    "function market() view returns (tuple(string description, string marketType, string[] options, uint256[] prices, uint256 totalLiquidity, bool resolved, string outcome))",
    "event BetPlaced(address bettor, string outcome, uint256 amount, uint256 price, uint256 timestamp)"
  ];

export const MARKET_FACTORY_ABI = [
    "function createMarket(string description, string marketType, string[] options, uint256[] initialPrices, uint256 initialLiquidity) returns (uint256 marketId, address marketAddress)",
    "event MarketCreated(uint256 indexed marketId, address marketAddress)"
  ];