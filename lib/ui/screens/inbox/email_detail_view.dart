import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../data/models/email_message.dart';
import '../../../data/objectbox/objectbox_store.dart';
import '../../../services/mail_sync_service.dart';

/// Reading pane for a single email. Lazily fetches the body via IMAP the first
/// time a message is opened (headers-only sync leaves [EmailMessage.bodyText]
/// empty), then caches it in ObjectBox.
class EmailDetailView extends ConsumerStatefulWidget {
  const EmailDetailView({super.key, required this.email});

  final EmailMessage email;

  @override
  ConsumerState<EmailDetailView> createState() => _EmailDetailViewState();
}

class _EmailDetailViewState extends ConsumerState<EmailDetailView> {
  bool _loading = false;
  String _body = '';

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void didUpdateWidget(covariant EmailDetailView oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.email.id != widget.email.id) _load();
  }

  Future<void> _load() async {
    final email = widget.email;
    if (email.bodyText.isNotEmpty) {
      setState(() {
        _body = email.bodyText;
        _loading = false;
      });
      return;
    }

    final accounts = ref.read(objectBoxStoreProvider).accounts.getAll();
    if (accounts.isEmpty) {
      setState(() => _body = '');
      return;
    }

    setState(() => _loading = true);
    // fetchBody swallows its own errors and writes bodyText into `email`.
    await ref.read(mailSyncServiceProvider).fetchBody(email, accounts.first);
    if (!mounted) return;
    setState(() {
      _body = email.bodyText;
      _loading = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    final email = widget.email;
    final tt = Theme.of(context).textTheme;
    final cs = Theme.of(context).colorScheme;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Header block: subject + sender/recipient/date metadata.
        Padding(
          padding: const EdgeInsets.fromLTRB(24, 20, 24, 12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              SelectableText(
                email.subject.isEmpty ? '（无主题）' : email.subject,
                style: tt.titleLarge,
              ),
              const SizedBox(height: 12),
              _MetaRow(
                icon: Icons.person_outline,
                text: email.fromAddress.isEmpty ? '未知发件人' : email.fromAddress,
              ),
              if (email.toAddresses.isNotEmpty)
                _MetaRow(icon: Icons.people_outline, text: email.toAddresses),
              _MetaRow(
                icon: Icons.schedule,
                text: _formatFull(email.date),
              ),
            ],
          ),
        ),
        const Divider(height: 1),
        // Body.
        Expanded(
          child: _loading
              ? const Center(child: CircularProgressIndicator())
              : SingleChildScrollView(
                  padding: const EdgeInsets.all(24),
                  child: _body.trim().isEmpty
                      ? Text(
                          '（无正文内容）',
                          style: tt.bodyMedium
                              ?.copyWith(color: cs.onSurfaceVariant),
                        )
                      : SelectableText(_body, style: tt.bodyMedium),
                ),
        ),
      ],
    );
  }

  String _formatFull(DateTime dt) {
    final l = dt.toLocal();
    String two(int n) => n.toString().padLeft(2, '0');
    return '${l.year}-${two(l.month)}-${two(l.day)} '
        '${two(l.hour)}:${two(l.minute)}';
  }
}

class _MetaRow extends StatelessWidget {
  const _MetaRow({required this.icon, required this.text});
  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final tt = Theme.of(context).textTheme;
    return Padding(
      padding: const EdgeInsets.only(bottom: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 15, color: cs.onSurfaceVariant),
          const SizedBox(width: 8),
          Expanded(
            child: SelectableText(
              text,
              style: tt.bodySmall?.copyWith(color: cs.onSurfaceVariant),
            ),
          ),
        ],
      ),
    );
  }
}
