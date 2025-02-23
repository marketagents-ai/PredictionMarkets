import os
from web3 import Web3
from eth_account import Account
import json
from pathlib import Path
import subprocess

def compile_contract(contract_path, abi_name):
    """Compile contract using Hardhat"""
    # Get the hardhat-testnet directory path
    hardhat_dir = Path(__file__).parent / "hardhat-testnet"
    contracts_dir = hardhat_dir / "contracts"
    
    # Create contracts directory if it doesn't exist
    contracts_dir.mkdir(exist_ok=True)
    
    # Copy all contract files from agent_evm_testnet/contracts to hardhat-testnet/contracts
    source_contracts_dir = Path(__file__).parent / "contracts"
    for contract_file in source_contracts_dir.glob("*.sol"):
        target_file = contracts_dir / contract_file.name
        target_file.write_text(contract_file.read_text())
    
    # Run hardhat compile
    subprocess.run(['npx', 'hardhat', 'compile'], check=True, cwd=str(hardhat_dir))
    
    # Get the compiled contract artifact
    artifact_path = hardhat_dir / 'artifacts' / 'contracts' / os.path.basename(contract_path) / abi_name
    
    with open(artifact_path, 'r') as file:
        contract_data = json.load(file)
    
    contract_interface = {
        'abi': contract_data['abi'],
        'bin': contract_data['bytecode']
    }
    return contract_interface

class PredictionMarketTestDeployer:
    def __init__(self, node_url="http://127.0.0.1:8545"):
        self.w3 = Web3(Web3.HTTPProvider(node_url))
        self.account_address = self.w3.eth.accounts[0]
    
    def compile_contracts(self):
        """Compile all prediction market contracts"""
        factory_interface = compile_contract("contracts/MarketFactory.sol", "MarketFactory.json")
        market_interface = compile_contract("contracts/PredictionMarket.sol", "PredictionMarket.json")
        bridge_interface = compile_contract("contracts/EnvironmentBridge.sol", "EnvironmentBridge.json")
        return factory_interface, market_interface, bridge_interface
    
    def deploy_contracts(self, factory_interface, bridge_interface):
        """Deploy factory and bridge contracts"""
        # Deploy factory
        factory = self.w3.eth.contract(
            abi=factory_interface['abi'],
            bytecode=factory_interface['bin']
        )
        
        tx_hash = factory.constructor().transact({
            'from': self.account_address,
            'gas': 3000000,
            'gasPrice': self.w3.eth.gas_price
        })
        
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        factory_address = tx_receipt.contractAddress
        
        # Deploy bridge with factory address
        bridge = self.w3.eth.contract(
            abi=bridge_interface['abi'],
            bytecode=bridge_interface['bin']
        )
        
        tx_hash = bridge.constructor(factory_address).transact({
            'from': self.account_address,
            'gas': 3000000,
            'gasPrice': self.w3.eth.gas_price
        })
        
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        bridge_address = tx_receipt.contractAddress
        
        return factory_address, bridge_address

def main():
    print("Initializing prediction market deployer...")
    deployer = PredictionMarketTestDeployer()
    
    try:
        # Deploy prediction market contracts
        print("\nCompiling and deploying prediction market contracts...")
        factory_interface, market_interface, bridge_interface = deployer.compile_contracts()
        factory_address, bridge_address = deployer.deploy_contracts(factory_interface, bridge_interface)
        
        print(f"MarketFactory deployed at: {factory_address}")
        print(f"EnvironmentBridge deployed at: {bridge_address}")

        # Save contract data
        data = {
            "market_factory_address": factory_address,
            "market_factory_abi": factory_interface['abi'],
            "prediction_market_abi": market_interface['abi'],
            "environment_bridge_abi": bridge_interface['abi'],
            "environment_bridge_address": bridge_address,
            "hardhat_private_keys": [
                "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",  # Account #0
                "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d",  # Account #1
                "0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a",  # Account #2
                "0x7c852118294e51e653712a81e05800f419141751be58f605c371e15141b007a6",  # Account #3
                "0x47e179ec197488593b187f80a00eb0da91f1b9d0b13f8733639f19c30a34926a",  # Account #4
            ]
        }
        
        # Save to the correct location
        testnet_data_path = Path(__file__).parent / "testnet_data.json"
        with open(testnet_data_path, 'w') as file:
            json.dump(data, file, indent=2)
            
        print("\nSetup complete! Prediction market contracts deployed and configuration saved.")

    except Exception as e:
        print(f"Error: {str(e)}")
        raise e