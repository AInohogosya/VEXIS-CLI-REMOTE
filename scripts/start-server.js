#!/usr/bin/env node

/**
 * VEXIS Server Starter
 * Auto-installs dependencies if needed, then starts the forwarder
 */

import { fileURLToPath } from 'url';
import { dirname, resolve } from 'path';
import { spawn } from 'child_process';
import { existsSync } from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const ROOT_DIR = dirname(__dirname);
const TARGET_DIR = resolve(ROOT_DIR, 'VEXIS-mail-CLI');
const NODE_MODULES = resolve(TARGET_DIR, 'node_modules');

// Validate we're running from the correct directory
const CWD = process.cwd();
if (CWD !== ROOT_DIR) {
  console.error('Error: Commands must be run from the VEXIS-CLI-REMOTE directory.');
  console.error(`Current: ${CWD}`);
  console.error(`Expected: ${ROOT_DIR}`);
  process.exit(1);
}

// Check if dependencies are installed
if (!existsSync(NODE_MODULES)) {
  console.log('📦 Dependencies not found. Installing...');
  console.log('');
  
  const install = spawn('npm', ['install'], {
    cwd: TARGET_DIR,
    stdio: 'inherit',
    shell: true
  });
  
  install.on('close', (code) => {
    if (code === 0) {
      console.log('');
      console.log('✓ Installation complete. Starting server...');
      console.log('');
      startForwarder();
    } else {
      console.error('✗ Installation failed');
      process.exit(1);
    }
  });
} else {
  startForwarder();
}

function startForwarder() {
  console.log('🚀 Starting VEXIS Mail Server...');
  console.log('');
  
  const forwarder = spawn('npm', ['run', 'forwarder'], {
    cwd: TARGET_DIR,
    stdio: 'inherit',
    shell: true
  });
  
  forwarder.on('exit', (code) => {
    process.exit(code || 0);
  });
}
