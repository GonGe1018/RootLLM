from openai import OpenAI
from pydantic import BaseModel, Field

from core.models import StepHistory, EventType
from instance_controller.prompt import generate_system_prompt


class CommandFormat(BaseModel):
    content: str = Field(..., description="실행할 bash 명령어")
    timeout: int = Field(30, description="명령어 실행 시간 제한 (초 단위)")


class ResponseFormat(BaseModel):
    event: str = Field(..., description=f"{[e.value for e in EventType]}")
    description: str = Field(..., description="event 명령을 선택한 이유와 설명")
    command: CommandFormat | None = Field(
        None, description="명령 이벤트일 경우 실행할 명령어"
    )


class LLM:
    def __init__(self, settings):
        self.api_key = settings.openai_api_key
        self.client = OpenAI(api_key=self.api_key)
        self.model = settings.openai_model

    def generate_response(self, history: list[StepHistory] = []) -> str:
        """
        LLM에 프롬프트를 보내고 응답 받는
        최근 10개는 원본, 그 이전은 요약해서 사용
        """
        if len(history) <= 10:
            history_text = "\n".join(
                [f"{entry.model_dump_json()}" for entry in history]
            )
        else:
            older_history = history[:-10]
            recent_history = history[-10:]

            summary = self.summarize_history(older_history)

            recent_history_text = "\n".join(
                [f"{entry.model_dump_json()}" for entry in recent_history]
            )

            history_text = f"=== 이전 기록 요약 ===\n{summary}\n\n=== 최근 10개 기록 (원본) ===\n{recent_history_text}"

        system_prompt = generate_system_prompt(history=history_text)
        messages = [{"role": "system", "content": system_prompt}]

        response = self.client.chat.completions.parse(
            model=self.model,
            messages=messages,
            response_format=ResponseFormat,
        )

        return response.choices[0].message.content  # ResponseFormat 객체로 가정

    def summarize_history(self, history):
        """
        LLM을 사용하여 SSH 명령 기록을 요약하는 메소드
        :param history: SSHCommandHistory 객체의 리스트
        :return: 요약된 문자열
        """
        prompt = "다음은 SSH 명령 기록입니다:\n"
        for entry in history:
            prompt += entry.model_dump_json() + "\n"

        prompt += "\n\n이 기록을 요약하는 보고서를 작성해주세요."

        summary = (
            self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
            )
            .choices[0]
            .message.content
        )
        return summary
