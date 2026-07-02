import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../data/models/account.dart';
import '../../../data/objectbox/objectbox_store.dart';
import '../../../providers/app_providers.dart';
import '../../../providers/sync_providers.dart';
import '../../../services/mail_sync_service.dart';
import '../../router.dart';

// ── Common IMAP provider presets ──────────────────────────────────────────────

class _ProviderPreset {
  const _ProviderPreset(this.name, this.host, this.port, this.useSsl);
  final String name;
  final String host;
  final int port;
  final bool useSsl;
}

const _presets = [
  _ProviderPreset('Gmail', 'imap.gmail.com', 993, true),
  _ProviderPreset('QQ 邮箱', 'imap.qq.com', 993, true),
  _ProviderPreset('163', 'imap.163.com', 993, true),
  _ProviderPreset('Outlook', 'outlook.office365.com', 993, true),
  _ProviderPreset('iCloud', 'imap.mail.me.com', 993, true),
];

// ── Screen ────────────────────────────────────────────────────────────────────

enum _TestStatus { idle, testing, success, failure }

class AccountSetupScreen extends ConsumerStatefulWidget {
  const AccountSetupScreen({super.key});

  @override
  ConsumerState<AccountSetupScreen> createState() => _AccountSetupScreenState();
}

class _AccountSetupScreenState extends ConsumerState<AccountSetupScreen> {
  final _formKey = GlobalKey<FormState>();
  final _emailCtrl = TextEditingController();
  final _passwordCtrl = TextEditingController();
  final _hostCtrl = TextEditingController();
  final _portCtrl = TextEditingController(text: '993');

  bool _useSsl = true;
  bool _passwordVisible = false;
  _TestStatus _testStatus = _TestStatus.idle;
  String _testError = '';
  String _testHint = '';
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    // If account already exists (e.g. app restart), skip straight to inbox.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final store = ref.read(objectBoxStoreProvider);
      if (store.accounts.getAll().isNotEmpty) {
        appRouterDelegate.navigateTo(AppRoutes.inbox);
      }
    });
  }

  @override
  void dispose() {
    _emailCtrl.dispose();
    _passwordCtrl.dispose();
    _hostCtrl.dispose();
    _portCtrl.dispose();
    super.dispose();
  }

  void _applyPreset(_ProviderPreset p) {
    setState(() {
      _hostCtrl.text = p.host;
      _portCtrl.text = p.port.toString();
      _useSsl = p.useSsl;
      _testStatus = _TestStatus.idle;
      _testError = '';
      _testHint = '';
    });
  }

  void _clearTestResult() {
    _testStatus = _TestStatus.idle;
    _testError = '';
    _testHint = '';
  }

  Future<void> _testConnection() async {
    if (!(_formKey.currentState?.validate() ?? false)) return;
    setState(() {
      _testStatus = _TestStatus.testing;
      _testError = '';
      _testHint = '';
    });

    final result =
        await ref.read(mailSyncServiceProvider).testConnectionWithKind(
              host: _hostCtrl.text.trim(),
              port: int.tryParse(_portCtrl.text.trim()) ?? 993,
              useSsl: _useSsl,
              username: _emailCtrl.text.trim(),
              password: _passwordCtrl.text,
            );

    if (!mounted) return;
    setState(() {
      if (result.error == null) {
        _testStatus = _TestStatus.success;
      } else {
        _testStatus = _TestStatus.failure;
        _testError = result.error!;
        _testHint = result.kind.hint;
      }
    });
  }

  Future<void> _saveAndSync() async {
    if (!(_formKey.currentState?.validate() ?? false)) return;
    setState(() => _saving = true);

    final store = ref.read(objectBoxStoreProvider);
    final secureStorage = ref.read(secureStorageProvider);

    final username = _emailCtrl.text.trim();
    final host = _hostCtrl.text.trim();
    final credentialKey = 'imap_${username}_$host';

    await secureStorage.write(key: credentialKey, value: _passwordCtrl.text);

    final account = Account()
      ..host = host
      ..port = int.tryParse(_portCtrl.text.trim()) ?? 993
      ..useSsl = _useSsl
      ..username = username
      ..credentialKey = credentialKey
      ..displayName = username;

    store.accounts.put(account);

    if (!mounted) return;

    // Navigate first; sync continues streaming into syncNotifierProvider.
    appRouterDelegate.navigateTo(AppRoutes.inbox);
    // ignore: unawaited_futures — intentional background operation
    ref.read(syncNotifierProvider.notifier).startInitialSync(account);
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final tt = Theme.of(context).textTheme;

    return Scaffold(
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 48),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 480),
            child: Form(
              key: _formKey,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // Header
                  Icon(Icons.mail_rounded, size: 56, color: cs.primary),
                  const SizedBox(height: 16),
                  Text(
                    '绑定邮箱',
                    style: tt.headlineMedium,
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 4),
                  Text(
                    '连接您的 IMAP 邮箱以开始使用',
                    style: tt.bodyMedium
                        ?.copyWith(color: cs.onSurfaceVariant),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 32),

                  // Provider chips
                  Text(
                    '快速选择',
                    style: tt.labelMedium
                        ?.copyWith(color: cs.onSurfaceVariant),
                  ),
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 8,
                    runSpacing: 4,
                    children: _presets
                        .map(
                          (p) => ActionChip(
                            label: Text(p.name),
                            onPressed: () => _applyPreset(p),
                          ),
                        )
                        .toList(),
                  ),
                  const SizedBox(height: 24),

                  // Email
                  TextFormField(
                    controller: _emailCtrl,
                    decoration: const InputDecoration(
                      labelText: '邮箱地址',
                      prefixIcon: Icon(Icons.email_outlined),
                      border: OutlineInputBorder(),
                    ),
                    keyboardType: TextInputType.emailAddress,
                    onChanged: (_) => setState(_clearTestResult),
                    validator: (v) {
                      if (v == null || v.trim().isEmpty) return '请输入邮箱地址';
                      if (!v.contains('@')) return '请输入有效的邮箱地址';
                      return null;
                    },
                  ),
                  const SizedBox(height: 16),

                  // Password
                  TextFormField(
                    controller: _passwordCtrl,
                    obscureText: !_passwordVisible,
                    decoration: InputDecoration(
                      labelText: '密码 / 授权码',
                      prefixIcon: const Icon(Icons.lock_outlined),
                      border: const OutlineInputBorder(),
                      suffixIcon: IconButton(
                        icon: Icon(
                          _passwordVisible
                              ? Icons.visibility_off
                              : Icons.visibility,
                        ),
                        onPressed: () => setState(
                          () => _passwordVisible = !_passwordVisible,
                        ),
                      ),
                    ),
                    onChanged: (_) => setState(_clearTestResult),
                    validator: (v) {
                      if (v == null || v.isEmpty) return '请输入密码或授权码';
                      return null;
                    },
                  ),
                  const SizedBox(height: 24),

                  // Server
                  Text(
                    'IMAP 服务器',
                    style: tt.labelMedium
                        ?.copyWith(color: cs.onSurfaceVariant),
                  ),
                  const SizedBox(height: 8),
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(
                        flex: 3,
                        child: TextFormField(
                          controller: _hostCtrl,
                          decoration: const InputDecoration(
                            labelText: '服务器地址',
                            border: OutlineInputBorder(),
                          ),
                          onChanged: (_) => setState(_clearTestResult),
                          validator: (v) {
                            if (v == null || v.trim().isEmpty) {
                              return '请输入服务器地址';
                            }
                            return null;
                          },
                        ),
                      ),
                      const SizedBox(width: 12),
                      SizedBox(
                        width: 84,
                        child: TextFormField(
                          controller: _portCtrl,
                          decoration: const InputDecoration(
                            labelText: '端口',
                            border: OutlineInputBorder(),
                          ),
                          keyboardType: TextInputType.number,
                          onChanged: (_) =>
                              setState(() => _testStatus = _TestStatus.idle),
                          validator: (v) {
                            final n = int.tryParse(v ?? '');
                            if (n == null || n < 1 || n > 65535) {
                              return '无效';
                            }
                            return null;
                          },
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 4),
                  SwitchListTile(
                    title: const Text('使用 SSL / TLS'),
                    value: _useSsl,
                    onChanged: (v) => setState(() {
                      _useSsl = v;
                      _portCtrl.text = v ? '993' : '143';
                      _testStatus = _TestStatus.idle;
                    }),
                    contentPadding: EdgeInsets.zero,
                  ),
                  const SizedBox(height: 24),

                  // Test connection button
                  FilledButton.tonal(
                    onPressed: _testStatus == _TestStatus.testing
                        ? null
                        : _testConnection,
                    child: _testStatus == _TestStatus.testing
                        ? const SizedBox(
                            width: 18,
                            height: 18,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Text('测试连接'),
                  ),

                  // Success feedback
                  if (_testStatus == _TestStatus.success) ...[
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        Icon(Icons.check_circle_outline,
                            color: cs.primary, size: 18),
                        const SizedBox(width: 8),
                        Text(
                          '连接成功',
                          style: tt.bodyMedium?.copyWith(color: cs.primary),
                        ),
                      ],
                    ),
                  ],

                  // Failure feedback: title + expandable hint box
                  if (_testStatus == _TestStatus.failure) ...[
                    const SizedBox(height: 12),
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Icon(Icons.error_outline,
                            color: cs.error, size: 18),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            _testError,
                            style: tt.bodySmall?.copyWith(color: cs.error),
                          ),
                        ),
                      ],
                    ),
                    if (_testHint.isNotEmpty) ...[
                      const SizedBox(height: 8),
                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: cs.errorContainer.withValues(alpha: 0.5),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Text(
                          _testHint,
                          style: tt.labelSmall
                              ?.copyWith(color: cs.onErrorContainer),
                        ),
                      ),
                    ],
                  ],

                  // Save & sync (only after successful test)
                  if (_testStatus == _TestStatus.success) ...[
                    const SizedBox(height: 16),
                    FilledButton(
                      onPressed: _saving ? null : _saveAndSync,
                      child: _saving
                          ? const SizedBox(
                              width: 18,
                              height: 18,
                              child: CircularProgressIndicator(
                                strokeWidth: 2,
                                color: Colors.white,
                              ),
                            )
                          : const Text('保存并开始同步'),
                    ),
                  ],
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
