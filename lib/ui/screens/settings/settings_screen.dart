import 'package:flutter/material.dart';

/// App settings: AI engine (local/cloud), model tier, download management.
/// Phase 3 will implement the full ModelManager UI.
class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('设置')),
      body: const Center(child: Text('Phase 3 将实现 AI 引擎设置与模型管理')),
    );
  }
}
