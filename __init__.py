import math
import time

import httpx
from aiocqhttp import MessageSegment
from httpx import ProxyError
from nonebot import NoticeSession, on_notice

from yuiChyan import get_bot, YuiChyan
from yuiChyan.config import NICKNAME
from yuiChyan.exception import LakePermissionException
from yuiChyan.http_request import rebuild_async_session
from yuiChyan.permission import check_permission, SUPERUSER
from yuiChyan.util import pic2b64
from .create_img import generate_info_pic, generate_support_pic, generate_talent_pic
from .pcr_client import ApiException
from .player_pref import sv
from .util import *


# 查询个人信息
async def query(uid: str):
    # 获取两种客户端的缓存
    client_first, client_other = await get_client()
    cur_client = client_first if uid.startswith('1') else client_other
    session_name = 'PcrClientFirst' if uid.startswith('1') else 'PcrClientOther'
    if cur_client is None:
        return {'lack share_prefs': {}}
    async with query_lock:
        try:
            res = await cur_client.callapi('/profile/get_profile', {'target_viewer_id': int(uid)})
            return res
        except ApiException:
            # 一般的请求异常 | 可尝试一次重新登录请求
            cur_client.shouldLogin = True
        except httpx.TransportError:
            # 特殊的请求异常 | 可能需要重建会话重新登录
            cur_client.shouldLogin = True
            # 重建并更新会话至客户端
            async_session = await rebuild_async_session(session_name)
            cur_client.update_async_session(async_session)
        # 如果需要登录就一直等待其进行登录
        while cur_client.shouldLogin:
            await cur_client.login()
        # 第二次请求客户端接口
        res = await cur_client.callapi('/profile/get_profile', {'target_viewer_id': int(uid)})
        return res


@sv.on_command('全局启用竞技场推送', only_to_me=True, cmd_permission=SUPERUSER)
async def enable_all_push(bot: YuiChyan, ev: CQEvent):
    binds_config = await get_binds_config()
    global_push = binds_config.get('global_push', True)
    if global_push:
        msg = '全局竞技场推送已经开启，无需再次开启'
    else:
        binds_config['global_push'] = True
        await save_binds_config(binds_config)
        msg = '已全局启用竞技场推送！'
    await bot.send(ev, msg)


@sv.on_command('全局禁用竞技场推送', only_to_me=True, cmd_permission=SUPERUSER)
async def disable_all_push(bot: YuiChyan, ev: CQEvent):
    binds_config = await get_binds_config()
    global_push = binds_config.get('global_push', True)
    if not global_push:
        msg = '全局竞技场推送已经禁用，无需再次禁用'
    else:
        binds_config['global_push'] = False
        await save_binds_config(binds_config)
        msg = '已全局禁用竞技场推送！'
    await bot.send(ev, msg)


@sv.on_prefix('手动更新竞技场版本号', only_to_me=True)
async def update_ver(bot: YuiChyan, ev: CQEvent):
    if not check_permission(ev, SUPERUSER):
        raise LakePermissionException(ev, None, SUPERUSER)
    # 更新版本
    update_headers_with_version(str(ev.message).strip())
    await bot.send(ev, f'竞技场查询的游戏版本已更新至{str(ev.message).strip()}')


@sv.on_match('查询竞技场版本号')
async def update_ver(bot: YuiChyan, ev: CQEvent):
    headers_config = get_headers_config()
    await bot.send(ev, f'竞技场查询的游戏版本为{headers_config.get("APP-VER", "")}')


@sv.on_prefix('竞技场绑定')
async def on_arena_bind(bot: YuiChyan, ev: CQEvent):
    id_str = str(ev.message)
    user_id = str(ev.user_id)
    await judge_uid(id_str, ev)
    cx = id_str[:1]
    # 绑定
    async with query_lock:
        binds_config = await get_binds_config()
        binds = binds_config.get('arena_bind', {})
        # 绑定或更新信息
        last = binds[user_id] if user_id in binds else None
        binds[user_id] = {
            'id': id_str,
            'uid': user_id,
            'gid': str(ev.group_id),
            'arena_on': False if last is None else last['arena_on'],
            'grand_arena_on': False if last is None else last['grand_arena_on'],
        }
        await save_binds_config(binds_config)
        # 判断一下该服的配置是否存在
        client_config = await get_client_config(int(cx))
        msg = f'\n> 您的QQ已成功绑定游戏ID [{id_str}]'
        msg += f'\n由于{NICKNAME}未配置台服{cx}服的配置，因此查询该服的玩家信息功能不可用，建议联系维护组咨询' if not client_config else ''
    await bot.send(ev, msg, at_sender=True)


@sv.on_prefix('删除竞技场订阅')
async def delete_arena_sub(bot: YuiChyan, ev: CQEvent):
    user_id = str(ev.user_id)
    # 判断删除的用户
    if ev.message[0].type == 'at':
        if not check_permission(ev, SUPERUSER):
            raise LakePermissionException(ev, '删除他人订阅仅限维护组', SUPERUSER)
    elif len(ev.message) == 1 and ev.message[0].type == 'text' and not ev.message[0].data['text']:
        user_id = str(ev.user_id)
    # 获取绑定
    binds_config = await get_binds_config()
    binds = binds_config.get('arena_bind', {})
    if user_id not in binds:
        await bot.send(ev, '您还未绑定竞技场呢', at_sender=True)
        return
    id_str = binds.get(user_id, {}).get('id', '')
    # 删除绑定
    rank_cache.pop(user_id)
    binds.pop(user_id)
    await save_binds_config(binds_config)
    await bot.send(ev, f'\n已成功为您删除对 [{id_str}] 的订阅', at_sender=True)


@sv.on_match('竞技场订阅状态')
async def send_arena_sub_status(bot: YuiChyan, ev: CQEvent):
    user_id = str(ev['user_id'])

    binds_config = await get_binds_config()
    binds = binds_config.get('arena_bind', {})
    if user_id not in binds:
        await bot.send(ev, '您还未绑定竞技场呢', at_sender=True)
        return
    info = binds.get(user_id, {})
    msg = f'\n游戏ID：{info["id"]}\n竞技场订阅：{"开启" if info["arena_on"] else "关闭"}\n公主竞技场订阅：{"开启" if info["grand_arena_on"] else "关闭"}'
    await bot.send(ev, msg, at_sender=True)


# 退群自动删除绑定
@on_notice('group_decrease.leave')
async def leave_notice(session: NoticeSession):
    user_id = str(session.ctx['user_id'])
    group_id = str(session.ctx['group_id'])
    binds_config = await get_binds_config()
    binds = binds_config.get('arena_bind', {})
    if user_id not in binds:
        return
    info = binds.get(user_id, {})
    if info.get('gid', '') == group_id:
        rank_cache.pop(user_id)
        binds.pop(user_id)
        await save_binds_config(binds_config)
        sv.logger.info(f'> {user_id}退群了，已自动删除其绑定在本群的竞技场订阅推送')


@sv.on_prefix('竞技场查询')
async def on_query_arena(bot: YuiChyan, ev: CQEvent):
    id_str = str(ev.message)
    user_id = str(ev['user_id'])
    # 获取UID
    binds_config = await get_binds_config()
    binds = binds_config.get('arena_bind', {})
    if not id_str:
        # 没有输入UID
        if user_id not in binds:
            await bot.send(ev, '您还未绑定竞技场呢', at_sender=True)
            return
        else:
            id_str = str(binds[user_id]['id'])
    else:
        # 输入了UID
        await judge_uid(id_str, ev)

    # 服务器名称
    cx = id_str[:1]
    cx_name = get_cx_name(cx)

    try:
        res = await query(id_str)

        if 'lack share_prefs' in res:
            await bot.send(ev, f'\n查询出错，缺少[{cx_name}]服的配置文件', at_sender=True)
            return

        last_login_time = int(res['user_info']['last_login_time'])
        last_login_date = time.localtime(last_login_time)
        last_login_str = time.strftime('%Y-%m-%d %H:%M:%S', last_login_date)

        msg = f'''
区服：{cx_name}
昵称：{res['user_info']["user_name"]}
JJC排名：{res['user_info']["arena_rank"]}  ({res['user_info']["arena_group"]}场)
PJJC排名：{res['user_info']["grand_arena_rank"]}  ({res['user_info']["grand_arena_group"]}场)
最后登录：{last_login_str}'''

        await bot.send(ev, msg, at_sender=True)
    except ApiException as e:
        await bot.send(ev, f'\n查询失败，{e}', at_sender=True)
    except ProxyError:
        await bot.send(ev, f'\n查询出错，连接代理失败，请再次尝试', at_sender=True)
    except Exception as e:
        await bot.send(ev, f'\n查询出错，{e}', at_sender=True)


@sv.on_prefix('详细查询')
async def on_query_arena_all(bot, ev):
    id_str = str(ev.message)
    user_id = str(ev['user_id'])
    # 获取UID
    binds_config = await get_binds_config()
    binds = binds_config.get('arena_bind', {})
    if not id_str:
        # 没有输入UID
        if user_id not in binds:
            await bot.send(ev, '您还未绑定竞技场呢', at_sender=True)
            return
        else:
            id_str = str(binds[user_id]['id'])
    else:
        # 输入了UID
        await judge_uid(id_str, ev)

    # 服务器名称
    cx = id_str[:1]
    cx_name = get_cx_name(cx)

    try:
        res = await query(id_str)

        if 'lack share_prefs' in res:
            await bot.send(ev, f'\n查询出错，缺少[{cx_name}]服的配置文件', at_sender=True)
            return

        sv.logger.info('开始生成竞技场查询图片...')  # 通过log显示信息
        result_image = await generate_info_pic(res, cx)
        result_image = pic2b64(result_image)  # 转base64发送，不用将图片存本地
        result_image = MessageSegment.image(result_image)
        result_support = await generate_support_pic(res)
        result_support = pic2b64(result_support)  # 转base64发送，不用将图片存本地
        result_support = MessageSegment.image(result_support)
        talent_image = await generate_talent_pic(res)
        talent_image = pic2b64(talent_image)  # 转base64发送，不用将图片存本地
        talent_image = MessageSegment.image(talent_image)
        sv.logger.info('竞技场查询图片已准备完毕！')
        await bot.send(ev, f"{str(result_image)}\n{result_support}\n{talent_image}", at_sender=True)

    except ApiException as e:
        await bot.send(ev, f'\n查询失败，{e}', at_sender=True)
    except ProxyError:
        await bot.send(ev, f'\n查询出错，连接代理失败，请再次尝试', at_sender=True)
    except Exception as e:
        await bot.send(ev, f'\n查询出错，{e}', at_sender=True)


# ========== ↓ ↓ ↓ 推送 ↓ ↓ ↓ ==========

@sv.on_rex('(启用|停止)(公主)?竞技场订阅')
async def change_arena_sub(bot, ev):
    key = 'arena_on' if ev['match'].group(2) is None else 'grand_arena_on'
    user_id = str(ev['user_id'])

    binds_config = await get_binds_config()
    binds = binds_config.get('arena_bind', {})
    if user_id not in binds:
        await bot.send(ev, '您还未绑定竞技场呢', at_sender=True)
    else:
        binds[user_id][key] = ev['match'].group(1) == '启用'
        await save_binds_config(binds_config)
        await bot.send(ev, f'{ev["match"].group(0)}成功', at_sender=True)


# 自动推送 | 默认周期为3分钟
@sv.scheduled_job(minute='*/3')
async def on_arena_schedule():
    binds_config = await get_binds_config()
    binds = binds_config.get('arena_bind', {})
    if not binds_config.get('global_push', True):
        sv.logger.info('竞技场推送已被维护组全局禁用')
        return

    bot = get_bot()
    msg_dict = {}
    for user_id in binds:
        info = binds[user_id]
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

            if user_id not in rank_cache:
                sv.logger.info(f'> 用户[{user_id}]的账号[{game_id}]排名：' + str(res) + '已存入缓存')
                rank_cache[user_id] = res
                continue

            sv.logger.info(f'> 用户[{user_id}]的账号[{game_id}]当前排名：' + str(res))
            last = rank_cache[user_id]
            rank_cache[user_id] = res

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
            sv.logger.error(f'对台服{cx}服的{game_id}的检查失败: {type(e)} {str(e)}')
            if e.code == 6:
                binds.pop(user_id)
                sv.logger.error(f'已经自动删除错误的UID [{game_id}]')
        except Exception as e:
            sv.logger.error(f'对台服{cx}服的{game_id}的检查出错: {type(e)} {str(e)}')

    # 开始分群发送消息
    if msg_dict:
        for group_id in msg_dict:
            list_get = msg_dict.get(group_id, [])
            if list_get:
                msg_end = '\n'.join(list_get)
                try:
                    await bot.send_group_msg(
                        self_id=bot.get_self_id(),
                        group_id=group_id,
                        message=msg_end.strip()
                    )
                except Exception as _:
                    sv.logger.error(f'bot账号{bot.get_self_id()}不在群{group_id}中，将忽略该消息')


@sv.on_rex(r'击剑(路径|路线)( )?(.{0,5})$')
async def arena_route(bot, ev):
    num = int(ev['match'].group(3))
    r = {}
    rank = 0
    while num > 1:
        rank += 1
        if num <= 11:
            num = 1
        elif num < 69:
            num -= 10
        else:
            num = math.floor(num * 0.85)
        r[rank] = num
    await bot.send(ev, '> 近5次最优击剑路径：' + ','.join(map(str, list(r.values())[:5])), at_sender=True)
