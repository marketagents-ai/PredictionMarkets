from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from web3 import Web3
from eth_account import Account
import json
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict

class MarketType(str, Enum):
    BINARY = "BINARY"
    SCALAR = "SCALAR"
    CATEGORICAL = "CATEGORICAL"

class PredictionMarketInterface(BaseModel):
    """Interface for interacting with prediction market smart contracts"""
    
    # Add model config to allow arbitrary types (Web3, contracts, etc)
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    # Define fields that need to be serialized
    rpc_url: str = Field(default="http://localhost:8545")
    markets: Dict[int, str] = Field(default_factory=dict)
    
    # Contract related fields
    factory_abi: Optional[List] = Field(default=None)
    market_abi: Optional[List] = Field(default=None)
    bridge_abi: Optional[List] = Field(default=None)
    factory_address: Optional[str] = Field(default=None)
    bridge_address: Optional[str] = Field(default=None)
    
    # These will be initialized in __init__
    w3: Optional[Web3] = None
    factory: Optional[Any] = None
    bridge: Optional[Any] = None
    accounts: List[Account] = Field(default_factory=list)
    testnet_data: Dict[str, Any] = Field(default_factory=dict)

    def __init__(self, **data):
        super().__init__(**data)
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        
        # Load contract data using correct path
        testnet_data_path = Path(__file__).parent.parent / "agent_evm_testnet" / "testnet_data.json"
        with open(testnet_data_path, 'r') as f:
            self.testnet_data = json.load(f)
            
        # Load contract ABIs and addresses
        self.factory_abi = self.testnet_data['market_factory_abi']
        self.market_abi = self.testnet_data['prediction_market_abi']
        self.bridge_abi = self.testnet_data['environment_bridge_abi']
        self.factory_address = self.testnet_data['market_factory_address']
        self.bridge_address = self.testnet_data['environment_bridge_address']
        
        # Initialize contract interfaces
        self.factory = self.w3.eth.contract(
            address=self.factory_address,
            abi=self.factory_abi
        )
        self.bridge = self.w3.eth.contract(
            address=self.bridge_address,
            abi=self.bridge_abi
        )
        
        # Initialize Hardhat accounts
        self.accounts = [
            Account.from_key(private_key)
            for private_key in self.testnet_data['hardhat_private_keys']
        ]

    async def create_market(
        self,
        description: str,
        market_type: MarketType,
        options: List[str],
        initial_prices: List[int],
        initial_liquidity: int
    ) -> Tuple[int, str]:
        """Create a new prediction market"""
        account = self.accounts[0]  # Use first account as admin
        
        # Build transaction
        nonce = self.w3.eth.get_transaction_count(account.address)
        gas_price = self.w3.eth.gas_price
        
        create_txn = self.factory.functions.createMarket(
            description,
            market_type.value,
            options,
            initial_prices,
            initial_liquidity
        ).build_transaction({
            'from': account.address,
            'nonce': nonce,
            'gasPrice': gas_price
        })
        
        # Sign and send transaction
        signed_txn = account.sign_transaction(create_txn)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        # Get market details from event
        market_created = self.factory.events.MarketCreated().process_receipt(receipt)[0]
        market_id = market_created['args']['marketId']
        market_address = market_created['args']['marketAddress']
        
        # Track the market
        self.markets[market_id] = market_address
        
        return market_id, market_address

    async def place_bet(
        self,
        market_id: int,
        outcome: str,
        amount: int,
        price: int,
        account_index: int = 0
    ) -> str:
        """Place a bet in a prediction market"""
        market_address = self.markets.get(market_id)
        if not market_address:
            raise ValueError(f"Market {market_id} not found")
            
        market = self.w3.eth.contract(
            address=market_address,
            abi=self.market_abi
        )
        
        account = self.accounts[account_index]
        nonce = self.w3.eth.get_transaction_count(account.address)
        
        bet_txn = market.functions.placeBet(
            outcome,
            amount,
            price
        ).build_transaction({
            'from': account.address,
            'nonce': nonce,
            'gasPrice': self.w3.eth.gas_price
        })
        
        signed_txn = account.sign_transaction(bet_txn)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        return tx_hash.hex()

    async def get_market_state(self, market_id: int) -> Dict:
        """Get current state of a prediction market"""
        market_address = self.markets.get(market_id)
        if not market_address:
            raise ValueError(f"Market {market_id} not found")
            
        market = self.w3.eth.contract(
            address=market_address,
            abi=self.market_abi
        )
        
        # Get market details
        market_data = market.functions.market().call()
        return {
            'description': market_data[0],
            'market_type': market_data[1],
            'options': market_data[2],
            'total_liquidity': market_data[3],
            'resolved': market_data[4],
            'outcome': market_data[5]
        }

    async def sync_environment_state(
        self,
        current_round: int,
        market_states: Dict[int, Dict]
    ) -> str:
        """Sync environment state to the blockchain"""
        account = self.accounts[0]
        
        # Format market states
        market_ids = []
        states = []
        for market_id, state in market_states.items():
            market_ids.append(market_id)
            states.append({
                'description': state['description'],
                'currentPrice': state['current_price'],
                'totalLiquidity': state['total_liquidity'],
                'resolved': state['resolved'],
                'outcome': state['outcome']
            })
        
        # Build sync transaction
        sync_txn = self.bridge.functions.syncEnvironmentState(
            current_round,
            market_ids,
            states
        ).build_transaction({
            'from': account.address,
            'nonce': self.w3.eth.get_transaction_count(account.address),
            'gasPrice': self.w3.eth.gas_price
        })
        
        signed_txn = account.sign_transaction(sync_txn)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        return tx_hash.hex()

    async def get_bet_history(self, market_id: int) -> List[Dict]:
        """Get betting history for a market"""
        market_address = self.markets.get(market_id)
        if not market_address:
            raise ValueError(f"Market {market_id} not found")
            
        market = self.w3.eth.contract(
            address=market_address,
            abi=self.market_abi
        )
        
        # Get bet events
        bet_filter = market.events.BetPlaced.create_filter(fromBlock=0)
        events = bet_filter.get_all_entries()
        
        return [{
            'bettor': event['args']['bettor'],
            'outcome': event['args']['outcome'],
            'amount': event['args']['amount'],
            'price': event['args']['price'],
            'timestamp': event['args']['timestamp']
        } for event in events]
    
    async def get_market_details(self, market_id: int) -> Dict:
        """Get comprehensive market details including prices and bets"""
        market_address = self.markets.get(market_id)
        if not market_address:
            raise ValueError(f"Market {market_id} not found")
            
        market = self.w3.eth.contract(
            address=market_address,
            abi=self.market_abi
        )
        
        # Get market data from contract
        market_data = market.functions.market().call()
        
        # Get bet history
        bet_filter = market.events.BetPlaced.create_filter(fromBlock=0)
        bets = bet_filter.get_all_entries()
        
        # Calculate total volume per outcome
        total_bets = {}
        for bet in bets:
            outcome = bet['args']['outcome']
            amount = bet['args']['amount']
            total_bets[outcome] = total_bets.get(outcome, 0) + amount

        return {
            'description': market_data[0],
            'market_type': market_data[1],
            'options': market_data[2],
            'current_prices': {
                option: market_data[3] / 1e18 if option == market_data[2][0] else (1 - market_data[3] / 1e18)
                for option in market_data[2]
            },
            'total_liquidity': market_data[3],
            'resolved': market_data[4],
            'outcome': market_data[5],
            'total_bets': total_bets,
            'recent_trades': [{
                'bettor': bet['args']['bettor'],
                'outcome': bet['args']['outcome'],
                'amount': bet['args']['amount'],
                'price': bet['args']['price'],
                'timestamp': bet['args']['timestamp']
            } for bet in bets[-10:]]  # Last 10 trades
        }