"""
Template System - Pre-defined and custom score templates.

Provides templates for common score layouts like Lead Sheet,
Piano Score, SATB Choir, etc.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional, Dict, Any
from enum import Enum
import logging

from music21 import stream, clef, meter, key, tempo, instrument

logger = logging.getLogger(__name__)


class TemplateCategory(Enum):
    """Template categories."""
    SOLO = "Solo"
    KEYBOARD = "Keyboard"
    VOCAL = "Vocal"
    ENSEMBLE = "Ensemble"
    ORCHESTRAL = "Orchestral"
    CUSTOM = "Custom"


@dataclass
class PartTemplate:
    """Template for a single part/staff."""
    name: str
    clef: str = "treble"  # treble, bass, alto, tenor
    instrument: str = ""  # music21 instrument name
    midi_program: int = 0  # MIDI program number
    transpose: int = 0  # Transposition in semitones
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'PartTemplate':
        return cls(**data)


@dataclass
class ScoreTemplate:
    """Template for a complete score."""
    name: str
    description: str
    category: TemplateCategory
    time_signature: str = "4/4"
    key_signature: str = "C major"
    tempo_bpm: int = 120
    parts: List[PartTemplate] = None
    is_builtin: bool = True
    
    def __post_init__(self):
        if self.parts is None:
            self.parts = []
    
    def to_dict(self) -> dict:
        data = {
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "time_signature": self.time_signature,
            "key_signature": self.key_signature,
            "tempo_bpm": self.tempo_bpm,
            "parts": [p.to_dict() for p in self.parts],
            "is_builtin": self.is_builtin,
        }
        return data
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ScoreTemplate':
        parts = [PartTemplate.from_dict(p) for p in data.get("parts", [])]
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            category=TemplateCategory(data.get("category", "Custom")),
            time_signature=data.get("time_signature", "4/4"),
            key_signature=data.get("key_signature", "C major"),
            tempo_bpm=data.get("tempo_bpm", 120),
            parts=parts,
            is_builtin=data.get("is_builtin", False),
        )
    
    def create_score(self) -> stream.Score:
        """Create a music21 Score from this template."""
        s = stream.Score()
        
        # Set metadata
        s.metadata = stream.metadata.Metadata()
        s.metadata.title = self.name
        
        # Add tempo
        mm = tempo.MetronomeMark(number=self.tempo_bpm)
        
        # Add parts
        for part_template in self.parts:
            p = stream.Part()
            p.partName = part_template.name
            
            # Set instrument
            if part_template.instrument:
                try:
                    instr_class = getattr(instrument, part_template.instrument, None)
                    if instr_class:
                        p.insert(0, instr_class())
                except Exception:
                    pass
            
            # Create first measure with time sig, key sig, clef
            m = stream.Measure(number=1)
            
            # Add clef
            clef_map = {
                "treble": clef.TrebleClef(),
                "bass": clef.BassClef(),
                "alto": clef.AltoClef(),
                "tenor": clef.TenorClef(),
            }
            m.append(clef_map.get(part_template.clef, clef.TrebleClef()))
            
            # Add time signature
            m.append(meter.TimeSignature(self.time_signature))
            
            # Add key signature
            try:
                ks = key.Key(self.key_signature)
                m.append(ks)
            except Exception:
                m.append(key.Key('C'))
            
            # Add tempo to first part only
            if len(s.parts) == 0:
                m.insert(0, mm)
            
            p.append(m)
            s.append(p)
        
        return s


# Built-in templates
BUILTIN_TEMPLATES = [
    ScoreTemplate(
        name="Blank Score",
        description="Empty single-staff score",
        category=TemplateCategory.SOLO,
        parts=[
            PartTemplate(name="Part 1", clef="treble"),
        ]
    ),
    ScoreTemplate(
        name="Lead Sheet",
        description="Single staff with chord symbols",
        category=TemplateCategory.SOLO,
        parts=[
            PartTemplate(name="Melody", clef="treble"),
        ]
    ),
    ScoreTemplate(
        name="Piano Score",
        description="Grand staff for piano",
        category=TemplateCategory.KEYBOARD,
        parts=[
            PartTemplate(name="Piano RH", clef="treble", instrument="Piano"),
            PartTemplate(name="Piano LH", clef="bass", instrument="Piano"),
        ]
    ),
    ScoreTemplate(
        name="Piano + Vocal",
        description="Vocal line with piano accompaniment",
        category=TemplateCategory.VOCAL,
        parts=[
            PartTemplate(name="Vocal", clef="treble", instrument="Vocalist"),
            PartTemplate(name="Piano RH", clef="treble", instrument="Piano"),
            PartTemplate(name="Piano LH", clef="bass", instrument="Piano"),
        ]
    ),
    ScoreTemplate(
        name="SATB Choir",
        description="Four-part vocal harmony",
        category=TemplateCategory.VOCAL,
        parts=[
            PartTemplate(name="Soprano", clef="treble", instrument="Soprano"),
            PartTemplate(name="Alto", clef="treble", instrument="Alto"),
            PartTemplate(name="Tenor", clef="treble", instrument="Tenor"),  # Treble 8vb
            PartTemplate(name="Bass", clef="bass", instrument="Bass"),
        ]
    ),
    ScoreTemplate(
        name="SATB + Piano",
        description="Choir with piano accompaniment",
        category=TemplateCategory.VOCAL,
        parts=[
            PartTemplate(name="Soprano", clef="treble", instrument="Soprano"),
            PartTemplate(name="Alto", clef="treble", instrument="Alto"),
            PartTemplate(name="Tenor", clef="treble", instrument="Tenor"),
            PartTemplate(name="Bass", clef="bass", instrument="Bass"),
            PartTemplate(name="Piano RH", clef="treble", instrument="Piano"),
            PartTemplate(name="Piano LH", clef="bass", instrument="Piano"),
        ]
    ),
    ScoreTemplate(
        name="String Quartet",
        description="Two violins, viola, cello",
        category=TemplateCategory.ENSEMBLE,
        parts=[
            PartTemplate(name="Violin I", clef="treble", instrument="Violin"),
            PartTemplate(name="Violin II", clef="treble", instrument="Violin"),
            PartTemplate(name="Viola", clef="alto", instrument="Viola"),
            PartTemplate(name="Cello", clef="bass", instrument="Violoncello"),
        ]
    ),
    ScoreTemplate(
        name="Jazz Combo",
        description="Lead, piano, bass, drums",
        category=TemplateCategory.ENSEMBLE,
        parts=[
            PartTemplate(name="Lead", clef="treble"),
            PartTemplate(name="Piano", clef="treble", instrument="Piano"),
            PartTemplate(name="Bass", clef="bass", instrument="ElectricBass"),
            PartTemplate(name="Drums", clef="percussion", instrument="DrumSet"),
        ]
    ),
    ScoreTemplate(
        name="Band - Bb Parts",
        description="Concert band Bb instruments",
        category=TemplateCategory.ENSEMBLE,
        parts=[
            PartTemplate(name="Bb Clarinet", clef="treble", instrument="Clarinet", transpose=-2),
            PartTemplate(name="Bb Trumpet", clef="treble", instrument="Trumpet", transpose=-2),
            PartTemplate(name="Tenor Sax", clef="treble", instrument="TenorSaxophone", transpose=-2),
        ]
    ),
]


class TemplateManager:
    """
    Manages score templates.
    
    Features:
    - Built-in templates for common layouts
    - User-created custom templates
    - Save/load templates to disk
    - Template categories for organization
    """
    
    def __init__(self, custom_templates_dir: Optional[Path] = None):
        """
        Initialize template manager.
        
        Args:
            custom_templates_dir: Directory for user templates
        """
        self._builtin = BUILTIN_TEMPLATES.copy()
        self._custom: List[ScoreTemplate] = []
        self._custom_dir = custom_templates_dir
        
        if self._custom_dir:
            self._custom_dir.mkdir(parents=True, exist_ok=True)
            self._load_custom_templates()
    
    @property
    def all_templates(self) -> List[ScoreTemplate]:
        """Get all templates (builtin + custom)."""
        return self._builtin + self._custom
    
    @property
    def builtin_templates(self) -> List[ScoreTemplate]:
        """Get built-in templates."""
        return self._builtin.copy()
    
    @property
    def custom_templates(self) -> List[ScoreTemplate]:
        """Get custom templates."""
        return self._custom.copy()
    
    def get_by_category(self, category: TemplateCategory) -> List[ScoreTemplate]:
        """Get templates in a category."""
        return [t for t in self.all_templates if t.category == category]
    
    def get_by_name(self, name: str) -> Optional[ScoreTemplate]:
        """Get a template by name."""
        for t in self.all_templates:
            if t.name.lower() == name.lower():
                return t
        return None
    
    def add_custom_template(self, template: ScoreTemplate) -> None:
        """
        Add a custom template.
        
        Args:
            template: Template to add
        """
        template.is_builtin = False
        template.category = TemplateCategory.CUSTOM
        
        # Remove existing with same name
        self._custom = [t for t in self._custom if t.name != template.name]
        
        self._custom.append(template)
        self._save_custom_templates()
    
    def remove_custom_template(self, name: str) -> bool:
        """
        Remove a custom template.
        
        Args:
            name: Template name
            
        Returns:
            True if removed
        """
        original_count = len(self._custom)
        self._custom = [t for t in self._custom if t.name != name]
        
        if len(self._custom) < original_count:
            self._save_custom_templates()
            return True
        return False
    
    def create_from_score(
        self,
        score,
        name: str,
        description: str = ""
    ) -> ScoreTemplate:
        """
        Create a template from an existing score.
        
        Args:
            score: Score object
            name: Template name
            description: Template description
            
        Returns:
            New ScoreTemplate
        """
        parts = []
        
        for part in score._score.parts:
            clef_name = "treble"
            for el in part.recurse():
                if isinstance(el, clef.Clef):
                    if isinstance(el, clef.BassClef):
                        clef_name = "bass"
                    elif isinstance(el, clef.AltoClef):
                        clef_name = "alto"
                    elif isinstance(el, clef.TenorClef):
                        clef_name = "tenor"
                    break
            
            parts.append(PartTemplate(
                name=part.partName or f"Part {len(parts) + 1}",
                clef=clef_name,
            ))
        
        return ScoreTemplate(
            name=name,
            description=description,
            category=TemplateCategory.CUSTOM,
            time_signature=score.time_signature or "4/4",
            key_signature=score.key_signature or "C major",
            tempo_bpm=120,
            parts=parts,
            is_builtin=False,
        )
    
    def _load_custom_templates(self) -> None:
        """Load custom templates from disk."""
        if not self._custom_dir:
            return
        
        templates_file = self._custom_dir / "templates.json"
        if not templates_file.exists():
            return
        
        try:
            with open(templates_file, 'r') as f:
                data = json.load(f)
            
            self._custom = [ScoreTemplate.from_dict(t) for t in data]
            logger.info(f"Loaded {len(self._custom)} custom templates")
            
        except Exception as e:
            logger.error(f"Failed to load custom templates: {e}")
    
    def _save_custom_templates(self) -> None:
        """Save custom templates to disk."""
        if not self._custom_dir:
            return
        
        templates_file = self._custom_dir / "templates.json"
        
        try:
            data = [t.to_dict() for t in self._custom]
            with open(templates_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Saved {len(self._custom)} custom templates")
            
        except Exception as e:
            logger.error(f"Failed to save custom templates: {e}")


# Singleton instance
_template_manager: Optional[TemplateManager] = None


def get_template_manager() -> TemplateManager:
    """Get the global template manager."""
    global _template_manager
    if _template_manager is None:
        from sheet_music_scanner.config import get_config
        config = get_config()
        _template_manager = TemplateManager(
            custom_templates_dir=config._config_dir / "templates"
        )
    return _template_manager
