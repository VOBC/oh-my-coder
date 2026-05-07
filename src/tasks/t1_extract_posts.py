"""
T1: 提取 Hacker News 首页帖子信息

从提供的网页内容中提取所有30条帖子的结构化信息。
"""

from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Post:
    """表示 Hacker News 上的一条帖子"""
    rank: int
    title: str
    source: str
    points: int
    author: str
    time_ago: str
    comments: int
    url: str = ""

def extract_posts(raw_content: str) -> list[Post]:
    """
    从原始网页内容中提取帖子列表。

    Args:
        raw_content: 从 Hacker News 首页抓取的文本内容。

    Returns:
        包含所有帖子的列表。
    """
    posts: list[Post] = []
    lines = raw_content.strip().split('\n')
    
    current_rank = 0
    current_title = ""
    current_source = ""
    current_points = 0
    current_author = ""
    current_time = ""
    current_comments = 0
    current_url = ""
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # 匹配帖子条目，格式: "序号. 标题 ( 来源 )"
        # 例如: "1. Valve releases Steam Controller CAD files under Creative Commons license ( digitalfoundry.net )"
        import re
        match = re.match(r'^(\d+)\.\s+(.+?)\s+\((.+?)\)\s*$', line)
        if match:
            # 如果已有上一个帖子，保存
            if current_title:
                posts.append(Post(
                    rank=current_rank,
                    title=current_title,
                    source=current_source,
                    points=current_points,
                    author=current_author,
                    time_ago=current_time,
                    comments=current_comments,
                    url=current_url
                ))
            
            # 新帖子的基本信息
            current_rank = int(match.group(1))
            current_title = match.group(2).strip()
            current_source = match.group(3).strip()
            current_points = 0
            current_author = ""
            current_time = ""
            current_comments = 0
            current_url = ""
            continue
        
        # 匹配点赞数、作者、时间、评论数行
        # 格式: "1505 points by haunter 20 hours ago | hide | 496 comments"
        points_match = re.match(r'^(\d+)\s+points\s+by\s+(\S+)\s+(.+?)\s+\|\s+hide\s+\|\s+(\d+)\s+comments$', line)
        if points_match and current_rank:
            current_points = int(points_match.group(1))
            current_author = points_match.group(2)
            current_time = points_match.group(3).strip()
            current_comments = int(points_match.group(4))
            continue
    
    # 保存最后一条帖子
    if current_title:
        posts.append(Post(
            rank=current_rank,
            title=current_title,
            source=current_source,
            points=current_points,
            author=current_author,
            time_ago=current_time,
            comments=current_comments,
            url=current_url
        ))
    
    return posts

def print_posts(posts: list[Post]) -> None:
    """打印帖子列表"""
    print(f"共提取 {len(posts)} 条帖子:\n")
    for post in posts:
        print(f"{post.rank}. {post.title}")
        print(f"   来源: {post.source} | 点赞: {post.points} | 作者: {post.author} | {post.time_ago} | 评论: {post.comments}")
        print()

if __name__ == "__main__":
    # 测试提取
    test_content = """1. Valve releases Steam Controller CAD files under Creative Commons license ( digitalfoundry.net )
1505 points by haunter 20 hours ago | hide | 496 comments"""
    
    posts = extract_posts(test_content)
    print_posts(posts)