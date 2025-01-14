import json
import os
import time

import zhconv
from PIL import Image, ImageDraw, ImageFont, ImageColor

from yuiChyan import font_path
from yuiChyan.core.princess import chara
from yuiChyan.util import filter_message
from .rank_parse import query_knight_exp_rank

current_path = os.path.dirname(__file__)


def get_frame(user_id):
    current_dir = os.path.join(current_path, 'frame.json')
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


async def generate_info_pic(data, cx, uid):
    """
    个人资料卡生成
    """
    frame_tmp = get_frame(uid)

    im = Image.open(os.path.join(current_path, 'img', 'template.png')).convert('RGBA')  # 图片模板
    im_frame = Image.open(os.path.join(current_path, 'img', 'frame', f'{frame_tmp}')).convert('RGBA')  # 头像框
    id_favorite = int(str(data['favorite_unit']['id'])[:4])  # 截取第1位到第4位的字符

    pic_dir = await chara.get_chara_by_id(id_favorite).get_icon_path()
    user_avatar = Image.open(pic_dir).convert('RGBA')
    user_avatar = user_avatar.resize((90, 90))
    im.paste(user_avatar, (44, 150), mask=user_avatar)
    im_frame = im_frame.resize((100, 100))
    im.paste(im=im_frame, box=(39, 145), mask=im_frame)

    font = ImageFont.truetype(font_path, 18)
    font_resize = ImageFont.truetype(font_path, 16)

    draw = ImageDraw.Draw(im)
    font_black = (77, 76, 81, 255)

    # 资料卡 个人信息
    user_name_text = _traditional_to_simplified(data["user_info"]["user_name"])
    user_name_text = await filter_message(str(user_name_text))
    team_level_text = _traditional_to_simplified(data["user_info"]["team_level"])
    team_level_text = await filter_message(str(team_level_text))
    total_power_text = _traditional_to_simplified(
        data["user_info"]["total_power"])
    total_power_text = await filter_message(str(total_power_text))
    clan_name_text = _traditional_to_simplified(data["clan_name"])
    clan_name_text = await filter_message(str(clan_name_text))
    user_comment_arr = _traditional_to_simplified(data["user_info"]["user_comment"])
    user_comment_arr = await filter_message(str(user_comment_arr))
    user_comment_arr = _cut_str(user_comment_arr, 25)
    last_login_time_text = _traditional_to_simplified(time.strftime(
        "%Y/%m/%d %H:%M:%S", time.localtime(data["user_info"]["last_login_time"]))).split(' ')

    draw.text((194, 120), user_name_text, font_black, font)

    # 等级
    w = font_resize.getlength(team_level_text)
    draw.text((568 - w, 168), team_level_text, font_black, font_resize)
    # 总战力
    w = font_resize.getlength(total_power_text)
    draw.text((568 - w, 210), total_power_text, font_black, font_resize)
    # 公会名
    w = font_resize.getlength(clan_name_text)
    draw.text((568 - w, 250), clan_name_text, font_black, font_resize)
    # 好友数
    draw.text((40, 265), '好友数：' + str(data["user_info"]["friend_num"]), font_black, font_resize)
    # 个人信息
    for index, value in enumerate(user_comment_arr):
        draw.text((185, 310 + (index * 22)), value, font_black, font_resize)
    # 登录时间
    draw.text((34, 350),
              '> 最后登录时间：\n' + last_login_time_text[0] + "\n" + last_login_time_text[1],
              font_black,
              font_resize)
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
    w = font_resize.getlength(up_quest_text)
    draw.text((550 - w, 498), up_quest_text, font_black, font_resize)

    down_quest_text = "H" + hard_quest_text + " / VH" + very_hard_quest_text
    w = font_resize.getlength(down_quest_text)
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

    w = font_resize.getlength(arena_time_text)
    draw.text((550 - w, 598), arena_time_text, font_black, font_resize)
    w = font_resize.getlength(arena_group_text + " 场")
    draw.text((550 - w, 630), arena_group_text + " 场", font_black, font_resize)
    w = font_resize.getlength(arena_rank_text + " 名")
    draw.text((550 - w, 662), arena_rank_text + " 名", font_black, font_resize)
    w = font_resize.getlength(grand_arena_time_text)
    draw.text((550 - w, 704), grand_arena_time_text, font_black, font_resize)
    w = font_resize.getlength(grand_arena_group_text + " 场")
    draw.text((550 - w, 738), grand_arena_group_text + " 场", font_black, font_resize)
    w = font_resize.getlength(grand_arena_rank_text + " 名")
    draw.text((550 - w, 772), grand_arena_rank_text + " 名", font_black, font_resize)

    unit_num_text = _traditional_to_simplified(data["user_info"]["unit_num"])
    open_story_num_text = _traditional_to_simplified(
        data["user_info"]["open_story_num"])

    w = font_resize.getlength(unit_num_text)
    draw.text((550 - w, 844), unit_num_text, font_black, font_resize)
    w = font_resize.getlength(open_story_num_text)
    draw.text((550 - w, 880), open_story_num_text, font_black, font_resize)

    tower_cleared_floor_num_text = _traditional_to_simplified(
        data["user_info"]["tower_cleared_floor_num"])
    tower_cleared_ex_quest_count_text = _traditional_to_simplified(
        data["user_info"]["tower_cleared_ex_quest_count"])

    w = font_resize.getlength(tower_cleared_floor_num_text + " 阶")
    draw.text((550 - w, 949), tower_cleared_floor_num_text + " 阶", font_black, font_resize)

    w = font_resize.getlength(tower_cleared_ex_quest_count_text)
    draw.text((550 - w, 984), tower_cleared_ex_quest_count_text, font_black, font_resize)

    simplified = _traditional_to_simplified(data["user_info"]["viewer_id"])
    cx = simplified[:1]
    viewer_id_arr = _cut_str(simplified[1:], 3)

    w = font.getlength(
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
    im_item = Image.open(os.path.join(current_path, 'img', 'item.png')).convert('RGBA')  # 一个支援ui模板
    id_friend_support = int(str(fr_data['unit_data']['id'])[0:4])
    pic_dir = await chara.get_chara_by_id(id_friend_support).get_icon_path()
    avatar = Image.open(pic_dir).convert('RGBA')
    avatar = avatar.resize((115, 115))
    im_item.paste(im=avatar, box=(28, 78), mask=avatar)
    im_frame = im_frame.resize((128, 128))
    im_item.paste(im=im_frame, box=(22, 72), mask=im_frame)

    # 合成文字信息
    item_draw = ImageDraw.Draw(im_item)
    icon_name_text = _traditional_to_simplified(chara.get_chara_by_id(id_friend_support).name)
    icon_LV_text = str(fr_data['unit_data']['unit_level'])  # 写入文本必须是str格式
    icon_rank_text = str(fr_data['unit_data']['promotion_level'])
    item_draw.text(xy=(167, 36.86), text=icon_name_text, font=fnt, fill=rgb)
    item_draw.text(xy=(340, 101.8), text=icon_LV_text, font=fnt, fill=rgb)
    item_draw.text(xy=(340, 159.09), text=icon_rank_text, font=fnt, fill=rgb)
    im.paste(im=im_item, box=bbox)  # 无A通道的图不能输入mask

    return im


async def _clan_support_position(clan_data, im, fnt, rgb, im_frame, bbox):
    """
    地下城及战队支援位
    """
    # 合成头像
    im_item = Image.open(os.path.join(current_path, 'img', 'item.png')).convert('RGBA')  # 一个支援ui模板
    id_clan_support = int(str(clan_data['unit_data']['id'])[0:4])
    pic_dir = await chara.get_chara_by_id(id_clan_support).get_icon_path()
    avatar = Image.open(pic_dir).convert('RGBA')
    avatar = avatar.resize((115, 115))
    im_item.paste(im=avatar, box=(28, 78), mask=avatar)
    im_frame = im_frame.resize((128, 128))
    im_item.paste(im=im_frame, box=(22, 72), mask=im_frame)

    # 合成文字信息
    icon_draw = ImageDraw.Draw(im_item)
    icon_name_text = _traditional_to_simplified(chara.get_chara_by_id(id_clan_support).name)
    icon_LV_text = str(clan_data['unit_data']['unit_level'])  # 写入文本必须是str格式
    icon_rank_text = str(clan_data['unit_data']['promotion_level'])
    icon_draw.text(xy=(167, 36.86), text=icon_name_text, font=fnt, fill=rgb)
    icon_draw.text(xy=(340, 101.8), text=icon_LV_text, font=fnt, fill=rgb)
    icon_draw.text(xy=(340, 159.09), text=icon_rank_text, font=fnt, fill=rgb)
    im.paste(im=im_item, box=bbox)  # 无A通道的图不能输入mask

    return im


async def generate_support_pic(data, uid):
    """
    支援界面图片合成
    """
    frame_tmp = get_frame(uid)
    im = Image.open(os.path.join(current_path, 'img', 'support.png')).convert('RGBA')  # 支援图片模板
    im_frame = Image.open(os.path.join(current_path, 'img', 'frame', frame_tmp)).convert('RGBA')  # 头像框

    fnt = ImageFont.truetype(font=font_path, size=30)
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
    im = Image.open(os.path.join(current_path, 'img', 'background.png')).convert('RGBA')
    fnt = ImageFont.truetype(font=font_path, size=40)
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
            item_img = Image.open(os.path.join(current_path, 'img', 'talent_quest', 'fire.png')).convert('RGBA')
            item_img = item_img.resize((240, 320))
            im.paste(im=item_img, box=bbox, mask=item_img)
            quest_draw.text(xy=(280, 650), text=quest, font=fnt, fill=rgb)

        elif talent['talent_id'] == 2:
            bbox = (520, 290)
            item_img = Image.open(os.path.join(current_path, 'img', 'talent_quest', 'water.png')).convert('RGBA')
            item_img = item_img.resize((240, 320))
            im.paste(im=item_img, box=bbox, mask=item_img)
            quest_draw.text(xy=(600, 650), text=quest, font=fnt, fill=rgb)

        elif talent['talent_id'] == 3:
            bbox = (840, 290)
            item_img = Image.open(os.path.join(current_path, 'img', 'talent_quest', 'wind.png')).convert('RGBA')
            item_img = item_img.resize((240, 320))
            im.paste(im=item_img, box=bbox, mask=item_img)
            quest_draw.text(xy=(920, 650), text=quest, font=fnt, fill=rgb)

        elif talent['talent_id'] == 4:
            bbox = (1160, 290)
            item_img = Image.open(os.path.join(current_path, 'img', 'talent_quest', 'light.png')).convert('RGBA')
            item_img = item_img.resize((240, 320))
            im.paste(im=item_img, box=bbox, mask=item_img)
            quest_draw.text(xy=(1240, 650), text=quest, font=fnt, fill=rgb)

        elif talent['talent_id'] == 5:
            bbox = (1480, 290)
            item_img = Image.open(os.path.join(current_path, 'img', 'talent_quest', 'darkness.png')).convert('RGBA')
            item_img = item_img.resize((240, 320))
            im.paste(im=item_img, box=bbox, mask=item_img)
            quest_draw.text(xy=(1560, 650), text=quest, font=fnt, fill=rgb)

    # 公主骑士经验和等级
    knight_img = Image.open(os.path.join(current_path, 'img', 'talent_quest', 'knight_rank.png')).convert('RGBA')
    knight_img = knight_img.resize((517, 61))
    bbox = (701, 729)
    im.paste(im=knight_img, box=bbox, mask=knight_img)
    quest_draw.text(xy=(735, 740), text='公主骑士经验', font=fnt, fill=rgb_w)
    quest_draw.text(xy=(1035, 738), text=str(knight_exp), font=fnt, fill=rgb)
    bbox = (701, 849)
    im.paste(im=knight_img, box=bbox, mask=knight_img)
    quest_draw.text(xy=(725, 860), text='公主骑士RANK', font=fnt, fill=rgb_w)
    knight_rank = await query_knight_exp_rank(int(knight_exp))
    quest_draw.text(xy=(1080, 858), text=str(knight_rank), font=fnt, fill=rgb)

    return im
