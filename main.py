import asyncio
import json
import os
import time
from asyncio import Lock
from copy import deepcopy

from aiocqhttp import MessageSegment
from httpx import ProxyError
from nonebot import NoticeSession

from yuiChyan import get_bot
from yuiChyan.exception import LakePermissionException
from yuiChyan.permission import check_permission, SUPERUSER
from yuiChyan.resources import base_img_path
from yuiChyan.util import pic2b64
from .create_img import generate_info_pic, generate_support_pic, _get_cx_name, generate_talent_pic
from .pcrclient import PcrClient, ApiException, default_headers
from .playerpref import decrypt_xml, sv
from .res_parse import updateData

# ========== ↓ ↓ ↓ 配置读取 ↓ ↓ ↓ ==========

# 读取绑定配置
curPath = os.path.dirname(__file__)
config = os.path.join(curPath, 'binds_v2.json')
root = {
    'global_push': True,
    'arena_bind': {}
}
if os.path.exists(config):
    with open(config) as fp:
        root = json.load(fp)
binds = root['arena_bind']

# 读取代理配置
with open(os.path.join(curPath, 'account.json')) as fp:
    pInfo = json.load(fp)

# 一些变量初始化
cache = {}
client = None

# 设置异步锁保证线程安全
lck = Lock()
captcha_lck = Lock()
qLck = Lock()

# 全局缓存的client登陆 | 减少协议握手次数
first_client_cache = None
other_client_cache = None

# ========== ↑ ↑ ↑ 配置读取 ↑ ↑ ↑ ==========


# ========== ↓ ↓ ↓ 启动时检查文件 ↓ ↓ ↓ ==========

# 生成一份旧版headers文件
header_path = os.path.join(os.path.dirname(__file__), 'headers.json')
if not os.path.exists(header_path):
    with open(header_path, 'w', encoding='UTF-8') as f:
        # noinspection PyTypeChecker
        json.dump(default_headers, f, indent=4, ensure_ascii=False)

# 头像框设置文件，默认彩色
current_dir = os.path.join(os.path.dirname(__file__), 'frame.json')
if not os.path.exists(current_dir):
    data = {
        "default_frame": "color.png",
        "customize": {}
    }
    with open(current_dir, 'w', encoding='UTF-8') as f:
        # noinspection PyTypeChecker
        json.dump(data, f, indent=4, ensure_ascii=False)

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
    global first_client_cache, other_client_cache

    ac_info_first = {'admin': ''}
    ac_info_other = {'admin': ''}

    # 1服
    if first_client_cache is None:
        if judge_file(1):
            ac_info_first = decrypt_xml(os.path.join(curPath, 'first_tw.sonet.princessconnect.v2.playerprefs.xml'))
            client_first = PcrClient(ac_info_first['UDID'], ac_info_first['SHORT_UDID'], ac_info_first['VIEWER_ID'],
                                     ac_info_first['TW_SERVER_ID'], pInfo['proxy'])
        else:
            client_first = None
        first_client_cache = client_first

    # 其他服
    if other_client_cache is None:
        if judge_file(0):
            ac_info_other = decrypt_xml(os.path.join(curPath, 'other_tw.sonet.princessconnect.v2.playerprefs.xml'))
            client_other = PcrClient(ac_info_other['UDID'], ac_info_other['SHORT_UDID'], ac_info_other['VIEWER_ID'],
                                     ac_info_other['TW_SERVER_ID'], pInfo['proxy'])
        else:
            client_other = None
        other_client_cache = client_other

    return first_client_cache, other_client_cache, ac_info_first, ac_info_other


# 查询个人信息
async def query(uid):
    client_first, client_other, _, _ = get_client()
    cur_client = client_first if uid.startswith('1') else client_other
    if cur_client is None:
        return {'lack share_prefs': {}}
    async with qLck:
        try:
            res = await cur_client.callapi('/profile/get_profile', {'target_viewer_id': int(uid)})
            return res
        except ApiException as _:
            sv.logger.error('竞技场接口：登录超时或失败，将尝试一次重新登录，正在重新登录...')
        while cur_client.shouldLogin:
            await cur_client.login()
        res = await cur_client.callapi('/profile/get_profile', {'target_viewer_id': int(uid)})
        return res


def save_binds():
    with open(config, 'w') as file:
        # noinspection PyTypeChecker
        json.dump(root, file, indent=4)


async def judge_uid(uid_str, bot, ev):
    # 校验数字
    try:
        int(uid_str)
    except TypeError or ValueError as _:
        await bot.send(ev, 'uid错误，需要10位纯数字，您输入了[' + str(uid_str) + ']')
        return

    if len(uid_str) != 10:
        await bot.send(ev, 'uid长度错误，需要10位数字，您输入了' + str(len(uid_str)) + '位数')
        return

    # 校验服务器
    cx = uid_str[:1]
    if cx not in ['1', '2', '3', '4']:
        await bot.send(ev, 'uid校验出错，第一位数字为原始服务器ID，只能为1/2/3/4，您输入了[' + str(len(uid_str)) + ']')
        return


# ========== ↑ ↑ ↑ 读取 & 校验 ↑ ↑ ↑ ==========


# ========== ↓ ↓ ↓ 维护组功能 ↓ ↓ ↓ ==========

@sv.on_command('清空竞技场订阅', only_to_me=True, cmd_permission=SUPERUSER)
async def on_match(bot, ev):
    global binds, lck
    async with lck:
        num = len(binds)
        binds.clear()
        save_binds()
        await bot.send(ev, f'已清空全部【{num}】个已订阅账号！')


@sv.on_command('全局启用竞技场推送', only_to_me=True, cmd_permission=SUPERUSER)
async def enable_all_push(bot, ev):
    global root, lck
    async with lck:
        root['global_push'] = True
        with open(config, 'w') as file:
            # noinspection PyTypeChecker
            json.dump(root, file, indent=4)
        await bot.send(ev, f'已全局启用竞技场推送！')


@sv.on_command('全局禁用竞技场推送', only_to_me=True, cmd_permission=SUPERUSER)
async def disable_all_push(bot, ev):
    global root, lck
    async with lck:
        root['global_push'] = False
        with open(config, 'w') as file:
            # noinspection PyTypeChecker
            json.dump(root, file, indent=4)
        await bot.send(ev, f'已全局禁用竞技场推送！')


# 手动更新版本号
@sv.on_prefix('手动更新竞技场版本号', only_to_me=True)
async def update_ver(bot, ev):
    global lck, first_client_cache, other_client_cache
    async with lck:
        if not check_permission(ev, SUPERUSER):
            raise LakePermissionException(ev, None, SUPERUSER)
        try:
            headers_path = os.path.join(os.path.dirname(__file__), 'headers.json')
            default_headers['APP-VER'] = str(ev.message).strip()
            with open(headers_path, 'w', encoding='UTF-8') as file:
                # noinspection PyTypeChecker
                json.dump(default_headers, file, indent=4, ensure_ascii=False)
            # 清理缓存
            first_client_cache = None
            other_client_cache = None
            await bot.send(ev, f'pcrjjc_tw_new的游戏版本已更新至{str(ev.message).strip()}')
        except Exception as e:
            sv.logger.error(f'pcrjjc_tw_new手动更新版本号的时候出现错误：' + str(e))


# 查询版本号
@sv.on_match('查询竞技场版本号')
async def update_ver(bot, ev):
    headers_path = os.path.join(os.path.dirname(__file__), 'headers.json')
    with open(headers_path, 'r', encoding='UTF-8') as file:
        headers = json.load(file)
    await bot.send(ev, f'pcrjjc_tw_new的游戏版本为{headers.get("APP-VER", "")}')


# 自动更新解包数据
@sv.scheduled_job(day='1/1', hour='2', minute='30')
async def update_rank_exp():
    await updateData()
    sv.logger.info('"rank_exp.csv" 已经更新到最新版本')


# 手动刷新竞技场缓存
@sv.on_command('手动刷新竞技场缓存', only_to_me=True, cmd_permission=SUPERUSER)
async def clear_cache(bot, ev):
    global lck, first_client_cache, other_client_cache, root, binds
    async with lck:
        # 清理缓存
        first_client_cache = None
        other_client_cache = None
        # 刷新订阅
        await refresh_binds()

        await bot.send(ev, f'pcrjjc_tw_new的Client缓存已刷新!')


# 刷新订阅
async def refresh_binds():
    global root, binds
    if os.path.exists(config):
        with open(config) as file:
            root = json.load(file)
    binds = root['arena_bind']


# 首次启动
res_dir = os.path.join(base_img_path, 'pcrjjc_tw_new')
os.makedirs(res_dir, exist_ok=True)
if not os.path.exists(os.path.join(res_dir, 'rank_exp.csv')):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(update_rank_exp())


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
            'arena_on': False if last is None else last['arena_on'],
            'grand_arena_on': False if last is None else last['grand_arena_on'],
        }
        save_binds()
        is_file = judge_file(int(cx))
        msg = '竞技场绑定成功'
        msg += f'\n注：本bot未识别到台服{cx}服配置文件，因此查询该服的玩家信息功能不可用，请联系维护组解决' if not is_file else ''

    await bot.finish(ev, msg, at_sender=True)


# 订阅删除方法
def delete_arena(user_id):
    binds.pop(user_id)
    save_binds()


@sv.on_prefix('删除竞技场订阅')
async def delete_arena_sub(bot, ev):
    global binds, lck
    user_id = str(ev.user_id)

    if ev.message[0].type == 'at':
        if not check_permission(ev, SUPERUSER):
            raise LakePermissionException(ev, '删除他人订阅仅限维护组', SUPERUSER)
    elif len(ev.message) == 1 and ev.message[0].type == 'text' and not ev.message[0].data['text']:
        user_id = str(ev.user_id)

    if user_id not in binds:
        await bot.send(ev, '未绑定竞技场', at_sender=True)
        return

    async with lck:
        delete_arena(user_id)

    await bot.finish(ev, '删除竞技场订阅成功', at_sender=True)


@sv.on_match('竞技场订阅状态')
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
    if uid not in binds:
        return
    async with lck:
        bind_cache = deepcopy(binds)
        info = bind_cache[uid]
        if info['gid'] == gid:
            binds.pop(uid)
            save_binds()
            sv.logger.info(f'{uid}退群了，已自动删除其绑定在本群的竞技场订阅推送')


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
jjc排名：{res['user_info']["arena_rank"]}  ({res['user_info']["arena_group"]}场)
pjjc排名：{res['user_info']["grand_arena_rank"]}  ({res['user_info']["grand_arena_group"]}场)
最后登录：{last_login_str}'''.strip()

            await bot.send(ev, msg, at_sender=False)
        except ApiException as e:
            await bot.send(ev, f'查询出错，{e}', at_sender=True)
        except ProxyError:
            await bot.send(ev, f'查询出错，连接代理失败，请再次尝试', at_sender=True)
        except Exception as e:
            await bot.send(ev, f'查询出错，{e}', at_sender=True)


@sv.on_prefix('详细查询')
async def on_query_arena_all(bot, ev):
    global binds, lck
    id_str = str(ev.message)
    user_id = str(ev['user_id'])

    async with lck:
        if not id_str:
            # 没有输入UID
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
            talent_image = await generate_talent_pic(res)
            talent_image = pic2b64(talent_image)  # 转base64发送，不用将图片存本地
            talent_image = MessageSegment.image(talent_image)
            sv.logger.info('竞技场查询图片已准备完毕！')
            await bot.send(ev, f"{str(result_image)}\n{result_support}\n{talent_image}", at_sender=True)

        except ApiException as e:
            await bot.send(ev, f'查询出错，{e}', at_sender=True)
        except ProxyError:
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
        # noinspection PyTypeChecker
        json.dump(f_data, rf, indent=4, ensure_ascii=False)
    await bot.send(ev, f'已成功选择头像框:{frame_tmp}')
    frame_path = os.path.join(os.path.dirname(__file__), f'img/frame/{frame_tmp}')
    msg = MessageSegment.image(f'file:///{os.path.abspath(frame_path)}')
    await bot.send(ev, msg)


# 查头像框
@sv.on_match(('查竞技场头像框', '查询竞技场头像框', '查询头像框'))
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


# ========== ↓ ↓ ↓ 推送 ↓ ↓ ↓ ==========

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


# 自动推送 | 默认周期为3分钟
@sv.scheduled_job(minute='*/3')
async def on_arena_schedule():
    global cache, root, binds, lck
    if not root.get('global_push', True):
        sv.logger.info('竞技场推送已被维护组全局禁用')
        return

    bot = get_bot()

    async with lck:
        bind_cache = deepcopy(binds)

    msg_dict = {}
    for user_id in bind_cache:
        info = bind_cache[user_id]
        arena_on = info['arena_on']
        grand_arena_on = info['grand_arena_on']
        game_id = info['id']
        cx = game_id[:1]
        gid = info['gid']

        # 两个订阅都没开
        if not arena_on and not grand_arena_on:
            continue

        try:
            res = await query(game_id)
            if 'lack share_prefs' in res:
                sv.logger.info(f'由于缺少该服配置文件，已跳过{cx}服的id: {game_id}')
                continue
            res = (res['user_info']['arena_rank'], res['user_info']['grand_arena_rank'])

            if user_id not in cache:
                sv.logger.info(f'> 用户[{user_id}]的账号[{game_id}]排名：' + str(res) + '已存入缓存')
                cache[user_id] = res
                continue

            sv.logger.info(f'> 用户[{user_id}]的账号[{game_id}]当前排名：' + str(res))
            last = cache[user_id]
            cache[user_id] = res

            # 两次间隔排名变化
            if res[0] != last[0] and arena_on:
                sv.logger.info(f'  - JJC {last[0]}->{res[0]}')
            if res[1] != last[1] and grand_arena_on:
                sv.logger.info(f'  - PJJC {last[1]}->{res[1]}')

            # 排名下降了且开启了相关订阅就推送
            if (res[0] > last[0] and arena_on) or (res[1] > last[1] and grand_arena_on):
                list_get = msg_dict.get(int(gid), [])
                msg = f'[CQ:at,qq={user_id}]:\n'
                if res[0] > last[0] and arena_on:
                    msg += f' > JJC：{last[0]}->{res[0]} ▼{res[0] - last[0]}\n'
                if res[1] > last[1] and grand_arena_on:
                    msg += f' > PJJC：{last[1]}->{res[1]} ▼{res[1] - last[1]}\n'
                list_get.append(msg)
                msg_dict[int(gid)] = list_get

        except ApiException as e:
            sv.logger.error(f'对台服{cx}服的{game_id}的检查出错' + str(e))
            if e.code == 6:
                async with lck:
                    delete_arena(user_id)
                sv.logger.error(f'已经自动删除错误的uid={game_id}')
        except Exception as e:
            sv.logger.error(f'对台服{cx}服的{game_id}的检查出错' + str(e))

    # 开始分群发送消息
    if msg_dict:
        for sid in bot.get_self_ids():
            for group_id in msg_dict:
                list_get = msg_dict.get(group_id, [])
                if list_get:
                    msg_end = '\n'.join(list_get)
                    try:
                        await bot.send_group_msg(
                            self_id=sid,
                            group_id=group_id,
                            message=msg_end.strip()
                        )
                    except Exception as _:
                        sv.logger.error(f'bot账号{sid}不在群{group_id}中，将忽略该消息')

# ========== ↑ ↑ ↑ 推送 & 历史 ↑ ↑ ↑ ==========
