import json
import time
from pathlib import Path

import zhconv
from PIL import Image, ImageDraw, ImageFont, ImageColor
from hoshino import util

from .res_parse import read_knight_exp_rank
from ..priconne import chara

path = Path(__file__).parent  # 获取文件所在目录的绝对路径
font_cn_path = str(path / 'fonts' / 'SourceHanSansCN-Medium.otf')  # Path是路径对象，必须转为str之后ImageFont才能读取
font_tw_path = str(path / 'fonts' / 'pcrtwfont.ttf')


def get_frame(user_id):
    current_dir = path / 'frame.json'
    with open(current_dir, 'r', encoding='UTF-8') as f:
        f_data = json.load(f)
    id_list = list(f_data['customize'].keys())
    if user_id not in id_list:
        frame_tmp = f_data['default_frame']
    else:
        frame_tmp = f_data['customize'][user_id]
    return frame_tmp


def _traditional_to_simplified(zh_str: str):
    """
    Function: 将 zh_str 由繁体转化为简体
    """
    return zhconv.convert(str(zh_str), 'zh-hans')


def _cut_str(obj: str, sec: int):
    """
    按步长分割字符串
    """
    return [obj[i: i + sec] for i in range(0, len(obj), sec)]


def _get_cx_name(cx):
    """
    获取服务器名称
    """
    if cx == '1':
        cx_name = '美食殿堂'
        return cx_name
    elif cx == '2':
        cx_name = '真步王国'
        return cx_name
    elif cx == '3':
        cx_name = '破晓之星'
        return cx_name
    elif cx == '4':
        cx_name = '小小甜心'
        return cx_name
    else:
        cx_name = '未知'
        return cx_name


async def generate_info_pic(data, cx, uid):
    """
    个人资料卡生成
    """
    frame_tmp = get_frame(uid)
    im = Image.open(path / 'img' / 'template.png').convert("RGBA")  # 图片模板
    im_frame = Image.open(path / 'img' / 'frame' / f'{frame_tmp}').convert("RGBA")  # 头像框
    try:
        id_favorite = int(str(data['favorite_unit']['id'])[0:4])  # 截取第1位到第4位的字符
    except Exception as _:
        id_favorite = 1000  # 一个未知角色头像
    # 适配新版，兼容旧版
    try:
        pic_dir = (await chara.fromid(id_favorite).get_icon()).path
    except Exception as _:
        pic_dir = chara.fromid(id_favorite).icon.path
    user_avatar = Image.open(pic_dir).convert("RGBA")
    user_avatar = user_avatar.resize((90, 90))
    im.paste(user_avatar, (44, 150), mask=user_avatar)
    im_frame = im_frame.resize((100, 100))
    im.paste(im=im_frame, box=(39, 145), mask=im_frame)

    cn_font = ImageFont.truetype(font_cn_path, 18)  # Path是路径对象，必须转为str之后ImageFont才能读取
    # tw_font = ImageFont.truetype(str(font_tw_path), 18) # 字体有点问题，暂时别用

    font = cn_font  # 选择字体

    cn_font_resize = ImageFont.truetype(font_cn_path, 16)
    # tw_font_resize = ImageFont.truetype(font_tw_path, 16) # 字体有点问题，暂时别用

    font_resize = cn_font_resize  # 选择字体

    draw = ImageDraw.Draw(im)
    font_black = (77, 76, 81, 255)

    # 资料卡 个人信息
    user_name_text = _traditional_to_simplified(data["user_info"]["user_name"])
    user_name_text = util.filt_message(str(user_name_text))
    team_level_text = _traditional_to_simplified(data["user_info"]["team_level"])
    team_level_text = util.filt_message(str(team_level_text))
    total_power_text = _traditional_to_simplified(
        data["user_info"]["total_power"])
    total_power_text = util.filt_message(str(total_power_text))
    clan_name_text = _traditional_to_simplified(data["clan_name"])
    clan_name_text = util.filt_message(str(clan_name_text))
    user_comment_arr = _traditional_to_simplified(data["user_info"]["user_comment"])
    user_comment_arr = util.filt_message(str(user_comment_arr))
    user_comment_arr = _cut_str(user_comment_arr, 25)
    last_login_time_text = _traditional_to_simplified(time.strftime(
        "%Y/%m/%d %H:%M:%S", time.localtime(data["user_info"]["last_login_time"]))).split(' ')

    draw.text((194, 120), user_name_text, font_black, font)

    # 等级
    w, h = font_resize.getsize(team_level_text)
    draw.text((568 - w, 168), team_level_text, font_black, font_resize)
    # 总战力
    w, h = font_resize.getsize(total_power_text)
    draw.text((568 - w, 210), total_power_text, font_black, font_resize)
    # 公会名
    w, h = font_resize.getsize(clan_name_text)
    draw.text((568 - w, 250), clan_name_text, font_black, font_resize)
    # 好友数
    draw.text((40, 265), '好友数：' + str(data["user_info"]["friend_num"]), font_black, font_resize)
    # 个人信息
    for index, value in enumerate(user_comment_arr):
        draw.text((185, 310 + (index * 22)), value, font_black, font_resize)
    # 登录时间
    draw.text((34, 350), '> 最后登录时间：\n' + last_login_time_text[0] + "\n" + last_login_time_text[1], font_black, font_resize)
    draw.text((34, 410), '> 区服：' + _get_cx_name(cx), font_black, font_resize)

    # 资料卡 冒险经历
    normal_quest_text = _traditional_to_simplified(
        data["quest_info"]["normal_quest"][2])
    hard_quest_text = _traditional_to_simplified(
        data["quest_info"]["hard_quest"][2])
    very_hard_quest_text = _traditional_to_simplified(
        data["quest_info"]["very_hard_quest"][2])
    byway_quest_text = _traditional_to_simplified(
        data["quest_info"]["byway_quest"])

    up_quest_text = "N" + normal_quest_text + " / SUB" + byway_quest_text
    w, h = font_resize.getsize(up_quest_text)
    draw.text((550 - w, 498), up_quest_text, font_black, font_resize)

    down_quest_text = "H" + hard_quest_text + " / VH" + very_hard_quest_text
    w, h = font_resize.getsize(down_quest_text)
    draw.text((550 - w, 530), down_quest_text, font_black, font_resize)

    arena_group_text = _traditional_to_simplified(
        data["user_info"]["arena_group"])
    arena_time_text = _traditional_to_simplified(time.strftime(
        "%Y/%m/%d", time.localtime(data["user_info"]["arena_time"])))
    arena_rank_text = _traditional_to_simplified(data["user_info"]["arena_rank"])
    grand_arena_group_text = _traditional_to_simplified(
        data["user_info"]["grand_arena_group"])
    grand_arena_time_text = _traditional_to_simplified(time.strftime(
        "%Y/%m/%d", time.localtime(data["user_info"]["grand_arena_time"])))
    grand_arena_rank_text = _traditional_to_simplified(
        data["user_info"]["grand_arena_rank"])

    w, h = font_resize.getsize(arena_time_text)
    draw.text((550 - w, 598), arena_time_text, font_black, font_resize)
    w, h = font_resize.getsize(arena_group_text + " 场")
    draw.text((550 - w, 630), arena_group_text + " 场", font_black, font_resize)
    w, h = font_resize.getsize(arena_rank_text + " 名")
    draw.text((550 - w, 662), arena_rank_text + " 名", font_black, font_resize)
    w, h = font_resize.getsize(grand_arena_time_text)
    draw.text((550 - w, 704), grand_arena_time_text, font_black, font_resize)
    w, h = font_resize.getsize(grand_arena_group_text + " 场")
    draw.text((550 - w, 738), grand_arena_group_text + " 场", font_black, font_resize)
    w, h = font_resize.getsize(grand_arena_rank_text + " 名")
    draw.text((550 - w, 772), grand_arena_rank_text + " 名", font_black, font_resize)

    unit_num_text = _traditional_to_simplified(data["user_info"]["unit_num"])
    open_story_num_text = _traditional_to_simplified(
        data["user_info"]["open_story_num"])

    w, h = font_resize.getsize(unit_num_text)
    draw.text((550 - w, 844), unit_num_text, font_black, font_resize)
    w, h = font_resize.getsize(open_story_num_text)
    draw.text((550 - w, 880), open_story_num_text, font_black, font_resize)

    tower_cleared_floor_num_text = _traditional_to_simplified(
        data["user_info"]["tower_cleared_floor_num"])
    tower_cleared_ex_quest_count_text = _traditional_to_simplified(
        data["user_info"]["tower_cleared_ex_quest_count"])

    w, h = font_resize.getsize(tower_cleared_floor_num_text + " 阶")
    draw.text((550 - w, 949), tower_cleared_floor_num_text + " 阶", font_black, font_resize)

    w, h = font_resize.getsize(tower_cleared_ex_quest_count_text)
    draw.text((550 - w, 984), tower_cleared_ex_quest_count_text, font_black, font_resize)

    simplified = _traditional_to_simplified(data["user_info"]["viewer_id"])
    cx = simplified[:1]
    viewer_id_arr = _cut_str(simplified[1:], 3)

    w, h = font.getsize(
        cx + "  " + viewer_id_arr[0] + "  " + viewer_id_arr[1] + "  " + viewer_id_arr[2])
    draw.text((138 + (460 - 138) / 2 - w / 2, 1060),
              cx + "  " + viewer_id_arr[0] + "  " + viewer_id_arr[1] + "  " + viewer_id_arr[2],
              (255, 255, 255, 255), font)

    return im


async def _friend_support_position(fr_data, im, fnt, rgb, im_frame, bbox):
    """
    好友支援位
    """
    # 合成头像
    im_yuansu = Image.open(path / 'img' / 'yuansu.png').convert("RGBA")  # 一个支援ui模板
    id_friend_support = int(str(fr_data['unit_data']['id'])[0:4])
    # 适配新版，兼容旧版
    try:
        pic_dir = (await chara.fromid(id_friend_support).get_icon()).path
    except:
        pic_dir = chara.fromid(id_friend_support).icon.path
    avatar = Image.open(pic_dir).convert("RGBA")
    avatar = avatar.resize((115, 115))
    im_yuansu.paste(im=avatar, box=(28, 78), mask=avatar)
    im_frame = im_frame.resize((128, 128))
    im_yuansu.paste(im=im_frame, box=(22, 72), mask=im_frame)

    # 合成文字信息
    yuansu_draw = ImageDraw.Draw(im_yuansu)
    icon_name_text = _traditional_to_simplified(chara.fromid(id_friend_support).name)
    icon_LV_text = str(fr_data['unit_data']['unit_level'])  # 写入文本必须是str格式
    icon_rank_text = str(fr_data['unit_data']['promotion_level'])
    yuansu_draw.text(xy=(167, 36.86), text=icon_name_text, font=fnt, fill=rgb)
    yuansu_draw.text(xy=(340, 101.8), text=icon_LV_text, font=fnt, fill=rgb)
    yuansu_draw.text(xy=(340, 159.09), text=icon_rank_text, font=fnt, fill=rgb)
    im.paste(im=im_yuansu, box=bbox)  # 无A通道的图不能输入mask

    return im


async def _clan_support_position(clan_data, im, fnt, rgb, im_frame, bbox):
    """
    地下城及战队支援位
    """
    # 合成头像
    im_yuansu = Image.open(path / 'img' / 'yuansu.png').convert("RGBA")  # 一个支援ui模板
    id_clan_support = int(str(clan_data['unit_data']['id'])[0:4])
    # 适配新版，兼容旧版
    try:
        pic_dir = (await chara.fromid(id_clan_support).get_icon()).path
    except:
        pic_dir = chara.fromid(id_clan_support).icon.path
    avatar = Image.open(pic_dir).convert("RGBA")
    avatar = avatar.resize((115, 115))
    im_yuansu.paste(im=avatar, box=(28, 78), mask=avatar)
    im_frame = im_frame.resize((128, 128))
    im_yuansu.paste(im=im_frame, box=(22, 72), mask=im_frame)

    # 合成文字信息
    yuansu_draw = ImageDraw.Draw(im_yuansu)
    icon_name_text = _traditional_to_simplified(chara.fromid(id_clan_support).name)
    icon_LV_text = str(clan_data['unit_data']['unit_level'])  # 写入文本必须是str格式
    icon_rank_text = str(clan_data['unit_data']['promotion_level'])
    yuansu_draw.text(xy=(167, 36.86), text=icon_name_text, font=fnt, fill=rgb)
    yuansu_draw.text(xy=(340, 101.8), text=icon_LV_text, font=fnt, fill=rgb)
    yuansu_draw.text(xy=(340, 159.09), text=icon_rank_text, font=fnt, fill=rgb)
    im.paste(im=im_yuansu, box=bbox)  # 无A通道的图不能输入mask

    return im


async def generate_support_pic(data, uid):
    '''
    支援界面图片合成
    '''
    frame_tmp = get_frame(uid)
    im = Image.open(path / 'img' / 'support.png').convert("RGBA")  # 支援图片模板
    im_frame = Image.open(path / 'img' / 'frame' / f'{frame_tmp}').convert("RGBA")  # 头像框

    fnt = ImageFont.truetype(font=font_cn_path, size=30)
    rgb = ImageColor.getrgb('#4e4e4e')

    # 判断玩家设置的支援角色应该存在的位置
    for fr_data in data['friend_support_units']:  # 若列表为空，则不会进行循环
        if fr_data['position'] == 1:  # 好友支援位1
            bbox = (1284, 156)
            im = await _friend_support_position(fr_data, im, fnt, rgb, im_frame, bbox)
        elif fr_data['position'] == 2:  # 好友支援位2
            bbox = (1284, 459)
            im = await _friend_support_position(fr_data, im, fnt, rgb, im_frame, bbox)

    for clan_data in data['clan_support_units']:
        if clan_data['position'] == 1:  # 地下城位置1
            bbox = (43, 156)
            im = await _clan_support_position(clan_data, im, fnt, rgb, im_frame, bbox)
        elif clan_data['position'] == 2:  # 地下城位置2
            bbox = (43, 459)
            im = await _clan_support_position(clan_data, im, fnt, rgb, im_frame, bbox)
        elif clan_data['position'] == 3:  # 战队位置1
            bbox = (665, 156)
            im = await _clan_support_position(clan_data, im, fnt, rgb, im_frame, bbox)
        elif clan_data['position'] == 4:  # 战队位置2
            bbox = (665, 459)
            im = await _clan_support_position(clan_data, im, fnt, rgb, im_frame, bbox)

    return im


# 生成深域进度图片
async def generate_talent_pic(data):
    im = Image.open(path / 'img' / 'background.png').convert("RGBA")
    fnt = ImageFont.truetype(font=font_cn_path, size=40)
    rgb = ImageColor.getrgb('#4e4e4e')
    rgb_w = ImageColor.getrgb('#ffffff')

    talent_quest = data['quest_info']['talent_quest']
    knight_exp = data['user_info']['princess_knight_rank_total_exp']

    quest_draw = ImageDraw.Draw(im)
    for talent in talent_quest:
        # 通关关数
        quest = '1-1'
        clear_count = int(talent['clear_count'])
        if clear_count:
            char = (clear_count - 1) // 10 + 1
            que_num = clear_count % 10
            que_num = que_num if que_num else 10
            quest = str(char) + '-' + str(que_num)

        if talent['talent_id'] == 1:
            bbox = (200, 290)
            item_img = Image.open(path / 'img' / 'talent_quest' / 'fire.png').convert("RGBA")
            item_img = item_img.resize((240, 320))
            im.paste(im=item_img, box=bbox, mask=item_img)
            quest_draw.text(xy=(280, 650), text=quest, font=fnt, fill=rgb)

        elif talent['talent_id'] == 2:
            bbox = (520, 290)
            item_img = Image.open(path / 'img' / 'talent_quest' / 'water.png').convert("RGBA")
            item_img = item_img.resize((240, 320))
            im.paste(im=item_img, box=bbox, mask=item_img)
            quest_draw.text(xy=(600, 650), text=quest, font=fnt, fill=rgb)

        elif talent['talent_id'] == 3:
            bbox = (840, 290)
            item_img = Image.open(path / 'img' / 'talent_quest' / 'wind.png').convert("RGBA")
            item_img = item_img.resize((240, 320))
            im.paste(im=item_img, box=bbox, mask=item_img)
            quest_draw.text(xy=(920, 650), text=quest, font=fnt, fill=rgb)

        elif talent['talent_id'] == 4:
            bbox = (1160, 290)
            item_img = Image.open(path / 'img' / 'talent_quest' / 'light.png').convert("RGBA")
            item_img = item_img.resize((240, 320))
            im.paste(im=item_img, box=bbox, mask=item_img)
            quest_draw.text(xy=(1240, 650), text=quest, font=fnt, fill=rgb)

        elif talent['talent_id'] == 5:
            bbox = (1480, 290)
            item_img = Image.open(path / 'img' / 'talent_quest' / 'darkness.png').convert("RGBA")
            item_img = item_img.resize((240, 320))
            im.paste(im=item_img, box=bbox, mask=item_img)
            quest_draw.text(xy=(1560, 650), text=quest, font=fnt, fill=rgb)

    # 公主骑士经验和等级
    knight_img = Image.open(path / 'img' / 'talent_quest' / 'knight_rank.png').convert("RGBA")
    knight_img = knight_img.resize((517, 61))
    bbox = (701, 729)
    im.paste(im=knight_img, box=bbox, mask=knight_img)
    quest_draw.text(xy=(735, 740), text='公主骑士经验', font=fnt, fill=rgb_w)
    quest_draw.text(xy=(1035, 738), text=str(knight_exp), font=fnt, fill=rgb)
    bbox = (701, 849)
    im.paste(im=knight_img, box=bbox, mask=knight_img)
    quest_draw.text(xy=(725, 860), text='公主骑士RANK', font=fnt, fill=rgb_w)
    knight_rank = await read_knight_exp_rank('rank_exp.csv', knight_exp)
    quest_draw.text(xy=(1080, 858), text=str(knight_rank), font=fnt, fill=rgb)

    return im
