"""
Django 项目示例

演示如何使用 Oh My Coder 开发 Django 项目。

场景：为博客系统实现文章管理功能
"""

# ============================================================
# 第一步：探索 Django 项目结构
# ============================================================

# CLI 命令：
# omc explore .

# 预期输出：
# - 识别为 Django 项目
# - 发现：manage.py, blog/, templates/, static/
# - 技术栈：Django 5.0, PostgreSQL, Redis

# ============================================================
# 第二步：执行构建任务
# ============================================================

# CLI 命令：
# omc run "为博客系统实现文章管理功能，包括：
# 1. 文章 CRUD（增删改查）
# 2. 文章分类和标签
# 3. 文章评论功能
# 4. Markdown 编辑器支持
# 5. 文章搜索功能
# 要求：遵循 Django 最佳实践，支持分页和缓存" -w build

# ============================================================
# 预期生成的代码结构
# ============================================================

"""
blog/
├── models/
│   ├── __init__.py
│   ├── article.py          # 文章模型
│   ├── category.py         # 分类模型
│   ├── tag.py               # 标签模型
│   └── comment.py           # 评论模型
├── views/
│   ├── __init__.py
│   ├── article_views.py     # 文章视图
│   ├── category_views.py    # 分类视图
│   └── comment_views.py     # 评论视图
├── forms/
│   ├── __init__.py
│   ├── article_form.py      # 文章表单
│   └── comment_form.py      # 评论表单
├── api/
│   ├── __init__.py
│   ├── serializers.py       # DRF 序列化器
│   └── viewsets.py          # DRF 视图集
├── services/
│   ├── __init__.py
│   ├── article_service.py   # 文章服务
│   └── search_service.py    # 搜索服务
├── migrations/
│   └── ...
└── urls.py                  # URL 配置
"""

# ============================================================
# 示例：生成的文章模型
# ============================================================

from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.text import slugify
from django.utils import timezone


class Category(models.Model):
    """文章分类"""
    name = models.CharField('名称', max_length=100)
    slug = models.SlugField('Slug', unique=True, blank=True)
    description = models.TextField('描述', blank=True)
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name='父分类'
    )
    order = models.IntegerField('排序', default=0)
    is_active = models.BooleanField('是否启用', default=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '分类'
        verbose_name_plural = '分类'
        ordering = ['order', 'name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Tag(models.Model):
    """文章标签"""
    name = models.CharField('名称', max_length=50, unique=True)
    slug = models.SlugField('Slug', unique=True, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '标签'
        verbose_name_plural = '标签'
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Article(models.Model):
    """文章模型"""
    STATUS_CHOICES = [
        ('draft', '草稿'),
        ('published', '已发布'),
        ('archived', '已归档'),
    ]

    title = models.CharField('标题', max_length=200)
    slug = models.SlugField('Slug', unique=True, blank=True)
    content = models.TextField('内容')
    summary = models.TextField('摘要', max_length=500, blank=True)
    
    # 关联
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='articles',
        verbose_name='作者'
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='articles',
        verbose_name='分类'
    )
    tags = models.ManyToManyField(Tag, blank=True, verbose_name='标签')
    
    # 状态
    status = models.CharField(
        '状态',
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft'
    )
    is_featured = models.BooleanField('是否推荐', default=False)
    allow_comments = models.BooleanField('允许评论', default=True)
    
    # 统计
    views = models.PositiveIntegerField('浏览次数', default=0)
    likes = models.PositiveIntegerField('点赞数', default=0)
    
    # 时间
    published_at = models.DateTimeField('发布时间', null=True, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '文章'
        verbose_name_plural = '文章'
        ordering = ['-published_at', '-created_at']
        indexes = [
            models.Index(fields=['status', 'published_at']),
            models.Index(fields=['author', 'status']),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        if self.status == 'published' and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('blog:article_detail', kwargs={'slug': self.slug})


class Comment(models.Model):
    """评论模型"""
    article = models.ForeignKey(
        Article,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='文章'
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='作者'
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies',
        verbose_name='父评论'
    )
    content = models.TextField('评论内容')
    is_visible = models.BooleanField('是否显示', default=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '评论'
        verbose_name_plural = '评论'
        ordering = ['created_at']

    def __str__(self):
        return f'{self.author.username}: {self.content[:50]}'


# ============================================================
# 示例：生成的 Django 视图
# ============================================================

from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache
from django.db.models import Q

from .models import Article, Category, Tag, Comment
from .forms import ArticleForm, CommentForm


class ArticleListView(ListView):
    """文章列表视图"""
    model = Article
    template_name = 'blog/article_list.html'
    context_object_name = 'articles'
    paginate_by = 10

    def get_queryset(self):
        cache_key = f'articles_list_{self.kwargs.get("category_slug", "all")}'
        queryset = cache.get(cache_key)
        
        if queryset is None:
            queryset = Article.objects.filter(status='published').select_related(
                'author', 'category'
            ).prefetch_related('tags')
            
            category_slug = self.kwargs.get('category_slug')
            if category_slug:
                queryset = queryset.filter(category__slug=category_slug)
            
            cache.set(cache_key, queryset, 60 * 5)  # 缓存 5 分钟
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.filter(is_active=True)
        context['popular_tags'] = Tag.objects.annotate(
            article_count=models.Count('article')
        ).order_by('-article_count')[:10]
        return context


class ArticleDetailView(DetailView):
    """文章详情视图"""
    model = Article
    template_name = 'blog/article_detail.html'
    context_object_name = 'article'

    def get_object(self, queryset=None):
        article = super().get_object(queryset)
        # 增加浏览次数
        article.views = models.F('views') + 1
        article.save(update_fields=['views'])
        article.refresh_from_db()
        return article

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['comments'] = self.object.comments.filter(is_visible=True)
        context['comment_form'] = CommentForm()
        context['related_articles'] = Article.objects.filter(
            status='published',
            category=self.object.category
        ).exclude(pk=self.object.pk)[:3]
        return context


class ArticleCreateView(LoginRequiredMixin, CreateView):
    """创建文章视图"""
    model = Article
    form_class = ArticleForm
    template_name = 'blog/article_form.html'

    def form_valid(self, form):
        form.instance.author = self.request.user
        messages.success(self.request, '文章创建成功！')
        return super().form_valid(form)


class ArticleUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """更新文章视图"""
    model = Article
    form_class = ArticleForm
    template_name = 'blog/article_form.html'

    def test_func(self):
        article = self.get_object()
        return self.request.user == article.author

    def form_valid(self, form):
        messages.success(self.request, '文章更新成功！')
        return super().form_valid(form)


class ArticleDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """删除文章视图"""
    model = Article
    success_url = '/blog/'

    def test_func(self):
        article = self.get_object()
        return self.request.user == article.author

    def delete(self, request, *args, **kwargs):
        messages.success(request, '文章已删除！')
        return super().delete(request, *args, **kwargs)


# ============================================================
# 示例：DRF API 视图集
# ============================================================

from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from django_filters.rest_framework import DjangoFilterBackend

from .models import Article, Category, Tag, Comment
from .serializers import ArticleSerializer, ArticleListSerializer


class ArticleViewSet(viewsets.ModelViewSet):
    """文章 API 视图集"""
    queryset = Article.objects.filter(status='published')
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'tags', 'author']
    search_fields = ['title', 'content', 'summary']
    ordering_fields = ['published_at', 'views', 'likes']
    ordering = ['-published_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return ArticleListSerializer
        return ArticleSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=True, methods=['post'])
    def like(self, request, pk=None):
        """点赞文章"""
        article = self.get_object()
        article.likes = models.F('likes') + 1
        article.save(update_fields=['likes'])
        article.refresh_from_db()
        return Response({'likes': article.likes})

    @action(detail=False)
    def featured(self, request):
        """获取推荐文章"""
        featured = self.queryset.filter(is_featured=True)[:5]
        serializer = self.get_serializer(featured, many=True)
        return Response(serializer.data)


# ============================================================
# 第三步：验证和测试
# ============================================================

# CLI 命令：
# omc run "为博客系统生成单元测试和功能测试" -w test

# 测试示例：
"""
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse

from .models import Article, Category, Tag


class ArticleModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.category = Category.objects.create(
            name='测试分类',
            description='测试描述'
        )
        self.article = Article.objects.create(
            title='测试文章',
            content='这是测试内容',
            author=self.user,
            category=self.category,
            status='published'
        )

    def test_article_creation(self):
        self.assertEqual(self.article.title, '测试文章')
        self.assertEqual(self.article.status, 'published')
        self.assertEqual(self.article.author, self.user)

    def test_article_slug_auto_generated(self):
        self.assertTrue(self.article.slug)

    def test_article_get_absolute_url(self):
        url = self.article.get_absolute_url()
        self.assertIn(self.article.slug, url)


class ArticleViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.category = Category.objects.create(name='测试分类')
        self.article = Article.objects.create(
            title='测试文章',
            content='测试内容',
            author=self.user,
            category=self.category,
            status='published'
        )

    def test_article_list_view(self):
        response = self.client.get('/blog/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '测试文章')

    def test_article_detail_view(self):
        response = self.client.get(self.article.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '测试文章')
"""

# ============================================================
# 运行步骤总结
# ============================================================

"""
完整执行流程：

1. 探索项目
   omc explore .

2. 构建功能
   omc run "实现博客文章管理功能" -w build

3. 生成测试
   omc run "为博客模块生成测试" -w test

4. 代码审查
   omc run "审查代码质量和安全性" -w review

5. 查看报告
   打开 reports/ 目录查看执行报告

6. 运行测试（手动）
   python manage.py test blog.tests
"""
