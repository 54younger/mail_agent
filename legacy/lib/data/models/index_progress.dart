import 'package:objectbox/objectbox.dart';

enum IndexStatus { idle, running, paused, completed }

@Entity()
class IndexProgress {
  @Id()
  int id = 0;

  int total = 0;
  int done = 0;

  /// Stored as [IndexStatus.index].
  int statusCode = IndexStatus.idle.index;

  @Property(type: PropertyType.date)
  DateTime startedAt = DateTime.now();

  /// The embedding model this progress run belongs to.
  String modelId = '';

  IndexStatus get status => IndexStatus.values[statusCode];
  set status(IndexStatus s) => statusCode = s.index;

  double get progressFraction => total == 0 ? 0.0 : done / total;
}
