from app.app import app


def test_internal_tags_hidden_from_openapi() -> None:
    internal_tags = {"control", "orchestration", "operations"}
    for route in app.routes:
        tags = set(getattr(route, "tags", []) or [])
        if tags & internal_tags:
            assert route.include_in_schema is False, (
                f"Route {route.path} with tags {tags} should be hidden from OpenAPI"
            )
