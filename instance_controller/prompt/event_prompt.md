"connect"            -> SSH 연결을 시도하는 명령 및 기록 이벤트
"disconnect"         -> SSH 연결을 종료하는 명령 및 기록 이벤트
"reconnect"          -> SSH 재연결을 시도하는 명령 및 기록 이벤트
"shell_create"       -> 새로운 셸 세션을 생성하는 명령 및 기록 이벤트
"shell_close"        -> 셸 세션을 닫는 명령 및 기록 이벤트
"shell_command"      -> 셸 내에서 명령 실행 후 결과를 기록하는 명령 및 기록 이벤트
"interrupt"          -> 실행 중인 명령을 중단(Ctrl+C)하는 명령 및 기록 이벤트
"timeout_interrupt"  -> 명령 실행이 타임아웃되어 자동 중단했을 때 기록용 이벤트, 명령으로는 쓰지 않습니다.