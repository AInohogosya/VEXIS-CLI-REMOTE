import { spawn } from 'child_process';

interface Command {
  name: string;
  action: string;
  description: string;
  command?: string;
}

let cachedCommands: Command[] | null = null;

function loadCommands(): Command[] {
  if (cachedCommands) return cachedCommands;
  try {
    const commands = require('../command.json');
    cachedCommands = commands;
    return commands;
  } catch (error) {
    console.error('[Command] Failed to load command.json:', error);
    return [];
  }
}

function execWithOutput(command: string): Promise<string> {
  return new Promise((resolve, reject) => {
    const [cmd, ...args] = command.split(' ');
    const child = spawn(cmd, args, {
      stdio: ['pipe', 'inherit', 'inherit'],
      shell: true
    });

    let output = '';
    child.stdout?.on('data', (data) => {
      output += data.toString();
    });

    child.on('close', (code) => {
      if (code === 0) {
        resolve(output);
      } else {
        reject(new Error(`Command exited with code ${code}`));
      }
    });

    child.on('error', (err) => {
      reject(err);
    });
  });
}

export async function executeCommands(messageContent: string, senderJid: string, senderPhone: string): Promise<string> {
  const commands = loadCommands();
  const results: string[] = [];

  for (const cmd of commands) {
    try {
      switch (cmd.action) {
        case 'log':
          console.log(`[Command:${cmd.name}] Message from ${senderPhone}: "${messageContent}"`);
          results.push(`Logged: ${messageContent.substring(0, 50)}`);
          break;

        case 'exec':
          if (cmd.command) {
            try {
              console.log(`[Command:${cmd.name}] Executing: ${cmd.command}`);
              const result = await execWithOutput(cmd.command);
              results.push(`Exec: ${cmd.name} completed`);
            } catch (error) {
              const errorMsg = error instanceof Error ? error.message : 'Unknown error';
              console.error(`[Command:${cmd.name}] Error:`, errorMsg);
              results.push(`Error in ${cmd.name}: ${errorMsg}`);
            }
          }
          break;

        default:
          console.log(`[Command:${cmd.name}] Unknown action: ${cmd.action}`);
      }
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'Unknown error';
      console.error(`[Command:${cmd.name}] Error:`, errorMsg);
      results.push(`Error in ${cmd.name}: ${errorMsg}`);
    }
  }

  return results.join('\n') || 'Commands executed';
}
