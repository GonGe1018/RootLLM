import paramiko
from pydantic import BaseModel, Field

# 인스턴스 실행 관리(SSH 연결, 명령 실행)

class SSHInfo(BaseModel):
    host: str = Field(...)
    port: int = Field(22)
    username: str = Field(...)
    password: str = Field(...)

class Instance:
    def __init__(self, instance_id, ssh_info: SSHInfo):
        self.instance_id = instance_id

        self.ssh_info = ssh_info
        self.ssh_client = paramiko.SSHClient()
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh_client.connect(
            hostname=self.ssh_info.host,
            port=self.ssh_info.port,
            username=self.ssh_info.username,
            password=self.ssh_info.password,
            timeout=10
        )


    def run_command(self, command: str, get_pty: bool = False) -> tuple[str, str]:
        stdin, stdout, stderr = self.ssh_client.exec_command(command, get_pty=get_pty)
        out = stdout.read().decode('utf-8')
        err = stderr.read().decode('utf-8')
        return out, err

    def close(self):
        self.ssh_client.close()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

