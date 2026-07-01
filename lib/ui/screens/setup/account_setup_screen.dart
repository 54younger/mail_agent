import 'package:flutter/material.dart';

/// First-run screen where the user binds an IMAP account.
/// Phase 1 will implement the full setup wizard:
///   host / port / TLS / username / password → test connection → save.
class AccountSetupScreen extends StatelessWidget {
  const AccountSetupScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.mail_outline, size: 64),
            const SizedBox(height: 24),
            Text(
              '绑定邮箱',
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: 8),
            const Text('Phase 1 将实现完整的 IMAP 绑定向导'),
          ],
        ),
      ),
    );
  }
}
