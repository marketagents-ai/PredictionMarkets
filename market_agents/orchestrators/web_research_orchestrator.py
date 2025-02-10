from datetime import datetime, timezone
import logging
from typing import List, Dict, Any, Type

from market_agents.web_search.web_search_config import WebSearchConfig
from market_agents.orchestrators.base_orchestrator import BaseEnvironmentOrchestrator
from market_agents.orchestrators.config import OrchestratorConfig, WebResearchConfig
from market_agents.agents.market_agent import MarketAgent
from market_agents.orchestrators.orchestration_data_inserter import OrchestrationDataInserter, serialize_for_json
from market_agents.orchestrators.parallel_cognitive_steps import ParallelCognitiveProcessor
from market_agents.environments.environment import EnvironmentStep, GlobalAction, LocalEnvironmentStep
from market_agents.environments.mechanisms.web_research import (
    WebSearchActionInput,
    WebSearchEnvironment,
    WebSearchAction,
    WebSearchLocalObservation,
    WebSearchMechanism
)
from market_agents.memory.agent_storage.storage_service import StorageService
from market_agents.orchestrators.logger_utils import log_action, log_perception, log_persona, log_reflection

logger = logging.getLogger(__name__)

class WebResearchOrchestrator(BaseEnvironmentOrchestrator):
    def __init__(
        self,
        config: WebResearchConfig,
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
        
        # Fixed initialization
        self.environment = WebSearchEnvironment(
            name=self.config.name,
            mechanism=WebSearchMechanism(
                search_config=WebSearchConfig.from_yaml(self.config.search_config),
                max_rounds=self.config.sub_rounds,
                current_query=self.config.initial_query
            )
        )

        # Register environment with agents
        for agent in self.agents:
            agent.environments[self.config.name] = self.environment

        self.logger.info(f"Initialized WebResearchOrchestrator for environment: {self.config.name}")

    async def setup_environment(self):
        """Setup or reset the web search environment."""
        self.logger.info("Setting up the Web Research Environment...")
        self.environment.reset()
        self.logger.info("Web Research Environment setup complete.")

    async def run_environment(self, round_num: int = None):
        """Run the environment for specified rounds."""
        if round_num is not None:
            await self.run_research_round(round_num)
        else:
            for r in range(1, self.orchestrator_config.max_rounds + 1):
                await self.run_research_round(r)

    async def run_research_round(self, round_num: int):
        """Orchestrates a single main round with multiple sub-rounds of web search."""
        self.logger.info(f"=== Running Web Research Round {round_num} ===")

        # Initialize agents for this round
        self._initialize_agents_for_round()

        # Run each sub-round
        for sub_round in range(1, self.config.sub_rounds + 1):
            self.logger.info(f"=== Starting Sub-round {sub_round}/{self.config.sub_rounds} of Round {round_num} ===")
            try:
                step_result = await self._run_sub_round(round_num, sub_round)
                await self.process_round_results(round_num, step_result, sub_round)
            except Exception as e:
                self.logger.error(f"Error in round {round_num}, sub-round {sub_round}: {e}")
                self.logger.exception("Sub-round failed")
                raise

        self.logger.info(f"Round {round_num} complete with {self.config.sub_rounds} sub-rounds.\n")

    def _initialize_agents_for_round(self):
        """Initialize agents with the current search query."""
        for agent in self.agents:
            agent.task = f"Research the following topic using web search:\n{self.environment.mechanism.current_query}"
            agent._refresh_prompts()

    async def _run_sub_round(self, round_num: int, sub_round: int):
        """Executes a single sub-round of the web research process."""
        try:
            # 1. Perception Phase
            perceptions = await self._run_perception_phase(round_num, sub_round)
            
            # 2. Action Phase (Web Search)
            step_result = await self._run_action_phase(round_num, sub_round)
            
            # 3. Reflection Phase
            await self._run_reflection_phase(round_num, sub_round)
            
            return step_result
            
        except Exception as e:
            self.logger.error(f"Error in sub-round {sub_round} of round {round_num}: {e}")
            raise

    async def _run_perception_phase(self, round_num: int, sub_round: int):
        """Handles the perception phase of the cognitive cycle."""
        self.logger.info(f"Round {round_num}.{sub_round}: Agents perceiving environment...")
        perceptions = await self.cognitive_processor.run_parallel_perception(
            self.agents, 
            self.config.name
        )
        
        for agent, perception in zip(self.agents, perceptions or []):
            log_persona(self.logger, agent.id, agent.persona)
            log_perception(
                self.logger, 
                agent.id, 
                perception.json_object.object if perception and perception.json_object else None
            )
        
        return perceptions

    async def _run_action_phase(self, round_num: int, sub_round: int):
        """Handles the action phase of the cognitive cycle."""
        self.logger.info(f"Round {round_num}.{sub_round}: Executing agent web searches...")
        
        actions = await self.cognitive_processor.run_parallel_action(
            self.agents,
            self.config.name
        )
        
        agent_summaries = await self._process_agent_actions(actions)
        self.logger.info(f"Processed web search queries: {agent_summaries}")
        
        global_actions = await self._create_global_actions(actions)
        
        # Await the async step
        step_result = await self.environment.step(GlobalAction(actions=global_actions))
        
        if step_result and step_result.global_observation:
            await self._update_agent_observations(step_result)
        
        return step_result

    async def _process_agent_actions(self, actions):
        """Process individual agent actions and create summaries."""
        agent_summaries = {}
        
        for agent, action in zip(self.agents, actions or []):
            try:
                content = None
                if action and action.json_object and action.json_object.object:
                    # Parse into WebSearchActionInput format
                    raw_content = action.json_object.object
                    content = WebSearchActionInput(
                        query=raw_content.get('query'),
                        num_results=raw_content.get('num_results', 5)
                    ).model_dump()

                agent.last_action = content
                if content:
                    agent_summaries[agent.id] = content
                
                model_name = agent.llm_config.model if agent.llm_config else None
                log_action(self.logger, agent.id, content, model_name=model_name)

            except Exception as e:
                self.logger.error(f"Error processing action for agent {agent.id}: {str(e)}", exc_info=True)
                agent.last_action = None
        
        return agent_summaries

    async def _create_global_actions(self, actions) -> Dict[str, WebSearchAction]:
        """Create global actions from individual agent actions."""
        global_actions = {}
        
        for agent, action_response in zip(self.agents, actions or []):
            try:
                if action_response and action_response.json_object and action_response.json_object.object:
                    # Parse into WebSearchActionInput first
                    action_data = action_response.json_object.object
                    llm_action = WebSearchActionInput(
                        query=action_data.get('query'),
                        num_results=action_data.get('num_results', 5)
                    )
                    
                    # Convert to internal WebSearchAction
                    local_action = WebSearchAction.from_llm_action(agent.id, llm_action)
                else:
                    self.logger.warning(f"No valid action response for agent {agent.id}")
                    local_action = WebSearchAction.sample(agent.id)
                
                global_actions[agent.id] = local_action
                
            except Exception as e:
                self.logger.error(
                    f"Error creating action for agent {agent.id}: {str(e)}\n"
                    f"Raw action data: {action_response.json_object.object if action_response and action_response.json_object else None}",
                    exc_info=True
                )
                local_action = WebSearchAction.sample(agent.id)
                global_actions[agent.id] = local_action
        
        return global_actions

    async def _update_agent_observations(self, step_result):
        """Update agent observations based on step results."""
        if not step_result:
            return
            
        for agent in self.agents:
            try:
                if isinstance(step_result, LocalEnvironmentStep):
                    if step_result.observation.agent_id == agent.id:
                        agent.last_observation = step_result.observation
                elif isinstance(step_result, EnvironmentStep) and step_result.global_observation:
                    if agent.id in step_result.global_observation.observations:
                        agent.last_observation = step_result.global_observation.observations[agent.id]
                
            except Exception as e:
                self.logger.error(f"Error updating observation for agent {agent.id}: {str(e)}")
                agent.last_observation = None

    async def _run_reflection_phase(self, round_num: int, sub_round: int):
        """Run parallel reflection for all agents."""
        self.logger.info(f"Round {round_num}.{sub_round}: Agents reflecting on search results...")
        reflections = await self.cognitive_processor.run_parallel_reflection(
            self.agents,
            self.config.name
        )

    async def process_round_results(self, round_num: int, step_result=None, sub_round: int = None):
        """Process and store results from the round."""
        if step_result:
            await self.data_inserter.insert_environment_state(
                environment_name=self.config.name,
                round_num=round_num,
                state_data={
                    'step_result': serialize_for_json(step_result),
                    'global_state': self.environment.get_global_state()
                },
                metadata={
                    'sub_round': sub_round,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            )

    async def get_round_summary(self, round_num: int) -> dict:
        """Get summary of the specified round."""
        return {
            "round": round_num,
            "environment": self.config.name,
            "global_state": self.environment.get_global_state()
        }

    async def print_summary(self):
        """Print final summary of web research results."""
        self.logger.info("\n=== WEB RESEARCH SUMMARY ===")
        
        global_state = self.environment.get_global_state()
        self.logger.info(f"Final Environment State: {global_state}")
        
        for agent in self.agents:
            self.logger.info(f"\nAgent {agent.id} final search results:")
            if agent.last_observation and isinstance(agent.last_observation, WebSearchLocalObservation):
                for result in agent.last_observation.search_results or []:
                    self.logger.info(f"- {result.title}: {result.url}")