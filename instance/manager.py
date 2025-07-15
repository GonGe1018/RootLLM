import paramiko
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
import time

# 인스턴스 실행 관리(SSH 연결, 명령 실행)

class SSHEventType(str, Enum):
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    RECONNECT = "reconnect"
    SHELL_CREATE = "shell_create"
    SHELL_CLOSE = "shell_close"
    SHELL_COMMAND = "shell_command"
    INTERRUPT = "interrupt"
    TIMEOUT_INTERRUPT = "timeout_interrupt"

class SSHInfo(BaseModel):
    host: str = Field(...)
    port: int = Field(22)
    username: str = Field(...)
    password: str = Field(...)

class SSHCommandHistory(BaseModel):
    event: SSHEventType
    error: str
    timestamp: datetime

    # 명령 이벤트일 때만 아래 필드 사용
    command: str | None = None
    output: str | None = None

class InstanceManager:
    def __init__(self, instance_id, ssh_info: SSHInfo):
        self.instance_id = instance_id
        self.ssh_info = ssh_info
        self.ssh_client = None
        self.history:list[SSHCommandHistory] = []
        self.shell_channel = None

    def connect(self, event: SSHEventType = SSHEventType.CONNECT) -> bool:
        if self.ssh_client is not None:
            return True
        self.ssh_client = paramiko.SSHClient()
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            self.ssh_client.connect(
                hostname=self.ssh_info.host,
                port=self.ssh_info.port,
                username=self.ssh_info.username,
                password=self.ssh_info.password
            )
            self.history.append(
                SSHCommandHistory(
                    event=event,
                    error="",
                    timestamp=datetime.now()
                )
            )
            self.create_shell() # 세션 생성
            return True
        except paramiko.SSHException as e:
            self.history.append(
                SSHCommandHistory(
                    event=event,
                    error=f"SSH {event.value} failed: {e}",
                    timestamp=datetime.now()
                )
            )
            print(f"SSH {event.value} failed: {e}")
            self.ssh_client = None
            return False

    def interrupt_command(self):
        """shell 명령 중지(Ctrl+C)"""
        if self.shell_channel is not None:
            self.shell_channel.send('\x03')  # Ctrl+C
            self.history.append(
                SSHCommandHistory(
                    event=SSHEventType.INTERRUPT,
                    error="",
                    timestamp=datetime.now()
                )
            )
            return True
        return False

    def get_history(self):
        return self.history
    
    def is_connected(self) -> bool:
        return self.ssh_client is not None

    def close(self):
        if self.shell_channel is not None:
            self.close_shell()
        self.ssh_client.close()
        self.history.append(
            SSHCommandHistory(
                event=SSHEventType.DISCONNECT,
                error="",
                timestamp=datetime.now()
            )
        )

    def reconnect(self, event: SSHEventType = SSHEventType.RECONNECT) -> bool:
        self.close()
        result = self.connect()
        return result

    def create_shell(self):
        if self.shell_channel is not None:
            return True
        
        try:
            self.shell_channel = self.ssh_client.invoke_shell()
            self.history.append(
                SSHCommandHistory(
                    event=SSHEventType.SHELL_CREATE,
                    error="",
                    timestamp=datetime.now()
                )
            )
            return True
        except Exception as e:
            self.history.append(
                SSHCommandHistory(
                    event=SSHEventType.SHELL_CREATE,
                    error=f"Shell creation failed: {e}",
                    timestamp=datetime.now()
                )
            )
            return False

    def send_command_to_shell(self, command: str, timeout: int = 10) -> tuple[str, str]:
        if self.shell_channel is None:
            if not self.create_shell():
                return "", "Shell not available"
        
        try:
            # 명령 전송
            self.shell_channel.send(command + '\n')
            
            # 응답 읽기
            output = ""
            start_time = time.time()
            
            while True:
                if self.shell_channel.recv_ready():
                    data = self.shell_channel.recv(1024).decode('utf-8')
                    output += data
                elif time.time() - start_time > timeout:
                    # 타임아웃 발생 시 Ctrl+C 전송하여 명령 중단
                    self.shell_channel.send('\x03')
                    time.sleep(0.1)  # 중단 신호 처리 대기
                    error_msg = f"Command timed out after {timeout} seconds"
                    self.history.append(
                        SSHCommandHistory(event=SSHEventType.TIMEOUT_INTERRUPT, command=command, output=output, error=error_msg, timestamp=datetime.now())
                    )
                    return output, error_msg
                elif self.shell_channel.exit_status_ready():
                    break
                else:
                    time.sleep(0.1)
            
            self.history.append(
                SSHCommandHistory(event=SSHEventType.SHELL_COMMAND, command=command, output=output, error="", timestamp=datetime.now())
            )
            return output, ""
            
        except Exception as e:
            error_msg = f"Shell command failed: {e}"
            self.history.append(
                SSHCommandHistory(event=SSHEventType.SHELL_COMMAND, command=command, output="", error=error_msg, timestamp=datetime.now())
            )
            return "", error_msg

    def close_shell(self):
        """shell 세션 종료"""
        if self.shell_channel is not None:
            self.shell_channel.close()
            self.shell_channel = None
            self.history.append(
                SSHCommandHistory(
                    event=SSHEventType.SHELL_CLOSE,
                    error="",
                    timestamp=datetime.now()
                )
            )

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

