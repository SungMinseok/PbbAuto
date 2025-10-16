"""
스케줄링 시스템 - PbbAuto 자동 실행 스케줄러
"""

# 로그 설정을 가장 먼저 import
import logger_setup

import os
import json
import time
import uuid
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from enum import Enum
from utils import start_keep_alive, stop_keep_alive, is_keep_alive_running


class ScheduleType(Enum):
    """스케줄 반복 유형"""
    ONCE = "once"           # 일회성
    DAILY = "daily"         # 매일
    WEEKLY = "weekly"       # 매주
    MONTHLY = "monthly"     # 매월
    INTERVAL = "interval"   # 간격 (N분/시간마다)


class ScheduleStatus(Enum):
    """스케줄 상태"""
    ENABLED = "enabled"
    DISABLED = "disabled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Schedule:
    """개별 스케줄 정보를 담는 클래스"""
    
    def __init__(self, name: str, commands: List[str], schedule_type: ScheduleType, 
                 schedule_time: str, **kwargs):
        self.id = str(uuid.uuid4())
        self.name = name
        self.commands = commands  # 실행할 명령어 리스트
        self.schedule_type = schedule_type
        self.schedule_time = schedule_time  # "HH:MM" 형식
        
        # 옵션 설정
        self.date = kwargs.get('date')  # ONCE 타입용 날짜 "YYYY-MM-DD"
        self.days_of_week = kwargs.get('days_of_week', [])  # WEEKLY용 요일 [0,1,2,3,4,5,6] (월-일)
        self.day_of_month = kwargs.get('day_of_month')  # MONTHLY용 날짜 (1-31)
        self.interval_minutes = kwargs.get('interval_minutes', 60)  # INTERVAL용 간격
        
        # 실행 옵션
        self.window_pattern = kwargs.get('window_pattern', '')
        self.retry_count = kwargs.get('retry_count', 1)
        self.retry_delay = kwargs.get('retry_delay', 60)
        self.notify_before = kwargs.get('notify_before', 0)  # 실행 N초 전 알림
        self.notify_after = kwargs.get('notify_after', False)
        
        # 상태 정보
        self.status = ScheduleStatus.ENABLED
        self.created_at = datetime.now()
        self.last_run = None
        self.next_run = None
        self.success_count = 0
        self.fail_count = 0
        
        # 다음 실행 시간 계산
        self.calculate_next_run()
    
    def calculate_next_run(self) -> Optional[datetime]:
        """다음 실행 시간 계산"""
        now = datetime.now()
        
        try:
            if self.schedule_type == ScheduleType.ONCE:
                # 일회성 - 지정된 날짜와 시간
                if self.date:
                    schedule_datetime = datetime.strptime(f"{self.date} {self.schedule_time}", 
                                                        "%Y-%m-%d %H:%M")
                    if schedule_datetime > now:
                        self.next_run = schedule_datetime
                        return self.next_run
                    else:
                        self.status = ScheduleStatus.COMPLETED
                        self.next_run = None
                        return None
                        
            elif self.schedule_type == ScheduleType.DAILY:
                # 매일 - 오늘 또는 내일의 지정 시간
                today = now.date()
                schedule_time = datetime.strptime(self.schedule_time, "%H:%M").time()
                schedule_datetime = datetime.combine(today, schedule_time)
                
                if schedule_datetime <= now:
                    # 오늘 시간이 지났으면 내일
                    schedule_datetime += timedelta(days=1)
                
                self.next_run = schedule_datetime
                return self.next_run
                
            elif self.schedule_type == ScheduleType.WEEKLY:
                # 매주 - 지정된 요일들의 지정 시간
                if not self.days_of_week:
                    return None
                
                today = now.date()
                schedule_time = datetime.strptime(self.schedule_time, "%H:%M").time()
                
                # 다음 실행 가능한 요일 찾기
                next_dates = []
                for day in self.days_of_week:
                    # 이번 주에서 해당 요일 찾기
                    days_ahead = day - today.weekday()
                    if days_ahead < 0:  # 이번 주는 지났음
                        days_ahead += 7
                    
                    target_date = today + timedelta(days=days_ahead)
                    target_datetime = datetime.combine(target_date, schedule_time)
                    
                    if target_datetime > now:
                        next_dates.append(target_datetime)
                    elif days_ahead == 0:  # 오늘인데 시간이 지났으면 다음 주
                        target_datetime += timedelta(days=7)
                        next_dates.append(target_datetime)
                
                if next_dates:
                    self.next_run = min(next_dates)
                    return self.next_run
                    
            elif self.schedule_type == ScheduleType.MONTHLY:
                # 매월 - 지정된 날짜의 지정 시간
                if not self.day_of_month:
                    return None
                
                schedule_time = datetime.strptime(self.schedule_time, "%H:%M").time()
                
                # 이번 달 시도
                try:
                    this_month = now.replace(day=self.day_of_month, 
                                           hour=schedule_time.hour, 
                                           minute=schedule_time.minute, 
                                           second=0, microsecond=0)
                    if this_month > now:
                        self.next_run = this_month
                        return self.next_run
                except ValueError:
                    pass  # 이번 달에 해당 날짜가 없음 (예: 2월 30일)
                
                # 다음 달 시도
                next_month = now.replace(day=1) + timedelta(days=32)
                next_month = next_month.replace(day=1)  # 다음 달 1일
                try:
                    next_month_schedule = next_month.replace(day=self.day_of_month,
                                                           hour=schedule_time.hour,
                                                           minute=schedule_time.minute,
                                                           second=0, microsecond=0)
                    self.next_run = next_month_schedule
                    return self.next_run
                except ValueError:
                    # 다음 달에도 해당 날짜가 없으면 더 다음 달로
                    return None
                    
            elif self.schedule_type == ScheduleType.INTERVAL:
                # 간격 실행 - 마지막 실행 시간 + 간격
                if self.last_run:
                    self.next_run = self.last_run + timedelta(minutes=self.interval_minutes)
                else:
                    # 첫 실행은 지금부터 간격 후
                    self.next_run = now + timedelta(minutes=self.interval_minutes)
                return self.next_run
                
        except Exception as e:
            print(f"다음 실행 시간 계산 오류 [{self.name}]: {e}")
            return None
        
        return None
    
    def should_run_now(self) -> bool:
        """현재 시간에 실행해야 하는지 확인"""
        if self.status != ScheduleStatus.ENABLED:
            return False
        
        if not self.next_run:
            return False
            
        now = datetime.now()
        # 1분 오차 허용 (스케줄러가 1분마다 체크하므로)
        return abs((now - self.next_run).total_seconds()) < 60
    
    def mark_executed(self, success: bool = True):
        """실행 완료 표시"""
        self.last_run = datetime.now()
        
        if success:
            self.success_count += 1
        else:
            self.fail_count += 1
        
        # 다음 실행 시간 재계산
        if self.schedule_type != ScheduleType.ONCE:
            self.calculate_next_run()
        else:
            self.status = ScheduleStatus.COMPLETED
    
    def to_dict(self) -> Dict:
        """딕셔너리로 변환 (저장용)"""
        return {
            'id': self.id,
            'name': self.name,
            'commands': self.commands,
            'schedule_type': self.schedule_type.value,
            'schedule_time': self.schedule_time,
            'date': self.date,
            'days_of_week': self.days_of_week,
            'day_of_month': self.day_of_month,
            'interval_minutes': self.interval_minutes,
            'window_pattern': self.window_pattern,
            'retry_count': self.retry_count,
            'retry_delay': self.retry_delay,
            'notify_before': self.notify_before,
            'notify_after': self.notify_after,
            'status': self.status.value,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_run': self.last_run.isoformat() if self.last_run else None,
            'next_run': self.next_run.isoformat() if self.next_run else None,
            'success_count': self.success_count,
            'fail_count': self.fail_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Schedule':
        """딕셔너리에서 복원 (로드용)"""
        schedule = cls(
            name=data['name'],
            commands=data['commands'],
            schedule_type=ScheduleType(data['schedule_type']),
            schedule_time=data['schedule_time'],
            date=data.get('date'),
            days_of_week=data.get('days_of_week', []),
            day_of_month=data.get('day_of_month'),
            interval_minutes=data.get('interval_minutes', 60),
            window_pattern=data.get('window_pattern', ''),
            retry_count=data.get('retry_count', 1),
            retry_delay=data.get('retry_delay', 60),
            notify_before=data.get('notify_before', 0),
            notify_after=data.get('notify_after', False)
        )
        
        # 저장된 상태 정보 복원
        schedule.id = data.get('id', schedule.id)
        schedule.status = ScheduleStatus(data.get('status', 'enabled'))
        
        if data.get('created_at'):
            schedule.created_at = datetime.fromisoformat(data['created_at'])
        if data.get('last_run'):
            schedule.last_run = datetime.fromisoformat(data['last_run'])
        if data.get('next_run'):
            schedule.next_run = datetime.fromisoformat(data['next_run'])
            
        schedule.success_count = data.get('success_count', 0)
        schedule.fail_count = data.get('fail_count', 0)
        
        return schedule


class ScheduleManager:
    """스케줄 저장/로드/관리 클래스"""
    
    def __init__(self, data_file: str = "schedules.json"):
        self.data_file = data_file
        self.schedules: Dict[str, Schedule] = {}
        self.load_schedules()
    
    def add_schedule(self, schedule: Schedule) -> bool:
        """스케줄 추가"""
        try:
            self.schedules[schedule.id] = schedule
            self.save_schedules()
            print(f"스케줄 추가됨: {schedule.name}")
            return True
        except Exception as e:
            print(f"스케줄 추가 실패: {e}")
            return False
    
    def remove_schedule(self, schedule_id: str) -> bool:
        """스케줄 제거"""
        try:
            if schedule_id in self.schedules:
                schedule_name = self.schedules[schedule_id].name
                del self.schedules[schedule_id]
                self.save_schedules()
                print(f"스케줄 제거됨: {schedule_name}")
                return True
            return False
        except Exception as e:
            print(f"스케줄 제거 실패: {e}")
            return False
    
    def update_schedule(self, schedule: Schedule) -> bool:
        """스케줄 업데이트"""
        try:
            if schedule.id in self.schedules:
                self.schedules[schedule.id] = schedule
                self.save_schedules()
                print(f"스케줄 업데이트됨: {schedule.name}")
                return True
            return False
        except Exception as e:
            print(f"스케줄 업데이트 실패: {e}")
            return False
    
    def get_schedule(self, schedule_id: str) -> Optional[Schedule]:
        """스케줄 조회"""
        return self.schedules.get(schedule_id)
    
    def get_all_schedules(self) -> List[Schedule]:
        """모든 스케줄 조회"""
        return list(self.schedules.values())
    
    def get_enabled_schedules(self) -> List[Schedule]:
        """활성화된 스케줄만 조회"""
        return [s for s in self.schedules.values() if s.status == ScheduleStatus.ENABLED]
    
    def save_schedules(self):
        """스케줄 저장"""
        try:
            data = {
                'schedules': [schedule.to_dict() for schedule in self.schedules.values()],
                'last_saved': datetime.now().isoformat()
            }
            
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"스케줄 저장 실패: {e}")
    
    def load_schedules(self):
        """스케줄 로드"""
        try:
            if not os.path.exists(self.data_file):
                print("스케줄 파일이 없습니다. 새로 생성됩니다.")
                return
            
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.schedules = {}
            for schedule_data in data.get('schedules', []):
                schedule = Schedule.from_dict(schedule_data)
                # 로드 시 다음 실행 시간 재계산
                schedule.calculate_next_run()
                self.schedules[schedule.id] = schedule
                
            print(f"스케줄 {len(self.schedules)}개 로드됨")
            
        except Exception as e:
            print(f"스케줄 로드 실패: {e}")
            self.schedules = {}


class SchedulerEngine:
    """백그라운드 스케줄 실행 엔진"""
    
    def __init__(self, schedule_manager: ScheduleManager, command_executor: Optional[Callable] = None):
        self.schedule_manager = schedule_manager
        self.command_executor = command_executor  # 명령어 실행 함수
        self.running = False
        self.thread = None
        self.check_interval = 60  # 1분마다 체크
        
    def set_command_executor(self, executor: Callable):
        """명령어 실행 함수 설정"""
        self.command_executor = executor
    
    def start(self):
        """스케줄러 시작"""
        if self.running:
            print("스케줄러가 이미 실행 중입니다.")
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.thread.start()
        
        # Keep-alive 자동 시작 (12분 간격 - 15분 잠금보다 짧게)
        if not is_keep_alive_running():
            start_keep_alive(interval_minutes=12)
            print("스케줄러 시작됨 (Keep-alive 포함)")
        else:
            print("스케줄러 시작됨")
    
    def stop(self):
        """스케줄러 중지"""
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
        
        # Keep-alive 중지
        if is_keep_alive_running():
            stop_keep_alive()
            print("스케줄러 중지됨 (Keep-alive 포함)")
        else:
            print("스케줄러 중지됨")
    
    def _run_scheduler(self):
        """스케줄러 메인 루프"""
        print("스케줄러 백그라운드 실행 시작")
        
        while self.running:
            try:
                self._check_and_execute_schedules()
                
                # check_interval 동안 대기 (중지 신호 체크하면서)
                for _ in range(self.check_interval):
                    if not self.running:
                        break
                    time.sleep(1)
                    
            except Exception as e:
                print(f"스케줄러 실행 중 오류: {e}")
                time.sleep(10)  # 오류 시 10초 대기 후 재시도
    
    def _check_and_execute_schedules(self):
        """스케줄 확인 및 실행"""
        enabled_schedules = self.schedule_manager.get_enabled_schedules()
        
        for schedule in enabled_schedules:
            if schedule.should_run_now():
                print(f"스케줄 실행: {schedule.name}")
                self._execute_schedule(schedule)
    
    def _execute_schedule(self, schedule: Schedule):
        """개별 스케줄 실행"""
        try:
            schedule.status = ScheduleStatus.RUNNING
            
            # 명령어 실행
            if self.command_executor and schedule.commands:
                success = True
                for command in schedule.commands:
                    try:
                        print(f"명령어 실행: {command}")
                        self.command_executor(command)
                    except Exception as e:
                        print(f"명령어 실행 실패 [{command}]: {e}")
                        success = False
                        break
                
                schedule.mark_executed(success)
                
                if success:
                    schedule.status = ScheduleStatus.ENABLED
                    print(f"✓ 스케줄 실행 성공: {schedule.name}")
                else:
                    schedule.status = ScheduleStatus.FAILED
                    print(f"❌ 스케줄 실행 실패: {schedule.name}")
                    
            else:
                print(f"⚠️ 명령어 실행기가 설정되지 않았거나 명령어가 없음: {schedule.name}")
                schedule.status = ScheduleStatus.FAILED
                
            # 변경사항 저장
            self.schedule_manager.save_schedules()
            
        except Exception as e:
            print(f"스케줄 실행 중 오류 [{schedule.name}]: {e}")
            schedule.status = ScheduleStatus.FAILED
            schedule.mark_executed(False)
