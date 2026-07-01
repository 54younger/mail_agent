import 'package:objectbox/objectbox.dart';

/// Application status progression.
/// Stored as int in ObjectBox; use [JobStatus.fromCode] / [.code] to convert.
enum JobStatus {
  applied(0),
  onlineTest(1),
  interview(2),
  offer(3),
  rejected(4),
  unknown(99);

  const JobStatus(this.code);
  final int code;

  static JobStatus fromCode(int code) =>
      JobStatus.values.firstWhere((s) => s.code == code, orElse: () => unknown);
}

@Entity()
class JobApplication {
  @Id()
  int id = 0;

  String company = '';

  @Property(type: PropertyType.date)
  DateTime appliedAt = DateTime.now();

  /// Stored as [JobStatus.code].
  int statusCode = JobStatus.applied.code;

  /// FK to EmailMessage.id that triggered this record.
  int emailId = 0;

  /// True when the user has manually overridden AI-extracted data.
  bool manuallyEdited = false;

  /// JSON-encoded list of {status, timestamp} objects for the timeline.
  /// Example: [{"status":0,"ts":"2026-06-15T09:00:00Z"}]
  String timelineJson = '[]';

  JobStatus get status => JobStatus.fromCode(statusCode);
  set status(JobStatus s) => statusCode = s.code;
}
