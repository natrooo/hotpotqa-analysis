import pandas as pd

df = pd.read_parquet('data/hotpotqa_validation.parquet')

print("=" * 60)
print("HotpotQA 数据集信息")
print("=" * 60)
print()

print("数据形状 (行数, 列数):", df.shape)
print()
print("列名:", df.columns.tolist())
print()

print("=" * 60)
print("前 2 条数据预览 (图2用)")
print("=" * 60)
print()

for i in range(2):
    row = df.iloc[i]
    print(f"--- 第 {i+1} 条 ---")
    print(f"id: {row['id']}")
    print(f"question: {row['question']}")
    print(f"answer: {row['answer']}")
    print(f"type: {row['type']}")
    print(f"level: {row['level']}")
    print(f"supporting_facts titles: {row['supporting_facts']['title']}")
    print(f"context 文档数: {len(row['context']['title'])}")
    print()

print("=" * 60)
print("数据统计 (图5用)")
print("=" * 60)
print()
print("类型分布:")
print(df['type'].value_counts())
print()
print("难度分布:")
print(df['level'].value_counts())
print()
print("总数据量:", len(df))
print()

input("按回车键退出...")
