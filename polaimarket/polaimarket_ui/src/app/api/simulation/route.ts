import { exec } from 'child_process';
import { NextResponse } from 'next/server';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import fs from 'fs';

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { numAgents, maxRounds, marketConfig } = body;

    // Get absolute paths
    const __filename = fileURLToPath(import.meta.url);
    const __dirname = dirname(__filename);
    const projectRoot = join(__dirname, '..', '..', '..', '..', '..', '..');

    // Prepare config overrides
    const configOverride = {
      num_agents: numAgents,
      max_rounds: maxRounds,
      environment_order: ["prediction_markets"],
      tool_mode: true,
      agent_config: {
        use_llm: true
      },
      environment_configs: {
        prediction_markets: {
          name: "prediction_markets",
          market_type: marketConfig.marketType || "CATEGORICAL",
          market: marketConfig.question,
          description: marketConfig.description,
          resolution_criteria: "Market will be resolved based on official announcements",
          resolution_date: marketConfig.resolutionDate,
          initial_liquidity: parseFloat(marketConfig.initialLiquidity),
          min_bet: 1.0,
          max_bet: 100.0,
          outcomes: marketConfig.outcomes,
          initial_prices: marketConfig.initialPrices || 
            Object.fromEntries(
              marketConfig.outcomes.map(outcome => [outcome, 1.0 / marketConfig.outcomes.length])
            )
        }
      }
    };

    // Create encoder for streaming
    const encoder = new TextEncoder();
    const stream = new TransformStream({
      transform(chunk, controller) {
        controller.enqueue(encoder.encode(`data: ${JSON.stringify(chunk)}\n\n`));
      }
    });

    const writer = stream.writable.getWriter();

    // Properly escape the JSON string for command line
    const configString = JSON.stringify(configOverride).replace(/'/g, "'\\''");

    // Execute main.py directly with properly escaped config override
    const childProcess = exec(
      `PYTHONUNBUFFERED=1 FORCE_COLOR=1 python3 main.py --config-override='${configString}'`,
      {
        cwd: projectRoot,
        env: {
          ...process.env,
          PYTHONUNBUFFERED: '1',
          FORCE_COLOR: '1',
          TERM: 'xterm-256color',
          PYTHONIOENCODING: 'utf-8'
        }
      }
    );

    if (!childProcess.stdout || !childProcess.stderr) {
      throw new Error('Failed to create process streams');
    }

    // Stream stdout
    childProcess.stdout.on('data', async (data) => {
      try {
        await writer.write(data);
      } catch (error) {
        console.error('Error writing stdout:', error);
      }
    });

    // Stream stderr
    childProcess.stderr.on('data', async (data) => {
      try {
        await writer.write(data);
      } catch (error) {
        console.error('Error writing stderr:', error);
      }
    });

    // Handle process completion
    childProcess.on('close', async () => {
      try {
        await writer.close();
      } catch (error) {
        console.error('Error closing writer:', error);
      }
    });

    // Return the readable stream
    return new Response(stream.readable, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
      },
    });

  } catch (error) {
    console.error('Error in API route:', error);
    return NextResponse.json({ 
      error: 'Failed to start simulation',
      details: error instanceof Error ? error.message : String(error)
    }, { status: 500 });
  }
}
