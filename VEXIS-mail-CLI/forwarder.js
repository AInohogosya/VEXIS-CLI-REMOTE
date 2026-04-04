#!/usr/bin/env node

/**
 * Message Forwarder Service
 * Forwards messages from VEXIS-mail-CLI to VEXIS-CLI-2 and sends responses back
 * 
 * Usage: node forwarder.js
 * 
 * This service:
 * 1. Listens for new "user" messages in Firebase Firestore
 * 2. Executes VEXIS-CLI-2 with --no-prompt mode
 * 3. Sends the AI response back to Firebase
 */

import { initializeApp } from 'firebase/app';
import { 
  getAuth, 
  signInWithEmailAndPassword,
  onAuthStateChanged
} from 'firebase/auth';
import { 
  getFirestore, 
  collection, 
  query, 
  orderBy, 
  onSnapshot, 
  serverTimestamp,
  doc,
  updateDoc,
  addDoc
} from 'firebase/firestore';
import { spawn } from 'child_process';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import * as readline from 'readline';
import { readFileSync, writeFileSync, existsSync } from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Firebase config
const firebaseConfig = {
  apiKey: "AIzaSyCgBfSlqZXwraxuxFAxZKG0GXHv-XP7umE",
  authDomain: "vexis.cli-remote-f6f4c.firebaseapp.com",
  projectId: "vexis-cli-remote-f6f4c",
  storageBucket: "vexis-cli-remote-f6f4c.firebasestorage.app",
  messagingSenderId: "420034681058",
  appId: "1:420034681058:web:86f601782961cf5d12e6bb"
};

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const db = getFirestore(app);

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

function question(prompt) {
  return new Promise((resolve) => {
    rl.question(prompt, resolve);
  });
}

// Path to VEXIS-CLI-2
const VEXIS_CLI_2_PATH = join(__dirname, '..', 'VEXIS-CLI-2', 'run.py');

// Settings file path
const SETTINGS_FILE = join(__dirname, 'forwarder_settings.json');

// Valid providers list
const VALID_PROVIDERS = [
  'ollama', 'google', 'openai', 'anthropic', 'xai', 'meta', 
  'groq', 'deepseek', 'together', 'microsoft', 'mistral', 
  'amazon', 'cohere', 'minimax', 'zhipuai'
];

// API key environment variable mapping for each provider
const API_KEY_ENV_VARS = {
  'google': 'GOOGLE_API_KEY',
  'openai': 'OPENAI_API_KEY',
  'anthropic': 'ANTHROPIC_API_KEY',
  'xai': 'XAI_API_KEY',
  'meta': 'META_API_KEY',
  'groq': 'GROQ_API_KEY',
  'deepseek': 'DEEPSEEK_API_KEY',
  'together': 'TOGETHER_API_KEY',
  'microsoft': 'AZURE_API_KEY',
  'mistral': 'MISTRAL_API_KEY',
  'amazon': ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY'],
  'cohere': 'COHERE_API_KEY',
  'minimax': 'MINIMAX_API_KEY',
  'zhipuai': 'ZHIPUAI_API_KEY'
};

// Default settings
let settings = {
  provider: 'ollama',
  model: 'qwen3.5:2b',
  apiKeys: {}  // Store API keys for each provider
};

/**
 * Load settings from file
 */
function loadSettings() {
  try {
    if (existsSync(SETTINGS_FILE)) {
      const data = readFileSync(SETTINGS_FILE, 'utf8');
      settings = JSON.parse(data);
      // Ensure apiKeys exists for backward compatibility
      if (!settings.apiKeys) {
        settings.apiKeys = {};
      }
      console.log(`[Forwarder] Loaded settings: provider=${settings.provider}, model=${settings.model}`);
    }
  } catch (error) {
    console.log(`[Forwarder] Could not load settings, using defaults`);
  }
}

/**
 * Save settings to file
 */
function saveSettings() {
  try {
    writeFileSync(SETTINGS_FILE, JSON.stringify(settings, null, 2));
    console.log(`[Forwarder] Settings saved to ${SETTINGS_FILE}`);
  } catch (error) {
    console.error(`[Forwarder] Failed to save settings: ${error.message}`);
  }
}

// Track processed messages to avoid re-processing
const processedMessageIds = new Set();

// Track currently processing messages to prevent concurrent execution
let isProcessing = false;
const messageQueue = [];

/**
 * Execute VEXIS-CLI-2 with the given instruction
 * @param {string} instruction - The user's instruction
 * @returns {Promise<string>} - The AI response
 */
function executeVEXISCLI2(instruction) {
  return new Promise((resolve, reject) => {
    console.log(`\n[Forwarder] Executing: ${instruction}`);
    console.log(`[Forwarder] Provider: ${settings.provider}, Model: ${settings.model}`);
    
    const args = [
      VEXIS_CLI_2_PATH, 
      instruction, 
      '--no-prompt',
      '--provider', settings.provider,
      '--model', settings.model
    ];
    
    // Prepare environment with API keys for non-Ollama providers
    const env = { ...process.env };
    if (settings.provider !== 'ollama' && settings.apiKeys) {
      const envVar = API_KEY_ENV_VARS[settings.provider];
      if (envVar) {
        if (Array.isArray(envVar)) {
          // For providers requiring multiple keys (e.g., Amazon)
          envVar.forEach(varName => {
            if (settings.apiKeys[varName]) {
              env[varName] = settings.apiKeys[varName];
              console.log(`[Forwarder] Setting ${varName}: ${settings.apiKeys[varName].substring(0, 10)}...`);
            }
          });
        } else {
          // For providers requiring single key
          if (settings.apiKeys[envVar]) {
            env[envVar] = settings.apiKeys[envVar];
            console.log(`[Forwarder] Setting ${envVar}: ${settings.apiKeys[envVar].substring(0, 10)}...`);
          }
        }
      }
    }
    
    const pythonProcess = spawn('python3', args, {
      cwd: dirname(VEXIS_CLI_2_PATH),
      env: env
    });
    
    let stdout = '';
    let stderr = '';
    
    pythonProcess.stdout.on('data', (data) => {
      const output = data.toString();
      stdout += output;
      // Print output in real-time
      process.stdout.write(output);
    });
    
    pythonProcess.stderr.on('data', (data) => {
      stderr += data.toString();
      process.stderr.write(data.toString());
    });
    
    pythonProcess.on('close', (code) => {
      if (code === 0) {
        // Extract the meaningful response from stdout
        // VEXIS-CLI-2 outputs various status messages, we need to capture the actual result
        const response = extractResponse(stdout);
        resolve(response);
      } else {
        reject(new Error(`VEXIS-CLI-2 exited with code ${code}: ${stderr}`));
      }
    });
    
    pythonProcess.on('error', (err) => {
      reject(new Error(`Failed to start VEXIS-CLI-2: ${err.message}`));
    });
  });
}

/**
 * Extract the actual AI response from VEXIS-CLI-2 output
 * @param {string} output - The full stdout from VEXIS-CLI-2
 * @returns {string} - The extracted response
 */
function extractResponse(output) {
  // VEXIS-CLI-2 outputs various status messages
  // The actual AI response is typically after "AI Agent executing:" line
  // and before "✓ Task completed successfully" or similar
  
  const lines = output.split('\n');
  const responseLines = [];
  let capturing = false;
  
  for (const line of lines) {
    // Start capturing after the execution header
    if (line.includes('AI Agent executing:')) {
      capturing = true;
      continue;
    }
    
    // Stop capturing at completion markers
    if (line.includes('✓ Task completed') || 
        line.includes('✗ Task failed') ||
        line.includes('Using provider:') ||
        line.includes('Using saved provider') ||
        line.includes('Using model:')) {
      if (capturing && responseLines.length > 0) {
        // Continue capturing but skip these header lines
        continue;
      }
      continue;
    }
    
    if (capturing) {
      // Skip empty lines at the beginning
      if (responseLines.length === 0 && line.trim() === '') {
        continue;
      }
      responseLines.push(line);
    }
  }
  
  // If we couldn't extract a clean response, return a summary
  const response = responseLines.join('\n').trim();
  if (response) {
    return response;
  }
  
  // Fallback: return the whole output cleaned up
  return output
    .replace(/Using (saved )?provider:.*\n/g, '')
    .replace(/Using (saved )?model:.*\n/g, '')
    .replace(/AI Agent executing:.*\n/g, '')
    .replace(/✓ Task completed.*\n/g, '')
    .replace(/\[.*?\]/g, '') // Remove ANSI color codes
    .trim();
}

/**
 * Send a response message to Firebase
 * @param {string} uid - The user's UID
 * @param {string} content - The response content
 */
async function sendResponse(uid, content) {
  try {
    await addDoc(collection(db, `conversations/${uid}/messages`), {
      role: "assistant",
      content: content,
      timestamp: serverTimestamp(),
      read: false
    });
    console.log(`[Forwarder] Response sent to Firebase`);
  } catch (error) {
    console.error(`[Forwarder] Error sending response:`, error.message);
  }
}

/**
 * Process a single message
 * @param {object} messageData - The message data
 * @param {string} uid - The user's UID
 */
async function processMessage(messageData, uid) {
  if (isProcessing) {
    console.log(`[Forwarder] Already processing, queuing message...`);
    messageQueue.push({ messageData, uid });
    return;
  }
  
  isProcessing = true;
  
  try {
    console.log(`\n[Forwarder] Processing: "${messageData.content.substring(0, 50)}..."`);
    
    const response = await executeVEXISCLI2(messageData.content);
    
    if (response) {
      await sendResponse(uid, response);
    } else {
      await sendResponse(uid, "Task completed. (No text output)");
    }
    
    console.log(`[Forwarder] ✓ Message processed successfully`);
  } catch (error) {
    console.error(`[Forwarder] ✗ Error processing message:`, error.message);
    await sendResponse(uid, `Error: ${error.message}`);
  } finally {
    isProcessing = false;
    
    // Process next message in queue
    if (messageQueue.length > 0) {
      const next = messageQueue.shift();
      processMessage(next.messageData, next.uid);
    }
  }
}

/**
 * Start listening for messages
 * @param {string} uid - The user's UID
 */
function startMessageListener(uid) {
  console.log(`\n[Forwarder] Starting message listener for user: ${uid}`);
  console.log(`[Forwarder] VEXIS-CLI-2 path: ${VEXIS_CLI_2_PATH}`);
  console.log(`[Forwarder] Mode: --no-prompt (automatic model selection)`);
  console.log(`\n[Forwarder] Waiting for messages...`);
  console.log(`[Forwarder] Press Ctrl+C to stop\n`);

  const q = query(
    collection(db, `conversations/${uid}/messages`),
    orderBy('timestamp', 'asc')
  );

  const listenerStartTime = new Date();

  return onSnapshot(q, (snapshot) => {
    console.log(`[Forwarder] ===== SNAPSHOT =====`);
    console.log(`[Forwarder] Docs: ${snapshot.docs.length}, Changes: ${snapshot.docChanges().length}`);

    const changes = snapshot.docChanges();

    for (const change of changes) {
      const docSnap = change.doc;
      const data = docSnap.data();
      const messageId = docSnap.id;

      console.log(`[Forwarder] Change: type=${change.type}, ID=${messageId}, role=${data.role}`);

      // Only process newly added documents
      if (change.type !== 'added') {
        console.log(`[Forwarder]   -> Skip: not 'added'`);
        continue;
      }

      // Only process user messages
      if (data.role !== 'user') {
        console.log(`[Forwarder]   -> Skip: role='${data.role}'`);
        continue;
      }

      // Skip empty messages
      if (!data.content || data.content.trim().length === 0) {
        console.log(`[Forwarder]   -> Skip: empty content`);
        continue;
      }

      // Check timestamp - skip old messages from before listener started
      let messageTimestamp = null;
      if (data.timestamp) {
        messageTimestamp = data.timestamp.toDate ? data.timestamp.toDate() : new Date(data.timestamp);
      }

      // Skip if timestamp exists and is older than listener start time
      if (messageTimestamp && messageTimestamp < listenerStartTime) {
        console.log(`[Forwarder]   -> Skip: old message (${messageTimestamp.toISOString()} < ${listenerStartTime.toISOString()})`);
        continue;
      }

      console.log(`[Forwarder]   -> PROCESS: "${data.content.substring(0, 50)}..."`);
      processMessage(data, uid);
    }
  }, (error) => {
    console.error(`[Forwarder] SNAPSHOT ERROR:`, error.message);
  });
}

/**
 * Main function
 */
async function main() {
  console.log('========================================');
  console.log('   VEXIS Message Forwarder Service');
  console.log('========================================');
  console.log('');
  console.log('This service forwards messages from');
  console.log('VEXIS-mail-CLI to VEXIS-CLI-2');
  console.log('');
  
  // Check if already logged in
  let uid = null;
  let unsubscribe = null;
  
  onAuthStateChanged(auth, async (user) => {
    if (user) {
      uid = user.uid;
      console.log(`[Forwarder] Logged in as: ${user.email}`);
      
      // Start listening for messages
      unsubscribe = startMessageListener(uid);
    } else {
      uid = null;
      if (unsubscribe) {
        unsubscribe();
        unsubscribe = null;
      }
      console.log(`[Forwarder] Not logged in. Please login first.`);
    }
  });
  
  // Simple command loop
  const commandLoop = async () => {
    const input = await question('');
    
    if (input.trim().toLowerCase() === '/exit') {
      console.log('\n[Forwarder] Stopping service...');
      if (unsubscribe) unsubscribe();
      rl.close();
      process.exit(0);
    } else if (input.trim().toLowerCase() === '/login' && !uid) {
      const email = await question('Email: ');
      const password = await question('Password: ');
      
      try {
        await signInWithEmailAndPassword(auth, email, password);
        console.log('[Forwarder] ✓ Login successful!\n');
      } catch (error) {
        console.log('[Forwarder] ✗ Login failed:', error.message, '\n');
      }
    } else if (input.trim().toLowerCase() === '/status') {
      if (uid) {
        console.log(`[Forwarder] Status: Running`);
        console.log(`[Forwarder] User: ${auth.currentUser?.email}`);
        console.log(`[Forwarder] Messages processed: ${processedMessageIds.size}`);
        console.log(`[Forwarder] Queue length: ${messageQueue.length}`);
      } else {
        console.log(`[Forwarder] Status: Not logged in`);
      }
    } else if (input.trim().toLowerCase() === '/setting') {
      console.log('\n[Forwarder] === Provider & Model Settings ===');
      console.log(`[Forwarder] Current: provider=${settings.provider}, model=${settings.model}`);
      console.log(`[Forwarder] Valid providers: ${VALID_PROVIDERS.join(', ')}`);
      console.log('');
      
      const providerInput = await question('Provider: ');
      const provider = providerInput.trim().toLowerCase();
      
      if (!VALID_PROVIDERS.includes(provider)) {
        console.log(`[Forwarder] ✗ Invalid provider. Valid options: ${VALID_PROVIDERS.join(', ')}\n`);
      } else {
        const model = await question('Model: ');
        
        if (!model.trim()) {
          console.log('[Forwarder] ✗ Model name cannot be empty\n');
        } else {
          // Prompt for API key if not Ollama (which doesn't need an API key)
          if (provider !== 'ollama') {
            const envVar = API_KEY_ENV_VARS[provider];
            console.log(`[Forwarder] Provider "${provider}" requires an API key.`);
            
            if (Array.isArray(envVar)) {
              // Special case for Amazon (needs two keys)
              console.log(`[Forwarder] Required environment variables: ${envVar.join(', ')}`);
              const existingKey1 = settings.apiKeys[envVar[0]];
              const existingKey2 = settings.apiKeys[envVar[1]];
              if (existingKey1 && existingKey2) {
                console.log(`[Forwarder] API keys already configured for ${provider}`);
                const useExisting = await question('Use existing keys? (Y/n): ');
                if (useExisting.trim().toLowerCase() === 'n') {
                  const accessKey = await question('AWS Access Key ID: ');
                  const secretKey = await question('AWS Secret Access Key: ');
                  if (accessKey.trim() && secretKey.trim()) {
                    settings.apiKeys[envVar[0]] = accessKey.trim();
                    settings.apiKeys[envVar[1]] = secretKey.trim();
                  }
                }
              } else {
                const accessKey = await question('AWS Access Key ID: ');
                const secretKey = await question('AWS Secret Access Key: ');
                if (accessKey.trim() && secretKey.trim()) {
                  settings.apiKeys[envVar[0]] = accessKey.trim();
                  settings.apiKeys[envVar[1]] = secretKey.trim();
                } else {
                  console.log('[Forwarder] ✗ Both AWS keys are required. API not saved.\n');
                }
              }
            } else {
              // Single API key for other providers
              console.log(`[Forwarder] Environment variable: ${envVar}`);
              const existingKey = settings.apiKeys[envVar];
              if (existingKey) {
                console.log(`[Forwarder] API key already configured for ${provider}`);
                const useExisting = await question('Use existing key? (Y/n): ');
                if (useExisting.trim().toLowerCase() === 'n') {
                  const apiKey = await question('API Key: ');
                  if (apiKey.trim()) {
                    settings.apiKeys[envVar] = apiKey.trim();
                  }
                }
              } else {
                const apiKey = await question('API Key: ');
                if (apiKey.trim()) {
                  settings.apiKeys[envVar] = apiKey.trim();
                }
              }
            }
          }
          
          settings.provider = provider;
          settings.model = model.trim();
          saveSettings();
          console.log(`[Forwarder] ✓ Settings updated: provider=${settings.provider}, model=${settings.model}\n`);
        }
      }
    } else if (input.trim().toLowerCase() === '/help') {
      console.log('\nCommands:');
      console.log('  /login   - Login to your account');
      console.log('  /setting - Configure provider and model');
      console.log('  /status  - Show service status');
      console.log('  /help    - Show this help message');
      console.log('  /exit    - Stop the service');
      console.log('');
    }
    
    commandLoop();
  };
  
  // Load settings on startup
  loadSettings();
  
  console.log('Type /login to authenticate or /help for commands.\n');
  commandLoop();
}

// Handle graceful shutdown
process.on('SIGINT', () => {
  console.log('\n[Forwarder] Shutting down...');
  process.exit(0);
});

process.on('SIGTERM', () => {
  console.log('\n[Forwarder] Shutting down...');
  process.exit(0);
});

main().catch(console.error);
