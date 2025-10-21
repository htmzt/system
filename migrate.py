# migrate.py
"""
Database Migration Helper Script

Usage:
    python migrate.py init        # Create initial migration
    python migrate.py upgrade     # Apply migrations
    python migrate.py downgrade   # Rollback one migration
    python migrate.py history     # Show migration history
    python migrate.py current     # Show current revision
    python migrate.py auto        # Create auto-generated migration
"""

import sys
import subprocess
from pathlib import Path


def run_command(command):
    """Run a shell command"""
    print(f"\n{'='*60}")
    print(f"Running: {command}")
    print('='*60)
    result = subprocess.run(command, shell=True)
    if result.returncode != 0:
        print(f"\n❌ Command failed with exit code {result.returncode}")
        sys.exit(result.returncode)
    print("\n✅ Command completed successfully")
    return result.returncode


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    action = sys.argv[1].lower()
    
    if action == "init":
        # Create initial migration
        message = input("Enter migration message (default: 'Initial migration'): ").strip()
        if not message:
            message = "Initial migration"
        run_command(f'alembic revision --autogenerate -m "{message}"')
        print("\n📝 Migration created! Review it in alembic/versions/")
        print("   Then run: python migrate.py upgrade")
    
    elif action == "auto":
        # Create auto-generated migration
        message = input("Enter migration message: ").strip()
        if not message:
            print("❌ Message is required for migrations")
            sys.exit(1)
        run_command(f'alembic revision --autogenerate -m "{message}"')
        print("\n📝 Migration created! Review it in alembic/versions/")
        print("   Then run: python migrate.py upgrade")
    
    elif action == "upgrade":
        # Apply migrations
        revision = "head"
        if len(sys.argv) > 2:
            revision = sys.argv[2]
        run_command(f"alembic upgrade {revision}")
        print("\n✅ Database upgraded successfully!")
    
    elif action == "downgrade":
        # Rollback migrations
        steps = "-1"
        if len(sys.argv) > 2:
            steps = sys.argv[2]
        
        confirm = input(f"\n⚠️  Are you sure you want to downgrade {steps} revision(s)? (yes/no): ")
        if confirm.lower() != "yes":
            print("❌ Cancelled")
            sys.exit(0)
        
        run_command(f"alembic downgrade {steps}")
        print("\n✅ Database downgraded successfully!")
    
    elif action == "history":
        # Show migration history
        run_command("alembic history --verbose")
    
    elif action == "current":
        # Show current revision
        run_command("alembic current --verbose")
    
    elif action == "stamp":
        # Mark database as being at a certain revision without running migrations
        if len(sys.argv) < 3:
            print("❌ Usage: python migrate.py stamp <revision>")
            sys.exit(1)
        revision = sys.argv[2]
        run_command(f"alembic stamp {revision}")
    
    elif action == "heads":
        # Show head revisions
        run_command("alembic heads")
    
    elif action == "branches":
        # Show branch points
        run_command("alembic branches")
    
    elif action == "help":
        print(__doc__)
    
    else:
        print(f"❌ Unknown action: {action}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()