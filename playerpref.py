from base64 import b64decode
from re import finditer
from struct import unpack
from urllib.parse import unquote

from hoshino import logger

key = b'e806f6'


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
    # 如果是旧版配置文件 | 需要加上服务器编号
    server_name = '[台服1服]' if str(result['TW_SERVER_ID']) == '1' else '[台服其他服]'
    version = '【旧版】' if len(result['VIEWER_ID']) == 9 else '【新版】'
    logger.info('当前' + server_name + '账号配置文件使用的是' + version + '用户文件')

    if len(result['VIEWER_ID']) == 9:
        result['VIEWER_ID'] = result['TW_SERVER_ID'] + result['VIEWER_ID']
    if len(result['SHORT_UDID']) == 9:
        result['SHORT_UDID'] = result['TW_SERVER_ID'] + result['SHORT_UDID']
    return result
