from datetime import datetime
import os
import time
from dotenv import load_dotenv
from instance.manager import SSHCommandHistory, SSHEventType, SSHInfo, InstanceManager # SSH 클라이언트 모듈 임포트
from controller.llm import LLM

class LLMController:
    def __init__(self):
        # 세션 실행 시간 초기화
        self.start_time = time.time()
        # SSH 연결 초기화
        load_dotenv()
        self.ssh_info = SSHInfo(
            host=os.getenv("SSH_HOST"),
            port=os.getenv("SSH_PORT"),
            username=os.getenv("SSH_USERNAME"),
            password=os.getenv("SSH_PASSWORD")
        )
        self.instance = InstanceManager('test', self.ssh_info)
        self.instance.connect()
        self.llm = LLM()

    def generate_command(self):
        """
        계획과 현재 history를 기반으로 계획, bash 명령 생성
        """
        res = self.llm.generate_response(history=self.instance.history)
        
        # JSON 응답을 파싱하여 command 추출
        import json
        try:
            command_data = json.loads(res)
            command = command_data.get('command', {}).get('content', '')
            
            # history에 기록
            self.instance.history.append(
                SSHCommandHistory(
                    event=SSHEventType.SHELL_COMMAND,
                    error="",
                    timestamp=datetime.now(),
                    description=command_data.get('description', 'Generated command from LLM'),
                    command=command
                )
            )
            return command
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error parsing LLM response: {e}")
            return "echo 'LLM response parsing failed'"

    def send_command(self, command):
        """
        SSH를 통해 명령을 라즈베리파이에 전송
        """
        response = self.instance.send_command_to_shell(command)
        return response

    def run_session(self, time_limit=2 * 60 * 60):
        """
        세션 실행 로직
        """
        try:
            while time.time() - self.start_time < time_limit:  # 시간 제한
                try:
                    command = self.generate_command()
                    if command:  # 빈 명령이 아닌 경우에만 실행
                        response = self.send_command(command)
                        print(time.time() - self.start_time, "초 경과")
                        print(f"Command: {command}")
                        print(f"Response: {response}")
                        print('\n\n\n')
                    time.sleep(1)  # 과도한 API 호출 방지
                except Exception as e:
                    print(f"Error in session loop: {e}")
                    time.sleep(5)  # 오류 발생 시 잠시 대기
                    continue
        finally:
            self.instance.close_shell()
        
        # 세션 종료 후 요약 출력
        for entry in self.instance.history:
            print(f"{entry.timestamp} - {entry.event.value}: {entry.command} - {entry.description}")
        summary = self.llm.summarize_history(self.instance.history)
        print("\nSession Summary:")
        print(summary)