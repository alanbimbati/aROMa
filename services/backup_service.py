
import os
import datetime
import subprocess
import glob
from services.event_dispatcher import EventDispatcher

class BackupService:
    """
    Manages automated database backups and cleanup.
    Runs pg_dump via Docker and deletes backups older than 30 days.
    """
    
    def __init__(self, backup_dir="backups", container_name="aroma_postgres", db_user="alan", db_name="aroma_bot"):
        self.backup_dir = backup_dir
        self.container_name = container_name
        self.db_user = db_user
        # Determine DB name from env or default, though usually passed or hardcoded for the setup
        self.db_name = db_name 
        self.retention_days = 30
        self.event_dispatcher = EventDispatcher()
        
        # Ensure backup directory exists
        #if not os.path.exists(self.backup_dir):
         #   os.makedirs(self.backup_dir)

    def create_backup(self):
        """Creates a new database dump."""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"aroma_backup_{timestamp}.sql"
        filepath = os.path.join(self.backup_dir, filename)
        
        print(f"[Backup] Starting database backup: {filename}")
        
        # Command to run pg_dump inside the container
        # Note: We rely on the system having 'docker' command accessible and permissions
        # If running as a service, might need specific paths or sudo. 
        # For now assuming the user runs python with sufficient rights or docker group.
        
        # Check if we are in test mode or prod to adjust DB name if necessary
        # But usually we want to backup the ACTIVE db. 
        # The bot knows the active DB from settings, but for pg_dump we need the name.
        # Let's try to detect or use the one passed in __init__.
        
        try:
            # Construct command
            # docker exec -t aroma_postgres pg_dump -U alan aroma_bot > filepath
            # We use subprocess.
            
            # Note: We can't easily redirect output of docker exec directly with shell=False without piping.
            # Best way: Use shell=True for the redirection, OR open file and write stdout.
            
            with open(filepath, 'w') as f:
                cmd = ["docker", "exec", "-t", self.container_name, "pg_dump", "-U", self.db_user, self.db_name]
                subprocess.run(cmd, stdout=f, check=True)
                
            print(f"[Backup] Backup created successfully: {filepath}")
            self.event_dispatcher.log_event('system_backup_created', user_id=0, value=0, context={'file': filename})
            
            # Trigger cleanup
            self.cleanup_old_backups()
            
            return True, filename
            
        except subprocess.CalledProcessError as e:
            print(f"[Backup] Failed to create backup: {e}")
            return False, str(e)
        except Exception as e:
            print(f"[Backup] Error: {e}")
            return False, str(e)

    def cleanup_old_backups(self):
        """Deletes backups older than retention_days."""
        print(f"[Backup] Checking for backups older than {self.retention_days} days...")
        
        now = datetime.datetime.now()
        pattern = os.path.join(self.backup_dir, "aroma_backup_*.sql")
        
        count = 0
        for filepath in glob.glob(pattern):
            try:
                # Check file modification time
                file_time = datetime.datetime.fromtimestamp(os.path.getmtime(filepath))
                age = now - file_time
                
                if age.days > self.retention_days:
                    os.remove(filepath)
                    count += 1
                    print(f"[Backup] Deleted old backup: {os.path.basename(filepath)}")
            except Exception as e:
                print(f"[Backup] Error checking file {filepath}: {e}")
                
        if count > 0:
            print(f"[Backup] Cleanup complete. Removed {count} old files.")
        else:
            print("[Backup] No old backups found to delete.")

