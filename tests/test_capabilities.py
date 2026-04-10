"""
能力包系统测试

测试 CapabilityPackage 和 CapabilityPackageManager 的功能。
"""

import json
import tempfile
from pathlib import Path

import pytest

from src.capabilities.package import (
    CapabilityPackage,
    CapabilityPackageManager,
)


class TestCapabilityPackage:
    """测试 CapabilityPackage 数据类"""
    
    def test_create_package(self):
        """测试创建能力包"""
        package = CapabilityPackage(
            name="test-package",
            version="1.0.0",
            description="测试能力包",
            author="tester",
            created_at="2024-01-01T00:00:00",
            tags=["test", "demo"],
            agents={"explore": {"tier": "medium"}},
            model_config={"temperature": 0.7},
            tools=["file_read", "file_write"],
            prompts={"system": "You are a test agent."},
            readme="# Test Package",
            examples=[{"input": "test", "output": "result"}],
        )
        
        assert package.name == "test-package"
        assert package.version == "1.0.0"
        assert package.description == "测试能力包"
        assert package.author == "tester"
        assert len(package.tags) == 2
        assert "test" in package.tags
    
    def test_save_and_load(self, tmp_path):
        """测试保存和加载能力包"""
        package = CapabilityPackage(
            name="test-save",
            version="1.0.0",
            description="测试保存",
            author="tester",
            created_at="2024-01-01T00:00:00",
            tags=["save"],
            agents={},
            model_config={},
            tools=[],
            prompts={},
        )
        
        file_path = tmp_path / "test.json"
        package.save(file_path)
        
        assert file_path.exists()
        
        loaded = CapabilityPackage.load(file_path)
        assert loaded.name == package.name
        assert loaded.version == package.version
        assert loaded.description == package.description
    
    def test_to_dict_and_from_dict(self):
        """测试字典转换"""
        package = CapabilityPackage(
            name="test-dict",
            version="1.0.0",
            description="测试字典转换",
            author="tester",
            created_at="2024-01-01T00:00:00",
            tags=["dict"],
            agents={"agent1": {}},
            model_config={"model": "test"},
            tools=["tool1"],
            prompts={"prompt1": "hello"},
        )
        
        data = package.to_dict()
        assert data["name"] == "test-dict"
        assert data["version"] == "1.0.0"
        
        restored = CapabilityPackage.from_dict(data)
        assert restored.name == package.name
        assert restored.version == package.version
    
    def test_validate_valid_package(self):
        """测试验证有效的能力包"""
        package = CapabilityPackage(
            name="valid-package",
            version="1.0.0",
            description="有效的能力包",
            author="tester",
            created_at="2024-01-01T00:00:00",
        )
        
        errors = package.validate()
        assert len(errors) == 0
    
    def test_validate_invalid_package(self):
        """测试验证无效的能力包"""
        package = CapabilityPackage(
            name="",
            version="invalid",
            description="",
            author="",
            created_at="",
        )
        
        errors = package.validate()
        assert len(errors) > 0
        assert any("名称" in e or "name" in e.lower() for e in errors)
        assert any("版本" in e or "version" in e.lower() for e in errors)


class TestCapabilityPackageManager:
    """测试 CapabilityPackageManager 管理器"""
    
    @pytest.fixture
    def manager(self, tmp_path):
        """创建临时管理器"""
        return CapabilityPackageManager(packages_dir=tmp_path / "capabilities")
    
    def test_init_creates_directory(self, tmp_path):
        """测试初始化创建目录"""
        packages_dir = tmp_path / "new_capabilities"
        manager = CapabilityPackageManager(packages_dir=packages_dir)
        
        assert packages_dir.exists()
        assert packages_dir.is_dir()
    
    def test_save_and_get_package(self, manager):
        """测试保存和获取能力包"""
        package = CapabilityPackage(
            name="test-save-get",
            version="1.0.0",
            description="测试保存和获取",
            author="tester",
            created_at="2024-01-01T00:00:00",
        )
        
        manager.save_package(package)
        
        retrieved = manager.get_package("test-save-get")
        assert retrieved is not None
        assert retrieved.name == "test-save-get"
        assert retrieved.version == "1.0.0"
    
    def test_get_nonexistent_package(self, manager):
        """测试获取不存在的能力包"""
        result = manager.get_package("nonexistent")
        assert result is None
    
    def test_list_packages(self, manager):
        """测试列出能力包"""
        # 创建几个能力包
        for i in range(3):
            package = CapabilityPackage(
                name=f"pkg-{i}",
                version=f"1.0.{i}",
                description=f"Package {i}",
                author="tester",
                created_at=f"2024-01-0{i+1}T00:00:00",
            )
            manager.save_package(package)
        
        packages = manager.list_packages()
        assert len(packages) == 3
        # 应该按创建时间倒序排列
        assert packages[0].name == "pkg-2"
    
    def test_list_packages_empty(self, manager):
        """测试空目录列出"""
        packages = manager.list_packages()
        assert len(packages) == 0
    
    def test_delete_package(self, manager):
        """测试删除能力包"""
        package = CapabilityPackage(
            name="to-delete",
            version="1.0.0",
            description="将被删除",
            author="tester",
            created_at="2024-01-01T00:00:00",
        )
        
        manager.save_package(package)
        assert manager.get_package("to-delete") is not None
        
        result = manager.delete_package("to-delete")
        assert result is True
        assert manager.get_package("to-delete") is None
    
    def test_delete_nonexistent_package(self, manager):
        """测试删除不存在的能力包"""
        result = manager.delete_package("nonexistent")
        assert result is False
    
    def test_export_from_config(self, manager):
        """测试从配置导出"""
        package = manager.export_from_config(
            name="exported",
            version="1.0.0",
            description="导出的配置",
            author="tester",
            tags=["export", "test"],
            agents={"explore": {"tier": "medium"}},
            model_config={"temperature": 0.7},
            tools=["file_read"],
            prompts={"system": "Hello"},
        )
        
        assert package.name == "exported"
        assert package.version == "1.0.0"
        assert len(package.tags) == 2
        
        # 验证已保存
        assert manager.get_package("exported") is not None
    
    def test_sanitize_model_config(self, manager):
        """测试敏感信息脱敏"""
        config = {
            "api_key": "sk-1234567890abcdef",
            "api_secret": "secret123456",
            "normal_key": "normal_value",
            "password": "mysecretpassword",
            "token": "bearer_token_12345",
        }
        
        sanitized = manager._sanitize_model_config(config)
        
        # 敏感信息应该被脱敏
        assert sanitized["api_key"] == "sk-1***cdef"
        assert sanitized["api_secret"] == "secr***3456"
        assert sanitized["password"] == "myse***word"
        assert sanitized["token"] == "bear***2345"
        
        # 普通信息保持不变
        assert sanitized["normal_key"] == "normal_value"
    
    def test_apply_package(self, manager):
        """测试应用能力包"""
        # 创建能力包
        package = CapabilityPackage(
            name="to-apply",
            version="1.0.0",
            description="待应用",
            author="tester",
            created_at="2024-01-01T00:00:00",
            agents={"new_agent": {"tier": "high"}},
            model_config={"temperature": 0.5},
            tools=["new_tool"],
            prompts={"custom": "prompt"},
        )
        manager.save_package(package)
        
        # 应用配置
        target_config = {
            "agents": {"existing": {}},
            "tools": ["existing_tool"],
        }
        
        result = manager.apply_package("to-apply", target_config)
        
        assert "new_agent" in result["agents"]
        assert "existing" in result["agents"]
        assert "new_tool" in result["tools"]
        assert "existing_tool" in result["tools"]
        assert result["model_config"]["temperature"] == 0.5
        assert result["prompts"]["custom"] == "prompt"
    
    def test_apply_nonexistent_package(self, manager):
        """测试应用不存在的能力包"""
        with pytest.raises(ValueError) as exc_info:
            manager.apply_package("nonexistent")
        
        assert "nonexistent" in str(exc_info.value)


class TestCapabilityPackageIntegration:
    """集成测试"""
    
    def test_full_workflow(self, tmp_path):
        """测试完整工作流程"""
        manager = CapabilityPackageManager(packages_dir=tmp_path / "caps")
        
        # 1. 导出配置
        package = manager.export_from_config(
            name="my-workflow",
            version="1.0.0",
            description="我的工作流配置",
            author="developer",
            tags=["python", "web"],
            agents={
                "explore": {"tier": "medium"},
                "planner": {"tier": "high"},
            },
            model_config={
                "default_model": "deepseek",
                "temperature": 0.7,
            },
            tools=["file_read", "shell_exec", "web_search"],
            prompts={
                "system": "You are a Python expert.",
            },
        )
        
        # 2. 验证导出
        assert manager.get_package("my-workflow") is not None
        
        # 3. 列出能力包
        packages = manager.list_packages()
        assert len(packages) == 1
        
        # 4. 应用配置
        target_config = {"agents": {}, "tools": []}
        result = manager.apply_package("my-workflow", target_config)
        
        assert "explore" in result["agents"]
        assert "planner" in result["agents"]
        assert len(result["tools"]) == 3
        
        # 5. 删除能力包
        manager.delete_package("my-workflow")
        assert manager.get_package("my-workflow") is None
    
    def test_json_format(self, tmp_path):
        """测试 JSON 格式正确性"""
        manager = CapabilityPackageManager(packages_dir=tmp_path / "caps")
        
        package = manager.export_from_config(
            name="json-test",
            version="2.0.0",
            description="测试 JSON 格式",
            author="tester",
            tags=["json"],
            agents={},
            model_config={},
            tools=[],
            prompts={},
        )
        
        # 读取 JSON 文件验证格式
        json_path = tmp_path / "caps" / "json-test.json"
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert data["name"] == "json-test"
        assert data["version"] == "2.0.0"
        assert "created_at" in data
        assert "tags" in data
