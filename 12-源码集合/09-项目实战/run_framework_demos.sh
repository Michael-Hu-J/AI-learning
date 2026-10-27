#!/bin/bash

# AI测试框架演示脚本
# 用于快速运行四个主要框架的演示

echo "==========================================="
echo "AI测试框架演示集合"
echo "==========================================="

case $1 in
  "langgraph")
    echo "运行LangGraph演示..."
    cd 78-langgraph实战 && python run_tests.py --demo
    ;;
  "langchain")
    echo "运行LangChain演示..."
    cd 79-langchain实战 && python run_rag_tests.py --demo
    ;;
  "crewai")
    echo "运行CrewAI演示..."
    cd 80-crewAI实战 && python run_crewai_tests.py --demo
    ;;
  "autogen")
    echo "运行AutoGen演示..."
    cd 81-autogen实战 && python run_autogen_tests.py --demo
    ;;
  "all")
    echo "依次运行所有框架演示..."
    echo "1. LangGraph演示"
    cd 78-langgraph实战 && python run_tests.py --demo && cd ..
    echo ""
    echo "2. LangChain演示" 
    cd 79-langchain实战 && python run_rag_tests.py --demo && cd ..
    echo ""
    echo "3. CrewAI演示"
    cd 80-crewAI实战 && python run_crewai_tests.py --demo && cd ..
    echo ""
    echo "4. AutoGen演示"
    cd 81-autogen实战 && python run_autogen_tests.py --demo && cd ..
    ;;
  *)
    echo "用法: $0 {langgraph|langchain|crewai|autogen|all}"
    echo "  langgraph - 运行LangGraph框架演示"
    echo "  langchain - 运行LangChain框架演示" 
    echo "  crewai    - 运行CrewAI框架演示"
    echo "  autogen   - 运行AutoGen框架演示"
    echo "  all       - 运行所有框架演示"
    ;;
esac