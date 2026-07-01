import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/objectbox/objectbox_store.dart';
import '../providers/app_providers.dart';
import '../providers/embedding/embedding_provider.dart';

/// Manages the background Isolate that builds and maintains the HNSW index.
/// Phase 3 will implement the full pipeline:
///   priority queue → batch embed → persist vector + mark isIndexed.
class IndexService {
  IndexService({
    required ObjectBoxStore store,
    required EmbeddingProvider embeddingProvider,
  })  : _store = store,
        _embeddingProvider = embeddingProvider;

  final ObjectBoxStore _store;
  final EmbeddingProvider _embeddingProvider;

  /// Start or resume background indexing.
  Future<void> start() async {
    // TODO(phase3): Spawn Isolate, process unindexed emails in priority order.
    throw UnimplementedError('IndexService.start not yet implemented.');
  }

  /// Pause the background Isolate (e.g. when app loses focus).
  Future<void> pause() async {
    // TODO(phase3): Signal Isolate to pause.
    throw UnimplementedError('IndexService.pause not yet implemented.');
  }

  /// Drop all vectors and restart indexing with the current model.
  /// Called after the user switches model tiers.
  Future<void> rebuildIndex() async {
    // TODO(phase3): Clear embedding + isIndexed, reset IndexProgress, restart.
    throw UnimplementedError('IndexService.rebuildIndex not yet implemented.');
  }
}

final indexServiceProvider = FutureProvider<IndexService>((ref) async {
  final store = ref.watch(objectBoxStoreProvider);
  final embeddingProvider = await ref.watch(embeddingProviderProvider.future);
  return IndexService(store: store, embeddingProvider: embeddingProvider);
});
