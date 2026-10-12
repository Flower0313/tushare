from app.core.codes import ErrorCode, WarningCode
from app.core.exceptions import PlatformError
from app.main import app


def all_subclasses(base: type[PlatformError]) -> set[type[PlatformError]]:
    children = set(base.__subclasses__())
    return children | {nested for child in children for nested in all_subclasses(child)}


def test_all_platform_error_codes_use_contract_enum() -> None:
    classes = {PlatformError, *all_subclasses(PlatformError)}
    assert all(isinstance(error_type.code, ErrorCode) for error_type in classes)


def test_error_and_warning_codes_are_exposed_in_openapi() -> None:
    schemas = app.openapi()["components"]["schemas"]
    assert set(schemas["ErrorCode"]["enum"]) == {code.value for code in ErrorCode}
    assert set(schemas["WarningCode"]["enum"]) == {code.value for code in WarningCode}
    assert schemas["ApiErrorResponse"]["properties"]["error"]["$ref"].endswith("/ErrorDetail")
