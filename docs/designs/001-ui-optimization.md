# 001 UI 样式优化与确认弹窗重构 — 实现设计

## 实现 Checklist

- [x] **规则更新**：
  - [x] 修改项目根目录下的 `AGENTS.md`，增加第十一诫（禁止使用默认浏览器 `confirm`/`alert` 弹窗，改用自定义 UI 组件）。
  - [x] 在 `AGENTS.md` 的常见陷阱中加入关于原生弹窗的负面示例。
- [x] **全局样式重构 (index.css)**：
  - [x] 将 CSS 变量重构为浅色模式（白色背景 `#ffffff`，侧边栏浅灰 `#f9f9f9`/`#f3f4f6`，文字深灰 `#1f2937`/`#374151`，边框 `#e5e7eb`）。
  - [x] 调整原本的 `.glass`、`.glass-card`、`.glass-input` 样式为浅色微光或纯白扁平带阴影卡片样式。
  - [x] 修改 `.message-markdown` 样式，使其中的标题、文字、代码块（`code`，`pre`）、表格在浅色底上表现得美观易读。
- [x] **基础 Modal 组件实现 (Modal.tsx)**：
  - [x] 新建 `frontend/src/components/Modal.tsx`。
  - [x] 设计为浅色 ChatGPT 风格，具备标题、内容槽、页脚操作按钮 and 遮罩层（backdrop-blur-sm, bg-black/25）。
- [x] **Sidebar 优化与 Dropdown 实现**：
  - [x] 优化 Session Item 样式，采用固定高度、稳定 border、统一字重，保证布局没有 Layout Shift。
  - [x] 在个人信息区域添加 Dropdown 下拉菜单。
  - [x] 下拉菜单包含项：设置、报表记录、订阅历史、退出登录。
  - [x] 与顶部 Header 一致地对齐侧边栏边界线条，使之保持 1px 的整洁过渡。
  - [x] **宽度微调**：将 Sidebar 的宽度从原 `w-80`（320px）缩窄为 `w-64`（256px）。
  - [x] **侧边栏折叠按钮**：在 Sidebar 顶部的 Header 区域最右侧添加一个折叠图标按钮（`PanelLeftClose` 或 `ChevronLeft`）。当点击该按钮时，触发侧边栏折叠状态。
- [x] **ChatWindow 优化与输入框重构**：
  - [x] 清空 Top Header 的内容和清空监测历史按钮，仅保留一根空白的 `h-16` 顶部栏作为布局和顶部边界（边框对齐）。
  - [x] **侧边栏展开按钮**：当侧边栏处于折叠状态时，在 ChatWindow 的顶部 Header 最左侧渲染一个精致的“展开侧边栏”按钮（`PanelLeftOpen` 或 `ChevronRight`）。点击它即可重新显示侧边栏。
  - [x] 重构输入框区域，外层限制在 `max-w-3xl` 或 `max-w-4xl` 居中。
  - [x] 输入框整体使用胶囊/圆角卡片，配合 ChatGPT 经典的悬浮阴影（`shadow-[0_0_15px_rgba(0,0,0,0.05)]`）。
  - [x] 输入框内部左侧设计一个扩展功能加号按钮占位符（Lucide `Plus`），右侧是小巧精致的发送按钮。
- [x] **AuthScreen 登录页白色化适配**：
  - [x] 将登录注册页面背景更换为白色/极浅灰，卡片由暗黑玻璃卡片变为精致白底阴影卡片，输入框和按钮统一成极简风格。
- [x] **App.tsx 状态编排与子弹窗实现**：
  - [x] 集中引入 `Modal.tsx` 并维护相关 Modal 的开启状态。
  - [x] **侧边栏折叠状态管理**：维护 `isSidebarCollapsed` 状态。如果为 `true`，则不渲染 Sidebar（或将其宽度过渡隐藏），并向 `ChatWindow` 传参以显示“展开”按钮。
  - [x] 替换原本 `Sidebar` 传出的删除会话逻辑：点击删除时不直接触发 `confirm`，而是通过 Modal 提示，确认后再执行删除。
  - [x] 退出登录同样触发自定义确认 Modal，确认后再执行 logout。
  - [x] 渲染“设置”、“报表记录”、“订阅历史”的极简白色调 Modal。
- [x] **功能测试与校验**：
  - [x] 确保各项操作（折叠展开、新建、选择、重命名、删除会话、发送消息、个人信息菜单操作等）运行完好，无报错。
  - [x] 测试各种分辨率下的布局对齐情况。

## 数据与迁移

本项目修改不涉及后端数据库的 Schema 改变，因此**不需要** Alembic 数据库迁移。

## API 与状态流转

在 `App.tsx` 中将引入以下新状态变量来管理 Modal 的开关与上下文，以及侧边栏的折叠显隐：

```typescript
const [modalType, setModalType] = useState<'settings' | 'reports' | 'subscription' | 'logout_confirm' | 'delete_confirm' | null>(null);
const [sessionToDelete, setSessionToDelete] = useState<SessionInfo | null>(null);
const [isSidebarCollapsed, setIsSidebarCollapsed] = useState<boolean>(false);
```

## 文件改动

### `AGENTS.md`
- [MODIFY] 补充第十一诫以及常见陷阱。

### Frontend Files
- [NEW] `frontend/src/components/Modal.tsx` — 通用弹窗组件。
- [MODIFY] `frontend/src/styles/index.css` — 浅色模式主题、Markdown 样式微调。
- [MODIFY] `frontend/src/components/Sidebar.tsx` — 缩窄宽度至 `w-64`，解决列表抖动、侧边栏线条对齐、底部个人信息 Dropdown 菜单、删除点击状态派发，顶部 Header 处新增折叠按钮。
- [MODIFY] `frontend/src/components/ChatWindow.tsx` — 清空 Header 内部内容（只在折叠时渲染“展开”按钮）、输入框样式重构。
- [MODIFY] `frontend/src/components/AuthScreen.tsx` — 登录注册页面白色极简适配。
- [MODIFY] `frontend/src/App.tsx` — 整合 Modal 状态机与 `isSidebarCollapsed` 状态，传递折叠动作，替换 `confirm` 为自定义 Modal。
