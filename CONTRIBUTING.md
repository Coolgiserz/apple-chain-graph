# 贡献指南 (Contributing)

感谢你对本项目的关注。本仓库以开放协作方式维护，欢迎提交改进。

## 如何贡献

1. **Fork** 本仓库并创建特性分支：`git checkout -b feature/your-change`
2. **修改数据或脚本**：
   - 供应链数据集中在 `scripts/generate.py`（`SUPPLIERS` / `COMPONENTS` / `PRODUCTS` / `COMP_SUP` 字典）。
     请在该文件中增删条目，**不要**直接手改 `data/neo4j/*.csv`——CSV 由脚本生成。
   - 改完跑 `python3 scripts/generate.py` 重新生成 CSV 与 JSON。
3. **校验**：运行三个脚本，确认无报错且节点/关系数量符合预期（115 节点 / 510 关系）。
4. **提交 PR**：描述改动动机与数据来源；涉及供应商/份额等结论请附公开出处。

## 数据规范

- 供应商节点字段：**全称 (`name`) / 英文名称 (`english_name`) / 简称 (`short_name`)** 三者分列，不要混写。
- 产品节点：含 `release_date`(发布时间)、`status`、`price_usd` 等；别名写入 `alias`。
- ID 稳定性：内部 `id`（如 `iphone_17_pro`、`tsmc`）作为图主键，一经发布尽量保持稳定，避免破坏已有引用。
- 关系方向固定：`Product -[USES_COMPONENT]-> Component -[SUPPLIED_BY]-> Supplier`、`Product -[ASSEMBLED_BY]-> Supplier`。

## 代码约定

- 脚本仅用 Python 标准库，不引入第三方依赖。
- 路径使用相对仓库根（脚本在 `scripts/`，数据在 `data/`），不要写硬编码绝对路径。
- CSV 必须为 **UTF-8 无 BOM**，表头保留 `:ID`/`:LABEL`/`:START_ID`/`:END_ID`/`:TYPE` 标记。

## 议题 (Issues)

数据纠错、型号补充、来源讨论均欢迎开 Issue。请注明具体型号/供应商与依据。
