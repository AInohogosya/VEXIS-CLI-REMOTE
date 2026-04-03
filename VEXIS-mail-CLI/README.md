# VEXIS-CLI

A CLI-based chat application for VEXIS Agent.

## Installation

```bash
npm install
```

## Usage

```bash
npm start
```

Or run directly:

```bash
node index.js
```

## Commands

- `/login` - Login to your account (requires valid email/password)
- `/register` - Create a new account
- `/logout` - Logout from current session
- `/clear` - Clear the screen
- `/help` - Show help message
- `/exit` - Exit the application

## Features

- User authentication (login/register)
- Real-time chat messaging
- Message history sync via Firebase Firestore

## Configuration

This application uses Firebase for authentication and data storage. The Firebase configuration is hardcoded for immediate use. To use your own Firebase project, edit the `firebaseConfig` object in `index.js` and `forwarder.js`.