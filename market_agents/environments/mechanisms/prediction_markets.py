# prediction_market.py

from typing import Dict, Any, List, Optional, Type, Union, Tuple
from pydantic import BaseModel, Field, validator, computed_field
from datetime import datetime
import random
import string

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


class PredictionBet(BaseModel):
    event_id: str = Field(..., description="Identifier of the market event")
    outcome: str = Field(..., description="Outcome option (e.g. 'Yes' or 'No', or a range label)")
    stake: float = Field(..., description="Amount of stake placed")
    price: Optional[float] = Field(None, description="Price at which the bet was placed (optional)")

    @validator('stake')
    def stake_positive(cls, v):
        if v <= 0:
            raise ValueError("Stake must be positive")
        return v

class PredictionMarketAction(LocalAction):
    action: PredictionBet

    @classmethod
    def sample(cls, agent_id: str) -> 'PredictionMarketAction':

        event_id = random.choice(["unemployment_Feb", "jobs_Feb", "kanye_tweets"])
        outcome = random.choice(["Yes", "No"])
        stake = round(random.uniform(10, 100), 2)
        price = round(random.uniform(0.3, 0.7), 2)
        bet = PredictionBet(event_id=event_id, outcome=outcome, stake=stake, price=price)
        return cls(agent_id=agent_id, action=bet)

class GlobalPredictionMarketAction(GlobalAction):
    actions: Dict[str, PredictionMarketAction]

class MarketState(BaseModel):
    event_id: str = Field(..., description="Unique identifier for the event")
    question: str = Field(..., description="The market poll question")
    options: List[str] = Field(..., description="List of outcome options (e.g. ['Yes', 'No'])")
    total_bets: Dict[str, float] = Field(default_factory=dict, description="Total stake per option")
    current_prices: Dict[str, float] = Field(default_factory=dict, description="Current market probabilities per option")
    resolved: bool = Field(default=False, description="Whether the event is resolved")
    outcome: Optional[str] = Field(default=None, description="The resolved outcome, if any")

    def update_with_bet(self, bet: PredictionBet):
        if bet.outcome not in self.options:
            raise ValueError(f"Outcome {bet.outcome} is not a valid option for event {self.event_id}")
        self.total_bets[bet.outcome] = self.total_bets.get(bet.outcome, 0.0) + bet.stake
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

class PredictionMarketActionSpace(BaseModel):
    allowed_actions: List[Type[LocalAction]] = Field(default_factory=lambda: [PredictionMarketAction])

    def sample(self, agent_id: str) -> PredictionMarketAction:
        return PredictionMarketAction.sample(agent_id)

    def get_action_schema(self) -> Dict[str, Any]:
        return PredictionMarketAction.schema()

class PredictionMarketObservationSpace(BaseModel):
    allowed_observations: List[Type[LocalObservation]] = Field(default_factory=lambda: [PredictionMarketLocalObservation])

class PredictionMarketMechanism(BaseModel):
    max_rounds: int = Field(default=10, description="Maximum number of rounds for the market")
    current_round: int = Field(default=0, description="Current round number")
    markets: Dict[str, MarketState] = Field(default_factory=dict)
    sequential: bool = Field(default=False, description="Whether the mechanism is sequential")

    def step(self, action: GlobalPredictionMarketAction) -> EnvironmentStep:
        self.current_round += 1

        for agent_id, local_action in action.actions.items():
            bet = local_action.action
            if bet.event_id not in self.markets:
                self.markets[bet.event_id] = MarketState(
                    event_id=bet.event_id,
                    question=f"Market poll for event {bet.event_id}",
                    options=["Yes", "No"],
                    total_bets={},
                    current_prices={}
                )
                uniform = 0.5
                self.markets[bet.event_id].current_prices = {"Yes": uniform, "No": uniform}
            self.markets[bet.event_id].update_with_bet(bet)

        if self.current_round >= self.max_rounds:
            for market in self.markets.values():
                if not market.resolved:
                    market.resolved = True
                    market.outcome = random.choice(market.options)

        market_obs = PredictionMarketObservation(market_states=self.markets)
        local_obs = {
            agent_id: PredictionMarketLocalObservation(
                agent_id=agent_id,
                observation=market_obs
            )
            for agent_id in action.actions.keys()
        }
        global_obs = PredictionMarketGlobalObservation(
            observations=local_obs,
            market_states=self.markets
        )
        done = self.current_round >= self.max_rounds
        info = {"current_round": self.current_round}
        return EnvironmentStep(global_observation=global_obs, done=done, info=info)

    def get_global_state(self) -> Any:
        return {
            "current_round": self.current_round,
            "markets": {eid: market.dict() for eid, market in self.markets.items()}
        }

class PredictionMarketEnv(BaseModel):
    name: str = Field(default="Prediction Market", description="Name of the prediction market environment")
    current_step: int = Field(default=0, description="Current simulation step")
    max_steps: int = Field(default=10, description="Maximum number of steps")
    action_space: PredictionMarketActionSpace = Field(default_factory=PredictionMarketActionSpace)
    observation_space: PredictionMarketObservationSpace = Field(default_factory=PredictionMarketObservationSpace)
    history: List[Tuple[GlobalAction, EnvironmentStep]] = Field(default_factory=list)
    mechanism: PredictionMarketMechanism = Field(default_factory=PredictionMarketMechanism)

    def step(self, actions: GlobalPredictionMarketAction) -> EnvironmentStep:
        step_result = self.mechanism.step(actions)
        self.current_step += 1
        self.history.append((actions, step_result))
        return step_result

    def reset(self) -> GlobalObservation:
        self.current_step = 0
        self.history = []
        self.mechanism.current_round = 0
        self.mechanism.markets = {}
        return GlobalObservation(observations={})

    def get_global_state(self) -> Any:
        return self.mechanism.get_global_state()

    def render(self):
        print("Global State:")
        print(self.get_global_state())

if __name__ == "__main__":
    num_agents = 3
    num_steps = 5
    env = PredictionMarketEnv(max_steps=num_steps)
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