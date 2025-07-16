"""
RootLLM - LLM을 이용한 자율적인 시스템 관리 도구
"""

from controller.controller import LLMController

def main():
    """메인 실행 함수"""
    try:
        print("RootLLM 시작...")
        controller = LLMController()
        print("SSH 연결 성공!")
        
        time_limit=60 * 30

        # 1시간 동안 세션 실행
        controller.run_session(time_limit=time_limit)

    except KeyboardInterrupt:
        print("\n프로그램이 사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"오류 발생: {e}")
    finally:
        print("RootLLM 종료.")

if __name__ == "__main__":
    main()
    
# TODO: 네인에서 시간, 모델 선택 가능하게 하기