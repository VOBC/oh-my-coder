# 🧬 GEP 协议支持 (WIP)

> 本文从 README.md 迁移而来。

## 🧬 GEP 协议支持 (WIP)

基于 EvoMap GEP 协议，将能力包升级为可注册、可发现、可互通的标准格式。

### 核心概念

| 概念 | 说明 |
|------|------|
| **Gene** | 能力元数据（UUID、名称、分类、标签、描述、版本） |
| **Capsule** | 完整能力包（Gene + manifest 配置 + 依赖 + SHA256 校验） |
| **GEPRegistry** | 本地注册表（register / discover / resolve / export_event） |

### .omcp 向后兼容

旧 `.omcp` 格式自动升级为 Capsule：
- 有 `gene` 字段 → 直接使用
- 无 `gene` 字段 → 根据文件名和内容推断虚拟 Gene（向后兼容）

### GEP Event 格式

```json
{
  "type": "GEP/Register",
  "version": "1.0",
  "payload": {
    "gene": { "id": "...", "name": "...", "category": "..." },
    "manifest": { "tools": [...], "agents": {...} },
    "dependencies": [...],
    "checksum": "..."
  }
}
```

---

