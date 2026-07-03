# Phase 0 — 首次启动步骤

> 所有命令在 **Windows** 侧（PowerShell 或 CMD）运行，不是 WSL2。

## 前置条件

1. 安装 Flutter SDK（推荐稳定渠道）
   ```
   https://docs.flutter.dev/get-started/install/windows/desktop
   ```
2. 安装 Visual Studio 2022（含"使用 C++ 的桌面开发"工作负载）
3. 把本项目目录从 WSL2 复制到 Windows 路径，或直接在 Windows 路径下操作

---

## 步骤

### 1. 补全 Flutter 平台层
```powershell
cd <项目目录>
flutter create . --platforms=windows,ios --org com.yourname
```
这会在不覆盖已有 `lib/` 源码的前提下，生成 `windows/` 和 `ios/` 平台脚手架。

### 2. 安装依赖
```powershell
flutter pub get
```

### 3. 运行代码生成（ObjectBox schema + Riverpod providers）
```powershell
dart run build_runner build --delete-conflicting-outputs
```
生成文件：
- `lib/objectbox.g.dart`（ObjectBox Store & entity adapters）
- `lib/objectbox-model.json`（schema 快照）

### 4. 验证编译
```powershell
flutter analyze
flutter build windows --debug
```

### 5. 运行
```powershell
flutter run -d windows
```
此时应看到"绑定邮箱"占位屏幕。

---

## 目录结构总览

```
lib/
├── main.dart                          # 入口
├── app.dart                           # MaterialApp + 路由
├── core/
│   ├── constants.dart
│   ├── platform/                      # 平台抽象（Windows / iOS）
│   └── secure_storage/               # 凭据存储抽象 + 实现
├── data/
│   ├── models/                        # ObjectBox 实体（6个）
│   └── objectbox/objectbox_store.dart
├── providers/
│   ├── app_providers.dart             # Riverpod providers
│   └── embedding/                    # EmbeddingProvider 接口 + 实现 + 模型目录
├── services/                          # 6 个服务（Phase 0 均为 stub）
└── ui/
    ├── router.dart
    ├── screens/                       # 6 个页面 stub
    └── widgets/index_progress_bar.dart
```

## 下一步：Phase 1

实现 IMAP 绑定向导（`account_setup_screen.dart` + `mail_sync_service.dart`）。
