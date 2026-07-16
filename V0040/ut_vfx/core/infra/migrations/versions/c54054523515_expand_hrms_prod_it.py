"""expand_hrms_prod_it

Revision ID: c54054523515
Revises: b6305c8549ef
Create Date: 2026-07-14 12:43:53.762257

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c54054523515'
down_revision: Union[str, Sequence[str], None] = 'b6305c8549ef'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute('''
    CREATE TABLE leave_requests (
        id SERIAL PRIMARY KEY,
        user_id VARCHAR(50) NOT NULL,
        start_date DATE NOT NULL,
        end_date DATE NOT NULL,
        type VARCHAR(50) NOT NULL,
        status VARCHAR(20) DEFAULT 'Pending',
        approved_by VARCHAR(50)
    );
    CREATE TABLE payroll_records (
        id SERIAL PRIMARY KEY,
        user_id VARCHAR(50) NOT NULL,
        month VARCHAR(20) NOT NULL,
        base_salary NUMERIC(10, 2) NOT NULL,
        overtime_hours NUMERIC(5, 2) DEFAULT 0,
        total NUMERIC(10, 2) NOT NULL,
        status VARCHAR(20) DEFAULT 'Pending'
    );
    CREATE TABLE onboarding_workflows (
        id SERIAL PRIMARY KEY,
        user_id VARCHAR(50) NOT NULL,
        task_name VARCHAR(255) NOT NULL,
        is_completed BOOLEAN DEFAULT FALSE,
        department VARCHAR(50)
    );
    CREATE TABLE performance_reviews (
        id SERIAL PRIMARY KEY,
        user_id VARCHAR(50) NOT NULL,
        reviewer_id VARCHAR(50) NOT NULL,
        review_date DATE NOT NULL,
        score NUMERIC(3, 1),
        notes TEXT
    );
    
    CREATE TABLE project_schedules (
        id SERIAL PRIMARY KEY,
        project_id VARCHAR(50) NOT NULL,
        task_name VARCHAR(255) NOT NULL,
        start_date DATE,
        target_date DATE,
        status VARCHAR(50) DEFAULT 'Not Started'
    );
    CREATE TABLE bidding_costs (
        id SERIAL PRIMARY KEY,
        project_id VARCHAR(50) NOT NULL,
        estimated_hours NUMERIC(10, 2),
        actual_hours NUMERIC(10, 2),
        quoted_price NUMERIC(15, 2),
        currency VARCHAR(10) DEFAULT 'USD'
    );
    
    CREATE TABLE hardware_inventory (
        id SERIAL PRIMARY KEY,
        machine_name VARCHAR(100) NOT NULL,
        assigned_to VARCHAR(50),
        gpu VARCHAR(100),
        ram VARCHAR(50),
        status VARCHAR(50) DEFAULT 'Active'
    );
    CREATE TABLE software_licenses (
        id SERIAL PRIMARY KEY,
        software_name VARCHAR(100) NOT NULL,
        total_seats INT DEFAULT 0,
        active_seats INT DEFAULT 0,
        expiration_date DATE
    );
    CREATE TABLE it_tickets (
        id SERIAL PRIMARY KEY,
        submitted_by VARCHAR(50) NOT NULL,
        category VARCHAR(50),
        description TEXT NOT NULL,
        status VARCHAR(50) DEFAULT 'Open',
        priority VARCHAR(20) DEFAULT 'Medium',
        resolved_at TIMESTAMP
    );
    ''')


def downgrade() -> None:
    """Downgrade schema."""
    op.execute('''
    DROP TABLE IF EXISTS it_tickets;
    DROP TABLE IF EXISTS software_licenses;
    DROP TABLE IF EXISTS hardware_inventory;
    DROP TABLE IF EXISTS bidding_costs;
    DROP TABLE IF EXISTS project_schedules;
    DROP TABLE IF EXISTS performance_reviews;
    DROP TABLE IF EXISTS onboarding_workflows;
    DROP TABLE IF EXISTS payroll_records;
    DROP TABLE IF EXISTS leave_requests;
    ''')
