# main.py

import asyncio
from asyncio.log import logger
import importlib
import logging
import random
import uuid
from pathlib import Path
from typing import List, Optional, Type

from market_agents.agents.market_agent import MarketAgent
from market_agents.agents.personas.persona import generate_persona
from market_agents.memory.knowledge_base import MarketKnowledgeBase
from market_agents.memory.knowledge_base_agent import KnowledgeBaseAgent
from market_agents.memory.config import AgentStorageConfig, load_config_from_yaml

from market_agents.orchestrators.config import load_config
from market_agents.orchestrators.meta_orchestrator import MetaOrchestrator
from market_agents.agents.protocols.acl_message import ACLMessage
from market_agents.inference.message_models import LLMConfig

from market_agents.orchestrators.groupchat_orchestrator import GroupChatOrchestrator
from market_agents.orchestrators.research_orchestrator import ResearchOrchestrator

from market_agents.memory.agent_storage.agent_storage_api_utils import AgentStorageAPIUtils

logger = logging.getLogger(__name__)

async def create_kb_agent(config: AgentStorageConfig, kb_name: str) -> Optional[KnowledgeBaseAgent]:
    if not kb_name:
        logger.info("No knowledge base specified in config")
        return None

    try:
        storage_utils = AgentStorageAPIUtils(
            config=config,
            logger=logging.getLogger("storage_api")
        )
        
        is_healthy = await storage_utils.check_api_health()
        if not is_healthy:
            logger.error("Storage API health check failed")
            return None

        logger.info(f"Creating MarketKnowledgeBase with prefix '{kb_name}'")
        market_kb = MarketKnowledgeBase(
            config=config,
            table_prefix=kb_name
        )
        
        logger.info(f"Initializing knowledge base '{kb_name}'")
        await market_kb.initialize()
        
        logger.info(f"Checking if knowledge base '{kb_name}' exists")
        exists = await market_kb.check_table_exists()
        if not exists:
            logger.warning(f"Knowledge base '{kb_name}' tables not found or empty")
            return None

        kb_agent = KnowledgeBaseAgent(market_kb=market_kb)
        logger.info(f"Successfully initialized knowledge base agent with '{kb_name}'")
        return kb_agent
        
    except Exception as e:
        logger.error(f"Failed to initialize knowledge base '{kb_name}': {str(e)}")
        return None

async def create_agents(
    config,
    storage_config: AgentStorageConfig,
) -> List[MarketAgent]:
    """Create market agents with specified configurations.
    
    Args:
        config: Orchestrator configuration
        storage_config (AgentStorageConfig): Storage configuration
        
    Returns:
        List[MarketAgent]: List of initialized market agents
    """
    agents = []
    num_agents = config.num_agents

    storage_utils = AgentStorageAPIUtils(config=storage_config)

    # Initialize knowledge base agent
    kb_agent = await create_kb_agent(storage_config, config.agent_config.knowledge_base)
    if not kb_agent and config.agent_config.knowledge_base:
        logger.warning("Failed to initialize knowledge base agent, continuing without it")

    # Create agents with random LLM configs
    llm_confs = config.llm_configs
    if not llm_confs:
        raise ValueError("No LLM configurations found in config")

    for i in range(num_agents):
        agent_id = f"agent_{i}"
        llm_c = random.choice(llm_confs)
        persona = generate_persona()

        try:
            agent = await MarketAgent.create(
                storage_utils=storage_utils,
                agent_id=agent_id,
                use_llm=True,
                llm_config=LLMConfig(
                    model=llm_c.model,
                    client=llm_c.client,
                    temperature=llm_c.temperature,
                    max_tokens=llm_c.max_tokens,
                    use_cache=llm_c.use_cache
                ),
                environments={},
                protocol=ACLMessage,
                persona=persona,
                econ_agent=None,
                knowledge_agent=kb_agent
            )

            agent.index = i
            agents.append(agent)
            logger.info(f"Created agent {agent_id} with LLM {llm_c.name}")
            
        except Exception as e:
            logger.error(f"Failed to create agent {agent_id}: {str(e)}")
            continue

    if not agents:
        raise RuntimeError("Failed to create any agents")

    return agents

async def main():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("meta_orchestrator")

    config_path = Path("market_agents/orchestrators/orchestrator_config.yaml")
    config = load_config(config_path)

    storage_config_path = Path("market_agents/memory/storage_config.yaml")
    storage_config = load_config_from_yaml(str(storage_config_path))

    agents = await create_agents(config, storage_config)

    orchestrator_registry = {}
    orchestrator_map = {
        "group_chat": GroupChatOrchestrator,
        "research": ResearchOrchestrator
    }
    
    if hasattr(config, 'environment_order'):
        for env_name in config.environment_order:
            if env_name in orchestrator_map:
                orchestrator_registry[env_name] = orchestrator_map[env_name]

    if not orchestrator_registry:
        orchestrator_registry["group_chat"] = GroupChatOrchestrator

    meta_orch = MetaOrchestrator(
        config=config,
        agents=agents,
        orchestrator_registry=orchestrator_registry,
        logger=logger
    )

    await meta_orch.start()

if __name__ == "__main__":
    asyncio.run(main())