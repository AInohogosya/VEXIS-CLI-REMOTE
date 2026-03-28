// Main entry point for WhatsApp Command Bot
import { startWhatsAppClient } from './whatsappClientAlt';

// Handle graceful shutdown
process.on('SIGINT', () => {
  process.exit(0);
});

process.on('SIGTERM', () => {
  process.exit(0);
});

// Handle unhandled promise rejections
process.on('unhandledRejection', (error) => {
  console.error('Unhandled rejection:', error);
  process.exit(1);
});

// Handle uncaught exceptions
process.on('uncaughtException', (error) => {
  console.error('Uncaught exception:', error);
  process.exit(1);
});

// Main application startup
async function main(): Promise<void> {
  try {
    // Start WhatsApp client directly
    await startWhatsAppClient();
  } catch (error) {
    console.error('Failed to start:', error);
    process.exit(1);
  }
}

// Start the application
main();
