"""
T2: 对 Hacker News 帖子进行主题分类和热点识别

根据标题和来源，判断每篇帖子的核心领域，并标记热门帖子。
"""

from dataclasses import dataclass, field
from typing import Optional
from .t1_extract_posts import Post

# 定义分类类别
CATEGORIES = {
    "hardware": ["steam controller", "hardware", "chip", "gpu", "cpu", "console"],
    "ai_ml": ["llm", "ai", "machine learning", "deep learning", "model", "agent", "gpt", "neural"],
    "open_source": ["open source", "github", "creative commons", "license", "release"],
    "programming": ["programming", "coding", "software", "developer", "code", "api", "framework"],
    "security": ["security", "privacy", "hack", "vulnerability", "fraud", "defense"],
    "web_dev": ["web", "css", "html", "javascript", "frontend", "backend", "http"],
    "startup_business": ["startup", "yc", "hiring", "business", "company", "funding"],
    "science": ["science", "research", "biology", "physics", "math", "cell"],
    "culture_life": ["culture", "life", "workplace", "productivity", "british", "sorry", "pen pal"],
    "gaming": ["game", "gaming", "steam", "controller"],
    "cloud_infra": ["cloud", "infrastructure", "diskless", "pxe", "zfs", "iscsi", "server"],
    "transportation": ["car", "camper", "van", "subway", "nyc", "transport"],
}

def classify_post(post: Post) -> list[str]:
    """
    对单条帖子进行分类。

    Args:
        post: 要分类的帖子。

    Returns:
        该帖子所属的类别列表（一个帖子可能属于多个类别）。
    """
    title_lower = post.title.lower()
    source_lower = post.source.lower()
    text = f"{title_lower} {source_lower}"
    
    matched_categories = []
    for category, keywords in CATEGORIES.items():
        for keyword in keywords:
            if keyword in text:
                matched_categories.append(category)
                break
    
    if not matched_categories:
        matched_categories.append("other")
    
    return matched_categories


@dataclass
class ClassificationResult:
    """分类结果"""
    posts: list[Post]
    categories: dict[str, list[Post]]
    hot_posts: list[Post]  # 点赞数 > 500 或评论数 > 200

def classify_all_posts(posts: list[Post]) -> ClassificationResult:
    """
    对所有帖子进行分类并识别热门话题。

    Args:
        posts: 所有帖子的列表。

    Returns:
        包含分类结果和热门帖子的对象。
    """
    categories: dict[str, list[Post]] = {}
    hot_posts: list[Post] = []
    
    for post in posts:
        # 分类
        matched = classify_post(post)
        for cat in matched:
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(post)
        
        # 热门识别
        if post.points > 500 or post.comments > 200:
            hot_posts.append(post)
    
    return ClassificationResult(
        posts=posts,
        categories=categories,
        hot_posts=hot_posts
    )

def print_classification(result: ClassificationResult) -> None:
    """打印分类结果"""
    print("=== 分类结果 ===\n")
    
    for category, posts in sorted(result.categories.items()):
        print(f"\n--- {category} ({len(posts)} 条) ---")
        for post in posts:
            print(f"  {post.rank}. {post.title}")
    
    print("\n\n=== 热门话题 (点赞 > 500 或评论 > 200) ===\n")
    for post in result.hot_posts:
        print(f"  {post.rank}. {post.title} (点赞: {post.points}, 评论: {post.comments})")

if __name__ == "__main__":
    # 测试分类
    from .t1_extract_posts import extract_posts
    
    test_content = """
1. Valve releases Steam Controller CAD files under Creative Commons license ( digitalfoundry.net )
1505 points by haunter 20 hours ago | hide | 496 comments
2. Appearing productive in the workplace ( nooneshappy.com )
1273 points by diebillionaires 19 hours ago | hide | 504 comments
3. Boris Cherny: TI-83 Plus Basic Programming Tutorial (2004) ( ticalc.org )
42 points by suoken 4 hours ago | hide | 16 comments
"""
    posts = extract_posts(test_content)
    result = classify_all_posts(posts)
    print_classification(result)