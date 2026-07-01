import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/models/model_state.dart';
import '../data/objectbox/objectbox_store.dart';
import '../providers/app_providers.dart';
import '../providers/embedding/model_catalog.dart';

/// Manages model downloads, checksum validation, and tier switching.
/// Phase 3 will implement the Dio-based download pipeline.
class ModelManager {
  ModelManager({
    required ObjectBoxStore store,
    required String appDocumentsPath,
  })  : _store = store,
        _appDocumentsPath = appDocumentsPath;

  final ObjectBoxStore _store;
  final String _appDocumentsPath;

  ModelState get currentState {
    final states = _store.modelStates.getAll();
    return states.isNotEmpty ? states.first : ModelState();
  }

  /// Download [spec] with streaming progress; verify SHA-256 checksum.
  Stream<double> downloadModel(ModelSpec spec) async* {
    // TODO(phase3): Dio streaming download → temp file → checksum verify → rename.
    throw UnimplementedError('ModelManager.downloadModel not yet implemented.');
  }

  /// Switch the active model; triggers a full index rebuild.
  Future<void> switchModel(ModelSpec spec) async {
    // TODO(phase3): Update ModelState in DB; caller triggers IndexService.rebuildIndex().
    throw UnimplementedError('ModelManager.switchModel not yet implemented.');
  }

  /// Delete a downloaded model file and update downloadedModelIds.
  Future<void> deleteModel(String modelId) async {
    // TODO(phase3): Delete file from disk, update ModelState.downloadedModelIds.
    throw UnimplementedError('ModelManager.deleteModel not yet implemented.');
  }

  /// Toggle local ONNX vs cloud API mode.
  Future<void> setUseLocalModel(bool useLocal) async {
    // TODO(phase3): Update ModelState.useLocalModel; invalidate embeddingProviderProvider.
    throw UnimplementedError('ModelManager.setUseLocalModel not yet implemented.');
  }
}

final modelManagerProvider = FutureProvider<ModelManager>((ref) async {
  final store = ref.watch(objectBoxStoreProvider);
  final platformService = ref.watch(platformServiceProvider);
  final docsPath = await platformService.getAppDocumentsPath();
  return ModelManager(store: store, appDocumentsPath: docsPath);
});
