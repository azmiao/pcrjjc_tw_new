import json
import os

import pandas as pd
from hoshino import aiorequests, R, logger

current_dir = R.img('pcrjjc_tw_new').path

# 读取代理配置
with open(os.path.join(os.path.dirname(__file__), 'account.json')) as fp:
    p_info = json.load(fp)


# 保存解包数据
async def download_file(file_name: str, file_uri: str):
    file_path = os.path.join(current_dir, file_name)
    file_url = 'https://raw.githubusercontent.com/Expugn/priconne-diff/master' + file_uri
    file_rep = await aiorequests.get(file_url, proxies=p_info['proxy'])
    response = await file_rep.content
    # 写入文件
    with open(file_path, 'wb') as file:
        file.write(response)


# 计算实际RANK
async def read_knight_exp_rank(file_name: str, target_value: int) -> int:
    file_path = os.path.join(current_dir, file_name)
    df = pd.read_csv(file_path)

    # 自动识别exp和rank列
    columns = df.columns.tolist()

    # 假设数据第一行用来识别 exp 列，通过 第一个数据为 0 判断
    if df.iloc[0][columns[0]] == 0:
        exp, rank = columns[0], columns[1]
    else:
        exp, rank = columns[1], columns[0]

    # 转换为 int，以提高计算效率
    df[exp] = df[exp].astype(int)
    df[rank] = df[rank].astype(int)

    target_rank = 1
    # 查找满足条件的目标 rank
    for _, row in df.iterrows():
        if target_value >= row[exp]:
            target_rank = row[rank]
        else:
            break
    return target_rank


# 更新解包资源
async def updateData():
    # 下载实际资源
    await download_file(
        'rank_exp.csv',
        f'/TW/csv/v1_ffa6d387cc127d4080b8b48c77f52257c4f5265d0c9b3d92b997bf10bc862642.csv'
    )
