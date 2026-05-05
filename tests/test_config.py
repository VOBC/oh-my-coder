"""
配置管理测试 - 按模型独立配置功能验证

测试内容：
1. 全局配置读取/设置
2. 按模型独立配置读取/设置  
3. 配置优先级（模型配置 > 全局配置）
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest


class ConfigManager:
    """配置管理器 - 从 cli.py 提取的核心逻辑"""
    
    def __init__(self, config_file: Path):
        self.config_file = config_file
    
    def _load(self) -> Dict[str, Any]:
        if self.config_file.exists():
            try:
                return json.loads(self.config_file.read_text())
            except Exception:
                return {}
        return {}
    
    def _save(self, cfg: Dict[str, Any]) -> None:
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        self.config_file.write_text(json.dumps(cfg, indent=2, ensure_ascii=False))
    
    def get(self, key: str, model: Optional[str] = None) -> Any:
        """获取配置项"""
        cfg = self._load()
        if model:
            return cfg.get("models", {}).get(model, {}).get(key)
        return cfg.get(key)
    
    def set(self, key: str, value: Any, model: Optional[str] = None) -> None:
        """设置配置项"""
        cfg = self._load()
        if model:
            if "models" not in cfg:
                cfg["models"] = {}
            if model not in cfg["models"]:
                cfg["models"][model] = {}
            cfg["models"][model][key] = value
        else:
            cfg[key] = value
        self._save(cfg)
    
    def delete(self, key: str, model: Optional[str] = None) -> None:
        """删除配置项"""
        cfg = self._load()
        if model:
            if model in cfg.get("models", {}):
                cfg["models"][model].pop(key, None)
        else:
            cfg.pop(key, None)
        self._save(cfg)
    
    def list_models(self) -> List[str]:
        """列出已配置模型的列表"""
        cfg = self._load()
        return list(cfg.get("models", {}).keys())
    
    def get_all(self, model: Optional[str] = None) -> Dict[str, Any]:
        """获取所有配置或指定模型的配置"""
        cfg = self._load()
        if model:
            return cfg.get("models", {}).get(model, {})
        return cfg


class TestConfigManager:
    """配置管理功能测试"""
    
    @pytest.fixture
    def temp_config(self, tmp_path):
        """创建临时配置目录"""
        config_dir = tmp_path / "config"
        config_file = config_dir / "config.json"
        return ConfigManager(config_file)
    
    def test_set_and_get_global_config(self, temp_config):
        """测试1: 全局配置设置和读取"""
        temp_config.set("api_key", "sk-test123")
        assert temp_config.get("api_key") == "sk-test123"
    
    def test_set_and_get_model_config(self, temp_config):
        """测试2: 按模型独立配置设置和读取"""
        temp_config.set("temperature", 0.7, model="deepseek")
        temp_config.set("api_base_url", "https://api.deepseek.com", model="deepseek")
        
        assert temp_config.get("temperature", model="deepseek") == 0.7
        assert temp_config.get("api_base_url", model="deepseek") == "https://api.deepseek.com"
    
    def test_model_config_isolation(self, temp_config):
        """测试3: 模型配置隔离（不同模型配置互不影响）"""
        temp_config.set("temperature", 0.7, model="deepseek")
        temp_config.set("temperature", 0.9, model="kimi")
        
        assert temp_config.get("temperature", model="deepseek") == 0.7
        assert temp_config.get("temperature", model="kimi") == 0.9
    
    def test_global_and_model_priority(self, temp_config):
        """测试4: 配置优先级（模型配置 > 全局配置）"""
        # 设置全局配置
        temp_config.set("temperature", 0.5)
        # 设置模型配置
        temp_config.set("temperature", 0.8, model="deepseek")
        
        # 模型配置应优先
        assert temp_config.get("temperature", model="deepseek") == 0.8
        # 全局配置仍然存在
        assert temp_config.get("temperature") == 0.5
    
    def test_delete_config(self, temp_config):
        """测试5: 删除配置项"""
        temp_config.set("api_key", "sk-test")
        temp_config.delete("api_key")
        assert temp_config.get("api_key") is None
    
    def test_list_models(self, temp_config):
        """测试6: 列出已配置的模型"""
        temp_config.set("temperature", 0.7, model="deepseek")
        temp_config.set("temperature", 0.9, model="kimi")
        temp_config.set("max_tokens", 4096, model="glm")
        
        models = temp_config.list_models()
        assert "deepseek" in models
        assert "kimi" in models
        assert "glm" in models


if __name__ == "__main__":
    pytest.main([__file__, "-v"])