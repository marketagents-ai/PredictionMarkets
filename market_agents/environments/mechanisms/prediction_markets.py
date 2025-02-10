# prediction_market.py

from enum import Enum
from typing import Dict, Any, List, Optional, Type, Union, Tuple
from pydantic import BaseModel, Field, validator, computed_field
from datetime import datetime
import random
import string

from market_agents.environments.environment import ActionSpace, EnvironmentHistory, Mechanism, MultiAgentEnvironment

class LocalAction(BaseModel):
    agent_id: str
    action: Any

    @classmethod
    def sample(cls, agent_id: str) -> 'LocalAction':
        raise NotImplementedError

class GlobalAction(BaseModel):
    actions: Dict[str, LocalAction]

    @classmethod
    def from_local_actions(cls, local_actions: Dict[str, LocalAction]) -> "GlobalAction":
        return cls(actions=local_actions)

class LocalObservation(BaseModel):
    agent_id: str
    observation: Any

class GlobalObservation(BaseModel):
    observations: Dict[str, LocalObservation]

    @classmethod
    def from_local_observations(cls, local_observations: Dict[str, LocalObservation]) -> "GlobalObservation":
        return cls(observations=local_observations)

class EnvironmentStep(BaseModel):
    global_observation: GlobalObservation
    done: bool
    info: Dict[str, Any]

    @classmethod
    def from_local_steps(cls, local_steps: Dict[str, 'LocalEnvironmentStep']) -> "EnvironmentStep":
        observations = {agent_id: step.observation for agent_id, step in local_steps.items()}
        done = all(step.done for step in local_steps.values())
        return cls(global_observation=GlobalObservation.from_local_observations(observations), done=done, info={})

class LocalEnvironmentStep(BaseModel):
    observation: LocalObservation
    reward: Optional[float] = None
    done: bool
    info: Dict[str, Any]


class ActionType(Enum):
    BET = "BET"
    HOLD = "HOLD"

class Outcome(Enum):
    YES = "Yes"
    NO = "No"

class PredictionMarketAction(BaseModel):
    """External action model for LLM agents"""
    action_type: ActionType = Field(
        ..., 
        description="Type of action ('BET' or 'HOLD')"
    )
    outcome: Optional[Outcome] = Field(
        None, 
        description="The outcome to bet on (e.g. 'Yes' or 'No')"
    )
    stake: Optional[float] = Field(
        None, 
        description="Amount to stake on the outcome",
        ge=1.0,
        le=100.0
    )
    price: Optional[float] = Field(
        None, 
        description="Price/probability for the outcome",
        ge=0.0,
        le=1.0
    )

    @validator('outcome')
    def validate_outcome_for_bet(cls, v, values):
        """Ensure outcome is provided for BET actions"""
        if values.get('action_type') == ActionType.BET and not v:
            raise ValueError("Outcome must be provided for BET actions")
        return v

    @validator('stake')
    def validate_stake_for_bet(cls, v, values):
        """Ensure stake is provided and positive for BET actions"""
        if values.get('action_type') == ActionType.BET:
            if v is None:
                raise ValueError("Stake must be provided for BET actions")
            if v <= 0:
                raise ValueError("Stake must be positive for BET actions")
        return v

    @validator('price')
    def validate_price_for_bet(cls, v, values):
        """Ensure price is provided and between 0 and 1 for BET actions"""
        if values.get('action_type') == ActionType.BET:
            if v is None:
                raise ValueError("Price must be provided for BET actions")
            if not 0 <= v <= 1:
                raise ValueError("Price must be between 0 and 1")
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "action_type": "BET",
                    "outcome": "Yes",
                    "stake": 50.0,
                    "price": 0.7
                },
                {
                    "action_type": "HOLD",
                    "outcome": None,
                    "stake": None,
                    "price": None
                }
            ]
        }
    }

class PredictionBet(PredictionMarketAction):
    """Internal bet model with additional fields"""
    event_id: str = Field(..., description="Market event ID")

class PredictionMarketLocalAction(LocalAction):
    """Local action wrapper for prediction markets"""
    action: PredictionBet

    @classmethod
    def sample(cls, agent_id: str) -> 'PredictionMarketLocalAction':
        """Generate a random valid action"""
        action = PredictionMarketAction(
            action_type="BET",
            outcome=random.choice(['Yes', 'No']),
            stake=random.uniform(1, 100),
            price=random.uniform(0.1, 0.9)
        )
        return cls(
            agent_id=agent_id,
            action=PredictionBet(**action.model_dump(), event_id="sample_event")
        )

    @classmethod
    def action_schema(cls) -> Dict[str, Any]:
        """Return the schema for LLM agents"""
        return PredictionMarketAction.model_json_schema()

    @classmethod
    def from_market_action(cls, agent_id: str, action: PredictionMarketAction, event_id: str) -> 'PredictionMarketLocalAction':
        """Create a local action from a market action and event ID"""
        internal_bet = PredictionBet(**action.model_dump(), event_id=event_id)
        return cls(agent_id=agent_id, action=internal_bet)

class GlobalPredictionMarketAction(GlobalAction):
    """Global action container for prediction markets"""
    actions: Dict[str, PredictionMarketLocalAction]

    @classmethod
    def from_local_actions(cls, local_actions: Dict[str, PredictionMarketLocalAction]) -> "GlobalPredictionMarketAction":
        return cls(actions=local_actions)

class MarketState(BaseModel):
    event_id: str = Field(..., description="Unique identifier for the event")
    question: str = Field(..., description="The market poll question")
    options: List[str] = Field(..., description="List of outcome options (e.g. ['Yes', 'No'])")
    total_bets: Dict[str, float] = Field(default_factory=dict, description="Total stake per option")
    current_prices: Dict[str, float] = Field(default_factory=dict, description="Current market probabilities per option")
    resolved: bool = Field(default=False, description="Whether the event is resolved")
    outcome: Optional[str] = Field(default=None, description="The resolved outcome, if any")

    def update_with_bet(self, bet: PredictionBet):
        outcome = bet.outcome.value if hasattr(bet.outcome, 'value') else bet.outcome
        
        if outcome not in self.options:
            raise ValueError(f"Outcome {outcome} is not a valid option for event {self.event_id}")
        
        self.total_bets[outcome] = self.total_bets.get(outcome, 0.0) + bet.stake
        total = sum(self.total_bets.get(opt, 0.0) for opt in self.options)
        if total > 0:
            self.current_prices = {opt: self.total_bets.get(opt, 0.0) / total for opt in self.options}
        else:
            uniform = 1.0 / len(self.options)
            self.current_prices = {opt: uniform for opt in self.options}

class PredictionMarketObservation(BaseModel):
    market_states: Dict[str, MarketState] = Field(default_factory=dict, description="States of all markets")
    timestamp: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

class PredictionMarketLocalObservation(LocalObservation):
    observation: PredictionMarketObservation

class PredictionMarketGlobalObservation(GlobalObservation):
    observations: Dict[str, PredictionMarketLocalObservation]
    market_states: Dict[str, MarketState] = Field(default_factory=dict, description="Global market states")

class PredictionMarketActionSpace(ActionSpace):
    allowed_actions: List[Type[LocalAction]] = Field(
        default=[PredictionMarketLocalAction],
        description="Allowed actions in prediction market"
    )

    @classmethod
    def get_action_schema(cls) -> Dict[str, Any]:
        """Return the schema for LLM agents"""
        return PredictionMarketAction.model_json_schema()

class PredictionMarketObservationSpace(BaseModel):
    allowed_observations: List[Type[LocalObservation]] = Field(default_factory=lambda: [PredictionMarketLocalObservation])

class PredictionMarketMechanism(Mechanism):
    max_rounds: int = Field(default=10, description="Maximum number of rounds for the market")
    current_round: int = Field(default=0, description="Current round number")
    markets: Dict[str, MarketState] = Field(default_factory=dict)
    sequential: bool = Field(default=False, description="Whether the mechanism is sequential")
    initial_liquidity: float = Field(default=1000.0, description="Initial market liquidity")
    round_summaries: List[Dict[str, Any]] = Field(default_factory=list, description="History of all round actions")
    last_step: Optional[EnvironmentStep] = Field(default=None, description="Last environment step")

    def step(self, action: GlobalPredictionMarketAction) -> EnvironmentStep:
        self.current_round += 1

        # Process bets and update markets
        round_actions = {}
        for agent_id, local_action in action.actions.items():
            bet = local_action.action
            round_actions[agent_id] = bet.dict()
            
            if bet.action_type != ActionType.HOLD:
                if bet.event_id not in self.markets:
                    self.markets[bet.event_id] = MarketState(
                        event_id=bet.event_id,
                        question=f"Market poll for event {bet.event_id}",
                        options=["Yes", "No"],
                        total_bets={},
                        current_prices={"Yes": 0.5, "No": 0.5}
                    )
                self.markets[bet.event_id].update_with_bet(bet)

        # Store round actions in history
        self.round_summaries.append(round_actions)

        # Build local observations for each agent
        local_observations: Dict[str, PredictionMarketLocalObservation] = {}
        agent_rewards: Dict[str, float] = {}
        
        market_obs = PredictionMarketObservation(market_states=self.markets)
        for agent_id in action.actions.keys():
            local_obs = PredictionMarketLocalObservation(
                agent_id=agent_id,
                observation=market_obs
            )
            local_observations[agent_id] = local_obs
            agent_rewards[agent_id] = 1.0

        # Check if markets should be resolved
        done = (self.current_round >= self.max_rounds)
        if done:
            for market in self.markets.values():
                if not market.resolved:
                    market.resolved = True
                    market.outcome = random.choice(market.options)

        # Create global observation
        global_obs = PredictionMarketGlobalObservation(
            observations=local_observations,
            market_states=self.markets
        )

        step_result = EnvironmentStep(
            global_observation=global_obs,
            done=done,
            info={
                "round": self.current_round,
                "agent_rewards": agent_rewards,
                "market_states": {k: v.dict() for k, v in self.markets.items()}
            }
        )
        self.last_step = step_result
        return step_result

    def get_global_state(self) -> Dict[str, Any]:
        """Return relevant global state for agent context"""
        return {
            "current_round": self.current_round,
            "max_rounds": self.max_rounds,
            "markets": {k: v.dict() for k, v in self.markets.items()},
            "round_summaries": self.round_summaries,
            "round_summaries_count": len(self.round_summaries),
            "last_step": self.last_step.dict() if self.last_step else None
        }

    def reset(self) -> None:
        """Reset mechanism state"""
        self.current_round = 0
        self.markets = {}
        self.round_summaries = []
        self.last_step = None

    def get_global_state(self) -> Dict[str, Any]:
        """Return relevant global state for agent context"""
        return {
            "current_round": self.current_round,
            "max_rounds": self.max_rounds,
            "markets": {k: v.dict() for k, v in self.markets.items()},
            "last_step": self.last_step.dict() if self.last_step else None
        }

    def reset(self) -> None:
        self.current_round = 0
        self.markets = {}
        self.last_step = None

class PredictionMarketEnvironment(MultiAgentEnvironment):
    name: str = Field(default="Prediction Market", description="Name of the prediction market environment")
    current_step: int = Field(default=0, description="Current simulation step")
    max_steps: int = Field(default=10, description="Maximum number of steps")
    action_space: PredictionMarketActionSpace = Field(
        default_factory=PredictionMarketActionSpace,
        description="Action space for prediction markets"
    )
    observation_space: PredictionMarketObservationSpace = Field(
        default_factory=PredictionMarketObservationSpace,
        description="Observation space for prediction markets"
    )
    mechanism: PredictionMarketMechanism = Field(
        default_factory=lambda: PredictionMarketMechanism(initial_liquidity=1000.0),
        description="Prediction market mechanism"
    )
    history: EnvironmentHistory = Field(
        default_factory=EnvironmentHistory,
        description="History of environment steps"
    )

    def step(self, actions: GlobalPredictionMarketAction) -> EnvironmentStep:
        step_result = self.mechanism.step(actions)
        self.current_step += 1
        self.history.add_step(action=actions, step=step_result)
        return step_result

    def reset(self) -> GlobalObservation:
        self.current_step = 0
        self.history = EnvironmentHistory()
        self.mechanism.reset()
        return GlobalObservation(observations={})

    def get_global_state(self) -> Any:
        return {
            **self.mechanism.get_global_state(),
            "current_step": self.current_step,
            "max_steps": self.max_steps,
            "steps": self.history.steps if self.history else []
        }

if __name__ == "__main__":
    num_agents = 3
    num_steps = 5
    env = PredictionMarketEnvironment(max_steps=num_steps)
    agent_ids = [f"Agent{i}" for i in range(num_agents)]

    for step in range(num_steps):
        print(f"\n--- Step {step+1} ---")
        actions = {}
        for agent_id in agent_ids:
            action = env.action_space.sample(agent_id)
            actions[agent_id] = action
            print(f"{agent_id} bets: {action.action.dict()}")
        global_action = GlobalPredictionMarketAction(actions=actions)
        step_result = env.step(global_action)
        env.render()
        if step_result.done:
            print("Market resolved!")
            break