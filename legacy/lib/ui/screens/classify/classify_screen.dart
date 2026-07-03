import 'package:flutter/material.dart';

/// Category management and AI classification trigger screen.
/// Phase 4: create/edit categories, run ClassifyService.classifyAll().
class ClassifyScreen extends StatelessWidget {
  const ClassifyScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('分类管理')),
      body: const Center(child: Text('Phase 4 将实现 AI 分类与归档')),
    );
  }
}
