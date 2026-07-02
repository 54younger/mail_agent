import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../providers/email_providers.dart';
import '../../widgets/index_progress_bar.dart';

class InboxScreen extends ConsumerWidget {
  const InboxScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final emailsAsync = ref.watch(emailListProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('收件箱')),
      body: Column(
        children: [
          const IndexProgressBar(),
          Expanded(
            child: emailsAsync.when(
              loading: () =>
                  const Center(child: CircularProgressIndicator()),
              error: (e, _) => Center(child: Text('加载失败：$e')),
              data: (emails) {
                if (emails.isEmpty) {
                  return const Center(
                    child: Text('暂无邮件，同步完成后将自动显示'),
                  );
                }
                return ListView.builder(
                  itemCount: emails.length,
                  itemBuilder: (context, index) {
                    final email = emails[index];
                    return ListTile(
                      leading: const CircleAvatar(
                        child: Icon(Icons.mail_outline, size: 18),
                      ),
                      title: Text(
                        email.subject.isEmpty ? '（无主题）' : email.subject,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                      subtitle: Text(
                        email.fromAddress.isEmpty
                            ? '未知发件人'
                            : email.fromAddress,
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
              },
            ),
          ),
        ],
      ),
    );
  }

  String _formatDate(DateTime dt) {
    final now = DateTime.now();
    if (dt.year == now.year &&
        dt.month == now.month &&
        dt.day == now.day) {
      return '${dt.hour.toString().padLeft(2, '0')}:'
          '${dt.minute.toString().padLeft(2, '0')}';
    }
    return '${dt.month}/${dt.day}';
  }
}
