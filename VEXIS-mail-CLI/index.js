#!/usr/bin/env node

import { initializeApp } from 'firebase/app';
import { 
  getAuth, 
  createUserWithEmailAndPassword, 
  signInWithEmailAndPassword,
  signOut,
  onAuthStateChanged
} from 'firebase/auth';
import { 
  getFirestore, 
  collection, 
  addDoc, 
  query, 
  orderBy, 
  onSnapshot, 
  serverTimestamp 
} from 'firebase/firestore';
import * as readline from 'readline';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';
import { config } from 'dotenv';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Load environment variables from .env file
config({ path: join(__dirname, '.env') });

// Firebase config from environment variables
const firebaseConfig = {
  apiKey: process.env.FIREBASE_API_KEY,
  authDomain: process.env.FIREBASE_AUTH_DOMAIN,
  projectId: process.env.FIREBASE_PROJECT_ID,
  storageBucket: process.env.FIREBASE_STORAGE_BUCKET,
  messagingSenderId: process.env.FIREBASE_MESSAGING_SENDER_ID,
  appId: process.env.FIREBASE_APP_ID
};

// Validate Firebase config
if (!firebaseConfig.apiKey || !firebaseConfig.authDomain || !firebaseConfig.projectId) {
  console.error('Error: Firebase configuration is missing. Please create a .env file based on .env.example');
  process.exit(1);
}

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const db = getFirestore(app);

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

let currentUid = null;
let unsubscribe = null;
let isChatMode = false;

function question(prompt) {
  return new Promise((resolve) => {
    rl.question(prompt, resolve);
  });
}

function printHeader() {
  console.clear();
  console.log('========================================');
  console.log('          VEXIS Chat CLI');
  console.log('========================================');
  console.log('');
}

function printHelp() {
  console.log('\nCommands:');
  console.log('  /login    - Login to your account');
  console.log('  /register - Create a new account');
  console.log('  /logout   - Logout from current session');
  console.log('  /clear    - Clear the screen');
  console.log('  /help     - Show this help message');
  console.log('  /exit     - Exit the application');
  console.log('');
}

async function handleLogin() {
  const email = await question('Email: ');
  const password = await question('Password: ');
  
  try {
    await signInWithEmailAndPassword(auth, email, password);
    console.log('\n✓ Login successful!\n');
  } catch (error) {
    console.log('\n✗ Login failed:', error.message, '\n');
  }
}

async function handleRegister() {
  const email = await question('Email: ');
  const password = await question('Password: ');
  
  try {
    await createUserWithEmailAndPassword(auth, email, password);
    console.log('\n✓ Registration successful!\n');
  } catch (error) {
    console.log('\n✗ Registration failed:', error.message, '\n');
  }
}

async function handleLogout() {
  try {
    if (unsubscribe) {
      unsubscribe();
      unsubscribe = null;
    }
    await signOut(auth);
    isChatMode = false;
    console.log('\n✓ Logged out successfully.\n');
  } catch (error) {
    console.log('\n✗ Logout failed:', error.message, '\n');
  }
}

async function sendMessage(text) {
  if (!text.trim() || !currentUid) return;
  
  try {
    await addDoc(collection(db, `conversations/${currentUid}/messages`), {
      role: "assistant",
      content: text.trim(),
      timestamp: serverTimestamp(),
      read: false
    });
  } catch (error) {
    console.log('Error sending message:', error.message);
  }
}

function startChatListener() {
  const q = query(
    collection(db, `conversations/${currentUid}/messages`),
    orderBy("timestamp", "asc")
  );
  
  let lastMessageCount = 0;
  
  unsubscribe = onSnapshot(q, (snapshot) => {
    if (snapshot.docs.length > lastMessageCount) {
      process.stdout.write('\x1b[2K\x1b[0G');
      
      snapshot.forEach((docSnap) => {
        const data = docSnap.data();
        const prefix = data.role === 'user' ? '[You]: ' : '[Agent]: ';
        console.log(prefix + data.content);
      });
      
      lastMessageCount = snapshot.docs.length;
      process.stdout.write('> ');
    }
  });
}

function startChatMode() {
  isChatMode = true;
  console.log('\n--- Chat Mode ---');
  console.log('Type your message and press Enter to send.');
  console.log('Type /back to return to main menu.\n');
  
  startChatListener();
  process.stdout.write('> ');
}

async function handleCommand(input) {
  const cmd = input.trim().toLowerCase();
  
  switch (cmd) {
    case '/login':
      if (currentUid) {
        console.log('Already logged in. Use /logout first.');
      } else {
        await handleLogin();
      }
      break;
      
    case '/register':
      if (currentUid) {
        console.log('Already logged in. Use /logout first.');
      } else {
        await handleRegister();
      }
      break;
      
    case '/logout':
      await handleLogout();
      break;
      
    case '/clear':
      printHeader();
      break;
      
    case '/help':
      printHelp();
      break;
      
    case '/exit':
    case '/quit':
      console.log('\nGoodbye!');
      if (unsubscribe) unsubscribe();
      rl.close();
      process.exit(0);
      
    default:
      if (currentUid && !cmd.startsWith('/')) {
        await sendMessage(input);
      } else if (cmd === '/back' && isChatMode) {
        isChatMode = false;
        if (unsubscribe) {
          unsubscribe();
          unsubscribe = null;
        }
        console.log('\nReturned to main menu.\n');
      } else {
        console.log('Unknown command. Type /help for available commands.');
      }
  }
}

function promptLoop() {
  rl.question('', async (input) => {
    if (isChatMode && !input.trim().startsWith('/')) {
      await sendMessage(input);
      process.stdout.write('> ');
    } else {
      await handleCommand(input);
    }
    promptLoop();
  });
}

onAuthStateChanged(auth, (user) => {
  if (user) {
    currentUid = user.uid;
    console.log('Logged in as:', user.email);
    console.log('Type /chat to start chatting or /help for commands.\n');
  } else {
    currentUid = null;
    isChatMode = false;
    if (unsubscribe) {
      unsubscribe();
      unsubscribe = null;
    }
  }
});

printHeader();
printHelp();
console.log('Type /login or /register to get started.\n');
promptLoop();
