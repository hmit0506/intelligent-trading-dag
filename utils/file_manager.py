"""
File management utilities for output files (logs, JSON, CSV).
"""
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from colorama import Fore, Style, init

init(autoreset=True)


class OutputFileManager:
    """
    Manages output files in the output directory.
    Provides utilities to list, filter, and delete output files.
    """
    
    def __init__(self, output_dir: str = "output"):
        """
        Initialize the file manager.
        
        Args:
            output_dir: Path to the output directory
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    def list_files(self, file_type: Optional[str] = None) -> List[Dict[str, any]]:
        """
        List all output files, optionally filtered by type.
        
        Args:
            file_type: Filter by file type ('log', 'json', 'csv', None for all)
        
        Returns:
            List of file information dictionaries
        """
        files = []
        
        for file_path in self.output_dir.iterdir():
            if not file_path.is_file():
                continue
            
            # Determine file type
            suffix = file_path.suffix.lower()
            if suffix == '.log':
                ftype = 'log'
            elif suffix == '.json':
                ftype = 'json'
            elif suffix == '.csv':
                ftype = 'csv'
            else:
                ftype = 'other'
            
            # Filter by type if specified
            if file_type and ftype != file_type:
                continue
            
            # Get file stats
            stat = file_path.stat()
            size_mb = stat.st_size / (1024 * 1024)
            
            files.append({
                'path': file_path,
                'name': file_path.name,
                'type': ftype,
                'size_mb': size_mb,
                'size_bytes': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime),
                'created': datetime.fromtimestamp(stat.st_ctime),
            })
        
        # Sort by modified time (newest first)
        files.sort(key=lambda x: x['modified'], reverse=True)
        return files
    
    def get_file_summary(self) -> Dict[str, any]:
        """
        Get summary statistics of output files.
        
        Returns:
            Dictionary with summary statistics
        """
        all_files = self.list_files()
        
        summary = {
            'total_files': len(all_files),
            'total_size_mb': sum(f['size_mb'] for f in all_files),
            'by_type': {},
        }
        
        for file_info in all_files:
            ftype = file_info['type']
            if ftype not in summary['by_type']:
                summary['by_type'][ftype] = {
                    'count': 0,
                    'size_mb': 0.0,
                }
            summary['by_type'][ftype]['count'] += 1
            summary['by_type'][ftype]['size_mb'] += file_info['size_mb']
        
        return summary
    
    def delete_files(
        self,
        file_type: Optional[str] = None,
        older_than_days: Optional[int] = None,
        keep_latest: Optional[int] = None,
        dry_run: bool = False
    ) -> Tuple[int, List[str]]:
        """
        Delete files based on criteria.
        
        Args:
            file_type: Delete only files of this type ('log', 'json', 'csv', None for all)
            older_than_days: Delete files older than N days
            keep_latest: Keep the N latest files (by type if file_type specified)
            dry_run: If True, only show what would be deleted without actually deleting
        
        Returns:
            Tuple of (deleted_count, deleted_file_names)
        """
        files = self.list_files(file_type=file_type)
        files_to_delete = []
        
        if keep_latest is not None:
            # Keep only the N latest files
            files_to_delete = files[keep_latest:]
        elif older_than_days is not None:
            # Delete files older than N days
            cutoff_date = datetime.now().timestamp() - (older_than_days * 24 * 60 * 60)
            files_to_delete = [
                f for f in files
                if f['modified'].timestamp() < cutoff_date
            ]
        else:
            # Delete all files of the specified type
            files_to_delete = files
        
        deleted_count = 0
        deleted_names = []
        
        for file_info in files_to_delete:
            if not dry_run:
                try:
                    file_info['path'].unlink()
                    deleted_count += 1
                    deleted_names.append(file_info['name'])
                except Exception as e:
                    print(f"{Fore.RED}Error deleting {file_info['name']}: {e}{Style.RESET_ALL}")
            else:
                deleted_count += 1
                deleted_names.append(file_info['name'])
        
        return deleted_count, deleted_names
    
    def cleanup_old_files(
        self,
        max_age_days: int = 30,
        keep_latest: int = 10,
        dry_run: bool = False
    ) -> Dict[str, int]:
        """
        Clean up old files based on retention policy.
        
        Args:
            max_age_days: Delete files older than this many days
            keep_latest: Always keep at least this many latest files
            dry_run: If True, only show what would be deleted
        
        Returns:
            Dictionary with deletion counts by type
        """
        results = {}
        
        for file_type in ['log', 'json', 'csv']:
            files = self.list_files(file_type=file_type)
            
            if len(files) <= keep_latest:
                results[file_type] = 0
                continue
            
            # Get files older than max_age_days
            cutoff_date = datetime.now().timestamp() - (max_age_days * 24 * 60 * 60)
            old_files = [
                f for f in files
                if f['modified'].timestamp() < cutoff_date
            ]
            
            # But keep at least keep_latest files
            if len(old_files) > len(files) - keep_latest:
                old_files = files[keep_latest:]
            
            deleted_count = 0
            for file_info in old_files:
                if not dry_run:
                    try:
                        file_info['path'].unlink()
                        deleted_count += 1
                    except Exception as e:
                        print(f"{Fore.RED}Error deleting {file_info['name']}: {e}{Style.RESET_ALL}")
                else:
                    deleted_count += 1
            
            results[file_type] = deleted_count
        
        return results
    
    def print_summary(self):
        """Print a formatted summary of output files."""
        summary = self.get_file_summary()
        
        print(f"\n{Fore.WHITE}{Style.BRIGHT}OUTPUT FILES SUMMARY{Style.RESET_ALL}")
        print("=" * 80)
        print(f"Total Files: {Fore.CYAN}{summary['total_files']}{Style.RESET_ALL}")
        print(f"Total Size: {Fore.CYAN}{summary['total_size_mb']:.2f} MB{Style.RESET_ALL}")
        print("\nBy Type:")
        
        for ftype, stats in summary['by_type'].items():
            print(f"  {Fore.YELLOW}{ftype.upper()}{Style.RESET_ALL}: "
                  f"{Fore.CYAN}{stats['count']}{Style.RESET_ALL} files, "
                  f"{Fore.CYAN}{stats['size_mb']:.2f} MB{Style.RESET_ALL}")
    
    def print_file_list(self, file_type: Optional[str] = None, limit: int = 20):
        """
        Print a formatted list of files.
        
        Args:
            file_type: Filter by file type
            limit: Maximum number of files to display
        """
        files = self.list_files(file_type=file_type)
        
        if not files:
            print(f"{Fore.YELLOW}No files found.{Style.RESET_ALL}")
            return
        
        print(f"\n{Fore.WHITE}{Style.BRIGHT}OUTPUT FILES{Style.RESET_ALL}")
        print("=" * 80)
        
        # Print header
        print(f"{'Type':<8} {'Size (MB)':<12} {'Modified':<20} {'Filename'}")
        print("-" * 80)
        
        # Print files (limited)
        for file_info in files[:limit]:
            ftype_color = {
                'log': Fore.RED,
                'json': Fore.GREEN,
                'csv': Fore.BLUE,
            }.get(file_info['type'], Fore.WHITE)
            
            print(f"{ftype_color}{file_info['type']:<8}{Style.RESET_ALL} "
                  f"{file_info['size_mb']:<12.2f} "
                  f"{file_info['modified'].strftime('%Y-%m-%d %H:%M:%S'):<20} "
                  f"{file_info['name']}")
        
        if len(files) > limit:
            print(f"\n{Fore.YELLOW}... and {len(files) - limit} more files{Style.RESET_ALL}")


def main():
    """CLI interface for file management."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Manage output files")
    parser.add_argument(
        '--output-dir',
        default='output',
        help='Output directory path (default: output)'
    )
    parser.add_argument(
        '--list',
        action='store_true',
        help='List all output files'
    )
    parser.add_argument(
        '--summary',
        action='store_true',
        help='Show summary statistics'
    )
    parser.add_argument(
        '--type',
        choices=['log', 'json', 'csv'],
        help='Filter by file type'
    )
    parser.add_argument(
        '--delete-all',
        action='store_true',
        help='Delete all files (use with caution!)'
    )
    parser.add_argument(
        '--delete-type',
        choices=['log', 'json', 'csv'],
        help='Delete all files of specified type'
    )
    parser.add_argument(
        '--delete-older-than',
        type=int,
        metavar='DAYS',
        help='Delete files older than N days'
    )
    parser.add_argument(
        '--keep-latest',
        type=int,
        metavar='N',
        help='Keep only the N latest files'
    )
    parser.add_argument(
        '--cleanup',
        action='store_true',
        help='Clean up old files (keeps latest 10, deletes older than 30 days)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be deleted without actually deleting'
    )
    
    args = parser.parse_args()
    
    manager = OutputFileManager(args.output_dir)
    
    if args.summary:
        manager.print_summary()
    
    if args.list:
        manager.print_file_list(file_type=args.type)
    
    if args.delete_all:
        if not args.dry_run:
            confirm = input(f"{Fore.RED}Are you sure you want to delete ALL files? (yes/no): {Style.RESET_ALL}")
            if confirm.lower() != 'yes':
                print("Cancelled.")
                return
        
        count, names = manager.delete_files(dry_run=args.dry_run)
        action = "Would delete" if args.dry_run else "Deleted"
        print(f"\n{Fore.GREEN}{action} {count} files{Style.RESET_ALL}")
        if names:
            print("Files:")
            for name in names[:10]:
                print(f"  - {name}")
            if len(names) > 10:
                print(f"  ... and {len(names) - 10} more")
    
    if args.delete_type:
        count, names = manager.delete_files(file_type=args.delete_type, dry_run=args.dry_run)
        action = "Would delete" if args.dry_run else "Deleted"
        print(f"\n{Fore.GREEN}{action} {count} {args.delete_type} files{Style.RESET_ALL}")
        if names:
            for name in names[:10]:
                print(f"  - {name}")
            if len(names) > 10:
                print(f"  ... and {len(names) - 10} more")
    
    if args.delete_older_than:
        count, names = manager.delete_files(
            older_than_days=args.delete_older_than,
            dry_run=args.dry_run
        )
        action = "Would delete" if args.dry_run else "Deleted"
        print(f"\n{Fore.GREEN}{action} {count} files older than {args.delete_older_than} days{Style.RESET_ALL}")
        if names:
            for name in names[:10]:
                print(f"  - {name}")
            if len(names) > 10:
                print(f"  ... and {len(names) - 10} more")
    
    if args.keep_latest:
        count, names = manager.delete_files(
            keep_latest=args.keep_latest,
            file_type=args.type,
            dry_run=args.dry_run
        )
        action = "Would delete" if args.dry_run else "Deleted"
        print(f"\n{Fore.GREEN}{action} {count} files (keeping {args.keep_latest} latest){Style.RESET_ALL}")
        if names:
            for name in names[:10]:
                print(f"  - {name}")
            if len(names) > 10:
                print(f"  ... and {len(names) - 10} more")
    
    if args.cleanup:
        results = manager.cleanup_old_files(dry_run=args.dry_run)
        action = "Would delete" if args.dry_run else "Deleted"
        print(f"\n{Fore.GREEN}{action} files:{Style.RESET_ALL}")
        for ftype, count in results.items():
            print(f"  {ftype}: {count} files")


if __name__ == "__main__":
    main()

