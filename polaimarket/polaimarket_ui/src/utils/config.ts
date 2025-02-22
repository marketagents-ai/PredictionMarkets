import { parse as yamlParse, stringify as yamlStringify } from 'yaml';
import path from 'path';
import fs from 'fs/promises';

export async function updateOrchestratorConfig(newConfig: {
  num_agents: number;
  max_rounds: number;
  environment_configs: {
    prediction_markets: any;
  };
}) {
  try {
    // Get absolute path to project root (3 levels up from current file)
    const projectRoot = path.resolve(__dirname, '../../../../..');
    const configPath = path.join(projectRoot, 'market_agents/orchestrators/orchestrator_config.yaml');
    
    console.log('Reading config from:', configPath);
    
    // Read existing config
    const existingConfig = yamlParse(await fs.readFile(configPath, 'utf8'));
    
    // Merge configs
    const updatedConfig = {
      ...existingConfig,
      num_agents: newConfig.num_agents,
      max_rounds: newConfig.max_rounds,
      environment_configs: {
        ...existingConfig.environment_configs,
        prediction_markets: newConfig.environment_configs.prediction_markets
      }
    };
    
    await fs.writeFile(configPath, yamlStringify(updatedConfig));
  } catch (error) {
    console.error('Error updating config:', error);
    throw error;
  }
}