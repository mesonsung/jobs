"""
兼職工作報名系統

使用 FastAPI 作為後台 API，LINE Bot 作為前台介面
包含：
1. JobService - 工作管理服務
2. ApplicationService - 報名管理服務
3. LineMessageService - LINE 訊息發送服務
4. JobHandler - 工作事件處理器
5. FastAPI 路由 - 後台管理 API
6. PartTimeJobBot - 主應用程式
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Tuple
import requests
from flask import Flask, request
import json
import datetime
import urllib.parse
import uvicorn
import threading
import socket
import os
import hmac
import hashlib
import base64

# ==================== 資料模型 ====================

class Job(BaseModel):
    """工作資料模型"""
    id: str
    name: str  # 臨時工作名稱
    location: str  # 工作地點
    date: str  # 工作日期，格式：YYYY-MM-DD
    shifts: List[str]  # 班別列表，例如 ["早班:08-19", "中班:14-23", "晚班:22-07"]
    location_image_url: Optional[str] = None  # 工作地點圖片 URL

class Application(BaseModel):
    """報名記錄模型"""
    id: str
    job_id: str
    user_id: str
    user_name: Optional[str] = None
    shift: str  # 選擇的班別
    applied_at: str  # 報名時間

class CreateJobRequest(BaseModel):
    """建立工作請求"""
    name: str = Field(..., description="臨時工作名稱")
    location: str = Field(..., description="工作地點")
    date: str = Field(..., description="工作日期，格式：YYYY-MM-DD")
    shifts: List[str] = Field(..., description="班別列表")
    location_image_url: Optional[str] = Field(None, description="工作地點圖片 URL")

# ==================== 模組 1: 工作服務 (JobService) ====================

class JobService:
    """工作管理服務"""
    
    def __init__(self):
        # 工作儲存（實際應用中應該使用資料庫）
        # 格式：{job_id: Job}
        self.jobs: Dict[str, Job] = {}
    
    def _get_next_job_id(self) -> str:
        """
        取得下一個工作編號
        
        返回:
            str: 工作編號（格式：JOB001, JOB002, ...）
        """
        # 找出現有工作中的最大流水號
        max_sequence = 0
        for job_id in self.jobs.keys():
            if job_id.startswith('JOB') and len(job_id) > 3:
                try:
                    # 提取流水號部分（JOB001 -> 001 -> 1）
                    sequence = int(job_id[3:])
                    max_sequence = max(max_sequence, sequence)
                except ValueError:
                    continue
        
        # 下一個流水號
        next_sequence = max_sequence + 1
        # 使用 3 位數流水號，不足補零
        return f"JOB{next_sequence:03d}"
    
    def create_job(self, job_data: CreateJobRequest) -> Job:
        """
        建立工作
        
        參數:
            job_data: 工作資料
        
        返回:
            Job: 建立的工作物件
        """
        # 工作編號格式：JOB+流水號（例如：JOB001, JOB002）
        job_id = self._get_next_job_id()
        
        job = Job(
            id=job_id,
            name=job_data.name,
            location=job_data.location,
            date=job_data.date,
            shifts=job_data.shifts,
            location_image_url=job_data.location_image_url
        )
        
        self.jobs[job_id] = job
        return job
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """取得工作"""
        return self.jobs.get(job_id)
    
    def get_all_jobs(self) -> List[Job]:
        """取得所有工作"""
        return list(self.jobs.values())
    
    def get_available_jobs(self) -> List[Job]:
        """取得可報名的工作（日期大於等於今天）"""
        today = datetime.date.today()
        available_jobs = []
        
        for job in self.jobs.values():
            try:
                job_date = datetime.datetime.strptime(job.date, '%Y-%m-%d').date()
                if job_date >= today:
                    available_jobs.append(job)
            except ValueError:
                continue
        
        # 按日期排序
        available_jobs.sort(key=lambda x: x.date)
        return available_jobs

# ==================== 模組 2: 報名服務 (ApplicationService) ====================

class ApplicationService:
    """報名管理服務"""
    
    def __init__(self):
        # 報名記錄儲存（實際應用中應該使用資料庫）
        # 格式：{application_id: Application}
        self.applications: Dict[str, Application] = {}
        # 使用者報名索引：{user_id: [application_id, ...]}
        self.user_applications: Dict[str, List[str]] = {}
        # 工作報名索引：{job_id: [application_id, ...]}
        self.job_applications: Dict[str, List[str]] = {}
    
    def create_application(self, job_id: str, user_id: str, shift: str, user_name: Optional[str] = None) -> Application:
        """
        建立報名記錄
        
        參數:
            job_id: 工作ID
            user_id: 使用者ID
            shift: 選擇的班別
            user_name: 使用者名稱（可選）
        
        返回:
            Application: 報名記錄
        """
        # 報名編號格式：工作編號_日期_流水號
        # 例如：JOB001_20260110_001
        
        # 取得當前日期（YYYYMMDD格式）
        today = datetime.datetime.now().strftime('%Y%m%d')
        
        # 計算該工作在同一天的流水號
        # 找出該工作在同一天的所有報名記錄
        same_day_applications = []
        for app_id, app in self.applications.items():
            if app.job_id == job_id:
                # 檢查報名時間是否為同一天
                app_date = app.applied_at.split()[0].replace('-', '')  # 提取日期部分並移除連字號
                if app_date == today:
                    same_day_applications.append(app_id)
        
        # 流水號 = 當天報名數量 + 1（3位數，補零）
        sequence_number = len(same_day_applications) + 1
        sequence_str = f"{sequence_number:03d}"
        
        # 組合報名編號：工作編號_日期_流水號
        application_id = f"{job_id}_{today}_{sequence_str}"
        
        application = Application(
            id=application_id,
            job_id=job_id,
            user_id=user_id,
            user_name=user_name,
            shift=shift,
            applied_at=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        
        self.applications[application_id] = application
        
        # 更新索引
        if user_id not in self.user_applications:
            self.user_applications[user_id] = []
        self.user_applications[user_id].append(application_id)
        
        if job_id not in self.job_applications:
            self.job_applications[job_id] = []
        self.job_applications[job_id].append(application_id)
        
        return application
    
    def get_user_application_for_job(self, user_id: str, job_id: str) -> Optional[Application]:
        """取得使用者對特定工作的報名記錄"""
        user_app_ids = self.user_applications.get(user_id, [])
        for app_id in user_app_ids:
            app = self.applications.get(app_id)
            if app and app.job_id == job_id:
                return app
        return None
    
    def cancel_application(self, user_id: str, job_id: str) -> Tuple[bool, Optional[Application]]:
        """
        取消報名
        
        參數:
            user_id: 使用者ID
            job_id: 工作ID
        
        返回:
            tuple: (是否成功, 取消的報名記錄)
        """
        application = self.get_user_application_for_job(user_id, job_id)
        if not application:
            return False, None
        
        # 移除報名記錄
        app_id = application.id
        if app_id in self.applications:
            del self.applications[app_id]
        
        # 更新索引
        if user_id in self.user_applications:
            if app_id in self.user_applications[user_id]:
                self.user_applications[user_id].remove(app_id)
        
        if job_id in self.job_applications:
            if app_id in self.job_applications[job_id]:
                self.job_applications[job_id].remove(app_id)
        
        return True, application
    
    def get_job_applications(self, job_id: str) -> List[Application]:
        """取得工作的所有報名記錄"""
        app_ids = self.job_applications.get(job_id, [])
        applications = []
        for app_id in app_ids:
            app = self.applications.get(app_id)
            if app:
                applications.append(app)
        return applications
    
    def get_user_applications(self, user_id: str) -> List[Application]:
        """
        取得使用者的所有報名記錄
        
        參數:
            user_id: 使用者ID
        
        返回:
            list: 報名記錄列表
        """
        app_ids = self.user_applications.get(user_id, [])
        applications = []
        for app_id in app_ids:
            app = self.applications.get(app_id)
            if app:
                applications.append(app)
        # 按報名時間排序（最新的在前）
        applications.sort(key=lambda x: x.applied_at, reverse=True)
        return applications

# ==================== 模組 3: LINE 訊息服務 (LineMessageService) ====================

class LineMessageService:
    """LINE 訊息發送服務"""
    
    def __init__(self, channel_access_token: str):
        self.token = channel_access_token
        self.api_url = "https://api.line.me/v2/bot/message/reply"
    
    def _get_headers(self) -> Dict[str, str]:
        """取得 API 請求標頭"""
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}"
        }
    
    def send_text(self, reply_token: str, text: str) -> requests.Response:
        """發送文字訊息"""
        payload = {
            "replyToken": reply_token,
            "messages": [{
                "type": "text",
                "text": text
            }]
        }
        return requests.post(
            self.api_url,
            headers=self._get_headers(),
            json=payload,
            timeout=10
        )
    
    def send_flex_message(self, reply_token: str, alt_text: str, contents: Dict) -> requests.Response:
        """發送 Flex 訊息"""
        payload = {
            "replyToken": reply_token,
            "messages": [{
                "type": "flex",
                "altText": alt_text,
                "contents": contents
            }]
        }
        return requests.post(
            self.api_url,
            headers=self._get_headers(),
            json=payload,
            timeout=10
        )
    
    def send_multiple_messages(self, reply_token: str, messages: List[Dict]) -> requests.Response:
        """在同一個回覆中發送多個訊息"""
        payload = {
            "replyToken": reply_token,
            "messages": messages
        }
        try:
            response = requests.post(
                self.api_url,
                headers=self._get_headers(),
                json=payload
            )
            response.raise_for_status()  # 如果狀態碼不是 2xx，會拋出異常
            return response
        except requests.exceptions.RequestException as e:
            print(f"❌ LINE API 錯誤：{e}")
            if hasattr(e.response, 'text'):
                print(f"   回應內容：{e.response.text}")
            raise
    
    def send_buttons_template(self, reply_token: str, title: str, text: str, actions: List[Dict]) -> requests.Response:
        """發送按鈕範本訊息"""
        buttons_template = {
            "type": "template",
            "altText": title,
            "template": {
                "type": "buttons",
                "title": title,
                "text": text,
                "actions": actions
            }
        }
        
        payload = {
            "replyToken": reply_token,
            "messages": [buttons_template]
        }
        
        return requests.post(
            self.api_url,
            headers=self._get_headers(),
            json=payload,
            timeout=10
        )

# ==================== 模組 4: 工作處理器 (JobHandler) ====================

class JobHandler:
    """工作事件處理器"""
    
    def __init__(self, job_service: JobService, application_service: ApplicationService, message_service: LineMessageService):
        self.job_service = job_service
        self.application_service = application_service
        self.message_service = message_service
    
    def show_available_jobs(self, reply_token: str, user_id: Optional[str] = None) -> None:
        """顯示可報名的工作列表"""
        jobs = self.job_service.get_available_jobs()
        
        print(f"📋 查詢可報名工作：找到 {len(jobs)} 個工作")
        
        if not jobs:
            self.message_service.send_text(
                reply_token,
                "目前沒有可報名的工作。\n\n請稍後再試，或聯絡管理員。\n\n💡 提示：管理員可以透過 API 發佈新工作。"
            )
            return
        
        # 建立工作列表訊息
        messages = []
        messages.append({
            "type": "text",
            "text": f"📋 可報名的工作（共 {len(jobs)} 個）："
        })
        
        # 每個工作建立一個 Flex 訊息或按鈕訊息
        for job in jobs:
            # 檢查使用者是否已報名
            is_applied = False
            applied_shift = None
            if user_id:
                application = self.application_service.get_user_application_for_job(user_id, job.id)
                if application:
                    is_applied = True
                    applied_shift = application.shift
            
            # 建立狀態標示
            status_icon = "✅ 已報名" if is_applied else "⭕ 未報名"
            status_text = f"\n{status_icon}"
            if is_applied and applied_shift:
                status_text += f" ({applied_shift})"
            
            # 建立 Google Maps 導航 URL
            encoded_location = urllib.parse.quote(job.location)
            navigation_url = f"https://www.google.com/maps/dir/?api=1&destination={encoded_location}"
            
            # 建立按鈕動作
            actions = [
                {
                    "type": "postback",
                    "label": "查看詳情",
                    "data": f"action=job&step=detail&job_id={job.id}"
                }
            ]
            
            # 根據報名狀態加入不同按鈕
            if is_applied:
                # 已報名：加入取消報名按鈕
                actions.append({
                    "type": "postback",
                    "label": "取消報名",
                    "data": f"action=job&step=cancel&job_id={job.id}"
                })
            else:
                # 未報名：加入報名按鈕
                actions.append({
                    "type": "postback",
                    "label": "報名",
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
                status_display = "\n✅已報名"
                if applied_shift and len(applied_shift) <= 10:
                    status_display += f"({applied_shift[:8]})"
            else:
                status_display = "\n⭕未報名"
            
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
        
        # 檢查使用者是否已報名
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
        
        if is_applied:
            job_detail += f"\n✅ 您已報名：{application.shift}"
        
        # 建立 Google Maps 導航 URL
        encoded_location = urllib.parse.quote(job.location)
        navigation_url = f"https://www.google.com/maps/dir/?api=1&destination={encoded_location}"
        
        # 建立按鈕
        actions = []
        if is_applied:
            actions.append({
                "type": "postback",
                "label": "取消報名",
                "data": f"action=job&step=cancel&job_id={job_id}"
            })
        else:
            actions.append({
                "type": "postback",
                "label": "報名",
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
        """處理報名工作流程 - 顯示班別選擇"""
        job = self.job_service.get_job(job_id)
        if not job:
            self.message_service.send_text(reply_token, "❌ 找不到指定的工作。")
            return
        
        # 檢查是否已報名
        existing_app = self.application_service.get_user_application_for_job(user_id, job_id)
        if existing_app:
            self.message_service.send_text(
                reply_token,
                f"❌ 您已經報名了這個工作（班別：{existing_app.shift}）\n\n如需取消，請先取消現有報名。"
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
                "text": f"請選擇要報名的班別：\n\n工作：{job.name}\n日期：{job.date}"
            },
            {
                "type": "template",
                "altText": "選擇班別",
                "template": {
                    "type": "buttons",
                    "title": "選擇班別",
                    "text": "請選擇您要報名的班別：",
                    "actions": shift_actions
                }
            }
        ]
        
        self.message_service.send_multiple_messages(reply_token, messages)
    
    def handle_select_shift(self, reply_token: str, user_id: str, job_id: str, shift: str) -> None:
        """處理選擇班別並完成報名"""
        job = self.job_service.get_job(job_id)
        if not job:
            self.message_service.send_text(reply_token, "❌ 找不到指定的工作。")
            return
        
        # 檢查班別是否有效
        if shift not in job.shifts:
            self.message_service.send_text(reply_token, "❌ 無效的班別選擇。")
            return
        
        # 檢查是否已報名
        existing_app = self.application_service.get_user_application_for_job(user_id, job_id)
        if existing_app:
            self.message_service.send_text(
                reply_token,
                f"❌ 您已經報名了這個工作（班別：{existing_app.shift}）"
            )
            return
        
        # 建立報名記錄
        application = self.application_service.create_application(job_id, user_id, shift)
        
        # 發送報名成功訊息
        success_message = f"""✅ 報名成功！

📋 報名資訊：
• 工作名稱：{job.name}
• 工作地點：{job.location}
• 工作日期：{job.date}
• 報名班別：{shift}
• 報名時間：{application.applied_at}
• 報名編號：{application.id}

感謝您的報名，我們會盡快與您聯繫！"""
        
        self.message_service.send_text(reply_token, success_message)
    
    def handle_cancel_application(self, reply_token: str, user_id: str, job_id: str) -> None:
        """處理取消報名流程 - 顯示報名資訊和確認按鈕"""
        job = self.job_service.get_job(job_id)
        if not job:
            self.message_service.send_text(reply_token, "❌ 找不到指定的工作。")
            return
        
        application = self.application_service.get_user_application_for_job(user_id, job_id)
        if not application:
            self.message_service.send_text(reply_token, "❌ 您尚未報名這個工作。")
            return
        
        # 顯示報名資訊和確認按鈕
        cancel_text = f"""請確認要取消的報名：

📋 報名資訊：
• 工作名稱：{job.name}
• 工作地點：{job.location}
• 工作日期：{job.date}
• 報名班別：{application.shift}
• 報名時間：{application.applied_at}
• 報名編號：{application.id}"""
        
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
                "altText": "確認取消報名",
                "template": {
                    "type": "buttons",
                    "title": "確認取消報名",
                    "text": "確定要取消這個報名嗎？",
                    "actions": actions
                }
            }
        ]
        
        self.message_service.send_multiple_messages(reply_token, messages)
    
    def handle_confirm_cancel(self, reply_token: str, user_id: str, job_id: str) -> None:
        """處理確認取消報名"""
        job = self.job_service.get_job(job_id)
        if not job:
            self.message_service.send_text(reply_token, "❌ 找不到指定的工作。")
            return
        
        success, canceled_app = self.application_service.cancel_application(user_id, job_id)
        
        if success and canceled_app:
            cancel_message = f"""✅ 報名已成功取消！

📋 已取消的報名資訊：
• 工作名稱：{job.name}
• 工作地點：{job.location}
• 工作日期：{job.date}
• 原報名班別：{canceled_app.shift}
• 報名編號：{canceled_app.id}

如有任何問題，歡迎隨時聯絡我們。"""
            self.message_service.send_text(reply_token, cancel_message)
        else:
            self.message_service.send_text(reply_token, "❌ 取消報名失敗，請稍後再試。")
    
    def show_user_applications(self, reply_token: str, user_id: str) -> None:
        """顯示使用者已報名的工作列表"""
        applications = self.application_service.get_user_applications(user_id)
        
        if not applications:
            self.message_service.send_text(
                reply_token,
                "📋 您目前沒有任何報名記錄。\n\n請使用「查看工作列表」來尋找並報名工作。"
            )
            return
        
        # 建立報名列表訊息
        messages = []
        messages.append({
            "type": "text",
            "text": f"📋 您的報名記錄（共 {len(applications)} 筆）："
        })
        
        # 每個報名建立一個訊息卡片
        for i, app in enumerate(applications, 1):
            job = self.job_service.get_job(app.job_id)
            
            if not job:
                # 如果工作不存在，只顯示報名資訊
                app_text = f"{i}. 報名編號：{app.id}\n   班別：{app.shift}\n   報名時間：{app.applied_at}\n   ⚠️ 工作已不存在"
                messages.append({
                    "type": "text",
                    "text": app_text
                })
                continue
            
            # 建立報名資訊文字（確保不超過 60 字元）
            # 簡化工作名稱和地點
            job_name_display = job.name[:15] if len(job.name) > 15 else job.name
            location_display = job.location[:12] if len(job.location) > 12 else job.location
            if len(job.location) > 12:
                location_display += "..."
            
            # 簡化報名編號（顯示日期+流水號，例如：20260110_001）
            # 報名編號格式：工作編號_日期_流水號
            # 提取最後部分（日期_流水號）
            if '_' in app.id:
                parts = app.id.split('_')
                if len(parts) >= 2:
                    # 取最後兩部分：日期和流水號
                    app_id_display = f"{parts[-2]}_{parts[-1]}"
                else:
                    app_id_display = app.id[-12:] if len(app.id) > 12 else app.id
            else:
                app_id_display = app.id[-12:] if len(app.id) > 12 else app.id
            
            # 簡化報名時間（只顯示日期）
            applied_date = app.applied_at.split()[0] if " " in app.applied_at else app.applied_at
            
            # 建立文字，逐步檢查長度
            app_text = f"📌{job_name_display}\n📍{location_display}\n📅{job.date}\n⏰{app.shift}"
            
            # 如果還有空間，加入報名編號
            test_text = app_text + f"\n🆔{app_id_display}"
            if len(test_text) <= 60:
                app_text = test_text
                # 如果還有更多空間，加入報名時間
                test_text = app_text + f"\n📝{applied_date}"
                if len(test_text) <= 60:
                    app_text = test_text
            
            # 建立 Google Maps 導航 URL
            encoded_location = urllib.parse.quote(job.location)
            navigation_url = f"https://www.google.com/maps/dir/?api=1&destination={encoded_location}"
            
            # 建立按鈕動作
            actions = [
                {
                    "type": "postback",
                    "label": "查看詳情",
                    "data": f"action=job&step=detail&job_id={job.id}"
                },
                {
                    "type": "postback",
                    "label": "取消報名",
                    "data": f"action=job&step=cancel&job_id={job.id}"
                },
                {
                    "type": "uri",
                    "label": "導航",
                    "uri": navigation_url
                }
            ]
            
            # 建立按鈕範本
            template = {
                "type": "buttons",
                "title": f"報名#{i}",
                "text": app_text,
                "actions": actions
            }
            
            # 如果有圖片，加入縮圖
            if job.location_image_url:
                template["thumbnailImageUrl"] = job.location_image_url
            
            messages.append({
                "type": "template",
                "altText": f"報名記錄 #{i} - {job.name}",
                "template": template
            })
        
        # 如果報名記錄很多，加入返回按鈕
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
    
    def show_main_menu(self, reply_token: str) -> None:
        """顯示主選單"""
        actions = [
            {
                "type": "postback",
                "label": "查看工作列表",
                "data": "action=job&step=list"
            },
            {
                "type": "postback",
                "label": "查詢已報名",
                "data": "action=job&step=my_applications"
            },
            {
                "type": "message",
                "label": "聯絡客服",
                "text": "我需要客服協助"
            }
        ]
        
        self.message_service.send_buttons_template(
            reply_token,
            "兼職工作報名系統",
            "請選擇您需要的服務：",
            actions
        )

# ==================== 模組 5: FastAPI 後台 API ====================

# 建立 FastAPI 應用程式
api_app = FastAPI(title="兼職工作報名系統 API", version="1.0.0")

# 全域服務實例（實際應用中應該使用依賴注入）
job_service = JobService()
application_service = ApplicationService()

@api_app.post("/api/jobs", response_model=Job)
def create_job(job_data: CreateJobRequest):
    """建立新工作"""
    try:
        job = job_service.create_job(job_data)
        return job
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@api_app.get("/api/jobs", response_model=List[Job])
def get_all_jobs():
    """取得所有工作"""
    return job_service.get_all_jobs()

@api_app.get("/api/jobs/{job_id}", response_model=Job)
def get_job(job_id: str):
    """取得特定工作"""
    job = job_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="工作不存在")
    return job

@api_app.get("/api/jobs/{job_id}/applications", response_model=List[Application])
def get_job_applications(job_id: str):
    """取得工作的報名清單"""
    job = job_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="工作不存在")
    
    applications = application_service.get_job_applications(job_id)
    return applications

@api_app.get("/api/applications", response_model=List[Application])
def get_all_applications():
    """取得所有報名記錄"""
    return list(application_service.applications.values())

# ==================== 模組 6: LINE Bot 主應用程式 ====================

class PartTimeJobBot:
    """兼職工作報名系統主應用程式"""
    
    def __init__(self, channel_access_token: str, channel_secret: Optional[str] = None):
        # 初始化服務
        self.job_service = job_service
        self.application_service = application_service
        self.message_service = LineMessageService(channel_access_token)
        self.handler = JobHandler(self.job_service, self.application_service, self.message_service)
        self.channel_secret = channel_secret
        
        # 建立 Flask 應用程式（用於 LINE Webhook）
        self.flask_app = Flask(__name__)
        self._setup_routes()
    
    def _setup_routes(self):
        """設定路由"""
        @self.flask_app.route("/", methods=['POST'])
        def webhook():
            return self.handle_webhook()
    
    def _verify_signature(self, body: bytes, signature: str) -> bool:
        """
        驗證 LINE Webhook 請求簽名
        
        參數:
            body: 請求原始 body（bytes）
            signature: X-Line-Signature header 的值
        
        返回:
            bool: 驗證是否通過
        """
        if not self.channel_secret:
            # 如果沒有設定 channel_secret，跳過驗證（開發模式）
            print("⚠️  警告：未設定 Channel Secret，跳過簽名驗證")
            return True
        
        try:
            # 使用 Channel Secret 和請求體計算 HMAC-SHA256
            hash_value = hmac.new(
                self.channel_secret.encode('utf-8'),
                body,
                hashlib.sha256
            ).digest()
            
            # 轉換為 base64
            expected_signature = base64.b64encode(hash_value).decode('utf-8')
            
            # 比較簽名（使用安全比較避免時間攻擊）
            return hmac.compare_digest(expected_signature, signature)
        except Exception as e:
            print(f"❌ 簽名驗證錯誤：{e}")
            return False
    
    def handle_webhook(self):
        """處理 LINE Webhook"""
        try:
            # 驗證請求簽名
            signature = request.headers.get('X-Line-Signature', '')
            body = request.get_data()
            
            if not self._verify_signature(body, signature):
                print(f"❌ Webhook 簽名驗證失敗")
                print(f"   收到的簽名：{signature[:20]}...")
                return 'Forbidden', 403
            
            # 解析 JSON 資料
            data = request.get_json()
            
            # 印出接收到的資料（方便除錯）
            print(json.dumps(data, indent=2, ensure_ascii=False))
            
            # 處理不同類型的事件
            for event in data.get('events', []):
                try:
                    event_type = event.get('type')
                    reply_token = event.get('replyToken')
                    user_id = event['source'].get('userId', 'unknown')
                    
                    if event_type == 'message':
                        self._handle_message(event, reply_token, user_id)
                    elif event_type == 'postback':
                        self._handle_postback(event, reply_token, user_id)
                except Exception as e:
                    print(f"❌ 處理事件時發生錯誤：{e}")
                    import traceback
                    traceback.print_exc()
                    # 嘗試發送錯誤訊息給使用者
                    try:
                        if reply_token:
                            self.message_service.send_text(
                                reply_token,
                                "❌ 處理您的請求時發生錯誤，請稍後再試。"
                            )
                    except:
                        pass
            
            return 'OK', 200
        except Exception as e:
            print(f"❌ Webhook 處理錯誤：{e}")
            import traceback
            traceback.print_exc()
            return 'OK', 200  # 即使出錯也返回 OK，避免 LINE 重試
    
    def _handle_message(self, event: Dict, reply_token: str, user_id: str) -> None:
        """處理文字訊息"""
        message_text = event['message'].get('text', '')
        
        if message_text in ['選單', 'menu', 'Menu', 'MENU', '工作', 'jobs']:
            self.handler.show_main_menu(reply_token)
        elif message_text in ['工作列表', '查看工作', 'list']:
            self.handler.show_available_jobs(reply_token, user_id)
        elif message_text in ['已報名', '我的報名', '報名記錄', 'my_applications']:
            self.handler.show_user_applications(reply_token, user_id)
        else:
            # 預設顯示主選單
            self.handler.show_main_menu(reply_token)
    
    def _handle_postback(self, event: Dict, reply_token: str, user_id: str) -> None:
        """處理 postback 事件"""
        postback_data = event['postback'].get('data', '')
        print(f"收到 postback: {postback_data}")
        
        # 解析 postback data
        parsed_data = urllib.parse.parse_qs(postback_data)
        action = parsed_data.get('action', [''])[0]
        step = parsed_data.get('step', [''])[0]
        job_id = parsed_data.get('job_id', [''])[0]
        shift = parsed_data.get('shift', [''])[0]
        
        # 解碼 shift（如果有）
        if shift:
            shift = urllib.parse.unquote(shift)
        
        # 根據不同的步驟處理
        if action == 'job':
            if step == 'list':
                self.handler.show_available_jobs(reply_token, user_id)
            elif step == 'detail':
                if job_id:
                    self.handler.show_job_detail(reply_token, user_id, job_id)
            elif step == 'apply':
                if job_id:
                    self.handler.handle_apply_job(reply_token, user_id, job_id)
            elif step == 'select_shift':
                if job_id and shift:
                    self.handler.handle_select_shift(reply_token, user_id, job_id, shift)
            elif step == 'cancel':
                if job_id:
                    self.handler.handle_cancel_application(reply_token, user_id, job_id)
            elif step == 'confirm_cancel':
                if job_id:
                    self.handler.handle_confirm_cancel(reply_token, user_id, job_id)
            elif step == 'my_applications':
                self.handler.show_user_applications(reply_token, user_id)
            elif step == 'menu':
                self.handler.show_main_menu(reply_token)
    
    def run(self, port: int = 3000, debug: bool = False, use_threading: bool = True):
        """
        啟動伺服器
        
        參數:
            port: 連接埠號
            debug: 是否啟用除錯模式
            use_threading: 是否使用執行緒在背景執行
        """
        if use_threading:
            import threading
            def run_server():
                self.flask_app.run(port=port, debug=debug, use_reloader=False, use_debugger=False)
            
            thread = threading.Thread(target=run_server, daemon=True)
            thread.start()
            print(f"✅ LINE Bot 伺服器已在背景啟動，監聽 port {port}")
            print("⚠️  注意：在 Jupyter 中，伺服器會在背景執行")
            print("   要停止伺服器，請重新啟動 kernel")
        else:
            self.flask_app.run(port=port, debug=debug)

# ==================== 測試資料建立 ====================

def create_sample_jobs(job_service: JobService):
    """建立測試工作資料"""
    from datetime import date, timedelta
    
    # 檢查是否已有工作
    if len(job_service.jobs) > 0:
        print("ℹ️  已有工作資料，跳過建立測試資料")
        return
    
    # 建立幾個測試工作
    sample_jobs = [
        {
            "name": "餐廳服務員",
            "location": "台北市信義區信義路五段7號",
            "date": (date.today() + timedelta(days=3)).strftime('%Y-%m-%d'),
            "shifts": ["早班:08-19", "中班:14-23", "晚班:22-07"],
            "location_image_url": None
        },
        {
            "name": "活動工作人員",
            "location": "新北市板橋區文化路一段188巷",
            "date": (date.today() + timedelta(days=5)).strftime('%Y-%m-%d'),
            "shifts": ["早班:09-18", "晚班:18-22"],
            "location_image_url": None
        },
        {
            "name": "展覽導覽員",
            "location": "台北市士林區至善路二段221號",
            "date": (date.today() + timedelta(days=7)).strftime('%Y-%m-%d'),
            "shifts": ["早班:10-18"],
            "location_image_url": None
        }
    ]
    
    for job_data in sample_jobs:
        job_request = CreateJobRequest(**job_data)
        job = job_service.create_job(job_request)
        print(f"✅ 已建立測試工作：{job.name} (ID: {job.id})")
    
    print(f"✅ 共建立 {len(sample_jobs)} 個測試工作")

# ==================== 主程式 ====================

CHANNEL_ACCESS_TOKEN = "oZPbAQXckPCTbRPN67GNPlyG/MqToO3haMOIvWOI35PGg8ZdBYEVtOc1KdJ+zYLJjOJ8+/YGaEk4f7m6W1RavpsYIp+5k1taVZ47HYboydFvMbTQ4rxXlNGysl2q0sM79gbzVuGnzHkPL2mf9SfU1gdB04t89/1O/w1cDnyilFU="
# Channel Secret 用於驗證 Webhook 請求來源（從 LINE Developers Console 取得）
# 如果未設定，系統會跳過簽名驗證（僅用於開發測試）
LINE_CHANNEL_SECRET = "793a80c83472d9ddf0451cad2dd4077c"
CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", LINE_CHANNEL_SECRET)

# 建立測試資料（在模組層級建立，每個進程都會執行，但有檢查機制避免重複）
create_sample_jobs(job_service)

# 建立 Bot 實例（在模組層級建立，每個進程都需要自己的實例）
bot = PartTimeJobBot(CHANNEL_ACCESS_TOKEN, channel_secret=CHANNEL_SECRET)

# 如果直接執行此檔案，啟動伺服器
if __name__ == "__main__":
    
    # 檢查 port 是否已被佔用
    def is_port_in_use(port: int, host: str = "0.0.0.0") -> bool:
        """檢查指定 port 是否已被使用"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((host, port))
                return False
            except OSError:
                return True
    
    # 檢查是否在主進程中（Flask reloader 會產生子進程）
    # WERKZEUG_RUN_MAIN 在 reloader 子進程中會被設為 'true'
    is_main_process = os.environ.get('WERKZEUG_RUN_MAIN') != 'true'
    
    # 啟動 FastAPI（後台 API）- 只在主進程且 port 未被佔用時啟動
    def run_fastapi():
        try:
            uvicorn.run(api_app, host="0.0.0.0", port=8880)
        except Exception as e:
            print(f"⚠️  FastAPI 啟動失敗：{e}")
    
    # 啟動 LINE Bot（前台）
    def run_line_bot():
        bot.run(port=3000, debug=True, use_threading=False)
    
    # 只在主進程且 port 未被佔用時啟動 FastAPI
    if is_main_process and not is_port_in_use(8880):
        fastapi_thread = threading.Thread(target=run_fastapi, daemon=True)
        fastapi_thread.start()
        print("✅ FastAPI 伺服器已啟動，監聽 http://0.0.0.0:8880")
        print("   API 文件：http://localhost:8880/docs")
    elif is_port_in_use(8880) and is_main_process:
        print("ℹ️  FastAPI 伺服器已在運行（port 8880 已被佔用）")
    
    # 在前景執行 LINE Bot
    print("✅ 啟動 LINE Bot 伺服器...")
    run_line_bot()
