import json
import os
from asyncio import Lock
from typing import Optional, TYPE_CHECKING

import zhconv

from yuiChyan import CQEvent, base_img_path
from yuiChyan.config import PROXY
from yuiChyan.exception import CommandErrorException
from yuiChyan.http_request import get_session_or_create
from .player_pref import decrypt_xml

if TYPE_CHECKING:
    from .pcr_client import PcrClient

# 资源文件夹
res_dir = os.path.join(base_img_path, 'pcrjjc_tw_new')
os.makedirs(res_dir, exist_ok=True)
# 当前目录
current_path: str = os.path.dirname(__file__)
# 默认绑定配置
default_config: dict[str, bool | dict] = {
    'global_push': True,
    'arena_bind': {}
}
# 绑定配置文件
config_path: str = os.path.join(current_path, 'binds_v2.json')
# 默认headers
default_headers: dict[str, str]= {
    'Accept': '*/*',
    'Accept-Encoding': 'deflate, gzip',
    'User-Agent': 'UnityPlayer/2021.3.27f1 (UnityWebRequest/1.0, libcurl/7.84.0-DEV)',
    'Content-Type': 'application/octet-stream',
    'X-Unity-Version': '2021.3.27f1',
    'APP-VER': '4.9.0',
    'BATTLE-LOGIC-VERSION': '4',
    'DEVICE': '2',
    'DEVICE-ID': '1e4a1b03d1b6cd8a174a826f76e009f4',
    'DEVICE-NAME': 'Xiaomi MI 9',
    'GRAPHICS-DEVICE-NAME': 'Adreno (TM) 640',
    'IP-ADDRESS': '10.0.2.15',
    'LOCALE': 'Jpn',
    'PLATFORM-OS-VERSION': 'Android OS 14 / API-34 (UKQ1.231003.002/V816.0.14.0.UFACNXM)',
    'RES-VER': '00420009'
}
# headers配置文件
header_path: str = os.path.join(current_path, 'headers.json')
# 竞技场排名的缓存
rank_cache: dict[str, tuple[int, int]] = {}
# 查询异步锁
query_lock: Lock = Lock()
# 全局缓存的PCR客户端
first_client_cache: Optional['PcrClient'] = None
other_client_cache: Optional['PcrClient'] = None


# 检验UID
async def judge_uid(uid_str: str, ev: CQEvent):
    # 校验数字
    try:
        int(uid_str)
    except TypeError or ValueError:
        raise CommandErrorException(ev, f'uid错误，需要10位纯数字，您输入了[{str(uid_str)}]')

    if len(uid_str) != 10:
        raise CommandErrorException(ev, f'uid长度错误，需要10位数字，您输入了[{str(len(uid_str))}]位数')

    # 校验服务器
    cx = uid_str[:1]
    if cx not in ['1', '2', '3', '4']:
        raise CommandErrorException(ev, f'uid校验出错，第一位数字为原始服务器ID，只能为1/2/3/4，您输入了[{str(uid_str)}]')


# 读取绑定配置
async def get_binds_config() -> dict[str, bool | dict]:
    if not os.path.isfile(config_path):
        # 没有文件 | 创建
        with open(config_path, 'w', encoding='utf-8') as _f:
            # noinspection PyTypeChecker
            json.dump(_f, default_config, indent=4, ensure_ascii=False)
        config = default_config
    else:
        # 有文件 | 读取
        with open(config_path, 'r', encoding='utf-8') as _f:
            config = json.load(_f)
    return config


# 保存绑定配置
async def save_binds_config(config: dict):
    with open(config_path, 'w', encoding='utf-8') as _f:
        # noinspection PyTypeChecker
        json.dump(_f, config, indent=4, ensure_ascii=False)


# 查询PCR客户端配置
async def get_client_config(cx_id: int) -> Optional[str]:
    cx = 'first' if cx_id == 1 else 'other'
    cx_path = os.path.join(current_path, f'{cx}_tw.sonet.princessconnect.v2.playerprefs.xml')
    return cx_path if os.path.isfile(cx_path) else None


# 获取PCR客户端
async def get_client() -> (Optional['PcrClient'], Optional['PcrClient']):
    global first_client_cache, other_client_cache

    # 1服
    if first_client_cache is None and await get_client_config(1):
        ac_info_first = decrypt_xml(await get_client_config(1))
        _async_session = get_session_or_create('PcrClientFirst', True, PROXY)
        first_client_cache = PcrClient(
            ac_info_first['UDID'],
            ac_info_first['SHORT_UDID'],
            ac_info_first['VIEWER_ID'],
            ac_info_first['TW_SERVER_ID'],
            _async_session
        )

    # 其他服
    if other_client_cache is None and await get_client_config(5):
        ac_info_other = decrypt_xml(await get_client_config(5))
        _async_session = get_session_or_create('PcrClientOther', True, PROXY)
        first_client_cache = PcrClient(
            ac_info_other['UDID'],
            ac_info_other['SHORT_UDID'],
            ac_info_other['VIEWER_ID'],
            ac_info_other['TW_SERVER_ID'],
            _async_session
        )

    return first_client_cache, other_client_cache


# 读取headers绑定配置
def get_headers_config() -> dict[str, str]:
    if not os.path.isfile(header_path):
        # 没有文件 | 创建
        with open(header_path, 'w', encoding='utf-8') as _f:
            # noinspection PyTypeChecker
            json.dump(_f, default_headers, indent=4, ensure_ascii=False)
        header_config = default_headers
    else:
        # 有文件 | 读取
        with open(header_path, 'r', encoding='utf-8') as _f:
            header_config = json.load(_f)
    return header_config


# 启动生成headers
get_headers_config()


# 保存headers配置文件
def save_headers_config(header_config: dict[str, str]):
    with open(header_path, 'w', encoding='utf-8') as _f:
        # noinspection PyTypeChecker
        json.dump(_f, header_config, indent=4, ensure_ascii=False)


# 更新headers的版本号
def update_headers_with_version(version: str):
    # 更新headers配置的版本
    headers_config = get_headers_config()
    headers_config['APP-VER'] = version
    save_headers_config(headers_config)

    # 更新缓存的版本
    global first_client_cache, other_client_cache
    if first_client_cache:
        first_client_cache.update_version(version)
    if other_client_cache:
        other_client_cache.update_version(version)


# 获取服务器名称
def get_cx_name(cx):
    match cx:
        case '1':
            cx_name = '美食殿堂'
        case '2':
            cx_name = '真步王国'
        case '3':
            cx_name = '破晓之星'
        case '4':
            cx_name = '小小甜心'
        case _:
            cx_name = '未知'
    return cx_name


# 由繁体转化为简体
def traditional_to_simplified(zh_str: str) -> str:
    return zhconv.convert(str(zh_str), 'zh-hans')


# 按步长分割字符串
def cut_str(obj: str, sec: int) -> list[str]:
    return [obj[i: i + sec] for i in range(0, len(obj), sec)]
