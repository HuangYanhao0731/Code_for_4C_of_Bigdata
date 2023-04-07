import pandas as pd

df = pd.read_excel('2021.06异常商品数据.xlsx')
df.insert(1, 'year', 2023)
df.insert(2, 'month', 2)
df.to_excel('data.xlsx', index=False)