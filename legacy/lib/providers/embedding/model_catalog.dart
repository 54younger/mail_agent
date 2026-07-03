import 'dart:io';

enum ModelTier { fast, balanced, powerful }

class ModelSpec {
  const ModelSpec({
    required this.id,
    required this.displayName,
    required this.tier,
    required this.dimensions,
    required this.approxSizeMb,
    required this.downloadUrl,
    required this.sha256,
    this.desktopOnly = false,
  });

  final String id;
  final String displayName;
  final ModelTier tier;
  final int dimensions;
  final int approxSizeMb;
  final String downloadUrl;
  final String sha256;

  /// True for models too large for mobile devices.
  final bool desktopOnly;
}

/// All available embedding models.
/// downloadUrl and sha256 are placeholders — fill in during Phase 3.
class ModelCatalog {
  ModelCatalog._();

  static const List<ModelSpec> all = [
    ModelSpec(
      id: 'multilingual-e5-small',
      displayName: '快速档  multilingual-e5-small',
      tier: ModelTier.fast,
      dimensions: 384,
      approxSizeMb: 120,
      downloadUrl: 'https://placeholder/multilingual-e5-small.onnx',
      sha256: 'placeholder_sha256_fast',
    ),
    ModelSpec(
      id: 'multilingual-e5-base',
      displayName: '均衡档  multilingual-e5-base',
      tier: ModelTier.balanced,
      dimensions: 768,
      approxSizeMb: 280,
      downloadUrl: 'https://placeholder/multilingual-e5-base.onnx',
      sha256: 'placeholder_sha256_balanced',
    ),
    ModelSpec(
      id: 'bge-m3',
      displayName: '强力档  bge-m3',
      tier: ModelTier.powerful,
      dimensions: 1024,
      approxSizeMb: 560,
      downloadUrl: 'https://placeholder/bge-m3.onnx',
      sha256: 'placeholder_sha256_powerful',
      desktopOnly: true,
    ),
  ];

  /// Models available on the current platform.
  static List<ModelSpec> available() {
    final isMobile = Platform.isIOS || Platform.isAndroid;
    return all.where((m) => !isMobile || !m.desktopOnly).toList();
  }

  /// Recommend a tier based on available system memory (MB).
  static ModelSpec recommend(int freeMemoryMb) {
    if (freeMemoryMb >= 4096) return all[2];
    if (freeMemoryMb >= 1536) return all[1];
    return all[0];
  }

  static ModelSpec? byId(String id) {
    try {
      return all.firstWhere((m) => m.id == id);
    } catch (_) {
      return null;
    }
  }
}
