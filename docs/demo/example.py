# 待优化的代码示例
def calculate(items):
    total = 0
    for i in range(len(items)):
        total = total + items[i]['price'] * items[i]['quantity']
    return total

def process(data):
    result = []
    for d in data:
        if d['active'] == True:
            result.append(d)
    return result
