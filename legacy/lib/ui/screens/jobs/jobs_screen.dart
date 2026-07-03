import 'package:flutter/material.dart';

/// Job application tracking dashboard.
/// Phase 5: table of company / appliedAt / status + status timeline.
class JobsScreen extends StatelessWidget {
  const JobsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('求职看板')),
      body: const Center(child: Text('Phase 5 将实现求职投递看板')),
    );
  }
}
