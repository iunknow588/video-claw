from app.app import app


def test_ceo_route_prefix_not_exposed() -> None:
    disallowed_prefixes = ["/ceo", "/api/ceo"]
    for route in app.routes:
        for prefix in disallowed_prefixes:
            assert not route.path.startswith(prefix), (
                f"Route path {route.path} should not expose CEO prefix {prefix}"
            )
