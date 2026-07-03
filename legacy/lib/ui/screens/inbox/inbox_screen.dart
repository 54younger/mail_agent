import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../data/models/email_message.dart';
import '../../../providers/email_providers.dart';
import 'email_detail_view.dart';

/// Inbox. On wide windows a master-detail split (list + reading pane); on narrow
/// windows the list, replaced by the reading pane when a message is opened.
class InboxScreen extends ConsumerStatefulWidget {
  const InboxScreen({super.key});

  @override
  ConsumerState<InboxScreen> createState() => _InboxScreenState();
}

class _InboxScreenState extends ConsumerState<InboxScreen> {
  EmailMessage? _selected;
  int _page = 0;

  static const _splitBreakpoint = 720.0;
  static const _pageSize = 100;

  @override
  Widget build(BuildContext context) {
    final emailsAsync = ref.watch(emailListProvider);
    final wide = MediaQuery.sizeOf(context).width >= _splitBreakpoint;
    final showingDetail = !wide && _selected != null;

    return Scaffold(
      appBar: AppBar(
        leading: showingDetail
            ? BackButton(onPressed: () => setState(() => _selected = null))
            : null,
        title: Text(showingDetail
            ? (_selected!.subject.isEmpty ? '（无主题）' : _selected!.subject)
            : '收件箱'),
      ),
      body: emailsAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('加载失败：$e')),
        data: (emails) {
          if (emails.isEmpty) {
            return const Center(child: Text('暂无邮件，同步完成后将自动显示'));
          }

          // Emails are sorted newest-first, so page 0 is the latest 100.
          final total = emails.length;
          final pageCount = (total + _pageSize - 1) ~/ _pageSize;
          final page = _page.clamp(0, pageCount - 1);
          final start = page * _pageSize;
          final end = start + _pageSize <= total ? start + _pageSize : total;
          final pageEmails = emails.sublist(start, end);

          final master = Column(
            children: [
              Expanded(
                child: _EmailList(
                  emails: pageEmails,
                  selectedId: _selected?.id,
                  onTap: (e) => setState(() => _selected = e),
                ),
              ),
              if (pageCount > 1)
                _Pager(
                  page: page,
                  pageCount: pageCount,
                  total: total,
                  onPrev:
                      page > 0 ? () => setState(() => _page = page - 1) : null,
                  onNext: page < pageCount - 1
                      ? () => setState(() => _page = page + 1)
                      : null,
                ),
            ],
          );

          if (!wide) {
            return _selected == null
                ? master
                : EmailDetailView(
                    key: ValueKey(_selected!.id), email: _selected!);
          }

          return Row(
            children: [
              SizedBox(width: 360, child: master),
              const VerticalDivider(width: 1),
              Expanded(
                child: _selected == null
                    ? const _EmptyReadingPane()
                    : EmailDetailView(
                        key: ValueKey(_selected!.id),
                        email: _selected!,
                      ),
              ),
            ],
          );
        },
      ),
    );
  }
}

class _EmailList extends StatelessWidget {
  const _EmailList({
    required this.emails,
    required this.selectedId,
    required this.onTap,
  });

  final List<EmailMessage> emails;
  final int? selectedId;
  final ValueChanged<EmailMessage> onTap;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return ListView.builder(
      itemCount: emails.length,
      itemBuilder: (context, index) {
        final email = emails[index];
        final selected = email.id == selectedId;
        return ListTile(
          selected: selected,
          selectedTileColor: cs.secondaryContainer.withValues(alpha: 0.4),
          onTap: () => onTap(email),
          leading: const CircleAvatar(
            child: Icon(Icons.mail_outline, size: 18),
          ),
          title: Text(
            email.subject.isEmpty ? '（无主题）' : email.subject,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
          subtitle: Text(
            email.fromAddress.isEmpty ? '未知发件人' : email.fromAddress,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
          trailing: Text(
            _formatDate(email.date),
            style: Theme.of(context).textTheme.labelSmall,
          ),
        );
      },
    );
  }

  String _formatDate(DateTime dt) {
    final now = DateTime.now();
    if (dt.year == now.year && dt.month == now.month && dt.day == now.day) {
      return '${dt.hour.toString().padLeft(2, '0')}:'
          '${dt.minute.toString().padLeft(2, '0')}';
    }
    return '${dt.month}/${dt.day}';
  }
}

class _Pager extends StatelessWidget {
  const _Pager({
    required this.page,
    required this.pageCount,
    required this.total,
    required this.onPrev,
    required this.onNext,
  });

  final int page;
  final int pageCount;
  final int total;
  final VoidCallback? onPrev;
  final VoidCallback? onNext;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final tt = Theme.of(context).textTheme;
    return Material(
      color: cs.surfaceContainerLow,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            IconButton(
              icon: const Icon(Icons.chevron_left),
              onPressed: onPrev,
              tooltip: '上一页',
            ),
            Text('第 ${page + 1} / $pageCount 页 · 共 $total 封',
                style: tt.labelSmall),
            IconButton(
              icon: const Icon(Icons.chevron_right),
              onPressed: onNext,
              tooltip: '下一页',
            ),
          ],
        ),
      ),
    );
  }
}

class _EmptyReadingPane extends StatelessWidget {
  const _EmptyReadingPane();

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.drafts_outlined, size: 48, color: cs.onSurfaceVariant),
          const SizedBox(height: 12),
          Text(
            '选择一封邮件以查看内容',
            style: Theme.of(context)
                .textTheme
                .bodyMedium
                ?.copyWith(color: cs.onSurfaceVariant),
          ),
        ],
      ),
    );
  }
}
