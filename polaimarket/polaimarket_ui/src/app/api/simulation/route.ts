import { exec } from 'child_process';
import { NextResponse } from 'next/server';
import path from 'path';

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { numAgents, maxRounds, marketConfig } = body;

    // Get absolute path to PredictionMarkets root directory
    const projectRoot = path.resolve(process.cwd(), '../../../../PredictionMarkets');
    const scriptPath = path.join(projectRoot, 'run_simulation.sh');
    
    console.log('Project root:', projectRoot);
    console.log('Executing simulation script at:', scriptPath);
    console.log('With config:', { numAgents, maxRounds, marketConfig });

    // Execute the simulation script with parameters
    return new Promise((resolve) => {
      // Change directory to project root and execute script
      exec(`cd "${projectRoot}" && bash "${scriptPath}"`, (error, stdout, stderr) => {
        if (error) {
          console.error(`Error: ${error}`);
          resolve(NextResponse.json({ error: 'Failed to start simulation' }, { status: 500 }));
          return;
        }
        console.log(`stdout: ${stdout}`);
        console.error(`stderr: ${stderr}`);
        resolve(NextResponse.json({ status: 'Simulation started', output: stdout }));
      });
    });

  } catch (error) {
    console.error('Error:', error);
    return NextResponse.json({ error: 'Failed to start simulation' }, { status: 500 });
  }
}