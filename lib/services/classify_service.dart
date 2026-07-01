import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/constants.dart';
import '../data/models/category.dart';
import '../data/models/email_message.dart';
import '../data/objectbox/objectbox_store.dart';
import '../providers/app_providers.dart';

/// Uses Claude Haiku to classify emails and auto-archive them.
/// Phase 4 will implement the Claude API call with structured output (tool use).
class ClassifyService {
  ClassifyService({
    required ObjectBoxStore store,
    required String claudeApiKey,
  })  : _store = store,
        _claudeApiKey = claudeApiKey;

  final ObjectBoxStore _store;
  final String _claudeApiKey;

  /// Classify [email] against [categories]; update [EmailMessage.categoryId].
  Future<Category?> classify(
    EmailMessage email,
    List<Category> categories,
  ) async {
    // TODO(phase4): Build prompt → Claude Haiku tool_use → persist categoryId
    // → move email to Category.targetFolder via IMAP.
    throw UnimplementedError('ClassifyService.classify not yet implemented.');
  }

  /// Classify all unclassified emails in batch.
  Future<void> classifyAll(List<Category> categories) async {
    // TODO(phase4): Iterate unclassified emails, call classify(), cache results.
    throw UnimplementedError('ClassifyService.classifyAll not yet implemented.');
  }
}

final classifyServiceProvider = FutureProvider<ClassifyService>((ref) async {
  final store = ref.watch(objectBoxStoreProvider);
  final secureStorage = ref.watch(secureStorageProvider);
  final apiKey =
      await secureStorage.read(key: AppConstants.secureStorageKeyClaudeApiKey) ?? '';
  return ClassifyService(store: store, claudeApiKey: apiKey);
});
