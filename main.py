import os
import sys
import re
import asyncio
import logging
import shutil

from typing import List, Optional

from PIL import Image

from astrbot.api.star import Context, Star, register
from astrbot.api.event import AstrMessageEvent
from astrbot.api.event.filter import (
    event_message_type,
    EventMessageType
)

logger = logging.getLogger(__name__)

# ─────────────────────────────
# 路径与依赖
# ─────────────────────────────
_PLUGIN_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

# 优先用内置 jmcomic，其次用外部源码
_JM_SRC = os.path.join(_PLUGIN_DIR, 'jmcomic')
if not os.path.isdir(_JM_SRC):
    _JM_SRC = os.path.join(
        _PLUGIN_DIR,
        '..',
        'JMComic-Crawler-Python-2.7.0',
        'src'
    )

_jm_ok = False
_JmOption = None
_download_album = None
_jm_err = ''


def _try_load():

    global _jm_ok
    global _JmOption
    global _download_album
    global _jm_err

    if _jm_ok:
        return True

    try:

        if (
            os.path.isdir(_JM_SRC)
            and _JM_SRC not in sys.path
        ):
            sys.path.insert(0, _JM_SRC)

        from jmcomic import (
            JmOption,
            download_album
        )

        _JmOption = JmOption
        _download_album = download_album

        _jm_ok = True

        return True

    except Exception as e:

        _jm_err = str(e)

        return False


HELP = (
    "JmTool 长图合并转发版\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "搜索：.jms 关键词\n"
    "下载：.jm本子ID\n"
    "测试：.jmtest\n\n"
    "功能：\n"
    "• 自动下载漫画\n"
    "• 每5张拼接成长图\n"
    "• 自动合并转发\n"
)


# ─────────────────────────────
# 获取群号
# ─────────────────────────────
def _get_group_id(
        event: AstrMessageEvent
) -> Optional[int]:

    try:

        if (
            hasattr(event, 'group_id')
            and event.group_id
        ):
            return int(event.group_id)

    except:
        pass

    try:

        obj = getattr(
            event,
            'message_obj',
            None
        )

        if obj and hasattr(obj, 'group_id'):
            return int(obj.group_id)

    except:
        pass

    return None


# ─────────────────────────────
# 扫描图片
# ─────────────────────────────
def _scan_imgs(root: str) -> List[str]:

    exts = {
        '.jpg',
        '.jpeg',
        '.png',
        '.webp',
        '.gif',
        '.bmp'
    }

    imgs = []

    for dp, _, fns in os.walk(root):

        for f in fns:

            if (
                os.path.splitext(f)[1]
                .lower() in exts
            ):
                imgs.append(
                    os.path.join(dp, f)
                )

    imgs.sort()

    return imgs


# ─────────────────────────────
# 下载
# ─────────────────────────────
def _download_flat(
        jm_id: str,
        save_dir: str
):

    opt = _JmOption.construct({

        'dir_rule': {
            'rule': 'Bd',
            'base_dir': save_dir
        },

        'download': {

            'cache': True,

            'threading': {
                'image': 2,
                'photo': 1
            },

            'image': {
                'decode': True
            }
        },

        'client': {
            'domain': [],
            'cache': True
        },
    })

    def _flat(image):

        ext = os.path.splitext(
            image.download_url
        )[1]

        if not ext:
            ext = '.jpg'

        return os.path.join(
            save_dir,
            image.img_file_name + ext
        )

    opt.decide_image_filepath = _flat

    return _download_album(
        jm_id,
        opt
    )


# ─────────────────────────────
# 拼接长图
# ─────────────────────────────
def build_long_images(
        img_paths: List[str],
        output_dir: str,
        group_size: int = 5
):

    os.makedirs(
        output_dir,
        exist_ok=True
    )

    result = []

    for i in range(
        0,
        len(img_paths),
        group_size
    ):

        chunk = img_paths[
            i:i + group_size
        ]

        images = []

        for p in chunk:

            try:

                img = (
                    Image
                    .open(p)
                    .convert("RGB")
                )

                images.append(img)

            except Exception as e:

                logger.error(
                    f"图片打开失败 {p}: {e}"
                )

        if not images:
            continue

        max_width = max(
            img.width
            for img in images
        )

        total_height = sum(
            img.height
            for img in images
        )

        long_img = Image.new(
            "RGB",
            (max_width, total_height),
            (255, 255, 255)
        )

        y = 0

        for img in images:

            long_img.paste(
                img,
                (0, y)
            )

            y += img.height

        save_path = os.path.join(
            output_dir,
            f"long_{i // group_size + 1}.jpg"
        )

        long_img.save(
            save_path,
            quality=70,
            optimize=True
        )

        result.append(save_path)

        for img in images:
            img.close()

    return result


# ─────────────────────────────
# 构建 forward 节点
# ─────────────────────────────
def build_forward_nodes(
        img_paths: List[str],
        bot_uin: int
) -> List[dict]:

    nodes = []

    for idx, path in enumerate(img_paths):

        try:

            abs_path = os.path.abspath(
                path
            ).replace(os.sep, '/')

            node = {

                "type": "node",

                "data": {

                    "name": f"长图{idx + 1}",

                    "uin": str(bot_uin),

                    "content": [
                        {
                            "type": "image",
                            "data": {
                                "file": f"file:///{abs_path}"
                            }
                        }
                    ]
                }
            }

            nodes.append(node)

        except Exception as e:

            logger.error(
                f"节点构建失败 {path}: {e}"
            )

    return nodes


# ─────────────────────────────
# 插件
# ─────────────────────────────
@register(
    "astrbot_plugin_JmTool",
    "Rirs",
    "JmTool",
    "1.0",
    "https://github.com/Rirs123/JmTool"
)
class JMComicPlugin(Star):

    def __init__(
            self,
            context: Context
    ):

        super().__init__(context)

        self.dl = os.path.join(
            _PLUGIN_DIR,
            'downloads'
        )

        os.makedirs(
            self.dl,
            exist_ok=True
        )

        self._busy = set()

    @event_message_type(
        EventMessageType.ALL
    )
    async def on_message(
            self,
            event: AstrMessageEvent
    ):

        t = event.message_str.strip()

        if re.match(
                r'^\.jmtest$',
                t,
                re.I
        ):
            return await self._test(event)

        if re.match(
                r'^\.jms$',
                t,
                re.I
        ):
            return event.plain_result(
                HELP
            )

        m = re.match(
            r'^\.jm(\d+)',
            t,
            re.I
        )

        if m:
            return await self._download(
                event,
                m.group(1)
            )

        m = re.match(
            r'^\.jms\s+(.+)',
            t,
            re.I
        )

        if m:
            return await self._search(
                event,
                m.group(1).strip()
            )

    # ─────────────────────────
    # 测试
    # ─────────────────────────
    async def _test(self, event):

        ok = _try_load()

        return event.plain_result(
            f"jmcomic加载: "
            f"{'✅' if ok else '❌'}\n"
            f"{_jm_err}"
        )

    # ─────────────────────────
    # 下载
    # ─────────────────────────
    async def _download(
            self,
            event,
            jm_id
    ):

        if not _try_load():

            return event.plain_result(
                f"依赖缺失\n{_jm_err}"
            )

        if jm_id in self._busy:

            return event.plain_result(
                f"JM{jm_id} 正在下载"
            )

        self._busy.add(jm_id)

        work_dir = os.path.join(
            self.dl,
            f'JM{jm_id}'
        )

        os.makedirs(
            work_dir,
            exist_ok=True
        )

        try:

            base_opt = _JmOption.construct({

                'dir_rule': {
                    'rule': 'Bd',
                    'base_dir': work_dir
                },

                'download': {
                    'cache': True,
                    'threading': {
                        'image': 1,
                        'photo': 1
                    },
                    'image': {
                        'decode': True
                    }
                },

                'client': {
                    'domain': [],
                    'cache': True
                },
            })

            cl = await asyncio.to_thread(
                base_opt.build_jm_client
            )

            alb = await asyncio.to_thread(
                cl.get_album_detail,
                jm_id
            )

            ch = len(alb)
            tags_str = ', '.join(alb.tags[:8]) if alb.tags else '无标签'

            await event.send(
                event.plain_result(
                    f"✅ 找到 JM{jm_id}\n"
                    f"📘 {alb.name}\n"
                    f"✍️ {alb.author}  ·  {ch} 话  "
                    f"{getattr(alb, 'page_count', '?')} 页\n"
                    f"🏷️ {tags_str}\n"
                    f"⏳ 开始下载，请耐心等待..."
                )
            )

            # 下载
            await asyncio.to_thread(
                _download_flat,
                jm_id,
                work_dir
            )

            imgs = _scan_imgs(work_dir)

            if not imgs:

                await event.send(
                    event.plain_result(
                        "❌ 没有下载到图片"
                    )
                )

                return

            total = len(imgs)

            # 拼接长图
            long_dir = os.path.join(
                work_dir,
                'long'
            )

            long_imgs = await asyncio.to_thread(
                build_long_images,
                imgs,
                long_dir,
                5
            )

            if not long_imgs:

                await event.send(
                    event.plain_result(
                        "❌ 长图生成失败"
                    )
                )

                return

            # bot
            bot = (
                getattr(event, 'bot', None)
                or getattr(event, '_bot', None)
            )

            if not bot:

                await event.send(
                    event.plain_result(
                        "❌ 无法获取 bot"
                    )
                )

                return

            # bot qq
            bot_uin = None

            try:

                sid = getattr(
                    bot,
                    'self_id',
                    None
                )

                if callable(sid):
                    sid = sid()

                bot_uin = int(str(sid))

            except:
                pass

            if not bot_uin:

                bot_uin = 123456789

                logger.warning(
                    "请修改 bot_uin"
                )

            # 群号
            group_id = _get_group_id(
                event
            )

            if not group_id:

                await event.send(
                    event.plain_result(
                        "❌ 请在群聊使用"
                    )
                )

                return

            # 构建节点
            nodes = build_forward_nodes(
                long_imgs,
                bot_uin
            )

            if not nodes:

                await event.send(
                    event.plain_result(
                        "❌ 节点构建失败"
                    )
                )

                return

            # 分批发送
            chunk_size = 10

            for i in range(
                0,
                len(nodes),
                chunk_size
            ):

                chunk = nodes[
                    i:i + chunk_size
                ]

                await bot.call_action(
                    'send_group_forward_msg',
                    group_id=group_id,
                    messages=chunk
                )

                await asyncio.sleep(1)

            await event.send(
                event.plain_result(
                    f"✅ 合并转发成功\n"
                    f"📚 共 {total} 张图片\n"
                    f"🖼️ 共 {len(long_imgs)} 张长图"
                )
            )

            shutil.rmtree(
                work_dir,
                ignore_errors=True
            )

        except Exception as e:

            logger.error(
                f"JM{jm_id} 失败",
                exc_info=True
            )

            await event.send(
                event.plain_result(
                    f"❌ 失败:\n"
                    f"{type(e).__name__}\n"
                    f"{str(e)}"
                )
            )

        finally:

            self._busy.discard(
                jm_id
            )

    # ─────────────────────────
    # 搜索
    # ─────────────────────────
    async def _search(
            self,
            event,
            kw
    ):

        if not _try_load():

            return event.plain_result(
                f"依赖缺失\n{_jm_err}"
            )

        try:

            opt = _JmOption.construct({

                'dir_rule': {
                    'rule': 'Bd',
                    'base_dir': self.dl
                },

                'client': {
                    'domain': [],
                    'cache': True
                },
            })

            cl = await asyncio.to_thread(
                opt.build_jm_client
            )

            pg = await asyncio.to_thread(
                cl.search_site,
                search_query=kw,
                page=1
            )

            if len(pg) == 0:

                return event.plain_result(
                    "😥 没有找到"
                )

            out = [
                f"🔍 搜索「{kw}」共 "
                f"{pg.total} 条:"
            ]

            for aid, title in list(pg)[:5]:

                short = (
                    title[:40] + '...'
                    if len(title) > 40
                    else title
                )

                out.append(
                    f".jm{aid}  {short}"
                )

            out.append(
                "\n💡 发送 .jm<ID> 下载"
            )

            return event.plain_result(
                '\n'.join(out)
            )

        except Exception as e:

            return event.plain_result(
                f"搜索失败: {e}"
            )

    async def terminate(self):

        if os.path.exists(self.dl):

            shutil.rmtree(
                self.dl,
                ignore_errors=True
            )