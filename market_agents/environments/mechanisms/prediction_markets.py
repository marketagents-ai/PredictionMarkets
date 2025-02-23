# prediction_market.py

import logging
from enum import Enum
from typing import Dict, Any, List, Optional, Type, Union, Tuple
from pydantic import BaseModel, Field, validator, computed_field
from datetime import datetime
import random
import string

from market_agents.environments.environment import ActionSpace, EnvironmentHistory, Mechanism, MultiAgentEnvironment
from polaimarket.agent_evm_interface.prediction_market_interface import PredictionMarketInterface

# Set up logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


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


class MarketType(str, Enum):
    BINARY = "BINARY"
    SCALAR = "SCALAR"
    CATEGORICAL = "CATEGORICAL"

class ActionType(str, Enum):
    BET = "BET"
    HOLD = "HOLD"

class BinaryOutcome(str, Enum):
    YES = "Yes"
    NO = "No"

class PredictionMarketAction(BaseModel):
    """External action model for LLM agents"""
    market_type: MarketType = Field(
        ..., 
        description="Type of market (BINARY, SCALAR, or CATEGORICAL)"
    )
    action_type: ActionType = Field(
        ..., 
        description="Type of action (BET or HOLD)"
    )
    outcome: Optional[Union[BinaryOutcome, float, str]] = Field(
        None, 
        description="The outcome to bet on: Yes/No for BINARY, float for SCALAR, string for CATEGORICAL"
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
    def validate_outcome(cls, v, values):
        """Validate outcome based on market_type"""
        if values.get('action_type') == ActionType.HOLD:
            return v
            
        market_type = values.get('market_type')
        if market_type == MarketType.BINARY:
            if not isinstance(v, BinaryOutcome):
                raise ValueError("Binary markets require Yes/No outcomes")
        elif market_type == MarketType.SCALAR:
            if not isinstance(v, (int, float)):
                raise ValueError("Scalar markets require numeric outcomes")
        elif market_type == MarketType.CATEGORICAL:
            if not isinstance(v, str):
                raise ValueError("Categorical markets require string outcomes")
        return v

    @validator('stake')
    def validate_stake_for_bet(cls, v, values):
        """Ensure stake is provided and within limits for BET actions"""
        if values.get('action_type') == ActionType.BET:
            if v is None:
                raise ValueError("Stake must be provided for BET actions")
            if v <= 0:
                raise ValueError("Stake must be positive for BET actions")
        return v

    @validator('price')
    def validate_price_for_bet(cls, v, values):
        """Ensure price is provided and valid for BET actions"""
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
                    # Binary market example
                    "market_type": "BINARY",
                    "action_type": "BET",
                    "outcome": "Yes",
                    "stake": 50.0,
                    "price": 0.7
                },
                {
                    # Categorical market example
                    "market_type": "CATEGORICAL",
                    "action_type": "BET",
                    "outcome": "No Change",
                    "stake": 75.0,
                    "price": 0.972
                },
                {
                    # Scalar market example
                    "market_type": "SCALAR",
                    "action_type": "BET",
                    "outcome": 5.25,
                    "stake": 25.0,
                    "price": 0.85
                },
                {
                    # Hold action example
                    "market_type": "BINARY",
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
    """Represents the current state of a prediction market"""
    event_id: str = Field(..., description="Unique identifier for the event")
    market_type: MarketType = Field(..., description="Type of market (BINARY, SCALAR, CATEGORICAL)")
    question: str = Field(..., description="The market poll question")
    
    options: Optional[List[str]] = Field(
        None, 
        description="List of possible outcomes for BINARY/CATEGORICAL markets"
    )
    
    range_min: Optional[float] = Field(
        None, 
        description="Minimum value for SCALAR markets"
    )
    range_max: Optional[float] = Field(
        None, 
        description="Maximum value for SCALAR markets"
    )
    
    total_bets: Dict[str, float] = Field(
        default_factory=dict, 
        description="Total stake per option/value"
    )
    current_prices: Dict[str, float] = Field(
        default_factory=dict, 
        description="Current market probabilities per option/value"
    )
    total_liquidity: float = Field(
        default=0.0,
        description="Total liquidity in the market"
    )
    resolved: bool = Field(
        default=False, 
        description="Whether the event is resolved"
    )
    outcome: Optional[Union[str, float]] = Field(
        default=None, 
        description="The resolved outcome, if any"
    )

    @validator('market_type')
    def validate_market_type(cls, v, values):
        if v not in [MarketType.BINARY, MarketType.CATEGORICAL]:
            raise ValueError(f"Invalid market type: {v}")
        return v

    @validator('options')
    def validate_options(cls, v, values):
        if 'market_type' in values:
            market_type = values['market_type']
            if market_type in [MarketType.BINARY, MarketType.CATEGORICAL] and not v:
                raise ValueError(f"{market_type} markets require options list")
        return v

    def update_with_bet(self, bet: PredictionBet):
        """Update market state with a new bet"""
        if self.market_type == MarketType.SCALAR:
            if not self.range_min <= float(bet.outcome) <= self.range_max:
                raise ValueError(
                    f"Outcome {bet.outcome} is outside valid range "
                    f"[{self.range_min}, {self.range_max}]"
                )
            outcome_key = str(bet.outcome)
        else:
            outcome = bet.outcome.value if hasattr(bet.outcome, 'value') else bet.outcome
            if outcome not in self.options:
                raise ValueError(
                    f"Outcome {outcome} is not a valid option for event {self.event_id}"
                )
            outcome_key = outcome

        self.total_bets[outcome_key] = self.total_bets.get(outcome_key, 0.0) + bet.stake
        self.total_liquidity += bet.stake

        if self.market_type == MarketType.SCALAR:
            total = sum(self.total_bets.values())
            for value in self.total_bets.keys():
                self.current_prices[value] = self.total_bets[value] / total
        else:
            total = sum(self.total_bets.get(opt, 0.0) for opt in self.options)
            if total > 0:
                self.current_prices = {
                    opt: self.total_bets.get(opt, 0.0) / total 
                    for opt in self.options
                }
            else:
                uniform = 1.0 / len(self.options)
                self.current_prices = {opt: uniform for opt in self.options}

    def resolve(self, outcome: Union[str, float]):
        """Resolve the market with final outcome"""
        if self.market_type == MarketType.SCALAR:
            if not self.range_min <= float(outcome) <= self.range_max:
                raise ValueError(f"Resolution outcome {outcome} is outside valid range")
        else:
            if outcome not in self.options:
                raise ValueError(f"Resolution outcome {outcome} is not a valid option")
        
        self.resolved = True
        self.outcome = outcome

    class Config:
        schema_extra = {
            "examples": [
                {
                    # Binary market example
                    "event_id": "fed_50bps_cut_march",
                    "market_type": "BINARY",
                    "question": "Will the Fed cut rates by 50+ bps in March 2024?",
                    "options": ["Yes", "No"],
                    "total_bets": {"Yes": 1000.0, "No": 9000.0},
                    "current_prices": {"Yes": 0.1, "No": 0.9},
                    "total_liquidity": 10000.0,
                    "resolved": False
                },
                {
                    # Categorical market example
                    "event_id": "fed_march_decision",
                    "market_type": "CATEGORICAL",
                    "question": "What will be the Fed's rate decision in March 2024?",
                    "options": ["No Change", "25 bps decrease", "50+ bps decrease", "25+ bps increase"],
                    "total_bets": {"No Change": 9720.0, "25 bps decrease": 140.0, "50+ bps decrease": 100.0, "25+ bps increase": 40.0},
                    "current_prices": {"No Change": 0.972, "25 bps decrease": 0.014, "50+ bps decrease": 0.01, "25+ bps increase": 0.004},
                    "total_liquidity": 10000.0,
                    "resolved": False
                },
                {
                    # Scalar market example
                    "event_id": "fed_rate_exact",
                    "market_type": "SCALAR",
                    "question": "What will be the exact Fed Funds Rate after March 2024 meeting?",
                    "range_min": 3.5,
                    "range_max": 5.5,
                    "total_bets": {"5.25": 8000.0, "5.0": 2000.0},
                    "current_prices": {"5.25": 0.8, "5.0": 0.2},
                    "total_liquidity": 10000.0,
                    "resolved": False
                }
            ]
        }

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
    round_summaries: List[Dict[str, Any]] = Field(default_factory=list)
    last_step: Optional[EnvironmentStep] = None
    market_config: Optional[Dict[str, Any]] = None
    last_action: Optional[GlobalPredictionMarketAction] = None  # Add this field

    def initialize_market(self, market_config: Dict[str, Any]) -> None:
        """Initialize market state from config"""
        market_id = market_config.get('name', 'default_market')
        market_type = MarketType(market_config['market_type'].upper())
        
        self.markets[market_id] = MarketState(
            event_id=market_id,
            market_type=market_type,
            question=market_config['market'],
            options=market_config['outcomes'],
            total_bets={},
            current_prices=market_config['initial_prices'],
            total_liquidity=market_config.get('initial_liquidity', self.initial_liquidity)
        )

    def _create_observations(self) -> Dict[str, PredictionMarketLocalObservation]:
        """Create observations for all agents"""
        if not self.last_action:
            return {}
            
        local_observations: Dict[str, PredictionMarketLocalObservation] = {}
        market_obs = PredictionMarketObservation(market_states=self.markets)
        
        # Create observation for each agent that placed a bet
        for agent_id in self.last_action.actions.keys():
            local_obs = PredictionMarketLocalObservation(
                agent_id=agent_id,
                observation=market_obs
            )
            local_observations[agent_id] = local_obs
            
        return local_observations

    def step(self, action: GlobalPredictionMarketAction) -> EnvironmentStep:
        self.current_round += 1
        self.last_action = action  # Store last action for observation creation

        # Process bets
        round_actions = {}
        for agent_id, local_action in action.actions.items():
            bet = local_action.action
            round_actions[agent_id] = bet.dict()
            
            if bet.action_type != ActionType.HOLD:
                if bet.event_id not in self.markets:
                    if self.market_config:
                        self.initialize_market(self.market_config)
                    else:
                        raise ValueError(f"No market configuration found for event {bet.event_id}")
                self.markets[bet.event_id].update_with_bet(bet)

        self.round_summaries.append(round_actions)

        # Create observations using the helper method
        local_observations = self._create_observations()
        
        # Check if market is done
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

        # Create step result
        step_result = EnvironmentStep(
            global_observation=global_obs,
            done=done,
            info={
                "round": self.current_round,
                "agent_rewards": {agent_id: 1.0 for agent_id in action.actions.keys()},
                "market_states": {k: v.dict() for k, v in self.markets.items()}
            }
        )
        self.last_step = step_result
        return step_result


    def _resolve_markets(self):
        """Resolve markets at end of simulation"""
        for event_id, market in self.markets.items():
            if not market.resolved:
                try:
                    # Resolve on blockchain
                    outcome = random.choice(market.options)
                    tx_hash = self.ethereum_interface.resolve_market(
                        self.market_contracts[event_id],
                        outcome
                    )
                    logger.info(f"Resolved market {event_id} with outcome {outcome}. TX: {tx_hash}")
                    
                    # Update local state
                    market.resolved = True
                    market.outcome = outcome
                    
                except Exception as e:
                    logger.error(f"Failed to resolve market: {e}")

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
    current_step: int = Field(default=0)
    max_steps: int = Field(default=10)
    action_space: PredictionMarketActionSpace = Field(default_factory=PredictionMarketActionSpace)
    observation_space: PredictionMarketObservationSpace = Field(default_factory=PredictionMarketObservationSpace)
    mechanism: PredictionMarketMechanism
    history: EnvironmentHistory = Field(default_factory=EnvironmentHistory)
    market_config: Optional[Dict[str, Any]] = None

    def __init__(self, **data):
        super().__init__(**data)
        if self.market_config:
            self.mechanism.market_config = self.market_config
            self.mechanism.initialize_market(self.market_config)

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