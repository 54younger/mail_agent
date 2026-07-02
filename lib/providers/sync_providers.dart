import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/models/account.dart';
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
  const SyncFailed(this.message);
  final String message;
}

// ── Notifier ──────────────────────────────────────────────────────────────────

class SyncNotifier extends Notifier<SyncState> {
  @override
  SyncState build() => const SyncIdle();

  /// Kicks off initial sync and streams progress updates into state.
  /// Does not need to be awaited — caller can navigate away immediately.
  Future<void> startInitialSync(Account account) async {
    state = const SyncRunning(0, 0);
    final service = ref.read(mailSyncServiceProvider);

    await for (final event in service.initialSync(account)) {
      switch (event) {
        case SyncProgress(:final fetched, :final total):
          state = SyncRunning(fetched, total);
        case SyncDone(:final total):
          state = SyncComplete(total);
        case SyncError(:final message):
          state = SyncFailed(message);
      }
    }
  }
}

final syncNotifierProvider =
    NotifierProvider<SyncNotifier, SyncState>(SyncNotifier.new);
