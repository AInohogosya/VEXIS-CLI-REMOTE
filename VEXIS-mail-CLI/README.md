# VEXIS-CLI

A CLI-based chat application for VEXIS Agent.

## Installation

From the `VEXIS-CLI-REMOTE` root directory:

```bash
npm run setup-mail
```

Or directly in the subdirectory:

```bash
cd VEXIS-mail-CLI && npm install
```

## Quick Start

From the `VEXIS-CLI-REMOTE` root directory:

**Start the server** (to receive messages):
```bash
npm run server
```

Then type `/login` to authenticate.

**Optional - Start the CLI** (to send messages, in another terminal):
```bash
npm start
```

## Commands

- `/login` - Login to your account (requires valid email/password)
- `/register` - Create a new account
- `/logout` - Logout from current session
- `/chat` - Start chat mode (requires login)
- `/setting` - Configure model settings (Ollama only)
- `/clear` - Clear the screen
- `/help` - Show help message
- `/exit` - Exit the application

## Features

- User authentication (login/register)
- Real-time chat messaging
- Message history sync via Firebase Firestore

## Configuration

This application uses Firebase for authentication and data storage. The Firebase configuration is hardcoded for immediate use. To use your own Firebase project, edit the `firebaseConfig` object in `index.js` and `forwarder.js`.