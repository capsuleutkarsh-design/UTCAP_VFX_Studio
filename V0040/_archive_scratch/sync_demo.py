import sys
from pathlib import Path
sys.path.insert(0, r'D:\Soft\UTCAP\V0040')

from ut_vfx.gui.tabs.vfx_dashboard_pro.core.project_manager import ProjectManager
from ut_vfx.gui.tabs.vfx_dashboard_pro.core.excel_handler import ExcelHandler
from ut_vfx.gui.tabs.vfx_dashboard_pro.core.sqlite_handler import SQLiteHandler

def sync_demo():
    print("Syncing DEMO project...")
    pm = ProjectManager()
    
    excel_path = r'D:\Soft\UTCAP\V0040\ut_vfx\gui\tabs\vfx_dashboard_pro\sample_project.xlsx'
    
    # Check if DEMO exists
    project = pm.get_project('DEMO')
    if not project:
        print("Creating DEMO project config...")
        project = pm.add_project(
            code='DEMO',
            name='Demo Project',
            excel_path=excel_path,
            folder_base=r'D:\Soft\UTCAP\V0040\ut_vfx\data\demo_project'
        )
    
    print("Reading Excel...")
    excel = ExcelHandler(excel_path, project_config=project)
    shots = excel.read_shots()
    print(f"Read {len(shots)} shots from Excel.")
    
    if shots:
        for s in shots:
            s.project_code = 'DEMO'
            
        print("Saving shots to database...")
        db = SQLiteHandler('DEMO')
        db.user_roles = ['admin']
        success = db.write_shots(shots)
        print(f"Success: {success}")
    
if __name__ == '__main__':
    sync_demo()
