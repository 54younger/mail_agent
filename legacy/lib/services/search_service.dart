import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/models/email_message.dart';
import '../data/objectbox/objectbox_store.dart';
import '../providers/app_providers.dart';
import '../providers/embedding/embedding_provider.dart';

/// Semantic search: embed a natural-language query and return Top-N emails.
/// Phase 3 will implement HNSW nearest-neighbour lookup via ObjectBox.
class SearchService {
  SearchService({
    required ObjectBoxStore store,
    required EmbeddingProvider embeddingProvider,
  })  : _store = store,
        _embeddingProvider = embeddingProvider;

  final ObjectBoxStore _store;
  final EmbeddingProvider _embeddingProvider;

  /// Returns up to [AppConstants.searchTopN] most relevant [EmailMessage]s.
  Future<List<EmailMessage>> search(String query) async {
    // TODO(phase3): embed(query) → ObjectBox nearestNeighbors HNSW query.
    throw UnimplementedError('SearchService.search not yet implemented.');
  }
}

final searchServiceProvider = FutureProvider<SearchService>((ref) async {
  final store = ref.watch(objectBoxStoreProvider);
  final embeddingProvider = await ref.watch(embeddingProviderProvider.future);
  return SearchService(store: store, embeddingProvider: embeddingProvider);
});
