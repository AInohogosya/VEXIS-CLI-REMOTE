import { execSync } from 'child_process';

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

export function executeCommands(messageContent: string, senderJid: string, senderPhone: string): string {
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
              const result = execSync(cmd.command, {
                encoding: 'utf-8',
                timeout: 300000,
                killSignal: 'SIGTERM',
                stdio: ['pipe', 'pipe', 'pipe']
              });
              console.log(`[Command:${cmd.name}] Executed: ${cmd.command}`);
              results.push(`Exec: ${result.trim().substring(0, 200)}`);
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
