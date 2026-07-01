import 'dart:io';

import 'package:path_provider/path_provider.dart';

import 'platform_service.dart';

class IosPlatformService implements PlatformService {
  @override
  Future<String> getAppDocumentsPath() async {
    final dir = await getApplicationDocumentsDirectory();
    return dir.path;
  }

  @override
  Future<int> getAvailableMemoryMb() async {
    // iOS does not expose free memory directly; return conservative estimate.
    return 1024;
  }

  @override
  int getLogicalCpuCount() => Platform.numberOfProcessors;

  @override
  bool get isDesktop => false;

  @override
  bool get isMobile => true;
}
