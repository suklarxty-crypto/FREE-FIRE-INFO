# main.py
# ═══════════════════════════════════════════════════════════
#   Free Fire Account Generator + Play Check — Vercel
#   Developer : @KINGFFAIAK47x
#   URL: /api/lookup/<id>=<api_key>?region=IND[&jwt=eyJ...]
# ═══════════════════════════════════════════════════════════
import os
import sys
import json
import time
import random
import base64
import hashlib
import hmac
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import wraps

import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import urllib3

from flask import Flask, request, jsonify

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# ═══════════════════════════════════════════════════════════
#  CONFIG
# ═══════════════════════════════════════════════════════════
DEVELOPER           = "@KINGFFAIAK47x"
API_KEY             = os.environ.get("FF_API_KEY", "AKJMA")
DEFAULT_REGION      = os.environ.get("FF_DEFAULT_REGION", "IND")
VALID_REGIONS       = {"IND", "SAC", "US", "BR", "ME"}
DEFAULT_BAN_RETRIES = int(os.environ.get("FF_BAN_RETRIES", "3"))

IS_VERCEL   = bool(os.environ.get("VERCEL"))
OUTPUT_FILE = os.environ.get("FF_OUTPUT_FILE",
                             "/tmp/accounts.json" if IS_VERCEL else "accounts.json")


def log_info(m):  print(f"[i] {m}", flush=True)
def log_ok(m):    print(f"[+] {m}", flush=True)
def log_warn(m):  print(f"[!] {m}", flush=True)
def log_err(m):   print(f"[-] {m}", flush=True)
def log_debug(m): print(f"    {m}", flush=True)


# ═══════════════════════════════════════════════════════════
#  CRYPTO CONSTANTS
# ═══════════════════════════════════════════════════════════
AES_KEY = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
AES_IV  = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])

CLIENT_SECRET = "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3"
APP_ID        = 100067

OAUTH_REGISTER_URL    = "https://100067.connect.garena.com/api/v2/oauth/guest:register"
OAUTH_TOKEN_URL       = "https://100067.connect.garena.com/oauth/guest/token/grant"
MAJOR_REGISTER_URL    = "https://loginbp.ppmainecoonghj.com/MajorRegister"
NEWBIE_URL            = "https://loginbp.ppmainecoonghj.com/ChooseNewbieChoice"
MAJOR_LOGIN_URL       = "https://loginbp.ppmainecoonghj.com/MajorLogin"
GENERATE_NICKNAME_URL = "https://loginbp.ppmainecoonghj.com/GenerateNickname"

XOR_KEY = [0x30,0x30,0x30,0x32,0x30,0x31,0x37,0x30,0x30,0x30,0x30,0x30,0x32,0x30,0x31,0x37,
           0x30,0x30,0x30,0x30,0x30,0x32,0x30,0x31,0x37,0x30,0x30,0x30,0x30,0x30,0x32,0x30]

FIELD_22_HEX = (
    "474752450101010062020000a78910bd098e3ff2e4345d59a31db114ea088f37e32e65"
    "212ff96621793d9eb78720d0bf2ac95176569765247ada5eb01376b3b9931794a4946"
    "d76ef8890779f3f2129317e6e1cb2fdcf7b06247cea343b8d4f167eff85a2e1dfe99"
    "b4583a7e1a155dbe7f7f85cff3b223eb77222ec1228f3ee1ef6ce7f8ca24b00a554"
    "e497328812f8df74c82d519ae3e3ceab436eb145e8a517089a7cef6a4efb22214b2"
    "a4b19989b74807584afe5e52825e7ac60e19a596a9bf02d961de6a0ed2515ec6023"
    "fdb7684d9464b97b21c527ce61b6bee4ef30d20a1fa33a996952d44d44e44f2f86c"
    "768aaf2a7808ad60f91048dca0207961ba7c2555c48341b30190debc775edb2cee24"
    "4cf51fca3760ce4388be2db45e80b813b5beb9c784007b7762d7a1e428affc8a3a4"
    "cd76cbaef648a274297fde33233dccd3f272cb77f39a1affe0365a24954111f768f72"
    "0e77535af024bea2b2726c3bac992374755c3deacf09235e6865d456e651680d115a"
    "751a797225eaacdf9a513cf104526e1a32e5296e111a33ae581a63850837921df848"
    "9adfd41ea895b7cf3f5b2e45d538a6e4f032f590ccbb7daf5fa9c50adadee0799661"
    "4c3f957bda349e6c484fdf55970d1943ad7955a76671298b6d98b636b69ebde6bc94"
    "dbd93ac3393a6ae230130445b2d744189167854a5617be2393e7d8fbb5719a1b4754"
    "1ba466167e3e05a6c244f1301ee2035acf94dffc8adbde747d5cd85e35ead3acc372"
    "a59c4220e54bf63f9d80485f3de2518495c1d0f78c911d2da595911fd2a1989cf17"
    "cf3ded5f6c92dea64d675c555c11df92d6c517ca5d0d61a8962f43f76ec7e87596c"
    "8325ebf9ab0f8e6d2eca33c511ceac6980906ebd68c478665591dcecf788ec6ef34c"
    "fbe3fcc279c6147c5bf91cd43cdc9704236"
)

# No cross-region fallback — IND only → IND host
PLAYER_INFO_HOSTS = {
    "IND": ["client.ind.freefiremobile.com"],
    "SAC": ["client.sac.freefiremobile.com"],
    "US":  ["client.us.freefiremobile.com"],
    "BR":  ["client.br.freefiremobile.com"],
    "ME":  ["client.me.freefiremobile.com"],
}

# ⭐ 17 labeled fields — same set the CLI shows
SUMMARY_FIELDS = [
    ("account_id",   ["6.3", "7.1", "9.1"]),
    ("nickname",     ["8.2"]),
    ("signature",    ["9.9"]),
    ("region",       ["9.14.1.1", "7.5"]),
    ("br_rank_tier", ["6.2"]),
    ("br_level",     ["6.5"]),
    ("cs_rank_name", ["7.3"]),
    ("avatar_id",    ["2.1"]),
    ("banner_id",    ["2.3"]),
    ("open_id_hash", ["2.4"]),
    ("language",     ["7.18", "18"]),
    ("pet_id",       ["7.19", "19"]),
    ("pet_level",    ["7.20", "20"]),
    ("pet_exp",      ["7.21", "21"]),
    ("title_id",     ["7.24", "24"]),
    ("release_ver",  ["7.50", "50"]),
    ("first_seen",   ["7.44", "44"]),
]


# ═══════════════════════════════════════════════════════════
#  IN-MEMORY JWT CACHE
# ═══════════════════════════════════════════════════════════
_jwt_cache = {}
_jwt_cache_lock = threading.Lock()
JWT_CACHE_TTL = 300


def cache_get_jwt(region):
    with _jwt_cache_lock:
        entry = _jwt_cache.get(region)
        if not entry:
            return None
        jwt, ts = entry
        if time.time() - ts > JWT_CACHE_TTL:
            del _jwt_cache[region]
            return None
        return jwt


def cache_set_jwt(region, jwt):
    if not jwt:
        return
    with _jwt_cache_lock:
        _jwt_cache[region] = (jwt, time.time())


# ═══════════════════════════════════════════════════════════
#  FILE STORE
# ═══════════════════════════════════════════════════════════
_file_lock = threading.Lock()


def _load_accounts():
    try:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []


def _write_accounts(data):
    try:
        tmp = OUTPUT_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, OUTPUT_FILE)
    except Exception as e:
        log_warn(f"write failed: {e}")


def save_account(account):
    with _file_lock:
        data = _load_accounts()
        for i, a in enumerate(data):
            if a.get("uid") == account.get("uid"):
                data[i] = account
                _write_accounts(data)
                return
        data.append(account)
        _write_accounts(data)


# ═══════════════════════════════════════════════════════════
#  PROTOBUF WRITER
# ═══════════════════════════════════════════════════════════
def write_varint(v: int) -> bytes:
    if v < 0:
        v = v & 0xFFFFFFFFFFFFFFFF
    out = []
    while v > 127:
        out.append((v & 0x7F) | 0x80)
        v >>= 7
    out.append(v & 0x7F)
    return bytes(out)


def write_varint_field(f, v):
    return write_varint((f << 3) | 0) + write_varint(v)


def write_string_field(f, v):
    b = v.encode("utf-8") if isinstance(v, str) else v
    return write_varint((f << 3) | 2) + write_varint(len(b)) + b


def write_bytes_field(f, v):
    return write_varint((f << 3) | 2) + write_varint(len(v)) + v


def assemble_proto(fields):
    data = bytearray()
    for k in sorted(fields.keys()):
        v = fields[k]
        if isinstance(v, bool):
            data.extend(write_varint_field(k, 1 if v else 0))
        elif isinstance(v, int):
            data.extend(write_varint_field(k, v))
        elif isinstance(v, str):
            data.extend(write_string_field(k, v))
        elif isinstance(v, (bytes, bytearray)):
            data.extend(write_bytes_field(k, bytes(v)))
        else:
            raise TypeError(f"bad type for key {k}: {type(v)}")
    return bytes(data)


# ═══════════════════════════════════════════════════════════
#  PROTOBUF READER
# ═══════════════════════════════════════════════════════════
def read_varint(data, offset):
    r, s = 0, 0
    while True:
        if offset >= len(data):
            raise ValueError("varint truncated")
        b = data[offset]
        offset += 1
        r |= (b & 0x7F) << s
        if not (b & 0x80):
            break
        s += 7
        if s > 63:
            raise ValueError("varint too long")
    return r, offset


def parse_proto(data):
    out, off, n = {}, 0, len(data)
    while off < n:
        try:
            tag, off = read_varint(data, off)
        except Exception:
            break
        f, w = tag >> 3, tag & 0x7
        if f == 0:
            break
        try:
            if w == 0:
                v, off = read_varint(data, off)
                out[f] = v
            elif w == 2:
                ln, off = read_varint(data, off)
                if off + ln > n:
                    break
                val = data[off:off + ln]
                off += ln
                try:
                    out[f] = val.decode("utf-8")
                except Exception:
                    out[f] = val.hex()
            elif w == 5:
                if off + 4 > n:
                    break
                off += 4
            elif w == 1:
                if off + 8 > n:
                    break
                off += 8
            else:
                break
        except Exception:
            break
    return out


def _add_field(d, f, v):
    if f in d:
        if not isinstance(d[f], list):
            d[f] = [d[f]]
        d[f].append(v)
    else:
        d[f] = v


def _try_utf8_printable(val):
    if not val or len(val) < 2:
        return None
    try:
        s = val.decode("utf-8")
    except UnicodeDecodeError:
        return None
    if not s:
        return None
    printable = sum(1 for c in s if c.isprintable() or c in '\n\r\t')
    if printable < len(s) * 0.9:
        return None
    return s


def _is_valid_full_proto(val):
    if not val or len(val) < 2:
        return False
    f0, w0 = val[0] >> 3, val[0] & 7
    if f0 == 0 or w0 not in (0, 1, 2, 5):
        return False
    off, n, count = 0, len(val), 0
    while off < n:
        try:
            tag, off = read_varint(val, off)
        except Exception:
            return False
        ff, ww = tag >> 3, tag & 7
        if ff == 0:
            return False
        count += 1
        try:
            if ww == 0:
                _, off = read_varint(val, off)
            elif ww == 2:
                ln, off = read_varint(val, off)
                if off + ln > n:
                    return False
                off += ln
            elif ww == 5:
                if off + 4 > n:
                    return False
                off += 4
            elif ww == 1:
                if off + 8 > n:
                    return False
                off += 8
            else:
                return False
        except Exception:
            return False
    return off == n and count >= 1


def parse_proto_rich(data, depth=0, max_depth=8):
    if depth > max_depth or not data:
        return {}
    out, off, n = {}, 0, len(data)
    while off < n:
        try:
            tag, off = read_varint(data, off)
        except Exception:
            break
        f, w = tag >> 3, tag & 7
        if f == 0:
            break
        try:
            if w == 0:
                v, off = read_varint(data, off)
                _add_field(out, f, v)
            elif w == 2:
                ln, off = read_varint(data, off)
                if off + ln > n:
                    break
                val = data[off:off + ln]
                off += ln
                if (len(val) >= 2
                        and _is_valid_full_proto(val)
                        and _try_utf8_printable(val) is None):
                    nested = parse_proto_rich(val, depth + 1, max_depth)
                    if nested:
                        _add_field(out, f, nested)
                        continue
                s = _try_utf8_printable(val)
                if s is not None:
                    _add_field(out, f, s)
                    continue
                _add_field(out, f, val.hex())
            elif w == 5:
                if off + 4 > n:
                    break
                _add_field(out, f, "f32:" + data[off:off + 4].hex())
                off += 4
            elif w == 1:
                if off + 8 > n:
                    break
                _add_field(out, f, "f64:" + data[off:off + 8].hex())
                off += 8
            else:
                break
        except Exception:
            break
    return out


# ═══════════════════════════════════════════════════════════
#  AES + XOR
# ═══════════════════════════════════════════════════════════
def aes_encrypt(plain):
    return AES.new(AES_KEY, AES.MODE_CBC, AES_IV).encrypt(pad(plain, AES.block_size))


def aes_decrypt(ct):
    if not ct or len(ct) % 16 != 0:
        return ct
    try:
        try:
            return unpad(AES.new(AES_KEY, AES.MODE_CBC, AES_IV).decrypt(ct), AES.block_size)
        except ValueError:
            return AES.new(AES_KEY, AES.MODE_CBC, AES_IV).decrypt(ct)
    except Exception:
        return ct


def xor_open_id(open_id: str) -> bytes:
    b = open_id.encode("utf-8")
    return bytes(x ^ XOR_KEY[i % len(XOR_KEY)] for i, x in enumerate(b))


# ═══════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════
def clean_jwt(jwt):
    if not isinstance(jwt, str):
        return jwt
    return jwt.strip().replace("\n", "").replace("\r", "").replace(" ", "")


def retry(func, retries=3, delay=1.0, backoff=2.0, label=""):
    last = None
    for attempt in range(1, retries + 1):
        try:
            return func()
        except Exception as e:
            last = e
            if attempt < retries:
                time.sleep(delay * (backoff ** (attempt - 1)))
    if label:
        log_debug(f"retry exhausted [{label}]: {last}")
    return None


def new_session():
    s = requests.Session()
    s.verify = False
    s.trust_env = False
    return s


# ═══════════════════════════════════════════════════════════
#  STEPS 1-6
# ═══════════════════════════════════════════════════════════
def register_guest(session, password):
    payload = {"app_id": APP_ID, "client_type": 2, "password": password, "source": 2}
    body = json.dumps(payload, separators=(",", ":"))
    sig = hmac.new(CLIENT_SECRET.encode(), body.encode(), hashlib.sha256).hexdigest()
    headers = {
        "User-Agent": "GarenaMSDK/4.0.42(KB2003 ;Android 13;en;HK;app 2.130.1 2019118332;)",
        "Accept": "application/json",
        "Content-Type": "application/json; charset=utf-8",
        "Connection": "Keep-Alive",
        "Accept-Encoding": "gzip",
        "Authorization": f"Signature {sig}",
    }
    r = session.post(OAUTH_REGISTER_URL, data=body, headers=headers, timeout=15, verify=False)
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}")
    d = r.json()
    if d.get("code") != 0:
        raise RuntimeError(f"register failed: {d.get('message')}")
    return str(d["data"]["uid"])


def get_token(session, uid, password):
    payload = {
        "uid": uid, "password": password, "response_type": "token",
        "client_type": "2", "client_secret": CLIENT_SECRET, "client_id": "100067",
    }
    headers = {
        "User-Agent": "GarenaMSDK/4.0.30",
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "Connection": "Keep-Alive",
    }
    r = session.post(OAUTH_TOKEN_URL, data=payload, headers=headers, timeout=30, verify=False)
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}")
    d = r.json()
    at, oi = d.get("access_token"), d.get("open_id")
    if not at or not oi:
        raise RuntimeError("token missing fields")
    return at, oi


def generate_nickname(session, open_id):
    plain = assemble_proto({1: "en", 2: open_id})
    encrypted = aes_encrypt(plain)
    host = GENERATE_NICKNAME_URL.split("/")[2]
    headers = {
        "Accept-Encoding": "gzip", "Authorization": "Bearer",
        "Connection": "Keep-Alive",
        "Content-Type": "application/x-www-form-urlencoded",
        "Host": host, "ReleaseVersion": "OB55",
        "User-Agent": "UnityPlayer/2018.4.12f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)",
        "X-GA": "v1 1", "X-Unity-Version": "2018.4.12f1",
    }
    r = session.post(GENERATE_NICKNAME_URL, data=encrypted, headers=headers, timeout=30, verify=False)
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}")
    name = r.text.strip()
    if not name:
        raise RuntimeError("empty nickname")
    return name


def send_major_register(session, nickname, access_token, open_id, region_code):
    fields = {
        1: nickname, 2: access_token, 3: open_id,
        5: 102000007, 6: 4, 7: 1, 13: 1,
        14: xor_open_id(open_id), 15: region_code, 16: 2,
        20: "2.133.8", 21: 1, 22: bytes.fromhex(FIELD_22_HEX),
    }
    encrypted = aes_encrypt(assemble_proto(fields))
    headers = {
        "Host": MAJOR_REGISTER_URL.split("/")[2],
        "User-Agent": "UnityPlayer/2018.4.12f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)",
        "Accept": "*/*", "Accept-Encoding": "deflate, gzip",
        "X-GA-SV": str(int(time.time())), "Authorization": "Bearer",
        "X-GA": "v1 1", "ReleaseVersion": "OB55",
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Unity-Version": "2018.4.12f1",
        "Content-Length": str(len(encrypted)),
    }
    r = session.post(MAJOR_REGISTER_URL, data=encrypted, headers=headers, timeout=30, verify=False)
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}")
    parsed = parse_proto(r.content)
    aid = parsed.get(3)
    if not aid:
        dec = aes_decrypt(r.content)
        if dec and dec != r.content:
            parsed = parse_proto(dec)
            aid = parsed.get(3)
    if not aid:
        raise RuntimeError("no account_id")
    return int(aid)


def send_newbie(session, account_id, choice=3):
    plain = assemble_proto({1: int(account_id), 2: 1, 3: int(choice)})
    encrypted = aes_encrypt(plain)
    headers = {
        "Host": "loginbp.ppmainecoonghj.com",
        "User-Agent": "UnityPlayer/2018.4.12f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)",
        "Accept": "*/*", "Accept-Encoding": "deflate, gzip",
        "X-GA-SV": str(int(time.time())), "Authorization": "Bearer",
        "X-GA": "v1 1", "ReleaseVersion": "OB55",
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Unity-Version": "2018.4.12f1",
        "Content-Length": str(len(encrypted)),
    }
    r = session.post(NEWBIE_URL, headers=headers, data=encrypted, timeout=30, verify=False)
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}")
    return True


def send_major_login(session, access_token, open_id, region_code, platform="4"):
    fields = {
        3: time.strftime("%Y-%m-%d %H:%M:%S"),
        4: "free fire", 5: 1, 7: "2.133.9",
        8: "Android OS 10 / API-29 (QP1A.190711.020/1617006012)",
        9: "Handheld", 10: "Vi India", 11: "WIFI",
        12: 1600, 13: 720, 14: "320",
        15: "ARM64 FP ASIMD AES | 2301 | 8", 16: 2799,
        17: "PowerVR Rogue GE8320",
        18: "OpenGL ES 3.2 build 1.11@5425693",
        19: "Google|9f7d6b8b-b10c-454a-852d-06332cd498eb",
        20: f"{random.randint(1,223)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}",
        21: "en", 22: open_id, 23: str(platform),
        24: "Handheld", 25: "realme RMX2189", 26: region_code,
        29: access_token, 30: 1, 41: "Vi India", 42: "WIFI",
        57: "1ac4b80ecf0478a44203bf8fac6120f5",
        60: 19799, 61: 2536, 62: 5056, 64: 2768,
        65: 19999, 66: 2536, 67: 19799, 73: 1,
        74: "/data/app/com.dts.freefiremax-ShI7E0dK8p1IiZ785pvuVQ==/lib/arm64",
        76: 2,
        77: "38f4751a330688ab124c2c804cec90a5|/data/app/com.dts.freefiremax-ShI7E0dK8p1IiZ785pvuVQ==/base.apk",
        78: 2, 79: 2, 81: "64", 83: "2019118527",
        86: "OpenGLES3", 87: 3071, 88: 4, 92: 67920,
        93: "android_max",
        94: "KqsHT+UrR1HKqb6+1db+Ofei+NtZr2+hbiBo3yKDL8w+8E3S5qF2IgEEe1fFQFyHRzl4iyHjHp+QsfeLbjJ6+DidTiKxm0ak2uYYa6QR4nAUdlZR",
        95: 111107, 96: '{"cur_rate":null,"support_etc2":true}',
        97: 1, 98: 1, 99: "4", 100: "4", 102: "",
        104: 83812, 105: 1,
        106: "https://dl-bs.ggpolarbear.com/live/ABHotUpdates/|https://core-bs.ggpolarbear.com/live/ABHotUpdates/|a4332cb1c1a84e51dd77441e4856ed5a",
        107: "1.9393e7b8e53e8aeb",
    }
    encrypted = aes_encrypt(assemble_proto(fields))
    headers = {
        "Host": "loginbp.ppmainecoonghj.com",
        "User-Agent": "UnityPlayer/2018.4.12f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)",
        "Accept": "*/*", "Accept-Encoding": "deflate, gzip",
        "X-GA-SV": str(int(time.time())), "Authorization": "Bearer",
        "X-GA": "v1 1", "ReleaseVersion": "OB55",
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Unity-Version": "2018.4.12f1",
        "Content-Length": str(len(encrypted)),
    }
    r = session.post(MAJOR_LOGIN_URL, data=encrypted, headers=headers, timeout=30, verify=False)
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}")
    raw = r.content
    candidates = []
    dec = aes_decrypt(raw)
    if dec and dec != raw:
        candidates.append(dec)
    if len(raw) > 64:
        candidates.append(raw[64:])
    candidates.append(raw)
    for buf in candidates:
        if not buf:
            continue
        try:
            parsed = parse_proto(buf)
        except Exception:
            continue
        jwt = parsed.get(8)
        if isinstance(jwt, bytes):
            try:
                jwt = jwt.decode("utf-8", "ignore")
            except Exception:
                jwt = ""
        jwt = clean_jwt(jwt)
        if isinstance(jwt, str) and jwt.startswith("eyJ") and jwt.count(".") == 2:
            sixteen = []
            for fnum in sorted(parsed.keys()):
                v = parsed[fnum]
                if isinstance(v, (bytes, bytearray)) and len(v) == 16:
                    sixteen.append(bytes(v))
                elif isinstance(v, str):
                    try:
                        b = bytes.fromhex(v)
                        if len(b) == 16:
                            sixteen.append(b)
                    except Exception:
                        pass
            k = sixteen[-2] if len(sixteen) >= 2 else AES_KEY
            i_ = sixteen[-1] if len(sixteen) >= 2 else AES_IV
            return jwt, k, i_
    raise RuntimeError("no JWT")


# ═══════════════════════════════════════════════════════════
#  JWT SOURCE PRIORITY
# ═══════════════════════════════════════════════════════════
def _get_saved_jwt(region):
    data = _load_accounts()
    for acc in reversed(data):
        jwt = acc.get("jwt")
        if (isinstance(jwt, str) and jwt.startswith("eyJ")
                and (not region or acc.get("region") == region)):
            return jwt, acc
    return None, None


def _refresh_account_jwt(acc, region_code=None):
    if not acc.get("uid") or not acc.get("password"):
        return None
    region_code = region_code or acc.get("region") or DEFAULT_REGION
    s = new_session()
    try:
        res = get_token(s, acc["uid"], acc["password"])
        if not res:
            return None
        access_token, open_id = res
        login = send_major_login(s, access_token, open_id, region_code)
        if not login:
            return None
        jwt, sk, siv = login
        acc["access_token"] = access_token
        acc["open_id"]      = open_id
        acc["jwt"]          = jwt
        acc["session_key"]  = sk.hex()
        acc["session_iv"]   = siv.hex()
        acc["jwt_refreshed_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        acc["banned"] = False
        save_account(acc)
        cache_set_jwt(region_code, jwt)
        return jwt
    except Exception as e:
        log_debug(f"jwt refresh failed: {e}")
        return None


def get_ephemeral_jwt(region_code, retries=2):
    try:
        acc = _generate_raw(region_code, retries=retries)
        if acc and acc.get("jwt"):
            log_info(f"ephemeral JWT created ({region_code})")
            time.sleep(2)
            return acc["jwt"]
    except Exception as e:
        log_warn(f"ephemeral jwt failed: {e}")
    return None


# ═══════════════════════════════════════════════════════════
#  PLAYER INFO
# ═══════════════════════════════════════════════════════════
def _get(parsed, path):
    cur = parsed
    for part in path.split("."):
        if cur is None or not isinstance(cur, dict):
            return None
        idx = None
        if "[" in part:
            kp, ip = part.split("[", 1)
            try:
                idx = int(ip.rstrip("]"))
            except Exception:
                return None
            part = kp
        try:
            k = int(part)
        except ValueError:
            return None
        if k not in cur:
            return None
        cur = cur[k]
        if idx is not None:
            if not isinstance(cur, list) or idx >= len(cur):
                return None
            cur = cur[idx]
    return cur


def _extract_response_account_id(parsed):
    for path in ("6.3", "7.1", "9.1"):
        v = _get(parsed, path)
        if isinstance(v, int):
            return v
    return None


def _try_parse_player_response(raw):
    candidates = []
    dec = aes_decrypt(raw)
    if dec and dec != raw:
        candidates.append(dec)
    if len(raw) > 64:
        candidates.append(raw[64:])
    if len(raw) > 16:
        candidates.append(raw[16:])
    candidates.append(raw)
    for buf in candidates:
        if not buf or len(buf) < 2:
            continue
        try:
            p = parse_proto_rich(buf)
        except Exception:
            continue
        if p and len(p) >= 2:
            return p
    return None


def fetch_player_info(session, account_id, jwt, region, requested_aid=None):
    region = (region or DEFAULT_REGION).upper()
    hosts = PLAYER_INFO_HOSTS.get(region, PLAYER_INFO_HOSTS["IND"])
    account_id = int(account_id)
    requested_aid = int(requested_aid if requested_aid is not None else account_id)

    payload_variants = [
        {1: account_id, 2: region},
        {1: account_id, 2: "en"},
        {1: account_id},
    ]
    per_host_errors = {}

    for host in hosts:
        url = f"https://{host}/GetPlayerPersonalShow"
        host_first_err = None
        for pv_idx, pfields in enumerate(payload_variants):
            try:
                encrypted = aes_encrypt(assemble_proto(pfields))
                headers = {
                    "Host": host,
                    "User-Agent": "UnityPlayer/2018.4.12f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)",
                    "Accept": "*/*", "Accept-Encoding": "deflate, gzip",
                    "X-GA-SV": str(int(time.time())),
                    "Authorization": f"Bearer {jwt}" if jwt else "Bearer",
                    "X-GA": "v1 1", "ReleaseVersion": "OB55",
                    "Content-Type": "application/x-www-form-urlencoded",
                    "X-Unity-Version": "2018.4.12f1",
                    "Content-Length": str(len(encrypted)),
                }
                r = session.post(url, headers=headers, data=encrypted,
                                 timeout=20, verify=False)

                if r.status_code != 200:
                    err = f"HTTP {r.status_code}"
                    if r.status_code == 401:
                        err += " (JWT required/expired)"
                    if host_first_err is None:
                        host_first_err = err
                    continue
                if not r.content:
                    if host_first_err is None:
                        host_first_err = "empty response"
                    continue

                parsed = _try_parse_player_response(r.content)
                if not parsed:
                    if host_first_err is None:
                        host_first_err = "decode failed"
                    continue

                returned_aid = _extract_response_account_id(parsed)
                if returned_aid is not None and returned_aid != requested_aid:
                    msg = f"wrong account returned ({returned_aid} != {requested_aid})"
                    log_warn(f"  {host}/v{pv_idx}: {msg}")
                    if host_first_err is None:
                        host_first_err = msg
                    continue

                return parsed, host

            except requests.exceptions.ConnectionError as e:
                msg = str(e)
                host_first_err = ("DNS failed"
                                  if ("NameResolutionError" in msg or "getaddrinfo" in msg)
                                  else "connection error")
                break
            except Exception as e:
                if host_first_err is None:
                    host_first_err = str(e)[:80]

        if host_first_err:
            per_host_errors[host] = host_first_err

    if per_host_errors:
        raise RuntimeError(" | ".join(f"{h}: {e}" for h, e in per_host_errors.items()))
    raise RuntimeError("player info failed — no host reachable")


# ═══════════════════════════════════════════════════════════
#  BAN CHECK + PROFILE EXTRACTION
# ═══════════════════════════════════════════════════════════
def is_banned(parsed):
    if not parsed or len(parsed) < 2:
        return True, "empty response"
    if not _get(parsed, "8.2"):
        return True, "missing nickname"
    if not (_get(parsed, "9.14.1.1") or _get(parsed, "7.5")):
        return True, "missing region"
    return False, None


def extract_profile(parsed):
    """Extract all 17 labeled fields (flat dict)."""
    out = {}
    for label, paths in SUMMARY_FIELDS:
        for p in paths:
            v = _get(parsed, p)
            if v is not None:
                out[label] = v
                break
    return out


def _count_leaves(obj):
    """Count every scalar leaf in nested structure."""
    if isinstance(obj, dict):
        return sum(_count_leaves(v) for v in obj.values()) or len(obj)
    if isinstance(obj, list):
        return sum(_count_leaves(x) for x in obj)
    return 1


# ═══════════════════════════════════════════════════════════
#  GENERATE
# ═══════════════════════════════════════════════════════════
def _generate_raw(region_code, retries=3):
    session = new_session()
    password = hashlib.sha256(os.urandom(32)).hexdigest().upper()

    uid = retry(lambda: register_guest(session, password), retries=retries, label="register")
    if not uid:
        return None

    res = retry(lambda: get_token(session, uid, password), retries=retries, label="token")
    if not res:
        return None
    access_token, open_id = res

    nickname = retry(lambda: generate_nickname(session, open_id), retries=retries, label="nickname")
    if not nickname:
        return None

    account_id = retry(
        lambda: send_major_register(session, nickname, access_token, open_id, region_code),
        retries=retries, label="major_register",
    )
    if not account_id:
        return None

    retry(lambda: send_newbie(session, account_id, 3), retries=retries, label="newbie")

    login = retry(
        lambda: send_major_login(session, access_token, open_id, region_code),
        retries=retries, label="major_login",
    )
    if not login:
        return None
    jwt, session_key, session_iv = login

    cache_set_jwt(region_code, jwt)

    return {
        "uid": uid, "password": password, "nickname": nickname,
        "open_id": open_id, "access_token": access_token,
        "account_id": account_id, "region": region_code, "jwt": jwt,
        "session_key": session_key.hex(), "session_iv": session_iv.hex(),
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "banned": False,
    }


def generate_one(region_code, retries=3, fetch_info=False):
    acc = _generate_raw(region_code, retries=retries)
    if not acc:
        return None
    log_ok(f"generated {acc['uid']}  nick={acc['nickname']}  acc_id={acc['account_id']}")
    if fetch_info:
        try:
            s = new_session()
            info, _ = fetch_player_info(s, acc["account_id"], acc["jwt"],
                                        region_code, requested_aid=acc["account_id"])
            acc["player_info"] = info
            acc["verified"] = True
        except Exception as e:
            log_warn(f"info fetch failed: {e}")
    return acc


def generate_with_ban_retry(region_code, retries=3, max_ban_retries=DEFAULT_BAN_RETRIES):
    for attempt in range(1, max_ban_retries + 1):
        log_info(f"[{region_code}] attempt {attempt}/{max_ban_retries}")
        try:
            acc = generate_one(region_code, retries, fetch_info=False)
        except Exception as e:
            log_err(f"gen exception: {e}")
            continue
        if not acc:
            continue

        try:
            time.sleep(1.5)
            s = new_session()
            info, _ = fetch_player_info(s, acc["account_id"], acc["jwt"],
                                        region_code, requested_aid=acc["account_id"])
            banned, reason = is_banned(info)
            if banned:
                log_warn(f"attempt {attempt}: BANNED ({reason}) — retrying")
                acc["banned"] = True
                continue

            acc["player_info"] = info
            acc["verified"] = True
            acc["verified_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            log_ok(f"attempt {attempt}: {acc['uid']} VERIFIED ✓")
            return acc
        except Exception as e:
            log_warn(f"attempt {attempt}: verify failed ({e})")
            continue

    log_err(f"all {max_ban_retries} attempts failed for {region_code}")
    return None


# ═══════════════════════════════════════════════════════════
#  JSON + AUTH
# ═══════════════════════════════════════════════════════════
def json_safe(obj):
    if isinstance(obj, dict):
        return {str(k): json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [json_safe(x) for x in obj]
    if isinstance(obj, bytes):
        return obj.hex()
    if isinstance(obj, (int, float, bool, str)) or obj is None:
        return obj
    return str(obj)


def simplify_account(acc):
    profile = acc.get("player_info")
    summary = extract_profile(profile) if profile else {}
    return {
        "uid":          acc.get("uid"),
        "password":     acc.get("password"),
        "nickname":     acc.get("nickname"),
        "open_id":      acc.get("open_id"),
        "account_id":   acc.get("account_id"),
        "region":       acc.get("region"),
        "jwt":          acc.get("jwt"),
        "session_key":  acc.get("session_key"),
        "session_iv":   acc.get("session_iv"),
        "created_at":   acc.get("created_at"),
        "verified":     acc.get("verified", False),
        "banned":       acc.get("banned", False),
        "profile":      json_safe(summary),
    }


def parse_region(region_str, default=DEFAULT_REGION):
    r = (region_str or default).strip().upper()
    if r not in VALID_REGIONS:
        return default, False
    return r, True


def _key_ok(provided):
    if not provided:
        return False
    try:
        return hmac.compare_digest(provided.strip(), API_KEY)
    except Exception:
        return False


def require_key(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        provided = (request.headers.get("X-API-Key")
                    or request.args.get("api_key")
                    or "").strip()
        if not _key_ok(provided):
            return jsonify({"ok": False, "error": "unauthorized"}), 401
        return f(*args, **kwargs)
    return wrapper


# ═══════════════════════════════════════════════════════════
#  FLASK APP
# ═══════════════════════════════════════════════════════════
app = Flask(__name__)


@app.route("/", methods=["GET"])
@app.route("/api", methods=["GET"])
def index():
    return jsonify({
        "ok": True,
        "service": "FreeFire Account Generator + Play Check",
        "developer": DEVELOPER,
        "version": "1.4.0",
        "lookup_example": "/api/lookup/206746194=YOUR_KEY?region=IND",
        "regions": sorted(VALID_REGIONS),
        "default_region": DEFAULT_REGION,
    })


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "ok": True,
        "developer": DEVELOPER,
        "vercel": IS_VERCEL,
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
    })


# ═══════════════════════════════════════════════════════════
#  ⭐ PRIMARY ENDPOINT
# ═══════════════════════════════════════════════════════════
@app.route("/api/lookup/<path:combined>", methods=["GET"])
def api_lookup(combined):
    try:
        if "=" not in combined:
            return jsonify({
                "ok": False,
                "error": "format: /api/lookup/<id>=<api_key>?region=IND",
                "example": "/api/lookup/206746194=YOUR_KEY?region=IND",
            }), 400

        aid_part, key_part = combined.split("=", 1)
        aid_part, key_part = aid_part.strip(), key_part.strip()

        if not _key_ok(key_part):
            return jsonify({"ok": False, "error": "unauthorized"}), 401

        if not aid_part or not aid_part.isdigit():
            return jsonify({"ok": False, "error": "id must be numeric"}), 400

        region_in = request.args.get("region", DEFAULT_REGION)
        region_code, valid = parse_region(region_in)
        if not valid:
            return jsonify({
                "ok": False,
                "error": f"invalid region '{region_in}' — valid: {sorted(VALID_REGIONS)}",
            }), 400

        saved_acc = None
        for acc in _load_accounts():
            if str(acc.get("uid")) == aid_part:
                saved_acc = acc
                break

        if saved_acc:
            account_id = int(saved_acc.get("account_id") or aid_part)
            region_code = saved_acc.get("region") or region_code
            jwt = saved_acc.get("jwt")
            matched_by = "uid"
        else:
            account_id = int(aid_part)
            jwt = None
            matched_by = "account_id"

        log_info(f"lookup → id={aid_part} ({matched_by}) region={region_code}")

        user_jwt = (request.args.get("jwt") or "").strip()
        if user_jwt and user_jwt.startswith("eyJ"):
            jwt = user_jwt
            log_info("using JWT from query param")
        if not jwt:
            sj, _ = _get_saved_jwt(region_code)
            if sj:
                jwt = sj
                log_info("using saved JWT")
        if not jwt:
            jwt = cache_get_jwt(region_code)
            if jwt:
                log_info("using cached JWT")

        s = new_session()

        try:
            info, _ = fetch_player_info(s, account_id, jwt=jwt,
                                        region=region_code,
                                        requested_aid=account_id)
        except Exception as e:
            err_str = str(e)
            log_warn(f"lookup attempt 1 failed: {err_str}")

            if not jwt or "401" in err_str:
                log_warn("no valid JWT — creating ephemeral")
                eph_jwt = get_ephemeral_jwt(region_code)
                if not eph_jwt:
                    return jsonify({
                        "ok": False,
                        "error": "could not obtain valid JWT",
                        "account_id": account_id,
                        "region": region_code,
                        "hint": "generate an account first, or pass &jwt=eyJ...",
                    }), 502
                try:
                    info, _ = fetch_player_info(s, account_id, jwt=eph_jwt,
                                                region=region_code,
                                                requested_aid=account_id)
                except Exception as e2:
                    return jsonify({
                        "ok": False, "error": str(e2),
                        "account_id": account_id, "region": region_code,
                    }), 502
            else:
                return jsonify({
                    "ok": False, "error": err_str,
                    "account_id": account_id, "region": region_code,
                }), 502

        returned_aid = _extract_response_account_id(info)
        if returned_aid is not None and int(returned_aid) != int(account_id):
            return jsonify({
                "ok": False,
                "error": "server returned wrong account",
                "requested_account_id": account_id,
                "returned_account_id": returned_aid,
                "region": region_code,
                "hint": "pass &jwt=YOUR_OWN_TOKEN to force correct account",
            }), 502

        banned, ban_reason = is_banned(info)
        profile = extract_profile(info)
        raw = json_safe(info)
        leaves = _count_leaves(info)

        return jsonify({
            "ok": True,
            "matched_by": matched_by,
            "input_id": aid_part,
            "account_id": account_id,
            "region": region_code,
            "banned": banned,
            "ban_reason": ban_reason,
            "leaves": leaves,
            "profile": json_safe(profile),
            "raw": raw,
            "developer": DEVELOPER,
        })
    except Exception as e:
        log_err(f"api_lookup: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/generate", methods=["POST"])
@require_key
def api_generate():
    try:
        data = request.get_json(silent=True) or {}
        count       = max(1, min(int(data.get("count", 1)), 10))
        threads     = max(1, min(int(data.get("threads", 2)), 5))
        retries     = max(1, min(int(data.get("retries", 3)), 10))
        ban_retries = max(1, min(int(data.get("ban_retries", DEFAULT_BAN_RETRIES)), 10))
        region_str  = data.get("region", DEFAULT_REGION)

        region_code, valid = parse_region(region_str)
        if not valid:
            return jsonify({
                "ok": False,
                "error": f"invalid region '{region_str}' — valid: {sorted(VALID_REGIONS)}",
            }), 400

        results, failed = [], 0
        t0 = time.time()

        with ThreadPoolExecutor(max_workers=threads) as pool:
            futures = [
                pool.submit(generate_with_ban_retry, region_code, retries, ban_retries)
                for _ in range(count)
            ]
            for f in as_completed(futures):
                try:
                    acc = f.result()
                except Exception as e:
                    log_err(f"worker: {e}")
                    failed += 1
                    continue
                if not acc:
                    failed += 1
                    continue
                save_account(acc)
                results.append(simplify_account(acc))

        elapsed = round(time.time() - t0, 2)
        return jsonify({
            "ok": True,
            "region": region_code,
            "requested": count,
            "generated": len(results),
            "failed": failed,
            "elapsed_seconds": elapsed,
            "accounts": results,
            "vercel_persist_warning": (
                "accounts in /tmp — lost after ~5min on Vercel" if IS_VERCEL else None
            ),
            "developer": DEVELOPER,
        })
    except ValueError as e:
        return jsonify({"ok": False, "error": f"bad input: {e}"}), 400
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/accounts", methods=["GET"])
@require_key
def api_accounts():
    try:
        data = _load_accounts()
        safe = [{
            "uid":         a.get("uid"),
            "nickname":    a.get("nickname"),
            "account_id":  a.get("account_id"),
            "region":      a.get("region"),
            "created_at":  a.get("created_at"),
            "verified":    a.get("verified", False),
            "banned":      a.get("banned", False),
            "has_jwt":     bool(a.get("jwt")),
        } for a in data]
        return jsonify({
            "ok": True, "count": len(safe),
            "accounts": safe, "developer": DEVELOPER,
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/refresh", methods=["POST"])
@require_key
def api_refresh():
    try:
        data = request.get_json(silent=True) or {}
        uid = str(data.get("uid", "")).strip()
        if not uid:
            return jsonify({"ok": False, "error": "uid required"}), 400

        target = None
        for acc in _load_accounts():
            if str(acc.get("uid")) == uid:
                target = acc
                break
        if not target:
            return jsonify({"ok": False, "error": f"account {uid} not found"}), 404

        region_str = data.get("region") or target.get("region", DEFAULT_REGION)
        region_code, _ = parse_region(region_str)
        new_jwt = _refresh_account_jwt(target, region_code)
        if not new_jwt:
            return jsonify({"ok": False, "error": "refresh failed", "uid": uid}), 502

        return jsonify({
            "ok": True, "uid": uid, "jwt": new_jwt,
            "region": region_code,
            "refreshed_at": target.get("jwt_refreshed_at"),
            "developer": DEVELOPER,
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.errorhandler(404)
def not_found(e):
    return jsonify({
        "ok": False,
        "error": "endpoint not found",
        "example": "/api/lookup/206746194=YOUR_KEY?region=IND",
    }), 404


@app.errorhandler(405)
def not_allowed(e):
    return jsonify({"ok": False, "error": "method not allowed"}), 405


@app.errorhandler(500)
def internal_error(e):
    return jsonify({"ok": False, "error": "internal server error"}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, threaded=True)
