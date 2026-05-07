"""
T3: 撰写 Hacker News 首页内容总结

基于分类结果，生成一段 200-300 字的自然语言总结。
"""

from .t2_classify_posts import ClassificationResult, classify_all_posts
from .t1_extract_posts import extract_posts

def generate_summary(result: ClassificationResult) -> str:
    """
    根据分类结果生成总结。

    Args:
        result: 分类结果对象。

    Returns:
        一段 200-300 字的总结文本。
    """
    hot_posts = result.hot_posts
    categories = result.categories
    
    # 找出最热门的帖子
    top_post = hot_posts[0] if hot_posts else result.posts[0]
    second_post = hot_posts[1] if len(hot_posts) > 1 else None
    
    # 统计各类别帖子数量
    category_counts = {cat: len(posts) for cat, posts in categories.items()}
    top_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:3]
    
    # 构建总结
    summary_parts = []
    
    # 开头：整体介绍
    summary_parts.append(
        f"Hacker News 首页今日呈现了{len(result.posts)}条热门科技动态，"
        f"涵盖硬件、AI、开源、编程、安全等多个领域。"
    )
    
    # 核心热门话题
    if top_post:
        summary_parts.append(
            f"最受关注的是「{top_post.title}」"
            f"（来自{top_post.source}），"
            f"获得了{top_post.points}点赞和{top_post.comments}条评论，"
            f"成为今日焦点。"
        )
    
    if second_post:
        summary_parts.append(
            f"紧随其后的是「{second_post.title}」"
            f"（来自{second_post.source}），"
            f"同样引发了社区的热烈讨论。"
        )
    
    # 类别分布
    if top_categories:
        cat_names = {
            "hardware": "硬件", "ai_ml": "AI/机器学习", "open_source": "开源",
            "programming": "编程开发", "security": "安全", "web_dev": "Web开发",
            "startup_business": "创业/商业", "science": "科学", "culture_life": "文化/生活",
            "gaming": "游戏", "cloud_infra": "云基础设施", "transportation": "交通"
        }
        category_text = "、".join(
            f"{cat_names.get(cat, cat)}（{count}条）"
            for cat, count in top_categories[:3]
        )
        summary_parts.append(
            f"从主题分布看，{category_text}是今日讨论最活跃的领域。"
        )
    
    # 有趣发现
    unique_posts = [p for p in result.posts if p not in hot_posts and p.points > 100]
    if unique_posts:
        interesting = unique_posts[0]
        summary_parts.append(
            f"一个有趣的亮点是「{interesting.title}」"
            f"（来自{interesting.source}），"
            f"虽然排名不高，但获得了{interesting.points}点赞，"
            f"值得关注。"
        )
    
    # 整体趋势
    ai_related = len(categories.get("ai_ml", []))
    if ai_related > 3:
        summary_parts.append(
            f"整体来看，AI和编程话题持续占据主导地位，"
            f"反映出技术社区对前沿工具和开发效率的持续关注。"
        )
    
    return "".join(summary_parts)

def main(raw_content: str) -> str:
    """
    主函数：提取、分类、总结。

    Args:
        raw_content: Hacker News 首页的原始文本内容。

    Returns:
        最终的总结文本。
    """
    posts = extract_posts(raw_content)
    result = classify_all_posts(posts)
    summary = generate_summary(result)
    return summary

if __name__ == "__main__":
    # 使用提供的网页内容进行测试
    test_content = """1. Valve releases Steam Controller CAD files under Creative Commons license ( digitalfoundry.net )
1505 points by haunter 20 hours ago | hide | 496 comments
2. Appearing productive in the workplace ( nooneshappy.com )
1273 points by diebillionaires 19 hours ago | hide | 504 comments
3. Boris Cherny: TI-83 Plus Basic Programming Tutorial (2004) ( ticalc.org )
42 points by suoken 4 hours ago | hide | 16 comments
4. SQLite Is a Library of Congress Recommended Storage Format ( sqlite.org )
335 points by whatisabcdefgh 14 hours ago | hide | 89 comments
5. Permacomputing Principles ( permacomputing.net )
170 points by andsoitis 9 hours ago | hide | 83 comments
6. GovernGPT (YC W24) Is Hiring Engineers to Build Thinking Systems in Montreal ( ycombinator.com )
6 minutes ago | hide
7. Agent-harness-kit scaffolding for multi-agent workflows (MCP, provider-agnostic) ( cardor.dev )
12 points by enmanuelmag 1 hour ago | hide | 3 comments
8. ZAYA1-8B: An 8B Moe Model with 760M Active Params Matching DeepSeek-R1 on Math ( firethering.com )
32 points by steveharing1 3 hours ago | hide | 25 comments
9. Diskless Linux boot using ZFS, iSCSI and PXE ( aniket.foo )
113 points by stereo-highway 8 hours ago | hide | 58 comments
10. Photoshop's challenges with focus, pt. 2 ( aresluna.org )
67 points by frizlab 5 hours ago | hide | 20 comments
11. LinkedIn profile visitor lists belong to the people, says Noyb ( theregister.com )
21 points by robin_reala 58 minutes ago | hide | 4 comments
12. Vibe coding and agentic engineering are getting closer than I'd like ( simonwillison.net )
635 points by e12e 21 hours ago | hide | 694 comments
13. Chevrolet Performance eCrate package (400v/200hp) ( chevrolet.com )
67 points by mindcrime 7 hours ago | hide | 43 comments
14. SingleRide: Longest route on NYC Subway without visiting the same station twice ( singleride.nyc )
30 points by TMWNN 5 hours ago | hide | 11 comments
15. RSS feeds send me more traffic than Google ( shkspr.mobi )
143 points by SpyCoder77 11 hours ago | hide | 31 comments
16. Show HN: Trust – Coding Rust like it's 1989 ( github.com/wojtczyk )
43 points by wojtczyk 6 hours ago | hide | 14 comments
17. ProgramBench: Can Language Models Rebuild Programs from Scratch? ( arxiv.org )
70 points by jonbaer 8 hours ago | hide | 39 comments
18. Indian matchbox labels as a visual archive ( itsnicethat.com )
10 points by sahar_builds 2 hours ago | hide | 1 comment
19. Making LLM Training Faster with Unsloth and NVIDIA ( unsloth.ai )
64 points by segmenta 4 hours ago | hide | 10 comments
20. The brave souls who bought a used, 340k-mile rental camper van ( thedrive.com )
13 points by PaulHoule 3 hours ago | hide | 5 comments
21. Google Cloud fraud defense, the next evolution of reCAPTCHA ( cloud.google.com )
328 points by unforgivenpasta 18 hours ago | hide | 329 comments
22. Show HN: Agent-skills-eval – Test whether Agent Skills improve outputs ( github.com/darkrishabh )
32 points by darkrishabh 5 hours ago | hide | 9 comments
23. From