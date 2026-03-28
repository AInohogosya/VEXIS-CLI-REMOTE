import dotenv from 'dotenv';

// Load environment variables
dotenv.config();

// Configuration validation
export const config = {
  // WhatsApp configuration
  ownPhoneNumber: process.env.OWN_PHONE_NUMBER || '',
  
  // Ollama configuration
  ollamaBaseUrl: process.env.OLLAMA_BASE_URL || '',
  ollamaModel: process.env.OLLAMA_MODEL || '',
  
  // Logging configuration
  logLevel: process.env.LOG_LEVEL || '',
  
  // System prompt for the AI
  systemPrompt: 'You are a helpful, friendly AI assistant.',
  
  // API timeout in milliseconds
  apiTimeout: 30000,
};

// Validate required configuration
if (!config.ownPhoneNumber) {
  throw new Error('OWN_PHONE_NUMBER is required in .env file');
}
