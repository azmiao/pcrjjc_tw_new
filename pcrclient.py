import json
import os
from base64 import b64encode, b64decode
from hashlib import md5, sha1
from random import choice
from random import randint

from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad, pad
from msgpack import packb, unpackb

from yuiChyan.config import PROXY
from yuiChyan.http_request import get_session_or_create

# 默认headers
default_headers = {
    'Accept-Encoding': 'deflate, gzip',
    'User-Agent': 'UnityPlayer/2021.3.20f1 (UnityWebRequest/1.0, libcurl/7.84.0-DEV)',
    'Content-Type': 'application/octet-stream',
    'Expect': '100-continue',
    'X-Unity-Version': '2021.3.20f1',
    'APP-VER': '4.4.0',
    'BATTLE-LOGIC-VERSION': '4',
    'BUNDLE-VER': '',
    'DEVICE': '2',
    'DEVICE-ID': '7b1703a5d9b394e24051d7a5d4818f17',
    'DEVICE-NAME': 'OPPO PCRM00',
    'GRAPHICS-DEVICE-NAME': 'Adreno (TM) 640',
    'IP-ADDRESS': '10.0.2.15',
    'KEYCHAIN': '',
    'LOCALE': 'Jpn',
    'PLATFORM-OS-VERSION': 'Android OS 5.1.1 / API-22 (LMY48Z/rel.se.infra.20200612.100533)',
    'REGION-CODE': '',
    'RES-VER': '00150001'
}


class ApiException(Exception):
    def __init__(self, message, code):
        super().__init__(message)
        self.code = code


class PcrClient:

    @staticmethod
    def _makemd5(data_str) -> str:
        return md5((data_str + 'r!I@nt8e5i=').encode('utf8')).hexdigest()

    def __init__(self, udid, short_udid, viewer_id, platform, session_name):
        self.short_udid = short_udid
        self.viewer_id = viewer_id
        self.udid = udid
        self.platform = platform
        self.api_root = f'https://api{"" if platform == "1" else "5"}-pc.so-net.tw'
        self.shouldLogin = True
        self.session_name = session_name

        header_path = os.path.join(os.path.dirname(__file__), 'headers.json')
        with open(header_path, 'r', encoding='UTF-8') as f:
            self.headers = json.load(f)
        self.headers['SID'] = PcrClient._makemd5(viewer_id + udid)
        # 手机类型：苹果/安卓
        self.headers['platform'] = '2'

    @staticmethod
    def create_key() -> bytes:
        return bytes([ord('0123456789abcdef'[randint(0, 15)]) for _ in range(32)])

    def _get_iv(self) -> bytes:
        return self.udid.replace('-', '')[:16].encode('utf8')

    def pack(self, data: object, key: bytes) -> tuple:
        aes = AES.new(key, AES.MODE_CBC, self._get_iv())
        packed = packb(data,
                       use_bin_type=False
                       )
        return packed, aes.encrypt(pad(packed, 16)) + key

    def encrypt(self, data: str, key: bytes) -> bytes:
        aes = AES.new(key, AES.MODE_CBC, self._get_iv())
        return aes.encrypt(pad(data.encode('utf8'), 16)) + key

    def decrypt(self, data: bytes):
        data = b64decode(data.decode('utf8'))
        aes = AES.new(data[-32:], AES.MODE_CBC, self._get_iv())
        return aes.decrypt(data[:-32]), data[-32:]

    def unpack(self, data: bytes):
        data = b64decode(data.decode('utf8'))
        aes = AES.new(data[-32:], AES.MODE_CBC, self._get_iv())
        dec = unpad(aes.decrypt(data[:-32]), 16)
        return unpackb(dec,
                       strict_map_key=False
                       ), data[-32:]

    alphabet = '0123456789'

    @staticmethod
    def _encode(dat: str) -> str:
        return f'{len(dat):0>4x}' + ''.join(
            [(chr(ord(dat[int(i / 4)]) + 10) if i % 4 == 2 else choice(PcrClient.alphabet)) for i in
             range(0, len(dat) * 4)]) + PcrClient._iv_string()

    @staticmethod
    def _iv_string() -> str:
        return ''.join([choice(PcrClient.alphabet) for _ in range(32)])

    async def callapi(self, api_url: str, request: dict, noerr: bool = False):
        key = PcrClient.create_key()

        try:
            if self.viewer_id is not None:
                request['viewer_id'] = b64encode(self.encrypt(str(self.viewer_id), key))
                request['tw_server_id'] = str(self.platform)
            packed, crypto = self.pack(request, key)
            self.headers['PARAM'] = sha1(
                (self.udid + api_url + b64encode(packed).decode('utf8') + str(self.viewer_id)).encode(
                    'utf8')).hexdigest()
            self.headers['SHORT-UDID'] = PcrClient._encode(self.short_udid)

            session = get_session_or_create(self.session_name, True, PROXY)
            resp = await session.post(self.api_root + api_url,
                                      data=crypto,
                                      headers=self.headers,
                                      timeout=5)
            response = resp.content

            response = self.unpack(response)[0]

            data_headers = response['data_headers']

            if 'viewer_id' in data_headers:
                self.viewer_id = data_headers['viewer_id']

            if 'required_res_ver' in data_headers:
                self.headers['RES-VER'] = data_headers['required_res_ver']

            data = response['data']
            if not noerr and 'server_error' in data:
                data = data['server_error']
                code = data_headers['result_code']
                print(f'pcr_client: {api_url} api failed code = {code}, {data}')
                raise ApiException(data['message'], data['status'])

            print(f'pcr_client: {api_url} api called')

            return data
        except Exception as _:
            self.shouldLogin = True
            raise

    async def login(self):

        await self.callapi('/check/check_agreement', {})
        await self.callapi('/check/game_start', {})
        await self.callapi('/load/index', {
            'carrier': 'Android'
        })

        self.shouldLogin = False
