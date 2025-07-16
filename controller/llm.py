from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path
import os
from instance.manager import SSHCommandHistory, SSHEventType

class LLM:
  def __init__(self):
    load_dotenv()
    self.api_key = os.getenv("OPENAI_API_KEY")
    self.client = OpenAI(api_key=self.api_key)
    self.model = "gpt-4.1-2025-04-14"  # 사용할 모델
    self.system_prompt = Path("controller/prompt/systemprompt.txt").read_text()
    
  
  def generate_response(self, history=list()): # history는 SSHCommandHistory 객체의 리스트
    """
    LLM에 프롬프트를 보내고 응답을 받는 메소드
    :param prompt: LLM에 보낼 프롬프트 문자열
    :return: LLM의 응답 문자열
    """
    messages = [{"role": "system", "content": self.system_prompt},]

    # history 추가
    content = "\n".join([f"{entry.event.value}: {entry.command}" for entry in history])
    messages.append({
      "role": "user",
      "content": content
    })

    schema = {
        "type": "json_schema",
        "json_schema": {
            "name": "ssh_command_response",
            "schema": {
                "type": "object",
                "properties": {
                    "event": {
                        "type": "string",
                        "enum": [e.value for e in SSHEventType]
                    },
                    "error": {
                        "type": "string"
                    },
                    "timestamp": {
                        "type": "string",
                        "format": "date-time"
                    },
                    "description": {
                        "type": "string"
                    },
                    "command": {
                        "type": ["string", "null"],
                        "description": "명령 이벤트일 경우 실행할 명령어"
                    },
                    "output": {
                        "type": ["string", "null"],
                        "description": "명령 실행 결과 출력"
                    }
                },
                "required": ["event", "error", "timestamp", "description"],
                "additionalProperties": False
            }
        }
    }
    response = self.client.chat.completions.create(
      model=self.model,
      messages=messages,
      response_format=schema,
    )
    return response.choices[0].message.content # SSHCommandHistory 객체로 가정
  
  def summarize_history(self, history):
    """
    LLM을 사용하여 SSH 명령 기록을 요약하는 메소드
    :param history: SSHCommandHistory 객체의 리스트
    :return: 요약된 문자열
    """
    prompt = "다음은 SSH 명령 기록입니다:\n"
    for entry in history:
      prompt += f"{entry.event.value}: {entry.command}\n"
    
    prompt += "이 기록을 요약해 주세요."
    
    summary = self.client.chat.completions.create(
      model=self.model,
      messages=[{"role": "user", "content": prompt}],
    ).choices[0].message.content
    return summary