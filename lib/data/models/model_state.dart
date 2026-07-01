import 'package:objectbox/objectbox.dart';

@Entity()
class ModelState {
  @Id()
  int id = 0;

  /// ID of the currently active embedding model, e.g. "multilingual-e5-small".
  String currentModelId = '';

  /// JSON-encoded list of downloaded model IDs.
  /// Example: ["multilingual-e5-small", "multilingual-e5-base"]
  String downloadedModelIds = '[]';

  /// Vector dimensions of the active model (384 / 768 / 1024).
  /// A mismatch with stored embeddings requires a full index rebuild.
  int vectorDimensions = 384;

  /// Whether to use local ONNX (true) or cloud API (false).
  bool useLocalModel = true;
}
