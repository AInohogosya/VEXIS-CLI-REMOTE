# VEXIS-CLI-REMOTE

AI-powered command-line ecosystem for terminal automation and real-time chat communication.

---

## 📦 Repository Structure

| Component | Language | Description |
|-----------|----------|-------------|
| [VEXIS-CLI-2](./VEXIS-CLI-2) | Python 3.8+ | Advanced 5-phase AI-powered terminal automation |
| [VEXIS-mail-CLI](./VEXIS-mail-CLI) | Node.js | Real-time chat CLI with Firebase integration |

---

## 🤖 VEXIS-CLI-2

**AI command-line agent** that transforms natural language into precise terminal commands using a sophisticated 5-phase pipeline architecture.

### Key Features

- **5-Phase Pipeline**: Command Suggestion → Extraction → Execution → Log Evaluation → Summary Generation
- **16+ AI Providers**: Groq, Google, OpenAI, Anthropic, xAI, Meta, Mistral, Azure, AWS, Cohere, DeepSeek, Together, MiniMax, Zhipu, Ollama (local)
- **Multi-iteration error recovery** with self-correction
- **Vision API support** for image-based tasks
- **Cross-platform**: macOS, Linux, Windows

### Quick Start

```bash
cd VEXIS-CLI-2
python3 run.py "list files in current directory"
```

See [VEXIS-CLI-2 README](./VEXIS-CLI-2/README.md) for detailed documentation.

---

## 💬 VEXIS-mail-CLI

**Real-time chat CLI application** powered by Firebase for instant messaging.

### Key Features

- Real-time messaging via Firebase
- Forwarder component for message relay
- Simple command-line interface

### Quick Start

```bash
cd VEXIS-mail-CLI
npm install
npm start
```

See [VEXIS-mail-CLI README](./VEXIS-mail-CLI/README.md) for details.

---

## 🚀 Installation

### Prerequisites

- **Python 3.8+** (for VEXIS-CLI-2)
- **Node.js** (for VEXIS-mail-CLI)
- **Git**

### Clone Repository

```bash
git clone https://github.com/AInohogosya/VEXIS-CLI-REMOTE.git
cd VEXIS-CLI-REMOTE
```

---

## 📋 Requirements

### VEXIS-CLI-2
- Python 3.8 or higher
- 4GB+ RAM (8GB+ recommended for local models)
- API keys for cloud providers (optional)
- Ollama for local AI (optional)

### VEXIS-mail-CLI
- Node.js
- Firebase configuration

---

## 📄 License

[MIT License](./VEXIS-CLI-2/LICENSE)

Copyright (C) 2026 VEXIS Project Contributors

---

## 🤝 Contributing

Contributions are welcome! Please refer to individual component READMEs for contribution guidelines.

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/AInohogosya/VEXIS-CLI-REMOTE/issues)
- **Email**: AInohogosya@proton.me

---

Built with ❤️ by the VEXIS Project
