"""Keep Alembic autogeneration from proposing deletion of unrelated legacy tables."""


def include_object(obj, name, type_, reflected, compare_to):
    # vehicle_profiles is a referenced legacy contract, never owned by autogenerate.
    return type_ != 'table' or name.startswith('ecosystem_')
