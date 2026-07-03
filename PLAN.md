# Mail Agent · 实现计划（Web 重构版）

## 一、方向

一个**自托管、可分发**的求职邮件助手：绑定邮箱（IMAP）→ 浏览/阅读邮件 → 按需 AI 翻译
→ Claude 从邮件抽取投递记录，汇成**求职看板（Kanban）**。

由原 Flutter/Dart 桌面应用重构为 **前后端分离的 Web 应用**：**React 前端 + Python
(FastAPI) 后端**。原 Flutter 代码归档于 `legacy/`。

### 已锁定决策
1. **运行方式 = 自托管单用户、可分发。** 每个用户运行自己的后端；首次启动选择一个**数据
   文件夹**存放各自的 SQLite 数据库。无注册/登录、无中心服务器。后端仅绑定 `127.0.0.1`。
2. **舍弃** AI 语义搜索 + AI 文件夹分类（连同 ONNX/embedding/模型目录/HNSW 向量、
   `Category`/`IndexProgress`/`ModelState`）。
3. **保留** AI 翻译（按需，非英语 → 目标语言，默认英语）。
4. **全力投入求职看板**：Claude 抽取 公司/投递时间/状态。
5. **MVP 界面 = 求职看板 + 邮件浏览 + 翻译。** 收件箱是数据来源与佐证，看板为核心主界面。
6. **凭据安全**：IMAP 密码 + Claude Key 存 OS keyring，绝不明文落盘/入库/进 git。

## 二、技术栈

| 层 | 选型 |
|----|------|
| 前端 | Vite + React + TypeScript + Tailwind + React Router + TanStack Query |
| 后端 | FastAPI + Uvicorn（异步） |
| 存储 | SQLite（数据文件夹内）+ SQLAlchemy 2.0 async（aiosqlite）+ Alembic |
| 邮件 | `imap-tools`（高层解析 envelope/主题/日期/发件人，规避原始 FETCH 陷阱）；`ID` 命令在 SELECT 前发送 |
| LLM | `anthropic` SDK，Claude Haiku（翻译 + 抽取共用一套客户端与 Key） |
| 语言检测 | `lingua`（或由 Claude 检测），源语言==目标语言则跳过翻译 |
| 密钥 | `keyring`（OS 钥匙串），回退：口令加密文件（无头/服务器场景） |

安全基线：后端仅绑 `127.0.0.1`；CORS 白名单=本地前端源；ORM 参数化查询；Pydantic 校验；
HTML 正文渲染前用 DOMPurify 消毒。

## 三、目录结构

```
mail_agent/
├── legacy/     归档的 Flutter 桌面应用（仅参考）
├── backend/    FastAPI（app/{main,config,db,core,models,schemas,services,api}）
└── frontend/   Vite React（src/{app,api,features/{board,inbox,settings,setup},components}）
```

## 四、分阶段计划

### Phase 0 — 重构 + 骨架 ✅（已完成）
- Flutter 应用 `git mv` 至 `legacy/`；根 `.gitignore`/`README.md`/`PLAN.md` 更新。
- 后端骨架：FastAPI + CORS + 可选静态前端；`config.py`（数据文件夹解析 + settings.json）；
  `db.py`（异步 SQLite 引擎/会话）；`core/errors.py`（**移植** imap_error.dart 错误分类，含
  中文提示，已单测 15 项通过）；`/api/health`。
- 前端骨架：React 外壳（求职看板/收件箱/设置导航）+ 首次运行数据文件夹引导 + API 客户端
  + 健康检查网关；`pnpm build` 通过。

### Phase 1 — 数据文件夹 + IMAP 绑定 + 同步 + 收件箱
- **首次运行**：`POST /api/setup/data-folder` 设定文件夹 → 建 SQLite + settings.json。
- **模型**（SQLAlchemy）：`Account`、`EmailMessage`（去除 embedding/embeddingModelId/
  categoryId；新增 `translated_text`/`detected_lang`）、`JobApplication`。
- **绑定向导**（host/port/ssl/username/授权码）→ `imap_sync.test_connection`
  （connect → login → **ID** → SELECT INBOX → logout）+ 移植的 `ImapErrorKind` 分类与提示。
  重新绑定 = 删账户 + 删 keyring 条目。
- **同步**（`imap-tools`）：初次全量邮件头（最新优先）+ 增量刷新（最新 100），**按 UID
  upsert** 不重复；`POST /api/sync` + 进度（SSE 或轮询）。
- **邮件**：`GET /api/emails?page=&size=100`（分页，最新优先）；`GET /api/emails/{id}`
  懒加载正文（`BODY.PEEK[]`，优先 HTML）并缓存。
- **收件箱 UI**：分页列表 + 主从阅读面板；DOMPurify 消毒 HTML 正文；远程图片处理。

### Phase 2 — 翻译（真正接入 Claude，按需）
- **设置**：Claude API Key（→ keyring）+ 翻译目标语言（默认 `en`；zh/ja/ko/fr/de/es）。
- `POST /api/emails/{id}/translate`：检测源语言；源==目标则返回原文；否则 Claude Haiku 翻译；
  **缓存** `translated_text` + `detected_lang` 于该行，避免重复调用。
- 阅读面板：「翻译为<语言>」按钮 → 原文/译文切换。

### Phase 3 — 求职看板（核心）
- **模型** `JobApplication`：company、appliedAt、statusCode（applied=0/onlineTest=1/
  interview=2/offer=3/rejected=4/unknown=99）、emailId、manuallyEdited、timelineJson。
- **抽取**（`job_extractor.py`）：Claude Haiku **tool_use / 结构化输出** 遍历候选邮件 →
  公司/投递时间/状态；upsert；`manuallyEdited=true` 的行不被覆盖。端点
  `POST /api/jobs/extract`、`GET /api/jobs`。
- **看板 UI**（主界面）：按状态分列（**语义色**）；卡片（公司/时间/状态）链接到**源邮件+
  译文**；状态时间线；拖拽改状态（→ `PATCH /api/jobs/{id}` 置 `manuallyEdited=true`，
  追加时间线）；手动新增/编辑兜底。遵循设计质量规则——刻意的层级/节奏/动效，非模板看板。

### Phase 4 — 打包与分发
- 一键运行（Uvicorn 提供已构建前端静态文件，单源无 CORS）+ Docker Compose；首次运行文件夹
  选择 + 配置持久化。面向其他用户的 README（前置条件、Claude Key、IMAP 授权码、本地 DB 文件夹）。

## 五、相对旧计划的删减
移除：ONNX/embedding provider、模型目录/下载/校验、HNSW 向量 + 语义搜索、Claude 文件夹分类
+ `Category`、`IndexProgress`、`ModelState`。`EmailMessage` 去掉 `embedding`/
`embeddingModelId`/`categoryId`，新增 `translated_text`/`detected_lang`。

## 六、验证
- **后端**：`pytest`（错误分类 parity、imap_sync 的 upsert-by-uid 与 ID-before-SELECT、
  翻译 skip-if-target 与缓存、job_extractor upsert 与 manuallyEdited 守卫）；`/api/health`
  与真实 163/Gmail 账户联调，确认主题/发件人/**真实日期**与正文加载。
- **前端**：`pnpm build` 通过；Playwright 冒烟（首次文件夹 → 绑定 → 同步进度 → 分页 100/页
  → 打开邮件 → 翻译切换 → 看板显示抽取记录 → 拖拽改状态并追加时间线）。
- **分发**：另一台机器全新克隆、选新数据文件夹，验证隔离的本地 DB 且完全可用。
- **安全**：grep 数据文件夹与 git 无明文密码/Key（仅 keyring）；确认后端默认拒绝非本地绑定。
