import rv
import rv.commands as commands
import rv.rvtypes as rvtypes
import rv.qtutils as qtutils
import os
import json
import time

class UTVFXLinkMode(rvtypes.MinorMode):
    def __init__(self):
        rvtypes.MinorMode.__init__(self)
        self.init("UTVFXLink", None, None, [
            ("UT VFX", [
                ("Approve Current Shot", self.approve_shot, None, None),
                ("Reject Current Shot", self.reject_shot, None, None)
            ])
        ])

    def send_status(self, status):
        try:
            # Get current frame and sources
            frame = commands.frame()
            sources = commands.sourcesAtFrame(frame)
            if not sources:
                commands.displayFeedback("No media loaded", 2.0)
                return

            # RV gives sources like 'sourceGroup000_source'
            # Let's get the media property
            media_prop = "%s.media.movie" % sources[0]
            media_path = commands.getStringProperty(media_prop, 0, 1)[0]
            
            # Write feedback to json file
            feedback_dir = os.path.join(os.path.expanduser("~"), ".utvfx")
            if not os.path.exists(feedback_dir):
                os.makedirs(feedback_dir)
                
            feedback_file = os.path.join(feedback_dir, "rv_feedback.json")
            
            data = {
                "status": status,
                "media_path": media_path,
                "timestamp": time.time()
            }
            
            with open(feedback_file, "w", encoding="utf-8") as f:
                json.dump(data, f)
                
            commands.displayFeedback("UT VFX: Shot %s!" % status.upper(), 2.0)
        except Exception as e:
            commands.displayFeedback("UT VFX Error: %s" % str(e), 3.0)

    def approve_shot(self, event):
        self.send_status("approved")

    def reject_shot(self, event):
        self.send_status("rejected")

def createMode():
    return UTVFXLinkMode()
