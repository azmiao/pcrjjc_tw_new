import os
import numpy as np
import pandas as pd

# 缓存优化后的数据结构
_cached_data = None
_cached_time = 0


def _normalize_cell(value) -> str:
    return str(value).strip().strip('"').strip("'")


# 加载优化后的数据
async def load_optimized_data():
    global _cached_data, _cached_time
    current_path = os.path.dirname(__file__)
    file_path = os.path.join(current_path, 'rank_exp.csv')

    current_time = os.path.getmtime(file_path)
    if _cached_data is None or current_time > _cached_time:
        # 先按字符串读取，基于“标题行后第一行”的固定值判断列含义
        df_raw = pd.read_csv(file_path, dtype=str)
        if df_raw.empty or len(df_raw.columns) < 2:
            raise ValueError('rank_exp.csv 数据异常，无法识别经验和RANK列')

        first_row = df_raw.iloc[0]
        rank_col = None
        exp_col = None
        for col in df_raw.columns:
            cell = _normalize_cell(first_row[col])
            if rank_col is None and cell == '1':
                rank_col = col
                continue
            if exp_col is None and cell == '0':
                exp_col = col

        # 兜底：若首行识别失败，按数值列的最大值推断经验列
        if rank_col is None or exp_col is None or rank_col == exp_col:
            numeric_df = df_raw.apply(pd.to_numeric, errors='coerce')
            numeric_cols = [col for col in numeric_df.columns if numeric_df[col].notna().any()]
            if len(numeric_cols) < 2:
                raise ValueError('rank_exp.csv 无法推断经验和RANK列')
            exp_col = max(numeric_cols, key=lambda _col: numeric_df[_col].max())
            rank_col = next(col for col in numeric_cols if col != exp_col)

        df = df_raw.copy()
        df[exp_col] = pd.to_numeric(df[exp_col], errors='coerce')
        df[rank_col] = pd.to_numeric(df[rank_col], errors='coerce')
        df = df.dropna(subset=[exp_col, rank_col])

        # 预处理排序
        df = df.sort_values(by=exp_col, ascending=True).reset_index(drop=True)
        _cached_data = {
            'exp': df[exp_col].values.astype(np.int64),
            'rank': df[rank_col].values.astype(np.int64),
            'min_exp': df[exp_col].min(),
            'max_exp': df[exp_col].max()
        }
        _cached_time = current_time

    return _cached_data


# 计算实际RANK
async def query_knight_exp_rank(target_value: int) -> int:
    data = await load_optimized_data()

    # 边界检查
    if target_value >= data['max_exp']:
        return data['rank'][-1]
    if target_value < data['min_exp']:
        return data['rank'][0]

    # 二分查找核心逻辑
    idx = np.searchsorted(data['exp'], target_value, side='right') - 1
    return data['rank'][idx]
