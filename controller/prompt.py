# # llm 프롬프트를 관리
# SYSTEM_PROMPT = """

# 다음은 현재 컴퓨터 시스템에 대한 로그입니다.
# json


# 다음은 당신이 이전에 짠 계획입니다.
# json

# 이제 다음에 입력할 명령어를 입력하십시오.

# ——————output_format——————
# {
#     "event" : type.value,
#     "command" : {
#         "content" : "ls"
#         "timeout" : 10
#     },
#     "description" : "",
#     "current_plan" : ""
# }
# """