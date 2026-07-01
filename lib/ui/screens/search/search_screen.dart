import 'package:flutter/material.dart';

/// Natural-language semantic search screen.
/// Phase 3: search bar → SearchService.search() → ranked result list.
class SearchScreen extends StatelessWidget {
  const SearchScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('语义搜索')),
      body: const Center(child: Text('Phase 3 将实现语义搜索')),
    );
  }
}
