# 苹果供应链图谱 — 导入你已有的 Neo4j 实例（详细教程）

> 本文件夹里的 6 个 CSV 是 **Neo4j 官方批量导入格式（neo4j-admin 格式）**，
> 已在 Neo4j 5.26 实测通过：**115 节点 / 510 关系 / 976 属性，零报错**。
> - 节点：Product 28 · Component 27 · Supplier 60
> - 关系：USES_COMPONENT 396 · SUPPLIED_BY 77 · ASSEMBLED_BY 37
>
> 数据模型三层：
> `Product -[USES_COMPONENT]-> Component -[SUPPLIED_BY]-> Supplier`
> 另有 `Product -[ASSEMBLED_BY]-> Supplier`（整机组装/代工）

---

## 0. 先选一种导入方式

| 方式 | 适用场景 | 是否需要停库 | 难度 |
|------|----------|--------------|------|
| **A. neo4j-admin 离线批量导入** | 想建一个**全新的数据库**专门放这份图谱 | **需要**（目标库必须离线） | 低，一条命令 |
| **B. LOAD CSV 在线导入（Cypher）** | 想直接导入**正在运行的现有库**（比如你默认的 `neo4j` 库） | **不需要**，库照常运行 | 中，需跑一段 Cypher |

- 想要"干净独立的新库" → 走 **A**。
- 想"不动现有库、直接加进去" → 走 **B**。

---

## 1. 文件夹里的 6 个文件（导入用）

```
data/neo4j/
├── products.csv              产品型号节点（28 行）
├── components.csv            零部件节点（27 行）
├── suppliers.csv            供应商/代工厂节点（60 行）
├── rel_product_component.csv   关系：产品→零部件（396 行）
├── rel_component_supplier.csv 关系：零部件→供应商（77 行）
└── rel_product_assembly.csv   关系：产品→代工厂（37 行）
```

各文件表头（这就是 neo4j-admin 格式，关系文件里的 `:TYPE` 列可忽略，关系类型我们在导入时写死）：

```
products.csv              : product_id:ID(Product),name,product_line,english_name,alias,release_date,release_year:int,status,soc,display,price_usd:int,:LABEL
components.csv            : component_id:ID(Component),name,english_name,category,subcategory,:LABEL
suppliers.csv            : supplier_id:ID(Supplier),name,english_name,short_name,country,region,category,tier:int,:LABEL
rel_product_component.csv: :START_ID(Product),:END_ID(Component),:TYPE
rel_component_supplier.csv: :START_ID(Component),:END_ID(Supplier),:TYPE,share,note
rel_product_assembly.csv : :START_ID(Product),:END_ID(Supplier),:TYPE
```

---

## 2. 方式 A：neo4j-admin 离线批量导入（建新库）

### 2.1 停掉目标数据库
`neo4j-admin` 是**离线**导入，目标库必须停止：
- **Neo4j Desktop**：在左侧数据库条目上点 **Stop**。
- **服务版（systemd）**：`sudo systemctl stop neo4j`
- **tar 包**：进入 `<neo4j-home>/bin` 执行 `./neo4j stop`
- 仅想要"新建一个独立库"时，也可只停那个具体库、不动默认库。

### 2.2 运行导入命令
用**你这台机器上那个 Neo4j 的 `neo4j-admin`**（确保 PATH 指向它，或 `cd` 到它的 `bin` 目录）。
把下面 `CSV_DIR` 换成你本机这个 `data/neo4j/` 文件夹的**绝对路径**。

```bash
CSV_DIR="/你的绝对路径/apple_supply_chain/data/neo4j"   # ← 改成你机器上的真实路径

neo4j-admin database import full apple-supply-chain \
  --nodes="$CSV_DIR/products.csv" \
  --nodes="$CSV_DIR/components.csv" \
  --nodes="$CSV_DIR/suppliers.csv" \
  --relationships="$CSV_DIR/rel_product_component.csv" \
  --relationships="$CSV_DIR/rel_component_supplier.csv" \
  --relationships="$CSV_DIR/rel_product_assembly.csv" \
  --overwrite-destination
```

> 也可以用文件夹里现成的脚本（它同样直接读本文件夹 CSV，不依赖 import 目录）：
> `bash data/neo4j/import_admin.sh apple-supply-chain`（库名可自定义）。

看到 `IMPORT DONE` 且节点/关系数与开头一致即成功。

### 2.3 启动并注册（若库未在列表出现）
Desktop 里点 **Start**；服务版 `sudo systemctl start neo4j`。
若 Browser 里没自动出现新库，执行一次：
```cypher
CREATE DATABASE apple-supply-chain;
```

---

## 3. 方式 B：LOAD CSV 在线导入（导入正在运行的现有库）

这种方式把 CSV 放进 Neo4j 的 **import 目录**，再用 Cypher 一段段读入。
**库全程不用停。**

### 3.1 找到你的 import 目录
在 Neo4j Browser 里执行，直接打印路径：
```cypher
CALL dbms.listConfig('server.directories.import');   -- Neo4j 5.x
-- 若是 4.x 用：CALL dbms.listConfig('dbms.directories.import');
```
常见默认位置：
- **Neo4j Desktop（Mac）**：`~/Library/Application Support/Neo4j Desktop/Application/neo4jDatabases/<dbId>/installation/neo4j/import/`
- **Neo4j Desktop（Windows）**：`%APPDATA%\Neo4j Desktop\Application\neo4jDatabases\<dbId>\installation\neo4j\import\`
- **服务版 tar 包**：`<neo4j-home>/import/`
- **Linux apt/deb 安装**：`/var/lib/neo4j/import/`
- **Neo4j Aura（云）**：本地文件方式不适用，见文末说明。

### 3.2 拷贝 CSV
把这 6 个文件**原样**复制到上面的 import 目录里（不要改名）。
之后在 Browser 里用 `file:///文件名.csv` 引用。

### 3.3 在 Browser 里依次执行这段 Cypher
> 注意：关系 CSV 的表头是 `:START_ID(Product)` 这种带冒号的列名，
> 在 Cypher 里必须用**反引号**当列名引用，例如 `row.`:START_ID(Product)``。

```cypher
// 1) 产品节点
LOAD CSV WITH HEADERS FROM 'file:///products.csv' AS row
MERGE (p:Product {product_id: row.`product_id:ID(Product)`})
SET p.name=row.name, p.product_line=row.product_line, p.english_name=row.english_name,
    p.alias=row.alias, p.release_date=row.release_date,
    p.release_year=toInteger(row.release_year), p.status=row.status,
    p.soc=row.soc, p.display=row.display, p.price_usd=toInteger(row.price_usd);

// 2) 零部件节点
LOAD CSV WITH HEADERS FROM 'file:///components.csv' AS row
MERGE (c:Component {component_id: row.`component_id:ID(Component)`})
SET c.name=row.name, c.english_name=row.english_name,
    c.category=row.category, c.subcategory=row.subcategory;

// 3) 供应商节点
LOAD CSV WITH HEADERS FROM 'file:///suppliers.csv' AS row
MERGE (s:Supplier {supplier_id: row.`supplier_id:ID(Supplier)`})
SET s.name=row.name, s.english_name=row.english_name, s.short_name=row.short_name,
    s.country=row.country, s.region=row.region,
    s.category=row.category, s.tier=toInteger(row.tier);

// 4) 关系：产品 → 零部件
LOAD CSV WITH HEADERS FROM 'file:///rel_product_component.csv' AS row
MATCH (p:Product {product_id: row.`:START_ID(Product)`})
MATCH (c:Component {component_id: row.`:END_ID(Component)`})
MERGE (p)-[:USES_COMPONENT]->(c);

// 5) 关系：零部件 → 供应商（含份额/备注属性）
LOAD CSV WITH HEADERS FROM 'file:///rel_component_supplier.csv' AS row
MATCH (c:Component {component_id: row.`:START_ID(Component)`})
MATCH (s:Supplier {supplier_id: row.`:END_ID(Supplier)`})
MERGE (c)-[:SUPPLIED_BY {share: row.share, note: row.note}]->(s);

// 6) 关系：产品 → 代工厂
LOAD CSV WITH HEADERS FROM 'file:///rel_product_assembly.csv' AS row
MATCH (p:Product {product_id: row.`:START_ID(Product)`})
MATCH (s:Supplier {supplier_id: row.`:END_ID(Supplier)`})
MERGE (p)-[:ASSEMBLED_BY]->(s);
```

> 数据量大（数十万行）时，每段 `LOAD CSV` 前加
> `CALL { LOAD CSV ... } IN TRANSACTIONS OF 2000 ROWS;` 以防内存溢出。
> 本数据集仅 510 行，直接跑即可。

每段执行后 Browser 会显示 "Added N labels, created M relationships" 之类，全部跑完即完成。

---

## 4. 导入后验证（两种方式通用）

在 Browser 里跑：
```cypher
-- 节点/关系总数核对
MATCH (n) RETURN labels(n)[0] AS 标签, count(*) AS 数量 ORDER BY 数量 DESC;
MATCH ()-[r]->() RETURN type(r) AS 关系, count(*) AS 数量 ORDER BY 数量 DESC;

-- 示例：iPhone 17 Pro 的完整供应链（注意箭头方向）
MATCH (p:Product {name:'iPhone 17 Pro'})-[:USES_COMPONENT]->(c:Component)-[:SUPPLIED_BY]->(s:Supplier)
RETURN p.name, c.name AS 零部件, s.short_name AS 供应商, s.country AS 国家
LIMIT 25;

-- 示例：台积电供应了哪些零部件
MATCH (s:Supplier)-[:SUPPLIED_BY]->(c:Component)
WHERE s.name CONTAINS '台积电'
RETURN s.name, c.name;
```

期望结果：标签计数 Product 28 / Component 27 / Supplier 60；
关系计数 USES_COMPONENT 396 / SUPPLIED_BY 77 / ASSEMBLED_BY 37。

> 关系方向固定为：
> `Product -[USES_COMPONENT]-> Component -[SUPPLIED_BY]-> Supplier`
> `Product -[ASSEMBLED_BY]-> Supplier`
> （早期示例里曾把箭头写反，数据本身没问题。）

---

## 5. 常见问题排查

| 报错 | 原因 | 解决 |
|------|------|------|
| `22N43: unable to load external resource file:///products.csv` | LOAD CSV 找不到文件 | 文件没放进 import 目录；或路径写错。放到 `import/` 后用 `file:///products.csv` |
| `Unable to find the parent of the path: products.csv` | neo4j-admin 收到**裸文件名** | 必须用**绝对路径**（见 2.2） |
| `22N77: property presence verification failed ... must have product_id:ID(Product)` | 节点 CSV 与关系 CSV 的 ID 分组**版本不一致**（旧匿名 `:ID` 混进了新带标签 `:ID(Product)`） | 保证 6 个文件**都是同一套**（本文件夹现版已自洽）；不要混入旧文件 |
| `22N31 / 22G03: MERGE cannot be used with null` | LOAD CSV 把整列表头 `product_id:ID(Product)` 当成列名，`row.product_id` 取到 null | 用反引号字面列名：`row.`product_id:ID(Product)``（见 3.3） |
| `Couldn't load external resource` | CSV 含 BOM 或编码非 UTF-8 | 确认是 UTF-8 无 BOM（本文件夹文件已是） |

---

## 6. 数据字段字典

**Product（产品型号）**
`product_id`(内部ID) · `name`(型号名) · `product_line`(产品线：iPhone/Mac/iPad/...) ·
`english_name` · `alias`(别名) · `release_date`(发布日期) · `release_year`(年份) ·
`status`(在售/停产) · `soc`(芯片) · `display`(屏幕) · `price_usd`(起售价)

**Component（零部件）**
`component_id`(内部ID) · `name` · `english_name` · `category`(大类) · `subcategory`(子类)

**Supplier（供应商/代工厂）**
`supplier_id`(内部ID) · `name`(全称) · `english_name` · `short_name`(简称) ·
`country` · `region`(地区) · `category`(角色：芯片/面板/代工…) · `tier`(层级)

**关系属性**
`SUPPLIED_BY` 带 `share`(供货份额) 与 `note`(备注)。

---

## 7. 关于 Neo4j Aura（云实例）

Aura 不支持直接 `file:///` 导入本地 CSV。可选路径：
1. 本地用 neo4j-admin 导入成一个**本地 Neo4j 5 库**（方式 A），再用
   `neo4j-admin database upload <db> <aura-connection-uri>` 推送到 Aura（需 Aura 企业/专业版）；
2. 或在 Aura 控制台用官方 **Data Importer** 上传这 6 个 CSV（界面化映射，按本教程的表头含义拖字段即可）。

---

### 想让我再给你一份"复制粘贴即跑"的精确命令？
告诉我三件事，我可以把命令写成你机器上能直接执行的版本：
1. 你的 Neo4j 版本（4.x 还是 5.x）；
2. 是 Neo4j Desktop、本地服务版，还是 Aura；
3. 想用方式 A（新建库）还是方式 B（加进现有运行库）。
