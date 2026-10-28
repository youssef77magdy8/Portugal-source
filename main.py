import os
import sys
import asyncio
import datetime
import random
import re
import pytz
from telethon import TelegramClient, events, functions, types
from telethon.tl.functions.channels import (
    EditBannedRequest, InviteToChannelRequest, GetParticipantsRequest,
    LeaveChannelRequest, CreateChannelRequest, JoinChannelRequest, EditAdminRequest,
    GetFullChannelRequest
)
from telethon.tl.functions.messages import (
    DeleteMessagesRequest, ExportChatInviteRequest, ImportChatInviteRequest,
    ReportSpamRequest, GetFullChatRequest
)
from telethon.tl.functions.phone import (
    CreateGroupCallRequest, DiscardGroupCallRequest
)
from telethon.tl.functions.contacts import BlockRequest, DeleteContactsRequest
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.types import ChatBannedRights, ChatAdminRights, ChannelParticipantsKicked
from telethon.sessions import StringSession
from telethon.errors import (
    UserPrivacyRestrictedError, ChatAdminRequiredError, UserNotMutualContactError,
    UserChannelsTooMuchError, UserBotError, PeerFloodError, FloodWaitError, UserKickedError,
    UserAlreadyParticipantError
)

# ----------------------------------------------------
# 1. إعدادات الجلسة والحساب
# ----------------------------------------------------
API_ID = int(os.getenv("API_ID", "24576280"))
API_HASH = os.getenv("API_HASH", "2d331fea63e2dfeb0d2c2cf71a9a0cc9")
STRING_SESSION = os.getenv("STRING_SESSION", "1BJWap1wBuynj7Xmp0_wFayhL0WyKiPP_KTvuNOTUFTIYEW5m_mH0gGZ9v75K0HMvvrco3PK59r0J7Elci_sqV37-5IAVrvUDYcIkkCcZAlMYpDUjD7XNuR4ITchGkkSCYwGQVMAbPbPawmYyrd7p1GHXrrG9JUF6VAqhohkzTbVI5BYB8j4Eb0zNAT62WI3xBBiNiJT5t4h2Sbxhi781O4L-zVMkll1pKKvVkMYdfMKJHC-ycBJdDFMfJB52o3mzISzpEF_JOA2DDPAomR35zxV-BvMUIUpN1hq1_Kc4JOQyB3soFT08tmNW6KdKH5M7bHIm01jLrFCElROtpHCKWf36W2X-_HE=")

client = TelegramClient(StringSession(STRING_SESSION.strip()), API_ID, API_HASH)

SOURCE_TITLE = "🇵🇹 Portuguese source 🇵🇹"
CAIRO_TZ = pytz.timezone('Africa/Cairo')
TELEGRAM_SYSTEM_IDS = {777000, 42777, 1271266}

# ----------------------------------------------------
# 2. الذاكرة والمتغيرات العامة
# ----------------------------------------------------
GBAN_SET = set()
GMUTE_SET = set()
MUTED_USERS = {}
MUTED_PMS = set()
REPLY_MAP = {}
BLOCKED_WORDS = set()

MAIN_DEV_ID = 1609075265
DEVELOPERS = {MAIN_DEV_ID} 

_env_devs = os.getenv("DEVELOPERS", "")
if _env_devs:
    for _id in _env_devs.split(","):
        if _id.strip().isdigit():
            DEVELOPERS.add(int(_id.strip()))

GAME_ACTIVE = False
GAME_PLAYERS = []
GAME_CHAT_ID = None

TIME_NAME_ACTIVE = False
TIME_NAME_TASK = None
ORIGINAL_NAME = ""

PM_PROTECTION_ACTIVE = False
APPROVED_USERS = set()
PM_WARNINGS = {}

AUTO_SAVE_MEDIA = False

SLEEP_ACTIVE = False
SLEEP_START_TIME = None

# ----------------------------------------------------
# 3. دالة التحقق واستخراج المستخدم (بالرد / اليوزر / الآيدي)
# ----------------------------------------------------
def is_sudo(event):
    return event.out or (event.sender_id in DEVELOPERS)

async def get_target_user(event):
    args = event.text.split(maxsplit=1)
    if len(args) > 1 and args[1].strip():
        target = args[1].strip()
        if target.isdigit() or (target.startswith("-") and target[1:].isdigit()):
            return int(target)
        try:
            user = await client.get_entity(target)
            return user.id
        except Exception:
            pass
            
    if event.is_reply:
        reply = await event.get_reply_message()
        if reply:
            if reply.forward and reply.forward.sender_id:
                return reply.forward.sender_id
            if reply.sender_id:
                return reply.sender_id
                
    return None

# ----------------------------------------------------
# 4. قائمة الأوامر
# ----------------------------------------------------
ALL_COMMANDS_TEXT = f"""✦─────『 {SOURCE_TITLE} 』─────✦

• `.اوامري` ➪ عرض جميع الأوامر
• `.انتحال` ➪ انتحال حساب بالرد على رسالته (نسخ الاسم والبايو والصورة)
• `.رفع مطور` ➪ رفع مطور (بالرد/باليوزر/بالآيدي)
• `.تنزيل مطور` ➪ تنزيل مطور (بالرد/باليوزر/بالآيدي)
• `.مسح المطورين` ➪ مسح جميع المطورين المضافين
• `.المطورين` ➪ عرض قائمة المطورين
• `.تفليش` ➪ تصفية وطرد أعضاء الجروب
• `.تفعيل الوقت` ➪ إظهار الوقت بجانب اسمك بتوقيت مصر
• `.تعطيل الوقت` ➪ إيقاف الوقت ورجوع اسمك الاصلي
• `.تفعيل الحمايه` ➪ قفل الخاص وتحذير أي حد يبعت
• `.تعطيل الحمايه` ➪ إيقاف حماية الخاص
• `.قبول` ➪ السماح لشخص بالحديث في الخاص بدون تحذيرات
• `.رفض` ➪ إلغاء القبول وإرجاع التحذيرات لشخص
• `.بلوك` ➪ حظر المستخدم
• `.حفظ الذاتية` ➪ حفظ صورة/فيديو ذاتية التدمير للرسائل المحفوظة
• `.تفعيل الذاتيه` ➪ حفظ ميديا الخاص والتدمير الذاتي تلقائياً
• `.تعطيل الذاتيه` ➪ إيقاف حفظ الصور تلقائياً
• `.سليب` ➪ تفعيل وضع النوم
• `.همسه` [الكلام] ➪ إرسال همسة سرية
• `.طرد` ➪ طرد عضو (بالرد/باليوزر/بالآيدي)
• `.طرد عام` ➪ طرد شخص من كل الجروبات والقنوات (بالرد/باليوزر/بالآيدي)
• `.حظر` ➪ حظر عضو (بالرد/باليوزر/بالآيدي)
• `.حظر عام` ➪ حظر عام (بالرد/باليوزر/بالآيدي)
• `.كتم` ➪ كتم عضو أو شات خاص
• `.كتم عام` ➪ كتم عام شامل (بالرد/باليوزر/بالآيدي)
• `.مسح المحظورين` ➪ فك الحظر عن كل المحظورين في الجروب
• `.مسح المكتومين` ➪ فك الكتم عن قائمة المكتومين"""

# ----------------------------------------------------
# 5. أوامر المطورين والأوامر الأساسية
# ----------------------------------------------------
@client.on(events.NewMessage(pattern=r"^\.(اوامري|الاوامر)(\s+.*)?$"))
async def show_all_commands(event):
    if not is_sudo(event): return
    await (event.edit(ALL_COMMANDS_TEXT) if event.out else event.reply(ALL_COMMANDS_TEXT))

@client.on(events.NewMessage(pattern=r"^\.انتحال(\s+.*)?$"))
async def clone_user_cmd(event):
    if not is_sudo(event): return
    target_id = await get_target_user(event)

    if not target_id:
        msg = "⚠️ **حدد الحساب بالرد عليه أو باليوزر/الآيدي!**"
        return await (event.edit(msg) if event.out else event.reply(msg))

    status_msg = await (event.edit("⏳ **جاري نسخ الاسم، البايو، وصورة البروفايل...**") if event.out else event.reply("⏳ **جاري نسخ الاسم، البايو، وصورة البروفايل...**"))

    try:
        full_user = await client(GetFullUserRequest(target_id))
        user_entity = full_user.users[0]
        
        bio = full_user.full_user.about or ""
        first_name = user_entity.first_name or ""
        last_name = user_entity.last_name or ""

        await client(functions.account.UpdateProfileRequest(
            first_name=first_name,
            last_name=last_name,
            about=bio
        ))

        photos = await client.get_profile_photos(target_id, limit=1)
        if photos:
            photo_path = await client.download_media(photos[0])
            if photo_path:
                uploaded_file = await client.upload_file(photo_path)
                await client(functions.photos.UploadProfilePhotoRequest(file=uploaded_file))
                if os.path.exists(photo_path):
                    os.remove(photo_path)

        await status_msg.edit(
            f"🎭 **تم انتحال الحساب بنجاح!**\n\n"
            f"👤 **الاسم:** {first_name} {last_name}\n"
            f"📝 **البايو:** {bio if bio else 'بدون بايو'}"
        )

    except Exception as e:
        await status_msg.edit(f"❌ **حدث خطأ أثناء عملية الانتحال:**\n`{e}`")

@client.on(events.NewMessage(pattern=r"^\.رفع مطور(?:\s+(.*))?$"))
async def add_developer(event):
    if not is_sudo(event): return
    target_id = await get_target_user(event)

    if not target_id:
        msg = "⚠️ **حدد الشخص بالرد أو باليوزر/الآيدي!**"
        return await (event.edit(msg) if event.out else event.reply(msg))

    if target_id in DEVELOPERS:
        msg = "⚠️ **الشخص ده مرفوع مطور بالفعل!**"
        return await (event.edit(msg) if event.out else event.reply(msg))

    DEVELOPERS.add(target_id)
    msg = "✅ **تم رفع الشخص مطور في السورس بنجاح!**"
    await (event.edit(msg) if event.out else event.reply(msg))

@client.on(events.NewMessage(pattern=r"^\.تنزيل مطور(?:\s+(.*))?$"))
async def remove_developer(event):
    if not is_sudo(event): return
    target_id = await get_target_user(event)

    if not target_id:
        msg = "⚠️ **حدد الشخص بالرد أو باليوزر/الآيدي!**"
        return await (event.edit(msg) if event.out else event.reply(msg))

    if target_id in DEVELOPERS:
        DEVELOPERS.remove(target_id)
        msg = "✅ **تم تنزيل الشخص من المطورين بنجاح.**"
    else:
        msg = "⚠️ **الشخص ده مش مطور من الأساس.**"
    await (event.edit(msg) if event.out else event.reply(msg))

@client.on(events.NewMessage(pattern=r"^\.مسح المطورين(\s+.*)?$"))
async def clear_developers(event):
    if not is_sudo(event): return
    me = await client.get_me()
    
    DEVELOPERS.clear()
    DEVELOPERS.add(MAIN_DEV_ID)
    DEVELOPERS.add(me.id)
    
    msg = "🗑️ **تم مسح جميع المطورين المضافين بنجاح!**"
    await (event.edit(msg) if event.out else event.reply(msg))

@client.on(events.NewMessage(pattern=r"^\.المطورين(\s+.*)?$"))
async def list_developers(event):
    if not is_sudo(event): return
    if not DEVELOPERS:
        msg = "ℹ️ **مفيش مطورين مرفوعين دلوقتي.**"
    else:
        msg = f"👑 **عدد المطورين المرفوعين:** `{len(DEVELOPERS)}`"
    await (event.edit(msg) if event.out else event.reply(msg))

# ----------------------------------------------------
# 6. أمر تفليش الجروب
# ----------------------------------------------------
@client.on(events.NewMessage(pattern=r"^\.تفليش(\s+.*)?$"))
async def taflesh_cmd(event):
    if not is_sudo(event): return
    if not event.is_group:
        msg = "⚠️ **الأمر ده بيشتغل جوة الجروبات بس!**"
        return await (event.edit(msg) if event.out else event.reply(msg))

    perms = await client.get_permissions(event.chat_id, event.sender_id)
    if not (perms.is_creator or perms.ban_users):
        msg = "⚠️ **معندكش صلاحية حظر الأعضاء لاستخدام الأمر ده!**"
        return await (event.edit(msg) if event.out else event.reply(msg))

    status_msg = await (event.edit("⚡ **جاري تفليش الجروب وتصفية الاعضاء...**") if event.out else event.reply("⚡ **جاري تفليش الجروب وتصفية الاعضاء...**"))

    kicked_count = 0
    failed_count = 0

    async for user in client.iter_participants(event.chat_id):
        if user.bot:
            continue

        try:
            user_perm = await client.get_permissions(event.chat_id, user.id)
            if user_perm.is_admin or user_perm.is_creator:
                continue

            await client.kick_participant(event.chat_id, user.id)
            kicked_count += 1
            await asyncio.sleep(0.05)
        except FloodWaitError as e:
            await asyncio.sleep(e.seconds)
        except Exception:
            failed_count += 1

    await status_msg.edit(
        f"💥 **تم الانتهاء من تفليش الجروب!**\n\n"
        f"👥 **تم طرد:** `{kicked_count}`\n"
        f"❌ **فشل طرد:** `{failed_count}`"
    )

# ----------------------------------------------------
# 7. الحماية، الخدمات، والتحكم بالخاص
# ----------------------------------------------------
@client.on(events.NewMessage(pattern=r"^\.همسه(?:\s+(.+))?$"))
async def whisper_cmd(event):
    if not is_sudo(event): return
    input_text = event.pattern_match.group(1)
    target = None
    whisper_text = ""

    if event.is_reply:
        reply = await event.get_reply_message()
        if reply and reply.sender_id:
            try:
                target_user = await client.get_entity(reply.sender_id)
                target = f"@{target_user.username}" if target_user.username else str(target_user.id)
                whisper_text = input_text if input_text else ""
            except Exception:
                target = str(reply.sender_id)
                whisper_text = input_text if input_text else ""
    elif input_text:
        parts = input_text.split(maxsplit=1)
        if len(parts) >= 2 and (parts[0].startswith("@") or parts[0].isdigit()):
            target = parts[0]
            whisper_text = parts[1]

    if not target or not whisper_text:
        msg = "⚠️ **طريقة استخدام أمر الهمسة:**\n• `.همسه @username الكلام`"
        return await (event.edit(msg) if event.out else event.reply(msg))

    try:
        await event.delete()
        results = await client.inline_query('@whisperbot', f"{target} {whisper_text}")
        if results:
            await results[0].click(event.chat_id)
        else:
            await client.send_message(event.chat_id, "❌ **تعذر إنشاء الهمسة.**")
    except Exception as e:
        await client.send_message(event.chat_id, f"❌ **حدث خطأ:** {e}")

@client.on(events.NewMessage(pattern=r"^\.تفعيل الحمايه(\s+.*)?$"))
async def enable_pm_guard(event):
    global PM_PROTECTION_ACTIVE
    if not is_sudo(event): return
    PM_PROTECTION_ACTIVE = True
    msg = "🛡️ **تم تفعيل حماية الخاص بنجاح!**"
    await (event.edit(msg) if event.out else event.reply(msg))

@client.on(events.NewMessage(pattern=r"^\.تعطيل الحمايه(\s+.*)?$"))
async def disable_pm_guard(event):
    global PM_PROTECTION_ACTIVE
    if not is_sudo(event): return
    PM_PROTECTION_ACTIVE = False
    msg = "🔓 **تم تعطيل حماية الخاص بنجاح!**"
    await (event.edit(msg) if event.out else event.reply(msg))

@client.on(events.NewMessage(pattern=r"^\.قبول(?:\s+(.*))?$"))
async def approve_user(event):
    global APPROVED_USERS
    if not is_sudo(event): return
    target_id = await get_target_user(event)
    if not target_id and event.is_private:
        target_id = event.chat_id

    if not target_id:
        msg = "⚠️ **حدد الشخص بالرد أو باليوزر/الآيدي!**"
        return await (event.edit(msg) if event.out else event.reply(msg))

    APPROVED_USERS.add(target_id)
    if target_id in PM_WARNINGS:
        del PM_WARNINGS[target_id]

    msg = "✅ **تم قبول المستخدم بنجاح ومسموح له بالحديث في الخاص.**"
    await (event.edit(msg) if event.out else event.reply(msg))

@client.on(events.NewMessage(pattern=r"^\.رفض(?:\s+(.*))?$"))
async def decline_user(event):
    global APPROVED_USERS
    if not is_sudo(event): return
    target_id = await get_target_user(event)
    if not target_id and event.is_private:
        target_id = event.chat_id

    if not target_id:
        msg = "⚠️ **حدد الشخص بالرد أو باليوزر/الآيدي!**"
        return await (event.edit(msg) if event.out else event.reply(msg))

    if target_id in APPROVED_USERS:
        APPROVED_USERS.remove(target_id)
        msg = "❌ **تم إلغاء قبول المستخدم وأصبح غير مسموح له بالحديث في الخاص.**"
    else:
        msg = "⚠️ **المستخدم غير مقبول من الأساس.**"

    await (event.edit(msg) if event.out else event.reply(msg))

@client.on(events.NewMessage(pattern=r"^\.بلوك(?:\s+(.*))?$"))
async def block_user_cmd(event):
    if not is_sudo(event): return
    target_id = await get_target_user(event)
    if not target_id and event.is_private:
        target_id = event.chat_id

    if not target_id:
        msg = "⚠️ **حدد المستخدم لحظره!**"
        return await (event.edit(msg) if event.out else event.reply(msg))

    try:
        await (event.edit("تم حظر المستخدم بنجاح 🚫") if event.out else event.reply("تم حظر المستخدم بنجاح 🚫"))
        await client(BlockRequest(id=target_id))
    except Exception as e:
        print(f"خطأ في تنفيذ البلوك: {e}")

# ----------------------------------------------------
# 8. أوامر إدارة الجروبات والقنوات (حظر، طرد، كتم موحد - تدعم اليوزر والآيدي)
# ----------------------------------------------------
@client.on(events.NewMessage(pattern=r"^\.حظر(?:\s+(.*))?$"))
async def ban_user(event):
    if not is_sudo(event): return
    if event.text.startswith(".حظر عام"): return
    if not event.is_group and not event.is_channel:
        msg = "⚠️ **الأمر ده بيشتغل جوة الجروبات والقنوات بس!**"
        return await (event.edit(msg) if event.out else event.reply(msg))
    
    target_id = await get_target_user(event)
    if not target_id:
        msg = "⚠️ **حدد العضو بالرد أو باليوزر أو بالآيدي!**"
        return await (event.edit(msg) if event.out else event.reply(msg))

    try:
        await client(EditBannedRequest(event.chat_id, target_id, ChatBannedRights(until_date=None, view_messages=True)))
        msg = "⛔ **تم حظر العضو بنجاح.**"
    except Exception as e:
        msg = f"❌ **حدث خطأ أثناء الحظر:** `{e}`"
    await (event.edit(msg) if event.out else event.reply(msg))

@client.on(events.NewMessage(pattern=r"^\.طرد(?:\s+(.*))?$"))
async def kick_user_cmd(event):
    if not is_sudo(event): return
    if event.text.startswith(".طرد عام") or event.text.startswith(".طرد البوتات"): return
    if not event.is_group and not event.is_channel:
        msg = "⚠️ **الأمر ده بيشتغل جوة الجروبات والقنوات بس!**"
        return await (event.edit(msg) if event.out else event.reply(msg))

    target_id = await get_target_user(event)
    if not target_id:
        msg = "⚠️ **حدد العضو بالرد أو باليوزر أو بالآيدي!**"
        return await (event.edit(msg) if event.out else event.reply(msg))

    try:
        await client.kick_participant(event.chat_id, target_id)
        msg = "🥾 **تم طرد العضو بنجاح.**"
    except Exception as e:
        msg = f"❌ **حدث خطأ أثناء الطرد:** `{e}`"
    await (event.edit(msg) if event.out else event.reply(msg))

@client.on(events.NewMessage(pattern=r"^\.طرد عام(?:\s+(.*))?$"))
async def gkick_user(event):
    if not is_sudo(event): return
    target_id = await get_target_user(event)
    if not target_id:
        msg = "⚠️ **حدد الشخص بالرد أو باليوزر أو بالآيدي!**"
        return await (event.edit(msg) if event.out else event.reply(msg))
    
    status_msg = await (event.edit("⏳ **جاري طرد المستخدم من جميع الجروبات والقنوات...**") if event.out else event.reply("⏳ **جاري طرد المستخدم من جميع الجروبات والقنوات...**"))
    
    kicked_chats = 0
    dialogs = await client.get_dialogs()
    
    for d in dialogs:
        if d.is_group or d.is_channel:
            try:
                await client.kick_participant(d.id, target_id)
                kicked_chats += 1
                await asyncio.sleep(0.2)
            except Exception:
                pass
                
    await status_msg.edit(f"💥 **تم طرد المستخدم من `{kicked_chats}` جروب وقناة بنجاح!**")

@client.on(events.NewMessage(pattern=r"^\.كتم(?:\s+(.*))?$"))
async def mute_user(event):
    if not is_sudo(event): return
    if event.text.startswith(".كتم عام") or event.text.startswith(".كتمخاص"): return

    if event.is_private:
        # كتم الخاص مباشرة بدون الحاجة لإعادة توجيه أو رد
        MUTED_PMS.add(event.chat_id)
        msg = "🔇 **تم كتم الشات الخاص بنجاح!**"
        return await (event.edit(msg) if event.out else event.reply(msg))

    elif event.is_group or event.is_channel:
        target_id = await get_target_user(event)
        if not target_id:
            msg = "⚠️ **حدد العضو بالرد أو باليوزر أو بالآيدي!**"
            return await (event.edit(msg) if event.out else event.reply(msg))

        MUTED_USERS.setdefault(event.chat_id, set()).add(target_id)
        msg = "🔇 **تم كتم العضو بنجاح في هذه المحادثة.**"
        return await (event.edit(msg) if event.out else event.reply(msg))

@client.on(events.NewMessage(pattern=r"^\.فك كتم(?:\s+(.*))?$"))
async def unmute_user(event):
    if not is_sudo(event): return
    if event.text.startswith(".فك كتمخاص"): return

    if event.is_private:
        if event.chat_id in MUTED_PMS:
            MUTED_PMS.remove(event.chat_id)
            msg = "🔊 **تم فك الكتم عن المحادثة الخاصة.**"
        else:
            msg = "⚠️ **المحادثة غير مكتومة.**"
        return await (event.edit(msg) if event.out else event.reply(msg))

    elif event.is_group or event.is_channel:
        target_id = await get_target_user(event)
        if not target_id:
            msg = "⚠️ **حدد العضو بالرد أو باليوزر أو بالآيدي!**"
            return await (event.edit(msg) if event.out else event.reply(msg))

        if event.chat_id in MUTED_USERS and target_id in MUTED_USERS[event.chat_id]:
            MUTED_USERS[event.chat_id].remove(target_id)
            msg = "🔊 **تم فك كتم العضو بنجاح.**"
        else:
            msg = "⚠️ **العضو غير مكتوم في هذه المحادثة.**"
        return await (event.edit(msg) if event.out else event.reply(msg))

@client.on(events.NewMessage(pattern=r"^\.حظر عام(?:\s+(.*))?$"))
async def gban_user(event):
    if not is_sudo(event): return
    target_id = await get_target_user(event)
    if not target_id:
        msg = "⚠️ **حدد المستخدم بالرد أو باليوزر أو بالآيدي!**"
        return await (event.edit(msg) if event.out else event.reply(msg))

    GBAN_SET.add(target_id)
    msg = "🚫 **تم حظر المستخدم عام من كل الجروبات والقنوات.**"
    await (event.edit(msg) if event.out else event.reply(msg))

@client.on(events.NewMessage(pattern=r"^\.كتم عام(?:\s+(.*))?$"))
async def gmute_user(event):
    if not is_sudo(event): return
    target_id = await get_target_user(event)
    if not target_id:
        msg = "⚠️ **حدد الشخص بالرد أو باليوزر أو بالآيدي!**"
        return await (event.edit(msg) if event.out else event.reply(msg))

    GMUTE_SET.add(target_id)
    msg = "🔇 **تم كتم المستخدم عام (يشمل كل الجروبات والقنوات والخاص).**"
    await (event.edit(msg) if event.out else event.reply(msg))

# ----------------------------------------------------
# 9. معالج الرسائل العام والتحكم بالتنفيذ
# ----------------------------------------------------
@client.on(events.NewMessage)
async def handle_incoming(event):
    if not event.sender_id or event.sender_id in TELEGRAM_SYSTEM_IDS:
        return

    global SLEEP_ACTIVE
    if event.out and SLEEP_ACTIVE:
        SLEEP_ACTIVE = False

    # الحظر العام (GBAN)
    if event.sender_id in GBAN_SET and not event.out:
        if event.is_group or event.is_channel:
            try:
                await client(EditBannedRequest(event.chat_id, event.sender_id, ChatBannedRights(until_date=None, view_messages=True)))
                await event.delete()
            except Exception:
                pass
        return

    # الكتم العام (GMUTE - يشمل الجروبات، القنوات، والخاص)
    if event.sender_id in GMUTE_SET and not event.out:
        try:
            await event.delete()
        except Exception:
            pass
        return

    # الكتم المحلي للجروب أو القناة
    if (event.is_group or event.is_channel) and event.chat_id in MUTED_USERS:
        if event.sender_id in MUTED_USERS[event.chat_id] and not event.out:
            try:
                await event.delete()
            except Exception:
                pass
            return

    # كتم الخاص
    if event.is_private and event.chat_id in MUTED_PMS and not event.out:
        try:
            await event.delete()
        except Exception:
            pass
        return

    # حماية الخاص
    if PM_PROTECTION_ACTIVE and event.is_private and not event.out and not is_sudo(event):
        if event.sender_id not in APPROVED_USERS:
            count = PM_WARNINGS.get(event.sender_id, 0) + 1
            PM_WARNINGS[event.sender_id] = count
            if count >= 7:
                await event.reply("⛔ **تم حظرك تلقائياً لتجاوز عدد التحذيرات المسموح بها.**")
                await client(BlockRequest(id=event.sender_id))
            else:
                await event.reply(f"⚠️ بلاش سبام عشان متاخدش بان تلقائي!**\nتحذير `{count}/7`")

# ----------------------------------------------------
# 10. تشغيل الحساب
# ----------------------------------------------------
print("⚡ Portuguese source client started successfully...")
client.start()
client.run_until_disconnected()
