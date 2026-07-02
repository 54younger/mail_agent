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

  static const _splitBreakpoint = 720.0;

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

          final list = _EmailList(
            emails: emails,
            selectedId: _selected?.id,
            onTap: (e) => setState(() => _selected = e),
          );

          if (!wide) {
            return _selected == null
                ? list
                : EmailDetailView(key: ValueKey(_selected!.id), email: _selected!);
          }

          return Row(
            children: [
              SizedBox(width: 360, child: list),
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
