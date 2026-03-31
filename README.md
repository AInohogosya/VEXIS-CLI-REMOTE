# VEXIS-CLI-Remote Beta-2

[![TypeScript](https://img.shields.io/badge/TypeScript-007ACC?style=for-the-badge&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![WhatsApp](https://img.shields.io/badge/WhatsApp-25D366?style=for-the-badge&logo=whatsapp&logoColor=white)](https://whatsapp.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)
[![Node.js](https://img.shields.io/badge/Node.js-339933?style=for-the-badge&logo=nodedotjs&logoColor=white)](https://nodejs.org/)

> **WhatsApp Bridge for VEXIS-CLI.** Chat with your local VEXIS AI agent from anywhere — just send a WhatsApp message.

<p align="center">
  <img src="V%20(1).png" alt="VEXIS-CLI-Remote Thumbnail" width="600">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/🔗-Connect-brightgreen?style=for-the-badge" alt="Connect">
  <img src="https://img.shields.io/badge/⚡-Execute-blue?style=for-the-badge" alt="Execute">
  <img src="https://img.shields.io/badge/🤖-Automate-purple?style=for-the-badge" alt="Automate">
</p>

---

## ✨ Features

- **🤖 VEXIS-CLI Integration** — Run the VEXIS AI agent directly from WhatsApp
- **📱 WhatsApp Bridge** — Seamless connection using `whatsapp-web.js`
- **⚡ Remote AI Access** — Chat with your local AI agent from anywhere
- **⚙️ JSON Configurable** — Customize commands and behaviors in `command.json`
- **📝 Message Logging** — Track conversations and agent responses
- **🔒 Secure by Design** — Only responds to your configured phone number
- **🔄 Auto-Reconnect** — Handles disconnections gracefully
- **📊 Terminal QR Code** — Easy one-time setup with QR scanning

---

## 🚀 Quick Start

### Prerequisites

- [WhatsApp](https://whatsapp.com) on your phone
- [Git](https://git-scm.com/)
- **[vexis-cli](https://pypi.org/project/vexis-cli/)** — The VEXIS AI agent this bridge connects to

```bash
pip install vexis-cli
```

### Installation

```bash
# Clone the repository
git clone https://github.com/AInohogosya/VEXIS-CLI-Remote.git
cd VEXIS-CLI-Remote

# Install dependencies
npm install

# Copy environment template
cp .env.example .env

# Edit .env with your settings
# Replace +1234567890 with your actual phone number
sed -i 's/OWN_PHONE_NUMBER=/OWN_PHONE_NUMBER=+1234567890/' .env
```

### Configuration

Edit `.env`:

```env
# WhatsApp configuration (required)
OWN_PHONE_NUMBER=+1234567890

# Logging configuration (optional)
LOG_LEVEL=info
```

### Run

```bash
# Development mode with hot reload
npm run dev

# Production build
npm run build
npm start
```

**Scan the QR code** in your terminal with:  
WhatsApp → Settings → Linked Devices → Link a Device

---

## 📋 Command Actions

| Action | Description | Use Case |
|--------|-------------|----------|
| `exec` | Execute shell commands | Server management, deployments |
| `log` | Log message content | Audit trails, monitoring |

### Command Schema

```typescript
{
  "name": string,        // Unique identifier
  "action": "exec" | "log",
  "command": string,     // Shell command (for exec only)
  "description": string  // Human-readable description
}
```

---

## 🏗️ How It Works

```
┌─────────────┐      ┌─────────────────┐      ┌─────────────────┐
│   Phone     │──────│  WhatsApp Web   │──────│  This Bridge    │
│  (You)      │      │   (QR Linked)   │      │  (WhatsApp →    │
└─────────────┘      └─────────────────┘      │    VEXIS-CLI)   │
                                              └────────┬────────┘
                                                       │
                                                       ▼
                                              ┌─────────────────┐
                                              │   VEXIS-CLI     │
                                              │  (AI Agent)     │
                                              │  pip install    │
                                              │  vexis-cli      │
                                              └─────────────────┘
```

**Flow:** Your WhatsApp message → Bridge → VEXIS-CLI AI Agent → Response back to WhatsApp

---

## 🎯 Use Cases

### � Chat with VEXIS AI from Anywhere
Send any message from WhatsApp and get intelligent responses from your local VEXIS-CLI agent.

```
You (WhatsApp): "What's the weather forecast?"
VEXIS-CLI (Response): "I don't have real-time weather data, but you can check..."
```

### 🔧 System Management via AI
Ask VEXIS to run system commands through natural language.

```
You: "Check how much disk space is left"
VEXIS: [Executes df -h and returns formatted results]
```

### � Remote Task Execution
Have VEXIS perform tasks on your machine while you're away.

```
You: "Create a summary of today's logs"
VEXIS: [Processes log files and returns summary]
```

### 🤖 AI-Powered Automation
Combine VEXIS intelligence with command execution for smart automations.

```
You: "Deploy the website if tests pass"
VEXIS: [Runs tests, analyzes results, deploys if successful]
```

---

## 🛠️ Configuration

### Default VEXIS-CLI Command

By default, `command.json` is configured to run VEXIS-CLI:

```json
[
  {
    "name": "run_vexis",
    "action": "exec",
    "command": "vexis-cli --no-prompt \"message received from user\"",
    "description": "Process message through VEXIS-CLI AI agent"
  }
]
```

**Customize it:** Edit `command.json` to adjust how VEXIS processes your messages.

### Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OWN_PHONE_NUMBER` | Yes | - | Your WhatsApp number with country code |
| `LOG_LEVEL` | No | `info` | Logging verbosity |

---

## 📁 Project Structure

```
VEXIS-CLI-Remote/
├── src/
│   ├── index.ts                 # Application entry point
│   ├── whatsappClientAlt.ts     # WhatsApp → VEXIS-CLI bridge logic
│   ├── commandExecutor.ts       # Command execution engine
│   └── config.ts                # Environment configuration
├── command.json                 # VEXIS-CLI command configuration
├── .env                         # Environment variables
├── .env.example                 # Environment template
├── package.json                 # Dependencies & scripts
└── tsconfig.json                # TypeScript configuration
```

---

## 🔧 Troubleshooting

### QR Code Not Showing
- Ensure your terminal supports Unicode
- Try resizing your terminal window
- Check that `qrcode-terminal` is installed

### Authentication Issues
- Delete `.wwebjs_auth` folder to re-authenticate
- Ensure your phone has stable internet
- Check that WhatsApp Web works in your browser

### Commands Not Executing
- Verify `command.json` syntax is valid JSON
- Check file permissions for executed scripts
- Review logs with `LOG_LEVEL=debug`

---

## 🤝 Contributing

Contributions are what make the open source community amazing! Any contributions you make are **greatly appreciated**.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

Please make sure to update tests as appropriate and follow the [Code of Conduct](CODE_OF_CONDUCT.md).

---

## 📝 Roadmap

- [x] VEXIS-CLI integration via WhatsApp
- [x] Command execution via JSON
- [ ] Docker containerization
- [ ] Web dashboard for command management
- [ ] Multi-user support with permission levels
- [ ] Scheduled/recurring commands
- [ ] Message templates and variables
- [ ] Webhook notifications

---

## 📜 License

Distributed under the MIT License. See `LICENSE` for more information.

---

## 🙏 Acknowledgments

- [whatsapp-web.js](https://github.com/pedroslopez/whatsapp-web.js) — WhatsApp Web API
- [Baileys](https://github.com/WhiskeySockets/Baileys) — Alternative WhatsApp library
- [Puppeteer](https://pptr.dev/) — Browser automation

---

<div align="center">

### Star ⭐ this repo if you find it helpful!

[![Star History Chart](https://api.star-history.com/svg?repos=AInohogosya/VEXIS-CLI-Remote&type=Date)](https://star-history.com/#AInohogosya/VEXIS-CLI-Remote&Date)

**[⬆ Back to Top](#-vexis-cli-remote)**

Made with ❤️ and ☕ by [AInohogosya](https://github.com/AInohogosya)

</div>
