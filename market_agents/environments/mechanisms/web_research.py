from typing import Dict, List, Any, Optional, Type, Union
from pydantic import BaseModel, Field
from datetime import datetime
import logging

from market_agents.environments.mechanisms.research import ResearchAction, ResearchActionSpace
from market_agents.web_search.url_processor import URLFetcher
from market_agents.web_search.web_search_config import WebSearchConfig
from market_agents.environments.environment import (
    EnvironmentHistory,
    MultiAgentEnvironment, 
    Mechanism,
    LocalAction,
    LocalObservation,
    GlobalAction,
    GlobalObservation,
    LocalEnvironmentStep,
    EnvironmentStep,
    ActionSpace,
    ObservationSpace,
    StrAction
)

from market_agents.web_search.web_search_manager import SearchManager
from market_agents.web_search.content_extractor import ContentExtractor

logger = logging.getLogger(__name__)

class WebSearchResult(BaseModel):
    """Structure for a single search result"""
    url: str
    title: str
    content: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

class WebSearchActionInput(BaseModel):
    """External action model for LLM agents"""
    query: str = Field(..., description="Search query to execute")
    num_results: int = Field(default=5, description="Number of results to fetch")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "query": "latest developments in AI technology",
                    "num_results": 5
                },
                {
                    "query": "current market trends in cryptocurrency",
                    "num_results": 3
                }
            ]
        }
    }

class WebSearchAction(LocalAction):
    """Internal action model with additional fields"""
    agent_id: str
    action: str = Field(default="web_search", description="Type of action")
    query: str = Field(..., description="Search query to execute")
    num_results: int = Field(default=5, description="Number of results to fetch")

    @classmethod
    def sample(cls, agent_id: str) -> 'WebSearchAction':
        return cls(
            agent_id=agent_id,
            query="latest developments in AI technology",
            num_results=5
        )

    @classmethod
    def from_llm_action(cls, agent_id: str, action: WebSearchActionInput) -> 'WebSearchAction':
        """Create internal action from LLM-generated action"""
        return cls(
            agent_id=agent_id,
            **action.model_dump()
        )

    @classmethod
    def action_schema(cls) -> Dict[str, Any]:
        """Return the schema for LLM agents"""
        return WebSearchActionInput.model_json_schema()

class WebSearchLocalObservation(LocalObservation):
    """Local observation for a specific agent"""
    agent_id: str
    observation: Dict[str, Any]
    status: str = "pending"
    search_results: Optional[List[Dict[str, str]]] = None

    def dict(self, *args, **kwargs):
        """Custom dict method to handle nested observation"""
        d = super().dict(*args, **kwargs)
        if self.observation:
            d['observation'] = self.observation
        return d

class WebSearchGlobalObservation(GlobalObservation):
    """Global observation containing all agent observations"""
    observations: Dict[str, WebSearchLocalObservation]


class WebSearchMechanism(Mechanism):
    """Mechanism that manages web search workflow"""
    search_manager: Optional[SearchManager] = Field(default=None, exclude=True)
    content_extractor: Optional[ContentExtractor] = Field(default=None, exclude=True)
    url_fetcher: Optional[URLFetcher] = Field(default=None, exclude=True)  # Add URLFetcher
    current_round: int = Field(default=0, description="Current search round")
    max_rounds: int = Field(default=3, description="Maximum search rounds")
    search_history: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="History of search results"
    )
    current_query: str = ""

    model_config = {
        "arbitrary_types_allowed": True,
        "extra": "allow"
    }

    def __init__(self, **data):
        super().__init__(**data)
        if not isinstance(data.get("search_config"), WebSearchConfig):
            raise ValueError("search_config must be a WebSearchConfig instance")
            
        search_config = data["search_config"]
        
        self.search_manager = SearchManager(config=search_config)
        self.content_extractor = ContentExtractor(config=search_config)
        self.url_fetcher = URLFetcher(config=search_config, prompts={})

    async def execute_web_search(
        self,
        query: str,
        num_results: int
    ) -> List[WebSearchResult]:
        """Execute web search and return results"""
        try:
            self.current_query = query
            
            urls = await self.search_manager.get_urls_for_query(query, num_results)
            
            for url in urls:
                self.search_manager.query_url_mapping[url] = query
            
            fetched_results = await self.url_fetcher.process_urls(urls, self.search_manager.query_url_mapping)
            
            search_results = [
                WebSearchResult(
                    url=fr.url,
                    title=fr.title,
                    content=fr.content.get('text', '')
                )
                for fr in fetched_results if fr is not None
            ]
            
            return search_results
                
        except Exception as e:
            logger.error(f"Error in web search: {str(e)}")
            return []
           
    async def step(
        self,
        action: Union[GlobalAction, WebSearchAction, str]
    ) -> Union[LocalEnvironmentStep, EnvironmentStep]:
        """Process agent actions in workflow sequence"""
        self.current_round += 1
        done = (self.current_round >= self.max_rounds)

        if isinstance(action, GlobalAction):
            observations = {}
            for agent_id, agent_action in action.actions.items():
                search_results = []
                if isinstance(agent_action, WebSearchAction):
                    search_results = await self.execute_web_search(
                        query=agent_action.query,
                        num_results=agent_action.num_results
                    )
                
                obs_data = {
                    "action": agent_action if isinstance(agent_action, dict) else {"summary": str(agent_action)},
                    "round": self.current_round,
                    "status": "success"
                }
                
                obs = WebSearchLocalObservation(
                    agent_id=agent_id,
                    observation=obs_data,
                    status="success",
                    search_results=[result.model_dump() for result in search_results]
                )
                observations[agent_id] = obs

            step_result = EnvironmentStep(
                global_observation=GlobalObservation(observations=observations),
                reward=1.0,
                done=done,
                info={
                    "round": self.current_round,
                    "actions": {k: str(v) for k, v in action.actions.items()}
                }
            )
            self.last_step = step_result
            return step_result

        agent_id = getattr(action, 'agent_id', 'default')
        search_results = []
        
        if isinstance(action, WebSearchAction):
            search_results = await self.execute_web_search(
                query=action.query,
                num_results=action.num_results
            )
        
        obs_data = {
            "action": action if isinstance(action, dict) else {"summary": str(action)},
            "round": self.current_round,
            "status": "success"
        }
        
        # reward = self._calculate_reward(search_results)

        observation = WebSearchLocalObservation(
            agent_id=agent_id,
            observation=obs_data,
            status="success",
            search_results=[result.model_dump() for result in search_results]
        )

        step_result = LocalEnvironmentStep(
            observation=observation,
            reward=1.0,
            done=done,
            info={
                "round": self.current_round,
                "action": str(action),
                "reward_info": {
                    "num_results": len(search_results),
                    "content_length": sum(len(r.content) for r in search_results),
                    "query_relevance": self._calculate_query_relevance(action.query)
                }
            }
        )
        self.last_step = step_result
        return step_result
        
    def get_global_state(self) -> Dict[str, Any]:
        """Get current global state"""
        return {
            "current_round": self.current_round,
            "max_rounds": self.max_rounds,
            "search_history": self.search_history,
            "current_query": self.current_query
        }

    def reset(self) -> None:
        """Reset mechanism state"""
        self.current_round = 0
        self.search_history.clear()
        self.current_query = ""

    def _calculate_reward(self, search_results: List[WebSearchResult]) -> float:
        """Calculate reward based on search results quality"""
        if not search_results:
            return 0.0

        reward = 0.2

        num_results = len(search_results)
        max_results = self.search_config.urls_per_query
        results_ratio = min(num_results / max_results, 1.0)
        reward += 0.3 * results_ratio

        avg_content_length = sum(len(r.content) for r in search_results) / num_results
        content_reward = min(avg_content_length / 500, 1.0)
        reward += 0.3 * content_reward

        unique_domains = len(set(self._extract_domain(r.url) for r in search_results))
        diversity_ratio = unique_domains / num_results
        reward += 0.2 * diversity_ratio

        return reward

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL for diversity calculation"""
        try:
            from urllib.parse import urlparse
            return urlparse(url).netloc
        except:
            return url

    def _calculate_query_relevance(self, query: str) -> float:
        """Calculate how relevant the query is to the current topic"""
        if not query:
            return 0.0
        if query == self.current_query:
            return 0.5
        return 1.0 

class WebResearchActionSpace(ActionSpace):
    """Action space that handles both web search and research summary actions"""
    allowed_actions: List[Type[LocalAction]] = Field(default_factory=list)
    summary_model: Optional[Type[BaseModel]] = None
    current_phase: str = "search"

    def __init__(self, summary_model: Type[BaseModel] = None, **data):
        super().__init__(**data)
        self.summary_model = summary_model
        self.set_phase("search")

    def set_phase(self, phase: str):
        """Switch between search and summary phases"""
        if phase not in ["search", "summary"]:
            raise ValueError(f"Invalid phase: {phase}")
            
        self.current_phase = phase
        if phase == "search":
            self.allowed_actions = [WebSearchAction]
        elif phase == "summary":
            self.allowed_actions = [ResearchAction] if self.summary_model else [StrAction]

    def get_action_schema(self) -> Dict[str, Any]:
        """Return JSON schema based on current phase"""
        if self.current_phase == "search":
            return WebSearchActionInput.model_json_schema()
        elif self.summary_model:
            return self.summary_model.model_json_schema()
        else:
            return {"type": "string"}

    def sample(self, agent_id: str) -> LocalAction:
        """Create a sample action based on current phase"""
        if not self.allowed_actions:
            return StrAction(agent_id=agent_id, action="Sample text output")
        elif self.current_phase == "search":
            return WebSearchAction.sample(agent_id)
        else:
            return ResearchAction.sample(agent_id, self.summary_model)

class WebSearchEnvironment(MultiAgentEnvironment):
    """Environment that manages web search operations"""
    name: str = Field(default="Web Search Environment")
    mechanism: WebSearchMechanism = Field(...)
    action_space: WebResearchActionSpace = Field(
        default_factory=WebResearchActionSpace,
        description="Action space that handles both phases"
    )
    current_phase: str = Field(
        default="search",
        description="Current action phase (search/summary)"
    )
    summary_model: Optional[Type[BaseModel]] = None
    internal_state: Dict[str, Any] = Field(
        default_factory=dict,
        description="Internal storage for global state"
    )
    
    def __init__(self, summary_model: Type[BaseModel] = None, **data):
        if "summary" in data.get("current_phase", "") and summary_model is None:
            raise ValueError("summary_model must be provided when starting in summary phase")
            
        super().__init__(**data)
        self.summary_model = summary_model
        self.action_space = WebResearchActionSpace(summary_model=summary_model)
        self.internal_state = {}

    def switch_phase(self, phase: str):
        """Switch between search and summary phases"""
        if phase not in ["search", "summary"]:
            raise ValueError(f"Invalid phase: {phase}")
            
        self.current_phase = phase
        self.action_space.set_phase(phase)

    async def step(self, action: Union[GlobalAction, WebSearchAction, str]) -> EnvironmentStep:
        """Execute a step in the environment"""
        try:
            mechanism_step = await self.mechanism.step(action)
            
            if isinstance(mechanism_step, EnvironmentStep):
                return mechanism_step
                
            elif isinstance(mechanism_step, LocalEnvironmentStep):
                observations = {
                    mechanism_step.observation.agent_id: mechanism_step.observation
                }
                return EnvironmentStep(
                    global_observation=GlobalObservation(observations=observations),
                    reward=mechanism_step.reward,
                    done=mechanism_step.done,
                    info=mechanism_step.info
                )
            else:
                raise ValueError(f"Unexpected step result type: {type(mechanism_step)}")
                
        except Exception as e:
            raise ValueError(f"Error in environment step: {str(e)}")

    def get_global_state(self) -> Dict[str, Any]:
        """Get current global state combining mechanism and environment state"""
        mechanism_state = self.mechanism.get_global_state()
        
        summary_schema = None
        if self.summary_model:
            try:
                summary_schema = self.summary_model.model_json_schema()
            except Exception as e:
                logger.error(f"Error getting summary model schema: {e}")
        
        return {
            **self.internal_state,
            **mechanism_state,
            "current_phase": self.current_phase,
            "summary_model": self.summary_model.__name__ if self.summary_model else None,
            "summary_schema": summary_schema
        }

    def reset(self) -> GlobalObservation:
        """Reset environment state"""
        self.internal_state = {}
        self.current_phase = "search"
        self.mechanism.reset()
        return GlobalObservation(observations={})