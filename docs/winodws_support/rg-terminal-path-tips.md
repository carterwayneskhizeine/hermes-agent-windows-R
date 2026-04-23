# Hermes Windows 环境 rg 与 terminal 路径技巧

> 更新时间：2026-04-23
> 适用环境：Windows + Git Bash / WSL

---

## 核心问题：路径格式

| 工具 | 路径格式 | 示例 |
|------|----------|------|
| Windows 原生 | `D:\Doc\Folder` | ❌ 不兼容 |
| search_files / rg | `D:/Doc/Folder`（正斜杠） | ✅ 正常 |
| terminal bash | `/d/Doc/Folder`（Git Bash 风格） | ✅ 正常 |
| Python | `D:/Doc/Folder` 或 `D:\\Doc\\Folder` | ✅ 正常 |

**规则：**
- `search_files`（底层 rg）用 `D:/Doc` 格式
- `terminal` bash 命令用 `/d/Doc` 格式
- `write_file` / `patch` 工具用 `/d/Doc` 格式（实际路径转换由工具内部处理）
- ⚠️ 绝对不能用 Windows 原生反斜杠 `D:\Doc`

---

## 危险命令清单（terminal 执行会卡死）

| 命令 | 原因 | 替代方案 |
|------|------|----------|
| `find /` | 遍历整个 Linux 根目录 | 指定具体路径 |
| `find /home` | 遍历 /home，可能卡死 | 指定具体路径 |
| `ls -R /` | 递归列出根目录 | 指定具体路径 |

**通用规则：** `find` 必须指定目标路径，禁止从根目录开始搜索。

---

## search_files 工具完整用法

```bash
# 搜索文件内容
search_files(pattern="关键词", target="content", path="D:/Doc")

# 搜索文件名
search_files(pattern="*.py", target="files", path="D:/Doc")

# 限制结果数量
search_files(pattern="关键词", limit=20, path="D:/Doc")

# 输出模式
search_files(pattern="关键词", output_mode="content")  # 显示匹配行+行号
search_files(pattern="关键词", output_mode="files_only")  # 只显示文件名
search_files(pattern="关键词", output_mode="count")  # 每个文件匹配次数
```

---

## terminal 工具完整用法

```bash
# 基础命令（注意路径格式）
terminal(command="ls /d/Doc", workdir="/tmp")

# 搜索文件（禁止从根目录开始！）
terminal(command="find /d/Doc -name '*.md'")

# 获取当前工作目录
terminal(command="pwd")

# 检查文件是否存在
terminal(command="test -f /d/Doc/test.txt && echo 'exists' || echo 'not found'")

# 避免的命令
terminal(command="find / -name '*.txt'")  # ❌ 会卡死
terminal(command="ls -R /")               # ❌ 递归列出根目录
```

---

## 源代码修改建议（hermes-agent-windows-R）

### 1. 添加路径自动转换函数

```python
import re

def windows_to_bash_path(path: str) -> str:
    """将 Windows 路径转换为 Git Bash 风格路径"""
    if not path:
        return path
    
    # 已经是 Git Bash 风格
    if path.startswith('/'):
        return path
    
    # Windows 绝对路径: D:\Doc\Folder 或 D:/Doc/Folder
    match = re.match(r'^([A-Za-z]):[/\\](.*)$', path)
    if match:
        drive = match.group(1).lower()
        rest = match.group(2).replace('\\', '/')
        return f"/{drive}/{rest}"
    
    # 相对路径或其他格式
    return path.replace('\\', '/')
```

### 2. 危险命令拦截器

```python
import re

def is_dangerous_command(command: str) -> bool:
    """检查命令是否危险"""
    # 禁止从根目录执行的 find 命令
    if re.search(r'\bfind\s+(/|[/$])\b', command):
        return True
    
    # 禁止递归列出根目录
    if re.search(r'ls\s+-R\s+/', command):
        return True
    
    return False

def sanitize_and_execute(command: str, workdir: str = None) -> str:
    """安全执行命令"""
    if is_dangerous_command(command):
        raise ValueError(f"危险命令已被拦截: {command}")
    
    # 路径转换
    if workdir:
        workdir = windows_to_bash_path(workdir)
    
    # 执行...
```

### 3. rg 调用的路径预处理

```python
def rg_safe_path(path: str) -> str:
    """确保 rg 使用正斜杠路径"""
    if not path:
        return path
    # 转换为正斜杠
    return path.replace('\\', '/')
```

---

## 验证方法

```bash
# 验证路径转换
python -c "print(windows_to_bash_path('D:\\Doc\\Folder'))"
# 输出: /d/Doc/Folder

# 验证文件存在
test -f /d/Doc/20260423/test.txt && echo "OK" || echo "FAIL"

# 验证 rg 搜索
rg "关键词" /d/Doc --files | head -5
```

---

## 常见错误对照表

| 错误现象 | 原因 | 解决方法 |
|----------|------|----------|
| `find /` 卡死 | 从根目录搜索 | 指定具体路径 |
| `rg "关键词" D:\Doc` 失败 | 反斜杠路径 | 改为 `D:/Doc` |
| `terminal` 路径错误 | Windows 路径未转换 | 用 `/d/Doc` 格式 |
| 文件写入失败 | 路径格式问题 | 确认工具的路径格式 |
| `ls /home` 卡死 | 目录不存在或无权限 | 指定存在的路径 |

---

## 附加问题记录（2026-04-23）

### write_file / patch 工具在 Windows 路径下无法创建文件

**现象：** 使用 `write_file(path="D:/Doc/20260423/test.md")` 或 `patch` 工具时，文件无法创建，无错误提示但文件不存在。

**原因分析：**
- `write_file` / `patch` 工具的路径解析可能存在跨平台问题
- Windows 路径 `D:/Doc` 或 `D:\Doc` 在工具内部可能未正确映射到实际文件系统

**临时解决方案：**
1. 使用 `terminal` + Python 脚本写入文件
2. 或通过 Telegram 对话直接输出文档内容（由用户手动复制到文件）

**待解决：** 需要在 `hermes-agent-windows-R` 源码中排查 `write_file` / `patch` 的路径处理逻辑。

---

> 💡 **提示：** 在修改源码前，建议先备份原文件，并逐步验证每个路径转换函数。
> 
> 📅 **下次更新：** 待 `write_file` 路径问题修复后，补充完整的源码修改方案。
