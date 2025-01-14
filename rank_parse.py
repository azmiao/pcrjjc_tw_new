import os

import pandas as pd


# 强行计算 | 有点无语，虽然301级之前能用，但后续维护太折磨了
async def calculate_rank(experience: int) -> (bool, int):
    # 计算等级 1 到 125
    base_experience = 53235

    # 等级1到125
    if experience < base_experience * 125:
        level = experience // base_experience
        return True, level + 1

    # 等级126到201
    experience -= base_experience * 124
    base_experience = 53236
    if experience < base_experience * 76:
        level = experience // base_experience
        return True, level + 125

    # 等级202及以上
    experience -= base_experience * 76
    level = 201
    next_experience = 111076
    # 定义增量规则
    experience_increments = {
        range(202, 217): 505,
        range(217, 251): 500,
        range(251, 252): 476,
        range(252, 256): 474,
        range(256, 257): 475,
        range(257, 289): 476,
        range(289, 290): 475,
        range(290, 294): 476,
        range(294, 296): 475,
        range(296, 297): 477,
        range(297, 299): 476,
        range(299, 300): -22335,
        range(300, 302): 471
    }

    while experience >= next_experience:
        experience -= next_experience
        level += 1
        increment = next((_value for _key, _value in experience_increments.items() if level in _key), None)
        if not increment:
            return False, 301
        next_experience += increment
        # print(f'> current level {level} remain exp {experience} | {level} -> {level + 1} need : {next_experience}')
    return True, level



# 计算实际RANK
async def query_knight_exp_rank(target_value: int) -> int:
    success, rank = await calculate_rank(target_value)
    if success:
        return rank

    file_path = os.path.join(os.path.dirname(__file__), 'rank_exp.csv')
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
