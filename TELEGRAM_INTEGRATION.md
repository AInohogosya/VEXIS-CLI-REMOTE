# Telegram Integration for VEXIS-CLI

This document describes the Telegram integration feature that allows you to control VEXIS-CLI remotely from your smartphone via Telegram.

## Overview

The Telegram integration enables:
1. **Account Creation**: Create or connect a Telegram account via CLI
2. **Contact Synchronization**: Sync contacts from config.yaml to Telegram
3. **Phase 5 Output**: Send AI agent outputs to your contacts via Telegram
4. **Phase 1 Input**: Receive Telegram messages as prompts from authorized users

## Setup Instructions

### 1. Install Dependencies

The Telegram integration requires the `telethon` library. It's already included in `requirements.txt`, but if you need to install it manually:

```bash
pip install telethon>=1.34.0
```

### 2. Configure Telegram in config.yaml

Copy `config.example.yaml` to `config.yaml` and enable Telegram:

```yaml
telegram:
  enabled: true
  api_id: 2040  # Default to official Telegram app
  api_hash: "YOUR_API_HASH_HERE"
  session_name: "vexis_telegram"
  contacts:  # List of contacts (defined in config.yaml)
    - name: "VEXIS Bot"
      telegram: "@VEXIS_cli_bot"
    - name: "YOUR_NAME"
      phone: "YOUR_PHONE_NUMBER"
  authorized_users: []  # List of authorized usernames for Phase 1 input
  output_recipients: []  # List of contact names for Phase 5 output
  enable_input_listener: false
```

**Note**: You can use the default API credentials (from Telegram's official app) or get your own from https://my.telegram.org

### 3. Setup Telegram Account

Run the Telegram setup command:

```bash
python3 run.py --telegram-setup
```

You'll be prompted to:
1. Enter your phone number (with country code, e.g., +1234567890123)
2. Enter the verification code sent to your phone
3. Enter your 2FA password if enabled

Your session will be saved securely in `~/.vexis/telegram_sessions/`

### 4. Configure Contacts

Contacts are now configured directly in `config.yaml` under the `telegram` section:

```yaml
telegram:
  contacts:
    - name: "Alice"
      telegram: "@alice_username"
    - name: "Bob"
      phone: "+1234567890"
    - name: "Charlie"
      user_id: 123456789
```

**Contact formats:**
- `telegram`: Telegram username (with or without @)
- `phone`: Phone number with country code
- `user_id`: Telegram user ID (numeric string)

### 5. Sync Contacts

Run the contact synchronization command:

```bash
python3 run.py --telegram-sync
```

This will:
- Load contacts from your config file
- Verify they exist in your Telegram contacts
- Report which contacts are valid/invalid

### 6. Configure Output Recipients (Phase 5)

Edit your `config.yaml` to specify which contacts should receive AI agent outputs:

```yaml
telegram:
  output_recipients: ["Alice", "Bob"]  # Contact names from contacts list
```

Now when you run VEXIS-CLI normally, Phase 5 outputs will be sent to these contacts via Telegram.

### 7. Configure Input Listener (Phase 1)

To enable receiving commands via Telegram:

```yaml
telegram:
  authorized_users: ["@your_username", "YOUR_PHONE_NUMBER"]  # Users allowed to send commands
  enable_input_listener: true
```

Then start the Telegram listener:

```bash
python3 run.py --telegram-listen
```

The listener will:
- Wait for messages from authorized users
- Process each message as a prompt through the 5-phase pipeline
- Send results back to configured output recipients (if set)

Press `Ctrl+C` to stop the listener.

## Usage Examples

### Normal CLI Usage with Telegram Output

```bash
python3 run.py "List all files in the current directory"
```

If Telegram is enabled and output recipients are configured, the Phase 5 summary will be sent to your contacts.

### Remote Control via Telegram

1. Start the listener:
   ```bash
   python3 run.py --telegram-listen
   ```

2. Send a message from your Telegram app (from an authorized user):
   ```
   Take a screenshot
   ```

3. The AI agent will process the command and send the result back via Telegram.

## Configuration Reference

### Telegram Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | boolean | `false` | Enable/disable Telegram integration |
| `api_id` | integer | `2040` | Telegram API ID |
| `api_hash` | string | `"YOUR_API_HASH_HERE"` | Telegram API hash |
| `session_name` | string | `"vexis_telegram"` | Session file name |
| `contacts` | list | `[]` | List of contacts (defined in config.yaml) |
| `authorized_users` | list | `[]` | Authorized users for Phase 1 input |
| `output_recipients` | list | `[]` | Contact names for Phase 5 output |
| `enable_input_listener` | boolean | `false` | Enable Phase 1 input listener |

### Contact Configuration

Each contact in the `contacts` list can have:

- `name`: Display name (required)
- `telegram`: Telegram username (optional)
- `phone`: Phone number (optional)
- `user_id`: Telegram user ID (optional)

At least one identifier (`telegram`, `phone`, or `user_id`) is required.

## CLI Commands

### `--telegram-setup`
Setup or create a Telegram account via CLI.

```bash
python3 run.py --telegram-setup
```

### `--telegram-sync`
Synchronize contacts from config to Telegram.

```bash
python3 run.py --telegram-sync
```

### `--telegram-listen`
Start Telegram message listener for Phase 1 input.

```bash
python3 run.py --telegram-listen
```

## Security Considerations

1. **Session Storage**: Telegram sessions are stored in `~/.vexis/telegram_sessions/` with restricted permissions.

2. **Authorized Users**: Only users listed in `authorized_users` can send commands via Telegram. Leave this empty to disable remote input.

3. **API Credentials**: The default API credentials are from Telegram's official app. For production use, get your own from https://my.telegram.org

4. **2FA**: If your Telegram account has 2FA enabled, you'll need to enter your password during setup.

## Troubleshooting

### "No existing session found"
Run `--telegram-setup` to create a new account or connect an existing one.

### "Contact not found in Telegram"
Ensure the contact is in your Telegram contacts list. Check the identifier format:
- Usernames should be valid Telegram usernames
- Phone numbers should include country code
- User IDs should be numeric strings

### "Telegram integration is not enabled in config"
Set `telegram.enabled: true` in your `config.yaml` file.

### Listener not receiving messages
- Verify the sender is in `authorized_users`
- Check that your Telegram account is connected
- Ensure the listener is running without errors

## Architecture

The Telegram integration consists of three main components:

1. **TelegramClientManager** (`telegram_client.py`): Handles Telegram account creation, authentication, and client management.

2. **ContactManager** (`contact_manager.py`): Synchronizes contacts between config files and Telegram.

3. **MessageHandler** (`message_handler.py`): Handles incoming Telegram messages and integrates with Phase 1 input.

Integration points:
- **Phase 5 Output**: Modified `five_phase_engine.py` to send summaries via Telegram when enabled.
- **Phase 1 Input**: `--telegram-listen` command creates a message listener that feeds prompts into the 5-phase pipeline.

## Advanced Usage

### Custom API Credentials

To use your own Telegram API credentials:

1. Go to https://my.telegram.org
2. Sign in with your phone number
3. Go to "API development tools"
4. Create a new application
5. Copy the `api_id` and `api_hash`
6. Update your `config.yaml`:

```yaml
telegram:
  api_id: YOUR_API_ID
  api_hash: "YOUR_API_HASH"
```

### Multiple Sessions

You can use different session names for different accounts:

```yaml
telegram:
  session_name: "my_custom_session"
```

This is useful if you want to switch between different Telegram accounts.

## Limitations

1. **Async/Sync Bridge**: The integration uses asyncio for Telegram operations, which may have compatibility issues with some synchronous code.

2. **Message Length**: Telegram has a 4096 character limit per message. Long outputs may need to be split.

3. **Rate Limits**: Telegram has rate limits on message sending. The integration handles basic rate limiting but may be throttled for high-volume usage.

## Future Enhancements

Potential improvements for future versions:
- Support for file attachments in messages
- Group chat support
- Message encryption
- Webhook mode for better scalability
- Message history and logging
- Interactive buttons and menus

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the logs in `vexis.log`
3. Enable debug mode with `--debug` flag
4. Check Telethon documentation: https://docs.telethon.dev
