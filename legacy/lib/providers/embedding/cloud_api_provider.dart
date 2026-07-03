import 'embedding_provider.dart';

/// Cloud-API embedding provider (fallback when local ONNX is unavailable
/// or the user explicitly selects cloud mode).
/// Phase 3 will wire in the actual API call and key management.
class CloudApiProvider implements EmbeddingProvider {
  CloudApiProvider({required this.apiKey, required String model})
      : _modelId = model;

  final String apiKey;
  final String _modelId;

  @override
  int get dimensions => 384; // TODO(phase3): derive from chosen cloud model.

  @override
  String get modelId => _modelId;

  @override
  Future<List<double>> embed(String text) async {
    // TODO(phase3): POST to cloud embedding API with [apiKey].
    throw UnimplementedError('CloudApiProvider.embed not yet implemented.');
  }

  @override
  Future<List<List<double>>> embedBatch(List<String> texts) async {
    // TODO(phase3): Batch request to cloud API.
    throw UnimplementedError('CloudApiProvider.embedBatch not yet implemented.');
  }

  @override
  Future<void> dispose() async {}
}
