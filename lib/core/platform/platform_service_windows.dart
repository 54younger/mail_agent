import 'dart:io';

import 'package:path_provider/path_provider.dart';

import 'platform_service.dart';

class WindowsPlatformService implements PlatformService {
  @override
  Future<String> getAppDocumentsPath() async {
    final dir = await getApplicationDocumentsDirectory();
    return dir.path;
  }

  @override
  Future<int> getAvailableMemoryMb() async {
    // Reads free physical memory from Windows Management Instrumentation.
    // Falls back to 2 GB estimate if unavailable.
    try {
      final result = await Process.run(
        'wmic',
        ['OS', 'get', 'FreePhysicalMemory', '/Value'],
        runInShell: true,
      );
      final match = RegExp(r'FreePhysicalMemory=(\d+)')
          .firstMatch(result.stdout as String);
      if (match != null) {
        return int.parse(match.group(1)!) ~/ 1024;
      }
    } catch (_) {}
    return 2048;
  }

  @override
  int getLogicalCpuCount() => Platform.numberOfProcessors;

  @override
  bool get isDesktop => true;

  @override
  bool get isMobile => false;
}
