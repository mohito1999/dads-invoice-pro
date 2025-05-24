# In your new migration file (e.g., xxxxx_rename_packing_list_enum_label.py)
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'your_new_revision_id_here' # Get this from the filename
down_revision = '908344afc5ef' # <-- IMPORTANT: Set this to the ID of your PREVIOUS migration 
                                # (the one that added packing list fields and the 'Packing List' enum value)
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Rename 'Packing List' to 'PACKING_LIST' if 'Packing List' exists and 'PACKING_LIST' does not.
    # This makes the operation idempotent if run multiple times or if already correct.
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'Packing List' AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'invoice_type_enum')) THEN
                IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'PACKING_LIST' AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'invoice_type_enum')) THEN
                    ALTER TYPE invoice_type_enum RENAME VALUE 'Packing List' TO 'PACKING_LIST';
                    RAISE NOTICE 'Renamed "Packing List" to "PACKING_LIST" in invoice_type_enum.';
                ELSE
                    RAISE NOTICE '"PACKING_LIST" already exists, "Packing List" also exists. Manual check might be needed if this is unexpected.';
                END IF;
            ELSIF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'PACKING_LIST' AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'invoice_type_enum')) THEN
                -- This case is if 'Packing List' was never added, but we want 'PACKING_LIST'
                -- This might have been handled by the previous migration, but for robustness:
                BEGIN
                    ALTER TYPE invoice_type_enum ADD VALUE 'PACKING_LIST';
                    RAISE NOTICE 'Added "PACKING_LIST" to invoice_type_enum as "Packing List" was not found.';
                EXCEPTION WHEN duplicate_object THEN
                    RAISE NOTICE 'Value "PACKING_LIST" already exists in invoice_type_enum (caught by ADD VALUE).';
                END;
            ELSE
                RAISE NOTICE '"PACKING_LIST" already exists, and "Packing List" not found. No action taken by RENAME logic.';
            END IF;
        END$$;
    """)

def downgrade() -> None:
    # To revert, rename 'PACKING_LIST' back to 'Packing List'
    # This also checks if 'PACKING_LIST' exists and 'Packing List' does not.
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'PACKING_LIST' AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'invoice_type_enum')) THEN
                IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'Packing List' AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'invoice_type_enum')) THEN
                    ALTER TYPE invoice_type_enum RENAME VALUE 'PACKING_LIST' TO 'Packing List';
                    RAISE NOTICE 'Renamed "PACKING_LIST" back to "Packing List" in invoice_type_enum.';
                ELSE
                    RAISE NOTICE '"Packing List" already exists. "PACKING_LIST" also exists. Manual check might be needed.';
                END IF;
            ELSE
                 RAISE NOTICE '"PACKING_LIST" not found. No action taken by RENAME logic in downgrade.';
            END IF;
        END$$;
    """)