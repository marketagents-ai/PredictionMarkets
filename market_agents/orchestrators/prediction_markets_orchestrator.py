from datetime import datetime, timezone
import json
import logging
from typing import List, Dict, Any, Optional

from market_agents.memory.agent_storage.storage_service import StorageService
from market_agents.orchestrators.base_orchestrator import BaseEnvironmentOrchestrator
from market_agents.agents.market_agent import MarketAgent
from market_agents.environments.environment import (
    EnvironmentStep, MultiAgentEnvironment, GlobalAction
)
from market_agents.environments.mechanisms.prediction_markets import (
    ActionType,
    MarketState,
    Outcome,
    PredictionBet,
    PredictionMarketEnvironment,
    PredictionMarketLocalAction,
    PredictionMarketMechanism,
    PredictionMarketGlobalObservation,
    PredictionMarketAction,
    GlobalPredictionMarketAction
)
from market_agents.orchestrators.config import OrchestratorConfig, PredictionMarketConfig
from market_agents.orchestrators.logger_utils import (
    log_perception,
    log_persona,
    log_section,
    log_environment_setup,
    log_running,
    log_action,
    log_round,
)
from market_agents.orchestrators.orchestration_data_inserter import OrchestrationDataInserter
from market_agents.orchestrators.parallel_cognitive_steps import ParallelCognitiveProcessor

class PredictionMarketsOrchestrator(BaseEnvironmentOrchestrator):
    def __init__(
        self,
        config: PredictionMarketConfig,
        agents: List[MarketAgent],
        storage_service: StorageService,
        orchestrator_config: OrchestratorConfig,
        logger=None,
        ai_utils=None,
        **kwargs
    ):
        super().__init__(
            config=config,
            orchestrator_config=orchestrator_config,
            agents=agents,
            storage_service=storage_service,
            logger=logger,
            environment_name=config.name,
            ai_utils=ai_utils,
            **kwargs
        )
        
        self.data_inserter = OrchestrationDataInserter(storage_service=storage_service)
        self.cognitive_processor = ParallelCognitiveProcessor(
            ai_utils=self.ai_utils,
            storage_service=storage_service,
            logger=self.logger,
            tool_mode=self.orchestrator_config.tool_mode
        )

    async def setup_environment(self):
        """Set up the prediction market environment."""
        log_section(self.logger, "CONFIGURING PREDICTION MARKET ENVIRONMENT")
        
        initial_market = MarketState(
            event_id=self.config.name,
            question=self.config.market,
            options=["Yes", "No"],
            total_bets={},
            current_prices={"Yes": self.config.initial_price, "No": 1 - self.config.initial_price}
        )
        
        prediction_mechanism = PredictionMarketMechanism(
            max_rounds=self.orchestrator_config.max_rounds,
            markets={self.config.name: initial_market},
            initial_liquidity=self.config.initial_liquidity
        )

        self.environment = PredictionMarketEnvironment(
            name=self.environment_name,
            mechanism=prediction_mechanism,
            max_steps=self.orchestrator_config.max_rounds
        )

        for agent in self.agents:
            agent.environments[self.environment_name] = self.environment
            self.logger.info(f"Agent {agent.id} environments: {list(agent.environments.keys())}")

        log_environment_setup(self.logger, self.environment_name)
        return self.environment

    async def run_environment(self, round_num: int = None):
        """
        Run the environment for the specified round number.
        If no round number is provided, run all rounds up to max_rounds.
        """
        if round_num is not None:
            await self.run_market_round(round_num)
        else:
            for r in range(1, self.orchestrator_config.max_rounds + 1):
                await self.run_market_round(r)

    async def run_market_round(self, round_num: int):
        """Run a single round of the prediction market."""
        self.logger.info(f"=== Running Market Round {round_num} ===")

        try:
            # 1. Perception Phase
            perceptions = await self._run_perception_phase(round_num)
            
            # 2. Action Phase
            step_result = await self._run_action_phase(round_num)
            
            # 3. Reflection Phase
            await self._run_reflection_phase(round_num)
            
            await self.process_round_results(round_num, step_result)
            
        except Exception as e:
            self.logger.error(f"Error in round {round_num}: {e}")
            self.logger.exception("Round failed")
            raise

        self.logger.info(f"Round {round_num} complete.\n")

    async def _run_perception_phase(self, round_num: int):
        """Handles the perception phase of the cognitive cycle."""
        self.logger.info(f"Round {round_num}: Agents perceiving environment...")
        perceptions = await self.cognitive_processor.run_parallel_perception(self.agents, self.environment_name)
        
        for agent, perception in zip(self.agents, perceptions or []):
            log_persona(self.logger, agent.id, agent.persona)
            log_perception(
                self.logger, 
                agent.id, 
                perception.json_object.object if perception and perception.json_object else None
            )
        
        return perceptions

    async def _run_action_phase(self, round_num: int):
        """Handles the action phase of the cognitive cycle."""
        self.logger.info(f"Round {round_num}: Gathering agent market actions...")
        actions = await self.cognitive_processor.run_parallel_action(self.agents, self.environment_name)
        
        # Process actions into market actions
        agent_actions = await self._process_agent_actions(actions)
        global_action = GlobalPredictionMarketAction(actions=agent_actions)
        
        # Step environment and process state
        step_result = self.environment.step(global_action)
        self.process_environment_state(step_result)
        
        return step_result

    async def _process_agent_actions(self, actions) -> Dict[str, PredictionMarketLocalAction]:
        """Process individual agent actions and create market actions."""
        agent_actions = {}
        
        for agent, action in zip(self.agents, actions or []):
            try:
                content = None
                if action and action.json_object and action.json_object.object:
                    content = action.json_object.object
                elif action and hasattr(action, 'str_content'):
                    content = json.loads(action.str_content) if isinstance(action.str_content, str) else action.str_content

                agent.last_action = content
                
                if content:
                    try:
                        formatted_content = {
                            'actionType': content.get('action_type'),
                            'outcome': content.get('outcome'),
                            'stake': float(content.get('stake')) if content.get('stake') is not None else None,
                            'price': float(content.get('price')) if content.get('price') is not None else None
                        }
                        
                        market_action = PredictionMarketAction(
                            action_type=ActionType(formatted_content['actionType']),
                            outcome=Outcome(formatted_content['outcome']) if formatted_content['outcome'] else None,
                            stake=formatted_content['stake'],
                            price=formatted_content['price']
                        )
                        
                        local_action = PredictionMarketLocalAction.from_market_action(
                            agent_id=agent.id,
                            action=market_action,
                            event_id=self.config.name
                        )
                        agent_actions[agent.id] = local_action
                        
                    except Exception as e:
                        self.logger.error(f"Failed to create action for agent {agent.id}: {e}")
                        market_action = PredictionMarketAction(action_type=ActionType.HOLD)
                        local_action = PredictionMarketLocalAction.from_market_action(
                            agent_id=agent.id,
                            action=market_action,
                            event_id=self.config.name
                        )
                        agent_actions[agent.id] = local_action

                model_name = agent.llm_config.model if agent.llm_config else None
                log_action(self.logger, agent.id, content, model_name=model_name)
                    
            except Exception as e:
                self.logger.error(f"Error creating PredictionMarketAction for agent {agent.id}: {str(e)}")
                market_action = PredictionMarketAction(action_type=ActionType.HOLD)
                local_action = PredictionMarketLocalAction.from_market_action(
                    agent_id=agent.id,
                    action=market_action,
                    event_id=self.config.name
                )
                agent_actions[agent.id] = local_action
        
        return agent_actions

    async def _run_reflection_phase(self, round_num: int):
        """Handles the reflection phase of the cognitive cycle."""
        self.logger.info(f"Round {round_num}: Agents reflecting on market changes...")
        try:
            agents_with_observations = [
                agent for agent in self.agents 
                if agent.last_observation and hasattr(agent.last_observation, 'observation') 
                and agent.last_observation.observation
            ]

            if not agents_with_observations:
                self.logger.warning("No agents had observations to reflect on")
                return

            reflections = await self.cognitive_processor.run_parallel_reflection(
                agents_with_observations,
                environment_name=self.environment_name
            )
            
            if not reflections:
                self.logger.warning("No reflections received from agents")
                return

        except Exception as e:
            self.logger.error(f"Error during reflection step: {str(e)}", exc_info=True)
            self.logger.exception("Reflection step failed but continuing...")

    def process_environment_state(self, env_state: EnvironmentStep):
        """Process the environment state after each step."""
        global_observation = env_state.global_observation
        if not isinstance(global_observation, PredictionMarketGlobalObservation):
            self.logger.error(f"Unexpected global observation type: {type(global_observation)}")
            return

        for agent_id, agent_observation in global_observation.observations.items():
            agent = next((a for a in self.agents if a.id == agent_id), None)
            if agent:
                agent.last_observation = agent_observation
                self.logger.debug(f"Updated last_observation for agent {agent.id}")

        log_section(self.logger, "MARKET STATES")
        for market_id, market_state in global_observation.market_states.items():
            self.logger.info(f"Market {market_id}:")
            for outcome, price in market_state.current_prices.items():
                self.logger.info(f"  Current price for {outcome}: {price:.4f}")
            self.logger.info(f"  Total bets: {market_state.total_bets}")
            if hasattr(market_state, 'liquidity'):
                self.logger.info(f"  Liquidity: {market_state.liquidity:.2f}")

    async def process_round_results(self, round_num: int, step_result=None, sub_round: int = None):
        """Process and store results for the prediction market round.
        
        Args:
            round_num: The current round number
            step_result: Optional environment step result
            sub_round: Optional sub-round number (not used in prediction markets)
        """
        try:
            actions_data = []
            for agent in self.agents:
                if hasattr(agent, 'last_action') and agent.last_action:
                    actions_data.append({
                        'agent_id': agent.id,
                        'environment_name': self.environment_name,
                        'round': round_num,
                        'action': agent.last_action,
                        'type': 'prediction_market_bet'
                    })
            
            if actions_data:
                await self.data_inserter.insert_actions(actions_data)

            if hasattr(self.environment, 'get_global_state'):
                env_state = self.environment.get_global_state()
                config_dict = self.orchestrator_config.model_dump() if hasattr(self.orchestrator_config, 'model_dump') else vars(self.orchestrator_config)
                
                metadata = {
                    'config': config_dict,
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'num_agents': len(self.agents),
                    'market_topic': self.config.market,
                    'current_prices': self.environment.mechanism.current_prices if hasattr(self.environment.mechanism, 'current_prices') else {},
                    'total_liquidity': self.environment.mechanism.initial_liquidity
                }

                await self.data_inserter.insert_environment_state(
                    self.environment_name,
                    round_num,
                    env_state,
                    metadata
                )

            if step_result and hasattr(step_result.global_observation, 'trades'):
                trades_data = []
                for trade in step_result.global_observation.trades:
                    trades_data.append({
                        'round': round_num,
                        'timestamp': datetime.now(timezone.utc).isoformat(),
                        'agent_id': trade.agent_id,
                        'position': trade.position,
                        'amount': trade.amount,
                        'price': trade.price,
                        'market_topic': self.config.market
                    })
                
                if trades_data:
                    await self.data_inserter.insert_trades(trades_data)

            self.logger.info(f"Data for prediction market round {round_num} inserted successfully")
            
        except Exception as e:
            self.logger.error(f"Error processing round {round_num} results: {e}")
            self.logger.exception("Details:")
            raise

    async def get_round_summary(self, round_num: int) -> dict:
        """Get a summary of the current round."""
        if not self.last_env_state:
            return {"round": round_num, "status": "No environment state available"}

        global_obs = self.last_env_state.global_observation
        
        summary = {
            "round": round_num,
            "markets": {},
            "agent_positions": {},
            "total_volume": 0.0
        }

        for market_id, state in global_obs.market_states.items():
            summary["markets"][market_id] = {
                "price": state.current_price,
                "volume": state.total_volume,
                "liquidity": state.liquidity
            }
            summary["total_volume"] += state.total_volume

        for agent in self.agents:
            if agent.id in global_obs.observations:
                obs = global_obs.observations[agent.id]
                summary["agent_positions"][agent.id] = {
                    "portfolio_value": obs.portfolio_value,
                    "positions": obs.positions
                }

        return summary
    
    async def run(self):
        """Main entrypoint to run everything"""
        await self.setup_environment()
        await self.run_environment()
        self.logger.info("All rounds complete. Printing final summary...\n")
        await self.print_summary()
    
