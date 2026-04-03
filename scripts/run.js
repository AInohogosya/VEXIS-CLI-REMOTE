#!/usr/bin/env node

/**
 * VEXIS CLI Runner
 * Validates execution directory and runs commands in VEXIS-mail-CLI
 */

import { fileURLToPath } from 'url';
import { dirname, basename, resolve } from 'path';
import { spawn } from 'child_process';
import { existsSync } from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const ROOT_DIR = dirname(__dirname);
const TARGET_DIR = resolve(ROOT_DIR, 'VEXIS-mail-CLI');

// Get the expected root directory name
const ROOT_NAME = basename(ROOT_DIR);

// Get current working directory
const CWD = process.cwd();

// Validate we're running from the correct directory
if (CWD !== ROOT_DIR) {
  console.error('Error: Commands must be run from the VEXIS-CLI-REMOTE directory.');
  console.error(`Current: ${CWD}`);
  console.error(`Expected: ${ROOT_DIR}`);
  process.exit(1);
}

// Check that VEXIS-mail-CLI exists
if (!existsSync(TARGET_DIR)) {
  console.error(`Error: VEXIS-mail-CLI directory not found at ${TARGET_DIR}`);
  process.exit(1);
}

// Get the command to run (passed as arguments)
const args = process.argv.slice(2);
if (args.length === 0) {
  console.error('Error: No command specified');
  process.exit(1);
}

// Run the command in VEXIS-mail-CLI directory
const [command, ...cmdArgs] = args;
const child = spawn(command, cmdArgs, {
  cwd: TARGET_DIR,
  stdio: 'inherit',
  shell: true
});

child.on('exit', (code) => {
  process.exit(code || 0);
});
