# HotpotQA 多跳问答探索器

基于 [hotpotqa/hotpot_qa](https://huggingface.co/datasets/hotpotqa/hotpot_qa) 的多跳问答数据管理系统与可视化网站，可部署到 GitHub Pages。

## 数据库选型

| 组件 | 技术 | 用途 |
|------|------|------|
| 主库 | SQLite + FTS5 | 导入 HF 数据、全文检索、多跳事实与段落关联 |
| 发布层 | JSON 静态文件 | GitHub Pages 无后端，浏览器端检索与可视化 |
| 可选扩展 | DuckDB + hf:// parquet | 对全量数据做 SQL 分析（见 [Hugging Face datasets SQL](https://huggingface.co/docs/datasets-server/sql_console)） |

选择 SQLite 的原因：单文件、零运维、支持 FTS5 与关系查询，适合 HotpotQA 的「问题—段落—支撑事实」层级结构。

## 功能

- **多跳检索**：Fuse.js 模糊搜索 + 按 type / level / 聚类过滤
- **多跳可视化**：根据 supporting_facts 构建 Question → Hop1 → Hop2 → Answer 推理图（vis-network）
- **简单聚类**：对问题文本做 TF-IDF + K-Means（k=6），散点图与柱状图（Chart.js）
- **上下文浏览**：展示 distractor 设置下的段落与支持句
- **统计分析**：类型分布环形图、聚类大小柱状图、聚类-类型堆叠柱状图

## 数据集

- **配置**：distractor + validation（含答案与支持事实，适合演示）
- **数据量**：7,405 条多跳问答对
- **多跳类型**：bridge（桥接推理，79.9%）与 comparison（比较推理，20.1%）
- **难度级别**：hard（HotpotQA 验证集全部为困难级别）
- **supporting_facts** 中的 (title, sent_id) 表示跨段落推理链上的关键句

## 目录结构

```
hotpotqa-project/
├── app.py                    # Flask Web 应用（搜索、聚类、统计 API）
├── show_data_info.py         # 数据集信息展示脚本
├── verify_import.py          # 数据导入验证脚本
├── run_clustering.py         # TF-IDF + K-Means + PCA 聚类计算
├── generate_report.py        # 实验报告自动生成脚本
├── hotpotqa.db               # SQLite 数据库（questions / contexts / sentences / clusters）
├── data/
│   ├── hotpotqa_validation.parquet  # 原始 Parquet 数据
│   ├── hotpotqa_data.json          # 500 条采样数据（Web 搜索用）
│   ├── cluster_data.json           # 7405 条聚类结果（PCA 坐标 + 标签）
│   ├── cluster_terms.json          # 各聚类 Top-10 关键词
│   ├── questions.json              # 500 条问题摘要
│   └── stats.json                  # 数据集统计信息
├── templates/
│   └── index.html                  # Web 前端页面
└── index.html                      # GitHub Pages 入口页
```

## 本地运行

```bash
# 1. 查看数据集信息
python show_data_info.py

# 2. 运行聚类计算（TF-IDF + K-Means + PCA）
python run_clustering.py

# 3. 验证数据导入情况
python verify_import.py

# 4. 启动 Flask Web 应用
python app.py
# 打开 http://127.0.0.1:5000
```

## 部署到 GitHub Pages

1. 将本仓库推送到 GitHub
2. Settings → Pages → Build and deployment 选择 **GitHub Actions**（或直接从分支部署）
3. 站点地址：`https://<username>.github.io/<repo>/`

在线演示：**[https://natrooo.github.io/hotpotqa-analysis/](https://natrooo.github.io/hotpotqa-analysis/)**

## 数据导入说明

### 从 Hugging Face Dataset Viewer API 导入

```bash
# 默认 distractor / validation，约 7405 条
python scripts/import_data.py

# 若出现 504/429 超时，用断点续传（不要删掉 db/hotpotqa.db）：
python scripts/import_data.py --resume

# 网络不稳定时可减小批次、加大间隔：
python scripts/import_data.py --resume --page-size 25 --delay 1.0

# 可选：限制条数、更换划分
python scripts/import_data.py --config distractor --split train --limit 500
```

### 数据预处理流程

1. 从 HuggingFace API 下载 Parquet 文件（约 45 MB）
2. 使用 pandas + pyarrow 读取 Parquet 格式
3. 遍历嵌套结构，展开 context 数组和 sentences 数组
4. 每 2,000 条提交一次事务，导入 SQLite
5. 创建 FTS5 全文索引，支持高效关键词检索

## 技术栈

| 层面 | 技术 |
|------|------|
| 后端 | Python / Flask / SQLite3 |
| 前端 | HTML5 / CSS3 / Chart.js / Canvas API |
| 数据处理 | pandas / scikit-learn (TF-IDF, K-Means, PCA) |
| 部署 | GitHub Pages |

## 引用

```bibtex
@inproceedings{yang2018hotpotqa,
  title={HotpotQA: A Dataset for Diverse, Explainable Multi-hop Question Answering},
  author={Zhilin Yang and Peng Qi and Saizheng Zhang and others},
  booktitle={EMNLP},
  year={2018}
}
```
