"""Add identity and owner-approved workshop access without rewriting legacy rows."""
from alembic import op, context
import sqlalchemy as sa

revision = '0001_ecosystem'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # The existing local profile API creates this table lazily. Preserve it if present.
    if context.is_offline_mode():
        op.execute('CREATE TABLE IF NOT EXISTS vehicle_profiles (id VARCHAR(64) PRIMARY KEY, payload JSON NOT NULL)')
    elif not sa.inspect(op.get_bind()).has_table('vehicle_profiles'):
        op.create_table('vehicle_profiles', sa.Column('id', sa.String(64), primary_key=True), sa.Column('payload', sa.JSON(), nullable=False))
    op.create_table('ecosystem_accounts',
        sa.Column('id', sa.String(36), primary_key=True), sa.Column('email', sa.String(254), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(256), nullable=False), sa.Column('full_name', sa.String(200), nullable=False),
        sa.Column('mobile', sa.String(20)), sa.Column('language', sa.String(2), nullable=False),
        sa.Column('timezone', sa.String(100), nullable=False), sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('email_verified', sa.Boolean(), nullable=False), sa.Column('mobile_verified', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("language IN ('en','hy','ru')", name='ck_eco_language'))
    op.create_table('ecosystem_account_roles',
        sa.Column('account_id', sa.String(36), sa.ForeignKey('ecosystem_accounts.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('role', sa.String(16), primary_key=True), sa.CheckConstraint("role IN ('USER','CUSTOMER','ADMIN','MARKET')", name='ck_eco_role'))
    op.create_table('ecosystem_auth_sessions',
        sa.Column('token_hash', sa.String(64), primary_key=True),
        sa.Column('account_id', sa.String(36), sa.ForeignKey('ecosystem_accounts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False), sa.Column('revoked', sa.Boolean(), nullable=False))
    op.create_index('ix_ecosystem_auth_sessions_account_id', 'ecosystem_auth_sessions', ['account_id'])
    op.create_index('ix_ecosystem_auth_sessions_expires_at', 'ecosystem_auth_sessions', ['expires_at'])
    op.create_table('ecosystem_service_centers',
        sa.Column('id', sa.String(36), primary_key=True), sa.Column('name', sa.String(200), nullable=False),
        sa.Column('address', sa.String(500), nullable=False), sa.Column('phone', sa.String(20)),
        sa.Column('verified', sa.Boolean(), nullable=False), sa.Column('active', sa.Boolean(), nullable=False))
    op.create_table('ecosystem_staff',
        sa.Column('center_id', sa.String(36), sa.ForeignKey('ecosystem_service_centers.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('account_id', sa.String(36), sa.ForeignKey('ecosystem_accounts.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('role', sa.String(16), nullable=False), sa.Column('active', sa.Boolean(), nullable=False),
        sa.CheckConstraint("role IN ('owner','admin','technician','viewer')", name='ck_eco_staff_role'))
    op.create_table('ecosystem_vehicle_ownership',
        sa.Column('profile_id', sa.String(64), sa.ForeignKey('vehicle_profiles.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('account_id', sa.String(36), sa.ForeignKey('ecosystem_accounts.id', ondelete='CASCADE'), nullable=False))
    op.create_index('ix_ecosystem_vehicle_ownership_account_id', 'ecosystem_vehicle_ownership', ['account_id'])
    op.create_table('ecosystem_invitations',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('center_id', sa.String(36), sa.ForeignKey('ecosystem_service_centers.id', ondelete='CASCADE'), nullable=False),
        sa.Column('account_id', sa.String(36), sa.ForeignKey('ecosystem_accounts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False), sa.Column('accepted_at', sa.DateTime(timezone=True)))
    op.create_index('ix_ecosystem_invitations_account_id', 'ecosystem_invitations', ['account_id'])
    op.create_table('ecosystem_access_consents',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('owner_id', sa.String(36), sa.ForeignKey('ecosystem_accounts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('center_id', sa.String(36), sa.ForeignKey('ecosystem_service_centers.id', ondelete='CASCADE'), nullable=False),
        sa.Column('profile_id', sa.String(64), sa.ForeignKey('vehicle_profiles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('invitation_id', sa.String(36), sa.ForeignKey('ecosystem_invitations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('scopes', sa.JSON(), nullable=False), sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked', sa.Boolean(), nullable=False),
        sa.UniqueConstraint('owner_id', 'center_id', 'profile_id', name='uq_eco_vehicle_consent'))
    op.create_index('ix_ecosystem_access_consents_owner_id', 'ecosystem_access_consents', ['owner_id'])
    op.create_index('ix_ecosystem_access_consents_center_id', 'ecosystem_access_consents', ['center_id'])
    op.create_table('ecosystem_audit_events',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('actor_id', sa.String(36), sa.ForeignKey('ecosystem_accounts.id', ondelete='SET NULL')),
        sa.Column('action', sa.String(80), nullable=False), sa.Column('target_id', sa.String(64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False))
    op.create_index('ix_ecosystem_audit_events_actor_id', 'ecosystem_audit_events', ['actor_id'])
    op.create_index('ix_ecosystem_audit_events_created_at', 'ecosystem_audit_events', ['created_at'])


def downgrade():
    for table in ('ecosystem_audit_events', 'ecosystem_access_consents', 'ecosystem_invitations',
                  'ecosystem_vehicle_ownership', 'ecosystem_staff', 'ecosystem_service_centers',
                  'ecosystem_auth_sessions', 'ecosystem_account_roles', 'ecosystem_accounts'):
        op.drop_table(table)
    # Never drop the pre-existing/legacy profile table or its data.
