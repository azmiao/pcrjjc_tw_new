import os

import httpx
import pandas as pd

from yuiChyan.config import PROXY
from yuiChyan.resources import base_img_path
from .playerpref import sv

res_dir = os.path.join(base_img_path, 'pcrjjc_tw_new')


# 保存解包数据
async def download_file(file_name: str, file_uri: str):
    file_path = os.path.join(res_dir, file_name)
    file_url = 'https://raw.githubusercontent.com/Expugn/priconne-diff/master' + file_uri
    async with httpx.AsyncClient(proxy=PROXY) as session:
        file_rep = await session.get(file_url)
    response = file_rep.content
    # 写入文件
    with open(file_path, 'wb') as file:
        file.write(response)


# 计算实际RANK
async def read_knight_exp_rank(file_name: str, target_value: int) -> int:
    file_path = os.path.join(res_dir, file_name)
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
    # 下载数据位置文档
    await download_file(
        'sqlite_stat1.csv',
        '/TW/csv/sqlite_stat1.csv'
    )
    stat_path = os.path.join(res_dir, 'sqlite_stat1.csv')
    stat_df = pd.read_csv(stat_path)
    stat_columns = stat_df.columns.tolist()
    # 表名
    tbl = stat_columns[0]
    # 标识符
    stat = stat_columns[2]
    # 查找表名
    tbl_name = None
    for _, row in stat_df.iterrows():
        if str(row[stat]) == '201':
            tbl_name = str(row[tbl])
            break

    if not tbl_name:
        sv.logger.error('[pcrjjc_tw_new] 根据201获取不到对应PCR解包资源的表名，请反馈至Github')
        return

    # 下载实际资源
    await download_file(
        'rank_exp.csv',
        f'/TW/csv/{tbl_name}.csv'
    )
