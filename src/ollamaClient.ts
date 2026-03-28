import axios, { AxiosError } from 'axios';
import { config } from './config';
import { ChatMessage, OllamaRequest, OllamaResponse } from './types';

// Send message to Ollama API
export async function sendMessageToOllama(message: string): Promise<string> {
  try {
    // Prepare request for Ollama
    const request: OllamaRequest = {
      model: config.ollamaModel,
      messages: [
        { role: 'system', content: config.systemPrompt },
        { role: 'user', content: message }
      ],
      stream: false,
    };
    
    // Make API call to Ollama
    const response = await axios.post<OllamaResponse>(
      `${config.ollamaBaseUrl}/api/chat`,
      request,
      {
        timeout: config.apiTimeout,
        headers: {
          'Content-Type': 'application/json',
        },
      }
    );
    
    return response.data.message.content;
  } catch (error) {
    if (error instanceof AxiosError) {
      if (error.code === 'ECONNREFUSED') {
        throw new Error('Ollama is not running.');
      } else {
        throw new Error('Failed to connect to Ollama');
      }
    } else {
      throw new Error('An unexpected error occurred');
    }
  }
}

// Check if Ollama is available
export async function checkOllamaStatus(): Promise<boolean> {
  try {
    await axios.get(`${config.ollamaBaseUrl}/api/tags`, { timeout: 5000 });
    return true;
  } catch (error) {
    return false;
  }
}

// No history management - stateless
export function clearHistory(): void {
  // No-op: no history stored
}
