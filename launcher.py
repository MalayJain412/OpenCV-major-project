"""
VisionTrack Launcher

Provides easy startup options for different modes of the VisionTrack application.

Author: VisionTrack Project
"""

import sys
import os
import subprocess
import argparse
from pathlib import Path


def check_dependencies():
    """Check if required dependencies are installed."""
    required_packages = [
        ('flask', 'flask'),
        ('cv2', 'opencv-python'), 
        ('mediapipe', 'mediapipe'),
        ('numpy', 'numpy')
    ]
    missing_packages = []
    
    for import_name, package_name in required_packages:
        try:
            __import__(import_name)
        except ImportError:
            missing_packages.append(package_name)
    
    if missing_packages:
        print("❌ Missing required packages:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\n💡 Install missing packages with:")
        print(f"   pip install {' '.join(missing_packages)}")
        return False
    
    return True


def launch_web_app():
    """Launch the web application."""
    print("🚀 Starting VisionTrack Web Application...")
    print("📱 Open your browser and go to: http://localhost:5000")
    print("⏹️  Press Ctrl+C to stop the application")
    print("-" * 50)
    
    try:
        subprocess.run([sys.executable, 'app.py'], check=True)
    except KeyboardInterrupt:
        print("\n👋 VisionTrack application stopped.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error starting web application: {e}")


def launch_desktop_app():
    """Launch the desktop application (original run.py)."""
    print("🖥️  Starting VisionTrack Desktop Application...")
    print("⏹️  Press ESC to exit, Space to reset, S to save session")
    print("-" * 50)
    
    try:
        subprocess.run([sys.executable, 'run.py'], check=True)
    except KeyboardInterrupt:
        print("\n👋 VisionTrack desktop application stopped.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error starting desktop application: {e}")


def show_system_info():
    """Show system information and setup status."""
    print("🔍 VisionTrack System Information")
    print("=" * 50)
    
    # Python version
    print(f"🐍 Python: {sys.version}")
    
    # Project directory
    project_dir = Path(__file__).parent
    print(f"📁 Project Directory: {project_dir.absolute()}")
    
    # Check if key files exist
    key_files = [
        'app.py', 'run.py', 'requirements.txt',
        'modules/pose_detector.py', 'modules/fitness_analyzer.py',
        'modules/surveillance_analyzer.py', 'utils/database.py'
    ]
    
    print("\n📋 File Status:")
    for file in key_files:
        file_path = project_dir / file
        status = "✅" if file_path.exists() else "❌"
        print(f"   {status} {file}")
    
    # Check dependencies
    print("\n📦 Dependencies:")
    if check_dependencies():
        print("   ✅ All required packages installed")
    else:
        print("   ❌ Some packages missing (see above)")
    
    # Database status
    db_path = project_dir / 'visiontrack.db'
    if db_path.exists():
        print(f"   ✅ Database: {db_path} (exists)")
    else:
        print(f"   ℹ️  Database: {db_path} (will be created)")
    
    print("\n🎯 Available Launch Options:")
    print("   1. python launcher.py web    - Start web application")
    print("   2. python launcher.py desktop - Start desktop application")
    print("   3. python launcher.py info   - Show this information")


def main():
    """Main launcher function."""
    parser = argparse.ArgumentParser(
        description="VisionTrack Application Launcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python launcher.py web      # Start web application
  python launcher.py desktop  # Start desktop application
  python launcher.py info     # Show system information
        """
    )
    
    parser.add_argument(
        'mode',
        choices=['web', 'desktop', 'info'],
        help='Launch mode: web (Flask app), desktop (OpenCV app), or info (system status)'
    )
    
    parser.add_argument(
        '--check-deps',
        action='store_true',
        help='Check dependencies before launching'
    )
    
    args = parser.parse_args()
    
    # ASCII Art Header
    print("""
██╗   ██╗██╗███████╗██╗ ██████╗ ███╗   ██╗████████╗██████╗  █████╗  ██████╗██╗  ██╗
██║   ██║██║██╔════╝██║██╔═══██╗████╗  ██║╚══██╔══╝██╔══██╗██╔══██╗██╔════╝██║ ██╔╝
██║   ██║██║███████╗██║██║   ██║██╔██╗ ██║   ██║   ██████╔╝███████║██║     █████╔╝ 
╚██╗ ██╔╝██║╚════██║██║██║   ██║██║╚██╗██║   ██║   ██╔══██╗██╔══██║██║     ██╔═██╗ 
 ╚████╔╝ ██║███████║██║╚██████╔╝██║ ╚████║   ██║   ██║  ██║██║  ██║╚██████╗██║  ██╗
  ╚═══╝  ╚═╝╚══════╝╚═╝ ╚═════╝ ╚═╝  ╚═══╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝
    """)
    print("Real-Time Human Pose Estimation for Fitness, Surveillance & Interactive Systems")
    print("=" * 80)
    
    # Check dependencies if requested
    if args.check_deps or args.mode in ['web', 'desktop']:
        if not check_dependencies():
            print("\n❌ Cannot launch application due to missing dependencies.")
            return
    
    # Execute based on mode
    if args.mode == 'web':
        launch_web_app()
    elif args.mode == 'desktop':
        launch_desktop_app()
    elif args.mode == 'info':
        show_system_info()


if __name__ == '__main__':
    main()