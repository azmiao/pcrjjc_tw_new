from urllib.parse import unquote
from re import finditer
from base64 import b64decode
from struct import unpack

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
            key = _deckey(g[0]).decode('utf8')
        except:
            continue
        val = _decval(key, g[1])
        if key == 'UDID':
            val = ''.join([chr(val[4 * i + 6] - 10) for i in range(36)])
        elif key == 'SHORT_UDID_lowBits':
            val = str(unpack('I', val)[0])
            key = 'SHORT_UDID'
        elif key == 'VIEWER_ID_lowBits':
            val = str(unpack('I', val)[0])
            key = 'VIEWER_ID'
        elif len(val) == 4:
            val = str(unpack('i', val)[0])
        result[key] = val
        #except:
        #    pass
    if len(result['VIEWER_ID'])==9:
        result['VIEWER_ID'] = result['TW_SERVER_ID']+result['VIEWER_ID']
    if len(result['SHORT_UDID'])==9:
        result['SHORT_UDID'] = result['TW_SERVER_ID']+result['SHORT_UDID']
    return result
