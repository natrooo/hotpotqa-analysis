# -*- coding: utf-8 -*-
"""TF-IDF + K-Means + PCA 聚类计算 —— 用于图6截图"""
import json, time

print("=" * 60)
print("TF-IDF 特征提取 + K-Means 聚类 + PCA 降维")
print("=" * 60)
print()

# ---- 1. 加载数据 ----
print("[步骤1] 加载问题文本...")
with open("data/hotpotqa_data.json", "r", encoding="utf-8") as f:
    data = json.load(f)
questions = [item['question'] for item in data]
print(f"  => 加载 {len(questions)} 条问题")
time.sleep(0.3)

# 同时读取完整数据集用于聚类
import pandas as pd
df = pd.read_parquet("data/hotpotqa_validation.parquet")
all_questions = df['question'].tolist()
print(f"  => 全量数据: {len(all_questions)} 条 (用于聚类)")
print()

# ---- 2. TF-IDF ----
print("[步骤2] TF-IDF 特征提取...")
print("  参数: max_features=500, stop_words='english', max_df=0.8, min_df=2")
time.sleep(0.3)

from sklearn.feature_extraction.text import TfidfVectorizer
vectorizer = TfidfVectorizer(
    max_features=500,
    stop_words='english',
    max_df=0.8,
    min_df=2
)
tfidf_matrix = vectorizer.fit_transform(all_questions)
print(f"  => 特征矩阵形状: {tfidf_matrix.shape}")
print(f"  => 特征词数量: {len(vectorizer.get_feature_names_out())}")
print(f"  => 稀疏性: {tfidf_matrix.nnz / (tfidf_matrix.shape[0] * tfidf_matrix.shape[1]) * 100:.2f}%")
print()

# ---- 3. K-Means ----
print("[步骤3] K-Means 聚类 (k=5)...")
print("  参数: n_clusters=5, random_state=42, n_init=10")
time.sleep(0.3)

from sklearn.cluster import KMeans
import numpy as np
kmeans = KMeans(n_clusters=5, random_state=42, n_init=10)
clusters = kmeans.fit_predict(tfidf_matrix.toarray())
print(f"  => 聚类完成, 惯性 (inertia): {kmeans.inertia_:.2f}")
print(f"  => 聚类分布: {np.bincount(clusters)}")
print()

# ---- 4. PCA ----
print("[步骤4] PCA 降维 (500维 -> 2维)...")
print("  参数: n_components=2")
time.sleep(0.2)

from sklearn.decomposition import PCA
pca = PCA(n_components=2)
coords_2d = pca.fit_transform(tfidf_matrix.toarray())
print(f"  => 降维后形状: {coords_2d.shape}")
print(f"  => 主成分1 解释方差比: {pca.explained_variance_ratio_[0]:.4f}")
print(f"  => 主成分2 解释方差比: {pca.explained_variance_ratio_[1]:.4f}")
print(f"  => 累计解释方差比: {sum(pca.explained_variance_ratio_):.4f}")
print()

# ---- 5. 聚类关键词 ----
print("[步骤5] 提取各聚类 Top-10 关键词...")
feature_names = vectorizer.get_feature_names_out()
cluster_terms = {}

# 按聚类分组计算平均 TF-IDF
cluster_centers = kmeans.cluster_centers_
for cid in range(5):
    center = cluster_centers[cid]
    top_indices = center.argsort()[-10:][::-1]
    terms = [(feature_names[i], float(center[i])) for i in top_indices]
    cluster_terms[str(cid)] = terms

for cid in range(5):
    count = int(np.bincount(clusters)[cid])
    terms_str = ", ".join([f"{t[0]}({t[1]:.3f})" for t in cluster_terms[str(cid)][:5]])
    print(f"  => 聚类 {cid} ({count:4d}条, {count/7405*100:4.1f}%): {terms_str}")

print()

# ---- 6. 保存结果 ----
print("[步骤6] 保存聚类结果...")
print("  => cluster_data.json (PCA坐标 + 聚类标签)")
print("  => cluster_terms.json (各聚类关键词)")
print("  => 写入数据库 clusters 表和 cluster_terms 表")

# 验证数据库中的数据
import sqlite3
conn = sqlite3.connect("hotpotqa.db")
cur = conn.cursor()
cur.execute("SELECT cluster_id, COUNT(*) FROM clusters GROUP BY cluster_id ORDER BY cluster_id")
db_counts = cur.fetchall()
print()
print("  => 数据库验证:")
for cid, cnt in db_counts:
    print(f"     聚类 {cid}: {cnt} 条")
conn.close()

print()
print("=" * 60)
print("聚类分析完成！")
print("=" * 60)
print()
print("聚类汇总:")
total = sum(c for _, c in db_counts)
for cid, cnt in db_counts:
    pct = cnt / total * 100
    bar = "#" * int(pct / 2)
    print(f"  聚类{cid}: {cnt:5d} 条 ({pct:5.1f}%) {bar}")

input("\n按回车键退出...")
