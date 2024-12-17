from base64 import b64decode
from re import finditer
from struct import unpack
from urllib.parse import unquote

from yuiChyan.service import Service

key = b'e806f6'
sv = Service('pcrjjc_tw_new')


def _dec_key(s) -> bytes:
    b = b64decode(unquote(s))
    return bytes([key[i % len(key)] ^ b[i] for i in range(len(b))])


def _dec_val(k, s):
    b = b64decode(unquote(s))
    key2 = k.encode('utf8') + key
    b = b[0:len(b) - (11 if b[-5] != 0 else 7)]
    return bytes([key2[i % len(key2)] ^ b[i] for i in range(len(b))])


def decrypt_xml(filename):
    result = {}

    with open(filename, 'r') as fp:
        content = fp.read()

    for re in finditer(r'<string name="(.*)">(.*)</string>', content):
        g = re.groups()
        try:
            xml_key = _dec_key(g[0]).decode('utf8')
            val = _dec_val(xml_key, g[1])
        except Exception as _:
            continue

        if xml_key == 'UDID':
            val = ''.join([chr(val[4 * i + 6] - 10) for i in range(36)])
        elif xml_key == 'SHORT_UDID_lowBits':
            val = str(unpack('I', val)[0])
            xml_key = 'SHORT_UDID'
        elif xml_key == 'VIEWER_ID_lowBits':
            val = str(unpack('I', val)[0])
            xml_key = 'VIEWER_ID'
        elif len(val) == 4:
            val = str(unpack('i', val)[0])
        result[xml_key] = val

    # 不同服务器
    server_name = '[台服1服]' if str(result['TW_SERVER_ID']) == '1' else '[台服其他服]'
    # 不同版本
    add_msg = ''
    if len(result['VIEWER_ID']) == 9 and ('VIEWER_ID_highBits' not in result or result['VIEWER_ID_highBits'] == '0'):
        # 最老的版本
        version = '【旧版】'
        result['VIEWER_ID'] = result['TW_SERVER_ID'] + result['VIEWER_ID']
        result['SHORT_UDID'] = result['TW_SERVER_ID'] + result['SHORT_UDID']
    elif len(result['VIEWER_ID']) == 10 and result['VIEWER_ID_highBits'] == '0':
        # v4.0.0+版本 | 2023-05-10更新后
        version = '【新版V1】'
    elif result['VIEWER_ID_highBits'] == '1':
        # v4.0.2+版本 | 2023-07-20更新后
        version = '【新版V2】'
        result['VIEWER_ID'] = encode_high_bit(result['VIEWER_ID'], result['TW_SERVER_ID'])
    elif result['SHORT_UDID_highBits'] == '1':
        # v4.0.2+版本 | 2023-07-20更新后
        version = '【新版V2】'
        result['SHORT_UDID'] = encode_high_bit(result['SHORT_UDID'], result['TW_SERVER_ID'])
    else:
        version = '【未适配的新版本】'
        add_msg = '，请反馈至 Github Issue 进行适配'

    sv.logger.info('当前' + server_name + '账号配置文件使用的是' + version + '用户文件' + add_msg)

    return result


# 高位补足简易算法
def encode_high_bit(id_str, server):
    old_id = int(id_str)
    server_old_id = int(server)

    # 转二进制
    server_id = bin(server_old_id).replace('0b', '')
    bin_id = bin(old_id).replace('0b', '')

    # 补位
    diff = 30 - len(bin_id)

    new_id = server_id
    for i in range(diff):
        new_id += '0'

    new_id += bin_id

    # 转回10进值
    dec_from_bin = int(new_id, 2)
    return str(dec_from_bin)
