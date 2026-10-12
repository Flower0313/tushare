from sqlalchemy import BigInteger, Double, Text

from app.services.sync.type_mapper import TypeMapper


def test_type_mapper_maps_core_types_and_falls_back_to_text() -> None:
    mapper = TypeMapper()

    assert isinstance(mapper.to_sqlalchemy("str"), Text)
    assert isinstance(mapper.to_sqlalchemy("int"), BigInteger)
    assert isinstance(mapper.to_sqlalchemy("float"), Double)
    assert isinstance(mapper.to_sqlalchemy("unexpected"), Text)


def test_type_mapper_normalizes_upstream_scalar_values() -> None:
    mapper = TypeMapper()

    assert mapper.normalize_value("str", 0) == "0"
    assert mapper.normalize_value("int", "12") == 12
    assert mapper.normalize_value("float", "10.5") == 10.5
    assert mapper.normalize_value("bool", "true") is True
    assert mapper.normalize_value("str", None) is None
    assert mapper.normalize_value("str", "") == ""
