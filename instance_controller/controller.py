from datetime import datetime
import time
import json
from enum import Enum
from pydantic import BaseModel, Field

from core.models import StepHistory, EventType
from instance.ssh import SSHInfo, SSHClient # SSH 클라이언트 모듈 임포트
from instance_controller.llm import LLM

class LLMController:
    def __init__(self, settings):
        # 세션 실행 시간 초기화
        self.start_time = datetime.now()
        # SSH 연결 초기화
        self.ssh_info = SSHInfo(
            host=settings.ssh_host,
            port=settings.ssh_port,
            username=settings.ssh_username,
            password=settings.ssh_password
        )
        self.instance = SSHClient(settings.experiment_id, self.ssh_info)
        self.instance.connect()
        self.llm = LLM(settings)
        self.history:list[StepHistory] = []
        
    def append_history(self, history_item: StepHistory):

        if len(history_item.output) > 1000:
            # 끝-300~끝 range 추가
            history_item.output = history_item.output[:1000] + "..."  + history_item.output[-300:]
        
        self.history.append(history_item)
        print(f"[{history_item.timestamp}] {history_item.event.value}")
        if history_item.command:
            print(f"  Command: {history_item.command}")
        if history_item.description:
            print(f"  Description: {history_item.description}")
        if history_item.error:
            print(f"  Error: {history_item.error}")
        if history_item.output:
            output_preview = history_item.output[:100] + "..." if len(history_item.output) > 100 else history_item.output
            print(f"  Output: {output_preview}")
        print("-" * 50)

    def next_step_from_llm(self):

        res = self.llm.generate_response(history=self.history)

        
        try:
            data = json.loads(res)

            event = data.get("event")
            description = data.get("description", "")
            error_msg = data.get("error", "")
            
            if event == 'shell_command':
                command = data.get('command', {}).get('content', '')
                timeout = data['command'].get("timeout", 30)
                output, error_msg = self.instance.send_command_to_shell(command, timeout)
                self.append_history(
                    StepHistory(
                        event=EventType.SHELL_COMMAND,
                        error=error_msg,
                        timestamp=datetime.now(),
                        description=description,
                        command=command,
                        output=output
                    )
                )

            elif event == 'connect':
                res = self.instance.connect()
                if isinstance(res, StepHistory):
                    res.description = description
                    self.append_history(res)
                else:
                    # bool 값이 반환된 경우
                    self.append_history(
                        StepHistory(
                            event=EventType.CONNECT,
                            error="" if res else "Failed to connect",
                            timestamp=datetime.now(),
                            description=description,
                            output="Connected successfully" if res else "Connection failed"
                        )
                    )

            elif event == 'disconnect':
                res = self.instance.disconnect()
                if isinstance(res, StepHistory):
                    res.description = description
                    self.append_history(res)
                else:
                    self.append_history(
                        StepHistory(
                            event=EventType.DISCONNECT,
                            error="" if res else "Failed to disconnect",
                            timestamp=datetime.now(),
                            description=description,
                            output="Disconnected successfully" if res else "Disconnection failed"
                        )
                    )

            elif event == 'reconnect':
                res = self.instance.reconnect()
                if isinstance(res, StepHistory):
                    res.description = description
                    self.append_history(res)
                else:
                    self.append_history(
                        StepHistory(
                            event=EventType.RECONNECT,
                            error="" if res else "Failed to reconnect",
                            timestamp=datetime.now(),
                            description=description,
                            output="Reconnected successfully" if res else "Reconnection failed"
                        )
                    )

            elif event == 'shell_create':
                res = self.instance.create_shell()
                if isinstance(res, StepHistory):
                    res.description = description
                    self.append_history(res)
                else:
                    # bool 값이 반환된 경우
                    self.append_history(
                        StepHistory(
                            event=EventType.SHELL_CREATE,
                            error="" if res else "Failed to create shell",
                            timestamp=datetime.now(),
                            description=description,
                            output="Shell created successfully" if res else "Failed to create shell"
                        )
                    )

            elif event == 'shell_close':
                res:StepHistory = self.instance.close_shell()
                res.description = description
                self.append_history(res)

            elif event == 'interrupt':
                res = self.instance.interrupt_command()
                res.description = description
                self.append_history(res)

            elif event == 'timeout_interrupt':
                res = self.instance.interrupt_command()
                res.event = EventType.TIMEOUT_INTERRUPT
                res.description = description
                res.output = "Timeout interrupt triggered by LLM"
                self.append_history(res)

        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error parsing LLM response: {e}")
            return "echo 'LLM response parsing failed'"

    def run_experiments(self, time_limit=2 * 60 * 60):
        """
        세션 실행 로직
        """
        try:
            print("세션 실행 시작...")
            while (datetime.now() - self.start_time).total_seconds() < time_limit:
                try:
                    self.next_step_from_llm()
                    elapsed_time = (datetime.now() - self.start_time).total_seconds()
                    print(f"{elapsed_time:.2f}초 경과")
                    time.sleep(1)
                except Exception as e:
                    print(f"Error in session loop: {e}")
                    time.sleep(5)
                    continue
        finally:
            self.instance.close_shell()

    def summarize_session(self):
        """
        세션 요약 출력
        """
        print("세션 요약:")
        for entry in self.history:
            print(f"{entry.timestamp} - {entry.event.value}: {entry.command} - {entry.description}")
        
        # LLM을 사용하여 전체 세션 요약
        summary = self.llm.summarize_history(self.history)        
        return summary
