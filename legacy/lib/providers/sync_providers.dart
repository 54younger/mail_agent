import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/imap_error.dart';
import '../data/models/account.dart';
import '../data/objectbox/objectbox_store.dart';
import '../providers/app_providers.dart';
import '../services/mail_sync_service.dart';

// ── State ─────────────────────────────────────────────────────────────────────

sealed class SyncState {
  const SyncState();
}

final class SyncIdle extends SyncState {
  const SyncIdle();
}

final class SyncRunning extends SyncState {
  const SyncRunning(this.fetched, this.total);
  final int fetched;
  final int total;
  double get fraction => total == 0 ? 0.0 : fetched / total;
}

final class SyncComplete extends SyncState {
  const SyncComplete(this.total);
  final int total;
}

final class SyncFailed extends SyncState {
  const SyncFailed(this.message, this.kind);
  final String message;
  final ImapErrorKind kind;
}

// ── Notifier ──────────────────────────────────────────────────────────────────

class SyncNotifier extends Notifier<SyncState> {
  Account? _lastAccount;

  @override
  SyncState build() => const SyncIdle();

  /// Starts a full initial sync for [account] (first bind — fetches all
  /// headers). Does not need to be awaited — caller can navigate away.
  Future<void> startInitialSync(Account account) =>
      _run(account, full: true);

  /// Incremental launch/refresh sync — fetches only the newest batch.
  /// Called when the app reopens with an already-bound account so the
  /// progress bar appears and new mail is pulled in.
  Future<void> syncAccount(Account account) => _run(account, full: false);

  Future<void> _run(Account account, {required bool full}) async {
    _lastAccount = account;
    state = const SyncRunning(0, 0);
    final service = ref.read(mailSyncServiceProvider);
    final stream =
        full ? service.initialSync(account) : service.refresh(account);

    await for (final event in stream) {
      switch (event) {
        case SyncProgress(:final fetched, :final total):
          state = SyncRunning(fetched, total);
        case SyncDone(:final total):
          state = SyncComplete(total);
        case SyncError(:final message, :final kind):
          state = SyncFailed(message, kind);
      }
    }
  }

  /// Retries the last sync (useful for transient network / server errors).
  Future<void> retry() async {
    if (_lastAccount case final a?) await startInitialSync(a);
  }

  /// Re-fetches ALL headers (not just the newest batch) and upserts them by
  /// UID, repairing any locally cached rows that were stored with incomplete
  /// metadata. Falls back to the stored account when there is no active one.
  Future<void> fullResync() async {
    final store = ref.read(objectBoxStoreProvider);
    final all = store.accounts.getAll();
    final account = _lastAccount ?? (all.isEmpty ? null : all.first);
    if (account == null) return;
    await startInitialSync(account);
  }

  /// Deletes the current account and its stored credential so the setup
  /// screen can start fresh. Navigation is the caller's responsibility
  /// (avoids a circular import between providers and the UI router).
  Future<void> resetForResetup() async {
    final store = ref.read(objectBoxStoreProvider);
    // On a fresh launch _lastAccount is null, so fall back to the stored
    // account — this is what makes re-bind work without a prior sync failure.
    final all = store.accounts.getAll();
    final account = _lastAccount ?? (all.isEmpty ? null : all.first);
    if (account == null) {
      state = const SyncIdle();
      return;
    }

    await ref.read(secureStorageProvider).delete(key: account.credentialKey);
    store.accounts.remove(account.id);

    state = const SyncIdle();
    _lastAccount = null;
  }
}

final syncNotifierProvider =
    NotifierProvider<SyncNotifier, SyncState>(SyncNotifier.new);
