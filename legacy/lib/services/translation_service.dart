import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/constants.dart';
import '../providers/app_providers.dart';

/// Target languages the user can translate into. Key = ISO code, value = label.
const kTranslationTargets = <String, String>{
  'en': 'English',
  'zh': '中文',
  'ja': '日本語',
  'ko': '한국어',
  'fr': 'Français',
  'de': 'Deutsch',
  'es': 'Español',
};

const kDefaultTranslationTarget = 'en';

/// Result of a translation: the translated text plus the detected source lang.
class TranslationResult {
  const TranslationResult({required this.translated, required this.sourceLang});
  final String translated;
  final String sourceLang;
}

/// Thrown when translation is requested but the Claude backend isn't wired up
/// yet (no API key configured). The UI surfaces a friendly message.
class TranslationUnavailable implements Exception {
  const TranslationUnavailable([this.message =
      '翻译将在配置 Claude API Key 后可用（Phase 4）']);
  final String message;

  @override
  String toString() => message;
}

/// Translates email text into a target language.
///
/// Phase 4.5 skeleton: the API surface and UI wiring are complete, but the
/// actual Claude call is deferred to Phase 4 (when the Claude HTTP client and
/// API-key configuration UI are built). Until then [translate] throws
/// [TranslationUnavailable].
class TranslationService {
  TranslationService({required String claudeApiKey}) : _apiKey = claudeApiKey;

  final String _apiKey;

  bool get isConfigured => _apiKey.isNotEmpty;

  /// Translates [text] into [targetLang]. On-demand (called per email).
  Future<TranslationResult> translate(
    String text, {
    required String targetLang,
  }) async {
    // TODO(phase4): detect source language + call Claude Haiku to translate
    // into [targetLang]; skip when source already equals target.
    throw const TranslationUnavailable();
  }
}

final translationServiceProvider =
    FutureProvider<TranslationService>((ref) async {
  final secureStorage = ref.watch(secureStorageProvider);
  final apiKey = await secureStorage.read(
        key: AppConstants.secureStorageKeyClaudeApiKey,
      ) ??
      '';
  return TranslationService(claudeApiKey: apiKey);
});

/// User-selected target language (persisted). Defaults to English.
class TranslationTargetNotifier extends Notifier<String> {
  static const _storageKey = 'pref_translation_target';

  @override
  String build() {
    _load();
    return kDefaultTranslationTarget;
  }

  Future<void> _load() async {
    final saved = await ref.read(secureStorageProvider).read(key: _storageKey);
    if (saved != null && kTranslationTargets.containsKey(saved)) {
      state = saved;
    }
  }

  Future<void> set(String code) async {
    if (!kTranslationTargets.containsKey(code)) return;
    state = code;
    await ref.read(secureStorageProvider).write(key: _storageKey, value: code);
  }
}

final translationTargetProvider =
    NotifierProvider<TranslationTargetNotifier, String>(
  TranslationTargetNotifier.new,
);
