import 'embedding_provider.dart';
import 'model_catalog.dart';

/// Local ONNX embedding provider.
/// Phase 3 will add ONNX Runtime session init, tokenizer, and batched inference.
class LocalOnnxProvider implements EmbeddingProvider {
  LocalOnnxProvider(this._spec);

  final ModelSpec _spec;

  @override
  int get dimensions => _spec.dimensions;

  @override
  String get modelId => _spec.id;

  @override
  Future<List<double>> embed(String text) async {
    // TODO(phase3): tokenizer → ONNX session → mean-pool.
    throw UnimplementedError('LocalOnnxProvider.embed not yet implemented.');
  }

  @override
  Future<List<List<double>>> embedBatch(List<String> texts) async {
    // TODO(phase3): Batched inference for efficiency.
    throw UnimplementedError('LocalOnnxProvider.embedBatch not yet implemented.');
  }

  @override
  Future<void> dispose() async {
    // TODO(phase3): Close ONNX session.
  }
}
