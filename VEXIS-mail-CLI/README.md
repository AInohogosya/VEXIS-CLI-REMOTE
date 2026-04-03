# VEXIS-CLI

A CLI-based chat application for VEXIS Agent.

## Installation

```bash
npm install
```

## Configuration

This application requires Firebase configuration. Before running, you must set up your environment variables:

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and fill in your Firebase credentials from your Firebase project settings:
   - `FIREBASE_API_KEY` - Your Firebase API key
   - `FIREBASE_AUTH_DOMAIN` - Your Firebase auth domain
   - `FIREBASE_PROJECT_ID` - Your Firebase project ID
   - `FIREBASE_STORAGE_BUCKET` - Your Firebase storage bucket
   - `FIREBASE_MESSAGING_SENDER_ID` - Your Firebase messaging sender ID
   - `FIREBASE_APP_ID` - Your Firebase app ID

**Security Note:** Never commit your `.env` file to version control. It is already excluded in `.gitignore`.

## Usage

```bash
npm start
```

Or run directly:

```bash
node index.js
```

## Commands

- `/login` - Login to your account
- `/register` - Create a new account
- `/logout` - Logout from current session
- `/clear` - Clear the screen
- `/help` - Show help message
- `/exit` - Exit the application

## Features

- User authentication (login/register)
- Real-time chat messaging
- Message history sync via Firebase Firestore