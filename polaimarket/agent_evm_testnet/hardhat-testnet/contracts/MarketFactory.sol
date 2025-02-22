// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "./PredictionMarket.sol";

contract MarketFactory {
    address public owner;
    event MarketCreated(uint256 marketId, address marketAddress);
    
    uint256 public nextMarketId;
    mapping(uint256 => address) public markets;
    
    struct MarketState {
        string description;
        uint256 currentPrice;
        uint256 totalLiquidity;
        bool resolved;
        string outcome;
    }
    
    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }
    
    constructor() {
        owner = msg.sender;
    }
    
    function createMarket(
        string memory description,
        string memory marketType,
        string[] memory options
    ) external returns (uint256) {
        PredictionMarket market = new PredictionMarket(
            description,
            marketType,
            options
        );
        
        uint256 marketId = nextMarketId++;
        markets[marketId] = address(market);
        
        emit MarketCreated(marketId, address(market));
        return marketId;
    }

    function updateMarketState(uint256 marketId, MarketState memory state) external onlyOwner {
        address marketAddr = markets[marketId];
        require(marketAddr != address(0), "Market not found");
        
        PredictionMarket market = PredictionMarket(marketAddr);
        market.updateState(state.currentPrice, state.totalLiquidity, state.resolved, state.outcome);
    }
}