import paramiko
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
import time

from core.models import StepHistory, EventType

# 인스턴스 실행 관리(SSH 연결, 명령 실행)

class SSHInfo(BaseModel):
    host: str = Field(...)
    port: int = Field(22)
    username: str = Field(...)
    password: str = Field(...)

class SSHClient:
    def __init__(self, instance_id, ssh_info: SSHInfo):
        self.instance_id = instance_id
        self.ssh_info = ssh_info
        self.ssh_client = None
        self.shell_channel = None

    def get_history(self, json: bool = False):
        if json:
            import json as json_module
            history_data = []
            for entry in self.history:
                entry_dict = {
                    "event": entry.event.value,
                    "error": entry.error,
                    "timestamp": entry.timestamp.isoformat(),
                }
                if entry.command:
                    entry_dict["command"] = entry.command
                if entry.output:
                    entry_dict["output"] = entry.output
                history_data.append(entry_dict)
            return json_module.dumps(history_data, indent=2, ensure_ascii=False)
        else:
            return self.history
    
    def is_connected(self) -> bool:
        return self.ssh_client is not None

    def connect(self, event: EventType = EventType.CONNECT) -> bool:
        """EventType.CONNECT"""
        self.ssh_client = paramiko.SSHClient()
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            self.ssh_client.connect(
                hostname=self.ssh_info.host,
                port=self.ssh_info.port,
                username=self.ssh_info.username,
                password=self.ssh_info.password
            )
            self.create_shell() # 세션 생성
            return StepHistory(
                event=EventType.CONNECT,
                error="",
                timestamp=datetime.now(),
                output=f"Connected to Instance id:{self.instance_id}"
            )
        
        except paramiko.SSHException as e:
            self.ssh_client = None

            return StepHistory(
                event=event,
                error=f"SSH {event.value} failed: {e}",
                timestamp=datetime.now(),
                output=f"Failed to {event.value} Instance id:{self.instance_id}"
            )

    def interrupt_command(self):
        """EventType.INTERRUPT"""
        if self.shell_channel is not None:
            self.shell_channel.send('\x03')  # Ctrl+C
        
            return StepHistory(
                event=EventType.INTERRUPT,
                error="",
                timestamp=datetime.now(),
                output=f"Interrupted(Ctrl+C) command on Instance id:{self.instance_id}"
            )
        else:
            return StepHistory(
                event=EventType.INTERRUPT,
                error="No active shell to interrupt",
                timestamp=datetime.now(),
                output=f"No active shell to interrupt(Ctrl+C) on Instance id:{self.instance_id}"
            )

    def disconnect(self):
        """EventType.DISCONNECT"""
        if self.shell_channel is not None:
            self.close_shell()
        self.ssh_client.close()
        self.ssh_client = None

        return StepHistory(
            event=EventType.DISCONNECT,
            error="",
            timestamp=datetime.now(),
            output=f"Disconnected from Instance id:{self.instance_id}"
        )

    def reconnect(self, event: EventType = EventType.RECONNECT) -> StepHistory:
        """EventType.RECONNECT"""
        self.close()
        result = self.connect()
        return result
    
    def create_shell(self):
        """EventType.SHELL_CREATE"""
        if self.shell_channel is not None:
            return True
        
        try:
            self.shell_channel = self.ssh_client.invoke_shell()
            
            # 초기 로그인 메시지 대기 및 제거
            time.sleep(1)
            initial_output = ""
            while self.shell_channel.recv_ready():
                data = self.shell_channel.recv(1024).decode('utf-8')
                initial_output += data
                time.sleep(0.1)
            
            # 프롬프트가 준비될 때까지 대기
            time.sleep(0.5)
            
            return StepHistory(
                event=EventType.SHELL_CREATE,
                error="",
                timestamp=datetime.now(),
                output=f"Created shell for Instance id:{self.instance_id}"
            )
        
        except Exception as e:
            return StepHistory(
                event=EventType.SHELL_CREATE,
                error=f"Failed to create shell: {e}",
                timestamp=datetime.now(),
                output=f"Failed to create shell for Instance id:{self.instance_id}"
            )

    def send_command_to_shell(self, command: str, timeout: int = 30) -> tuple[str, str]:
        """
        EventType.SHELL_COMMAND
        
        returns:
        - output: 명령 실행 결과
        - error: 오류 메시지 (명령 실행 실패 시)
        """
        if self.shell_channel is None:
            if not self.create_shell():
                return "", "Shell not available"
        
        try:
            # 명령 전송
            self.shell_channel.send(command + '\n')
            
            # 응답 읽기
            output = ""
            start_time = time.time()
            last_line = ""
            sudo_password_sent = False
            
            while True:
                if self.shell_channel.recv_ready():
                    data = self.shell_channel.recv(1024).decode('utf-8')
                    output += data
                    
                    # 마지막 라인 확인
                    lines = output.split('\n')
                    if lines:
                        last_line = lines[-1]
                    
                    # sudo 비밀번호 프롬프트 감지
                    if not sudo_password_sent and ('[sudo]' in output or 'password' in output.lower() or 'Password:' in output):
                        # 비밀번호 입력
                        self.shell_channel.send(self.ssh_info.password + '\n')
                        sudo_password_sent = True
                        time.sleep(0.5)  # 비밀번호 처리 대기
                        continue
                    
                    # 프롬프트 감지 ($ 로 끝나는 라인)
                    if last_line.strip().endswith('$ ') or last_line.strip().endswith('$'):
                        # 명령 완료로 판단
                        break
                        
                elif time.time() - start_time > timeout:
                    # 타임아웃 발생 시 Ctrl+C 전송하여 명령 중단
                    self.shell_channel.send('\x03')
                    time.sleep(0.1)  # 중단 신호 처리 대기
                    error_msg = f"Command timed out after {timeout} seconds"
                    return output, error_msg
                elif self.shell_channel.exit_status_ready():
                    break
                else:
                    time.sleep(0.1)
            
            # 출력 정리
            lines = output.split('\n')
            clean_lines = []
            
            for i, line in enumerate(lines):
                # 첫 번째 라인이 명령 에코인 경우 스킵
                if i == 0 and line.strip() == command:
                    continue
                # 프롬프트 라인 스킵
                elif line.strip().endswith('$ ') or line.strip().endswith('$'):
                    continue
                # sudo 비밀번호 관련 라인 스킵
                elif '[sudo]' in line or 'password' in line.lower() or 'Password:' in line:
                    continue
                # 빈 라인이 아닌 경우 추가
                else:
                    clean_lines.append(line)
            
            clean_output = '\n'.join(clean_lines).strip()
            
            return clean_output, ""
            
        except Exception as e:
            error_msg = f"Shell command failed: {e}"
            return "", error_msg

    def close_shell(self):
        """EventType.SHELL_CLOSE"""
        if self.shell_channel is not None:
            self.shell_channel.close()
            self.shell_channel = None

            return StepHistory(
                event=EventType.SHELL_CLOSE,
                error="",
                timestamp=datetime.now(),
                output=f"Closed shell for Instance id:{self.instance_id}"
            )
        else:
            return StepHistory(
                event=EventType.SHELL_CLOSE,
                error="No shell to close",
                timestamp=datetime.now(),
                output=f"No shell to close for Instance id:{self.instance_id}"
            )
            

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

