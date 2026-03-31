#!/bin/bash
# 安装依赖脚本

echo "安装CodeRipple依赖..."

# 安装基础依赖
python3 -m pip install --user gitpython tree-sitter click pyyaml pytest pytest-cov

echo "安装完成！"
echo "请运行: python3 verify.py"
