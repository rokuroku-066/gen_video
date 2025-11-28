@echo off
setlocal

echo ============================================
echo  Gemini + Veo 開発環境セットアップスクリプト
echo  - Python 3
echo  - Node.js (LTS)
echo  - Git
echo  - ffmpeg
echo  - VS Code
echo ============================================
echo.

REM --- 管理者権限チェック ---
net session >nul 2>&1
if %errorlevel% NEQ 0 (
    echo [ERROR] 管理者権限で実行してください。
    echo  - PowerShell または コマンドプロンプトを「管理者として実行」
    echo  - その上で setup_env.bat を実行
    pause
    exit /b 1
)

REM --- winget の存在チェック ---
where winget >nul 2>&1
if %errorlevel% NEQ 0 (
    echo [ERROR] winget が見つかりません。
    echo Windows 11 もしくは winget が利用可能な環境が必要です。
    pause
    exit /b 1
)

echo [INFO] 必要なツールを winget でインストールします...
echo.

REM =======================================================
REM  Python 3
REM =======================================================
echo [INFO] Python 3 をインストール / 更新します...
winget install -e --id Python.Python.3 --source winget --silent
if %errorlevel% NEQ 0 (
    echo [WARN] Python のインストールに失敗したか、既にインストール済みの可能性があります。
) else (
    echo [OK] Python インストール完了
)
echo.

REM =======================================================
REM  Node.js (LTS)
REM =======================================================
echo [INFO] Node.js LTS をインストール / 更新します...
winget install -e --id OpenJS.NodeJS.LTS --source winget --silent
if %errorlevel% NEQ 0 (
    echo [WARN] Node.js のインストールに失敗したか、既にインストール済みの可能性があります。
) else (
    echo [OK] Node.js インストール完了
)
echo.

REM =======================================================
REM  Git
REM =======================================================
echo [INFO] Git をインストール / 更新します...
winget install -e --id Git.Git --source winget --silent
if %errorlevel% NEQ 0 (
    echo [WARN] Git のインストールに失敗したか、既にインストール済みの可能性があります。
) else (
    echo [OK] Git インストール完了
)
echo.

REM =======================================================
REM  ffmpeg
REM =======================================================
echo [INFO] ffmpeg をインストール / 更新します...
winget install -e --id Gyan.FFmpeg --source winget --silent
if %errorlevel% NEQ 0 (
    echo [WARN] ffmpeg のインストールに失敗したか、既にインストール済みの可能性があります。
) else (
    echo [OK] ffmpeg インストール完了
)
echo.

REM =======================================================
REM  Visual Studio Code (任意)
REM =======================================================
echo [INFO] Visual Studio Code をインストール / 更新します...
winget install -e --id Microsoft.VisualStudioCode --source winget --silent
if %errorlevel% NEQ 0 (
    echo [WARN] VS Code のインストールに失敗したか、既にインストール済みの可能性があります。
) else (
    echo [OK] VS Code インストール完了
)
echo.

echo ============================================
echo  セットアップ処理が完了しました。
echo  必要に応じて PC を再起動してください。
echo ============================================
echo.

pause
endlocal
exit /b 0
