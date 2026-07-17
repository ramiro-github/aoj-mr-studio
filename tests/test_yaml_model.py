"""Tests for object.yaml model."""

from pathlib import Path

from aoj_mr_studio.yaml_model import ObjectDefinition, load_object_yaml, save_object_yaml


def test_roundtrip(tmp_path: Path) -> None:
    package = tmp_path / "Leon"
    package.mkdir()

    original = ObjectDefinition(
        name="Leon",
        display_name="Leon",
        model_file="leon.glb",
        surface_type=5,
        allow_stick_rotation=True,
        components=["grab"],
        grab_return_on_release=True,
    )
    save_object_yaml(package, original)
    loaded = load_object_yaml(package)

    assert loaded.name == "Leon"
    assert loaded.surface_type == 5
    assert loaded.allow_stick_rotation is True
    assert "grab" in loaded.components
    assert loaded.grab_return_on_release is True


def test_validate_missing_glb(tmp_path: Path) -> None:
    package = tmp_path / "Test"
    package.mkdir()
    definition = ObjectDefinition(name="Test", model_file="missing.glb")
    errors = definition.validate(package)
    assert any("model file not found" in error for error in errors)


def test_light_roundtrip(tmp_path: Path) -> None:
    package = tmp_path / "Lamp"
    package.mkdir()
    (package / "lamp.glb").write_bytes(b"glb")

    original = ObjectDefinition(
        name="Lamp",
        display_name="Candeeiro",
        model_file="lamp.glb",
        surface_type=2,
        components=["light"],
        light_target="Bulb",
        light_type="point",
        light_intensity=1.5,
        light_range=3.5,
        light_color_r=1.0,
        light_color_g=0.85,
        light_color_b=0.6,
        light_shadows=False,
    )
    save_object_yaml(package, original)
    loaded = load_object_yaml(package)

    assert "light" in loaded.components
    assert loaded.light_target == "Bulb"
    assert loaded.light_type == "point"
    assert loaded.light_intensity == 1.5
    assert loaded.light_color_g == 0.85
    assert loaded.validate(package) == []
