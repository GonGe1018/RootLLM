from instance_controller.controller import LLMController
from core.config import settings
import json
import os
from datetime import datetime

def main():
    """메인 실행 함수"""
    controller = None
    try:
        print("RootLLM 시작...")
        controller = LLMController(settings)
        print("SSH 연결 성공!")
    
        controller.run_experiments(time_limit=settings.time_limit_seconds)

    except KeyboardInterrupt:
        print("\n프로그램이 사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"오류 발생: {e}")
    finally:
        if controller:
            # 결과 저장 디렉토리 생성
            os.makedirs(os.path.dirname(settings.summary_path), exist_ok=True)
            os.makedirs(os.path.dirname(settings.history_path), exist_ok=True)
            
            # 히스토리 저장 (JSONL 형식)
            try:
                with open(settings.history_path, 'w', encoding='utf-8') as f:
                    for entry in controller.history:
                        f.write(entry.model_dump_json() + '\n')
                print(f"히스토리 저장됨: {settings.history_path}")
            except Exception as e:
                print(f"히스토리 저장 실패: {e}")
            
            # 요약 저장
            try:
                summary = controller.llm.summarize_history(controller.history)
                with open(settings.summary_path, 'w', encoding='utf-8') as f:
                    f.write(f"# RootLLM 실행 요약 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                    f.write(summary)
                print(f"요약 저장됨: {settings.summary_path}")
            except Exception as e:
                print(f"요약 저장 실패: {e}")
                # 요약 실패 시 기본 정보만 저장
                with open(settings.summary_path, 'w', encoding='utf-8') as f:
                    f.write(f"# RootLLM 실행 요약 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                    f.write(f"총 실행된 명령 수: {len(controller.history)}\n")
                    f.write("요약 생성 중 오류가 발생했습니다.\n")
        
        print("RootLLM 종료.")

if __name__ == "__main__":
    print(settings)
    main()
    
# TODO: 네인에서 시간, 모델 선택 가능하게 하기