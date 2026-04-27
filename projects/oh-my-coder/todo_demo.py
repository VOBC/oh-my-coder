# 文件路径: /Users/vobc/.qclaw/workspace-agent-bf627e2b/projects/oh-my-coder/todo.py
# 变更说明: 创建主入口文件，处理 CLI 参数解析和命令路由

#!/usr/bin/env python3
"""
待办事项 CLI 应用
支持添加、查看、完成、删除任务，数据存储在 JSON 文件中
"""

import argparse
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径，以便导入本地模块
sys.path.insert(0, str(Path(__file__).parent))

from src.todo.logic import TodoManager
from src.todo.storage import TodoStorage


def main():
    """主函数：解析命令行参数并执行相应命令"""
    parser = argparse.ArgumentParser(
        description="简单的待办事项管理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python todo.py add "买牛奶"
  python todo.py list
  python todo.py done 1
  python todo.py delete 1
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # add 命令
    add_parser = subparsers.add_parser("add", help="添加新任务")
    add_parser.add_argument("description", help="任务描述")
    
    # list 命令
    subparsers.add_parser("list", help="查看所有任务")
    
    # done 命令
    done_parser = subparsers.add_parser("done", help="标记任务为完成")
    done_parser.add_argument("index", type=int, help="任务序号（从1开始）")
    
    # delete 命令
    delete_parser = subparsers.add_parser("delete", help="删除任务")
    delete_parser.add_argument("index", type=int, help="任务序号（从1开始）")
    
    # 解析参数
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    try:
        # 初始化存储和管理器
        storage = TodoStorage()
        manager = TodoManager(storage)
        
        # 执行命令
        if args.command == "add":
            task = manager.add_task(args.description)
            print(f"✓ 已添加任务: {task.description}")
            
        elif args.command == "list":
            tasks = manager.list_tasks()
            if not tasks:
                print("暂无待办事项")
            else:
                print("待办事项列表:")
                for i, task in enumerate(tasks, 1):
                    status = "✓" if task.status == "done" else "□"
                    print(f"{i:3d}. [{status}] {task.description}")
                    
        elif args.command == "done":
            task = manager.mark_done(args.index)
            print(f"✓ 已完成任务: {task.description}")
            
        elif args.command == "delete":
            task = manager.delete_task(args.index)
            print(f"✓ 已删除任务: {task.description}")
            
    except ValueError as e:
        print(f"错误: {e}")
        return 1
    except Exception as e:
        print(f"系统错误: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())