# 数据模型与字段字典

本图谱由三类节点 + 三类关系构成，反映苹果产品供应链的上下游传导：

```
Product ──USES_COMPONENT──▶ Component ──SUPPLIED_BY──▶ Supplier
Product ──ASSEMBLED_BY──▶ Supplier(代工)
```

- 节点标签：`Product` / `Component` / `Supplier`
- 关系类型：`USES_COMPONENT` / `SUPPLIED_BY` / `ASSEMBLED_BY`

> 说明：`product_id` / `component_id` / `supplier_id` 是图内部主键（neo4j-admin 离线导入时作为
> 元素 ID；用 LOAD CSV 在线导入时会同时存为节点属性）。查询优先用 `name` 等真实属性匹配更稳妥。

---

## Product（产品型号）

| 字段 | 含义 | 可获取性 |
|------|------|----------|
| `product_id` | 节点唯一 ID（图数据库主键） | 内部生成，稳定唯一 |
| `name` | 官方型号全称（节点名称，如 iPhone 17 Pro） | 苹果官方发布名称，公开可得 |
| `product_line` | 产品线大类（iPhone / Mac / iPad / Wearable / Spatial / Audio） | 苹果产品分类，公开可得 |
| `english_name` | 英文名称 | 苹果全球统一命名，公开可得 |
| `alias` | 别名 / 内部代号（如 iPhone 17 Slim、Apple Watch X） | 发布前代号或别称，部分公开可得，无则空 |
| `release_date` | 发布时间（发布/发售日期，ISO 格式；未确认者标注年份） | 发布会与发售日期，公开可得 |
| `release_year` | 发布年份（便于按年聚合） | 由发布时间派生 |
| `status` | 在售 / 停产 / 传闻未发布 | 苹果在售列表，公开可得 |
| `soc` | 主芯片型号（A/M 系列） | 苹果芯片命名，公开可得 |
| `display` | 显示规格摘要 | 规格公开，供应商为定性 |
| `price_usd` | 起售价（美元） | 苹果全球定价，公开可得 |

## Component（零部件）

| 字段 | 含义 | 可获取性 |
|------|------|----------|
| `component_id` | 节点唯一 ID | 内部生成 |
| `name` | 中文全称（节点名称） | BOM 拆解命名，公开可得 |
| `english_name` | 英文名称 | 行业通用英文术语，公开可得 |
| `category` | 零部件大类 | 按功能分类，可定义 |
| `subcategory` | 子类 / 规格说明 | BOM 拆解，公开可得 |

## Supplier（供应商 / 代工厂）

| 字段 | 含义 | 可获取性 |
|------|------|----------|
| `supplier_id` | 节点唯一 ID | 内部生成 |
| `name` | 全称（法定注册名，节点名称） | 公司注册信息，公开可得 |
| `english_name` | 英文名称 | 公司官方英文名，公开可得 |
| `short_name` | 简称 / 股票代码 / 常用缩写（如 TSMC、京东方） | 市场惯用简称，公开可得 |
| `country` | 总部所在国家/地区 | 公开可得 |
| `region` | 大区（东亚 / 北美 / 欧洲） | 由 country 派生 |
| `category` | 供应类别（代工 / 显示 / 存储 / 半导体 …） | 按业务分类，可定义 |
| `tier` | 层级（1 = 核心/高壁垒，2 = 次级/可替代） | 依据技术壁垒与可替代性评估 |

## Relationship（关系）

| 关系 | 方向 | 含义 | 可获取性 |
|------|------|------|----------|
| `USES_COMPONENT` | Product → Component | 产品使用某零部件 | BOM 拆解，公开可得 |
| `SUPPLIED_BY` | Component → Supplier | 零部件由某供应商供货（含 `share` 份额、`note` 备注） | 供应链报道，份额仅个别环节量化 |
| `ASSEMBLED_BY` | Product → Supplier | 产品由某代工厂组装 | 苹果供应链名单，公开可得 |

### 关系属性

- `SUPPLIED_BY` 带两个属性：
  - `share`：供货份额（仅对公开披露较明确的少数环节标注，如 MacBook 面板 BOE 51%、DRAM 三星约 60–70%；其余为空）。
  - `note`：备注（如制程节点、二供状态等）。

---

## 示例查询

```cypher
-- 某型号完整上游链（注意箭头方向）
MATCH (p:Product {name:'iPhone 17 Pro'})-[:USES_COMPONENT]->(c:Component)-[:SUPPLIED_BY]->(s:Supplier)
RETURN p.name, c.name, s.short_name, s.country
LIMIT 25;

-- 某供应商供应了哪些零部件
MATCH (s:Supplier)-[:SUPPLIED_BY]->(c:Component)
WHERE s.name CONTAINS '台积电'
RETURN s.name, c.name;

-- 按发布时间看产品时间线
MATCH (p:Product)
RETURN p.release_date AS 发布时间, p.name AS 型号, p.product_line AS 产品线,
       p.price_usd AS 起售价, p.status AS 状态
ORDER BY p.release_date;
```
