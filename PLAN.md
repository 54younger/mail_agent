# 邮件管理系统 · 完整实现计划

## 一、项目概述

一个 AI 驱动的邮件管理桌面应用，Windows 优先、未来上架 iOS。核心能力：绑定邮箱后自动收信 → AI 自动分类并归档 → 自然语言语义检索 → 求职投递看板。技术上以一套 **Flutter/Dart** 代码同时覆盖桌面与移动端。

---

## 二、已锁定的决策

| 维度 | 选择 |
|------|------|
| 技术栈 | **Flutter + Dart**（Windows 优先，iOS 复用同一套代码；**全程不用 Python**） |
| AI 策略 | **可切换的混合模式**：本地 embedding ⇄ 云端 API，用户可选 |
| 本地模型 | **模型目录**：快速/均衡/强力三档，按机器性能推荐、可手动切换 |
| 邮箱 | **通用 IMAP** 起步 |
| MVP | **AI 分类 + 语义搜索** 先扎实，求职看板作为其上的特化视图后加 |

---

## 三、技术栈

| 层 | 选型 | 理由 |
|----|------|------|
| UI / 状态 | Flutter + **Riverpod** | 跨平台、声明式、易测 |
| 邮件协议 | **`enough_mail`** | 成熟 Dart IMAP/SMTP 库，支持授权码/OAuth |
| 存储 + 向量 | **ObjectBox**（自带端上 HNSW 向量搜索） | 纯 Dart，Windows/iOS 原生，关系数据与向量一处搞定 |
| 本地 embedding | **ONNX Runtime**（iOS 官方支持，走 CoreML/CPU）+ 多语言模型 | 中英混杂邮件需多语言；桌面与 iOS 双端可跑 |
| 云端 embedding | 云端 embedding API（备选路径） | 端上不理想或用户选"纯云端"时切换 |
| 云端 LLM | **Claude Haiku**（结构化输出/tool use） | 分类与信息抽取，便宜可靠 |
| 凭据安全 | 平台安全存储（Windows Credential Manager / iOS Keychain） | 加密保存邮箱凭据 |

---

## 四、系统架构

### 4.1 分层
```
UI 层 (Flutter Widgets + Riverpod)
  ├─ 收件箱/阅读  ├─ 分类管理  ├─ 语义搜索  ├─ 求职看板  ├─ 设置
──────────────────────────────────────────────────────────
应用/服务层
  ├─ MailSyncService     (IMAP 收取 + 增量同步)
  ├─ IndexService        (embedding 管线, 后台 Isolate, 可恢复)
  ├─ SearchService       (向量检索 Top-N)
  ├─ ClassifyService     (Claude 分类 + 规则归档)
  ├─ JobTrackerService   (Claude 抽取 公司/时间/状态)
  └─ ModelManager        (模型下载/校验/切换/测速)
──────────────────────────────────────────────────────────
Provider 抽象层
  EmbeddingProvider ─┬─ LocalOnnxProvider(modelSpec)
                     └─ CloudApiProvider
──────────────────────────────────────────────────────────
数据层 (ObjectBox: Account/Email/Category/JobApplication/IndexProgress/ModelState)
平台抽象层 (安全存储、文件路径、性能探测 —— 为 iOS 预留差异隔离)
```

### 4.2 Embedding 三层灵活度
```
本地 vs 云端 (EmbeddingProvider)
   └─ 本地时: 模型目录 ModelCatalog
        • 快速档  multilingual-e5-small (384维,~120MB)  低配/手机
        • 均衡档  multilingual-e5-base  (768维,~280MB)
        • 强力档  bge-m3 / e5-large     (1024维,~560MB) 仅桌面
   └─ 按机器性能(CPU/内存/平台)自动推荐 + 手动覆盖
```
- **按需下载**：模型不塞进安装包，选后再下（显示体积/进度/checksum 校验/断点续传）。
- **平台过滤**：iOS 只暴露快速/均衡档，强力档标"仅桌面"。
- **换模型 = 重建索引**：不同模型维度不兼容；每条向量记录其来源模型，切换时复用"后台+进度条+可恢复"体验重建，UI 明确提示预计耗时与逐步恢复。

---

## 五、数据模型（ObjectBox 实体）

- **Account**：IMAP 服务器/端口/TLS、用户名、加密凭据引用。
- **Email**：uid、folder、from/to、subject、body、date、`isIndexed`、`categoryId`、`embedding`(HNSW)、`embeddingModelId`。
- **Category**：名称、颜色、目标归档文件夹、可选 AI 提示词。
- **JobApplication**：company、appliedAt、status（已投递/笔试/面试/Offer/拒信）、emailId、`manuallyEdited` 标志、状态时间线。
- **IndexProgress**：total/done/status，断点续跑。
- **ModelState**：当前所用模型、已下载模型列表、维度。

---

## 六、分阶段计划

### Phase 0 — 项目骨架
Flutter 工程初始化、Riverpod、ObjectBox schema、平台安全存储封装、平台抽象层（为 iOS 预留）、目录结构与依赖。

### Phase 1 — IMAP 绑定与收取
首屏绑定向导（服务器/授权码引导，含 Gmail/QQ/163 常见提示）→ `enough_mail` 全量拉取 + 增量同步 + 凭据加密保存。

### Phase 2 — 邮件浏览 UI（秒级可用，不依赖 AI）
邮件列表 / 详情阅读 / 文件夹导航。绑定后立即可浏览可读信。

### Phase 3 — 本地 Embedding + 语义搜索 ⭐MVP 核心
1. **Provider 抽象** + **模型目录 + 下载管理 + 性能推荐**。
2. **ONNX 双端验证**（本阶段第一技术验证点；不过则默认走云端）。
3. **索引管线**：后台 Isolate、分批、优先级队列（最近优先+疑似求职优先）、可恢复。
4. **语义搜索**：自然语言 → 向量检索 Top-N，已索引子集即时可用。

### Phase 4 — AI 分类与自动归档 ⭐MVP 核心
用户自定义类别 → Claude Haiku 打标（结构化输出）→ 规则落文件夹 → 结果可人工纠正、缓存复用。

### Phase 5 — 求职看板
Claude 从邮件结构化抽取 公司/投递时间/状态 → 表格视图 + 状态时间线 + 手动校正兜底。

### Phase 6 — 打磨与 iOS 预研
平台差异抽象收口、性能与体验打磨、iOS 构建预研。

---

## 七、设置模块（AI 引擎设置）

- 本地 ⇄ 云端切换；
- 本地时选模型档位（快速/均衡/强力），显示推荐与"仅桌面"标记；
- 显示当前索引所用模型；切换触发重建索引并提示耗时；
- 模型下载管理（体积/进度/删除）。

---

## 八、Embedding 初始化 HCI

1. **秒级**：列表/阅读不等 embedding，绑定后立即可用。
2. **后台 Isolate**：ONNX 推理不卡 UI，分批（如每批 32 封）。
3. **优先级队列**：最近优先 + 疑似求职优先。
4. **非阻塞进度**：顶部"智能索引构建中 62% · 约剩 3 分钟"，可折叠/后台。
5. **渐进可用**：搜索在已索引子集即时可用，标注"结果随进度增多"。
6. **可恢复 + 增量**：断点续跑；首建后仅索引新邮件；换模型走同一套重建体验。

---

## 九、风险登记

| 级别 | 风险 | 缓解 |
|------|------|------|
| HIGH | ONNX 多语言模型 iOS 双端跑通 + 体积 | Phase 3 首步验证；不过则默认云端（Provider 已抽象） |
| HIGH | 各邮箱 IMAP/授权差异 | 绑定向导给清晰引导 |
| MEDIUM | 换模型维度不兼容 → 重建索引一致性 | 记录来源模型 + 复用可恢复索引管线 |
| MEDIUM | 模型下载/校验健壮性 | 断点续传 + checksum + 失败回退 |
| MEDIUM | 求职状态识别准确率 | AI 抽取 + 人工可改兜底 |
| MEDIUM | tokenizer 端上化（ONNX 集成最易踩坑处） | Phase 3 验证时一并解决 |

---

## 十、待定 / 后续讨论

- embedding 模型目录的最终具体选型（默认：快速档 `multilingual-e5-small`）
- 云端 LLM 默认 Claude Haiku，是否提供其他 provider
- 是否加入"自动测速跑分"而非仅看硬件参数来推荐模型档位
- iOS 上架相关的证书/发布流程（Phase 6 预研）
