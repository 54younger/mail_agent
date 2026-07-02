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
  // Fetch ENVELOPE *and* the full header block. enough_mail parses ENVELOPE into
  // `message.envelope` and BODY[HEADER] into `message.headers`; _toRow reads
  // both with a fallback chain so metadata is populated whichever path the
  // server/library fills. Headers also let decode* MIME-decode Chinese subjects.
  // MUST be a parenthesized list: enough_mail writes this raw after "FETCH
  // <seq> ", and IMAP requires multi-attribute fetches to be wrapped in "()".
  // Without the parens the server honours only the first attribute (UID) and
  // drops ENVELOPE/HEADER — leaving subject/from/date empty.
  static const _headersDef = '(UID ENVELOPE BODY.PEEK[HEADER])';

  /// Sent to the server via the IMAP ID command (RFC 2971). NetEase
  /// (163/126/yeah.net) rejects SELECT with "Unsafe Login ... kefu@188.com"
  /// unless the client identifies itself this way after login.
  static const _clientId = Id(name: 'Mail Agent', version: '1.0');

  /// Best-effort client identification. Required by 163 before SELECT; harmless
  /// for other providers, which either accept or ignore it. Any failure is
  /// swallowed so a server that rejects ID never breaks the connection.
  Future<void> _identify(ImapClient client) async {
    try {
      await client.id(clientId: _clientId);
    } on Object {
      // Non-fatal — providers without ID support simply move on.
    }
  }

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
      await _identify(client); // 163 requires ID before SELECT
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
      await _identify(client); // 163 requires ID before SELECT

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

        final rows = _upsertRows(result.messages, 'INBOX');
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

  /// Streamed launch/refresh sync: fetches the latest [_fetchBatch] messages
  /// and yields progress so the UI can show a short progress bar on reopen.
  /// Upserts by UID so re-syncing never duplicates rows.
  Stream<SyncEvent> refresh(Account account) => _refresh(account);

  Stream<SyncEvent> _refresh(Account account) async* {
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
      await _identify(client); // 163 requires ID before SELECT
      final select = await client.selectInbox();
      final total = select.messagesExists ?? 0;
      if (total == 0) {
        yield SyncDone(0);
        await client.logout();
        return;
      }

      final low = (total - _fetchBatch + 1).clamp(1, total);
      final want = total - low + 1;
      yield SyncProgress(0, want);

      final seq = MessageSequence.fromRange(low, total);
      final result = await client.fetchMessages(seq, _headersDef);
      final rows = _upsertRows(result.messages, 'INBOX');
      if (rows.isNotEmpty) _store.emails.putMany(rows);

      account.lastSyncAt = DateTime.now().toIso8601String();
      _store.accounts.put(account);
      await client.logout();

      yield SyncProgress(want, want);
      yield SyncDone(want);
    } catch (e) {
      final kind = classifyImapError(e);
      yield SyncError(kind.userMessage, kind);
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
      await _identify(client); // 163 requires ID before SELECT
      await client.selectInbox();

      // seq is a UID sequence, so it must go through UID FETCH, not plain
      // FETCH (which would treat the UID as a sequence number).
      final seq = MessageSequence.fromId(uid, isUid: true);
      final result = await client.uidFetchMessages(seq, '(BODY.PEEK[])');

      if (result.messages.isNotEmpty) {
        final msg = result.messages.first;
        // Prefer HTML so the reading pane can render images/links; fall back to
        // plain text. Cap is large so HTML isn't truncated mid-tag.
        final html = msg.decodeTextHtmlPart();
        final body = (html != null && html.trim().isNotEmpty)
            ? html
            : (msg.decodeTextPlainPart() ?? '');
        const cap = 500000;
        email.bodyText = body.length > cap ? body.substring(0, cap) : body;
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

  /// Maps messages to rows, reusing existing ObjectBox ids for known UIDs so
  /// `putMany` updates in place instead of inserting duplicates.
  List<EmailMessage> _upsertRows(List<MimeMessage> messages, String folder) {
    final existing = _store.emailIdsByUid(folder);
    return messages.map((m) {
      final row = _toRow(m, folder);
      final id = existing[row.uid];
      if (id != null) row.id = id;
      return row;
    }).toList();
  }

  EmailMessage _toRow(MimeMessage msg, String folder) {
    final env = msg.envelope;
    final from = msg.fromEmail ??
        msg.from?.firstOrNull?.email ??
        env?.from?.firstOrNull?.email ??
        '';
    final to = (msg.to ?? env?.to)?.map((a) => a.email).join(',') ?? '';
    final subject = msg.decodeSubject() ?? env?.subject ?? '';
    final date = msg.decodeDate() ?? env?.date ?? DateTime.now();

    return EmailMessage()
      ..uid = (msg.uid ?? 0).toString()
      ..folder = folder
      ..fromAddress = from
      ..toAddresses = to
      ..subject = subject
      ..date = date
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
