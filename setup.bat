@echo off
chcp 65001 >nul
title JmTool 一键环境配置

echo ============================================
echo   JmTool - 一键环境配置
echo ============================================
echo.
echo 正在检查 Python 环境...

python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [FAIL] 未检测到 Python，请先安装 Python 3.9+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)
echo [OK] Python 已安装
echo.

echo 正在安装依赖包，请稍候...
echo.

pip install commonx -q 2>&1 | findstr /V "WARNING"
pip install curl_cffi -q 2>&1 | findstr /V "WARNING"
pip install Pillow -q 2>&1 | findstr /V "WARNING"
pip install pycryptodome -q 2>&1 | findstr /V "WARNING"
pip install PyYAML -q 2>&1 | findstr /V "WARNING"

echo.
echo ============================================
echo   自检依赖
echo ============================================
echo.

python -c "import common;           print('[OK] commonx')"       2>nul || echo "[FAIL] commonx - pip install commonx"
python -c "import curl_cffi;        print('[OK] curl_cffi')"    2>nul || echo "[FAIL] curl_cffi - pip install curl_cffi"
python -c "from PIL import Image;   print('[OK] Pillow')"       2>nul || echo "[FAIL] Pillow - pip install Pillow"
python -c "from Crypto import __version__; print('[OK] pycryptodome')" 2>nul || echo "[FAIL] pycryptodome - pip install pycryptodome"
python -c "import yaml;             print('[OK] PyYAML')"       2>nul || echo "[FAIL] PyYAML - pip install PyYAML"
python -c "import sys; sys.path.insert(0, 'jmcomic'); import jmcomic; print('[OK] jmcomic ' + jmcomic.__version__)" 2>nul || echo "[FAIL] jmcomic 内置库异常"

echo.
echo ============================================
echo   配置完成！
echo   如全部 OK，重启 AstrBot 后发送 .jmtest 验证
echo ============================================
pause
