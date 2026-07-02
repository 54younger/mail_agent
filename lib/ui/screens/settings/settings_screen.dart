import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../data/models/account.dart';
import '../../../data/objectbox/objectbox_store.dart';
import '../../../providers/sync_providers.dart';
import '../../../services/translation_service.dart';
import '../../router.dart';

/// Settings home. Hosts the bound-account section (info, manual sync, re-bind)
/// and — in Phase 3 — AI engine selection and model management.
class SettingsScreen extends ConsumerWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // Watch sync state so "last synced" / status refreshes after a sync.
    ref.watch(syncNotifierProvider);
    final accounts = ref.read(objectBoxStoreProvider).accounts.getAll();
    final account = accounts.isEmpty ? null : accounts.first;

    return Scaffold(
      appBar: AppBar(title: const Text('设置')),
      body: ListView(
        padding: const EdgeInsets.symmetric(vertical: 8),
        children: [
          _SectionHeader('账户'),
          if (account == null)
            const ListTile(
              leading: Icon(Icons.person_off_outlined),
              title: Text('未绑定邮箱'),
            )
          else
            _AccountTile(account: account),
          if (account != null) ...[
            ListTile(
              leading: const Icon(Icons.sync),
              title: const Text('立即同步'),
              subtitle: const Text('拉取最新邮件'),
              onTap: () => ref
                  .read(syncNotifierProvider.notifier)
                  .syncAccount(account),
            ),
            ListTile(
              leading: const Icon(Icons.sync_problem),
              title: const Text('重新同步全部邮件'),
              subtitle: const Text('重新拉取所有邮件头，修复标题/发件人/日期缺失'),
              onTap: () =>
                  ref.read(syncNotifierProvider.notifier).fullResync(),
            ),
            ListTile(
              leading: const Icon(Icons.swap_horiz),
              title: const Text('重新绑定邮箱'),
              subtitle: const Text('删除当前账户并重新配置'),
              onTap: () => _confirmRebind(context, ref),
            ),
          ],
          const Divider(height: 24),
          _SectionHeader('翻译'),
          ListTile(
            leading: const Icon(Icons.translate),
            title: const Text('翻译目标语言'),
            subtitle: const Text('阅读邮件时可将外语翻译为该语言'),
            trailing: DropdownButton<String>(
              value: ref.watch(translationTargetProvider),
              underline: const SizedBox.shrink(),
              onChanged: (code) {
                if (code != null) {
                  ref.read(translationTargetProvider.notifier).set(code);
                }
              },
              items: [
                for (final entry in kTranslationTargets.entries)
                  DropdownMenuItem(value: entry.key, child: Text(entry.value)),
              ],
            ),
          ),
          const Divider(height: 24),
          _SectionHeader('AI 引擎'),
          const ListTile(
            leading: Icon(Icons.memory_outlined),
            title: Text('模型管理'),
            subtitle: Text('Phase 3 将实现 AI 引擎设置与模型下载'),
            enabled: false,
          ),
        ],
      ),
    );
  }

  Future<void> _confirmRebind(BuildContext context, WidgetRef ref) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('重新绑定邮箱'),
        content: const Text('将删除当前账户及其本地凭据，需要重新输入邮箱信息。确定继续？'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('取消'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('确定'),
          ),
        ],
      ),
    );
    if (ok != true) return;

    await ref.read(syncNotifierProvider.notifier).resetForResetup();
    appRouterDelegate.navigateTo(AppRoutes.setup);
  }
}

class _SectionHeader extends StatelessWidget {
  const _SectionHeader(this.title);
  final String title;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
      child: Text(
        title,
        style: Theme.of(context)
            .textTheme
            .labelLarge
            ?.copyWith(color: cs.primary),
      ),
    );
  }
}

class _AccountTile extends StatelessWidget {
  const _AccountTile({required this.account});
  final Account account;

  @override
  Widget build(BuildContext context) {
    return ListTile(
      leading: const CircleAvatar(child: Icon(Icons.person)),
      title: Text(account.username),
      subtitle: Text(
        '${account.host}\n上次同步：${_lastSync(account.lastSyncAt)}',
      ),
      isThreeLine: true,
    );
  }

  String _lastSync(String? iso) {
    if (iso == null) return '从未';
    final dt = DateTime.tryParse(iso);
    if (dt == null) return '从未';
    final l = dt.toLocal();
    String two(int n) => n.toString().padLeft(2, '0');
    return '${l.year}-${two(l.month)}-${two(l.day)} '
        '${two(l.hour)}:${two(l.minute)}';
  }
}
