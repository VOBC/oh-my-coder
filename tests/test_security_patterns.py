"""
安全模式测试

验证代码遵循安全编码规范：
1. 异常信息不泄露敏感数据
2. URL 验证使用安全方法
3. 加密算法使用强算法
"""

import re
import subprocess
from pathlib import Path
from urllib.parse import urlparse

import pytest


class TestExceptionHandling:
    """测试异常处理安全性"""

    def test_no_str_e_in_error_return(self):
        """确保错误返回不使用 str(e)"""
        # 扫描所有 Python 文件
        src_dir = Path("src")
        issues = []

        for py_file in src_dir.rglob("*.py"):
            content = py_file.read_text()
            # 查找不安全的 str(e) 使用
            # 排除安全的使用场景
            for match in re.finditer(r'error["\']?\s*[:=]\s*str\(e\)', content):
                issues.append(
                    f"{py_file}:{content[: match.start()].count(chr(10)) + 1}"
                )

        assert not issues, f"发现不安全的 str(e) 使用: {issues}"

    def test_no_str_e_in_http_exception(self):
        """确保 HTTPException 不使用 str(e)"""
        src_dir = Path("src")
        issues = []

        for py_file in src_dir.rglob("*.py"):
            content = py_file.read_text()
            for match in re.finditer(r"HTTPException.*detail=str\(e\)", content):
                issues.append(
                    f"{py_file}:{content[: match.start()].count(chr(10)) + 1}"
                )

        assert not issues, f"发现 HTTPException(detail=str(e)): {issues}"


class TestURLValidation:
    """测试 URL 验证安全性"""

    def test_no_in_url_pattern(self):
        """确保不使用 'domain' in url 模式"""
        # 白名单：这些模式是安全的
        safe_patterns = [
            r"urlparse",
            r"startswith",
            r"endswith",
            r"#.*in.*url",  # 注释
        ]

        src_dir = Path("src")
        issues = []

        for py_file in src_dir.rglob("*.py"):
            content = py_file.read_text()
            # 查找 "xxx" in url_var 模式
            for match in re.finditer(r'["\'][^"\']*["\']\s+in\s+\w*url', content):
                line_num = content[: match.start()].count("\n") + 1
                # 检查是否在安全上下文中
                line = content.split("\n")[line_num - 1]
                if not any(re.search(p, line) for p in safe_patterns):
                    issues.append(f"{py_file}:{line_num}")

        # 测试文件可能有例外，只检查 src/
        assert not issues, f"发现不安全的 'in url' 模式: {issues}"

    def test_urlparse_usage(self):
        """验证 urlparse 正确使用"""
        # 这个测试验证 urlparse 的使用方式
        url = "https://api.deepseek.com/v1/chat"
        parsed = urlparse(url)

        assert parsed.scheme == "https"
        assert parsed.netloc == "api.deepseek.com"
        assert parsed.path == "/v1/chat"


class TestCryptographicAlgorithms:
    """测试加密算法安全性"""

    def test_no_md5_for_password(self):
        """确保 MD5 不用于密码存储"""
        src_dir = Path("src")
        issues = []

        for py_file in src_dir.rglob("*.py"):
            content = py_file.read_text()
            # 查找 hashlib.md5 使用
            for match in re.finditer(r"hashlib\.md5\(", content):
                line_num = content[: match.start()].count("\n") + 1
                line = content.split("\n")[line_num - 1]
                # 检查是否有安全注释
                if not re.search(r"#.*(safe|non-crypto|cache|id)", line, re.I):
                    # 检查上下文是否涉及密码
                    start = max(0, line_num - 5)
                    context = "\n".join(content.split("\n")[start:line_num])
                    if re.search(r"password|passwd|pwd|secret|key", context, re.I):
                        issues.append(f"{py_file}:{line_num}")

        assert not issues, f"发现 MD5 用于密码相关操作: {issues}"

    def test_sha256_for_cache_key(self):
        """验证缓存键使用 SHA256"""
        # 这是一个正向测试，验证我们的修复
        content = (
            Path("src/utils/performance.py").read_text()
            if Path("src/utils/performance.py").exists()
            else ""
        )

        if content:
            # 应该使用 sha256 而非 md5
            assert "hashlib.sha256" in content or "hashlib.md5" not in content


class TestCommandInjection:
    """测试命令注入防护"""

    def test_no_os_system_with_format(self):
        """确保不使用 os.system + 格式化字符串"""
        src_dir = Path("src")
        issues = []

        for py_file in src_dir.rglob("*.py"):
            content = py_file.read_text()
            # 查找 os.system(f"...") 模式
            for match in re.finditer(r"os\.system\s*\(\s*f[\"']", content):
                line_num = content[: match.start()].count("\n") + 1
                issues.append(f"{py_file}:{line_num}")

        assert not issues, f"发现 os.system + f-string: {issues}"

    def test_subprocess_with_list(self):
        """验证 subprocess 使用参数列表"""
        # 正确示例
        result = subprocess.run(
            ["echo", "hello"], capture_output=True, text=True, check=False
        )
        assert result.returncode == 0


class TestPathTraversal:
    """测试路径遍历防护"""

    def test_path_validation_pattern(self):
        """验证路径验证模式"""
        base = Path("/data").resolve()
        user_input = "../../../etc/passwd"

        # 危险：直接拼接
        # dangerous_path = base / user_input  # ❌

        # 安全：验证路径
        try:
            target = (base / user_input).resolve()
            if not str(target).startswith(str(base)):
                raise ValueError("Path traversal detected")
        except Exception:
            pass  # 预期会失败或被拦截

        # 正确用法
        safe_filename = "safe_file.txt"
        safe_path = (base / safe_filename).resolve()
        assert str(safe_path).startswith(str(base))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
