import 'package:objectbox/objectbox.dart';

@Entity()
class EmailMessage {
  @Id()
  int id = 0;

  /// IMAP UID scoped to a folder.
  String uid = '';

  String folder = '';
  String fromAddress = '';

  /// Comma-separated recipient addresses.
  String toAddresses = '';
  String subject = '';
  String bodyText = '';

  @Property(type: PropertyType.date)
  DateTime date = DateTime.now();

  bool isIndexed = false;

  /// FK to Category.id; 0 = unclassified.
  int categoryId = 0;

  /// Which embedding model generated the vector below.
  String? embeddingModelId;

  /// HNSW semantic-search vector.
  /// Default dimensions 384 matches multilingual-e5-small (fast tier).
  /// Rebuilding the index is required when switching to a different tier.
  @Property(type: PropertyType.floatVector)
  @HnswIndex(dimensions: 384)
  List<double>? embedding;
}
