import json
import os

import pandas as pd
from hoshino import aiorequests, R

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
    columns = df.columns.tolist()

    rank = columns[0]
    exp = columns[1]

    target_rank = 1

    for _, row in df.iterrows():
        if target_value >= int(row[exp]):
            target_rank = int(row[rank])
        else:
            break
    return target_rank
