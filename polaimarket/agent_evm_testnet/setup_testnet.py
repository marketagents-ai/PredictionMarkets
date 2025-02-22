import os
import subprocess
import time
import json
from pathlib import Path
from typing import Optional
from web3 import Web3
from polaimarket_testnet_deployer import PredictionMarketTestDeployer

class TestnetManager:
    DEFAULT_RPC_PORT = 8545  # Default Hardhat port
    DEFAULT_NETWORK_ID = 31337  # Default Hardhat network ID
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.testnet_dir = base_dir / "polaimarket" / "agent_evm_testnet"
        self.contracts_dir = self.testnet_dir / "contracts"
        self.pid_file = self.testnet_dir / "hardhat-node.pid"
        self.testnet_data_file = self.testnet_dir / "testnet_data.json"

    def ensure_hardhat_running(self) -> Optional[int]:
        """Start Hardhat node if not running"""
        try:
            # Check if already running
            if self.pid_file.exists():
                with open(self.pid_file) as f:
                    pid = int(f.read().strip())
                try:
                    os.kill(pid, 0)  # Check if process exists
                    print(f"Hardhat node already running (PID: {pid})")
                    return self.DEFAULT_RPC_PORT
                except OSError:
                    self.pid_file.unlink()  # Remove stale PID file
            
            print("Starting Hardhat node...")
            
            # Start Hardhat node
            process = subprocess.Popen(
                ["npx", "hardhat", "node"],
                cwd=str(self.testnet_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Save PID
            with open(self.pid_file, "w") as f:
                f.write(str(process.pid))
            
            # Wait for node to start
            time.sleep(5)
            
            # Verify node is responding
            w3 = Web3(Web3.HTTPProvider(f"http://localhost:{self.DEFAULT_RPC_PORT}"))
            if not w3.is_connected():
                raise RuntimeError("Failed to connect to Hardhat node")
                
            return self.DEFAULT_RPC_PORT
            
        except Exception as e:
            print(f"Failed to start Hardhat node: {e}")
            return None

    def deploy_contracts(self) -> bool:
        """Deploy all contracts"""
        try:
            # Deploy prediction market contracts
            print("\nDeploying prediction market contracts...")
            deployer = PredictionMarketTestDeployer()
            factory_interface, market_interface, bridge_interface = deployer.compile_contracts()
            factory_address, bridge_address = deployer.deploy_contracts(factory_interface, bridge_interface)
            
            print(f"MarketFactory deployed at: {factory_address}")
            print(f"EnvironmentBridge deployed at: {bridge_address}")
            
            # Save deployment data
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
            
            with open(self.testnet_data_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            print("Contracts deployed successfully")
            return True
            
        except Exception as e:
            print(f"Failed to deploy contracts: {e}")
            return False

def main():
    # Get project root directory
    root_dir = Path(__file__).parent.parent.parent
    
    manager = TestnetManager(root_dir)
    
    # Start testnet
    rpc_port = manager.ensure_hardhat_running()
    if not rpc_port:
        print("Failed to start testnet")
        return False
        
    # Deploy contracts
    if not manager.deploy_contracts():
        print("Failed to deploy contracts")
        return False
        
    print("Testnet setup complete!")
    return True

if __name__ == "__main__":
    main()