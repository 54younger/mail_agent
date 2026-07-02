import 'package:enough_mail/enough_mail.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/imap_error.dart';
import '../core/secure_storage/secure_storage.dart';
import '../data/models/account.dart';
import '../data/models/email_message.dart';
import '../data/objectbox/objectbox_store.dart';
import '../providers/app_providers.dart';

// ── Sync events ───────────────────────────────────────────────────────────────

sealed class SyncEvent {}

final class SyncProgress extends SyncEvent {
  SyncProgress(this.fetched, this.total);
  final int fetched;
  final int total;
}

final class SyncDone extends SyncEvent {
  SyncDone(this.total);
  final int total;
}

final class SyncError extends SyncEvent {
  SyncError(this.message, [this.kind = ImapErrorKind.unknown]);
  final String message;
  final ImapErrorKind kind;
}

// ── Service ───────────────────────────────────────────────────────────────────

class MailSyncService {
  MailSyncService({
    required ObjectBoxStore store,
    required SecureStorage secureStorage,
  })  : _store = store,
        _secureStorage = secureStorage;

  final ObjectBoxStore _store;
  final SecureStorage _secureStorage;

  static const _fetchBatch = 100;
  static const _headersDef = 'UID FLAGS ENVELOPE';

  /// Returns null on success, user-friendly error message on failure.
  /// Calls selectInbox() so provider-level auth blocks
  /// (e.g. 163 "SELECT Unsafe Login") are caught at setup time.
  Future<String?> testConnection({
    required String host,
    required int port,
    required bool useSsl,
    required String username,
    required String password,
  }) async {
    final r = await testConnectionWithKind(
      host: host,
      port: port,
      useSsl: useSsl,
      username: username,
      password: password,
    );
    return r.error;
  }

  /// Like [testConnection] but also returns the [ImapErrorKind] so the
  /// setup screen can show provider-specific hints.
  Future<({String? error, ImapErrorKind kind})> testConnectionWithKind({
    required String host,
    required int port,
    required bool useSsl,
    required String username,
    required String password,
  }) async {
    final client = ImapClient(isLogEnabled: false);
    try {
      await client.connectToServer(host, port, isSecure: useSsl);
      await client.login(username, password);
      await client.selectInbox(); // probes inbox — catches "SELECT Unsafe Login"
      await client.logout();
      return (error: null, kind: ImapErrorKind.unknown);
    } catch (e) {
      final kind = classifyImapError(e);
      return (error: kind.userMessage, kind: kind);
    } finally {
      await client.disconnect();
    }
  }

  /// Yields [SyncEvent]s while fetching all INBOX headers, newest first.
  Stream<SyncEvent> initialSync(Account account) => _initialSync(account);

  Stream<SyncEvent> _initialSync(Account account) async* {
    final password = await _secureStorage.read(key: account.credentialKey);
    if (password == null || password.isEmpty) {
      yield SyncError('找不到密码，请重新绑定账号', ImapErrorKind.authFailed);
      return;
    }

    final client = ImapClient(isLogEnabled: false);
    try {
      await client.connectToServer(
        account.host,
        account.port,
        isSecure: account.useSsl,
      );
      await client.login(account.username, password);

      final select = await client.selectInbox();
      final total = select.messagesExists ?? 0;

      if (total == 0) {
        yield SyncDone(0);
        await client.logout();
        return;
      }

      account.uidValidity = select.uidValidity ?? 0;

      int fetched = 0;
      for (int high = total; high >= 1; high -= _fetchBatch) {
        final low = (high - _fetchBatch + 1).clamp(1, total);
        final seq = MessageSequence.fromRange(low, high);
        final result = await client.fetchMessages(seq, _headersDef);

        final rows = result.messages.map((m) => _toRow(m, 'INBOX')).toList();
        if (rows.isNotEmpty) {
          _store.emails.putMany(rows);
          fetched += rows.length;
          yield SyncProgress(fetched, total);
        }
      }

      account.lastSyncAt = DateTime.now().toIso8601String();
      _store.accounts.put(account);
      await client.logout();
      yield SyncDone(total);
    } catch (e) {
      final kind = classifyImapError(e);
      yield SyncError(kind.userMessage, kind);
    } finally {
      await client.disconnect();
    }
  }

  /// Fetches the latest [_fetchBatch] messages; safe to call periodically.
  Future<void> incrementalSync(Account account) async {
    final password = await _secureStorage.read(key: account.credentialKey);
    if (password == null || password.isEmpty) return;

    final client = ImapClient(isLogEnabled: false);
    try {
      await client.connectToServer(
        account.host,
        account.port,
        isSecure: account.useSsl,
      );
      await client.login(account.username, password);
      final select = await client.selectInbox();
      final total = select.messagesExists ?? 0;
      if (total == 0) return;

      final low = (total - _fetchBatch + 1).clamp(1, total);
      final seq = MessageSequence.fromRange(low, total);
      final result = await client.fetchMessages(seq, _headersDef);

      final rows = result.messages.map((m) => _toRow(m, 'INBOX')).toList();
      if (rows.isNotEmpty) _store.emails.putMany(rows);

      account.lastSyncAt = DateTime.now().toIso8601String();
      _store.accounts.put(account);
      await client.logout();
    } catch (_) {
      // Best-effort; suppress to avoid disrupting the UI.
    } finally {
      await client.disconnect();
    }
  }

  /// Populates body text for one message (called when user opens an email).
  Future<void> fetchBody(EmailMessage email, Account account) async {
    final uid = int.tryParse(email.uid);
    if (uid == null || uid == 0) return;

    final password = await _secureStorage.read(key: account.credentialKey);
    if (password == null || password.isEmpty) return;

    final client = ImapClient(isLogEnabled: false);
    try {
      await client.connectToServer(
        account.host,
        account.port,
        isSecure: account.useSsl,
      );
      await client.login(account.username, password);
      await client.selectInbox();

      final seq = MessageSequence.fromId(uid, isUid: true);
      final result = await client.fetchMessages(seq, 'BODY.PEEK[]');

      if (result.messages.isNotEmpty) {
        final msg = result.messages.first;
        final body =
            msg.decodeTextPlainPart() ?? msg.decodeTextHtmlPart() ?? '';
        email.bodyText = body.length > 20000 ? body.substring(0, 20000) : body;
        _store.emails.put(email);
      }
      await client.logout();
    } catch (_) {
      // Best-effort.
    } finally {
      await client.disconnect();
    }
  }

  // ── Internal ─────────────────────────────────────────────────────────────────

  EmailMessage _toRow(MimeMessage msg, String folder) {
    final env = msg.envelope;
    return EmailMessage()
      ..uid = (msg.uid ?? 0).toString()
      ..folder = folder
      ..fromAddress = env?.from?.firstOrNull?.email ?? ''
      ..toAddresses = env?.to?.map((a) => a.email).join(',') ?? ''
      ..subject = env?.subject ?? ''
      ..date = env?.date ?? DateTime.now()
      ..bodyText = ''
      ..isIndexed = false;
  }
}

// ── Provider ──────────────────────────────────────────────────────────────────

final mailSyncServiceProvider = Provider<MailSyncService>((ref) {
  final store = ref.watch(objectBoxStoreProvider);
  final secureStorage = ref.watch(secureStorageProvider);
  return MailSyncService(store: store, secureStorage: secureStorage);
});
