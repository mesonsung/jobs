"""
LINE Bot 工作事件處理器
"""
from typing import Dict, Optional, List
import urllib.parse
import datetime

from app.services.job_service import JobService
from app.services.application_service import ApplicationService
from app.services.line_message_service import LineMessageService
from app.services.auth_service import AuthService
from app.models.schemas import Job, Application

class JobHandler:
    """工作事件處理器"""
    
    def __init__(self, job_service: JobService, application_service: ApplicationService, message_service: LineMessageService, auth_service: Optional[AuthService] = None):
        self.job_service = job_service
        self.application_service = application_service
        self.message_service = message_service
        self.auth_service = auth_service
        # 註冊狀態管理：{user_id: {'step': step, 'data': {...}}}
        self.registration_states: Dict[str, Dict] = {}
        # 修改資料狀態管理：{user_id: {'step': step, 'field': field_name}}
        self.edit_profile_states: Dict[str, Dict] = {}
    
    def show_available_jobs(self, reply_token: str, user_id: Optional[str] = None) -> None:
        """顯示可報班的工作列表"""
        jobs = self.job_service.get_available_jobs()
        
        print(f"📋 查詢可報班工作：找到 {len(jobs)} 個工作")
        
        if not jobs:
            self.message_service.send_text(
                reply_token,
                "目前沒有可報班的工作。\n\n請稍後再試，或聯絡管理員。\n\n💡 提示：管理員可以透過 API 發佈新工作。"
            )
            return
        
        # 建立工作列表訊息
        messages = []
        messages.append({
            "type": "text",
            "text": f"📋 可報班的工作（共 {len(jobs)} 個）："
        })
        
        # 每個工作建立一個 Flex 訊息或按鈕訊息
        for job in jobs:
            # 檢查使用者是否已報班
            is_applied = False
            applied_shift = None
            if user_id:
                application = self.application_service.get_user_application_for_job(user_id, job.id)
                if application:
                    is_applied = True
                    applied_shift = application.shift
            
            # 建立狀態標示
            status_icon = "✅ 已報班" if is_applied else "⭕ 未報班"
            status_text = f"\n{status_icon}"
            if is_applied and applied_shift:
                status_text += f" ({applied_shift})"
            
            # 建立 Google Maps 導航 URL
            encoded_location = urllib.parse.quote(job.location)
            navigation_url = f"https://www.google.com/maps/dir/?api=1&destination={encoded_location}"
            
            # 檢查使用者是否已註冊
            is_registered = True
            if self.auth_service:
                is_registered = self.auth_service.is_line_user_registered(user_id) if user_id else False
            
            # 建立按鈕動作
            actions = [
                {
                    "type": "postback",
                    "label": "查看詳情",
                    "data": f"action=job&step=detail&job_id={job.id}"
                }
            ]
            
            # 如果未註冊，加入註冊按鈕
            if not is_registered:
                actions.append({
                    "type": "postback",
                    "label": "📝 註冊",
                    "data": "action=register&step=register"
                })
            # 根據報班狀態加入不同按鈕
            elif is_applied:
                # 已報班：加入取消報班按鈕
                actions.append({
                    "type": "postback",
                    "label": "取消報班",
                    "data": f"action=job&step=cancel&job_id={job.id}"
                })
            else:
                # 未報班：加入報班按鈕
                actions.append({
                    "type": "postback",
                    "label": "報班",
                    "data": f"action=job&step=apply&job_id={job.id}"
                })
            
            # 加入導航按鈕
            actions.append({
                "type": "uri",
                "label": "導航",
                "uri": navigation_url
            })
            
            # 建立按鈕範本文字（確保不超過 60 字元，包括換行符）
            # 簡化地點顯示（如果太長）
            location_display = job.location
            max_location_len = 18
            if len(location_display) > max_location_len:
                location_display = location_display[:max_location_len-3] + "..."
            
            # 建立班別顯示文字
            if len(job.shifts) == 1:
                shifts_display = job.shifts[0]
            elif len(job.shifts) == 2:
                shifts_display = ", ".join(job.shifts)
            else:
                # 多個班別時，只顯示第一個和總數
                shifts_display = f"{job.shifts[0]}等{len(job.shifts)}個"
            
            # 建立基本文字（不含狀態）
            base_text = f"📍{location_display}\n📅{job.date}\n⏰{shifts_display}"
            
            # 嘗試加入狀態文字
            if is_applied:
                status_display = "\n✅已報班"
                if applied_shift and len(applied_shift) <= 10:
                    status_display += f"({applied_shift[:8]})"
            else:
                status_display = "\n⭕未報班"
            
            # 檢查總長度（換行符算 1 個字元）
            test_text = base_text + status_display
            if len(test_text) <= 60:
                job_text = test_text
            else:
                # 如果太長，簡化班別顯示
                if len(job.shifts) > 1:
                    shifts_display = f"{len(job.shifts)}個班別"
                else:
                    shifts_display = job.shifts[0][:10] if job.shifts else ""
                
                base_text = f"📍{location_display}\n📅{job.date}\n⏰{shifts_display}"
                test_text = base_text + status_display
                
                if len(test_text) <= 60:
                    job_text = test_text
                else:
                    # 最後手段：只顯示基本資訊，不顯示狀態
                    job_text = base_text
            
            template = {
                "type": "buttons",
                "title": job.name[:40],  # LINE 限制標題長度
                "text": job_text,
                "actions": actions
            }
            
            # 如果有圖片，加入縮圖（LINE API 不接受 None 值）
            if job.location_image_url:
                template["thumbnailImageUrl"] = job.location_image_url
                # 也可以選擇發送單獨的圖片訊息
                # messages.append({
                #     "type": "image",
                #     "originalContentUrl": job.location_image_url,
                #     "previewImageUrl": job.location_image_url
                # })
            
            messages.append({
                "type": "template",
                "altText": job.name,
                "template": template
            })
        
        self.message_service.send_multiple_messages(reply_token, messages)
    
    def show_job_detail(self, reply_token: str, user_id: str, job_id: str) -> None:
        """顯示工作詳情"""
        job = self.job_service.get_job(job_id)
        if not job:
            self.message_service.send_text(reply_token, "❌ 找不到指定的工作。")
            return
        
        # 檢查使用者是否已註冊
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

📍 工作地點：{job.location}
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
            # 未註冊使用者：顯示註冊按鈕
            actions.append({
                "type": "postback",
                "label": "📝 註冊",
                "data": "action=register&step=register"
            })
        elif is_applied:
            actions.append({
                "type": "postback",
                "label": "取消報班",
                "data": f"action=job&step=cancel&job_id={job_id}"
            })
        else:
            actions.append({
                "type": "postback",
                "label": "報班",
                "data": f"action=job&step=apply&job_id={job_id}"
            })
        
        # 加入導航按鈕
        actions.append({
            "type": "uri",
            "label": "導航",
            "uri": navigation_url
        })
        
        actions.append({
            "type": "postback",
            "label": "返回工作列表",
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
                "text": "請選擇操作：",
                "actions": actions
            }
        })
        
        self.message_service.send_multiple_messages(reply_token, messages)
    
    def handle_apply_job(self, reply_token: str, user_id: str, job_id: str) -> None:
        """處理報班工作流程 - 顯示班別選擇"""
        # 檢查使用者是否已註冊
        if self.auth_service and not self.auth_service.is_line_user_registered(user_id):
            self.message_service.send_text(
                reply_token,
                "❌ 您尚未註冊，無法報班工作。\n\n請先使用「註冊」功能完成註冊。"
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
                "label": shift,
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
                    "title": "選擇班別",
                    "text": "請選擇您要報班的班別：",
                    "actions": shift_actions
                }
            }
        ]
        
        self.message_service.send_multiple_messages(reply_token, messages)
    
    def handle_select_shift(self, reply_token: str, user_id: str, job_id: str, shift: str) -> None:
        """處理選擇班別並完成報班"""
        # 檢查使用者是否已註冊
        if self.auth_service and not self.auth_service.is_line_user_registered(user_id):
            self.message_service.send_text(
                reply_token,
                "❌ 您尚未註冊，無法報班工作。\n\n請先使用「註冊」功能完成註冊。"
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
                "label": "確認取消",
                "data": f"action=job&step=confirm_cancel&job_id={job_id}"
            },
            {
                "type": "postback",
                "label": "不取消",
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
                "altText": "確認取消報班",
                "template": {
                    "type": "buttons",
                    "title": "確認取消報班",
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
            cancel_message = f"""✅ 報班已成功取消！

📋 已取消的報班資訊：
• 工作名稱：{job.name}
• 工作地點：{job.location}
• 工作日期：{job.date}
• 原報班班別：{canceled_app.shift}
• 報班編號：{canceled_app.id}

如有任何問題，歡迎隨時聯絡我們。"""
            self.message_service.send_text(reply_token, cancel_message)
        else:
            self.message_service.send_text(reply_token, "❌ 取消報班失敗，請稍後再試。")
    
    def show_user_applications(self, reply_token: str, user_id: str) -> None:
        """顯示使用者已報班的工作列表"""
        applications = self.application_service.get_user_applications(user_id)
        
        if not applications:
            self.message_service.send_text(
                reply_token,
                "📋 您目前沒有任何報班記錄。\n\n請使用「查看工作列表」來尋找並報班工作。"
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
            app_text = f"📌{job_name_display}\n📍{location_display}\n📅{job.date}\n⏰{app.shift}"
            
            # 如果還有空間，加入報班編號
            test_text = app_text + f"\n🆔{app_id_display}"
            if len(test_text) <= 60:
                app_text = test_text
                # 如果還有更多空間，加入報班時間
                test_text = app_text + f"\n📝{applied_date}"
                if len(test_text) <= 60:
                    app_text = test_text
            
            # 建立 Google Maps 導航 URL
            encoded_location = urllib.parse.quote(job.location)
            navigation_url = f"https://www.google.com/maps/dir/?api=1&destination={encoded_location}"
            
            # 檢查使用者是否已註冊
            is_registered = True
            if self.auth_service:
                is_registered = self.auth_service.is_line_user_registered(user_id)
            
            # 建立按鈕動作
            actions = [
                {
                    "type": "postback",
                    "label": "查看詳情",
                    "data": f"action=job&step=detail&job_id={job.id}"
                }
            ]
            
            if is_registered:
                actions.extend([
                    {
                        "type": "postback",
                        "label": "取消報班",
                        "data": f"action=job&step=cancel&job_id={job.id}"
                    },
                    {
                        "type": "uri",
                        "label": "導航",
                        "uri": navigation_url
                    }
                ])
            else:
                actions.append({
                    "type": "postback",
                    "label": "📝 註冊",
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
                            "label": "返回主選單",
                            "data": "action=job&step=menu"
                        },
                        {
                            "type": "postback",
                            "label": "查看工作列表",
                            "data": "action=job&step=list"
                        }
                    ]
                }
            })
        
        self.message_service.send_multiple_messages(reply_token, messages)
    
    def handle_register(self, reply_token: str, user_id: str) -> None:
        """處理 LINE 使用者註冊 - 開始註冊流程"""
        if not self.auth_service:
            self.message_service.send_text(reply_token, "❌ 註冊功能暫時無法使用。")
            return
        
        # 檢查是否已註冊
        if self.auth_service.is_line_user_registered(user_id):
            user = self.auth_service.get_user_by_line_id(user_id)
            if user:
                user_info = f"""✅ 您已經註冊過了！

📋 您的帳號資訊：
• 姓名：{user.full_name or '未填寫'}
• 手機：{user.phone or '未填寫'}
• 地址：{user.address or '未填寫'}
• Email：{user.email or '未填寫'}
• 註冊時間：{user.created_at}"""
                self.message_service.send_text(reply_token, user_info)
            return
        
        # 開始註冊流程 - 第一步：輸入姓名
        self.registration_states[user_id] = {
            'step': 'name',
            'data': {}
        }
        
        self.message_service.send_text(
            reply_token,
            "📝 歡迎註冊！請依序填寫以下資料：\n\n第一步：請輸入您的姓名"
        )
    
    def handle_register_input(self, reply_token: str, user_id: str, text: str) -> None:
        """處理註冊資料輸入"""
        if not self.auth_service:
            return
        
        # 檢查是否在註冊流程中
        if user_id not in self.registration_states:
            return
        
        # 檢查是否要取消註冊
        if text.strip().lower() in ['取消', 'cancel', '取消註冊']:
            del self.registration_states[user_id]
            self.message_service.send_text(
                reply_token,
                "❌ 已取消註冊流程。\n\n如需註冊，請重新發送「註冊」。"
            )
            return
        
        state = self.registration_states[user_id]
        step = state['step']
        data = state['data']
        
        if step == 'name':
            # 儲存姓名，進入下一步
            name = text.strip()
            if not name:
                self.message_service.send_text(
                    reply_token,
                    "❌ 姓名不能為空，請重新輸入。"
                )
                return
            data['full_name'] = name
            state['step'] = 'phone'
            self.message_service.send_text(
                reply_token,
                f"✅ 姓名已記錄：{data['full_name']}\n\n第二步：請輸入您的手機號碼\n（格式：09XX-XXX-XXX 或 09XXXXXXXX）"
            )
        
        elif step == 'phone':
            # 驗證並儲存手機號碼
            phone = text.strip().replace('-', '').replace(' ', '')
            # 簡單驗證：台灣手機號碼格式
            if not phone.isdigit() or len(phone) != 10 or not phone.startswith('09'):
                self.message_service.send_text(
                    reply_token,
                    "❌ 手機號碼格式不正確，請輸入10位數手機號碼（例如：0912345678）"
                )
                return
            
            data['phone'] = phone
            state['step'] = 'address'
            self.message_service.send_text(
                reply_token,
                f"✅ 手機號碼已記錄：{data['phone']}\n\n第三步：請輸入您的地址"
            )
        
        elif step == 'address':
            # 儲存地址，進入下一步
            address = text.strip()
            if not address:
                self.message_service.send_text(
                    reply_token,
                    "❌ 地址不能為空，請重新輸入。"
                )
                return
            data['address'] = address
            state['step'] = 'email'
            self.message_service.send_text(
                reply_token,
                f"✅ 地址已記錄：{data['address']}\n\n第四步：請輸入您的 Email\n（可選，直接輸入「跳過」即可）"
            )
        
        elif step == 'email':
            # 處理 Email（可選）
            email = text.strip()
            if email.lower() in ['跳過', 'skip', '略過', '']:
                data['email'] = None
            else:
                # 簡單的 Email 驗證
                if '@' not in email or '.' not in email.split('@')[-1]:
                    self.message_service.send_text(
                        reply_token,
                        "❌ Email 格式不正確，請重新輸入或輸入「跳過」"
                    )
                    return
                data['email'] = email
            
            # 完成註冊
            try:
                # 取得並驗證必填欄位
                full_name = data.get('full_name', '').strip()
                phone = data.get('phone', '').strip()
                address = data.get('address', '').strip()
                email = data.get('email')  # email 可能是 None（可選）
                if email:
                    email = email.strip() if email else None
                
                # 驗證必填欄位
                if not full_name:
                    self.message_service.send_text(
                        reply_token,
                        "❌ 姓名為必填欄位，請重新開始註冊流程。"
                    )
                    if user_id in self.registration_states:
                        del self.registration_states[user_id]
                    return
                
                if not phone:
                    self.message_service.send_text(
                        reply_token,
                        "❌ 手機號碼為必填欄位，請重新開始註冊流程。"
                    )
                    if user_id in self.registration_states:
                        del self.registration_states[user_id]
                    return
                
                if not address:
                    self.message_service.send_text(
                        reply_token,
                        "❌ 地址為必填欄位，請重新開始註冊流程。"
                    )
                    if user_id in self.registration_states:
                        del self.registration_states[user_id]
                    return
                
                # 建立使用者（確保所有欄位都有值）
                user = self.auth_service.create_line_user(
                    line_user_id=user_id,
                    full_name=full_name,
                    phone=phone,
                    address=address,
                    email=email
                )
                
                # 清除註冊狀態
                del self.registration_states[user_id]
                
                success_message = f"""✅ 註冊成功！

📋 您的註冊資訊：
• 姓名：{user.full_name}
• 手機：{user.phone}
• 地址：{user.address}
• Email：{user.email or '未填寫'}
• 註冊時間：{user.created_at}

現在您可以開始報班工作了！"""
                
                # 使用 send_multiple_messages 在同一個回覆中發送成功訊息和主選單
                # 先準備主選單的內容（與 show_main_menu 一致）
                is_registered = True  # 剛註冊完成，一定是已註冊狀態
                actions = []
                
                actions.extend([
                    {
                        "type": "postback",
                        "label": "查看工作列表",
                        "data": "action=job&step=list"
                    },
                    {
                        "type": "postback",
                        "label": "查詢已報班",
                        "data": "action=job&step=my_applications"
                    }
                ])
                
                # 已註冊使用者：顯示查看註冊資料選項
                if is_registered:
                    actions.append({
                        "type": "postback",
                        "label": "👤 查看註冊資料",
                        "data": "action=view_profile&step=view"
                    })
                
                actions.append({
                    "type": "message",
                    "label": "聯絡客服",
                    "text": "我需要客服協助"
                })
                
                menu_text = "請選擇您需要的服務："
                
                messages = [
                    {
                        "type": "text",
                        "text": success_message
                    },
                    {
                        "type": "template",
                        "altText": "主選單",
                        "template": {
                            "type": "buttons",
                            "title": "Good Jobs 報班系統",
                            "text": menu_text,
                            "actions": actions
                        }
                    }
                ]
                
                self.message_service.send_multiple_messages(reply_token, messages)
            except Exception as e:
                print(f"❌ 註冊失敗：{e}")
                import traceback
                traceback.print_exc()
                # 清除註冊狀態
                if user_id in self.registration_states:
                    del self.registration_states[user_id]
                self.message_service.send_text(
                    reply_token,
                    f"❌ 註冊失敗：{str(e)}\n\n請稍後再試或聯絡客服。"
                )
    
    def handle_edit_profile(self, reply_token: str, user_id: str) -> None:
        """處理修改註冊資料 - 選擇要修改的欄位"""
        if not self.auth_service:
            self.message_service.send_text(reply_token, "❌ 修改註冊資料功能暫時無法使用。")
            return
        
        # 檢查是否已註冊
        if not self.auth_service.is_line_user_registered(user_id):
            self.message_service.send_text(
                reply_token,
                "❌ 您尚未註冊，無法修改註冊資料。\n\n請先使用「註冊」功能完成註冊。"
            )
            return
        
        # 取得當前使用者資料
        user = self.auth_service.get_user_by_line_id(user_id)
        if not user:
            self.message_service.send_text(reply_token, "❌ 找不到您的帳號資訊。")
            return
        
        # 顯示選擇要修改的欄位
        actions = [
            {
                "type": "postback",
                "label": "📱 手機號碼",
                "data": f"action=edit_profile&step=input&field=phone"
            },
            {
                "type": "postback",
                "label": "📍 地址",
                "data": f"action=edit_profile&step=input&field=address"
            },
            {
                "type": "postback",
                "label": "📧 Email",
                "data": f"action=edit_profile&step=input&field=email"
            },
            {
                "type": "postback",
                "label": "返回",
                "data": "action=view_profile&step=view"
            }
        ]
        
        # LINE 按鈕範本 text 欄位限制 60 字元，需要簡化顯示
        # 使用最簡潔的版本，只顯示關鍵提示
        current_info = "📋修改註冊資料\n\n請選擇要修改的欄位："
        
        try:
            response = self.message_service.send_buttons_template(
                reply_token,
                "修改註冊資料",
                current_info,
                actions
            )
            response.raise_for_status()  # 檢查 HTTP 狀態碼
        except requests.exceptions.RequestException as e:
            print(f"❌ 發送修改註冊資料選單失敗: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"   回應內容：{e.response.text}")
            # 嘗試發送文字訊息作為備用
            backup_message = f"""📋 您目前的資料：

• 姓名：{user.full_name or '未填寫'}（不可修改）
• 手機：{user.phone or '未填寫'}
• 地址：{user.address or '未填寫'}
• Email：{user.email or '未填寫'}

請點擊主選單中的「修改註冊資料」來修改資料。"""
            self.message_service.send_text(reply_token, backup_message)
    
    def handle_edit_profile_input(self, reply_token: str, user_id: str, text: str) -> None:
        """處理修改註冊資料輸入"""
        if not self.auth_service:
            return
        
        # 檢查是否在修改流程中
        if user_id not in self.edit_profile_states:
            return
        
        # 檢查是否要取消修改
        if text.strip().lower() in ['取消', 'cancel', '取消修改']:
            del self.edit_profile_states[user_id]
            self.message_service.send_text(
                reply_token,
                "❌ 已取消修改流程。"
            )
            return
        
        state = self.edit_profile_states[user_id]
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
                updated_user = self.auth_service.create_line_user(
                    line_user_id=user_id,
                    full_name=user.full_name,  # 保持原姓名
                    phone=phone,
                    address=user.address,  # 保持原地址
                    email=user.email  # 保持原 Email
                )
                
                # 清除修改狀態
                del self.edit_profile_states[user_id]
                
                # 發送成功訊息並返回查看註冊資料頁面
                success_message = f"✅ 手機號碼已更新為：{phone}"
                self._send_update_success_and_show_profile(reply_token, user_id, success_message)
            else:
                del self.edit_profile_states[user_id]
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
                updated_user = self.auth_service.create_line_user(
                    line_user_id=user_id,
                    full_name=user.full_name,  # 保持原姓名
                    phone=user.phone,  # 保持原手機
                    address=address,
                    email=user.email  # 保持原 Email
                )
                
                # 清除修改狀態
                del self.edit_profile_states[user_id]
                
                # 發送成功訊息並返回查看註冊資料頁面
                success_message = f"✅ 地址已更新為：{address}"
                self._send_update_success_and_show_profile(reply_token, user_id, success_message)
            else:
                del self.edit_profile_states[user_id]
                self.message_service.send_text(reply_token, "❌ 找不到您的帳號資訊。")
        
        elif field == 'email':
            # 更新 Email
            email = text.strip()
            if email.lower() in ['跳過', 'skip', '略過', '清除', '清空', '']:
                email = None
            else:
                # 簡單的 Email 驗證
                if '@' not in email or '.' not in email.split('@')[-1]:
                    self.message_service.send_text(
                        reply_token,
                        "❌ Email 格式不正確，請重新輸入或輸入「跳過」清除 Email。"
                    )
                    return
            
            # 更新資料
            user = self.auth_service.get_user_by_line_id(user_id)
            if user:
                updated_user = self.auth_service.create_line_user(
                    line_user_id=user_id,
                    full_name=user.full_name,  # 保持原姓名
                    phone=user.phone,  # 保持原手機
                    address=user.address,  # 保持原地址
                    email=email
                )
                
                # 清除修改狀態
                del self.edit_profile_states[user_id]
                
                # 發送成功訊息並返回查看註冊資料頁面
                if email:
                    success_message = f"✅ Email 已更新為：{email}"
                else:
                    success_message = "✅ Email 已清除。"
                self._send_update_success_and_show_profile(reply_token, user_id, success_message)
            else:
                del self.edit_profile_states[user_id]
                self.message_service.send_text(reply_token, "❌ 找不到您的帳號資訊。")
    
    def _send_update_success_and_show_profile(self, reply_token: str, user_id: str, success_message: str) -> None:
        """發送更新成功訊息並顯示註冊資料頁面"""
        # 取得更新後的使用者資料
        user = self.auth_service.get_user_by_line_id(user_id) if self.auth_service else None
        if not user:
            # 如果無法取得使用者資料，只發送成功訊息
            self.message_service.send_text(reply_token, success_message)
            return
        
        # 顯示更新後的註冊資料
        user_info = f"""📋 您的註冊資料：

• 姓名：{user.full_name or '未填寫'}
• 手機：{user.phone or '未填寫'}
• 地址：{user.address or '未填寫'}
• Email：{user.email or '未填寫'}
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
                "label": "🗑️ 取消註冊",
                "data": "action=delete_registration&step=confirm"
            },
            {
                "type": "postback",
                "label": "返回主選單",
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
                "altText": "註冊資料操作",
                "template": {
                    "type": "buttons",
                    "title": "註冊資料",
                    "text": "請選擇操作：",
                    "actions": actions
                }
            }
        ]
        
        try:
            self.message_service.send_multiple_messages(reply_token, messages)
        except Exception as e:
            print(f"❌ 發送更新成功訊息和註冊資料失敗: {e}")
            # 如果發送失敗，至少發送成功訊息
            self.message_service.send_text(reply_token, success_message)
    
    def handle_delete_registration(self, reply_token: str, user_id: str) -> None:
        """處理取消註冊 - 顯示確認訊息"""
        if not self.auth_service:
            self.message_service.send_text(reply_token, "❌ 取消註冊功能暫時無法使用。")
            return
        
        # 檢查是否已註冊
        if not self.auth_service.is_line_user_registered(user_id):
            self.message_service.send_text(
                reply_token,
                "❌ 您尚未註冊，無需取消。"
            )
            return
        
        # 取得使用者資料
        user = self.auth_service.get_user_by_line_id(user_id)
        if not user:
            self.message_service.send_text(reply_token, "❌ 找不到您的帳號資訊。")
            return
        
        # 顯示確認訊息（LINE 按鈕範本 text 限制 60 字元）
        # 使用簡潔版本
        confirm_text = "⚠️ 確認取消註冊\n\n取消後將無法報班工作，且無法復原。\n\n確定要取消嗎？"
        
        actions = [
            {
                "type": "postback",
                "label": "確認取消",
                "data": "action=delete_registration&step=confirm_delete"
            },
            {
                "type": "postback",
                "label": "返回",
                "data": "action=view_profile&step=view"
            }
        ]
        
        self.message_service.send_buttons_template(
            reply_token,
            "取消註冊",
            confirm_text,
            actions
        )
    
    def handle_confirm_delete_registration(self, reply_token: str, user_id: str) -> None:
        """處理確認取消註冊"""
        if not self.auth_service:
            self.message_service.send_text(reply_token, "❌ 取消註冊功能暫時無法使用。")
            return
        
        # 檢查是否已註冊
        if not self.auth_service.is_line_user_registered(user_id):
            self.message_service.send_text(
                reply_token,
                "❌ 您尚未註冊，無需取消。"
            )
            return
        
        # 取消使用者註冊
        success = self.auth_service.delete_line_user(user_id)
        
        if success:
            # 同時取消該使用者的所有報班記錄
            applications = self.application_service.get_user_applications(user_id)
            for app in applications:
                self.application_service.cancel_application(user_id, app.job_id)
            
            self.message_service.send_text(
                reply_token,
                "✅ 您的註冊已成功取消。\n\n如需重新使用服務，請重新註冊。"
            )
        else:
            self.message_service.send_text(
                reply_token,
                "❌ 取消註冊失敗，請稍後再試或聯絡客服。"
            )
    
    def show_user_profile(self, reply_token: str, user_id: str) -> None:
        """顯示使用者註冊資料"""
        if not self.auth_service:
            self.message_service.send_text(reply_token, "❌ 查看註冊資料功能暫時無法使用。")
            return
        
        # 檢查是否已註冊
        if not self.auth_service.is_line_user_registered(user_id):
            self.message_service.send_text(
                reply_token,
                "❌ 您尚未註冊，無法查看註冊資料。\n\n請先使用「註冊」功能完成註冊。"
            )
            return
        
        # 取得使用者資料
        user = self.auth_service.get_user_by_line_id(user_id)
        if not user:
            self.message_service.send_text(reply_token, "❌ 找不到您的帳號資訊。")
            return
        
        # 顯示註冊資料（使用文字訊息，因為內容較長）
        user_info = f"""📋 您的註冊資料：

• 姓名：{user.full_name or '未填寫'}
• 手機：{user.phone or '未填寫'}
• 地址：{user.address or '未填寫'}
• Email：{user.email or '未填寫'}
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
                "label": "🗑️ 取消註冊",
                "data": "action=delete_registration&step=confirm"
            },
            {
                "type": "postback",
                "label": "返回主選單",
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
                "altText": "註冊資料操作",
                "template": {
                    "type": "buttons",
                    "title": "註冊資料",
                    "text": "請選擇操作：",
                    "actions": actions
                }
            }
        ]
        
        try:
            self.message_service.send_multiple_messages(reply_token, messages)
        except Exception as e:
            print(f"❌ 發送註冊資料失敗: {e}")
            # 如果發送失敗，至少發送文字訊息
            self.message_service.send_text(reply_token, user_info)
    
    def show_main_menu(self, reply_token: str, user_id: Optional[str] = None) -> None:
        """顯示主選單"""
        # 檢查使用者是否已註冊
        is_registered = False
        if self.auth_service and user_id:
            is_registered = self.auth_service.is_line_user_registered(user_id)
        
        actions = []
        
        if not is_registered:
            # 未註冊使用者：顯示註冊選項
            actions.append({
                "type": "postback",
                "label": "📝 註冊",
                "data": "action=register&step=register"
            })
        
        actions.extend([
            {
                "type": "postback",
                "label": "查看工作列表",
                "data": "action=job&step=list"
            },
            {
                "type": "postback",
                "label": "查詢已報班",
                "data": "action=job&step=my_applications"
            }
        ])
        
        # 已註冊使用者：顯示查看註冊資料選項
        if is_registered:
            actions.append({
                "type": "postback",
                "label": "👤 查看註冊資料",
                "data": "action=view_profile&step=view"
            })
        
        actions.append({
            "type": "message",
            "label": "聯絡客服",
            "text": "我需要客服協助"
        })
        
        menu_text = "請選擇您需要的服務："
        if not is_registered:
            menu_text = "⚠️ 您尚未註冊，請先完成註冊才能報班工作。\n\n" + menu_text
        
        self.message_service.send_buttons_template(
            reply_token,
            "Good Jobs 報班系統",
            menu_text,
            actions
        )

