// Message interface for conversation history
export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

// WhatsApp message interface
export interface WhatsAppMessage {
  key: {
    remoteJid: string;
    id: string;
    fromMe: boolean;
  };
  message: {
    conversation?: string;
    extendedTextMessage?: {
      text?: string;
    };
  };
  messageTimestamp: number;
}

// Ollama API request/response interfaces
export interface OllamaRequest {
  model: string;
  messages: ChatMessage[];
  stream?: boolean;
}

export interface OllamaResponse {
  message: ChatMessage;
  done: boolean;
  total_duration?: number;
  load_duration?: number;
}
