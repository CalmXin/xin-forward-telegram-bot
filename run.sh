#! /bin/bash

WORK_DIR=$(dirname "$0")
VENV_DIR="$WORK_DIR/.venv"

cd "$WORK_DIR" || exit

if [ ! -d "$VENV_DIR" ]; then
    echo "虚拟环境不存在，正在创建……"
    python3 -m venv "$VENV_DIR"

    source "$VENV_DIR/bin/activate"
    pip install -r "$WORK_DIR/requirements.txt"
else
  echo "检测到虚拟环境，开始执行……"
    source "$VENV_DIR/bin/activate"
fi

python3 "$WORK_DIR/main.py"
deactivate
echo "运行结束"