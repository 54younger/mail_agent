import 'package:flutter/material.dart';

import '../../widgets/index_progress_bar.dart';

/// Main email list screen.
/// Phase 2: folder nav / list / detail / search entry point.
/// Available immediately after binding — does not depend on AI indexing.
class InboxScreen extends StatelessWidget {
  const InboxScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('收件箱')),
      body: Column(
        children: [
          const IndexProgressBar(),
          const Expanded(
            child: Center(child: Text('Phase 2 将实现邮件列表')),
          ),
        ],
      ),
    );
  }
}
