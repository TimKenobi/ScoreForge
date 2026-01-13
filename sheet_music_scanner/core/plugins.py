"""
Plugin Architecture - Extensible plugin system for OMR engines, exporters, etc.

Provides a framework for loading and managing plugins from external packages.
"""

from __future__ import annotations

import importlib
import importlib.util
import json
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional, Dict, Any, Type, TypeVar
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class PluginType(Enum):
    """Types of plugins supported."""
    OMR_ENGINE = "omr_engine"
    EXPORTER = "exporter"
    IMPORTER = "importer"
    EFFECT = "effect"
    TOOL = "tool"


@dataclass
class PluginInfo:
    """Information about a plugin."""
    id: str
    name: str
    version: str
    description: str
    author: str
    plugin_type: PluginType
    module_path: str
    class_name: str
    enabled: bool = True
    config: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.config is None:
            self.config = {}
    
    def to_dict(self) -> dict:
        data = asdict(self)
        data["plugin_type"] = self.plugin_type.value
        return data
    
    @classmethod
    def from_dict(cls, data: dict) -> 'PluginInfo':
        data["plugin_type"] = PluginType(data.get("plugin_type", "tool"))
        return cls(**data)


class Plugin(ABC):
    """Base class for all plugins."""
    
    @classmethod
    @abstractmethod
    def get_info(cls) -> PluginInfo:
        """Return plugin information."""
        pass
    
    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the plugin with configuration."""
        pass
    
    def cleanup(self) -> None:
        """Clean up plugin resources."""
        pass


class OMREnginePlugin(Plugin):
    """Base class for OMR engine plugins."""
    
    @abstractmethod
    def process_image(self, image_path: Path) -> Any:
        """
        Process an image and return a Score.
        
        Args:
            image_path: Path to input image
            
        Returns:
            Score object or music21 Score
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the engine's dependencies are available."""
        pass
    
    def get_supported_formats(self) -> List[str]:
        """Get supported image formats."""
        return ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']


class ExporterPlugin(Plugin):
    """Base class for exporter plugins."""
    
    @abstractmethod
    def export(self, score: Any, output_path: Path, **options) -> Path:
        """
        Export a score to file.
        
        Args:
            score: Score object to export
            output_path: Output file path
            **options: Export options
            
        Returns:
            Path to exported file
        """
        pass
    
    @abstractmethod
    def get_file_extension(self) -> str:
        """Get the file extension for this format."""
        pass
    
    def get_format_name(self) -> str:
        """Get human-readable format name."""
        return self.get_info().name


class ImporterPlugin(Plugin):
    """Base class for importer plugins."""
    
    @abstractmethod
    def import_file(self, file_path: Path) -> Any:
        """
        Import a file and return a Score.
        
        Args:
            file_path: Path to input file
            
        Returns:
            Score object
        """
        pass
    
    @abstractmethod
    def get_supported_extensions(self) -> List[str]:
        """Get supported file extensions."""
        pass


class EffectPlugin(Plugin):
    """Base class for effect plugins (score transformations)."""
    
    @abstractmethod
    def apply(self, score: Any, **options) -> Any:
        """
        Apply effect to score.
        
        Args:
            score: Input score
            **options: Effect options
            
        Returns:
            Modified score
        """
        pass
    
    def get_options(self) -> Dict[str, Any]:
        """Get available options and their defaults."""
        return {}


class ToolPlugin(Plugin):
    """Base class for tool plugins (UI tools, utilities)."""
    
    @abstractmethod
    def execute(self, context: Dict[str, Any]) -> Any:
        """
        Execute the tool.
        
        Args:
            context: Execution context with score, UI references, etc.
            
        Returns:
            Tool result
        """
        pass
    
    def get_menu_location(self) -> Optional[str]:
        """Get menu path for this tool (e.g., 'Tools/My Tool')."""
        return None
    
    def get_shortcut(self) -> Optional[str]:
        """Get keyboard shortcut."""
        return None


T = TypeVar('T', bound=Plugin)


class PluginManager:
    """
    Manages plugin discovery, loading, and lifecycle.
    
    Features:
    - Discover plugins from directory
    - Load plugins dynamically
    - Plugin enable/disable
    - Plugin configuration
    - Type-safe plugin retrieval
    """
    
    def __init__(self, plugins_dir: Optional[Path] = None):
        """
        Initialize plugin manager.
        
        Args:
            plugins_dir: Directory containing plugins
        """
        self._plugins_dir = plugins_dir
        self._plugins: Dict[str, Plugin] = {}
        self._plugin_info: Dict[str, PluginInfo] = {}
        self._config_file: Optional[Path] = None
        
        if plugins_dir:
            plugins_dir.mkdir(parents=True, exist_ok=True)
            self._config_file = plugins_dir / "plugins.json"
            self._load_config()
    
    def discover_plugins(self) -> List[PluginInfo]:
        """
        Discover available plugins.
        
        Returns:
            List of discovered plugin info
        """
        if not self._plugins_dir:
            return []
        
        discovered = []
        
        # Look for plugin packages
        for item in self._plugins_dir.iterdir():
            if item.is_dir() and (item / "__init__.py").exists():
                # Try to load plugin manifest
                manifest_path = item / "plugin.json"
                if manifest_path.exists():
                    try:
                        with open(manifest_path, 'r') as f:
                            manifest = json.load(f)
                        
                        info = PluginInfo(
                            id=manifest["id"],
                            name=manifest["name"],
                            version=manifest.get("version", "1.0.0"),
                            description=manifest.get("description", ""),
                            author=manifest.get("author", "Unknown"),
                            plugin_type=PluginType(manifest.get("type", "tool")),
                            module_path=str(item / manifest.get("module", "__init__.py")),
                            class_name=manifest.get("class", "Plugin"),
                        )
                        
                        discovered.append(info)
                        logger.info(f"Discovered plugin: {info.name}")
                        
                    except Exception as e:
                        logger.warning(f"Failed to load plugin manifest {manifest_path}: {e}")
        
        return discovered
    
    def load_plugin(self, info: PluginInfo) -> Optional[Plugin]:
        """
        Load a plugin.
        
        Args:
            info: Plugin information
            
        Returns:
            Loaded plugin instance, or None if failed
        """
        if info.id in self._plugins:
            return self._plugins[info.id]
        
        try:
            # Load the module
            spec = importlib.util.spec_from_file_location(
                f"plugin_{info.id}",
                info.module_path
            )
            if not spec or not spec.loader:
                raise ImportError(f"Cannot load module: {info.module_path}")
            
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
            
            # Get the plugin class
            plugin_class = getattr(module, info.class_name)
            
            # Create instance
            plugin = plugin_class()
            
            # Initialize with config
            plugin.initialize(info.config)
            
            # Store
            self._plugins[info.id] = plugin
            self._plugin_info[info.id] = info
            
            logger.info(f"Loaded plugin: {info.name} v{info.version}")
            return plugin
            
        except Exception as e:
            logger.exception(f"Failed to load plugin {info.id}: {e}")
            return None
    
    def unload_plugin(self, plugin_id: str) -> bool:
        """
        Unload a plugin.
        
        Args:
            plugin_id: Plugin ID
            
        Returns:
            True if unloaded
        """
        if plugin_id not in self._plugins:
            return False
        
        try:
            plugin = self._plugins[plugin_id]
            plugin.cleanup()
            del self._plugins[plugin_id]
            logger.info(f"Unloaded plugin: {plugin_id}")
            return True
        except Exception as e:
            logger.error(f"Error unloading plugin {plugin_id}: {e}")
            return False
    
    def get_plugin(self, plugin_id: str) -> Optional[Plugin]:
        """Get a loaded plugin by ID."""
        return self._plugins.get(plugin_id)
    
    def get_plugins_by_type(self, plugin_type: PluginType) -> List[Plugin]:
        """Get all plugins of a specific type."""
        result = []
        for plugin_id, info in self._plugin_info.items():
            if info.plugin_type == plugin_type and plugin_id in self._plugins:
                result.append(self._plugins[plugin_id])
        return result
    
    def get_omr_engines(self) -> List[OMREnginePlugin]:
        """Get all OMR engine plugins."""
        return [p for p in self.get_plugins_by_type(PluginType.OMR_ENGINE)
                if isinstance(p, OMREnginePlugin)]
    
    def get_exporters(self) -> List[ExporterPlugin]:
        """Get all exporter plugins."""
        return [p for p in self.get_plugins_by_type(PluginType.EXPORTER)
                if isinstance(p, ExporterPlugin)]
    
    def get_importers(self) -> List[ImporterPlugin]:
        """Get all importer plugins."""
        return [p for p in self.get_plugins_by_type(PluginType.IMPORTER)
                if isinstance(p, ImporterPlugin)]
    
    def enable_plugin(self, plugin_id: str) -> bool:
        """Enable a plugin."""
        if plugin_id in self._plugin_info:
            self._plugin_info[plugin_id].enabled = True
            self._save_config()
            return True
        return False
    
    def disable_plugin(self, plugin_id: str) -> bool:
        """Disable a plugin."""
        if plugin_id in self._plugin_info:
            self._plugin_info[plugin_id].enabled = False
            self.unload_plugin(plugin_id)
            self._save_config()
            return True
        return False
    
    def set_plugin_config(self, plugin_id: str, config: Dict[str, Any]) -> None:
        """Set plugin configuration."""
        if plugin_id in self._plugin_info:
            self._plugin_info[plugin_id].config = config
            
            # Re-initialize if loaded
            if plugin_id in self._plugins:
                self._plugins[plugin_id].initialize(config)
            
            self._save_config()
    
    @property
    def loaded_plugins(self) -> Dict[str, Plugin]:
        """Get all loaded plugins."""
        return self._plugins.copy()
    
    @property
    def all_plugin_info(self) -> List[PluginInfo]:
        """Get info for all known plugins."""
        return list(self._plugin_info.values())
    
    def _load_config(self) -> None:
        """Load plugin configuration."""
        if not self._config_file or not self._config_file.exists():
            return
        
        try:
            with open(self._config_file, 'r') as f:
                data = json.load(f)
            
            for plugin_data in data.get("plugins", []):
                info = PluginInfo.from_dict(plugin_data)
                self._plugin_info[info.id] = info
                
        except Exception as e:
            logger.warning(f"Failed to load plugin config: {e}")
    
    def _save_config(self) -> None:
        """Save plugin configuration."""
        if not self._config_file:
            return
        
        try:
            data = {
                "plugins": [info.to_dict() for info in self._plugin_info.values()]
            }
            with open(self._config_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save plugin config: {e}")
    
    def cleanup(self) -> None:
        """Cleanup all plugins."""
        for plugin_id in list(self._plugins.keys()):
            self.unload_plugin(plugin_id)


# Singleton instance
_plugin_manager: Optional[PluginManager] = None


def get_plugin_manager() -> PluginManager:
    """Get the global plugin manager."""
    global _plugin_manager
    if _plugin_manager is None:
        from sheet_music_scanner.config import get_config
        config = get_config()
        _plugin_manager = PluginManager(
            plugins_dir=config._config_dir / "plugins"
        )
    return _plugin_manager
