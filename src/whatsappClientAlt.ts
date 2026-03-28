import { Client } from 'whatsapp-web.js';
import { config } from './config';
import { readFileSync } from 'fs';
import { join } from 'path';
import { execSync } from 'child_process';

// Command interface
interface Command {
  name: string;
  action: string;
  description?: string;
  command?: string;
}

// Load commands from command.json
function loadCommands(): Command[] {
  try {
    const commandPath = join(process.cwd(), 'command.json');
    const data = readFileSync(commandPath, 'utf-8');
    return JSON.parse(data) as Command[];
  } catch (error) {
    console.error('[WA] Failed to load command.json:', error);
    return [];
  }
}

// Execute a single command
async function executeCommand(cmd: Command, messageContent: string, senderJid: string): Promise<string> {
  console.log(`[WA] Executing command: ${cmd.name} (${cmd.action})`);
  
  switch (cmd.action) {
    case 'log':
      console.log(`[WA] [LOG] Message content: "${messageContent}"`);
      return `Logged: ${messageContent.substring(0, 50)}`;
      
    case 'exec':
      if (cmd.command) {
        try {
          const result = execSync(cmd.command, { encoding: 'utf-8', timeout: 30000 });
          console.log(`[WA] [EXEC] Command: ${cmd.command}, Output: ${result.trim().substring(0, 100)}`);
          return `Exec result: ${result.trim().substring(0, 200)}`;
        } catch (error) {
          const errorMsg = error instanceof Error ? error.message : 'Unknown error';
          console.error(`[WA] [EXEC ERROR] ${errorMsg}`);
          return `Exec error: ${errorMsg}`;
        }
      }
      return 'No command specified';
      
    default:
      console.log(`[WA] Unknown command action: ${cmd.action}`);
      return `Unknown action: ${cmd.action}`;
  }
}

// WhatsApp client instance
let waClient: Client | null = null;

// Bot response prefixes - messages starting with these should be ignored to prevent loops
const BOT_RESPONSE_PREFIXES = ['Logged:', 'Exec result:', 'Exec error:', 'Commands executed', 'Unknown action:'];

// Handle incoming messages - executes commands for ALL messages regardless of content
async function handleMessage(message: any): Promise<void> {
  try {
    // Get message content first
    const messageContent = message.body || message.content || message.text || message.caption || '';
    
    // Ignore messages that look like bot responses (prevents infinite loops)
    if (BOT_RESPONSE_PREFIXES.some(prefix => messageContent.startsWith(prefix))) {
      return;
    }
    
    console.log(`[DEBUG] Processing message from: ${message.from}, body: "${messageContent.substring(0, 50)}"`);

    // Extract sender phone number from different possible formats
    let senderPhone = '';
    if (message.from) {
      senderPhone = message.from.replace('@c.us', '').replace('@s.whatsapp.net', '').replace('@g.us', '');
    } else if (message.author) {
      senderPhone = message.author.replace('@c.us', '').replace('@s.whatsapp.net', '').replace('@g.us', '');
    } else if (message.id?.remote) {
      senderPhone = message.id.remote.replace('@c.us', '').replace('@s.whatsapp.net', '').replace('@g.us', '');
    }

    console.log('\n========================================');
    console.log('[WA] 📩 RECEIVED MESSAGE:');
    console.log(`[WA] Content: "${messageContent}"`);
    console.log(`[WA] From: ${senderPhone}`);
    console.log('========================================\n');

    // Execute ALL commands from command.json for EVERY message (no filtering)
    const commands = loadCommands();
    console.log(`[WA] Executing ${commands.length} commands from command.json...`);

    const recipient = message.from || message.chatId || message.id?.remote;
    const results: string[] = [];

    for (const cmd of commands) {
      const result = await executeCommand(cmd, messageContent, recipient);
      results.push(result);
    }

    // Send results back to WhatsApp
    const responseText = results.join('\n') || 'Commands executed';
    await waClient?.sendMessage(recipient, responseText);
    
    console.log('[WA] All commands executed.\n');

  } catch (error) {
    console.error('[WA] Error handling message:', error);
  }
}

// Start WhatsApp client with whatsapp-web.js
export async function startWhatsAppClient(): Promise<void> {
  try {
    // Create new WhatsApp client (no local auth - no session caching)
    waClient = new Client({
      puppeteer: {
        headless: true,
        args: ['--no-sandbox']
      }
    });

    // Handle QR code generation
    waClient.on('qr', (qr: string) => {
      console.log('[WA] QR Code received! Displaying...');
      // Generate QR code in terminal
      const qrcode = require('qrcode-terminal');
      qrcode.generate(qr, { small: false });
    });

    // Handle authentication
    waClient.on('authenticated', () => {
      // Authentication successful
    });

    // Handle ready state
    waClient.on('ready', () => {
      console.log('[WA] Client is ready!');
    });

    // Handle incoming messages
    waClient.on('message', (msg) => {
      console.log(`[WA] Event 'message' received from: ${msg.from}`);
      handleMessage(msg);
    });
    
    // Also try message_create as backup
    waClient.on('message_create', (msg) => {
      console.log(`[WA] Event 'message_create' received from: ${msg.from}`);
      handleMessage(msg);
    });

    // Handle disconnection
    waClient.on('disconnected', () => {
      setTimeout(() => startWhatsAppClient(), 10000);
    });

    // Handle authentication failure
    waClient.on('auth_failure', () => {
      // Authentication failed
    });

    await waClient.initialize();
    
  } catch (error) {
    setTimeout(() => startWhatsAppClient(), 10000); // Retry after 10 seconds
  }
}

// Get current client instance
export function getWhatsAppClient(): Client | null {
  return waClient;
}
