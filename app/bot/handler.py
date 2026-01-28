"""
LINE Bot 工作事件處理器
"""
from typing import Dict, Optional, List, Any, Union
import urllib.parse
import datetime
import re
import requests

from app.services.job_service import JobService
from app.services.application_service import ApplicationService
from app.services.line_message_service import LineMessageService
from app.services.auth_service import AuthService
from app.services.state_service import StateService
from app.services.rich_menu_service import LineRichMenuService
from app.models.schemas import Job, Application
from app.core.logger import setup_logger
from app.config import REGISTERED_USER_RICH_MENU_ID, UNREGISTERED_USER_RICH_MENU_ID

from email_validator import validate_email as validate_email_address, EmailNotValidError

# 設置 logger
logger = setup_logger(__name__)


def validate_email(email: str) -> bool:
    """
    驗證 Email 格式
    
    參數:
        email: Email 地址字串
    
    返回:
        bool: 如果 Email 格式正確返回 True，否則返回 False
    """
    if not email or not email.strip():
        return False
    
    try:
        # 只檢查格式，不檢查域名是否真的接受郵件（check_deliverability=False）
        email_info = validate_email_address(
            email, 
            check_deliverability=False  # 不檢查域名是否真的接受郵件
        )
        # email_info.normalized 是標準化後的 Email 地址
        return True
    except EmailNotValidError as e:  # catch invalid emails
        logger.debug(f"Email 驗證失敗：{str(e)}")
        return False
    except Exception as e:
        logger.error(f"Email 驗證時發生錯誤：{str(e)}", exc_info=True)
        return False


def validate_name_at_least_two_chinese(name: str) -> bool:
    """
    驗證姓名至少包含二個中文字。
    """
    if not name or not name.strip():
        return False
    chinese_chars = re.findall(r'[\u4e00-\u9fff]', name)
    return len(chinese_chars) >= 2


def validate_taiwan_id(id_str: str) -> bool:
    """
    台灣身份證字號驗證（含檢核碼）。
    格式：一碼英文字母 + 九碼數字，字母對照表不含 I、O（與 1、0 易混淆）。
    """
    if not id_str or len(id_str) != 10:
        return False
    id_str = id_str.strip().upper()
    # 第 1 碼：A-Z（依內政部對照表）
    letter_map = "ABCDEFGHJKLMNPQRSTUVXYWZIO"  # 對應 10~35
    if id_str[0] not in letter_map:
        return False
    # 第 2 碼：性別 1 或 2
    if id_str[1] not in ('1', '2'):
        return False
    # 第 3~10 碼：數字
    if not id_str[2:].isdigit():
        return False
    # 檢核：權重 [1,9,8,7,6,5,4,3,2,1,1]，字母換成兩碼（十位、個位）
    n = letter_map.index(id_str[0]) + 10  # 10~35
    digits = [n // 10, n % 10] + [int(c) for c in id_str[1:]]
    weights = [1, 9, 8, 7, 6, 5, 4, 3, 2, 1, 1]
    if len(digits) != 11 or len(weights) != 11:
        return False
    total = sum(d * w for d, w in zip(digits, weights))
    return (total % 10) == 0


def validate_birthday_iso(s: str) -> bool:
    """驗證西元生日格式 YYYY-MM-DD 且為合理日期。"""
    if not s or len(s) != 10:
        return False
    s = s.strip()
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', s):
        return False
    try:
        y, m, d = int(s[:4]), int(s[5:7]), int(s[8:10])
        dt = datetime.date(y, m, d)
        # 合理範圍：1900~今年
        today = datetime.date.today()
        return datetime.date(1900, 1, 1) <= dt <= today
    except ValueError:
        return False


class JobHandler:
    """工作事件處理器"""
    
    def __init__(self, job_service: JobService, application_service: ApplicationService, message_service: LineMessageService, auth_service: Optional[AuthService] = None, state_service: Optional[StateService] = None, rich_menu_service: Optional[LineRichMenuService] = None):
        self.job_service = job_service
        self.application_service = application_service
        self.message_service = message_service
        self.auth_service = auth_service
        # 使用資料庫狀態服務，支援 Gunicorn 多進程環境
        self.state_service = state_service or StateService()
        # Rich Menu 服務（用於自動設定用戶的 Rich Menu）
        self.rich_menu_service = rich_menu_service or LineRichMenuService()
    
    def show_available_jobs(self, reply_token: str, user_id: Optional[str] = None) -> None:
        """顯示可報班的可報班工作（使用輪播方式，按日期升序排序），排除使用者已報班的日期"""
        jobs = self.job_service.get_available_jobs()
        
        # 排除使用者已報班的日期：若該日已有任一報班記錄，該日期的所有工作都不顯示
        if user_id:
            applications = self.application_service.get_user_applications(user_id)
            applied_dates = set()
            for app in applications:
                job = self.job_service.get_job(app.job_id)
                if job and job.date:
                    applied_dates.add(job.date)
            if applied_dates:
                jobs = [j for j in jobs if j.date not in applied_dates]
                logger.info(f"排除已報班日期 {applied_dates}，剩餘 {len(jobs)} 個可報班工作")
        
        logger.info(f"查詢可報班工作：找到 {len(jobs)} 個工作")
        # 記錄每個工作的 ID 和名稱，方便調試（按日期排序）
        for i, job in enumerate(jobs, 1):
            logger.debug(f"工作 {i}: {job.id} - {job.name} - {job.date} (按日期排序)")
        
        # 確保工作按日期排序（從早到晚）
        # 雖然 get_available_jobs 已經排序，但這裡再次確認
        jobs = sorted(jobs, key=lambda x: x.date)
        
        if not jobs:
            self.message_service.send_text(
                reply_token,
                "目前沒有可報班的工作。\n\n請稍後再試，或聯絡管理員。\n\n💡 提示：管理員可以透過 API 發佈新工作。"
            )
            return
        
        # LINE API 限制：
        # - Carousel 最多 10 個 columns
        # - 一次回覆最多 5 個訊息
        MAX_CAROUSEL_COLUMNS = 10
        MAX_MESSAGES_PER_REPLY = 5
        
        # 只處理第一批工作（最多 10 個），確保不超過訊息限制
        # 如果工作超過 10 個，只顯示前 10 個
        display_jobs = jobs[:MAX_CAROUSEL_COLUMNS]
        logger.info(f"將顯示 {len(display_jobs)} 個工作（總共 {len(jobs)} 個）")
        
        # 準備訊息（文字訊息 + 輪播訊息），在同一個回覆中發送
        messages = []
        
        # 添加工作總數文字訊息
        if len(jobs) > MAX_CAROUSEL_COLUMNS:
            messages.append({
                "type": "text",
                "text": f"📋 可報班的工作（共 {len(jobs)} 個）：\n\n顯示前 {MAX_CAROUSEL_COLUMNS} 個工作，請使用「查看詳情」查看完整資訊。"
            })
        else:
            messages.append({
                "type": "text",
                "text": f"📋 可報班的工作（共 {len(jobs)} 個）："
            })
        
        # 建立輪播 columns
        columns = []
        for job in display_jobs:
            try:
                logger.debug(f"處理工作：{job.id} - {job.name}")
                
                # 檢查使用者是否已報班
                is_applied = False
                applied_shift = None
                if user_id:
                    application = self.application_service.get_user_application_for_job(user_id, job.id)
                    if application:
                        is_applied = True
                        applied_shift = application.shift
                
                # 建立 Google Maps 導航 URL
                encoded_location = urllib.parse.quote(job.location)
                navigation_url = f"https://www.google.com/maps/dir/?api=1&destination={encoded_location}"
                
                # 檢查使用者是否已註冊報班帳號
                is_registered = True
                if self.auth_service:
                    is_registered = self.auth_service.is_line_user_registered(user_id) if user_id else False
                
                # 建立按鈕動作（Carousel 每個 bubble 最多 3 個按鈕）
                actions = [
                    {
                        "type": "postback",
                        "label": "🔍 查看詳情",
                        "data": f"action=job&step=detail&job_id={job.id}"
                    }
                ]
                
                # 根據狀態加入第二個按鈕
                if not is_registered:
                    actions.append({
                        "type": "postback",
                        "label": "📝 註冊",
                        "data": "action=register&step=register"
                    })
                elif is_applied:
                    actions.append({
                        "type": "postback",
                        "label": "🚫 取消報班",
                        "data": f"action=job&step=cancel&job_id={job.id}"
                    })
                else:
                    actions.append({
                        "type": "postback",
                        "label": "📝 報班",
                        "data": f"action=job&step=apply&job_id={job.id}"
                    })
                
                # 加入導航按鈕（第三個）
                actions.append({
                    "type": "uri",
                    "label": "🧭 導航",
                    "uri": navigation_url
                })
                
                # 建立文字內容（Carousel text 最多 120 字元，但建議 60 字元以內）
                # 簡化地點顯示
                location_display = job.location or "未指定地點"
                if len(location_display) > 20:
                    location_display = location_display[:17] + "..."
                
                # 建立班別顯示文字
                shifts = job.shifts or []
                if len(shifts) == 0:
                    shifts_display = "未指定班別"
                elif len(shifts) == 1:
                    shifts_display = shifts[0]
                elif len(shifts) == 2:
                    shifts_display = ", ".join(shifts)
                else:
                    shifts_display = f"{shifts[0]}等{len(shifts)}個"
                
                # 建立狀態標示
                if is_applied:
                    status_text = f"✅已報班"
                    if applied_shift:
                        status_text += f"({applied_shift[:6]})"  # 限制班別顯示長度
                else:
                    status_text = "⭕未報班"
                
                # 組合文字內容（最多 120 字元）
                job_text = f"🏠{location_display}\n📅{job.date or '未指定日期'}\n⏰{shifts_display}\n{status_text}"
                
                # 確保文字不超過 120 字元
                if len(job_text) > 120:
                    # 簡化班別顯示
                    if len(shifts) > 1:
                        shifts_display = f"{len(shifts)}個班別"
                    else:
                        shifts_display = shifts[0][:15] if shifts else "未指定"
                    job_text = f"🏠{location_display}\n📅{job.date or '未指定日期'}\n⏰{shifts_display}\n{status_text}"
                    
                    # 如果還是太長，進一步簡化
                    if len(job_text) > 120:
                        job_text = f"🏠{location_display[:15]}\n📅{job.date or '未指定日期'}\n⏰{shifts_display}\n{status_text}"
                
                # 建立 Carousel column
                column = {
                    "title": (job.name or "未命名工作")[:40],  # LINE 限制標題最多 40 字元
                    "text": job_text,
                    "actions": actions
                }
                
                # 如果有圖片，加入縮圖
                if job.location_image_url:
                    column["thumbnailImageUrl"] = job.location_image_url
                
                columns.append(column)
                logger.debug(f"成功添加工作到輪播：{job.id} - {job.name}，目前 columns 數量：{len(columns)}")
            except Exception as e:
                logger.error(f"處理工作 {job.id} ({job.name}) 時發生錯誤：{e}", exc_info=True)
                # 即使處理失敗，也繼續處理下一個工作
                continue
        
        logger.info(f"輪播 columns 建立完成：共 {len(columns)} 個，原始工作數量：{len(display_jobs)}")
        
        # 將輪播訊息添加到 messages 列表
        alt_text = f"可報班可報班工作（1-{len(display_jobs)}/{len(jobs)}）"
        carousel_message = {
            "type": "template",
            "altText": alt_text,
            "template": {
                "type": "carousel",
                "columns": columns
            }
        }
        messages.append(carousel_message)
        
        # 一次性發送所有訊息（文字 + 輪播，共 2 個訊息）
        try:
            self.message_service.send_multiple_messages(reply_token, messages)
        except Exception as e:
            logger.error(f"發送可報班工作訊息失敗：{e}", exc_info=True)
            # 如果發送失敗，嘗試發送簡單的文字訊息作為備用
            try:
                fallback_text = f"📋 可報班的工作（共 {len(jobs)} 個）：\n\n"
                for i, job in enumerate(jobs[:5], 1):  # 只顯示前 5 個
                    fallback_text += f"{i}. {job.name}\n   🏠{job.location}\n   📅{job.date}\n\n"
                if len(jobs) > 5:
                    fallback_text += f"... 還有 {len(jobs) - 5} 個工作，請稍後再試。"
                self.message_service.send_text(reply_token, fallback_text)
            except Exception as fallback_error:
                logger.error(f"發送備用訊息也失敗：{fallback_error}", exc_info=True)
    
    def show_job_detail(self, reply_token: str, user_id: str, job_id: str) -> None:
        """顯示工作詳情"""
        job = self.job_service.get_job(job_id)
        if not job:
            self.message_service.send_text(reply_token, "❌ 找不到指定的工作。")
            return
        
        # 檢查使用者是否已註冊報班帳號
        is_registered = True
        if self.auth_service:
            is_registered = self.auth_service.is_line_user_registered(user_id)
        
        # 檢查使用者是否已報班
        application = None
        is_applied = False
        if is_registered:
            application = self.application_service.get_user_application_for_job(user_id, job_id)
            is_applied = application is not None
        
        # 建立工作詳情訊息
        job_detail = f"""📌 {job.name}

🏠 工作地點：{job.location}
📅 工作日期：{job.date}
⏰ 可選班別：
"""
        for shift in job.shifts:
            job_detail += f"   • {shift}\n"
        
        if is_applied and application:
            job_detail += f"\n✅ 您已報班：{application.shift}"
        
        # 建立 Google Maps 導航 URL
        encoded_location = urllib.parse.quote(job.location)
        navigation_url = f"https://www.google.com/maps/dir/?api=1&destination={encoded_location}"
        
        # 建立按鈕
        actions = []
        if not is_registered:
            # 未註冊報班帳號使用者：顯示註冊報班帳號按鈕
            actions.append({
                "type": "postback",
                "label": "📝 註冊報班帳號",
                "data": "action=register&step=register"
            })
        elif is_applied:
            actions.append({
                "type": "postback",
                "label": "🚫 取消報班",
                "data": f"action=job&step=cancel&job_id={job_id}"
            })
        else:
            actions.append({
                "type": "postback",
                "label": "📝 報班",
                "data": f"action=job&step=apply&job_id={job_id}"
            })
        
        # 加入導航按鈕
        actions.append({
            "type": "uri",
            "label": "🧭 導航",
            "uri": navigation_url
        })
        
        actions.append({
            "type": "postback",
            "label": "🔙 返回可報班工作",
            "data": "action=job&step=list"
        })
        
        messages = []
        
        # 如果有圖片，先發送圖片
        if job.location_image_url:
            messages.append({
                "type": "image",
                "originalContentUrl": job.location_image_url,
                "previewImageUrl": job.location_image_url
            })
        
        messages.append({
            "type": "text",
            "text": job_detail
        })
        
        messages.append({
            "type": "template",
            "altText": job.name,
            "template": {
                "type": "buttons",
                "title": job.name,
                "text": "📋 請選擇操作：",
                "actions": actions
            }
        })
        
        self.message_service.send_multiple_messages(reply_token, messages)
    
    def handle_apply_job(self, reply_token: str, user_id: str, job_id: str) -> None:
        """處理報班工作流程 - 顯示班別選擇"""
        # 檢查使用者是否已註冊報班帳號
        if self.auth_service and not self.auth_service.is_line_user_registered(user_id):
            self.message_service.send_text(
                reply_token,
                "❌ 您尚未註冊報班帳號，無法報班工作。\n\n請先使用「註冊報班帳號」功能完成註冊報班帳號。"
            )
            return
        
        job = self.job_service.get_job(job_id)
        if not job:
            self.message_service.send_text(reply_token, "❌ 找不到指定的工作。")
            return
        
        # 檢查是否已報班
        existing_app = self.application_service.get_user_application_for_job(user_id, job_id)
        if existing_app:
            self.message_service.send_text(
                reply_token,
                f"❌ 您已經報班了這個工作（班別：{existing_app.shift}）\n\n如需取消，請先取消現有報班。"
            )
            return
        
        # 建立班別選擇按鈕（最多4個）
        shift_actions = []
        for shift in job.shifts[:4]:  # LINE 按鈕最多4個
            shift_actions.append({
                "type": "postback",
                "label": f"📅 {shift}",
                "data": f"action=job&step=select_shift&job_id={job_id}&shift={urllib.parse.quote(shift)}"
            })
        
        messages = [
            {
                "type": "text",
                "text": f"請選擇要報班的班別：\n\n工作：{job.name}\n日期：{job.date}"
            },
            {
                "type": "template",
                "altText": "選擇班別",
                "template": {
                    "type": "buttons",
                    "title": "📅 選擇班別",
                    "text": "請選擇報班的班別：",
                    "actions": shift_actions
                }
            }
        ]
        
        self.message_service.send_multiple_messages(reply_token, messages)
    
    def handle_select_shift(self, reply_token: str, user_id: str, job_id: str, shift: str) -> None:
        """處理選擇班別並完成報班"""
        # 檢查使用者是否已註冊報班帳號
        if self.auth_service and not self.auth_service.is_line_user_registered(user_id):
            self.message_service.send_text(
                reply_token,
                "❌ 您尚未註冊報班帳號，無法報班工作。\n\n請先使用「註冊報班帳號」功能完成註冊報班帳號。"
            )
            return
        
        job = self.job_service.get_job(job_id)
        if not job:
            self.message_service.send_text(reply_token, "❌ 找不到指定的工作。")
            return
        
        # 檢查班別是否有效
        if shift not in job.shifts:
            self.message_service.send_text(reply_token, "❌ 無效的班別選擇。")
            return
        
        # 檢查是否已報班
        existing_app = self.application_service.get_user_application_for_job(user_id, job_id)
        if existing_app:
            self.message_service.send_text(
                reply_token,
                f"❌ 您已經報班了這個工作（班別：{existing_app.shift}）"
            )
            return
        
        # 建立報班記錄
        application = self.application_service.create_application(job_id, user_id, shift)
        
        # 發送報班成功訊息
        success_message = f"""✅ 報班成功！

📋 報班資訊：
• 工作名稱：{job.name}
• 工作地點：{job.location}
• 工作日期：{job.date}
• 報班班別：{shift}
• 報班時間：{application.applied_at}
• 報班編號：{application.id}

感謝您的報班，我們會盡快與您聯繫！"""
        
        self.message_service.send_text(reply_token, success_message)
    
    def handle_cancel_application(self, reply_token: str, user_id: str, job_id: str) -> None:
        """處理取消報班流程 - 顯示報班資訊和確認按鈕"""
        job = self.job_service.get_job(job_id)
        if not job:
            self.message_service.send_text(reply_token, "❌ 找不到指定的工作。")
            return
        
        application = self.application_service.get_user_application_for_job(user_id, job_id)
        if not application:
            self.message_service.send_text(reply_token, "❌ 您尚未報班這個工作。")
            return
        
        # 顯示報班資訊和確認按鈕
        cancel_text = f"""請確認要取消的報班：

📋 報班資訊：
• 工作名稱：{job.name}
• 工作地點：{job.location}
• 工作日期：{job.date}
• 報班班別：{application.shift}
• 報班時間：{application.applied_at}
• 報班編號：{application.id}"""
        
        actions = [
            {
                "type": "postback",
                "label": "✅ 確認取消",
                "data": f"action=job&step=confirm_cancel&job_id={job_id}"
            },
            {
                "type": "postback",
                "label": "🚫 不取消",
                "data": f"action=job&step=detail&job_id={job_id}"
            }
        ]
        
        messages = [
            {
                "type": "text",
                "text": cancel_text
            },
            {
                "type": "template",
                "altText": "📋 確認取消報班",
                "template": {
                    "type": "buttons",
                    "title": "📋 確認取消報班",
                    "text": "確定要取消這個報班嗎？",
                    "actions": actions
                }
            }
        ]
        
        self.message_service.send_multiple_messages(reply_token, messages)
    
    def handle_confirm_cancel(self, reply_token: str, user_id: str, job_id: str) -> None:
        """處理確認取消報班"""
        job = self.job_service.get_job(job_id)
        if not job:
            self.message_service.send_text(reply_token, "❌ 找不到指定的工作。")
            return
        
        success, canceled_app = self.application_service.cancel_application(user_id, job_id)
        
        if success and canceled_app:
            cancel_message = f"""✅ 報班已成功註銷！

📋 已註銷的報班資訊：
• 工作名稱：{job.name}
• 工作地點：{job.location}
• 工作日期：{job.date}
• 原報班班別：{canceled_app.shift}
• 報班編號：{canceled_app.id}

如有任何問題，歡迎隨時聯絡我們。"""
            self.message_service.send_text(reply_token, cancel_message)
        else:
            self.message_service.send_text(reply_token, "❌ 註銷報班失敗，請稍後再試。")
    
    def show_user_applications(self, reply_token: str, user_id: str) -> None:
        """顯示使用者已報班的可報班工作"""
        applications = self.application_service.get_user_applications(user_id)
        
        if not applications:
            self.message_service.send_text(
                reply_token,
                "📋 您目前沒有任何報班記錄。\n\n請使用「查看可報班工作」來尋找並報班工作。"
            )
            return
        
        # 建立報班列表訊息
        messages = []
        messages.append({
            "type": "text",
            "text": f"📋 您的報班記錄（共 {len(applications)} 筆）："
        })
        
        # 每個報班建立一個訊息卡片
        for i, app in enumerate(applications, 1):
            job = self.job_service.get_job(app.job_id)
            
            if not job:
                # 如果工作不存在，只顯示報班資訊
                app_text = f"{i}. 報班編號：{app.id}\n   班別：{app.shift}\n   報班時間：{app.applied_at}\n   ⚠️ 工作已不存在"
                messages.append({
                    "type": "text",
                    "text": app_text
                })
                continue
            
            # 建立報班資訊文字（確保不超過 60 字元）
            # 簡化工作名稱和地點
            job_name_display = job.name[:15] if len(job.name) > 15 else job.name
            location_display = job.location[:12] if len(job.location) > 12 else job.location
            if len(job.location) > 12:
                location_display += "..."
            
            # 簡化報班編號（顯示日期+流水號，例如：20260110-001）
            # 報班編號格式：工作編號-日期-流水號
            # 提取最後部分（日期-流水號）
            if '-' in app.id:
                parts = app.id.split('-')
                if len(parts) >= 2:
                    # 取最後兩部分：日期和流水號
                    app_id_display = f"{parts[-2]}-{parts[-1]}"
                else:
                    app_id_display = app.id[-12:] if len(app.id) > 12 else app.id
            else:
                app_id_display = app.id[-12:] if len(app.id) > 12 else app.id
            
            # 簡化報班時間（只顯示日期）
            applied_date = app.applied_at.split()[0] if " " in app.applied_at else app.applied_at
            
            # 建立文字，逐步檢查長度
            app_text = f"📌{job_name_display}\n🏠{location_display}\n📅{job.date}\n⏰{app.shift}"
            
            # 如果還有空間，加入報班編號
            test_text = app_text + f"\n。🏷️{app_id_display}"
            if len(test_text) <= 60:
                app_text = test_text
                # 如果還有更多空間，加入報班時間
                test_text = app_text + f"\n📝{applied_date}"
                if len(test_text) <= 60:
                    app_text = test_text
            
            # 建立 Google Maps 導航 URL
            encoded_location = urllib.parse.quote(job.location)
            navigation_url = f"https://www.google.com/maps/dir/?api=1&destination={encoded_location}"
            
            # 檢查使用者是否已註冊報班帳號
            is_registered = True
            if self.auth_service:
                is_registered = self.auth_service.is_line_user_registered(user_id)
            
            # 建立按鈕動作
            actions = [
                {
                    "type": "postback",
                    "label": "🔍 查看詳情",
                    "data": f"action=job&step=detail&job_id={job.id}"
                }
            ]
            
            if is_registered:
                actions.extend([
                    {
                        "type": "postback",
                        "label": "🚫 取消報班",
                        "data": f"action=job&step=cancel&job_id={job.id}"
                    },
                    {
                        "type": "uri",
                        "label": "🧭 導航",
                        "uri": navigation_url
                    }
                ])
            else:
                actions.append({
                    "type": "postback",
                    "label": "📝 註冊報班帳號",
                    "data": "action=register&step=register"
                })
            
            # 建立按鈕範本
            template = {
                "type": "buttons",
                "title": f"報班#{i}",
                "text": app_text,
                "actions": actions
            }
            
            # 如果有圖片，加入縮圖
            if job.location_image_url:
                template["thumbnailImageUrl"] = job.location_image_url
            
            messages.append({
                "type": "template",
                "altText": f"報班記錄 #{i} - {job.name}",
                "template": template
            })
        
        # 如果報班記錄很多，加入返回按鈕
        if len(applications) > 1:
            messages.append({
                "type": "template",
                "altText": "操作選單",
                "template": {
                    "type": "buttons",
                    "text": "請選擇操作：",
                    "actions": [
                        {
                            "type": "postback",
                            "label": "🔙 返回主選單",
                            "data": "action=job&step=menu"
                        },
                        {
                            "type": "postback",
                            "label": "🔍 可報班工作",
                            "data": "action=job&step=list"
                        }
                    ]
                }
            })
        
        self.message_service.send_multiple_messages(reply_token, messages)
        
        
    
    def handle_register(self, reply_token: str, user_id: str) -> None:
        """處理 LINE 使用者註冊報班帳號 - 開始註冊報班帳號流程"""
        logger.debug(f"handle_register: user_id: {user_id}")
        if not self.auth_service:
            self.message_service.send_text(reply_token, "❌ 註冊報班帳號功能暫時無法使用。")
            return
        
        # 檢查是否已註冊報班帳號
        if self.auth_service.is_line_user_registered(user_id):
            user = self.auth_service.get_user_by_line_id(user_id)
            if user:
                user_info = f"""✅ 您已經註冊報班帳號過了！

📋 您的帳號資訊：
• 🧑‍💼 姓名：{user.full_name or '未填寫'}
• 🎂 生日：{user.birthday or '未填寫'}
• 📞 手機：{user.phone or '未填寫'}
• 🏠 地址：{user.address or '未填寫'}
• 🪪 身份證：{user.id_number or '未填寫'}
• 📬 Email：{user.email or '未填寫'}
• 註冊時間：{user.created_at}"""
                self.message_service.send_text(reply_token, user_info)
            return
        
        # 開始註冊報班帳號流程 - 第一步：輸入姓名
        state = self.state_service.new_registration_state(user_id, step='name', data={})
        logger.debug(f"Start registration state: {state}")
        
        self.message_service.send_text(
            reply_token,
            "📝 歡迎註冊報班帳號！請依序填寫以下資料：\n\n"
            "🧑‍💼 第一步：請輸入您的姓名（至少二個中文字）"
        )
        
    def _handle_register_complete(self, reply_token: str, user_id: str, data: dict) -> None:
        logger.debug(f"_create_line_user: data: {data} (user_id: {user_id})")
        # 完成註冊報班帳號
        try:
            # 取得並驗證必填欄位
            full_name = data['full_name']
            birthday = data.get('birthday') or ''
            phone = data['phone']
            address = data['address']
            id_number = data.get('id_number') or ''
            email = data['email']

            # 建立使用者（確保所有欄位都有值）
            if not self.auth_service:
                self.message_service.send_text(reply_token, "❌ 註冊報班帳號功能暫時無法使用。")
                # 清除註冊報班帳號狀態
                self.state_service.delete_registration_state(user_id)
                return
            
            # 檢查是否為新註冊的用戶（在建立之前檢查）
            is_new_user = not self.auth_service.is_line_user_registered(user_id)
            
            # 建立使用者
            user = self.auth_service.create_line_user(
                line_user_id=user_id,
                full_name=full_name,
                birthday=birthday or None,
                phone=phone,
                address=address,
                id_number=id_number.upper().strip() if id_number else None,
                email=email
            )
            
            # 自動為新註冊的用戶設定已註冊用戶的 Rich Menu
            if is_new_user:
                logger.info(f"檢測到新註冊用戶 {user_id}，準備設定 Rich Menu")
                
                # 優先使用環境變數設定的 Rich Menu ID
                rich_menu_id = REGISTERED_USER_RICH_MENU_ID
                logger.debug(f"從環境變數讀取的 REGISTERED_USER_RICH_MENU_ID: {rich_menu_id}")
                
                # 如果未設定，嘗試從 Rich Menu 列表中查找
                if not rich_menu_id:
                    logger.info("環境變數未設定，嘗試從 Rich Menu 列表中查找...")
                    try:
                        rich_menus = self.rich_menu_service.get_rich_menu_list()
                        logger.debug(f"取得 {len(rich_menus)} 個 Rich Menu")
                        
                        # 方法1: 嘗試透過 name 欄位查找
                        for rm in rich_menus:
                            rm_id = rm.get('richMenuId')
                            rm_name = rm.get('name', '')
                            logger.debug(f"檢查 Rich Menu: ID={rm_id}, name={rm_name}")
                            
                            if rm_name == '已註冊用戶 Rich Menu':
                                rich_menu_id = rm_id
                                logger.info(f"透過 name 欄位找到已註冊用戶 Rich Menu: {rich_menu_id}")
                                break
                        
                        # 方法2: 如果方法1失敗，透過詳細資訊查找（檢查 areas 數量）
                        if not rich_menu_id:
                            logger.info("透過 name 欄位未找到，嘗試透過詳細資訊查找...")
                            for rm in rich_menus:
                                rm_id = rm.get('richMenuId')
                                if not rm_id or not isinstance(rm_id, str):
                                    continue
                                try:
                                    rm_detail = self.rich_menu_service.get_rich_menu(rm_id)
                                    if rm_detail:
                                        areas = rm_detail.get('areas', [])
                                        # 已註冊用戶有 3 個區域，未註冊用戶有 2 個區域
                                        if len(areas) == 3:
                                            # 進一步檢查是否有 "已報班記錄" 的 action
                                            has_my_applications = any(
                                                area.get('action', {}).get('data', '').endswith('my_applications')
                                                for area in areas
                                            )
                                            if has_my_applications:
                                                rich_menu_id = rm_id
                                                logger.info(f"透過詳細資訊找到已註冊用戶 Rich Menu: {rich_menu_id}")
                                                break
                                except Exception as e:
                                    logger.debug(f"取得 Rich Menu {rm_id} 詳細資訊時發生錯誤：{e}")
                                    continue
                    except Exception as e:
                        logger.error(f"查找 Rich Menu 列表時發生錯誤：{e}", exc_info=True)
                
                # 設定 Rich Menu
                if rich_menu_id:
                    logger.info(f"準備為用戶 {user_id} 設定 Rich Menu: {rich_menu_id}")
                    try:
                        success = self.rich_menu_service.set_user_rich_menu(user_id, rich_menu_id)
                        if success:
                            logger.info(f"✅ 已為新註冊用戶 {user_id} 設定 Rich Menu: {rich_menu_id}")
                        else:
                            logger.warning(f"❌ 為用戶 {user_id} 設定 Rich Menu 失敗（API 返回失敗）")
                    except Exception as e:
                        logger.error(f"❌ 設定用戶 Rich Menu 時發生錯誤：{e}", exc_info=True)
                        # 不影響註冊流程，繼續執行
                else:
                    logger.warning(f"⚠️  未找到已註冊用戶的 Rich Menu，跳過自動設定（用戶 {user_id}）")
            else:
                logger.debug(f"用戶 {user_id} 不是新註冊用戶，跳過 Rich Menu 設定")
            
            success_message = f"""✅ 註冊報班帳號成功！

📋 您的註冊報班帳號資訊：
• 🧑‍💼 姓名：{user.full_name}
• 🎂 生日：{user.birthday or '未填寫'}
• 📞 手機：{user.phone}
• 🏠 地址：{user.address}
• 🪪 身份證：{user.id_number or '未填寫'}
• 📬 Email：{user.email or '未填寫'}
• 註冊時間：{user.created_at}

現在您可以開始報班工作了！"""
            
            # 清除註冊報班帳號狀態
            self.state_service.delete_registration_state(user_id)
            
            # 發送成功訊息和主選單
            messages: List[Dict[str, Any]] = [
                {
                    "type": "text",
                    "text": success_message
                },
                self._build_main_menu_message(user_id)  # 使用輔助方法構建主選單
            ]
            
            self.message_service.send_multiple_messages(reply_token, messages)
            
        except Exception as e:
            logger.error(f"註冊報班帳號失敗：{e}", exc_info=True)
            # 清除註冊報班帳號狀態
            self.state_service.delete_registration_state(user_id)
            self.message_service.send_text(
                reply_token,
                f"❌ 註冊報班帳號失敗：{str(e)}\n\n請稍後再試或聯絡客服。"
            )

        
                    
    def handle_register_input(self, reply_token: str, user_id: str, text: str) -> None:

        state = self.state_service.get_registration_state(user_id)
        if state is None:
            logger.debug(f"handle_register_input: user_id: {user_id} not in registration_states")
            return
        
        step = state.get('step', None)
        if step is None:
            logger.debug(f"handle_register_input: user_id: {user_id} state missing 'step' key")
            return
        
        logger.debug(f"handle_register_input: step: {step} (data: {state['data']}) (user_id: {user_id})")
        if step == 'name':
            # 儲存姓名（至少二個中文字），進入下一步
            name = text.strip()
            if not name:
                self.message_service.send_text(
                    reply_token,
                    "❌ 姓名不能為空，請重新輸入。"
                )
                return
            if not validate_name_at_least_two_chinese(name):
                self.message_service.send_text(
                    reply_token,
                    "❌ 姓名至少需包含二個中文字，請重新輸入。"
                )
                return
            state['data']['full_name'] = name
            self.state_service.update_registration_state(user_id, step='birthday', data=state['data'])
            logger.debug(f"Set registration_states: new step: birthday (data: {state['data']}) (user_id: {user_id})")
            # 使用 date picker 選擇生日（範圍：今天-65年 ～ 今天-15年）
            today = datetime.date.today()
            min_birthday = today.replace(year=today.year - 65)
            max_birthday = today.replace(year=today.year - 15)
            picker_action = {
                "type": "datetimepicker",
                "label": "選擇生日",
                "data": "action=register&step=birthday",
                "mode": "date",
                "min": min_birthday.isoformat(),
                "max": max_birthday.isoformat()
            }
            messages = [
                {"type": "text", "text": f"✅ 姓名已記錄：{name}\n\n🎂 第二步：請點下方按鈕選擇生日"},
                {
                    "type": "template",
                    "altText": "選擇生日",
                    "template": {
                        "type": "buttons",
                        "title": "選擇生日",
                        "text": "請點下方按鈕選擇您的生日（西元）",
                        "actions": [picker_action]
                    }
                }
            ]
            self.message_service.send_multiple_messages(reply_token, messages)

        elif step == 'birthday':
            # 若使用者用文字輸入生日（date picker 以外的備援）
            raw = text.strip()
            if not validate_birthday_iso(raw):
                self.message_service.send_text(
                    reply_token,
                    "❌ 生日格式不正確，請點下方按鈕選擇生日，或使用西元 YYYY-MM-DD（例：1990-01-15）。"
                )
                return
            state['data']['birthday'] = raw
            self.state_service.update_registration_state(user_id, step='phone', data=state['data'])
            self.message_service.send_text(
                reply_token,
                f"✅ 生日已記錄：{raw}\n\n📞 第三步：請輸入您的手機號碼（格式：09XX-XXX-XXX 或 09XXXXXXXX）"
            )
        
        elif step == 'phone':
            # 驗證並儲存手機號碼
            phone = text.strip().replace('-', '').replace(' ', '')
            if not phone.isdigit() or len(phone) != 10 or not phone.startswith('09'):
                self.message_service.send_text(
                    reply_token,
                    "❌ 手機號碼格式不正確，請輸入 10 位數手機（例如：0912345678）。"
                )
                return
            
            state['data']['phone'] = phone
            self.state_service.update_registration_state(user_id, step='address', data=state['data'])
            self.message_service.send_text(
                reply_token,
                f"✅ 手機號碼已記錄：{phone}\n\n🏠 第四步：請輸入您的地址"
            )
        
        elif step == 'address':
            address = text.strip()
            if not address:
                self.message_service.send_text(
                    reply_token,
                    "❌ 地址不能為空，請重新輸入。"
                )
                return
            state['data']['address'] = address
            self.state_service.update_registration_state(user_id, step='id_number', data=state['data'])
            self.message_service.send_text(
                reply_token,
                f"✅ 地址已記錄：{address}\n\n🪪 第五步：請輸入您的身份證字號（台灣身份證格式）"
            )

        elif step == 'id_number':
            # 驗證並儲存台灣身份證字號
            id_str = text.strip().upper().replace(' ', '')
            if not validate_taiwan_id(id_str):
                self.message_service.send_text(
                    reply_token,
                    "❌ 身份證字號格式或檢核不符，請輸入正確的台灣身份證字號（一碼英文+九碼數字）。"
                )
                return
            state['data']['id_number'] = id_str
            self.state_service.update_registration_state(user_id, step='email', data=state['data'])
            self.message_service.send_text(
                reply_token,
                f"✅ 身份證已記錄\n\n📬 第六步：請輸入您的 E-mail（須可收信）"
            )
        
        elif step == 'email':
            email = text.strip()
            if not validate_email(email):
                self.message_service.send_text(
                    reply_token,
                    "❌ E-mail 格式不正確，請重新輸入。"
                )
                return
            state['data']['email'] = email
            self.state_service.update_registration_state(user_id, data=state['data'])
            self._handle_register_complete(reply_token, user_id, state['data'])

    def handle_register_birthday_picked(self, reply_token: str, user_id: str, date_str: str) -> None:
        """處理註冊流程中由 date picker 選擇的生日"""
        state = self.state_service.get_registration_state(user_id)
        if state is None or state.get('step') != 'birthday':
            logger.warning(f"handle_register_birthday_picked: user_id={user_id} state invalid or step not birthday (state={state})")
            self.message_service.send_text(
                reply_token,
                "❓ 未偵測到註冊中的生日步驟，請重新點「註冊報班帳號」從頭填寫。"
            )
            return
        if not isinstance(state.get('data'), dict):
            state['data'] = state.get('data') or {}
        state['data']['birthday'] = date_str
        self.state_service.update_registration_state(user_id, step='phone', data=state['data'])
        self.message_service.send_text(
            reply_token,
            f"✅ 生日已記錄：{date_str}\n\n📞 第三步：請輸入您的手機號碼（格式：09XX-XXX-XXX 或 09XXXXXXXX）"
        )
    
    def handle_edit_profile(self, reply_token: str, user_id: str) -> None:
        """處理修改報班帳號資料 - 選擇要修改的欄位"""
        if not self.auth_service:
            self.message_service.send_text(reply_token, "❌ 修改報班帳號資料功能暫時無法使用。")
            return
        
        # 檢查是否已註冊報班帳號
        if not self.auth_service.is_line_user_registered(user_id):
            self.message_service.send_text(
                reply_token,
                "❌ 您尚未註冊報班帳號，無法修改報班帳號資料。\n\n請先使用「註冊報班帳號」功能完成註冊報班帳號。"
            )
            return
        
        # 取得當前使用者資料
        user = self.auth_service.get_user_by_line_id(user_id)
        if not user:
            self.message_service.send_text(reply_token, "❌ 找不到您的帳號資訊。")
            return
        
        # 顯示選擇要修改的欄位（可修改：手機、地址、Email；LINE 按鈕範本最多 4 個）
        actions = [
            {"type": "postback", "label": "📞 手機", "data": "action=edit_profile&step=input&field=phone"},
            {"type": "postback", "label": "🏠 地址", "data": "action=edit_profile&step=input&field=address"},
            {"type": "postback", "label": "📬 Email", "data": "action=edit_profile&step=input&field=email"},
            {"type": "postback", "label": "🔙 返回", "data": "action=view_profile&step=view"}
        ]
        
        # LINE 按鈕範本 text 欄位限制 60 字元，需要簡化顯示
        # 使用最簡潔的版本，只顯示關鍵提示
        current_info = "📋修改報班帳號資料\n\n請選擇要修改的欄位："
        
        try:
            response = self.message_service.send_buttons_template(
                reply_token,
                "修改報班帳號資料",
                current_info,
                actions
            )
            response.raise_for_status()  # 檢查 HTTP 狀態碼
        except requests.exceptions.RequestException as e:
            logger.error(f"發送修改報班帳號資料選單失敗: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.debug(f"回應內容：{e.response.text}")
            # 嘗試發送文字訊息作為備用
            backup_message = f"""📋 您目前的資料：

• 🧑‍💼 姓名：{user.full_name or '未填寫'}（不可修改）
• 🎂 生日：{user.birthday or '未填寫'}
• 📞 手機：{user.phone or '未填寫'}
• 🏠 地址：{user.address or '未填寫'}
• 🪪 身份證：{user.id_number or '未填寫'}
• 📬 Email：{user.email or '未填寫'}

請點擊主選單中的「修改報班帳號資料」來修改資料。"""
            self.message_service.send_text(reply_token, backup_message)
    
    def handle_edit_profile_input(self, reply_token: str, user_id: str, text: str) -> None:
        """處理修改報班帳號資料輸入"""
        if not self.auth_service:
            return
        
        # 檢查是否在修改流程中
        state = self.state_service.get_edit_profile_state(user_id)
        if state is None:
            return
        
        # 檢查是否要取消修改
        if text.strip().lower() in ['取消', 'cancel', '取消修改']:
            self.state_service.delete_edit_profile_state(user_id)
            self.message_service.send_text(
                reply_token,
                "❌ 已取消修改流程。"
            )
            return
        
        field = state.get('field')
        
        if field == 'phone':
            # 驗證並更新手機號碼
            phone = text.strip().replace('-', '').replace(' ', '')
            if not phone.isdigit() or len(phone) != 10 or not phone.startswith('09'):
                self.message_service.send_text(
                    reply_token,
                    "❌ 手機號碼格式不正確，請輸入10位數手機號碼（例如：0912345678）\n\n或輸入「取消」取消修改。"
                )
                return
            
            # 更新資料
            user = self.auth_service.get_user_by_line_id(user_id)
            if user:
                self.auth_service.create_line_user(
                    line_user_id=user_id,
                    full_name=user.full_name,
                    birthday=user.birthday,
                    phone=phone,
                    address=user.address,
                    id_number=user.id_number,
                    email=user.email
                )
                
                # 清除修改狀態
                self.state_service.delete_edit_profile_state(user_id)
                
                # 發送成功訊息並返回查看報班帳號資料頁面
                success_message = f"✅ 手機號碼已更新為：{phone}"
                self._send_update_success_and_show_profile(reply_token, user_id, success_message)
            else:
                self.state_service.delete_edit_profile_state(user_id)
                self.message_service.send_text(reply_token, "❌ 找不到您的帳號資訊。")
        
        elif field == 'address':
            # 更新地址
            address = text.strip()
            if not address:
                self.message_service.send_text(
                    reply_token,
                    "❌ 地址不能為空，請重新輸入。\n\n或輸入「取消」取消修改。"
                )
                return
            
            # 更新資料
            user = self.auth_service.get_user_by_line_id(user_id)
            if user:
                self.auth_service.create_line_user(
                    line_user_id=user_id,
                    full_name=user.full_name,
                    birthday=user.birthday,
                    phone=user.phone,
                    address=address,
                    id_number=user.id_number,
                    email=user.email
                )
                
                # 清除修改狀態
                self.state_service.delete_edit_profile_state(user_id)
                
                # 發送成功訊息並返回查看報班帳號資料頁面
                success_message = f"✅ 地址已更新為：{address}"
                self._send_update_success_and_show_profile(reply_token, user_id, success_message)
            else:
                self.state_service.delete_edit_profile_state(user_id)
                self.message_service.send_text(reply_token, "❌ 找不到您的帳號資訊。")
        
        elif field == 'email':
            # 更新 Email
            email = text.strip()
            if email.lower() in ['跳過', 'skip', '略過', '清除', '清空', '']:
                email = None
            else:
                if not validate_email(email):
                    self.message_service.send_text(
                        reply_token,
                        "❌ Email 格式不正確，請重新輸入或輸入「跳過」清除 Email。"
                    )
                    return
            
            # 更新資料
            user = self.auth_service.get_user_by_line_id(user_id)
            if user:
                self.auth_service.create_line_user(
                    line_user_id=user_id,
                    full_name=user.full_name,
                    birthday=user.birthday,
                    phone=user.phone,
                    address=user.address,
                    id_number=user.id_number,
                    email=email
                )
                
                # 清除修改狀態
                self.state_service.delete_edit_profile_state(user_id)
                
                # 發送成功訊息並返回查看報班帳號資料頁面
                if email:
                    success_message = f"✅ Email 已更新為：{email}"
                else:
                    success_message = "✅ Email 已清除。"
                self._send_update_success_and_show_profile(reply_token, user_id, success_message)
            else:
                self.state_service.delete_edit_profile_state(user_id)
                self.message_service.send_text(reply_token, "❌ 找不到您的帳號資訊。")
    
    def _send_update_success_and_show_profile(self, reply_token: str, user_id: str, success_message: str) -> None:
        """發送更新成功訊息並顯示報班帳號資料頁面"""
        # 取得更新後的使用者資料
        user = self.auth_service.get_user_by_line_id(user_id) if self.auth_service else None
        if not user:
            # 如果無法取得使用者資料，只發送成功訊息
            self.message_service.send_text(reply_token, success_message)
            return
        
        # 顯示更新後的報班帳號資料
        user_info = f"""📋 您的報班帳號資料：

• 🧑‍💼 姓名：{user.full_name or '未填寫'}
• 🎂 生日：{user.birthday or '未填寫'}
• 📞 手機：{user.phone or '未填寫'}
• 🏠 地址：{user.address or '未填寫'}
• 🪪 身份證：{user.id_number or '未填寫'}
• 📬 Email：{user.email or '未填寫'}
• 註冊時間：{user.created_at}"""
        
        # 準備操作按鈕
        actions = [
            {
                "type": "postback",
                "label": "✏️ 修改資料",
                "data": "action=edit_profile&step=select_field"
            },
            {
                "type": "postback",
                "label": "🗑️ 註銷帳號",
                "data": "action=delete_registration&step=confirm"
            },
            {
                "type": "postback",
                "label": "🔙 返回主選單",
                "data": "action=job&step=menu"
            }
        ]
        
        # 使用 send_multiple_messages 在同一個回覆中發送成功訊息、更新後的資料和操作按鈕
        messages = [
            {
                "type": "text",
                "text": success_message
            },
            {
                "type": "text",
                "text": user_info
            },
            {
                "type": "template",
                "altText": "報班帳號資料操作",
                "template": {
                    "type": "buttons",
                    "title": "📋 報班帳號",
                    "text": "請選擇操作：",
                    "actions": actions
                }
            }
        ]
        
        try:
            self.message_service.send_multiple_messages(reply_token, messages)
        except Exception as e:
            logger.error(f"發送更新成功訊息和報班帳號資料失敗: {e}", exc_info=True)
            # 如果發送失敗，至少發送成功訊息
            self.message_service.send_text(reply_token, success_message)
    
    def handle_delete_registration(self, reply_token: str, user_id: str) -> None:
        """處理註銷報班帳號 - 顯示確認訊息"""
        if not self.auth_service:
            self.message_service.send_text(reply_token, "❌ 註銷報班帳號功能暫時無法使用。")
            return
        
        # 檢查是否已註冊報班帳號
        if not self.auth_service.is_line_user_registered(user_id):
            self.message_service.send_text(
                reply_token,
                "❌ 您尚未註冊報班帳號，無需取消。"
            )
            return
        
        # 取得使用者資料
        user = self.auth_service.get_user_by_line_id(user_id)
        if not user:
            self.message_service.send_text(reply_token, "❌ 找不到您的帳號資訊。")
            return
        
        # 顯示確認訊息（LINE 按鈕範本 text 限制 60 字元）
        # 使用簡潔版本
        confirm_text = "⚠️ 確認註銷報班帳號\n\n取消後將無法報班工作，且無法復原。\n\n確定要取消嗎？"
        
        actions = [
            {
                "type": "postback",
                "label": "✅ 確認註銷",
                "data": "action=delete_registration&step=confirm_delete"
            },
            {
                "type": "postback",
                "label": "🔙 返回",
                "data": "action=view_profile&step=view"
            }
        ]
        
        self.message_service.send_buttons_template(
            reply_token,
            "🗑️ 註銷報班帳號",
            confirm_text,
            actions
        )
    
    def handle_confirm_delete_registration(self, reply_token: str, user_id: str) -> None:
        """處理確認註銷報班帳號"""
        if not self.auth_service:
            self.message_service.send_text(reply_token, "❌ 註銷報班帳號功能暫時無法使用。")
            return
        
        # 檢查是否已註冊報班帳號
        if not self.auth_service.is_line_user_registered(user_id):
            self.message_service.send_text(
                reply_token,
                "❌ 您尚未註冊報班帳號，無需取消。"
            )
            return
        
        # 取消使用者註冊報班帳號
        success = self.auth_service.delete_line_user(user_id)
        
        if success:
            # 同時取消該使用者的所有報班記錄
            applications = self.application_service.get_user_applications(user_id)
            for app in applications:
                self.application_service.cancel_application(user_id, app.job_id)
            
            # 自動將用戶的 Rich Menu 設為未註冊用戶的 Rich Menu
            logger.info(f"用戶 {user_id} 已註銷，準備設定未註冊用戶的 Rich Menu")
            
            # 優先使用環境變數設定的 Rich Menu ID
            rich_menu_id = UNREGISTERED_USER_RICH_MENU_ID
            logger.debug(f"從環境變數讀取的 UNREGISTERED_USER_RICH_MENU_ID: {rich_menu_id}")
            
            # 如果未設定，嘗試從 Rich Menu 列表中查找
            if not rich_menu_id:
                logger.info("環境變數未設定，嘗試從 Rich Menu 列表中查找...")
                try:
                    rich_menus = self.rich_menu_service.get_rich_menu_list()
                    logger.debug(f"取得 {len(rich_menus)} 個 Rich Menu")
                    
                    # 方法1: 嘗試透過 name 欄位查找
                    for rm in rich_menus:
                        rm_id = rm.get('richMenuId')
                        rm_name = rm.get('name', '')
                        logger.debug(f"檢查 Rich Menu: ID={rm_id}, name={rm_name}")
                        
                        if rm_name == '未註冊用戶 Rich Menu':
                            rich_menu_id = rm_id
                            logger.info(f"透過 name 欄位找到未註冊用戶 Rich Menu: {rich_menu_id}")
                            break
                    
                    # 方法2: 如果方法1失敗，透過詳細資訊查找（檢查 areas 數量）
                    if not rich_menu_id:
                        logger.info("透過 name 欄位未找到，嘗試透過詳細資訊查找...")
                        for rm in rich_menus:
                            rm_id = rm.get('richMenuId')
                            if not rm_id or not isinstance(rm_id, str):
                                continue
                            try:
                                rm_detail = self.rich_menu_service.get_rich_menu(rm_id)
                                if rm_detail:
                                    areas = rm_detail.get('areas', [])
                                    # 未註冊用戶有 2 個區域，已註冊用戶有 3 個區域
                                    if len(areas) == 2:
                                        # 進一步檢查是否有 "註冊功能" 的 action
                                        has_register = any(
                                            'action=register' in area.get('action', {}).get('data', '')
                                            for area in areas
                                        )
                                        if has_register:
                                            rich_menu_id = rm_id
                                            logger.info(f"透過詳細資訊找到未註冊用戶 Rich Menu: {rich_menu_id}")
                                            break
                            except Exception as e:
                                logger.debug(f"取得 Rich Menu {rm_id} 詳細資訊時發生錯誤：{e}")
                                continue
                except Exception as e:
                    logger.error(f"查找 Rich Menu 列表時發生錯誤：{e}", exc_info=True)
            
            # 設定 Rich Menu
            if rich_menu_id:
                logger.info(f"準備為用戶 {user_id} 設定未註冊用戶的 Rich Menu: {rich_menu_id}")
                try:
                    success_rm = self.rich_menu_service.set_user_rich_menu(user_id, rich_menu_id)
                    if success_rm:
                        logger.info(f"✅ 已為註銷用戶 {user_id} 設定未註冊用戶的 Rich Menu: {rich_menu_id}")
                    else:
                        logger.warning(f"❌ 為用戶 {user_id} 設定未註冊用戶的 Rich Menu 失敗（API 返回失敗）")
                except Exception as e:
                    logger.error(f"❌ 設定用戶 Rich Menu 時發生錯誤：{e}", exc_info=True)
                    # 不影響註銷流程，繼續執行
            else:
                logger.warning(f"⚠️  未找到未註冊用戶的 Rich Menu，跳過自動設定（用戶 {user_id}）")
            
            self.message_service.send_text(
                reply_token,
                "✅ 您的報班帳號已成功取消。\n\n如需重新使用服務，請重新註冊報班帳號。"
            )
        else:
            self.message_service.send_text(
                reply_token,
                "❌ 註銷報班帳號失敗，請稍後再試或聯絡客服。"
            )
    
    def show_user_profile(self, reply_token: str, user_id: str) -> None:
        """顯示使用者報班帳號資料"""
        if not self.auth_service:
            self.message_service.send_text(reply_token, "❌ 查看報班帳號資料功能暫時無法使用。")
            return
        
        # 檢查是否已註冊報班帳號
        if not self.auth_service.is_line_user_registered(user_id):
            self.message_service.send_text(
                reply_token,
                "❌ 您尚未註冊報班帳號，無法查看報班帳號資料。\n\n請先使用「註冊報班帳號」功能完成註冊報班帳號。"
            )
            return
        
        # 取得使用者資料
        user = self.auth_service.get_user_by_line_id(user_id)
        if not user:
            self.message_service.send_text(reply_token, "❌ 找不到您的帳號資訊。")
            return
        
        # 顯示報班帳號資料（使用文字訊息，因為內容較長）
        user_info = f"""📋 您的報班帳號資料：

• 🧑‍💼 姓名：{user.full_name or '未填寫'}
• 🎂 生日：{user.birthday or '未填寫'}
• 📞 手機：{user.phone or '未填寫'}
• 🏠 地址：{user.address or '未填寫'}
• 🪪 身份證：{user.id_number or '未填寫'}
• 📬 Email：{user.email or '未填寫'}
• 註冊時間：{user.created_at}"""
        
        # 準備操作按鈕
        actions = [
            {
                "type": "postback",
                "label": "✏️ 修改資料",
                "data": "action=edit_profile&step=select_field"
            },
            {
                "type": "postback",
                "label": "🗑️ 註銷帳號",
                "data": "action=delete_registration&step=confirm"
            },
            {
                "type": "postback",
                "label": "🔙 返回主選單",
                "data": "action=job&step=menu"
            }
        ]
        
        # 使用 send_multiple_messages 在同一個回覆中發送資料和按鈕
        messages = [
            {
                "type": "text",
                "text": user_info
            },
            {
                "type": "template",
                "altText": "報班帳號資料操作",
                "template": {
                    "type": "buttons",
                    "title": "📋 報班帳號",
                    "text": "請選擇操作：",
                    "actions": actions
                }
            }
        ]
        
        try:
            self.message_service.send_multiple_messages(reply_token, messages)
        except Exception as e:
            logger.error(f"發送報班帳號資料失敗: {e}", exc_info=True)
            # 如果發送失敗，至少發送文字訊息
            self.message_service.send_text(reply_token, user_info)
    
    def _build_main_menu_message(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """構建主選單訊息（不發送）"""
        # 檢查使用者是否已註冊報班帳號
        is_registered = False
        if self.auth_service and user_id:
            is_registered = self.auth_service.is_line_user_registered(user_id)
        
        actions = []
        
        if not is_registered:
            # 未註冊報班帳號使用者：顯示註冊報班帳號選項
            actions.append({
                "type": "postback",
                "label": "📝 註冊報班帳號",
                "data": "action=register&step=register"
            })
        
        actions.extend([
            {
                "type": "postback",
                "label": "📋 可報班工作",
                "data": "action=job&step=list"
            },
            {
                "type": "postback",
                "label": "🔍 已報班記錄",
                "data": "action=job&step=my_applications"
            }
        ])
        
        # 已註冊報班帳號使用者：顯示查看報班帳號資料選項
        if is_registered:
            actions.append({
                "type": "postback",
                "label": "👤 報班帳號",
                "data": "action=view_profile&step=view"
            })
        
        actions.append({
            "type": "message",
            "label": "📞 聯絡客服",
            "text": "我需要客服協助"
        })
        
        menu_text = "請選擇您需要的服務："
        if not is_registered:
            menu_text = "⚠️ 您尚未註冊報班帳號，請先完成註冊才能報班工作。\n\n" + menu_text
        
        return {
            "type": "template",
            "altText": "💼 Good Jobs 報班系統",
            "template": {
                "type": "buttons",
                "title": "💼 Good Jobs 報班系統",
                "text": menu_text,
                "actions": actions
            }
        }
    
    def show_main_menu(self, reply_token: str, user_id: Optional[str] = None) -> None:
        """顯示主選單"""
        menu_message = self._build_main_menu_message(user_id)
        self.message_service.send_buttons_template(
            reply_token,
            "Good Jobs 報班系統",
            menu_message["template"]["text"],
            menu_message["template"]["actions"]
        )

