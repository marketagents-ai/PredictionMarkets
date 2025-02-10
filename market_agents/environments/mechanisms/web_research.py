from typing import Dict, List, Any, Optional, Type, Union
from pydantic import BaseModel, Field
from datetime import datetime
import logging

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
    ObservationSpace
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
    """Local observation with web search results"""
    agent_id: str
    observation: Dict[str, Any] = Field(default_factory=dict)
    search_results: Optional[List[WebSearchResult]] = None
    query: str = ""
    status: str = "pending"

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
        action: Union[WebSearchAction, Dict[str, Any]]
    ) -> Union[LocalEnvironmentStep, EnvironmentStep]:
        """Process agent actions in workflow sequence"""
        self.current_round += 1
        done = (self.current_round >= self.max_rounds)

        if isinstance(action, dict):
            action = WebSearchAction(**action)

        search_results = await self.execute_web_search(
            action.query,
            action.num_results
        )

        self.search_history.append({
            "round": self.current_round,
            "query": action.query,
            "results": [result.dict() for result in search_results],
            "timestamp": datetime.now().isoformat()
        })

        observation = WebSearchLocalObservation(
            agent_id=action.agent_id,
            observation={
                "query": action.query,
                "num_results": len(search_results)
            },
            search_results=search_results,
            query=action.query,
            status="success" if search_results else "no_results"
        )

        return LocalEnvironmentStep(
            observation=observation,
            reward=float(len(search_results)),
            done=done,
            info={
                "round": self.current_round,
                "total_results": len(search_results),
                "query": action.query
            }
        )

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

class WebSearchEnvironment(MultiAgentEnvironment):
    """Environment that manages web search operations"""
    name: str = Field(default="Web Search Environment")
    mechanism: WebSearchMechanism = Field(...)
    action_space: ActionSpace = Field(
        default_factory=lambda: ActionSpace(allowed_actions=[WebSearchAction])
    )
    observation_space: ObservationSpace = Field(
        default_factory=lambda: ObservationSpace(allowed_observations=[WebSearchLocalObservation])
    )
    
    model_config = {
        "arbitrary_types_allowed": True,
        "extra": "allow"
    }
    
    async def step(self, action: GlobalAction) -> EnvironmentStep:
        """Execute environment step with search actions"""
        if not isinstance(action, GlobalAction):
            raise ValueError("Expected GlobalAction")
            
        local_steps = {}
        
        for agent_id, local_action in action.actions.items():
            local_step = await self.mechanism.step(local_action)
            local_steps[agent_id] = local_step
        
        global_step = EnvironmentStep.from_local_steps(local_steps)
        
        self.current_step += 1
        self.update_history(action, global_step)
        return global_step