// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract PredictionMarket {
    address public owner;
    
    struct Market {
        string description;
        string marketType;  // "BINARY", "SCALAR", "CATEGORICAL"
        string[] options;
        uint256 currentPrice;  // Add currentPrice to the struct
        uint256 totalLiquidity;
        bool resolved;
        string outcome;
    }
    
    Market public market;
    mapping(address => mapping(string => uint256)) public bets;
    
    event BetPlaced(
        address bettor,
        string outcome,
        uint256 amount,
        uint256 price,
        uint256 timestamp
    );
    
    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }
    
    constructor(
        string memory _description,
        string memory _marketType,
        string[] memory _options
    ) {
        owner = msg.sender;
        market = Market({
            description: _description,
            marketType: _marketType,
            options: _options,
            currentPrice: 0,  // Initialize currentPrice
            totalLiquidity: 0,
            resolved: false,
            outcome: ""
        });
    }
    
    function placeBet(string memory outcome, uint256 amount, uint256 price) external {
        require(!market.resolved, "Market is resolved");
        bets[msg.sender][outcome] += amount;
        market.totalLiquidity += amount;
        emit BetPlaced(msg.sender, outcome, amount, price, block.timestamp);
    }
    
    function updateState(
        uint256 currentPrice,
        uint256 totalLiquidity,
        bool resolved,
        string memory outcome
    ) external onlyOwner {
        market.currentPrice = currentPrice;
        market.totalLiquidity = totalLiquidity;
        market.resolved = resolved;
        market.outcome = outcome;
    }
}