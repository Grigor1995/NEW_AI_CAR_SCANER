"""Local companion host preserving the source platform API contracts."""
from native_acceleration import install, status

# Patch before route/service imports capture the function references.
install()
from api.main import app  # noqa: E402


@app.get('/api/v1/migration/runtime', tags=['migration'])
def migration_runtime():
    return {'source_commit': 'a71c547b4b58f88f9c09f7f25d86931b79131bd2',
            'native': status(), 'host': 'local_companion',
            'account_scope': 'separate_from_v3_accounts', 'hardware_verified': False}
