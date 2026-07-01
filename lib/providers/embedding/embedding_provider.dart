/// Abstract interface for all embedding backends.
/// Swap between [LocalOnnxProvider] and [CloudApiProvider] without
/// changing any upstream code.
abstract class EmbeddingProvider {
  /// Embed a single text string.
  Future<List<double>> embed(String text);

  /// Embed multiple texts in one batch call (more efficient for local models).
  Future<List<List<double>>> embedBatch(List<String> texts);

  /// Dimensionality of vectors produced by this provider.
  int get dimensions;

  /// Stable identifier matching [ModelState.currentModelId].
  String get modelId;

  /// Release any held resources (ONNX session, HTTP client, etc.).
  Future<void> dispose();
}
