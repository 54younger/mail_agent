import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/constants.dart';
import '../data/models/email_message.dart';
import '../data/models/job_application.dart';
import '../data/objectbox/objectbox_store.dart';
import '../providers/app_providers.dart';

/// Uses Claude Haiku to extract job application data from emails.
/// Phase 5 will implement structured extraction and the dashboard view.
class JobTrackerService {
  JobTrackerService({
    required ObjectBoxStore store,
    required String claudeApiKey,
  })  : _store = store,
        _claudeApiKey = claudeApiKey;

  final ObjectBoxStore _store;
  final String _claudeApiKey;

  /// Extract company, date, and status from [email]; upsert a [JobApplication].
  Future<JobApplication?> extractJobApplication(EmailMessage email) async {
    // TODO(phase5): Claude tool_use → company / appliedAt / status.
    // Upsert into ObjectBox; manuallyEdited=false initially.
    throw UnimplementedError(
        'JobTrackerService.extractJobApplication not yet implemented.');
  }

  /// Manually update the status of an existing application.
  /// Sets manuallyEdited=true and appends to timelineJson.
  Future<void> updateStatus(int applicationId, JobStatus status) async {
    // TODO(phase5): Append {status, ts} to timelineJson.
    throw UnimplementedError('JobTrackerService.updateStatus not yet implemented.');
  }

  List<JobApplication> getAllApplications() {
    // TODO(phase5): Return sorted by appliedAt desc.
    throw UnimplementedError(
        'JobTrackerService.getAllApplications not yet implemented.');
  }
}

final jobTrackerServiceProvider = FutureProvider<JobTrackerService>((ref) async {
  final store = ref.watch(objectBoxStoreProvider);
  final secureStorage = ref.watch(secureStorageProvider);
  final apiKey =
      await secureStorage.read(key: AppConstants.secureStorageKeyClaudeApiKey) ?? '';
  return JobTrackerService(store: store, claudeApiKey: apiKey);
});
