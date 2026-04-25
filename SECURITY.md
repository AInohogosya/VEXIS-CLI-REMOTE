# Security Guide for VEXIS-CLI

This document provides security best practices for using VEXIS-CLI safely and protecting your sensitive information.

## Overview

VEXIS-CLI requires API keys and credentials to function with various AI providers and Telegram integration. This guide explains how to manage these credentials securely.

## Sensitive Information

The following types of sensitive information are used by VEXIS-CLI:

- **API Keys**: Google, OpenAI, Anthropic, xAI, Meta, Groq, DeepSeek, Together, Microsoft, Mistral, Amazon, Cohere, MiniMax, ZhipuAI, OpenRouter
- **Telegram Credentials**: API ID, API Hash, Bot Token
- **Personal Data**: Phone numbers, user IDs, contact information
- **Session Data**: Telegram session files stored locally

## Security Best Practices

### 1. Never Commit Sensitive Data

**✅ DO**: Use the provided `.gitignore` file which excludes:
- `config.yaml` (contains API keys and personal data)
- `.vexis/` (contains Telegram sessions)
- `telegram_sessions/` (contains session files)
- `*.log` (may contain sensitive information)

**❌ DON'T**: Commit `config.yaml` or any files containing API keys to version control.

### 2. Use Environment Variables

**✅ RECOMMENDED**: Store sensitive credentials in environment variables instead of config files.

```bash
# AI Provider API Keys
export GOOGLE_API_KEY="your_google_api_key"
export OPENAI_API_KEY="your_openai_api_key"
export ANTHROPIC_API_KEY="your_anthropic_api_key"
export XAI_API_KEY="your_xai_api_key"
export META_API_KEY="your_meta_api_key"
export GROQ_API_KEY="your_groq_api_key"
export DEEPSEEK_API_KEY="your_deepseek_api_key"
export TOGETHER_API_KEY="your_together_api_key"
export MINIMAX_API_KEY="your_minimax_api_key"
export ZHIPUAI_API_KEY="your_zhipuai_api_key"
export OPENROUTER_API_KEY="your_openrouter_api_key"

# Telegram Integration
export TELEGRAM_API_ID="your_telegram_api_id"
export TELEGRAM_API_HASH="your_telegram_api_hash"
export TELEGRAM_BOT_TOKEN="your_telegram_bot_token"
```

**How to set environment variables permanently**:

```bash
# Add to ~/.bashrc or ~/.zshrc
export GOOGLE_API_KEY="your_key_here"
export TELEGRAM_API_ID="your_id_here"
# ... other keys
```

Then reload your shell:
```bash
source ~/.bashrc  # or source ~/.zshrc
```

### 3. Clean Up Sensitive Information

VEXIS-CLI provides a built-in command to remove sensitive data:

```bash
python3 run.py --cleanup-secrets
```

This command will:
- Remove API keys and tokens from `config.yaml`
- Remove phone numbers and user IDs from `config.yaml`
- Delete Telegram session files from `~/.vexis/telegram_sessions/`
- Clear cache and log files

**When to run cleanup**:
- Before committing code to Git
- When sharing your code with others
- When switching to a different account or API key
- Periodically as a security best practice

### 4. Use Minimal Permissions

- Only grant necessary permissions to API keys
- Use separate API keys for development and production
- Rotate API keys regularly (especially if compromised)
- Revoke unused API keys

### 5. Secure Your Local Environment

- **File Permissions**: Ensure `config.yaml` has restricted permissions:
  ```bash
  chmod 600 config.yaml  # Read/write for owner only
  ```

- **Session Storage**: Telegram sessions are stored in `~/.vexis/telegram_sessions/` with restricted permissions by default.

- **Log Files**: Review `vexis.log` before sharing, as it may contain sensitive information.

### 6. Telegram-Specific Security

**Bot Mode**:
- Use a dedicated bot account (not your personal account)
- Restrict bot commands to authorized users only
- Use webhooks for production deployments (more secure than long polling)

**User Account Mode**:
- Enable 2FA (Two-Factor Authentication) on your Telegram account
- Be cautious about which contacts you authorize
- Review `authorized_users` list regularly

### 7. API Key Management

**Generation**:
- Generate API keys from official provider websites
- Use strong, unique keys for each application
- Document which key is used for which purpose

**Storage**:
- Never hardcode API keys in source code
- Use environment variables or secret management tools
- Consider using a `.env` file (added to `.gitignore`) for local development

**Rotation**:
- Rotate API keys every 90 days
- Rotate immediately if compromised
- Update all applications using the old key

### 8. Auditing and Monitoring

**Regular Audits**:
- Review your `config.yaml` for accidentally committed secrets
- Check Git history for sensitive data (use `git log -p` to search)
- Review environment variables regularly

**Monitoring**:
- Monitor API usage for unusual activity
- Set up alerts for unusual spending or usage patterns
- Review provider dashboards for security notifications

## Troubleshooting

### "I accidentally committed config.yaml to Git"

1. **Remove from current branch**:
   ```bash
   git rm --cached config.yaml
   git commit -m "Remove sensitive config.yaml"
   ```

2. **Remove from Git history** (advanced):
   ```bash
   git filter-branch --force --index-filter \
     "git rm --cached --ignore-unmatch config.yaml" \
     --prune-empty --tag-name-filter cat -- --all
   ```

3. **Rotate all API keys** that were in the committed file.

4. **Force push** (only if necessary and you understand the risks):
   ```bash
   git push origin --force --all
   ```

### "I can't remember which API keys I've used"

1. Check provider dashboards for active keys
2. Review `config.yaml` (if you still have it)
3. Check environment variables: `env | grep API_KEY`
4. Run `python3 run.py --cleanup-secrets` to clear local data, then regenerate keys

### "Telegram session files are not being created"

1. Check that `~/.vexis/telegram_sessions/` exists and is writable
2. Check file permissions:
   ```bash
   ls -la ~/.vexis/telegram_sessions/
   ```
3. Ensure you have proper API credentials (API ID and API Hash)

## Additional Resources

- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)
- [GitHub Security Best Practices](https://docs.github.com/en/security)
- [Telethon Security Documentation](https://docs.telethon.dev/en/stable/concepts/security.html)

## Reporting Security Issues

If you discover a security vulnerability in VEXIS-CLI, please:

1. **Do not** create a public issue
2. Email the details to: AInohogosya@proton.me
3. Include steps to reproduce the vulnerability
4. Allow time for the issue to be addressed before disclosing publicly

## Disclaimer

VEXIS-CLI is provided as-is without warranty. Users are responsible for:
- Securing their own API keys and credentials
- Complying with provider terms of service
- Following applicable laws and regulations
- Implementing appropriate security measures for their use case
