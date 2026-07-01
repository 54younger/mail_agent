import 'package:flutter/material.dart';

/// Non-blocking progress indicator shown while the HNSW index is being built.
/// Displayed at the top of InboxScreen — user can still browse emails.
/// Phase 3 will wire this to IndexService's progress stream.
class IndexProgressBar extends StatelessWidget {
  const IndexProgressBar({super.key});

  @override
  Widget build(BuildContext context) {
    // TODO(phase3): Watch indexProgressProvider; hide when completed.
    return const SizedBox.shrink();
  }
}

/// Visible variant rendered during active indexing.
class ActiveIndexProgressBar extends StatelessWidget {
  const ActiveIndexProgressBar({
    super.key,
    required this.fraction,
    required this.estimatedSecondsRemaining,
  });

  final double fraction;
  final int estimatedSecondsRemaining;

  @override
  Widget build(BuildContext context) {
    final minutes = estimatedSecondsRemaining ~/ 60;
    final seconds = estimatedSecondsRemaining % 60;
    final timeLabel =
        minutes > 0 ? '约剩 $minutes 分 $seconds 秒' : '约剩 $seconds 秒';

    return Material(
      color: Theme.of(context).colorScheme.surfaceContainerHighest,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    '智能索引构建中 ${(fraction * 100).toStringAsFixed(0)}% · $timeLabel',
                    style: Theme.of(context).textTheme.labelSmall,
                  ),
                  const SizedBox(height: 4),
                  LinearProgressIndicator(value: fraction),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
