// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "./MarketFactory.sol";

contract EnvironmentBridge {
    address public owner;
    MarketFactory public factory;
    
    struct MarketState {
        string description;
        uint256 currentPrice;
        uint256 totalLiquidity;
        bool resolved;
        string outcome;
    }
    
    event EnvironmentStateUpdated(
        uint256 round,
        uint256[] marketIds,
        MarketState[] states
    );
    
    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }
    
    constructor(address _factory) {
        owner = msg.sender;
        factory = MarketFactory(_factory);
    }
    
    function syncEnvironmentState(
        uint256 round,
        uint256[] memory marketIds,
        MarketState[] memory states
    ) external onlyOwner {
        require(marketIds.length == states.length, "Length mismatch");
        emit EnvironmentStateUpdated(round, marketIds, states);
    }
}