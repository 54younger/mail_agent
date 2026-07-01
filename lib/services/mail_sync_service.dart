import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/secure_storage/secure_storage.dart';
import '../data/models/account.dart';
import '../data/models/email_message.dart';
import '../data/objectbox/objectbox_store.dart';
import '../providers/app_providers.dart';

/// Handles initial full fetch and subsequent incremental IMAP sync.
/// Phase 1 will implement the actual enough_mail integration.
class MailSyncService {
  MailSyncService({
    required ObjectBoxStore store,
    required SecureStorage secureStorage,
  })  : _store = store,
        _secureStorage = secureStorage;

  final ObjectBoxStore _store;
  final SecureStorage _secureStorage;

  /// Full fetch of all messages in all folders.
  /// Persists headers immediately; body is fetched lazily.
  Future<void> initialSync(Account account) async {
    // TODO(phase1): Connect via enough_mail, iterate UIDs, persist EmailMessage.
    throw UnimplementedError('MailSyncService.initialSync not yet implemented.');
  }

  /// Fetch only new/changed messages since [account.lastSyncAt].
  Future<void> incrementalSync(Account account) async {
    // TODO(phase1): IMAP UIDFETCH since last sync time.
    throw UnimplementedError('MailSyncService.incrementalSync not yet implemented.');
  }

  /// Populate body text for a single message (triggered on open).
  Future<void> fetchBody(EmailMessage email, Account account) async {
    // TODO(phase1): IMAP FETCH BODY for the given UID.
    throw UnimplementedError('MailSyncService.fetchBody not yet implemented.');
  }
}

final mailSyncServiceProvider = Provider<MailSyncService>((ref) {
  final store = ref.watch(objectBoxStoreProvider);
  final secureStorage = ref.watch(secureStorageProvider);
  return MailSyncService(store: store, secureStorage: secureStorage);
});
