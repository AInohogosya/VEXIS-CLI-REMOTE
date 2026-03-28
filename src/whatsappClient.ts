import makeWASocket, { DisconnectReason, WASocket, useMultiFileAuthState } from '@whiskeysockets/baileys';
import { Boom } from '@hapi/boom';
import qrcode from 'qrcode-terminal';
import { config } from './config';
import { executeCommands } from './commandExecutor';
import { WhatsAppMessage } from './types';
import { join } from 'path';
import { existsSync, mkdirSync } from 'fs';

// WhatsApp client instance
let waSocket: WASocket | null = null;

// Generate QR code for connection
function generateQRCode(qr: string): void {
  try {
    console.log('\n[WA] 📱 Scan this QR code with WhatsApp:');
    console.log('[WA]    1. Open WhatsApp on your phone');
    console.log('[WA]    2. Go to Settings > Linked Devices');
    console.log('[WA]    3. Tap "Link a device" and scan the code below\n');
    
    // Generate QR code with larger size for better visibility
    console.log('[WA] Generating QR code...');
    qrcode.generate(qr, { 
      small: false
    });
    
    console.log('\n[WA] ⏳ Waiting for scan...');
    console.log('[WA] QR code length:', qr.length);
    console.log('[WA] QR code preview:', qr.substring(0, 50) + '...');
  } catch (error) {
    console.error('[WA] Error generating QR code:', error);
    console.log('[WA] Raw QR string:', qr);
  }
}

// Handle incoming messages
async function handleMessage(message: WhatsAppMessage): Promise<void> {
  try {
    const senderJid = message.key.remoteJid;
    const senderPhone = senderJid.replace('@s.whatsapp.net', '').replace('@g.us', '');

    console.log(`[WA] Received message from: ${senderPhone}`);

    // Extract message content
    let messageContent = '';
    if (message.message?.conversation) {
      messageContent = message.message.conversation;
    } else if (message.message?.extendedTextMessage?.text) {
      messageContent = message.message.extendedTextMessage.text;
    }

    if (!messageContent) {
      console.log('[WA] Empty message, skipping');
      return;
    }

    console.log(`[WA] Processing message: "${messageContent}"`);

    // Execute ALL commands from command.json regardless of message content
    const result = executeCommands(messageContent, senderJid, senderPhone);

    // Send result back to WhatsApp
    await waSocket?.sendMessage(senderJid, { text: result });
    console.log(`[WA] Sent command result to ${senderPhone}`);

  } catch (error) {
    console.error('[WA] Error handling message:', error);
  }
}

export async function startWhatsAppClient(): Promise<void> {
  try {
    console.log('[WA] Initializing WhatsApp client...');
    
    // Create auth directory if it doesn't exist
    const authFolder = join(process.cwd(), 'auth');
    if (!existsSync(authFolder)) {
      mkdirSync(authFolder, { recursive: true });
    }
    
    console.log('[WA] Auth folder path:', authFolder);
    
    // Clear any existing auth to force QR code generation
    const { rmSync, readdirSync } = require('fs');
    if (existsSync(authFolder)) {
      try {
        const files = readdirSync(authFolder);
        console.log('[WA] Existing auth files:', files);
        if (files.length > 0) {
          console.log('[WA] Clearing existing auth files to force QR generation...');
          files.forEach((file: string) => {
            rmSync(join(authFolder, file), { force: true });
          });
          console.log('[WA] Auth files cleared');
        }
      } catch (error) {
        console.log('[WA] Could not clear auth folder:', error);
      }
    }
    
    console.log('[WA] Getting auth state...');
    // Get auth state
    const { state, saveCreds } = await useMultiFileAuthState(authFolder);
    
    console.log('[WA] Creating WhatsApp socket...');
    // Create new WhatsApp socket with Chrome browser signature
    waSocket = makeWASocket({
      auth: state,
      browser: ['Chrome (Mac OS)', '', ''],
      connectTimeoutMs: 60000,
      qrTimeout: 60000,
      defaultQueryTimeoutMs: 20000,
      keepAliveIntervalMs: 25000,
      mobile: false,
      retryRequestDelayMs: 2500
    });
    
    console.log('[WA] Socket created successfully');
    console.log('[WA] Setting up event listeners...');
    
    // Save credentials when updated
    waSocket.ev.on('creds.update', saveCreds);
    
    // Handle connection events with detailed logging
    waSocket.ev.on('connection.update', (update: any) => {
      console.log('[WA] === CONNECTION UPDATE ===');
      console.log('[WA] Full update:', JSON.stringify(update, null, 2));
      console.log('[WA] =========================');
      
      const { connection, lastDisconnect, qr } = update;
      
      // Display QR code when available
      if (qr) {
        console.log('\n[WA] 🎉 QR CODE RECEIVED!');
        console.log('[WA] QR Code length:', qr.length);
        console.log('[WA] QR Code preview:', qr.substring(0, 50) + '...');
        
        // Also try our custom QR generation
        console.log('\n[WA] Generating custom QR code...');
        generateQRCode(qr);
      }
      
      if (connection === 'close') {
        const shouldReconnect = (lastDisconnect?.error as Boom)?.output?.statusCode !== DisconnectReason.loggedOut;
        console.log(`[WA] Connection closed due to ${lastDisconnect?.error?.message || 'unknown error'}, reconnecting: ${shouldReconnect}`);
        
        if (shouldReconnect) {
          console.log('[WA] Attempting to reconnect in 5 seconds...');
          setTimeout(() => startWhatsAppClient(), 5000);
        } else {
          console.log('[WA] Logged out, please scan QR code again');
        }
      }
      
      if (connection === 'open') {
        console.log('[WA] ✅ WhatsApp connection opened successfully');
        console.log(`[WA] 🤖 Bot is ready! Send messages to ${config.ownPhoneNumber}`);
      }
      
      if (connection === 'connecting') {
        console.log('[WA] Connecting to WhatsApp...');
      }
    });
    
    waSocket.ev.on('messages.upsert', async (m: any) => {
      const message = m.messages[0];
      if (message && !message.key.fromMe) {
        await handleMessage(message as WhatsAppMessage);
      }
    });
    
    console.log('[WA] WhatsApp client setup completed');
    
  } catch (error) {
    console.error('[WA] Failed to start WhatsApp client:', error);
    if (error instanceof Error) {
      console.error('[WA] Error details:', error.stack);
    }
    setTimeout(() => startWhatsAppClient(), 10000); // Retry after 10 seconds
  }
}

// Get current socket instance
export function getWhatsAppSocket(): WASocket | null {
  return waSocket;
}
