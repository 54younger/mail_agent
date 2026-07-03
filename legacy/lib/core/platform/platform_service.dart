abstract class PlatformService {
  Future<String> getAppDocumentsPath();
  Future<int> getAvailableMemoryMb();
  int getLogicalCpuCount();
  bool get isDesktop;
  bool get isMobile;
}
