# 优化后的代码
from typing import List, Dict

def calculate(items: List[Dict]) -> float:
    """计算订单总价"""
    return sum(
        item['price'] * item['quantity']
        for item in items
    )

def process(data: List[Dict]) -> List[Dict]:
    """筛选活跃数据"""
    return [d for d in data if d.get('active')]
