from instance_controller.controller import LLMController
from core.config import settings

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
            summary = controller.summarize_session()



        print("RootLLM 종료.")

if __name__ == "__main__":
    print(settings)
    main()
    
# TODO: 네인에서 시간, 모델 선택 가능하게 하기