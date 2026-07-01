import 'dart:io';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/platform/platform_service.dart';
import '../core/platform/platform_service_ios.dart';
import '../core/platform/platform_service_windows.dart';
import '../core/secure_storage/secure_storage.dart';
import '../core/secure_storage/secure_storage_impl.dart';
import '../data/objectbox/objectbox_store.dart';
import 'embedding/cloud_api_provider.dart';
import 'embedding/embedding_provider.dart';
import 'embedding/local_onnx_provider.dart';
import 'embedding/model_catalog.dart';

// ── Platform ──────────────────────────────────────────────────────────────────

final platformServiceProvider = Provider<PlatformService>((ref) {
  if (Platform.isWindows) return WindowsPlatformService();
  if (Platform.isIOS) return IosPlatformService();
  throw UnsupportedError('Unsupported platform: ${Platform.operatingSystem}');
});

// ── Secure storage ────────────────────────────────────────────────────────────

final secureStorageProvider = Provider<SecureStorage>((ref) {
  return SecureStorageImpl();
});

// ── Embedding provider ────────────────────────────────────────────────────────

/// Reads ModelState from DB to decide local vs cloud and which model tier.
/// Phase 3 will make this reactive (watch ModelState stream for hot-swapping).
final embeddingProviderProvider = FutureProvider<EmbeddingProvider>((ref) async {
  final store = ref.watch(objectBoxStoreProvider);
  final secureStorage = ref.watch(secureStorageProvider);
  final platformService = ref.watch(platformServiceProvider);

  final modelStates = store.modelStates.getAll();
  final modelState = modelStates.isNotEmpty ? modelStates.first : null;

  final useLocal = modelState?.useLocalModel ?? true;

  if (useLocal) {
    final freeMemory = await platformService.getAvailableMemoryMb();
    final availableModels = ModelCatalog.available();

    ModelSpec spec;
    if (modelState != null && modelState.currentModelId.isNotEmpty) {
      spec = ModelCatalog.byId(modelState.currentModelId) ??
          ModelCatalog.recommend(freeMemory);
    } else {
      spec = ModelCatalog.recommend(freeMemory);
    }

    if (!availableModels.any((m) => m.id == spec.id)) {
      spec = availableModels.first;
    }

    return LocalOnnxProvider(spec);
  } else {
    final apiKey = await secureStorage.read(key: 'claude_api_key') ?? '';
    return CloudApiProvider(apiKey: apiKey, model: 'cloud-embedding-v1');
  }
});
