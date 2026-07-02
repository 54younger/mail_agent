import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../providers/sync_providers.dart';

/// Shown at the top of InboxScreen while IMAP sync is in progress.
/// Hides automatically when sync is idle or complete.
class IndexProgressBar extends ConsumerWidget {
  const IndexProgressBar({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(syncNotifierProvider);
    return switch (state) {
      SyncRunning(:final fetched, :final total, :final fraction) =>
        _SyncBar(fetched: fetched, total: total, fraction: fraction),
      SyncFailed(:final message) => _ErrorBanner(message: message),
      _ => const SizedBox.shrink(),
    };
  }
}

class _SyncBar extends StatelessWidget {
  const _SyncBar({
    required this.fetched,
    required this.total,
    required this.fraction,
  });

  final int fetched;
  final int total;
  final double fraction;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final pct = (fraction * 100).round();

    return Material(
      color: cs.surfaceContainerHighest,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              '正在同步邮件  $pct%  ($fetched / $total)',
              style: Theme.of(context).textTheme.labelSmall,
            ),
            const SizedBox(height: 4),
            LinearProgressIndicator(value: fraction),
          ],
        ),
      ),
    );
  }
}

class _ErrorBanner extends StatelessWidget {
  const _ErrorBanner({required this.message});
  final String message;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Material(
      color: cs.errorContainer,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        child: Row(
          children: [
            Icon(Icons.error_outline, color: cs.onErrorContainer, size: 16),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                '同步失败：$message',
                style: TextStyle(color: cs.onErrorContainer, fontSize: 12),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
