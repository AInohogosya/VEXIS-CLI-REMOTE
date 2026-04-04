# VEXIS-CLI

A CLI-based chat application for VEXIS Agent.

> **Note:** While this project is very useful for sending emails, we recommend [AInohogosya/VEXIS-CLI-2](https://github.com/AInohogosya/VEXIS-CLI-2) for beginners, as it is easier to use.

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

```bash
npm run server
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

## Web Interface

You can also send messages to this VEXIS-CLI-REMOTE from the web interface at: https://ainohogosya.github.io/VEXIS-Web/

## Configuration

This application uses Firebase for authentication and data storage. The Firebase configuration is hardcoded for immediate use. To use your own Firebase project, edit the `firebaseConfig` object in `index.js` and `forwarder.js`.