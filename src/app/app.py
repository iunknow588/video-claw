from departments.CEO.app import create_application
from departments.CEO.coordinator import register_ceo_routes

app = create_application()

# Register CEO-managed routes via the internal coordinator
register_ceo_routes(app)
