import json
import time
from asyncio import Lock
from copy import deepcopy
from json import load, dump
from os.path import dirname, join, exists

import requests
from hoshino import priv, get_bot, get_self_ids
from hoshino.typing import NoticeSession, MessageSegment
from hoshino.util import pic2b64

from .create_img import generate_info_pic, generate_support_pic, _get_cx_name
from .jjchistory import *
from .pcrclient import pcrclient, ApiException, get_headers
from .playerpref import decryptxml
from .safeservice import SafeService

sv_help = '''
[竞技场绑定 uid] 绑定竞技场信息

[竞技场订阅状态] 查看绑定状态

[删除竞技场绑定] 删除绑定的信息

[竞技场查询 uid] 查询竞技场简要信息（绑定后无需输入uid）

[详细查询 uid] 查询账号详细信息（绑定后无需输入uid）

[启用竞技场订阅] 启用战斗竞技场排名变动推送，全局推送启用时有效

[停止竞技场订阅] 停止战斗竞技场排名变动推送

[启用公主竞技场订阅] 启用公主竞技场排名变动推送，全局推送启用时有效

[停止公主竞技场订阅] 停止公主竞技场排名变动推送

[竞技场历史] 查询战斗竞技场变化记录（战斗竞技场订阅开启有效，可保留10条）

[公主竞技场历史] 查询公主竞技场变化记录（公主竞技场订阅开启有效，可保留10条）

[查询头像框] 查看自己设置的详细查询里的角色头像框

[更换头像框] 更换详细查询生成的头像框，默认彩色

[查询群数] 查询bot所在群的数目

[查询竞技场订阅数] 查询绑定账号的总数量

[@BOT全局启用竞技场推送] 启用所有群的竞技场排名推送功能(仅限维护组)

[@BOT全局禁用竞技场推送] 禁用所有推送功能(仅限维护组)

[@BOT清空竞技场订阅] 清空所有绑定的账号(仅限维护组)
'''.strip()

sv = SafeService('pcrjjc_tw_new', help_=sv_help, bundle='pcr查询')

# ========== ↓ ↓ ↓ 配置读取 ↓ ↓ ↓ ==========

# 读取绑定配置
curPath = dirname(__file__)
old_config = join(curPath, 'binds.json')
config = join(curPath, 'binds_v2.json')
root = {
    'global_push': True,
    'arena_bind': {}
}
if exists(config):
    with open(config) as fp:
        root = load(fp)
binds = root['arena_bind']

# 读取代理配置
with open(join(curPath, 'account.json')) as fp:
    pInfo = load(fp)

# 一些变量初始化
cache = {}
client = None

# 设置异步锁保证线程安全
lck = Lock()
captcha_lck = Lock()
qLck = Lock()

# 数据库对象初始化
jjc_history = JJCHistoryStorage()

# ========== ↑ ↑ ↑ 配置读取 ↑ ↑ ↑ ==========


# ========== ↓ ↓ ↓ 启动时检查文件 ↓ ↓ ↓ ==========

# headers文件
header_path = os.path.join(os.path.dirname(__file__), 'headers.json')
if not os.path.exists(header_path):
    default_headers = get_headers()
    with open(header_path, 'w', encoding='UTF-8') as f:
        json.dump(default_headers, f, indent=4, ensure_ascii=False)

# 头像框设置文件，默认彩色
current_dir = os.path.join(os.path.dirname(__file__), 'frame.json')
if not os.path.exists(current_dir):
    data = {
        "default_frame": "color.png",
        "customize": {}
    }
    with open(current_dir, 'w', encoding='UTF-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# 2023-05-10 合服 | 如果检测到旧配置且没有新配置，就将其移入新配置文件
if os.path.exists(old_config) and not os.path.exists(config):
    with open(old_config, 'r', encoding='UTF-8') as file0:
        config_data = dict(json.load(file0))
    bind_data = config_data.get('arena_bind', {})
    for user_id_str in list(bind_data.keys()):
        bind_data_info = bind_data.get(user_id_str, {})

        game_id_str = bind_data_info.get('id', '')
        cx_str = bind_data_info.get('cx', '')
        bind_data_info['id'] = cx_str + game_id_str
        bind_data[user_id_str] = bind_data_info
    config_data['arena_bind'] = bind_data
    with open(config, 'w', encoding='UTF-8') as f:
        json.dump(config_data, f, indent=4, ensure_ascii=False)


# ========== ↑ ↑ ↑ 启动时检查文件 ↑ ↑ ↑ ==========


# ========== ↓ ↓ ↓ 读取 & 校验 ↓ ↓ ↓ ==========

# 查询配置文件是否存在
def judge_file(cx_id: int):
    cx = 'first' if cx_id == 1 else 'other'
    cx_path = os.path.join(os.path.dirname(__file__), f'{cx}_tw.sonet.princessconnect.v2.playerprefs.xml')
    if os.path.exists(cx_path):
        return True
    else:
        return False


# 获取配置文件
def get_client():
    ac_info_first = decryptxml(join(curPath, 'first_tw.sonet.princessconnect.v2.playerprefs.xml')) \
        if judge_file(1) else {'admin': ''}
    client_first = pcrclient(ac_info_first['UDID'], ac_info_first['SHORT_UDID'], ac_info_first['VIEWER_ID'],
                             ac_info_first['TW_SERVER_ID'], pInfo['proxy']) if judge_file(1) else None
    ac_info_other = decryptxml(join(curPath, 'other_tw.sonet.princessconnect.v2.playerprefs.xml')) \
        if judge_file(0) else {'admin': ''}
    client_other = pcrclient(ac_info_other['UDID'], ac_info_other['SHORT_UDID'], ac_info_other['VIEWER_ID'],
                             ac_info_other['TW_SERVER_ID'], pInfo['proxy']) if judge_file(0) else None
    return client_first, client_other, ac_info_first, ac_info_other


async def query(uid):
    client_first, client_other, _, _ = get_client()
    cur_client = client_first if uid.startswith('1') else client_other
    if cur_client is None:
        return {'lack share_prefs': {}}
    async with qLck:
        while cur_client.shouldLogin:
            await cur_client.login()
        res = (await cur_client.callapi('/profile/get_profile', {'target_viewer_id': int(uid)}))
        return res


def save_binds():
    with open(config, 'w') as file:
        dump(root, file, indent=4)


async def judge_uid(uid_str, bot, ev):
    # 校验数字
    try:
        int(uid_str)
    except TypeError as _:
        await bot.send(ev, 'uid错误，需要10位纯数字，您输入了[' + str(len(uid_str)) + ']')
        return

    if len(uid_str) != 10:
        await bot.send(ev, 'uid长度错误，需要10位数字，您输入了[' + str(len(uid_str)) + ']')
        return

    # 校验服务器
    cx = uid_str[:1]
    if cx not in ['1', '2', '3', '4']:
        await bot.send(ev, 'uid校验出错，您输入了[' + str(len(uid_str)) + ']')
        return


# 每天13点左右自动更新版本号
@sv.scheduled_job('cron', hour='13', minute='1')
async def update_ver():
    headers_path = os.path.join(os.path.dirname(__file__), 'headers.json')
    headers = get_headers()
    with open(headers_path, 'w', encoding='UTF-8') as file:
        json.dump(headers, file, indent=4, ensure_ascii=False)
    sv.logger.info(f'pcrjjc_tw_new的游戏版本已更新至最新')


# ========== ↑ ↑ ↑ 读取 & 校验 ↑ ↑ ↑ ==========


# ========== ↓ ↓ ↓ 插件信息功能 ↓ ↓ ↓ ==========

@sv.on_fullmatch('竞技场帮助', only_to_me=False)
async def send_help(bot, ev):
    await bot.send(ev, f'{sv_help}')


@sv.on_fullmatch('查询群数', only_to_me=False)
async def group_num(bot, ev):
    self_ids = get_self_ids()
    msg_list = []
    for sid in self_ids:
        gl = await bot.get_group_list(self_id=sid)
        msg_list.append(f'Bot({str(sid)})目前正在为【{len(gl)}】个群服务')
    await bot.send(ev, '\n'.join(msg_list))


@sv.on_fullmatch('查询竞技场订阅数', only_to_me=False)
async def describe_number(bot, ev):
    global binds, lck
    async with lck:
        await bot.send(ev, f'当前竞技场已订阅的账号数量为【{len(binds)}】个')


# ========== ↑ ↑ ↑ 插件信息功能 ↑ ↑ ↑ ==========


# ========== ↓ ↓ ↓ 维护组功能 ↓ ↓ ↓ ==========

@sv.on_fullmatch('清空竞技场订阅', only_to_me=True)
async def del_all(bot, ev):
    global binds, lck
    async with lck:
        if not priv.check_priv(ev, priv.SUPERUSER):
            await bot.send(ev, '抱歉，您的权限不足，只有BOT维护组才能进行该操作！')
            return
        num = len(binds)
        binds.clear()
        save_binds()
        await bot.send(ev, f'已清空全部【{num}】个已订阅账号！')


@sv.on_fullmatch('全局启用竞技场推送', only_to_me=True)
async def enable_all_push(bot, ev):
    global root, lck
    async with lck:
        if not priv.check_priv(ev, priv.SUPERUSER):
            await bot.send(ev, '抱歉，您的权限不足，只有BOT维护组才能进行该操作！')
            return
        root['global_push'] = True
        with open(config, 'w') as file:
            dump(root, file, indent=4)
        await bot.send(ev, f'已全局启用竞技场推送！')


@sv.on_fullmatch('全局禁用竞技场推送', only_to_me=True)
async def disable_all_push(bot, ev):
    global root, lck
    async with lck:
        if not priv.check_priv(ev, priv.SUPERUSER):
            await bot.send(ev, '抱歉，您的权限不足，只有BOT维护组才能进行该操作！')
            return
        root['global_push'] = False
        with open(config, 'w') as file:
            dump(root, file, indent=4)
        await bot.send(ev, f'已全局禁用竞技场推送！')


# ========== ↑ ↑ ↑ 维护组功能 ↑ ↑ ↑ ==========


# ========== ↓ ↓ ↓ 绑定解绑功能 ↓ ↓ ↓ ==========

@sv.on_prefix('竞技场绑定')
async def on_arena_bind(bot, ev):
    global binds, lck
    id_str = str(ev.message)
    # 校验
    await judge_uid(id_str, bot, ev)
    cx = id_str[:1]

    async with lck:
        user_id = str(ev.user_id)
        last = binds[user_id] if user_id in binds else None
        binds[user_id] = {
            'id': id_str,
            'uid': user_id,
            'gid': str(ev.group_id),
            'arena_on': last is None or last['arena_on'],
            'grand_arena_on': last is None or last['grand_arena_on'],
        }
        save_binds()
        is_file = judge_file(int(cx))
        msg = '竞技场绑定成功'
        msg += f'\n注：本bot未识别到台服{cx}服配置文件，因此查询该服的玩家信息功能不可用，请联系维护组解决' if not is_file else ''

    await bot.finish(ev, msg, at_sender=True)


# 订阅删除方法
def delete_arena(user_id):
    jjc_history.remove(binds[user_id]['id'])
    binds.pop(user_id)
    save_binds()


@sv.on_prefix('删除竞技场订阅')
async def delete_arena_sub(bot, ev):
    global binds, lck
    user_id = str(ev.user_id)

    if ev.message[0].type == 'at':
        if not priv.check_priv(ev, priv.SUPERUSER):
            await bot.send(ev, '删除他人订阅请联系维护', at_sender=True)
            return
    elif len(ev.message) == 1 and ev.message[0].type == 'text' and not ev.message[0].data['text']:
        user_id = str(ev.user_id)

    if user_id not in binds:
        await bot.send(ev, '未绑定竞技场', at_sender=True)
        return

    async with lck:
        delete_arena(user_id)

    await bot.finish(ev, '删除竞技场订阅成功', at_sender=True)


@sv.on_fullmatch('竞技场订阅状态')
async def send_arena_sub_status(bot, ev):
    global binds, lck
    uid = str(ev['user_id'])

    if uid not in binds:
        await bot.send(ev, '您还未绑定竞技场', at_sender=True)
    else:
        info = binds[uid]
        await bot.finish(ev,
                         f'''
    当前竞技场绑定ID：{info['id']}
    竞技场订阅：{'开启' if info['arena_on'] else '关闭'}
    公主竞技场订阅：{'开启' if info['grand_arena_on'] else '关闭'}''', at_sender=True)


# 退群自动删除绑定
@sv.on_notice('group_decrease.leave')
async def leave_notice(session: NoticeSession):
    global lck, binds
    uid = str(session.ctx['user_id'])
    gid = str(session.ctx['group_id'])
    bot = get_bot()
    if uid not in binds:
        return
    async with lck:
        bind_cache = deepcopy(binds)
        info = bind_cache[uid]
        if info['gid'] == gid:
            binds.pop(uid)
            save_binds()
            await bot.send_group_msg(
                group_id=int(info['gid']),
                message=f'{uid}退群了，已自动删除其绑定在本群的竞技场订阅推送'
            )


# ========== ↑ ↑ ↑ 绑定解绑功能 ↑ ↑ ↑ ==========


# ========== ↓ ↓ ↓ 查询功能 ↓ ↓ ↓ ==========

@sv.on_prefix('竞技场查询')
async def on_query_arena(bot, ev):
    global binds, lck
    id_str = str(ev.message)
    async with lck:
        if not id_str:
            # 没有输入UID
            user_id = str(ev['user_id'])
            if user_id not in binds:
                await bot.send(ev, '您还未绑定竞技场', at_sender=True)
                return
            else:
                id_str = str(binds[user_id]['id'])
        else:
            # 输入了UID
            await judge_uid(id_str, bot, ev)

        # 服务器名称
        cx = id_str[:1]
        cx_name = _get_cx_name(cx)

        try:
            res = await query(id_str)

            if 'lack share_prefs' in res:
                await bot.send(ev, f'查询出错，缺少[{cx_name}]服的配置文件', at_sender=True)
                return

            last_login_time = int(res['user_info']['last_login_time'])
            last_login_date = time.localtime(last_login_time)
            last_login_str = time.strftime('%Y-%m-%d %H:%M:%S', last_login_date)

            msg = f'''
区服：{cx_name}
昵称：{res['user_info']["user_name"]}
jjc排名：{res['user_info']["arena_rank"]}
pjjc排名：{res['user_info']["grand_arena_rank"]}
最后登录：{last_login_str}'''.strip()

            await bot.send(ev, msg, at_sender=False)
        except ApiException as e:
            await bot.send(ev, f'查询出错，{e}', at_sender=True)
        except requests.exceptions.ProxyError:
            await bot.send(ev, f'查询出错，连接代理失败，请再次尝试', at_sender=True)
        except Exception as e:
            await bot.send(ev, f'查询出错，{e}', at_sender=True)


@sv.on_prefix('详细查询')
async def on_query_arena_all(bot, ev):
    global binds, lck
    id_str = str(ev.message)

    async with lck:
        if not id_str:
            # 没有输入UID
            user_id = str(ev['user_id'])
            if user_id not in binds:
                await bot.send(ev, '您还未绑定竞技场', at_sender=True)
                return
            else:
                id_str = str(binds[user_id]['id'])
        else:
            # 输入了UID
            await judge_uid(id_str, bot, ev)

        # 服务器名称
        cx = id_str[:1]
        cx_name = _get_cx_name(cx)

        try:
            res = await query(id_str)

            if 'lack share_prefs' in res:
                await bot.send(ev, f'查询出错，缺少[{cx_name}]服的配置文件', at_sender=True)
                return

            sv.logger.info('开始生成竞技场查询图片...')  # 通过log显示信息
            result_image = await generate_info_pic(res, cx, user_id)
            result_image = pic2b64(result_image)  # 转base64发送，不用将图片存本地
            result_image = MessageSegment.image(result_image)
            result_support = await generate_support_pic(res, user_id)
            result_support = pic2b64(result_support)  # 转base64发送，不用将图片存本地
            result_support = MessageSegment.image(result_support)
            sv.logger.info('竞技场查询图片已准备完毕！')
            await bot.send(ev, f"{str(result_image)}\n{result_support}", at_sender=True)

        except ApiException as e:
            await bot.send(ev, f'查询出错，{e}', at_sender=True)
        except requests.exceptions.ProxyError:
            await bot.send(ev, f'查询出错，连接代理失败，请再次尝试', at_sender=True)
        except Exception as e:
            await bot.send(ev, f'查询出错，{e}', at_sender=True)


# ========== ↑ ↑ ↑ 绑查询功能 ↑ ↑ ↑ ==========


# ========== ↓ ↓ ↓ 头像框功能 ↓ ↓ ↓ ==========

@sv.on_prefix(('竞技场换头像框', '更换竞技场头像框', '更换头像框'))
async def change_frame(bot, ev):
    user_id = ev.user_id
    frame_tmp = ev.message.extract_plain_text()
    path = os.path.join(os.path.dirname(__file__), 'img/frame/')
    frame_list = os.listdir(path)
    if not frame_list:
        await bot.finish(ev, 'img/frame/路径下没有任何头像框，请联系维护组检查目录')
    if frame_tmp not in frame_list:
        msg = f'文件名输入错误，命令样例：\n竞技场换头像框 color.png\n目前可选文件有：\n' + '\n'.join(frame_list)
        await bot.finish(ev, msg)
    frame_data = {str(user_id): frame_tmp}
    frame_dir = os.path.join(os.path.dirname(__file__), 'frame.json')
    with open(frame_dir, 'r', encoding='UTF-8') as file:
        f_data = json.load(file)
    f_data['customize'] = frame_data
    with open(frame_dir, 'w', encoding='UTF-8') as rf:
        json.dump(f_data, rf, indent=4, ensure_ascii=False)
    await bot.send(ev, f'已成功选择头像框:{frame_tmp}')
    frame_path = os.path.join(os.path.dirname(__file__), f'img/frame/{frame_tmp}')
    msg = MessageSegment.image(f'file:///{os.path.abspath(frame_path)}')
    await bot.send(ev, msg)


# 查头像框
@sv.on_fullmatch(('查竞技场头像框', '查询竞技场头像框', '查询头像框'))
async def see_a_see_frame(bot, ev):
    user_id = str(ev.user_id)
    frame_dir = os.path.join(os.path.dirname(__file__), 'frame.json')
    with open(frame_dir, 'r', encoding='UTF-8') as file:
        f_data = json.load(file)
    id_list = list(f_data['customize'].keys())
    if user_id not in id_list:
        frame_tmp = f_data['default_frame']
    else:
        frame_tmp = f_data['customize'][user_id]
    path = os.path.join(os.path.dirname(__file__), f'img/frame/{frame_tmp}')
    msg = MessageSegment.image(f'file:///{os.path.abspath(path)}')
    await bot.send(ev, msg)


# ========== ↑ ↑ ↑ 头像框功能 ↑ ↑ ↑ ==========


# ========== ↓ ↓ ↓ 推送 & 历史 ↓ ↓ ↓ ==========

@sv.on_rex('(启用|停止)(公主)?竞技场订阅')
async def change_arena_sub(bot, ev):
    global binds, lck

    key = 'arena_on' if ev['match'].group(2) is None else 'grand_arena_on'
    user_id = str(ev['user_id'])

    async with lck:
        if user_id not in binds:
            await bot.send(ev, '您还未绑定竞技场', at_sender=True)
        else:
            binds[user_id][key] = ev['match'].group(1) == '启用'
            save_binds()
            await bot.finish(ev, f'{ev["match"].group(0)}成功', at_sender=True)


# 竞技场历史记录
@sv.on_prefix('竞技场历史')
async def send_arena_history(bot, ev):
    global binds, lck
    user_id = str(ev['user_id'])
    if user_id not in binds:
        await bot.send(ev, '您暂未未绑定竞技场', at_sender=True)
    else:
        game_id = binds[user_id]['id']
        msg = f'\n{jjc_history.select(game_id, 1)}'
        await bot.finish(ev, msg, at_sender=True)


@sv.on_prefix('公主竞技场历史')
async def send_p_arena_history(bot, ev):
    global binds, lck
    user_id = str(ev['user_id'])
    if user_id not in binds:
        await bot.send(ev, '您暂未未绑定竞技场', at_sender=True)
    else:
        game_id = binds[user_id]['id']
        msg = f'\n{jjc_history.select(game_id, 0)}'
        await bot.finish(ev, msg, at_sender=True)


# 自动推送
@sv.scheduled_job('interval', minutes=3)
async def on_arena_schedule():
    global cache, root, binds, lck
    if not root.get('global_push', True):
        sv.logger.info('竞技场推送已被维护组全局禁用')
        return

    bot = get_bot()

    async with lck:
        bind_cache = deepcopy(binds)

    for uid in bind_cache:
        info = bind_cache[uid]
        cx = info["id"][:1]
        try:
            sv.logger.info(f'用户({info["uid"]}) 查询[ {cx}服 ]: {info["id"]}')
            res = await query(info["id"])
            if 'lack share_prefs' in res:
                sv.logger.info(f'由于缺少该服配置文件，已跳过{cx}服的id: {info["id"]}')
                continue
            res = (res['user_info']['arena_rank'], res['user_info']['grand_arena_rank'])

            if uid not in cache:
                cache[uid] = res
                continue

            last = cache[uid]
            cache[uid] = res

            # 两次间隔排名变化且开启了相关订阅就记录到数据库
            if res[0] != last[0] and info['arena_on']:
                jjc_history.add(int(info["id"]), 1, last[0], res[0])
                jjc_history.refresh(int(info["id"]), 1)
                sv.logger.info(f"{info['id']}: JJC {last[0]}->{res[0]}")
            if res[1] != last[1] and info['grand_arena_on']:
                jjc_history.add(int(info["id"]), 0, last[1], res[1])
                jjc_history.refresh(int(info["id"]), 0)
                sv.logger.info(f"{info['id']}: PJJC {last[1]}->{res[1]}")

            if res[0] > last[0] and info['arena_on']:
                for sid in get_self_ids():
                    try:
                        await bot.send_group_msg(
                            self_id=sid,
                            group_id=int(info['gid']),
                            message=f'[CQ:at,qq={info["uid"]}]jjc：{last[0]}->{res[0]} ▼{res[0] - last[0]}'
                        )
                        break
                    except Exception as _:
                        gid = int(info['gid'])
                        sv.logger.info(f'bot账号{sid}不在群{gid}中，将忽略该消息')

            if res[1] > last[1] and info['grand_arena_on']:
                for sid in get_self_ids():
                    try:
                        await bot.send_group_msg(
                            self_id=sid,
                            group_id=int(info['gid']),
                            message=f'[CQ:at,qq={info["uid"]}]pjjc：{last[1]}->{res[1]} ▼{res[1] - last[1]}'
                        )
                        break
                    except Exception as _:
                        gid = int(info['gid'])
                        sv.logger.info(f'bot账号{sid}不在群{gid}中，将忽略该消息')

        except ApiException as e:
            sv.logger.info(f'对台服{cx}服的{info["id"]}的检查出错' + str(e))
            if e.code == 6:
                async with lck:
                    delete_arena(uid)
                sv.logger.info(f'已经自动删除错误的uid={info["id"]}')
        except Exception as _:
            sv.logger.info(f'对台服{cx}服的{info["id"]}的检查出错' + str(e))


# ========== ↑ ↑ ↑ 推送 & 历史 ↑ ↑ ↑ ==========
