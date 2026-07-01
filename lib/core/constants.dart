class AppConstants {
  AppConstants._();

  static const String appName = 'Mail Agent';
  static const String objectBoxDirName = 'mail_agent_db';

  static const int embeddingBatchSize = 32;
  static const int searchTopN = 20;

  static const String claudeApiBaseUrl = 'https://api.anthropic.com/v1';
  static const String claudeModelHaiku = 'claude-haiku-4-5-20251001';

  static const String secureStorageKeyImapPassword = 'imap_password_';
  static const String secureStorageKeyClaudeApiKey = 'claude_api_key';
}
