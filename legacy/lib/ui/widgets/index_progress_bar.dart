import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/imap_error.dart';
import '../../providers/sync_providers.dart';
import '../router.dart';

/// Shown at the top of InboxScreen during sync or when sync fails.
/// Hides automatically when idle or complete.
class IndexProgressBar extends ConsumerWidget {
  const IndexProgressBar({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(syncNotifierProvider);
    return switch (state) {
      SyncRunning(:final fetched, :final total, :final fraction) =>
        _SyncBar(fetched: fetched, total: total, fraction: fraction),
      SyncFailed(:final message, :final kind) =>
        _ErrorBanner(message: message, kind: kind),
      _ => const SizedBox.shrink(),
    };
  }
}

// ── Progress bar ──────────────────────────────────────────────────────────────

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

// ── Error banner ──────────────────────────────────────────────────────────────

class _ErrorBanner extends ConsumerStatefulWidget {
  const _ErrorBanner({required this.message, required this.kind});
  final String message;
  final ImapErrorKind kind;

  @override
  ConsumerState<_ErrorBanner> createState() => _ErrorBannerState();
}

class _ErrorBannerState extends ConsumerState<_ErrorBanner> {
  bool _showHint = false;
  bool _loading = false;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final tt = Theme.of(context).textTheme;
    final notifier = ref.read(syncNotifierProvider.notifier);

    return Material(
      color: cs.errorContainer,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 10, 8, 10),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            // Title row
            Row(
              children: [
                Icon(Icons.error_outline,
                    color: cs.onErrorContainer, size: 16),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    widget.message,
                    style:
                        tt.bodySmall?.copyWith(color: cs.onErrorContainer),
                  ),
                ),
                IconButton(
                  icon: Icon(
                    _showHint ? Icons.expand_less : Icons.expand_more,
                    size: 18,
                    color: cs.onErrorContainer,
                  ),
                  tooltip: _showHint ? '收起详情' : '查看解决方法',
                  onPressed: () =>
                      setState(() => _showHint = !_showHint),
                ),
              ],
            ),

            // Expandable hint
            if (_showHint) ...[
              const SizedBox(height: 6),
              Padding(
                padding: const EdgeInsets.only(left: 24, right: 8),
                child: Text(
                  widget.kind.hint,
                  style: tt.labelSmall
                      ?.copyWith(color: cs.onErrorContainer),
                ),
              ),
            ],

            // Action buttons
            const SizedBox(height: 4),
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                // Retry button (network / server errors, or unknown)
                if (widget.kind.canRetry || widget.kind == ImapErrorKind.unknown)
                  TextButton(
                    onPressed: _loading
                        ? null
                        : () async {
                            setState(() => _loading = true);
                            await notifier.retry();
                            if (mounted) setState(() => _loading = false);
                          },
                    style: TextButton.styleFrom(
                        foregroundColor: cs.onErrorContainer),
                    child: _loading
                        ? SizedBox(
                            width: 14,
                            height: 14,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              color: cs.onErrorContainer,
                            ),
                          )
                        : const Text('重试'),
                  ),
                // Re-bind button (auth / config / unknown errors)
                if (widget.kind.shouldResetup)
                  FilledButton.tonal(
                    onPressed: _loading
                        ? null
                        : () async {
                            setState(() => _loading = true);
                            await notifier.resetForResetup();
                            if (mounted) {
                              appRouterDelegate.navigateTo(AppRoutes.setup);
                            }
                          },
                    style: FilledButton.styleFrom(
                      backgroundColor: cs.onErrorContainer,
                      foregroundColor: cs.errorContainer,
                    ),
                    child: const Text('重新绑定邮箱'),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
