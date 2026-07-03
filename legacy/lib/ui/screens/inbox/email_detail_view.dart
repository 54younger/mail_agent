import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_widget_from_html_core/flutter_widget_from_html_core.dart';

import '../../../data/models/email_message.dart';
import '../../../data/objectbox/objectbox_store.dart';
import '../../../services/mail_sync_service.dart';
import '../../../services/translation_service.dart';

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

  // Translation state (on-demand, per email).
  String? _translated;
  bool _showTranslated = false;
  bool _translating = false;

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
    // Reset translation when switching to a different email.
    _translated = null;
    _showTranslated = false;
    _translating = false;

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
        // Translation toolbar.
        if (!_loading && _body.trim().isNotEmpty) _buildTranslateBar(context),
        const Divider(height: 1),
        // Body (original or translated).
        Expanded(
          child: _loading
              ? const Center(child: CircularProgressIndicator())
              : SingleChildScrollView(
                  padding: const EdgeInsets.all(24),
                  child: _buildBody(tt, cs),
                ),
        ),
      ],
    );
  }

  Widget _buildBody(TextTheme tt, ColorScheme cs) {
    final showTranslation = _showTranslated && _translated != null;
    final content = showTranslation ? _translated! : _body;

    if (content.trim().isEmpty) {
      return Text('（无正文内容）',
          style: tt.bodyMedium?.copyWith(color: cs.onSurfaceVariant));
    }
    // Translated text is plain; original may be HTML (render images/links).
    if (showTranslation) {
      return SelectableText(content, style: tt.bodyMedium);
    }
    return _looksLikeHtml(content)
        ? HtmlWidget(content)
        : SelectableText(content, style: tt.bodyMedium);
  }

  Widget _buildTranslateBar(BuildContext context) {
    final target = ref.watch(translationTargetProvider);
    final targetLabel = kTranslationTargets[target] ?? target;

    return Padding(
      padding: const EdgeInsets.fromLTRB(24, 0, 16, 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.end,
        children: [
          if (_translating)
            const SizedBox(
              width: 16,
              height: 16,
              child: CircularProgressIndicator(strokeWidth: 2),
            )
          else if (_translated == null)
            TextButton.icon(
              icon: const Icon(Icons.translate, size: 18),
              label: Text('翻译为$targetLabel'),
              onPressed: _translate,
            )
          else
            SegmentedButton<bool>(
              segments: const [
                ButtonSegment(value: false, label: Text('原文')),
                ButtonSegment(value: true, label: Text('译文')),
              ],
              selected: {_showTranslated},
              onSelectionChanged: (s) =>
                  setState(() => _showTranslated = s.first),
              style: const ButtonStyle(visualDensity: VisualDensity.compact),
            ),
        ],
      ),
    );
  }

  Future<void> _translate() async {
    setState(() => _translating = true);
    try {
      final service = await ref.read(translationServiceProvider.future);
      final target = ref.read(translationTargetProvider);
      final result = await service.translate(_body, targetLang: target);
      if (!mounted) return;
      setState(() {
        _translated = result.translated;
        _showTranslated = true;
        _translating = false;
      });
    } on TranslationUnavailable catch (e) {
      if (!mounted) return;
      setState(() => _translating = false);
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(e.message)));
    } catch (e) {
      if (!mounted) return;
      setState(() => _translating = false);
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text('翻译失败：$e')));
    }
  }

  String _formatFull(DateTime dt) {
    final l = dt.toLocal();
    String two(int n) => n.toString().padLeft(2, '0');
    return '${l.year}-${two(l.month)}-${two(l.day)} '
        '${two(l.hour)}:${two(l.minute)}';
  }

  /// Heuristic: does the stored body contain HTML markup? fetchBody prefers the
  /// HTML part, so plain-text bodies (no tags) fall through to SelectableText.
  static final _htmlTag = RegExp(
    r'<(html|body|head|div|table|tr|td|p|br|img|a|span|ul|ol|li|h[1-6]|style|meta)\b',
    caseSensitive: false,
  );

  bool _looksLikeHtml(String s) => _htmlTag.hasMatch(s);
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
