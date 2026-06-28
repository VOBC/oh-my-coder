"""
测试依赖解析器 (src/core/dependency_resolver.py)

覆盖 DependencyResolver、DependencyInfo、ResolutionResult 和辅助函数。
"""

from unittest.mock import MagicMock, patch

import pytest

from src.core.dependency_resolver import (
    MODULE_TO_PACKAGE,
    DependencyInfo,
    DependencyResolver,
    ResolutionResult,
    get_resolver,
    resolve_dependencies,
)


class TestDependencyInfo:
    """DependencyInfo 数据类测试"""

    def test_basic_info(self):
        info = DependencyInfo(module_name="requests", package_name="requests")
        assert info.module_name == "requests"
        assert info.package_name == "requests"
        assert info.is_standard_lib is False

    def test_with_standard_lib_flag(self):
        info = DependencyInfo(
            module_name="os", package_name="os", is_standard_lib=True
        )
        assert info.is_standard_lib is True


class TestResolutionResult:
    """ResolutionResult 数据类测试"""

    def test_default_fields(self):
        result = ResolutionResult()
        assert result.needed == []
        assert result.missing == []
        assert result.installed == []
        assert result.failed == []

    def test_with_data(self):
        dep = DependencyInfo("pytest", "pytest")
        result = ResolutionResult(
            needed=[dep],
            missing=[dep],
            installed=[],
            failed=[("numpy", "timeout")],
        )
        assert len(result.needed) == 1
        assert len(result.missing) == 1
        assert len(result.failed) == 1


class TestDependencyResolverExtraction:
    """extract_from_code 测试"""

    def test_extract_import(self):
        resolver = DependencyResolver()
        deps = resolver.extract_from_code("import requests\nimport os\n")
        names = {d.module_name for d in deps}
        assert "requests" in names
        assert "os" in names

    def test_extract_from_import(self):
        resolver = DependencyResolver()
        deps = resolver.extract_from_code("from typing import List, Optional\n")
        names = {d.module_name for d in deps}
        assert "typing" in names

    def test_extract_from_with_alias(self):
        resolver = DependencyResolver()
        deps = resolver.extract_from_code("import pandas as pd\nimport numpy as np\n")
        names = {d.module_name for d in deps}
        assert "pandas" in names
        assert "numpy" in names
        assert "pd" not in names  # alias 不算
        assert "np" not in names  # alias 不算

    def test_extract_multiple_same_module(self):
        """同一模块出现多次只提取一次"""
        resolver = DependencyResolver()
        deps = resolver.extract_from_code(
            "import requests\nimport os\nimport requests\n"
        )
        names = list(d.module_name for d in deps)
        assert names.count("requests") == 1

    def test_extract_stdlib(self):
        resolver = DependencyResolver()
        deps = resolver.extract_from_code(
            "import os\nimport sys\nimport json\nimport pathlib\n"
        )
        names = {d.module_name for d in deps}
        assert "os" in names
        assert "sys" in names
        assert "json" in names

    def test_extract_ignores_comments(self):
        resolver = DependencyResolver()
        deps = resolver.extract_from_code("# import notreal\nimport os\n")
        names = {d.module_name for d in deps}
        assert "import" not in names

    def test_extract_submodule(self):
        resolver = DependencyResolver()
        deps = resolver.extract_from_code(
            "import urllib.parse\nimport http.client\n"
        )
        names = {d.module_name for d in deps}
        # urllib.parse 的根模块是 urllib
        assert "urllib" in names
        assert "http" in names

    def test_extract_mixed_code_and_imports(self):
        resolver = DependencyResolver()
        code = '''
import requests
from typing import Dict

def main():
    import os
    pass
'''
        deps = resolver.extract_from_code(code)
        names = {d.module_name for d in deps}
        assert "requests" in names
        assert "typing" in names
        assert "os" in names  # 函数内的 import 也能提取


class TestDependencyResolverMapping:
    """模块映射测试"""

    def test_map_known_package(self):
        resolver = DependencyResolver()
        assert resolver._map_to_package("requests") == "requests"
        assert resolver._map_to_package("numpy") == "numpy"
        assert resolver._map_to_package("PIL") == "Pillow"
        assert resolver._map_to_package("bs4") == "beautifulsoup4"
        assert resolver._map_to_package("sklearn") == "scikit-learn"

    def test_map_unknown_package(self):
        """未知模块保持原名"""
        resolver = DependencyResolver()
        assert resolver._map_to_package("mypackage") == "mypackage"
        assert resolver._map_to_package("some_weird_lib") == "some_weird_lib"


class TestDependencyResolverStandardLib:
    """标准库检查测试"""

    def test_is_standard_lib_positive(self):
        resolver = DependencyResolver()
        for lib in ["os", "sys", "json", "re", "pathlib", "typing", "datetime"]:
            assert resolver._is_standard_lib(lib) is True, f"{lib} should be stdlib"

    def test_is_standard_lib_negative(self):
        resolver = DependencyResolver()
        for lib in ["requests", "numpy", "pandas", "pytest", "rich"]:
            assert resolver._is_standard_lib(lib) is False, f"{lib} should NOT be stdlib"

    def test_stdlib_submodules(self):
        resolver = DependencyResolver()
        # urllib.parse 的根是 urllib
        assert resolver._is_standard_lib("urllib") is True
        # collections.abc 的根是 collections
        assert resolver._is_standard_lib("collections") is True


class TestDependencyResolverCheck:
    """check_installed / check_dependencies 测试"""

    def test_check_installed_cached(self):
        resolver = DependencyResolver()
        resolver._package_cache["pytest"] = True
        assert resolver.check_installed("pytest") is True

    @patch("subprocess.run")
    def test_check_installed_not_cached(self, mock_run: MagicMock):
        mock_run.return_value = MagicMock(returncode=0)
        resolver = DependencyResolver()
        result = resolver.check_installed("new-package")
        assert result is True
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_check_installed_missing(self, mock_run: MagicMock):
        mock_run.return_value = MagicMock(returncode=1)
        resolver = DependencyResolver()
        result = resolver.check_installed("definitely-not-installed")
        assert result is False

    @patch("subprocess.run")
    def test_check_dependencies(self, mock_run: MagicMock):
        mock_run.return_value = MagicMock(returncode=0)
        resolver = DependencyResolver()
        deps = [
            DependencyInfo("os", "os", is_standard_lib=True),
            DependencyInfo("requests", "requests"),
            DependencyInfo("numpy", "numpy"),
        ]
        result = resolver.check_dependencies(deps)

        # os 是标准库，不计入 needed
        assert len(result.needed) == 2
        assert result.installed[0].module_name == "requests"
        assert result.installed[1].module_name == "numpy"

    @patch("subprocess.run")
    def test_check_dependencies_with_missing(self, mock_run: MagicMock):
        def side_effect(*args, **kwargs):
            cmd = args[0] if args else kwargs.get("args", [])
            if isinstance(cmd, list):
                pkg = cmd[-1] if cmd else ""
                mock = MagicMock()
                mock.returncode = 0 if pkg == "requests" else 1
                return mock
            return MagicMock(returncode=1)

        mock_run.side_effect = side_effect
        resolver = DependencyResolver()
        deps = [
            DependencyInfo("requests", "requests"),
            DependencyInfo("missing-pkg", "missing-pkg"),
        ]
        result = resolver.check_dependencies(deps)
        assert len(result.installed) >= 1
        assert len(result.missing) >= 1


class TestDependencyResolverInstall:
    """install_missing 测试"""

    @patch("subprocess.run")
    def test_install_success(self, mock_run: MagicMock):
        mock_run.return_value = MagicMock(returncode=0, stderr=b"")
        resolver = DependencyResolver()
        deps = [DependencyInfo("httpx", "httpx")]
        result = resolver.install_missing(deps, quiet=True)

        assert len(result.installed) == 1
        assert len(result.failed) == 0
        assert len(result.missing) == 0

    @patch("subprocess.run")
    def test_install_failure(self, mock_run: MagicMock):
        mock_run.return_value = MagicMock(
            returncode=1, stderr=b"error: install failed"
        )
        resolver = DependencyResolver()
        deps = [DependencyInfo("broken-pkg", "broken-pkg")]
        result = resolver.install_missing(deps, quiet=True)

        assert len(result.failed) == 1
        assert result.failed[0][0] == "broken-pkg"
        assert "error" in result.failed[0][1].lower()

    @patch("subprocess.run")
    def test_install_timeout(self, mock_run: MagicMock):
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired("cmd", 120)
        resolver = DependencyResolver()
        deps = [DependencyInfo("slow-pkg", "slow-pkg")]
        result = resolver.install_missing(deps)

        assert len(result.failed) == 1
        assert "timeout" in result.failed[0][1].lower()


class TestDependencyResolverResolve:
    """resolve 完整流程测试"""

    @patch("subprocess.run")
    def test_resolve_full_flow(self, mock_run: MagicMock):
        # pip show 返回未安装（returncode=1），pip install 返回成功
        def run_side_effect(*args, **kwargs):
            cmd = args[0] if args else []
            if isinstance(cmd, list) and "install" in cmd:
                return MagicMock(returncode=0, stderr=b"")
            return MagicMock(returncode=1, stderr=b"not found")

        mock_run.side_effect = run_side_effect
        resolver = DependencyResolver()
        code = "import rich\nimport pytest\n"
        result = resolver.resolve(code, auto_install=True)

        # rich 和 pytest 都是第三方库，不是标准库
        # 都应该被识别为需要但缺失
        assert len(result.needed) == 2
        pkg_names = {d.package_name for d in result.needed}
        assert "rich" in pkg_names
        assert "pytest" in pkg_names

    @patch("subprocess.run")
    def test_resolve_no_auto_install(self, mock_run: MagicMock):
        # pip show 返回未安装
        mock_run.return_value = MagicMock(returncode=1, stderr=b"not found")
        resolver = DependencyResolver()
        code = "import rich\n"
        result = resolver.resolve(code, auto_install=False)

        assert len(result.missing) >= 1
        # auto_install=False 时，missing 不被安装，installed 为空
        assert len(result.installed) == 0

    def test_resolve_auto_install_false_uses_cached(self):
        """auto_install=False 时不触发 subprocess 调用"""
        resolver = DependencyResolver()
        # 缓存 rich 为已安装
        resolver._package_cache["rich"] = True
        code = "import rich\n"
        result = resolver.resolve(code, auto_install=False)

        assert len(result.installed) == 1
        assert result.installed[0].package_name == "rich"
        assert len(result.missing) == 0


class TestModuleToPackageMapping:
    """MODULE_TO_PACKAGE 映射完整性测试"""

    def test_key_mappings(self):
        assert MODULE_TO_PACKAGE["requests"] == "requests"
        assert MODULE_TO_PACKAGE["bs4"] == "beautifulsoup4"
        assert MODULE_TO_PACKAGE["PIL"] == "Pillow"  # 注意大写 P
        assert MODULE_TO_PACKAGE["sklearn"] == "scikit-learn"
        assert MODULE_TO_PACKAGE["yaml"] == "pyyaml"
        assert MODULE_TO_PACKAGE["dotenv"] == "python-dotenv"
        assert MODULE_TO_PACKAGE["tqdm"] == "tqdm"


class TestGlobalFunctions:
    """全局便利函数测试"""

    def test_resolve_dependencies_function(self):
        """resolve_dependencies 是 get_resolver().resolve 的包装"""
        with patch.object(DependencyResolver, "resolve") as mock_resolve:
            mock_resolve.return_value = ResolutionResult()
            result = resolve_dependencies("import os\n")
            mock_resolve.assert_called_once_with("import os\n", True)

    def test_get_resolver_singleton(self):
        """get_resolver 返回单例"""
        r1 = get_resolver()
        r2 = get_resolver()
        assert r1 is r2
        # 重置单例以便后续测试不受影响
        import src.core.dependency_resolver as dr
        dr._default_resolver = None
